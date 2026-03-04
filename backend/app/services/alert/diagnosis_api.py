"""
诊断 API 调用服务
调用百度云 CCE 节点诊断接口
"""
import logging
import time
import hmac
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote
import httpx

from app.core.config_alert import settings

logger = logging.getLogger(__name__)


class DiagnosisAPIService:
    """诊断 API 服务"""
    
    def __init__(self):
        self.base_url = settings.DIAGNOSIS_API_BASE_URL
        self.access_key = settings.BCE_ACCESS_KEY
        self.secret_key = settings.BCE_SECRET_KEY
        self.timeout = settings.DIAGNOSIS_API_TIMEOUT
    
    def _generate_auth_string(self, method: str, uri: str, params: Dict = None) -> str:
        """
        生成百度云 BCE 认证字符串
        
        Args:
            method: HTTP 方法
            uri: 请求 URI
            params: 查询参数
            
        Returns:
            认证字符串
        """
        # 生成时间戳
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # 生成签名密钥
        auth_string_prefix = f"bce-auth-v1/{self.access_key}/{timestamp}/1800"
        signing_key = hmac.new(
            self.secret_key.encode('utf-8'),
            auth_string_prefix.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # 生成 CanonicalRequest
        canonical_uri = quote(uri, safe='/')
        canonical_querystring = ''
        if params:
            sorted_params = sorted(params.items())
            canonical_querystring = '&'.join([f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted_params])
        
        canonical_headers = f"host:{self.base_url.replace('https://', '').replace('http://', '')}"
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}"
        
        # 生成签名
        signature = hmac.new(
            signing_key.encode('utf-8'),
            canonical_request.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # 生成最终认证字符串
        auth_string = f"{auth_string_prefix}/host/{signature}"
        
        return auth_string
    
    async def create_node_diagnosis(self, cluster_id: str, node_name: str) -> Optional[str]:
        """
        创建节点诊断任务
        
        Args:
            cluster_id: 集群 ID
            node_name: 节点名称（IP地址）
            
        Returns:
            任务 ID，失败返回 None
        """
        uri = f"/v2/cluster/{cluster_id}/diagnosis"
        url = f"{self.base_url}{uri}"
        
        # 生成认证字符串
        auth_string = self._generate_auth_string('POST', uri)
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_string,
            'Host': self.base_url.replace('https://', '').replace('http://', '')
        }
        
        payload = {
            'type': 'node',
            'target': {
                'nodeName': node_name
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    task_id = data.get('taskId')
                    logger.info(f"创建诊断任务成功: {task_id}, 节点: {node_name}")
                    return task_id
                else:
                    logger.error(f"创建诊断任务失败: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"调用诊断 API 失败: {str(e)}", exc_info=True)
            return None
    
    async def get_diagnosis_report(self, cluster_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取诊断报告详情
        
        Args:
            cluster_id: 集群 ID
            task_id: 任务 ID
            
        Returns:
            诊断报告，失败返回 None
        """
        uri = f"/v2/cluster/{cluster_id}/diagnosis/{task_id}/report"
        url = f"{self.base_url}{uri}"
        
        # 生成认证字符串
        auth_string = self._generate_auth_string('GET', uri)
        
        headers = {
            'Authorization': auth_string,
            'Host': self.base_url.replace('https://', '').replace('http://', '')
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"获取诊断报告成功: {task_id}")
                    return data
                else:
                    logger.error(f"获取诊断报告失败: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取诊断报告失败: {str(e)}", exc_info=True)
            return None
    
    async def wait_for_diagnosis_complete(
        self, 
        cluster_id: str, 
        task_id: str, 
        max_wait_time: int = 300,
        poll_interval: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        等待诊断任务完成并获取报告
        
        Args:
            cluster_id: 集群 ID
            task_id: 任务 ID
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            诊断报告，失败或超时返回 None
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            report = await self.get_diagnosis_report(cluster_id, task_id)
            
            if report:
                # 检查是否完成
                if report.get('completed'):
                    logger.info(f"诊断任务完成: {task_id}")
                    return report
                
                # 检查是否失败
                task_result = report.get('taskResult', '')
                if task_result == 'failed':
                    logger.error(f"诊断任务失败: {task_id}")
                    return report
            
            # 等待后重试
            logger.info(f"诊断任务进行中: {task_id}, 等待 {poll_interval} 秒后重试...")
            await asyncio.sleep(poll_interval)
        
        logger.warning(f"诊断任务超时: {task_id}, 等待时间: {max_wait_time} 秒")
        return None
    
    def parse_diagnosis_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析诊断报告
        
        Args:
            report: 原始诊断报告
            
        Returns:
            解析后的诊断结果（包含原始报告）
        """
        if not report:
            return {}
        
        # 提取关键信息
        result = {
            'task_id': report.get('taskId'),
            'diagnosis_type': report.get('diagnosisType'),
            'task_result': report.get('taskResult'),  # normal/abnormal/doing/failed
            'completed': report.get('completed', False),
            'start_time': report.get('startTime'),
            'end_time': report.get('endTime'),
            'items_count': report.get('itemsCount', 0),
            'target': report.get('target', {}),
            'conclusion': report.get('conclusion', {}),
            'all_items': [],  # 所有诊断项
            'abnormal_items': [],
            'warning_items': [],
            'error_items': [],
            'raw_report': report  # 保存完整的原始报告
        }
        
        # 解析诊断项
        # reportItems结构: {"分类名": {"诊断项名": {诊断项数据}}}
        report_items = report.get('reportItems', {})
        
        logger.info(f"开始解析诊断报告: 任务ID={result['task_id']}, "
                   f"分类数量={len(report_items)}")
        
        for category, items in report_items.items():
            if not isinstance(items, dict):
                logger.warning(f"分类 {category} 的内容不是字典: {type(items)}")
                continue
            
            logger.debug(f"解析分类 {category}: {len(items)} 个诊断项")
                
            for item_name, item_data in items.items():
                if not isinstance(item_data, dict):
                    logger.warning(f"诊断项 {item_name} 的内容不是字典: {type(item_data)}")
                    continue
                    
                composed_result = item_data.get('composedResult', 'normal')
                grade = item_data.get('grade', 'info')
                
                # 直接使用 composedResult 作为诊断结果
                # grade 只是检查项的严重程度级别，不是检查结果
                actual_result = composed_result
                
                item_info = {
                    'category': category,
                    'item_name': item_name,
                    'item_name_zh': item_data.get('itemNameZH', ''),
                    'description': item_data.get('description', ''),
                    'result': actual_result,  # 使用映射后的结果
                    'original_result': composed_result,  # 保留原始结果
                    'grade': grade,
                    'value': item_data.get('value', ''),
                    'suggestion': item_data.get('suggestion', ''),
                    'exact_message': item_data.get('exactMessage', '')
                }
                
                # 保存所有诊断项
                result['all_items'].append(item_info)
                
                # 分类存储异常项（根据 composedResult 字段判断）
                if composed_result == 'error':
                    result['error_items'].append(item_info)
                    logger.debug(f"错误项: {item_info['item_name_zh']} ({item_name})")
                elif composed_result == 'warning':
                    result['warning_items'].append(item_info)
                    logger.debug(f"警告项: {item_info['item_name_zh']} ({item_name})")
                elif composed_result == 'abnormal':
                    result['abnormal_items'].append(item_info)
                    logger.debug(f"异常项: {item_info['item_name_zh']} ({item_name})")
        
        logger.info(f"诊断报告解析完成: 任务ID={result['task_id']}, "
                   f"总诊断项={len(result['all_items'])}, "
                   f"错误项={len(result['error_items'])}, "
                   f"警告项={len(result['warning_items'])}, "
                   f"异常项={len(result['abnormal_items'])}")
        
        return result
