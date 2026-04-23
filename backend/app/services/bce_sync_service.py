"""
BCE 数据同步服务
将百度云 BCC 实例和 CCE 节点数据写入本地容器数据库
使用 BCE 官方 API（AK/SK 鉴权），不依赖 Cookie
"""
import csv
import io
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from loguru import logger
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig
from app.core.database import get_db_connection


# ========== BCE 官方 API 下载器 ==========

# BCC 官方 API endpoint（成都区域）
_BCC_ENDPOINT_MAP = {
    'cd': 'bcc.cd.baidubce.com',
    'bj': 'bcc.bj.baidubce.com',
    'gz': 'bcc.gz.baidubce.com',
    'su': 'bcc.su.baidubce.com',
}

# CCE 官方 API endpoint
_CCE_ENDPOINT_MAP = {
    'cd': 'cce.cd.baidubce.com',
    'bj': 'cce.bj.baidubce.com',
    'gz': 'cce.gz.baidubce.com',
    'su': 'cce.su.baidubce.com',
}


def _make_bcc_client(access_key: str, secret_key: str, region: str):
    """构造 baidubce BCC 客户端"""
    from baidubce.bce_client_configuration import BceClientConfiguration
    from baidubce.auth.bce_credentials import BceCredentials
    from baidubce.services.bcc.bcc_client import BccClient

    endpoint = _BCC_ENDPOINT_MAP.get(region, f'bcc.{region}.baidubce.com')
    config = BceClientConfiguration(
        credentials=BceCredentials(access_key, secret_key),
        endpoint=endpoint,
    )
    return BccClient(config)


def _make_cce_signed_session(access_key: str, secret_key: str):
    """返回一个带有 BCE 签名能力的 requests Session（用于 CCE REST API）
    使用 bce-python-sdk 的 bce_v1_signer，签名算法与 BCC/BOS/EIP 保持一致
    """
    import baidubce.auth.bce_v1_signer as bce_signer
    from baidubce.auth.bce_credentials import BceCredentials
    from urllib.parse import urlparse, parse_qs

    creds = BceCredentials(access_key.encode(), secret_key.encode())

    class _BCEAuth(requests.auth.AuthBase):
        def __call__(self, r):
            parsed = urlparse(r.url)
            host = parsed.netloc
            qs_dict = {}
            if parsed.query:
                for k, v_list in parse_qs(parsed.query, keep_blank_values=True).items():
                    qs_dict[k] = v_list[0] if v_list else ''
            headers = {b'host': host.encode()}
            auth_bytes = bce_signer.sign(
                creds, b'GET', parsed.path.encode(), headers, qs_dict
            )
            r.headers['Authorization'] = auth_bytes.decode()
            r.headers['host'] = host
            return r

    session = requests.Session()
    session.auth = _BCEAuth()
    return session


