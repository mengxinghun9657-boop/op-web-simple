"""
BCE 数据同步服务
将百度云 BCC 实例和 CCE 节点数据下载并写入本地容器数据库
（复用 auto_download_instanceID 中的下载逻辑，集成到后端服务）
"""
import csv
import io
import time
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from loguru import logger
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.core.database import get_db_connection


# ========== 下载器（内联，避免跨目录依赖） ==========

class _BCCDownloader:
    def __init__(self, cookies: str, region: str = 'cd'):
        self.base_url = "https://console.bce.baidu.com/api/bcc/instance/download"
        self.region = region
        # trust_env=True（默认）：自动读取环境变量中的 HTTP_PROXY/HTTPS_PROXY/NO_PROXY
        # docker-compose 中已将 console.bce.baidu.com 加入 NO_PROXY，会绕过代理直连
        self.session = requests.Session()
        self.session.trust_env = True
        for cookie in cookies.split('; '):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session.cookies.set(name, value)
        csrf_token = self._extract_csrf_token()
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'csrftoken': csrf_token,
            'referer': 'https://console.bce.baidu.com/bcc/',
            'user-agent': 'Mozilla/5.0',
            'x-region': region,
            'x-request-by': 'RestClient'
        }

    def _extract_csrf_token(self):
        bce_user_info = self.session.cookies.get('bce-user-info')
        return bce_user_info.strip('"') if bce_user_info else None

    def download(self) -> Dict[str, Any]:
        params = {
            'keywordType': 'fuzzySearch',
            'order': 'desc',
            'orderBy': 'createTime',
            'serverType': 'BCC',
            'enableBid': True,
            'filters': json.dumps([]),
            'needAlarmStatus': True,
            'isAdvancedSearch': False,
            'region': self.region,
            'locale': 'zh-cn',
            '_': str(int(time.time() * 1000))
        }
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            response = self.session.post(url, headers=self.headers, json={}, timeout=60)
            response.raise_for_status()
            text = response.text
            if text.startswith('\ufeff'):
                text = text[1:]
            if not text.strip():
                return {'success': False, 'error': '响应为空'}
            if text.startswith('BCC_ID,') or (',' in text and '\n' in text):
                return {'success': True, 'data': text, 'format': 'csv'}
            return {'success': False, 'error': '非CSV响应', 'raw': text[:200]}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class _CCEDownloader:
    def __init__(self, cookies: str, region: str = 'cd'):
        self.base_url_base = "https://console.bce.baidu.com/api/cce/service/v2/cluster"
        self.region = region
        # 同 BCCDownloader：trust_env=True 读取 NO_PROXY，console.bce.baidu.com 已在其中
        self.session = requests.Session()
        self.session.trust_env = True
        for cookie in cookies.split('; '):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session.cookies.set(name, value)
        csrf_token = self._extract_csrf_token()
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'csrftoken': csrf_token,
            'referer': 'https://console.bce.baidu.com/cce/',
            'user-agent': 'Mozilla/5.0',
            'x-region': region,
            'x-request-by': 'RestClient'
        }

    def _extract_csrf_token(self):
        bce_user_info = self.session.cookies.get('bce-user-info')
        return bce_user_info.strip('"') if bce_user_info else None

    def download(self, cluster_id: str) -> Dict[str, Any]:
        params = {'locale': 'zh-cn', '_': str(int(time.time() * 1000))}
        url = f"{self.base_url_base}/{cluster_id}/instances/download?{urlencode(params)}"
        payload = {
            "cceInstanceIDs": [],
            "exportAll": True,
            "calculateGPUCountRequested": False,
            "keywordType": "k8sNodeName",
            "clusterUuid": cluster_id,
            "clusterRole": "node",
            "orderBy": "createdAt",
            "order": "desc",
        }
        try:
            response = self.session.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            text = response.text
            if text.startswith('\ufeff'):
                text = text[1:]
            if not text.strip():
                return {'success': False, 'error': '响应为空'}
            if ',' in text and '\n' in text:
                return {'success': True, 'data': text, 'format': 'csv'}
            return {'success': False, 'error': '非CSV响应', 'raw': text[:200]}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ========== 数据库写入器（写容器本地库） ==========

