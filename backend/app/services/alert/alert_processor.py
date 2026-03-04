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
                                self.webhook_notifier = WebhookNotifier(db)
                            
                            # 解析文件
                            alerts_data = self.parser.parse_file(file_path)
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
            alerts_data = self.parser.parse_file(file_path)
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
        db = None
        try:
            # 创建独立Session
            db = self._get_db_session()
            
            # 按需初始化依赖
            if self.manual_matcher is None:
                self.manual_matcher = ManualMatchService(db)
            if self.webhook_notifier is None:
                self.webhook_notifier = WebhookNotifier(db)
            
            # 处理基础流程
            alert, diagnosis = await self._process_alert_basic(alert_data, db)
            
            if not alert or not diagnosis:
                return False
            
            # 判断是否为CCE集群节点
            is_cce = alert.is_cce_cluster
            
            if is_cce and alert.cluster_id and alert.ip:
                # 检查15分钟窗口
                existing_diagnosis = await self._find_existing_diagnosis(alert.cluster_id, alert.ip, db)
                
                if existing_diagnosis:
                    # 复用已有诊断结果
                    await self._reuse_diagnosis(existing_diagnosis, [(alert, diagnosis)], db)
                    db.commit()
                    logger.info(f"🔄 复用诊断: {alert.cluster_id}:{alert.ip} → {existing_diagnosis.api_task_id}")
                else:
                    # 创建新诊断任务
                    await self._create_single_diagnosis(alert.cluster_id, alert.ip, [(alert, diagnosis)], db)
            else:
                logger.info(f"📋 物理机节点跳过诊断: IP={alert.ip}, 告警类型={alert.alert_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"处理单条告警异常: {str(e)}", exc_info=True)
            if db:
                db.rollback()
            return False
        finally:
            if db:
                try:
                    db.close()
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
        try:
            # 1. 检查是否已存在相同告警（防止重复）
            existing_alert = db.query(AlertRecord).filter(
                AlertRecord.alert_type == alert_data.get('alert_type', ''),
                AlertRecord.ip == alert_data.get('ip'),
                AlertRecord.timestamp == alert_data.get('timestamp', datetime.now())
            ).first()
            
            if existing_alert:
                logger.info(f"告警已存在，跳过: ID={existing_alert.id}, 类型={existing_alert.alert_type}, IP={existing_alert.ip}")
                # 返回已存在的告警和诊断结果
                diagnosis = db.query(DiagnosisResult).filter(
                    DiagnosisResult.alert_id == existing_alert.id
                ).first()
                return existing_alert, diagnosis
            
            # 2. 创建告警记录
            # 将raw_data中的datetime对象转换为ISO格式字符串，以便JSON序列化
            raw_data_serializable = self._make_json_serializable(alert_data)
            
            alert = AlertRecord(
                alert_type=alert_data.get('alert_type', ''),
                component=alert_data.get('component'),
                severity=alert_data.get('severity', 'WARN'),
                ip=alert_data.get('ip'),
                cluster_id=alert_data.get('cluster_id'),
                instance_id=alert_data.get('instance_id'),
                hostname=alert_data.get('hostname'),
                is_cce_cluster=alert_data.get('is_cce_cluster', False),
                timestamp=alert_data.get('timestamp', datetime.now()),
                raw_data=raw_data_serializable
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            logger.info(f"创建告警记录: ID={alert.id}, 类型={alert.alert_type}, 集群={alert.cluster_id}, IP={alert.ip}")
            
            # 3. 匹配故障手册
            diagnosis = await self._match_manual(alert, db)
            
            # 4. 初始AI解读（不包含诊断结果）
            if diagnosis:
                await self._ai_interpret(alert, diagnosis, api_result=None, db=db)
            
            # 5. 发送初始Webhook通知
            await self.webhook_notifier.send_alert_notification(alert, diagnosis)
            
            return alert, diagnosis
            
        except Exception as e:
            logger.error(f"处理单条告警基础流程异常: {str(e)}", exc_info=True)
            db.rollback()
            return None, None
    
    
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
            task_id = await self.diagnosis_api.create_node_diagnosis(cluster_id, first_alert.ip)
            
            if task_id:
                # 更新所有告警的诊断结果
                for alert, diagnosis in alert_diagnosis_list:
                    db.refresh(diagnosis)
                    diagnosis.api_task_id = task_id
                    diagnosis.api_status = 'processing'
                
                db.commit()
                logger.info(f"✅ 创建新诊断任务: {cluster_id}:{ip} → {task_id}")
                
                # 启动后台线程等待诊断完成
                diagnosis_ids = [diagnosis.id for _, diagnosis in alert_diagnosis_list]
                import threading
                threading.Thread(
                    target=self._wait_diagnosis_in_thread,
                    args=(cluster_id, task_id, diagnosis_ids),
                    daemon=True
                ).start()
            else:
                # 创建失败
                for alert, diagnosis in alert_diagnosis_list:
                    db.refresh(diagnosis)
                    diagnosis.api_status = 'failed'
                db.commit()
                logger.error(f"❌ 创建诊断任务失败: {cluster_id}:{ip}")
                
        except Exception as e:
            logger.error(f"创建诊断任务异常: {cluster_id}:{ip}, {str(e)}", exc_info=True)
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
    
    async def _match_manual(self, alert: AlertRecord, db: Session) -> Optional[DiagnosisResult]:
        """
        匹配故障手册
        
        Args:
            alert: 告警记录
            db: 数据库Session
            
        Returns:
            诊断结果
        """
        try:
            # 匹配手册
            manual = self.manual_matcher.match(alert.alert_type, alert.component)
            
            # 创建诊断结果
            diagnosis = DiagnosisResult(
                alert_id=alert.id,
                manual_matched=manual is not None,
                manual_name_zh=manual.get('name_zh') if manual else None,
                danger_level=manual.get('danger_level') if manual else None,
                manual_solution=manual.get('solution') if manual else None,
                manual_impact=manual.get('impact') if manual else None,
                manual_recovery=manual.get('recovery') if manual else None,
                customer_aware=manual.get('customer_aware') if manual else None,
                source='manual' if manual else 'none'
            )
            
            db.add(diagnosis)
            db.commit()
            db.refresh(diagnosis)
            
            if manual:
                logger.info(f"✅ 手册匹配成功: 告警ID={alert.id}, 类型={alert.alert_type}, 手册={manual.get('name_zh')}")
                logger.debug(f"   影响: {manual.get('impact', 'N/A')[:50]}...")
                logger.debug(f"   恢复: {manual.get('recovery', 'N/A')[:50]}...")
            else:
                logger.warning(f"⚠️ 未找到匹配的手册: 告警ID={alert.id}, 类型={alert.alert_type}")
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"匹配手册异常: {str(e)}", exc_info=True)
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
            logger.info(f"等待诊断任务完成: {task_id}, 关联诊断记录数={len(diagnosis_ids)}")
            
            # 等待诊断完成（增加等待时间到15分钟）
            report = await self.diagnosis_api.wait_for_diagnosis_complete(
                cluster_id, 
                task_id,
                max_wait_time=900,  # 15分钟
                poll_interval=15     # 每15秒轮询一次
            )
            
            if not report:
                logger.error(f"诊断任务超时或失败: {task_id}")
                # 更新所有诊断记录的状态为失败
                for diagnosis_id in diagnosis_ids:
                    diagnosis = db_session.query(DiagnosisResult).filter(
                        DiagnosisResult.id == diagnosis_id
                    ).first()
                    if diagnosis:
                        diagnosis.api_status = 'timeout'
                        db_session.commit()
                return
            
            # 解析诊断报告
            parsed_result = self.diagnosis_api.parse_diagnosis_report(report)
            
            # 更新所有诊断记录（共享同一个诊断结果）
            for diagnosis_id in diagnosis_ids:
                diagnosis = db_session.query(DiagnosisResult).filter(
                    DiagnosisResult.id == diagnosis_id
                ).first()
                
                if diagnosis:
                    diagnosis.api_status = parsed_result.get('task_result', 'unknown')
                    # 保存完整的诊断报告（包含 raw_report 和解析后的数据）
                    diagnosis.api_diagnosis = parsed_result
                    # 保存统计字段
                    diagnosis.api_items_count = len(parsed_result.get('all_items', []))
                    diagnosis.api_error_count = len(parsed_result.get('error_items', []))
                    diagnosis.api_warning_count = len(parsed_result.get('warning_items', []))
                    diagnosis.api_abnormal_count = len(parsed_result.get('abnormal_items', []))
                    
                    logger.info(f"更新诊断记录: 诊断ID={diagnosis.id}, 告警ID={diagnosis.alert_id}, "
                               f"总项={diagnosis.api_items_count}, "
                               f"错误={diagnosis.api_error_count}, "
                               f"警告={diagnosis.api_warning_count}")
                    
                    # 获取告警记录
                    alert = db_session.query(AlertRecord).filter(
                        AlertRecord.id == diagnosis.alert_id
                    ).first()
                    
                    if alert:
                        # 使用诊断结果重新进行AI解读
                        await self._ai_interpret(alert, diagnosis, api_result=parsed_result)
                        
                        # 发送更新通知（包含诊断结果和AI解读）
                        await self.webhook_notifier.send_alert_notification(alert, diagnosis)
                    
                    db_session.commit()
            
            logger.info(f"诊断任务完成: {task_id}, 已更新 {len(diagnosis_ids)} 条诊断记录")
            
        except Exception as e:
            logger.error(f"等待诊断完成异常: {str(e)}", exc_info=True)
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
        try:
            # 在新线程中创建独立的数据库session和事件循环
            from app.core.deps import SessionLocal
            db = SessionLocal()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 运行异步等待任务（传入独立的db session）
                loop.run_until_complete(
                    self._wait_and_update_diagnosis(cluster_id, task_id, diagnosis_ids, db)
                )
            finally:
                loop.close()
                db.close()
        except Exception as e:
            logger.error(f"线程中等待诊断异常: {str(e)}", exc_info=True)
