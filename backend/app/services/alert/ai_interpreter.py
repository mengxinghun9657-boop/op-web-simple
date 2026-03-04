"""
AI 解读服务
使用厂内 ERNIE API 对诊断结果进行智能解读
"""
import logging
from typing import Dict, Any, Optional
from app.services.ai.ernie_client import ERNIEClient
from app.core.config_alert import settings

logger = logging.getLogger(__name__)


class AIInterpreterService:
    """AI 解读服务"""
    
    def __init__(self):
        self.ernie_client = None
        try:
            self.ernie_client = ERNIEClient()
            logger.info("ERNIE客户端初始化成功")
        except Exception as e:
            logger.error(f"ERNIE客户端初始化失败: {str(e)}")
    
    async def interpret_diagnosis(
        self, 
        alert_info: Dict[str, Any],
        manual_result: Optional[Dict[str, Any]] = None,
        api_result: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        使用AI解读诊断结果
        
        Args:
            alert_info: 告警信息
            manual_result: 手册匹配结果
            api_result: API诊断结果
            
        Returns:
            AI解读文本，失败返回 None
        """
        if not self.ernie_client:
            logger.warning("ERNIE客户端未初始化，跳过AI解读")
            return None
        
        try:
            # 构建提示词
            prompt = self._build_prompt(alert_info, manual_result, api_result)
            
            # 调用ERNIE API
            logger.info("开始调用ERNIE API进行诊断解读")
            response = await self.ernie_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            if response:
                logger.info("AI解读成功")
                return response
            else:
                logger.warning("AI解读返回空结果")
                return None
                
        except Exception as e:
            logger.error(f"AI解读失败: {str(e)}", exc_info=True)
            return None
    
    def _build_prompt(
        self,
        alert_info: Dict[str, Any],
        manual_result: Optional[Dict[str, Any]] = None,
        api_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建AI解读提示词
        
        Args:
            alert_info: 告警信息
            manual_result: 手册匹配结果
            api_result: API诊断结果
            
        Returns:
            提示词文本
        """
        # 构建提示词
        prompt_parts = [
            "请对以下硬件告警诊断数据进行专业的AI分析和总结：",
            "",
            "【告警信息】"
        ]
        
        # 基本告警信息
        prompt_parts.extend([
            f"- 告警类型: {alert_info.get('alert_type', 'N/A')}",
            f"- 组件类型: {alert_info.get('component', 'N/A')}",
            f"- 严重程度: {alert_info.get('severity', 'N/A')}",
            f"- IP地址: {alert_info.get('ip', 'N/A')}",
            f"- 告警时间: {alert_info.get('timestamp', 'N/A')}",
            ""
        ])
        
        # 添加手册匹配结果
        if manual_result and manual_result.get('matched'):
            prompt_parts.extend([
                "【故障手册匹配】",
                f"- 故障名称: {manual_result.get('name_zh', 'N/A')}",
                f"- 危害等级: {manual_result.get('danger_level', 'N/A')}",
                f"- 解决方案: {manual_result.get('solution', 'N/A')[:200]}...",
                ""
            ])
        
        # 添加API诊断结果
        if api_result:
            prompt_parts.extend([
                "【节点诊断结果】",
                f"- 诊断状态: {api_result.get('task_result', 'N/A')}",
                f"- 诊断项数量: {api_result.get('items_count', 0)}项",
                f"- 异常项数量: {len(api_result.get('error_items', []))}个错误, {len(api_result.get('warning_items', []))}个警告",
                ""
            ])
            
            # 添加关键异常项
            error_items = api_result.get('error_items', [])
            warning_items = api_result.get('warning_items', [])
            
            if error_items:
                prompt_parts.append("【关键错误项】")
                for item in error_items[:3]:  # 最多显示3个
                    item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                    message = item.get('exact_message') or item.get('description', 'N/A')
                    prompt_parts.append(f"- {item_name}: {message[:100]}")
                prompt_parts.append("")
            
            if warning_items:
                prompt_parts.append("【警告项】")
                for item in warning_items[:2]:  # 最多显示2个
                    item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                    message = item.get('exact_message') or item.get('description', 'N/A')
                    prompt_parts.append(f"- {item_name}: {message[:100]}")
                prompt_parts.append("")
        
        # 添加分析要求
        prompt_parts.extend([
            "请生成一段Markdown格式的诊断分析（300字以内），包括：",
            "1. 问题诊断（故障根本原因）",
            "2. 影响评估（可能造成的影响）",
            "3. 处理建议（具体操作步骤）",
            "4. 预防措施（如何避免复发）",
            "",
            "要求：",
            "- 使用Markdown格式（标题、列表、加粗）",
            "- 语言简洁专业，重点突出",
            "- 提供可操作的具体建议",
            "- 如果信息不足，说明需要进一步检查的方向",
            "- 不要使用代码块包裹，直接输出Markdown文本"
        ])
        
        return "\n".join(prompt_parts)
    
    async def close(self):
        """关闭客户端"""
        if self.ernie_client and hasattr(self.ernie_client, 'client'):
            await self.ernie_client.client.aclose()