class _LocalDBWriter:
    """将 CSV 数据写入容器本地 MySQL（cluster_management 库）"""

    @staticmethod
    def _clean_field(name: str) -> str:
        return (name.replace(' ', '_').replace('%', 'percent')
                .replace('/', '_').replace('(', '').replace(')', '')
                .replace('-', '_').lower())

    @staticmethod
    def _infer_type(value: str) -> str:
        if not value:
            return 'TEXT'
        try:
            if '.' in value:
                float(value)
                return 'DECIMAL(20,2)'
            else:
                int(value)
                return 'INT'
        except (ValueError, TypeError):
            pass
        ln = len(value)
        if ln <= 50:
            return 'VARCHAR(100)'
        elif ln <= 255:
            return 'VARCHAR(500)'
        return 'TEXT'

    @staticmethod
    def _convert(value: str):
        if not value or str(value).strip().upper() in ('N/A', 'NULL', '-'):
            return None
        v = str(value).strip()
        try:
            if '.' in v:
                return float(v)
            return int(v)
        except (ValueError, TypeError):
            return v

    def _ensure_table(self, conn, table: str, headers: List[str],
                       sample_rows: List[Dict], source_type: str):
        """建表（若不存在）"""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            if cursor.fetchone():
                return
            cleaned = [self._clean_field(h) for h in headers]
            # 推断字段类型
            types = []
            for orig in headers:
                vals = [r.get(orig, '') for r in sample_rows[:100]]
                max_val = max(vals, key=lambda x: len(str(x)) if x else 0)
                types.append(self._infer_type(max_val))
            if source_type == 'BCC':
                base = [('id', 'BIGINT AUTO_INCREMENT'), ('collect_date', 'DATE'), ('insert_time', 'DATETIME')]
                unique = f"UNIQUE KEY `uk_bcc_id` (`{cleaned[0]}`)" if cleaned else ''
            else:
                base = [('id', 'BIGINT AUTO_INCREMENT'), ('cluster_id', 'VARCHAR(100)'),
                        ('collect_date', 'DATE'), ('insert_time', 'DATETIME')]
                if len(cleaned) >= 2:
                    unique = f"UNIQUE KEY `uk_cluster_instance` (`cluster_id`, `{cleaned[1]}`)"
                else:
                    unique = "UNIQUE KEY `uk_cluster_date` (`cluster_id`, `collect_date`)"
            col_defs = ', '.join([f'`{f}` {t}' for f, t in base])
            col_defs += ', ' + ', '.join([f'`{f}` {t}' for f, t in zip(cleaned, types)])
            sql = (f"CREATE TABLE `{table}` ({col_defs}, PRIMARY KEY (`id`)"
                   + (f', {unique}' if unique else '') + ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
            cursor.execute(sql)
            conn.commit()
            logger.info(f"✓ 创建表 `{table}`")
        finally:
            cursor.close()

    def import_csv(self, csv_text: str, table: str, source_type: str,
                   cluster_id: str = '', collect_date: Optional[datetime] = None) -> Dict[str, Any]:
        """将 CSV 文本写入指定表，返回统计结果"""
        if collect_date is None:
            collect_date = datetime.now().date()
        insert_time = datetime.now()

        reader = csv.DictReader(io.StringIO(csv_text))
        headers = reader.fieldnames or []
        rows = list(reader)

        if not rows:
            return {'success': False, 'error': '无有效数据行'}

        conn = get_db_connection()
        try:
            self._ensure_table(conn, table, headers, rows, source_type)
            cleaned_headers = [self._clean_field(h) for h in headers]

            if source_type == 'BCC':
                all_fields = ['collect_date', 'insert_time'] + cleaned_headers
            else:
                all_fields = ['cluster_id', 'collect_date', 'insert_time'] + cleaned_headers

            insert_fields = ', '.join([f'`{f}`' for f in all_fields])
            placeholders = ', '.join(['%s'] * len(all_fields))
            update_parts = ', '.join([f'`{f}`=VALUES(`{f}`)' for f in cleaned_headers])
            update_parts += ', `collect_date`=VALUES(`collect_date`), `insert_time`=VALUES(`insert_time`)'

            sql = (f"INSERT INTO `{table}` ({insert_fields}) VALUES ({placeholders})"
                   f" ON DUPLICATE KEY UPDATE {update_parts}")

            insert_values = []
            for row in rows:
                if source_type == 'BCC':
                    row_data = [collect_date, insert_time]
                else:
                    row_data = [cluster_id, collect_date, insert_time]
                for orig in headers:
                    row_data.append(self._convert(row.get(orig, '')))
                insert_values.append(row_data)

            cursor = conn.cursor()
            try:
                cursor.executemany(sql, insert_values)
                conn.commit()
                count = len(insert_values)
                logger.info(f"✓ {source_type} 写入/更新 {count} 条 -> {table}")
                return {'success': True, 'count': count}
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"写入 {table} 失败: {e}")
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()


