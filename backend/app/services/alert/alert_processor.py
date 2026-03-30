"""
告警处理服务
整合告警解析、手册匹配、诊断API调用、AI解读和Webhook通知
"""
import logging
import asyncio
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.alert import AlertRecord, DiagnosisResult
from app.services.alert.parser import AlertParserService
from app.services.alert.manual_matcher import ManualMatchService
from app.services.alert.diagnosis_api import DiagnosisAPIService
from app.services.alert.ai_interpreter import AIInterpreterService
from app.services.alert.webhook_notifier import WebhookNotifier
from app.core.config_alert import settings

logger = logging.getLogger(__name__)


class AlertProcessor:
    """告警处理器 - 完整的告警处理流程"""
    
    def __init__(self):
        """不再持有db，按需创建Session"""
        self.parser = AlertParserService()
        self.manual_matcher = None  # 按需初始化
        self.diagnosis_api = DiagnosisAPIService()
        self.ai_interpreter = AIInterpreterService()
        self.webhook_notifier = None  # 按需初始化
        
        # Redis客户端（用于跨worker去重）
        self.redis_client = None
        try:
            from app.core.redis_client import get_redis_client
            redis_wrapper = get_redis_client()
            self.redis_client = redis_wrapper.client
            logger.info("✅ AlertProcessor已连接Redis")
        except Exception as e:
            logger.warning(f"⚠️ 无法连接Redis: {str(e)}")
        
        # Lua脚本：安全释放锁（只删除token匹配的锁）
        self.unlock_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        # 预加载Lua脚本SHA（提升性能）
        self.unlock_sha = None
        if self.redis_client:
            try:
                self.unlock_sha = self.redis_client.script_load(self.unlock_script)
                logger.debug("✅ Lua解锁脚本预加载成功")
            except Exception as e:
                logger.warning(f"⚠️ Lua脚本预加载失败: {e}")
    def _get_db_session(self) -> Session:
        """按需创建数据库session"""
        from app.core.deps import SessionLocal
        return SessionLocal()
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        递归转换对象，使其可以被JSON序列化
        将datetime对象转换为ISO格式字符串
        
        Args:
            obj: 任意对象
            
        Returns:
            JSON可序列化的对象
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj

    def _parse_file_to_alert_records(self, file_path: str) -> Optional[list]:
        """
        解析文件并转换为告警记录列表。

        当前解析器返回 ParsedAlert，处理器统一在这里转成旧流程可消费的字典列表。
        """
        parsed_alert = self.parser.parse_file(file_path)
        if not parsed_alert:
            return None

        alerts_data = AlertParserService.convert_to_alert_records(parsed_alert)
        if not alerts_data:
            return None

        return alerts_data
    
    async def process_alert_file(self, file_path: str) -> bool:
        """
        处理告警文件（双重锁保护：文件锁 + 节点锁）
        
        流程：
        1. 从文件名提取节点信息（cluster_id + ip）
        2. 获取节点级Redis锁（防止同节点不同文件并发）
        3. 创建独立Session
        4. 解析告警文件
        5. 存储告警记录 + 匹配手册 + 发送通知
        6. 创建/复用诊断任务（如果需要）
        7. 释放节点锁 + 关闭Session
        
        Args:
            file_path: 告警文件路径
            
        Returns:
            是否处理成功
        """
        db = None
        lock_token = None
        redis_key = None
        
        try:
            # 1. 从文件名提取节点信息
            node_info = AlertParserService.extract_node_info_from_filename(file_path)
            if not node_info:
                logger.warning(f"无法从文件名提取节点信息，跳过: {file_path}")
                return False
            
            cluster_id = node_info.get('cluster_id')
            ip = node_info.get('ip')
            is_cce = cluster_id is not None and cluster_id.startswith('cce-')
            
            # 2. 如果是CCE集群，获取节点级Redis锁（关键：防止同节点不同文件并发）
            if is_cce and cluster_id and ip and self.redis_client:
                import uuid
                redis_key = f"alert:diagnosis_lock:{cluster_id}:{ip}"
                lock_token = uuid.uuid4().hex
                
                # SETNX原子获取锁，TTL=900秒（15分钟）
                acquired = self.redis_client.set(redis_key, lock_token, nx=True, ex=900)
                if not acquired:
                    # 锁已被占用 → 查询已有任务并复用
                    logger.info(f"🔒 节点诊断锁被占用，查询复用: {cluster_id}:{ip}")
                    temp_db = self._get_db_session()
                    try:
                        existing = await self._find_existing_diagnosis(cluster_id, ip, temp_db)
                        if existing:
                            # 解析文件 + 存储告警 + 复用诊断
                            db = self._get_db_session()
                            
                            # 按需初始化依赖
                            if self.manual_matcher is None:
                                self.manual_matcher = ManualMatchService(db)
                            if self.webhook_notifier is None:
                                self.webhook_notifier = WebhookNotifier(db, redis_client=self.redis_client)
                            
                            # 解析文件
                            alerts_data = self._parse_file_to_alert_records(file_path)
                            if not alerts_data:
                                logger.warning(f"文件解析失败或无数据: {file_path}")
                                return False
                            
                            # 存储告警
                            alert_diagnosis_list = []
                            for alert_data in alerts_data:
                                try:
                                    alert, diagnosis = await self._process_alert_basic(alert_data, db)
                                    if alert and diagnosis:
                                        alert_diagnosis_list.append((alert, diagnosis))
                                except Exception as e:
                                    logger.error(f"处理单条告警失败: {str(e)}", exc_info=True)
                            
                            # 复用诊断
                            if alert_diagnosis_list:
                                await self._reuse_diagnosis(existing, alert_diagnosis_list, db)
                                db.commit()
                                logger.info(f"🔄 复用诊断任务: {cluster_id}:{ip} → {existing.api_task_id}")
                            
                            return len(alert_diagnosis_list) > 0
                        else:
                            # 查不到已有任务，说明锁刚释放，跳过避免竞争
                            logger.info(f"⚠️ 节点锁占用但无诊断任务，跳过: {cluster_id}:{ip}")
                            return False
                    finally:
                        temp_db.close()
                        if db:
                            db.close()
                            db = None
                
                logger.info(f"🔓 获取节点锁成功: {cluster_id}:{ip}")
            else:
                logger.info(f"📋 物理机节点，跳过诊断: ip={ip}")
            
            # 3. 创建独立Session处理告警（现在安全了，因为持有节点锁）
            db = self._get_db_session()
            
            # 按需初始化依赖
            if self.manual_matcher is None:
                self.manual_matcher = ManualMatchService(db)
            if self.webhook_notifier is None:
                self.webhook_notifier = WebhookNotifier(db)
            
            # 4. 解析告警文件
            alerts_data = self._parse_file_to_alert_records(file_path)
            if not alerts_data:
                logger.warning(f"文件解析失败或无数据: {file_path}")
                return False
            
            # 5. 处理每条告警（存储、匹配手册、发送通知）
            success_count = 0
            alert_diagnosis_list = []
            
            for alert_data in alerts_data:
                try:
                    alert, diagnosis = await self._process_alert_basic(alert_data, db)
                    if alert and diagnosis:
                        success_count += 1
                        alert_diagnosis_list.append((alert, diagnosis))
                except Exception as e:
                    logger.error(f"处理单条告警失败: {str(e)}", exc_info=True)
            
            logger.info(f"文件处理完成: {file_path}, 成功 {success_count}/{len(alerts_data)}")
            
            # 6. 创建诊断任务（仅CCE集群，现在持有锁，安全）
            if is_cce and cluster_id and ip and alert_diagnosis_list:
                # 双重检查DB（防止锁过期后的极端情况）
                existing = await self._find_existing_diagnosis(cluster_id, ip, db)
                if existing:
                    # 复用已有诊断
                    await self._reuse_diagnosis(existing, alert_diagnosis_list, db)
                    db.commit()
                    logger.info(f"🔄 复用诊断任务（双重检查）: {cluster_id}:{ip} → {existing.api_task_id}")
                else:
                    # 创建新诊断任务
                    await self._create_single_diagnosis(cluster_id, ip, alert_diagnosis_list, db)
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"处理告警文件异常: {file_path}, {str(e)}", exc_info=True)
            if db:
                db.rollback()
            return False
        finally:
            # 7. 安全释放节点锁（Lua脚本保证原子性）
            if lock_token and redis_key and self.redis_client:
                try:
                    if self.unlock_sha:
                        self.redis_client.evalsha(self.unlock_sha, 1, redis_key, lock_token)
                    else:
                        self.redis_client.eval(self.unlock_script, 1, redis_key, lock_token)
                    logger.debug(f"🔓 释放节点锁: {redis_key}")
                except Exception as e:
                    logger.warning(f"⚠️ 释放节点锁异常: {e}")
            
            if db:
                try:
                    db.close()
                    logger.debug(f"已关闭数据库连接: {file_path}")
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")
    

    
    async def process_single_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        处理单条告警（用于手动触发或单个告警处理）
        
        Args:
            alert_data: 告警数据
            
        Returns:
            是否处理成功
        """
        print("=== NEW CODE VERSION 2026-03-11 ===")
        db = None
        try:
            logger.info(f"🚀 开始处理单条告警: alert_type={alert_data.get('alert_type')}, ip={alert_data.get('ip')}")
            
            # 创建独立Session
            db = self._get_db_session()
            logger.info(f"✅ 数据库Session创建成功")
            
            # 按需初始化依赖
            logger.info(f"🔧 初始化依赖服务...")
            if self.manual_matcher is None:
                logger.info(f"📋 初始化ManualMatchService...")
                self.manual_matcher = ManualMatchService(db)
                logger.info(f"✅ ManualMatchService初始化完成")
            
            if self.webhook_notifier is None:
                logger.info(f"📢 初始化WebhookNotifier...")
                self.webhook_notifier = WebhookNotifier(db)
                logger.info(f"✅ WebhookNotifier初始化完成")
            
            # 处理基础流程（手册匹配、AI解读、通知）
            logger.info(f"🔄 调用基础流程处理...")
            print(f"DEBUG: 调用 _process_alert_basic")
            alert, diagnosis = await self._process_alert_basic(alert_data, db)
            
            print(f"DEBUG: _process_alert_basic 返回结果: alert={alert}, diagnosis={diagnosis}")
            logger.info(f"🔄 基础流程处理结果: alert={'存在' if alert else 'None'}, diagnosis={'存在' if diagnosis else 'None'}")
            
            if not alert or not diagnosis:
                print(f"DEBUG: 基础流程处理失败: alert={alert}, diagnosis={diagnosis}")
                logger.error(f"基础流程处理失败: alert={alert}, diagnosis={diagnosis}")
                return False
            
            # 判断是否为CCE集群节点
            is_cce = alert.is_cce_cluster
            logger.info(f"🏷️ 节点类型判断: is_cce={is_cce}, cluster_id={alert.cluster_id}, ip={alert.ip}")
            
            if is_cce and alert.cluster_id and alert.ip:
                # 检查15分钟窗口（正常流程）
                existing_diagnosis = await self._find_existing_diagnosis(alert.cluster_id, alert.ip, db)
                
                if existing_diagnosis:
                    # 复用已有诊断结果
                    await self._reuse_diagnosis(existing_diagnosis, [(alert, diagnosis)], db)
                    db.commit()
                    logger.info(f"🔄 复用诊断: {alert.cluster_id}:{alert.ip} → {existing_diagnosis.api_task_id}")
                else:
                    # 尝试创建新诊断任务（允许失败）
                    try:
                        await self._create_single_diagnosis(alert.cluster_id, alert.ip, [(alert, diagnosis)], db)
                        logger.info(f"✅ 诊断任务创建成功: {alert.cluster_id}:{alert.ip}")
                    except Exception as diag_error:
                        # 诊断API失败不影响整体流程
                        logger.warning(f"⚠️ 诊断API失败但基础流程已完成: {alert.cluster_id}:{alert.ip}, 错误: {str(diag_error)}")
                        # 更新诊断状态为失败
                        db.refresh(diagnosis)
                        diagnosis.api_status = 'failed'
                        diagnosis.api_diagnosis = {'error': str(diag_error), 'timestamp': datetime.now().isoformat()}
                        db.commit()
            else:
                logger.info(f"📋 物理机节点跳过诊断: IP={alert.ip}, 告警类型={alert.alert_type}")
            
            # 基础流程（手册匹配、AI解读、通知）已完成，返回成功
            logger.info(f"✅ 告警处理完成: ID={alert.id}, 类型={alert.alert_type}, CCE诊断={'成功' if diagnosis.api_task_id else '跳过/失败'}")
            return True
            
        except Exception as e:
            logger.error(f"处理单条告警异常: alert_type={alert_data.get('alert_type')}, error={str(e)}", exc_info=True)
            if db:
                db.rollback()
            return False
        finally:
            if db:
                try:
                    db.close()
                    logger.info(f"🔒 数据库连接已关闭")
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")
    
    async def _process_alert_basic(self, alert_data: Dict[str, Any], db: Session) -> tuple:
        """
        处理单条告警的基础流程（不包含诊断API）
        
        Args:
            alert_data: 告警数据
            db: 数据库Session
            
        Returns:
            (告警记录, 诊断结果) 元组
        """
        print(f"DEBUG: 进入 _process_alert_basic")
        logger.info(f"🚀 开始基础流程处理: alert_type={alert_data.get('alert_type')}, ip={alert_data.get('ip')}")
        
        try:
            print(f"DEBUG: 步骤1 - 检查重复告警")
            # 1. 检查是否已存在相同告警（防止重复）
            # 注意：重新诊断场景下，会找到已存在的告警但诊断结果为空
            logger.info(f"🔍 检查重复告警: alert_type={alert_data.get('alert_type')}, ip={alert_data.get('ip')}")
            existing_alert = db.query(AlertRecord).filter(
                AlertRecord.alert_type == alert_data.get('alert_type', ''),
                AlertRecord.ip == alert_data.get('ip'),
                AlertRecord.timestamp == alert_data.get('timestamp', datetime.now())
            ).first()
            
            if existing_alert:
                print(f"DEBUG: 找到已存在告警: {existing_alert.id}")
                logger.info(f"告警已存在: ID={existing_alert.id}, 类型={existing_alert.alert_type}, IP={existing_alert.ip}")
                
                # 强制从数据库重新查询最新数据（避免使用缓存的旧对象）
                print(f"DEBUG: 强制从数据库重新查询最新告警数据")
                old_cluster_id = existing_alert.cluster_id
                logger.warning(f"🔍 [BUG-021] 重新查询前 cluster_id={old_cluster_id}")
                
                # 关键修复：使用主键重新查询，确保获取最新数据
                alert = db.query(AlertRecord).filter(AlertRecord.id == existing_alert.id).first()
                if not alert:
                    logger.error(f"❌ 重新查询告警失败: alert_id={existing_alert.id}")
                    alert = existing_alert  # 降级使用原对象
                else:
                    new_cluster_id = alert.cluster_id
                    logger.warning(f"✅ [BUG-021] 重新查询后 cluster_id={new_cluster_id}")
                    if old_cluster_id != new_cluster_id:
                        logger.warning(f"⚠️ [BUG-021] 检测到cluster_id变化: {old_cluster_id} → {new_cluster_id}")
                    else:
                        logger.warning(f"✓ [BUG-021] cluster_id未变化: {new_cluster_id}")
                
                # 检查诊断结果
                diagnosis = db.query(DiagnosisResult).filter(
                    DiagnosisResult.alert_id == alert.id
                ).first()
                print(f"DEBUG: 已存在告警的诊断结果: {diagnosis}")
                
                if diagnosis:
                    # 诊断结果存在，直接返回（正常的重复告警）
                    print(f"DEBUG: 诊断结果存在，直接返回")
                    logger.info(f"返回已存在告警: alert_id={alert.id}, diagnosis_id={diagnosis.id}")
                    return alert, diagnosis
                else:
                    # 诊断结果不存在，这是重新诊断场景，继续处理
                    print(f"DEBUG: 诊断结果为空（重新诊断场景），使用重新查询的告警继续处理")
                    logger.info(f"重新诊断场景: alert_id={alert.id}，cluster_id={alert.cluster_id}，继续处理")
                    # 注意：不要在这里return，要继续执行后续的手册匹配等流程
            else:
                print(f"DEBUG: 步骤2 - 创建新告警记录")
                # 2. 创建新的告警记录
                logger.info(f"📝 创建新告警记录: alert_type={alert_data.get('alert_type')}")
                alert = self._create_new_alert_record(alert_data, db)
                print(f"DEBUG: 新告警记录创建成功: alert_id={alert.id}")
                logger.info(f"✅ 告警记录创建成功: alert_id={alert.id}")
            
            print(f"DEBUG: 步骤3 - 匹配故障手册")
            # 3. 匹配故障手册
            logger.info(f"📋 开始匹配故障手册: alert_id={alert.id}")
            fault_items = None
            raw_data = alert_data.get('raw_data')
            if isinstance(raw_data, dict):
                candidate_fault_items = raw_data.get('error_types')
                if isinstance(candidate_fault_items, list) and candidate_fault_items:
                    fault_items = candidate_fault_items

            diagnosis = await self._match_manual(alert, db, fault_items=fault_items)
            print(f"DEBUG: 手册匹配结果: diagnosis={diagnosis}")
            logger.info(f"📋 手册匹配完成: diagnosis={'成功' if diagnosis else '失败'}")
            
            if not diagnosis:
                print(f"DEBUG: 手册匹配返回None，尝试创建基础诊断结果")
                logger.error(f"❌ 手册匹配返回None: alert_id={alert.id}")
                # 手册匹配失败不应该导致整个流程失败，创建一个基础诊断结果
                try:
                    print(f"DEBUG: 开始创建基础诊断结果")
                    logger.warning(f"⚠️ 手册匹配失败，创建基础诊断结果: alert_id={alert.id}")
                    diagnosis = DiagnosisResult(
                        alert_id=alert.id,
                        manual_matched=False,
                        source='none'
                    )
                    db.add(diagnosis)
                    print(f"DEBUG: 诊断结果已添加到session，准备commit")
                    db.commit()
                    print(f"DEBUG: commit成功，准备refresh")
                    db.refresh(diagnosis)
                    print(f"DEBUG: 基础诊断结果创建成功: diagnosis_id={diagnosis.id}")
                    logger.warning(f"⚠️ 基础诊断结果创建成功: diagnosis_id={diagnosis.id}, alert_id={alert.id}")
                except Exception as fallback_error:
                    print(f"DEBUG: 创建基础诊断结果失败: {str(fallback_error)}")
                    logger.error(f"❌ 创建基础诊断结果也失败: alert_id={alert.id}, error={str(fallback_error)}", exc_info=True)
                    return alert, None
            
            print(f"DEBUG: 步骤4 - AI解读")
            # 4. 初始AI解读（不包含诊断结果）- 允许失败
            logger.info(f"🤖 开始AI解读: alert_id={alert.id}")
            try:
                await self._ai_interpret(alert, diagnosis, api_result=None, db=db)
                print(f"DEBUG: AI解读成功")
                logger.info(f"✅ AI解读完成: alert_id={alert.id}")
            except Exception as ai_error:
                print(f"DEBUG: AI解读失败: {str(ai_error)}")
                logger.warning(f"⚠️ AI解读失败但继续流程: 告警ID={alert.id}, 错误: {str(ai_error)}")
            
            print(f"DEBUG: 步骤5 - Webhook通知")
            # 5. 发送初始Webhook通知 - 允许失败
            logger.info(f"📢 开始Webhook通知: alert_id={alert.id}")
            try:
                await self.webhook_notifier.send_alert_notification(alert, diagnosis)
                print(f"DEBUG: Webhook通知成功")
                logger.info(f"✅ Webhook通知完成: alert_id={alert.id}")
            except Exception as webhook_error:
                print(f"DEBUG: Webhook通知失败: {str(webhook_error)}")
                logger.warning(f"⚠️ Webhook通知失败但继续流程: 告警ID={alert.id}, 错误: {str(webhook_error)}")
            
            print(f"DEBUG: 基础流程处理成功，返回结果")
            logger.info(f"🎉 基础流程处理成功: alert_id={alert.id}, diagnosis_id={diagnosis.id}")
            return alert, diagnosis
            
        except Exception as e:
            print(f"DEBUG: 基础流程处理异常: {str(e)}")
            logger.error(f"处理单条告警基础流程异常: alert_type={alert_data.get('alert_type')}, error={str(e)}", exc_info=True)
            db.rollback()
            return None, None
    
    def _create_new_alert_record(self, alert_data: Dict[str, Any], db: Session) -> AlertRecord:
        """创建新的告警记录"""
        # 将raw_data中的datetime对象转换为ISO格式字符串，以便JSON序列化
        raw_data_serializable = self._make_json_serializable(alert_data)
        
        # 确定告警来源
        source = alert_data.get('source', 'file')
        file_path = alert_data.get('file_path', '')
        
        # 获取IP和cluster_id
        ip = alert_data.get('ip')
        cluster_id = alert_data.get('cluster_id')
        
        # 如果有IP但没有cluster_id，尝试自动查询修正
        if ip and not cluster_id:
            try:
                from app.services.alert.database_corrector import get_database_corrector
                corrector = get_database_corrector()
                correct_cluster_id = corrector._query_correct_cluster_id(ip)
                if correct_cluster_id:
                    cluster_id = correct_cluster_id
                    logger.info(f"自动修正cluster_id: IP={ip} -> cluster_id={cluster_id}")
            except Exception as e:
                logger.warning(f"自动修正cluster_id失败: IP={ip}, 错误={e}")
        
        alert = AlertRecord(
            alert_type=alert_data.get('alert_type', ''),
            component=alert_data.get('component'),
            severity=alert_data.get('severity', 'WARN'),
            ip=ip,
            cluster_id=cluster_id,
            instance_id=alert_data.get('instance_id'),
            hostname=alert_data.get('hostname'),
            is_cce_cluster=cluster_id.startswith('cce-') if cluster_id else False,
            timestamp=alert_data.get('timestamp', datetime.now()),
            file_path=file_path,
            source=source,
            raw_data=raw_data_serializable
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"创建告警记录: ID={alert.id}, 类型={alert.alert_type}, 集群={alert.cluster_id}, IP={alert.ip}")
        return alert
    
    
    async def _create_single_diagnosis(self, cluster_id: str, ip: str, alert_diagnosis_list: list, db: Session):
        """
        创建单个节点的诊断任务（简化版：无Redis锁，文件级别已去重）
        
        Args:
            cluster_id: 集群ID
            ip: 节点IP
            alert_diagnosis_list: [(alert, diagnosis), ...] 列表
            db: 数据库Session
        """
        try:
            first_alert = alert_diagnosis_list[0][0]
            
            # 创建诊断任务
            logger.info(f"🔍 开始创建诊断任务: {cluster_id}:{ip}")
            logger.info(f"📋 调用诊断API参数: cluster_id={cluster_id}, ip={ip}")
            task_id = await self.diagnosis_api.create_node_diagnosis(cluster_id, ip)
            
            if task_id:
                # 更新所有告警的诊断结果
                for alert, diagnosis in alert_diagnosis_list:
                    db.refresh(diagnosis)
                    diagnosis.api_task_id = task_id
                    diagnosis.api_status = 'processing'
                
                db.commit()
                logger.warning(f"✅ [诊断任务] 创建成功: {cluster_id}:{ip} → {task_id}")
                
                # 启动后台线程等待诊断完成
                diagnosis_ids = [diagnosis.id for _, diagnosis in alert_diagnosis_list]
                logger.warning(f"🚀 [后台线程] 准备启动: task_id={task_id}, diagnosis_ids={diagnosis_ids}")
                
                import threading
                thread = threading.Thread(
                    target=self._wait_diagnosis_in_thread,
                    args=(cluster_id, task_id, diagnosis_ids),
                    daemon=True,
                    name=f"DiagnosisWaiter-{task_id}"
                )
                thread.start()
                logger.warning(f"✅ [后台线程] 已启动: thread_name={thread.name}, is_alive={thread.is_alive()}")
            else:
                # 创建失败，记录错误但不抛出异常
                error_msg = f"CCE诊断API调用失败: {cluster_id}:{ip}"
                logger.warning(f"⚠️ {error_msg}")
                
                for alert, diagnosis in alert_diagnosis_list:
                    db.refresh(diagnosis)
                    diagnosis.api_status = 'failed'
                    diagnosis.api_diagnosis = {
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat(),
                        'reason': 'CCE API调用失败，可能是节点不存在或网络问题'
                    }
                db.commit()
                
                # 不抛出异常，让基础流程继续
                logger.info(f"📋 诊断API失败但基础流程已完成: {cluster_id}:{ip}")
                
        except Exception as e:
            # 记录错误但不抛出异常，让基础流程继续
            error_msg = f"创建诊断任务异常: {cluster_id}:{ip}, {str(e)}"
            logger.warning(f"⚠️ {error_msg}")
            
            try:
                for alert, diagnosis in alert_diagnosis_list:
                    db.refresh(diagnosis)
                    diagnosis.api_status = 'failed'
                    diagnosis.api_diagnosis = {
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat(),
                        'exception': str(e)
                    }
                db.commit()
            except Exception as db_error:
                logger.error(f"❌ 更新诊断状态失败: {str(db_error)}")
                db.rollback()
    
    async def _find_existing_diagnosis(self, cluster_id: str, ip: str, db: Session) -> Optional[DiagnosisResult]:
        """查询15分钟内已有的诊断任务"""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(minutes=15)
        
        return db.query(DiagnosisResult).join(
            AlertRecord, DiagnosisResult.alert_id == AlertRecord.id
        ).filter(
            AlertRecord.cluster_id == cluster_id,
            AlertRecord.ip == ip,
            DiagnosisResult.api_task_id.isnot(None),
            DiagnosisResult.created_at >= cutoff
        ).order_by(DiagnosisResult.created_at.desc()).first()
    
    async def _reuse_diagnosis(self, existing: DiagnosisResult, alert_diagnosis_list: list, db: Session):
        """复用已有诊断结果（只复用API结果，保留手册匹配）"""
        for alert, diagnosis in alert_diagnosis_list:
            if diagnosis.id != existing.id:
                # 只复用API结果，保留手册匹配
                diagnosis.api_task_id = existing.api_task_id
                diagnosis.api_status = existing.api_status
                diagnosis.api_diagnosis = existing.api_diagnosis
                diagnosis.api_items_count = existing.api_items_count
                diagnosis.api_error_count = existing.api_error_count
                diagnosis.api_warning_count = existing.api_warning_count
                diagnosis.api_abnormal_count = existing.api_abnormal_count
        logger.info(f"🔄 复用诊断: {len(alert_diagnosis_list)} 条告警 → task_id={existing.api_task_id}")
    
    async def _match_manual(self, alert: AlertRecord, db: Session, fault_items: list = None) -> Optional[DiagnosisResult]:
        """
        匹配故障手册（支持多故障类型）
        
        Args:
            alert: 告警记录
            db: 数据库Session
            fault_items: 故障类型列表（可选，用于多故障类型场景）
            
        Returns:
            诊断结果
        """
        logger.info(f"🔍 开始匹配手册: 告警ID={alert.id}, 类型={alert.alert_type}, 组件={alert.component}")
        
        try:
            # 检查manual_matcher是否已初始化
            if self.manual_matcher is None:
                logger.error(f"❌ manual_matcher未初始化: alert_id={alert.id}")
                raise Exception("manual_matcher未初始化")
            
            # 多故障类型匹配
            if fault_items and len(fault_items) > 0:
                logger.info(f"📋 多故障类型匹配: 共 {len(fault_items)} 个故障项")
                match_result = self.manual_matcher.match_multiple(fault_items)
            else:
                logger.info(f"📋 单故障类型匹配: alert_type={alert.alert_type}, component={alert.component}")
                manual = self.manual_matcher.match(alert.alert_type, alert.component)
                match_result = {
                    'matched': manual is not None,
                    'name_zh': manual.get('name_zh') if manual else None,
                    'danger_level': manual.get('danger_level') if manual else None,
                    'solution': manual.get('solution') if manual else None,
                    'impact': manual.get('impact') if manual else None,
                    'recovery': manual.get('recovery') if manual else None,
                    'customer_aware': manual.get('customer_aware') if manual else None,
                    'fault_items': None
                }
            
            logger.info(f"📋 手册匹配结果: matched={match_result.get('matched', False)}")
            
            # 创建诊断结果
            logger.info(f"💾 创建诊断结果: alert_id={alert.id}")
            diagnosis = DiagnosisResult(
                alert_id=alert.id,
                manual_matched=match_result.get('matched', False),
                manual_name_zh=match_result.get('name_zh'),
                danger_level=match_result.get('danger_level'),
                manual_solution=match_result.get('solution'),
                manual_impact=match_result.get('impact'),
                customer_aware=match_result.get('customer_aware'),
                fault_items=match_result.get('fault_items'),  # 多故障类型详情
                source='manual' if match_result.get('matched') else 'none'
            )
            
            logger.info(f"💾 保存诊断结果到数据库: alert_id={alert.id}")
            db.add(diagnosis)
            db.commit()
            db.refresh(diagnosis)
            
            logger.info(f"✅ 诊断结果创建成功: diagnosis_id={diagnosis.id}, alert_id={alert.id}")
            
            if match_result.get('matched'):
                logger.info(f"✅ 手册匹配成功: 告警ID={alert.id}, 类型={alert.alert_type}")
                if match_result.get('fault_items'):
                    logger.info(f"   匹配到 {len(match_result['fault_items'])} 个故障项")
            else:
                logger.warning(f"⚠️ 未找到匹配的手册: 告警ID={alert.id}, 类型={alert.alert_type}")
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"匹配手册异常: alert_id={alert.id}, error={str(e)}", exc_info=True)
            # 即使匹配失败，也要创建基础诊断结果
            try:
                logger.warning(f"⚠️ 尝试创建基础诊断结果: alert_id={alert.id}")
                diagnosis = DiagnosisResult(
                    alert_id=alert.id,
                    manual_matched=False,
                    source='none'
                )
                db.add(diagnosis)
                db.commit()
                db.refresh(diagnosis)
                logger.warning(f"⚠️ 手册匹配异常，创建基础诊断结果成功: diagnosis_id={diagnosis.id}, alert_id={alert.id}")
                return diagnosis
            except Exception as db_error:
                logger.error(f"创建基础诊断结果失败: alert_id={alert.id}, error={str(db_error)}", exc_info=True)
                db.rollback()
                return None
    
    async def _ai_interpret(
        self, 
        alert: AlertRecord, 
        diagnosis: DiagnosisResult,
        api_result: Optional[Dict[str, Any]] = None,
        db: Session = None
    ):
        """
        AI解读诊断结果
        
        Args:
            alert: 告警记录
            diagnosis: 诊断结果
            api_result: API诊断结果
            db: 数据库Session（可选）
        """
        try:
            # 准备告警信息
            alert_info = {
                'alert_type': alert.alert_type,
                'component': alert.component,
                'severity': alert.severity,
                'ip': alert.ip,
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') if alert.timestamp else 'N/A'
            }
            
            # 准备手册匹配结果
            manual_result = None
            if diagnosis.manual_matched:
                manual_result = {
                    'matched': True,
                    'name_zh': diagnosis.manual_name_zh,
                    'danger_level': diagnosis.danger_level,
                    'solution': diagnosis.manual_solution
                }
            
            # 调用AI解读
            logger.info(f"开始AI解读: 告警ID={alert.id}")
            ai_interpretation = await self.ai_interpreter.interpret_diagnosis(
                alert_info=alert_info,
                manual_result=manual_result,
                api_result=api_result
            )
            
            if ai_interpretation:
                # 保存AI解读结果
                diagnosis.ai_interpretation = ai_interpretation
                if db:
                    db.commit()
                logger.info(f"AI解读成功: 告警ID={alert.id}")
            else:
                logger.warning(f"AI解读失败: 告警ID={alert.id}")
                
        except Exception as e:
            logger.error(f"AI解读异常: {str(e)}", exc_info=True)
    
    async def _wait_and_update_diagnosis(self, cluster_id: str, task_id: str, diagnosis_ids: list, db=None):
        """
        等待诊断完成并更新结果（后台任务）
        
        Args:
            cluster_id: 集群ID
            task_id: 任务ID
            diagnosis_ids: 诊断结果ID列表（同一个节点可能有多个告警）
            db: 数据库session（如果为None则使用self.db）
        """
        # 使用传入的db或self.db
        db_session = db if db is not None else self.db
        
        try:
            logger.warning(f"⏳ [等待诊断] 开始: task_id={task_id}, diagnosis_ids={diagnosis_ids}")
            
            # 等待诊断完成（增加等待时间到15分钟）
            logger.warning(f"📞 [等待诊断] 调用API轮询: cluster_id={cluster_id}, task_id={task_id}")
            report = await self.diagnosis_api.wait_for_diagnosis_complete(
                cluster_id, 
                task_id,
                max_wait_time=900,  # 15分钟
                poll_interval=15     # 每15秒轮询一次
            )
            
            if not report:
                logger.warning(f"⏰ [等待诊断] 超时或失败: task_id={task_id}")
                # 更新所有诊断记录的状态为失败
                for diagnosis_id in diagnosis_ids:
                    diagnosis = db_session.query(DiagnosisResult).filter(
                        DiagnosisResult.id == diagnosis_id
                    ).first()
                    if diagnosis:
                        diagnosis.api_status = 'timeout'
                        db_session.commit()
                        logger.warning(f"⏰ [等待诊断] 已更新超时状态: diagnosis_id={diagnosis_id}")
                return
            
            logger.warning(f"✅ [等待诊断] API返回成功: task_id={task_id}, report_size={len(str(report))}")
            
            # 解析诊断报告
            parsed_result = self.diagnosis_api.parse_diagnosis_report(report)
            logger.warning(f"📊 [等待诊断] 报告解析完成: items={len(parsed_result.get('all_items', []))}")
            
            # 更新所有诊断记录（共享同一个诊断结果）
            for diagnosis_id in diagnosis_ids:
                # 重新查询诊断记录（使用独立查询，不依赖缓存）
                diagnosis = db_session.query(DiagnosisResult).filter(
                    DiagnosisResult.id == diagnosis_id
                ).first()
                
                if not diagnosis:
                    logger.warning(f"⚠️ [等待诊断] 诊断记录不存在: diagnosis_id={diagnosis_id}")
                    continue
                
                # 🔒 检查是否已发送通知（防止重复发送）
                # 注意：即使已发送通知，也需要更新诊断结果，否则前端看不到结果
                already_notified = diagnosis.notified
                if already_notified:
                    logger.warning(f"⏭️ [等待诊断] 已发送过通知，仍更新诊断结果: diagnosis_id={diagnosis.id}, alert_id={diagnosis.alert_id}")
                
                # 更新诊断结果
                diagnosis.api_status = parsed_result.get('task_result', 'unknown')
                diagnosis.api_diagnosis = parsed_result  # 保存完整的诊断报告
                diagnosis.api_items_count = len(parsed_result.get('all_items', []))
                diagnosis.api_error_count = len(parsed_result.get('error_items', []))
                diagnosis.api_warning_count = len(parsed_result.get('warning_items', []))
                diagnosis.api_abnormal_count = len(parsed_result.get('abnormal_items', []))
                
                logger.warning(f"💾 [等待诊断] 准备更新: diagnosis_id={diagnosis.id}, alert_id={diagnosis.alert_id}, "
                           f"总项={diagnosis.api_items_count}, 错误={diagnosis.api_error_count}, 警告={diagnosis.api_warning_count}")
                
                # 先提交诊断结果更新
                try:
                    db_session.flush()  # 刷新到数据库但不提交事务
                    logger.warning(f"✅ [等待诊断] 诊断结果已flush: diagnosis_id={diagnosis.id}")
                except Exception as flush_error:
                    logger.error(f"❌ [等待诊断] flush失败: {str(flush_error)}", exc_info=True)
                    db_session.rollback()
                    continue
                
                # 获取告警记录
                alert = db_session.query(AlertRecord).filter(
                    AlertRecord.id == diagnosis.alert_id
                ).first()
                
                if alert:
                    logger.warning(f"🤖 [等待诊断] 开始AI解读: alert_id={alert.id}")
                    try:
                        # 使用诊断结果重新进行AI解读
                        await self._ai_interpret(alert, diagnosis, api_result=parsed_result, db=db_session)
                        logger.warning(f"✅ [等待诊断] AI解读完成: alert_id={alert.id}")
                    except Exception as ai_error:
                        logger.warning(f"⚠️ [等待诊断] AI解读失败但继续: {str(ai_error)}")
                    
                    logger.warning(f"📢 [等待诊断] 发送通知: alert_id={alert.id}")
                    try:
                        # 发送更新通知（包含诊断结果和AI解读）
                        await self.webhook_notifier.send_alert_notification(alert, diagnosis)
                        logger.warning(f"✅ [等待诊断] 通知发送完成: alert_id={alert.id}")
                    except Exception as webhook_error:
                        logger.warning(f"⚠️ [等待诊断] 通知发送失败但继续: {str(webhook_error)}")
                
                # 最后统一提交所有更改
                try:
                    db_session.commit()
                    logger.warning(f"✅ [等待诊断] 数据库提交成功: diagnosis_id={diagnosis.id}, api_status={diagnosis.api_status}, items={diagnosis.api_items_count}")
                except Exception as commit_error:
                    logger.error(f"❌ [等待诊断] commit失败: {str(commit_error)}", exc_info=True)
                    db_session.rollback()
            
            logger.warning(f"🎉 [等待诊断] 全部完成: task_id={task_id}, 已更新 {len(diagnosis_ids)} 条记录")
            
        except Exception as e:
            logger.error(f"❌ [等待诊断] 异常: task_id={task_id}, error={str(e)}", exc_info=True)
            # 回滚事务
            db_session.rollback()
    
    def _wait_diagnosis_in_thread(self, cluster_id: str, task_id: str, diagnosis_ids: list):
        """
        在独立线程中等待诊断完成（不依赖事件循环）
        
        Args:
            cluster_id: 集群ID
            task_id: 任务ID
            diagnosis_ids: 诊断结果ID列表（同一个节点可能有多个告警）
        """
        logger.warning(f"🔵 [后台线程] 进入方法: task_id={task_id}, diagnosis_ids={diagnosis_ids}")
        
        try:
            # 在新线程中创建独立的数据库session和事件循环
            logger.warning(f"📦 [后台线程] 准备创建Session和事件循环: task_id={task_id}")
            from app.core.deps import SessionLocal
            db = SessionLocal()
            logger.warning(f"✅ [后台线程] Session创建成功: task_id={task_id}")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.warning(f"✅ [后台线程] 事件循环创建成功: task_id={task_id}")
            
            try:
                # 运行异步等待任务（传入独立的db session）
                logger.warning(f"🔄 [后台线程] 开始执行异步等待: task_id={task_id}")
                loop.run_until_complete(
                    self._wait_and_update_diagnosis(cluster_id, task_id, diagnosis_ids, db)
                )
                logger.warning(f"✅ [后台线程] 异步等待完成: task_id={task_id}")
            finally:
                logger.warning(f"🔒 [后台线程] 清理资源: task_id={task_id}")
                loop.close()
                db.close()
                logger.warning(f"✅ [后台线程] 资源清理完成: task_id={task_id}")
        except Exception as e:
            logger.error(f"❌ [后台线程] 异常: task_id={task_id}, error={str(e)}", exc_info=True)
