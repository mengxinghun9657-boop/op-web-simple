#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIP带宽监控服务
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
    logger.warning("bce-python-sdk未安装，EIP监控功能将不可用")

from legacy_modules.eip_analysis import EIPAnalyzer
from legacy_modules.eip_analysis.eip_analyzer_ai import EIPAnalyzerAI


class EIPService:
    """EIP带宽监控服务"""
    
    def __init__(self):
        self.tasks = {}  # 任务存储
        self.bcm_client = None
        
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
    
    async def analyze_eip(
        self,
        eip_ids: List[str],
        hours: int = 6,
        ak: Optional[str] = None,
        sk: Optional[str] = None
    ) -> str:
        """
        执行EIP带宽分析
        
        Args:
            eip_ids: EIP ID列表
            hours: 查询小时数
            ak: 访问密钥（可选）
            sk: 密钥（可选）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        try:
            # 初始化BCM客户端（优先使用传入的AK/SK，否则使用默认配置）
            if ak and sk:
                self.init_bcm_client(ak, sk)
            elif not self.bcm_client:
                # 使用默认配置
                from app.core.config import settings
                logger.info(f"[{task_id}] 使用默认BCE配置")
                self.init_bcm_client(settings.BCE_ACCESS_KEY, settings.BCE_SECRET_KEY)
            
            if not self.bcm_client:
                raise Exception("BCM客户端初始化失败")
            
            # 创建AI分析器
            analyzer = EIPAnalyzerAI(bcm_client=self.bcm_client)
            
            # 执行分析
            logger.info(f"[{task_id}] 开始EIP带宽分析（AI增强版），实例数: {len(eip_ids)}")
            
            # 执行完整分析
            analysis_result = analyzer.analyze(eip_ids=eip_ids, hours=hours)
            
            if not analysis_result['success']:
                raise Exception(analysis_result.get('message', '分析失败'))
            
            # 生成HTML报告（AI驱动的倒金字塔结构）
            logger.info(f"[{task_id}] 生成AI驱动的HTML报告...")
            
            # 需要DataFrame来生成HTML
            import pandas as pd
            df = pd.DataFrame(analysis_result['raw_data']['df'])
            eip_stats = analysis_result['eip_stats']
            html_content = analyzer.generate_html_report(df, eip_stats)

            # 使用统一上传服务上传HTML到MinIO（EIP只有HTML报告）
            from app.services.report_upload_service import get_report_upload_service
            upload_service = get_report_upload_service()

            html_object_name, html_url = upload_service.upload_html_content(
                task_id=task_id,
                html_content=html_content,
                report_type='eip'
            )

            logger.info(f"[{task_id}] EIP AI HTML报告已上传到MinIO: {html_object_name}")

            # 存储结果（移除raw_data避免过大）
            result_summary = {
                'success': analysis_result['success'],
                'eip_count': analysis_result['eip_count'],
                'data_points': analysis_result['data_points'],
                'eip_stats': analysis_result['eip_stats'],
                'aggregate': analysis_result['aggregate'],
                'anomalies': analysis_result.get('anomalies', []),
                'recommendations': analysis_result.get('recommendations', []),
                'analysis_time': analysis_result['analysis_time'],
                'html_report': html_object_name,
                'html_report_url': html_url
            }
            
            self.tasks[task_id] = {
                'status': 'completed',
                'result': result_summary,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存到MySQL
            try:
                from app.services.task_service import save_task_to_db
                from app.models.task import TaskType, TaskStatus
                save_task_to_db(task_id, TaskType.MONITORING_EIP, TaskStatus.COMPLETED, "EIP AI分析完成", result_url=html_object_name)
            except Exception as e:
                logger.warning(f"保存EIP任务到MySQL失败: {e}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"[{task_id}] EIP分析失败: {e}")
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
                save_task_to_db(task_id, TaskType.MONITORING_EIP, TaskStatus.FAILED, error_message=str(e))
            except Exception as db_error:
                logger.warning(f"[{task_id}] 保存EIP任务失败状态到数据库失败: {db_error}")
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
                    'task_id': task_id,
                    'eip_count': task['result'].get('eip_count', 0),
                    'data_points': task['result'].get('data_points', 0)
                }
        
        return task


# 全局服务实例
eip_service = EIPService()
