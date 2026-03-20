"""
告警数据库修正服务
从本地容器数据库查询正确的cluster_id，修正容器内数据库的告警记录
（bce_cce_nodes 表由宿主机下载脚本定期同步到容器数据库）
"""
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.models.alert import AlertRecord
from app.core.deps import SessionLocal
from app.core.database import get_db_connection


class DatabaseCorrectorService:
    """数据库修正服务：修正告警记录中的cluster_id"""

    def __init__(self):
        """初始化服务"""
        # 缓存查询结果
        self._cluster_cache: Dict[str, str] = {}

    def _get_local_db_connection(self):
        """获取本地容器数据库连接"""
        try:
            return get_db_connection()
        except Exception as e:
            logger.error(f"连接本地数据库失败: {e}")
            return None

    def test_host_connection(self) -> Dict[str, Any]:
        """
        测试本地数据库连接（保留接口兼容性）

        Returns:
            连接测试结果
        """
        try:
            conn = self._get_local_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM bce_cce_nodes LIMIT 1")
                    count = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()
                    return {
                        'success': True,
                        'message': f'本地数据库连接正常，bce_cce_nodes 共 {count} 条记录'
                    }
                except Exception as e:
                    conn.close()
                    return {
                        'success': False,
                        'error': f'数据库查询失败: {str(e)}',
                        'message': '本地数据库连接异常（bce_cce_nodes 表可能尚未同步）'
                    }
            else:
                return {
                    'success': False,
                    'error': '无法连接到本地数据库',
                    'message': '本地数据库连接失败',
                    'suggestions': [
                        '检查容器内 MySQL 服务是否启动',
                        '确认 bce_cce_nodes 表已由宿主机脚本同步'
                    ]
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '本地数据库连接测试异常'
            }

    def _query_correct_cluster_id(self, ip: str) -> Optional[str]:
        """
        通过IP查询正确的cluster_id

        Args:
            ip: 节点IP地址

        Returns:
            正确的cluster_id，如果查询失败返回None
        """
        # 检查缓存
        if ip in self._cluster_cache:
            return self._cluster_cache[ip]

        conn = self._get_local_db_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            # 查询bce_cce_nodes表，通过节点名称（IP）获取cluster_id
            cursor.execute(
                "SELECT cluster_id FROM bce_cce_nodes WHERE `节点名称`=%s LIMIT 1",
                (ip,)
            )
            result = cursor.fetchone()

            if result:
                correct_cluster_id = str(result[0])
                # 确保格式为 cce-xxxxxxxx
                if not correct_cluster_id.startswith("cce-"):
                    correct_cluster_id = f"cce-{correct_cluster_id}"

                # 缓存结果
                self._cluster_cache[ip] = correct_cluster_id
                logger.debug(f"查询到正确的cluster_id: IP={ip} -> cluster_id={correct_cluster_id}")
                return correct_cluster_id
            else:
                logger.debug(f"未找到IP对应的cluster_id: {ip}")
                return None

        except Exception as e:
            logger.error(f"查询cluster_id失败: IP={ip}, 错误={e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def detect_incorrect_records(self, db: Session = None) -> List[Dict[str, Any]]:
        """
        检测需要修正的告警记录
        
        Args:
            db: 数据库Session，如果为None则创建新的
            
        Returns:
            需要修正的记录列表
        """
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            incorrect_records = []
            
            # 查询所有有IP但cluster_id可能不正确的记录
            alerts = db.query(AlertRecord).filter(
                AlertRecord.ip.isnot(None),
                AlertRecord.ip != ''
            ).all()
            
            for alert in alerts:
                try:
                    # 查询正确的cluster_id
                    correct_cluster_id = self._query_correct_cluster_id(alert.ip)
                    
                    if correct_cluster_id and alert.cluster_id != correct_cluster_id:
                        incorrect_records.append({
                            'id': alert.id,
                            'ip': alert.ip,
                            'current_cluster_id': alert.cluster_id,
                            'correct_cluster_id': correct_cluster_id,
                            'alert_type': alert.alert_type,
                            'timestamp': alert.timestamp
                        })
                        
                except Exception as e:
                    logger.error(f"检测告警记录失败: ID={alert.id}, IP={alert.ip}, 错误={e}")
            
            logger.info(f"检测完成: 找到 {len(incorrect_records)} 条需要修正的记录")
            return incorrect_records
            
        except Exception as e:
            logger.error(f"检测不正确记录异常: {e}")
            return []
        finally:
            if should_close:
                db.close()
    
    def correct_single_record(self, alert_id: int, db: Session = None) -> Dict[str, Any]:
        """
        修正单条告警记录
        
        Args:
            alert_id: 告警记录ID
            db: 数据库Session，如果为None则创建新的
            
        Returns:
            修正结果
        """
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # 查询告警记录
            alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
            if not alert:
                return {'success': False, 'error': f'告警记录不存在: ID={alert_id}'}
            
            if not alert.ip:
                return {'success': False, 'error': f'告警记录缺少IP: ID={alert_id}'}
            
            # 查询正确的cluster_id
            correct_cluster_id = self._query_correct_cluster_id(alert.ip)
            if not correct_cluster_id:
                return {'success': False, 'error': f'无法查询到正确的cluster_id: IP={alert.ip}'}
            
            # 检查是否需要修正
            if alert.cluster_id == correct_cluster_id:
                return {'success': True, 'changed': False, 'message': 'cluster_id已正确，无需修正'}
            
            # 执行修正
            old_cluster_id = alert.cluster_id
            alert.cluster_id = correct_cluster_id
            alert.is_cce_cluster = correct_cluster_id.startswith('cce-')
            
            db.commit()
            
            logger.info(f"修正告警记录成功: ID={alert_id}, IP={alert.ip}, "
                       f"{old_cluster_id} -> {correct_cluster_id}")
            
            return {
                'success': True,
                'changed': True,
                'id': alert_id,
                'ip': alert.ip,
                'old_cluster_id': old_cluster_id,
                'new_cluster_id': correct_cluster_id
            }
            
        except Exception as e:
            logger.error(f"修正告警记录异常: ID={alert_id}, 错误={e}")
            if db:
                db.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            if should_close:
                db.close()
    
    def correct_batch_records(self, alert_ids: List[int] = None, db: Session = None) -> Dict[str, Any]:
        """
        批量修正告警记录
        
        Args:
            alert_ids: 告警记录ID列表，如果为None则修正所有需要修正的记录
            db: 数据库Session，如果为None则创建新的
            
        Returns:
            批量修正结果
        """
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # 如果没有指定ID列表，检测所有需要修正的记录
            if alert_ids is None:
                incorrect_records = self.detect_incorrect_records(db)
                alert_ids = [record['id'] for record in incorrect_records]
            
            if not alert_ids:
                return {
                    'success': True,
                    'total': 0,
                    'corrected': 0,
                    'skipped': 0,
                    'failed': 0,
                    'message': '没有需要修正的记录'
                }
            
            # 批量修正
            results = {
                'success': True,
                'total': len(alert_ids),
                'corrected': 0,
                'skipped': 0,
                'failed': 0,
                'details': []
            }
            
            for alert_id in alert_ids:
                try:
                    result = self.correct_single_record(alert_id, db)
                    
                    if result['success']:
                        if result.get('changed', False):
                            results['corrected'] += 1
                        else:
                            results['skipped'] += 1
                    else:
                        results['failed'] += 1
                    
                    results['details'].append(result)
                    
                except Exception as e:
                    logger.error(f"批量修正单条记录失败: ID={alert_id}, 错误={e}")
                    results['failed'] += 1
                    results['details'].append({
                        'success': False,
                        'id': alert_id,
                        'error': str(e)
                    })
            
            logger.info(f"批量修正完成: 总数={results['total']}, "
                       f"成功={results['corrected']}, "
                       f"跳过={results['skipped']}, "
                       f"失败={results['failed']}")
            
            return results
            
        except Exception as e:
            logger.error(f"批量修正异常: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if should_close:
                db.close()


# 全局单例
_database_corrector: Optional[DatabaseCorrectorService] = None


def get_database_corrector() -> DatabaseCorrectorService:
    """获取数据库修正服务单例"""
    global _database_corrector
    if _database_corrector is None:
        _database_corrector = DatabaseCorrectorService()
    return _database_corrector