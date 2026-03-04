#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控数据分析服务
"""
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

# 百度云BCM客户端
try:
    from baidubce.services.bcm.bcm_client import BcmClient
    from baidubce.bce_client_configuration import BceClientConfiguration
    from baidubce.auth.bce_credentials import BceCredentials
    BCM_AVAILABLE = True
except ImportError:
    BCM_AVAILABLE = False
    logger.warning("bce-python-sdk未安装，BCC/BOS监控功能将不可用")

from legacy_modules.monitoring_analysis import BCCAnalyzer, BOSAnalyzer
from legacy_modules.monitoring_analysis.bcc_analyzer_ai import BCCAnalyzerAI
from legacy_modules.monitoring_analysis.bos_analyzer_ai import BOSAnalyzerAI


class MonitoringService:
    """监控分析服务"""
    
    def __init__(self):
        self.tasks = {}  # 任务存储
        self.bcm_client = None
        self.task_progress = {}  # 任务进度存储
        
    def init_bcm_client(self, access_key_id: str, secret_access_key: str, endpoint: str = "bcm.cd.baidubce.com"):
        """
        初始化BCM客户端
        
        Args:
            access_key_id: AK
            secret_access_key: SK
            endpoint: BCM端点
        """
        if not BCM_AVAILABLE:
            raise Exception("bce-python-sdk未安装")
        
        config = BceClientConfiguration(
            credentials=BceCredentials(access_key_id, secret_access_key),
            endpoint=endpoint
        )
        self.bcm_client = BcmClient(config)
        logger.info(f"BCM客户端初始化成功: {endpoint}")
    
    def _update_progress(self, task_id: str, current: int, total: int, message: str):
        """更新任务进度"""
        progress = int((current / total) * 100) if total > 0 else 0
        self.task_progress[task_id] = {
            'current': current,
            'total': total,
            'progress': progress,
            'message': message,
            'updated_at': datetime.now().isoformat()
        }
        logger.info(f"[{task_id}] 进度: {progress}% - {message}")
    
    async def analyze_bcc(
        self,
        instance_ids: List[str],
        days: int = 7,
        ak: Optional[str] = None,
        sk: Optional[str] = None
    ) -> str:
        """
        执行BCC监控分析
        
        Args:
            instance_ids: BCC实例ID列表
            days: 查询天数
            ak: 访问密钥（可选）
            sk: 密钥（可选）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        try:
            self._update_progress(task_id, 0, 100, "初始化BCM客户端...")
            
            # 初始化BCM客户端（优先使用传入的AK/SK，否则使用默认配置）
            if ak and sk:
                self.init_bcm_client(ak, sk)
            elif not self.bcm_client:
                # 使用默认配置
                from app.core.config import settings
                logger.info(f"[{task_id}] 使用默认BCE配置")
                self.init_bcm_client(settings.BCE_ACCESS_KEY, settings.BCE_SECRET_KEY, settings.BCM_HOST)
            
            if not self.bcm_client:
                raise Exception("BCM客户端初始化失败")
            
            self._update_progress(task_id, 10, 100, "创建分析器...")
            
            # 创建分析器
            analyzer = BCCAnalyzerAI(bcm_client=self.bcm_client)
            
            # 执行分析
            logger.info(f"[{task_id}] 开始BCC监控分析，实例数: {len(instance_ids)}")
            
            self._update_progress(task_id, 20, 100, f"加载{len(instance_ids)}个实例...")
            
            # 加载实例列表
            analyzer.load_instances_from_list(instance_ids)
            
            self._update_progress(task_id, 30, 100, "获取监控数据...")
            
            # 获取监控数据
            responses = analyzer.get_monitoring_data(days=days)
            
            self._update_progress(task_id, 60, 100, "处理监控数据...")
            
            # 处理数据
            df = analyzer.process_data(responses)
            
            if df.empty:
                raise Exception("未获取到任何监控数据")
            
            self._update_progress(task_id, 70, 100, "计算统计数据...")
            
            # 获取统计数据
            instance_stats = analyzer.get_instance_stats(df)
            
            self._update_progress(task_id, 80, 100, "生成HTML报告...")
            
            # 生成HTML报告（倒金字塔结构）
            logger.info(f"[{task_id}] 生成HTML报告...")
            html_content = analyzer.generate_html_report_ai(df)
            
            self._update_progress(task_id, 90, 100, "上传报告到MinIO...")

            # 使用统一上传服务上传HTML到MinIO
            from app.services.report_upload_service import get_report_upload_service
            upload_service = get_report_upload_service()

            html_object_name, html_url = upload_service.upload_html_content(
                task_id=task_id,
                html_content=html_content,
                report_type='bcc'
            )

            logger.info(f"[{task_id}] BCC报告已上传到MinIO: {html_object_name}")
            
            self._update_progress(task_id, 100, 100, "分析完成")

            # 构建分析结果
            analysis_result = {
                'success': True,
                'instance_count': len(instance_ids),
                'data_points': len(df),
                'instance_stats': instance_stats,
                'html_report': html_object_name,
                'html_report_url': html_url,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.tasks[task_id] = {
                'status': 'completed',
                'result': analysis_result,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存到MySQL
            try:
                from app.services.task_service import save_task_to_db
                from app.models.task import TaskType, TaskStatus
                save_task_to_db(task_id, TaskType.MONITORING_BCC, TaskStatus.COMPLETED, "BCC AI分析完成", result_url=html_object_name)
            except Exception as e:
                logger.warning(f"保存BCC任务到MySQL失败: {e}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"[{task_id}] BCC分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.tasks[task_id] = {
                'status': 'failed',
                'error': str(e),
                'created_at': datetime.now().isoformat()
            }
            # 保存失败状态到MySQL
            try:
                from app.services.task_service import save_task_to_db
                from app.models.task import TaskType, TaskStatus
                save_task_to_db(task_id, TaskType.MONITORING_BCC, TaskStatus.FAILED, error_message=str(e))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 保存BCC任务失败状态到数据库失败: {db_error}")
            raise
    
    async def analyze_bos(
        self,
        buckets: List[str],
        ak: Optional[str] = None,
        sk: Optional[str] = None
    ) -> str:
        """
        执行BOS存储分析
        
        Args:
            buckets: Bucket名称列表
            ak: 访问密钥（可选）
            sk: 密钥（可选）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        try:
            self._update_progress(task_id, 0, 100, "初始化BCM客户端...")
            
            # 初始化BCM客户端（优先使用传入的AK/SK，否则使用默认配置）
            if ak and sk:
                self.init_bcm_client(ak, sk)
            elif not self.bcm_client:
                # 使用默认配置
                from app.core.config import settings
                logger.info(f"[{task_id}] 使用默认BCE配置")
                self.init_bcm_client(settings.BCE_ACCESS_KEY, settings.BCE_SECRET_KEY, settings.BCM_HOST)
            
            if not self.bcm_client:
                raise Exception("BCM客户端初始化失败")
            
            self._update_progress(task_id, 10, 100, "创建分析器...")
            
            # 创建分析器
            analyzer = BOSAnalyzerAI(bcm_client=self.bcm_client)
            
            # 设置进度回调
            def progress_callback(current: int, total: int, message: str):
                # 将分析器的进度映射到20%-80%
                progress = 20 + int((current / total) * 60) if total > 0 else 20
                self._update_progress(task_id, progress, 100, message)
            
            analyzer.set_progress_callback(progress_callback)
            
            # 执行分析
            logger.info(f"[{task_id}] 开始BOS存储分析，Bucket数: {len(buckets)}")
            
            self._update_progress(task_id, 20, 100, f"开始分析{len(buckets)}个Bucket...")
            
            # 执行完整分析
            analysis_result = analyzer.analyze(buckets=buckets)
            
            if not analysis_result['success']:
                raise Exception(analysis_result.get('message', '分析失败'))
            
            self._update_progress(task_id, 80, 100, "生成HTML报告...")
            
            # 生成HTML报告（倒金字塔结构）
            logger.info(f"[{task_id}] 生成HTML报告...")
            html_content = await analyzer.generate_html_report(analysis_result['all_buckets'])  # 添加 await
            
            self._update_progress(task_id, 90, 100, "上传报告到MinIO...")

            # 使用统一上传服务上传HTML到MinIO
            from app.services.report_upload_service import get_report_upload_service
            upload_service = get_report_upload_service()

            html_object_name, html_url = upload_service.upload_html_content(
                task_id=task_id,
                html_content=html_content,
                report_type='bos'
            )

            logger.info(f"[{task_id}] BOS报告已上传到MinIO: {html_object_name}")
            
            self._update_progress(task_id, 100, 100, "分析完成")

            # 更新分析结果
            analysis_result['html_report'] = html_object_name
            analysis_result['html_report_url'] = html_url
            self.tasks[task_id] = {
                'status': 'completed',
                'result': analysis_result,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存到MySQL
            try:
                from app.services.task_service import save_task_to_db
                from app.models.task import TaskType, TaskStatus
                save_task_to_db(task_id, TaskType.MONITORING_BOS, TaskStatus.COMPLETED, "BOS AI分析完成", result_url=html_object_name)
            except Exception as e:
                logger.warning(f"保存BOS任务到MySQL失败: {e}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"[{task_id}] BOS分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.tasks[task_id] = {
                'status': 'failed',
                'error': str(e),
                'created_at': datetime.now().isoformat()
            }
            # 保存失败状态到MySQL
            try:
                from app.services.task_service import save_task_to_db
                from app.models.task import TaskType, TaskStatus
                save_task_to_db(task_id, TaskType.MONITORING_BOS, TaskStatus.FAILED, error_message=str(e))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 保存BOS任务失败状态到数据库失败: {db_error}")
            raise
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # 如果任务完成，返回包含html_file的响应
        if task.get('status') == 'completed' and 'result' in task:
            html_report = task['result'].get('html_report', '')
            # 使用API代理路径访问MinIO文件
            if html_report:
                return {
                    'status': 'completed',
                    'html_file': f'/api/v1/reports/proxy/{html_report}',
                    'task_id': task_id
                }
        
        return task
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            进度信息
        """
        return self.task_progress.get(task_id)


# 全局服务实例
monitoring_service = MonitoringService()