class _BCCApiClient:
    """使用 baidubce SDK 获取 BCC 实例列表"""

    def __init__(self, access_key: str, secret_key: str, region: str = 'cd'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

    def list_all_instances(self) -> Dict[str, Any]:
        """分页获取全部 BCC 实例，返回标准化字段列表"""
        try:
            client = _make_bcc_client(self.access_key, self.secret_key, self.region)
            all_instances = []
            marker = None
            while True:
                resp = client.list_instances(marker=marker, max_keys=1000)
                items = resp.instances if hasattr(resp, 'instances') else []
                for inst in items:
                    all_instances.append(self._normalize(inst))
                if not getattr(resp, 'is_truncated', False):
                    break
                marker = getattr(resp, 'next_marker', None)
                if not marker:
                    break
            return {'success': True, 'instances': all_instances}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _normalize(inst) -> Dict[str, Any]:
        """将 SDK 返回的对象转为扁平 dict"""
        d = inst.__dict__ if hasattr(inst, '__dict__') else {}
        nic = d.get('nic_info') or {}
        if hasattr(nic, '__dict__'):
            nic = nic.__dict__
        ips = nic.get('ips') or []
        eip = ''
        if ips:
            first = ips[0]
            if hasattr(first, '__dict__'):
                first = first.__dict__
            eip = first.get('eip', '') or ''
        tags = d.get('tags') or []
        tag_str = ','.join(
            f"{(t.__dict__ if hasattr(t, '__dict__') else t).get('tag_key','')}:"
            f"{(t.__dict__ if hasattr(t, '__dict__') else t).get('tag_value','')}"
            for t in tags
        )
        return {
            'BCC_ID': d.get('id', ''),
            '名称': d.get('name', ''),
            '实例规格': d.get('spec', '') or d.get('instance_type', ''),
            '状态': d.get('status', ''),
            '内网IP': d.get('internal_ip', ''),
            '公网IP': eip,
            'CPU': d.get('cpu_count', ''),
            '内存(GB)': d.get('memory_capacity_in_g_b', '') or d.get('memory_capacity_in_gb', ''),
            '付费方式': d.get('payment_timing', ''),
            '创建时间': d.get('create_time', ''),
            '到期时间': d.get('expire_time', ''),
            '可用区': d.get('zone_name', ''),
            'VPC_ID': d.get('vpc_id', ''),
            '子网ID': d.get('subnet_id', ''),
            '标签': tag_str,
        }


class _CCEApiClient:
    """使用 BCE REST API 获取 CCE 集群节点列表"""

    def __init__(self, access_key: str, secret_key: str, region: str = 'cd'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        endpoint = _CCE_ENDPOINT_MAP.get(region, f'cce.{region}.baidubce.com')
        self.base_url = f'https://{endpoint}'
        self.session = _make_cce_signed_session(access_key, secret_key)

    def list_cluster_nodes(self, cluster_id: str) -> Dict[str, Any]:
        """获取集群所有节点"""
        try:
            all_nodes = []
            page_no = 1
            page_size = 100
            while True:
                url = f"{self.base_url}/v2/cluster/{cluster_id}/instances"
                params = {'pageNo': page_no, 'pageSize': page_size}
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                # 实测响应结构：data.instancePage.instanceList
                instance_page = data.get('instancePage') or data.get('result') or data
                nodes = instance_page.get('instanceList') or []
                if not nodes:
                    break
                for n in nodes:
                    all_nodes.append(self._normalize(n, cluster_id))
                total = instance_page.get('totalCount') or instance_page.get('total', 0)
                if len(all_nodes) >= total or len(nodes) < page_size:
                    break
                page_no += 1
            return {'success': True, 'nodes': all_nodes}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _normalize(node: Dict, cluster_id: str) -> Dict[str, Any]:
        # 实测响应结构：
        #   IP          → status.machine.vpcIP
        #   k8sNodeName → status.machine.k8sNodeName
        #   BCC实例ID   → status.machine.instanceID
        #   CPU/内存    → spec.instanceResource.cpu/mem
        #   OS          → spec.instanceOS.osName
        spec = node.get('spec') or {}
        status = node.get('status') or {}
        machine_status = status.get('machine') or {}
        inst_resource = spec.get('instanceResource') or {}
        inst_os = spec.get('instanceOS') or {}
        vpc_cfg = spec.get('vpcConfig') or {}
        return {
            '节点ID': machine_status.get('instanceID') or spec.get('cceInstanceID', ''),
            '节点名称': spec.get('instanceName', ''),
            'K8S节点名': machine_status.get('k8sNodeName', ''),
            '状态': status.get('instancePhase', ''),
            '内网IP': machine_status.get('vpcIP', ''),
            'CPU核数': inst_resource.get('cpu', ''),
            '内存(GB)': inst_resource.get('mem', ''),
            '操作系统': inst_os.get('osName', '') or inst_os.get('imageName', ''),
            '节点角色': spec.get('clusterRole', ''),
            '机器类型': spec.get('machineType', ''),
            '可用区': vpc_cfg.get('availableZone', ''),
            '集群ID': cluster_id,
            '创建时间': node.get('createdAt', ''),
        }


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
                # 全量替换：API 数据已确认正常后，先删除旧数据，再写入新数据，避免已释放/下线资源残留
                if source_type == 'BCC':
                    cursor.execute(f"DELETE FROM `{table}`")
                elif source_type == 'CCE' and cluster_id:
                    cursor.execute(f"DELETE FROM `{table}` WHERE `cluster_id`=%s", (cluster_id,))
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

    DEFAULTS = {
        'region': 'cd',
        'access_key': '',
        'secret_key': '',
    }

    def __init__(self, db: Session):
        self.db = db
        self._writer = _LocalDBWriter()

    # -------- 配置读写 --------

    def _load_config(self) -> Dict[str, Any]:
        row = self.db.query(SystemConfig).filter_by(
            module=self.MODULE, config_key='main').first()
        if row and row.config_value:
            try:
                stored = json.loads(row.config_value)
                result = dict(self.DEFAULTS)
                result.update(stored)
                return result
            except Exception:
                pass
        return dict(self.DEFAULTS)

    def _save_config(self, patch: Dict[str, Any], updated_by_id: Optional[int] = None):
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
                description='BCE 数据同步配置（AK/SK、区域、集群ID列表）',
                updated_by=updated_by_id,
            )
            self.db.add(row)
        self.db.commit()

    def get_full_config(self) -> Dict[str, Any]:
        """返回完整配置（供前端展示，SK 脱敏）"""
        cfg = self._load_config()
        ak = cfg.get('access_key', '')
        sk = cfg.get('secret_key', '')
        return {
            'access_key': ak,
            'secret_key_configured': bool(sk),
            'secret_key_preview': (sk[:4] + '****' + sk[-4:]) if len(sk) > 8 else ('****' if sk else ''),
            'region': cfg.get('region', self.DEFAULTS['region']),
        }

    def update_config(self, access_key: str = '', secret_key: str = '',
                      region: str = '', cluster_ids: Optional[List[str]] = None,
                      updated_by_id: Optional[int] = None):
        patch: Dict[str, Any] = {}
        if access_key:
            patch['access_key'] = access_key
        if secret_key:
            patch['secret_key'] = secret_key
        if region:
            patch['region'] = region
        # cluster_ids 参数保留兼容但不再保存
        if patch:
            self._save_config(patch, updated_by_id=updated_by_id)

    def get_credentials(self):
        cfg = self._load_config()
        return cfg.get('access_key', ''), cfg.get('secret_key', '')

    def get_region(self) -> str:
        return self._load_config().get('region', self.DEFAULTS['region'])

    # -------- 工具：列表转 CSV 文本 --------

    @staticmethod
    def _list_to_csv(rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return ''
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    # -------- 同步执行 --------

    def sync_bcc(self) -> Dict[str, Any]:
        ak, sk = self.get_credentials()
        if not ak or not sk:
            return {'success': False, 'error': '未配置 BCE Access Key / Secret Key'}
        region = self.get_region()
        logger.info(f"开始同步 BCC 实例（region={region}）")
        result = _BCCApiClient(ak, sk, region).list_all_instances()
        if not result['success']:
            return result
        csv_text = self._list_to_csv(result['instances'])
        if not csv_text:
            return {'success': False, 'error': '接口返回 0 条实例'}
        write_result = self._writer.import_csv(
            csv_text, self.BCC_TABLE, 'BCC',
            collect_date=datetime.now().date()
        )
        if write_result['success']:
            logger.info(f"BCC 同步完成，写入 {write_result['count']} 条")
        return write_result

    def sync_cce(self, cluster_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        ak, sk = self.get_credentials()
        if not ak or not sk:
            return {'success': False, 'error': '未配置 BCE Access Key / Secret Key'}
        region = self.get_region()

        # 优先使用 CCE 官方 API 动态获取集群 ID
        if cluster_ids is None:
            try:
                from app.services.cce_api_service import CCEApiService
                cluster_ids = CCEApiService(self.db).get_cluster_ids()
                if cluster_ids:
                    logger.info(f"从 CCE API 获取到 {len(cluster_ids)} 个集群")
            except Exception as e:
                logger.warning(f"CCE API 获取集群列表失败: {e}")
                cluster_ids = []
        if not cluster_ids:
            return {'success': False, 'error': '无法获取集群 ID（CCE API 调用失败且未手动配置）'}

        results = {}
        total_count = 0
        has_error = False
        client = _CCEApiClient(ak, sk, region)
        for cid in cluster_ids:
            logger.info(f"同步 CCE 集群 {cid}")
            dl = client.list_cluster_nodes(cid)
            if not dl['success']:
                results[cid] = {'success': False, 'error': dl['error']}
                has_error = True
                continue
            csv_text = self._list_to_csv(dl['nodes'])
            if not csv_text:
                results[cid] = {'success': True, 'count': 0}
                continue
            wr = self._writer.import_csv(
                csv_text, self.CCE_TABLE, 'CCE',
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