# ========== 主服务 ==========

class BCESyncService:
    """BCE 数据同步服务（BCC实例 + CCE节点 → 容器本地库）"""

    MODULE = 'bce_sync'
    BCC_TABLE = 'bce_bcc_instances'
    CCE_TABLE = 'bce_cce_nodes'

    # 默认配置（与 auto_download_instanceID/config.py 保持一致）
    DEFAULTS = {
        'region': 'cd',
        'cluster_ids': [
            'cce-266b50jq', 'cce-3nusu9su', 'cce-9m1ht29q', 'cce-elwhlymq',
            'cce-48c915gn', 'cce-ld2ckre2', 'cce-216ima4l', 'cce-2ys5dxch',
            'cce-75n0j16r', 'cce-hcbs74xg', 'cce-xrg955qz', 'cce-pog0r4mg',
            'cce-gzk0qlzk', 'cce-p6w3c5z8', 'cce-uk1zi507', 'cce-k5sn275j',
            'cce-4nmy1x1s',
        ],
        'bce_cookie': '',
    }

    def __init__(self, db: Session):
        self.db = db
        self._writer = _LocalDBWriter()

    # -------- 配置读写（复用 SystemConfig 表，config_key='main' 存 JSON blob）--------

    def _load_config(self) -> Dict[str, Any]:
        """从 SystemConfig 读取完整配置，不存在时返回默认值"""
        row = self.db.query(SystemConfig).filter_by(
            module=self.MODULE, config_key='main').first()
        if row and row.config_value:
            try:
                stored = json.loads(row.config_value)
                # 用默认值补全缺失字段（但不覆盖已配置的值）
                result = dict(self.DEFAULTS)
                result.update(stored)
                return result
            except Exception:
                pass
        return dict(self.DEFAULTS)

    def _save_config(self, patch: Dict[str, Any], updated_by_id: Optional[int] = None):
        """将 patch 合并到现有配置后写回"""
        current = self._load_config()
        current.update(patch)
        config_value = json.dumps(current, ensure_ascii=False)
        row = self.db.query(SystemConfig).filter_by(
            module=self.MODULE, config_key='main').first()
        if row:
            row.config_value = config_value
            row.updated_at = datetime.utcnow()
            if updated_by_id:
                row.updated_by = updated_by_id
        else:
            row = SystemConfig(
                module=self.MODULE,
                config_key='main',
                config_value=config_value,
                description='BCE 数据同步配置（Cookie、区域、集群ID列表）',
                updated_by=updated_by_id,
            )
            self.db.add(row)
        self.db.commit()

    def get_full_config(self) -> Dict[str, Any]:
        """返回完整配置（供前端展示，Cookie 脱敏）"""
        cfg = self._load_config()
        cookie = cfg.get('bce_cookie', '')
        return {
            'cookie_configured': bool(cookie),
            'cookie_preview': (cookie[:10] + '...' + cookie[-10:]) if len(cookie) > 20 else None,
            'region': cfg.get('region', self.DEFAULTS['region']),
            'cluster_ids': cfg.get('cluster_ids', self.DEFAULTS['cluster_ids']),
        }

    def update_config(self, cookie: str = '', region: str = '',
                      cluster_ids: Optional[List[str]] = None,
                      updated_by_id: Optional[int] = None):
        """更新配置（只更新传入的非空字段）"""
        patch: Dict[str, Any] = {}
        if cookie:
            patch['bce_cookie'] = cookie
        if region:
            patch['region'] = region
        if cluster_ids is not None:
            patch['cluster_ids'] = cluster_ids
        if patch:
            self._save_config(patch, updated_by_id=updated_by_id)

    def get_cookie(self) -> Optional[str]:
        return self._load_config().get('bce_cookie') or None

    def get_region(self) -> str:
        return self._load_config().get('region', self.DEFAULTS['region'])

    def get_cluster_ids(self) -> List[str]:
        return self._load_config().get('cluster_ids', self.DEFAULTS['cluster_ids'])

    # -------- 同步执行 --------

    def sync_bcc(self) -> Dict[str, Any]:
        """下载 BCC 实例并写入本地库"""
        cookie = self.get_cookie()
        if not cookie:
            return {'success': False, 'error': '未配置 BCE Cookie'}
        region = self.get_region()
        logger.info(f"开始同步 BCC 实例（region={region}）")
        result = _BCCDownloader(cookie, region).download()
        if not result['success']:
            return result
        write_result = self._writer.import_csv(
            result['data'], self.BCC_TABLE, 'BCC',
            collect_date=datetime.now().date()
        )
        if write_result['success']:
            logger.info(f"BCC 同步完成，写入 {write_result['count']} 条")
        return write_result

    def sync_cce(self, cluster_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """下载 CCE 节点并写入本地库，支持多集群"""
        cookie = self.get_cookie()
        if not cookie:
            return {'success': False, 'error': '未配置 BCE Cookie'}
        region = self.get_region()
        if cluster_ids is None:
            cluster_ids = self.get_cluster_ids()
        if not cluster_ids:
            return {'success': False, 'error': '未配置集群 ID'}

        results = {}
        total_count = 0
        has_error = False
        downloader = _CCEDownloader(cookie, region)
        for cid in cluster_ids:
            logger.info(f"同步 CCE 集群 {cid}")
            dl = downloader.download(cid)
            if not dl['success']:
                results[cid] = {'success': False, 'error': dl['error']}
                has_error = True
                continue
            wr = self._writer.import_csv(
                dl['data'], self.CCE_TABLE, 'CCE',
                cluster_id=cid,
                collect_date=datetime.now().date()
            )
            results[cid] = wr
            if wr['success']:
                total_count += wr['count']
            else:
                has_error = True

        return {
            'success': not has_error,
            'total_count': total_count,
            'clusters': results
        }

    def sync_all(self) -> Dict[str, Any]:
        """同步全部：BCC + 所有 CCE 集群"""
        bcc = self.sync_bcc()
        cce = self.sync_cce()
        return {
            'success': bcc.get('success', False) and cce.get('success', False),
            'bcc': bcc,
            'cce': cce
        }

    def get_table_stats(self) -> Dict[str, Any]:
        """查询本地库中 BCC/CCE 表的记录数和最新采集日期"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            stats = {}
            for tbl, key in [(self.BCC_TABLE, 'bcc'), (self.CCE_TABLE, 'cce')]:
                try:
                    cursor.execute(f"SELECT COUNT(*), MAX(collect_date) FROM `{tbl}`")
                    row = cursor.fetchone()
                    stats[key] = {
                        'count': row[0] if row else 0,
                        'latest_date': row[1].isoformat() if row and row[1] else None
                    }
                except Exception:
                    stats[key] = {'count': 0, 'latest_date': None}
            cursor.close()
            conn.close()
            return stats
        except Exception as e:
            return {'error': str(e)}
