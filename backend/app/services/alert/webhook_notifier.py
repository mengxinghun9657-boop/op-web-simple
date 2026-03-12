"""
Webhook 通知服务
支持如流和飞书通知
"""
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import httpx
from sqlalchemy.orm import Session
from loguru import logger

from app.models.alert import WebhookConfig, AlertRecord, DiagnosisResult
from app.core.config_alert import settings


class WebhookNotifier:
    """Webhook 通知服务"""
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.retry_times = settings.WEBHOOK_RETRY_TIMES
        self.redis_client = redis_client
        
        # 如果未传入Redis客户端，尝试获取
        if not self.redis_client:
            try:
                from app.core.redis_client import get_redis_client
                self.redis_client = get_redis_client()
            except Exception as e:
                logger.warning(f"无法获取Redis客户端，节点级通知去重将被禁用: {str(e)}")
    
    def _try_acquire_node_notification_lock(self, alert: AlertRecord) -> bool:
        """
        尝试获取节点级通知锁（15分钟窗口）
        
        Args:
            alert: 告警记录
            
        Returns:
            True: 获取锁成功，可以发送通知
            False: 锁已被占用，跳过通知（15分钟内已发送过）
        """
        if not self.redis_client:
            # Redis不可用时，允许发送（降级策略）
            return True
        
        try:
            # 构造节点级锁键：cluster_id + ip（或仅ip）
            if alert.cluster_id:
                lock_key = f"alert:node_notification_lock:{alert.cluster_id}:{alert.ip}"
            else:
                lock_key = f"alert:node_notification_lock:{alert.ip}"
            
            # 尝试获取锁（15分钟 = 900秒）
            acquired = self.redis_client.set(lock_key, "1", nx=True, ex=900)
            
            if acquired:
                logger.info(f"✅ 获取节点通知锁成功: {lock_key}")
                return True
            else:
                logger.info(f"⏭️ 节点通知锁已存在，跳过通知: {lock_key}（15分钟内已发送过）")
                return False
                
        except Exception as e:
            logger.warning(f"Redis锁检查失败，允许发送通知（降级策略）: {str(e)}")
            return True
    
    async def send_alert_notification(
        self, 
        alert: AlertRecord, 
        diagnosis: Optional[DiagnosisResult] = None
    ) -> bool:
        """
        发送告警通知（分段发送：基础信息 + AI解读）
        
        Args:
            alert: 告警记录
            diagnosis: 诊断结果（可选）
            
        Returns:
            是否发送成功
        """
        # 🔒 检查是否已发送通知（防止重复发送）
        if diagnosis and diagnosis.notified:
            logger.info(f"⏭️ 跳过通知: 诊断ID={diagnosis.id}, 告警ID={alert.id}, 已在 {diagnosis.notified_at} 发送过通知")
            return True
        
        # 🔒 节点级通知去重（15分钟窗口）
        if not self._try_acquire_node_notification_lock(alert):
            logger.info(f"⏭️ 跳过通知: 节点 {alert.cluster_id or 'physical'}:{alert.ip} 在15分钟内已发送过通知")
            # 虽然跳过通知，但仍标记为已通知（避免后续重复尝试）
            if diagnosis:
                try:
                    from datetime import datetime
                    diagnosis.notified = True
                    diagnosis.notified_at = datetime.now()
                    self.db.commit()
                except Exception as e:
                    logger.error(f"更新通知状态失败: {str(e)}")
                    self.db.rollback()
            return True
        
        # 获取启用的 Webhook 配置
        webhooks = self.db.query(WebhookConfig).filter(
            WebhookConfig.enabled == True
        ).all()
        
        if not webhooks:
            logger.info("没有启用的 Webhook 配置")
            return False
        
        success_count = 0
        
        for webhook in webhooks:
            # 检查过滤条件
            if not self._should_notify(webhook, alert):
                logger.debug(f"告警不满足 Webhook 过滤条件: {webhook.name}")
                continue
            
            # 发送通知（分两条消息）
            try:
                if webhook.type == 'ruliu':
                    # 第一条：基础告警信息和诊断结果
                    result1 = await self._send_ruliu_notification(webhook, alert, diagnosis, include_ai=False)
                    # 第二条：完整AI解读（如果有）
                    result2 = True
                    if diagnosis and diagnosis.ai_interpretation:
                        result2 = await self._send_ruliu_ai_interpretation(webhook, alert, diagnosis)
                    result = result1 and result2
                    
                elif webhook.type == 'feishu':
                    # 第一条：基础告警信息和诊断结果
                    result1 = await self._send_feishu_notification(webhook, alert, diagnosis, include_ai=False)
                    # 第二条：完整AI解读（如果有）
                    result2 = True
                    if diagnosis and diagnosis.ai_interpretation:
                        result2 = await self._send_feishu_ai_interpretation(webhook, alert, diagnosis)
                    result = result1 and result2
                else:
                    logger.warning(f"不支持的 Webhook 类型: {webhook.type}")
                    continue
                
                if result:
                    success_count += 1
                    logger.info(f"通知发送成功: {webhook.name}")
                else:
                    logger.error(f"通知发送失败: {webhook.name}")
                    
            except Exception as e:
                logger.error(f"发送通知异常: {webhook.name}, {str(e)}", exc_info=True)
        
        # 更新通知状态（如果至少有一个通知发送成功）
        if success_count > 0 and diagnosis:
            try:
                from datetime import datetime
                diagnosis.notified = True
                diagnosis.notified_at = datetime.now()
                self.db.commit()
                logger.info(f"✅ 更新通知状态: 诊断ID={diagnosis.id}, 告警ID={diagnosis.alert_id}")
            except Exception as e:
                logger.error(f"更新通知状态失败: {str(e)}", exc_info=True)
                self.db.rollback()
        
        return success_count > 0
    
    def _should_notify(self, webhook: WebhookConfig, alert: AlertRecord) -> bool:
        """
        检查是否应该发送通知
        
        Args:
            webhook: Webhook 配置
            alert: 告警记录
            
        Returns:
            是否应该通知
        """
        # 检查严重程度过滤
        # 注意：前端发送的是 critical/warning/info，需要映射到数据库值 ERROR/FAIL/WARN/GOOD
        if webhook.severity_filter:
            allowed_severities_frontend = [s.strip().lower() for s in webhook.severity_filter.split(',')]
            
            # 映射前端值到数据库值
            allowed_severities_db = set()
            for sev in allowed_severities_frontend:
                if sev == 'critical':
                    allowed_severities_db.add('ERROR')
                elif sev == 'warning':
                    allowed_severities_db.update(['FAIL', 'WARN'])
                elif sev == 'info':
                    allowed_severities_db.add('GOOD')
            
            if alert.severity not in allowed_severities_db:
                return False
        
        # 检查组件过滤
        if webhook.component_filter and alert.component:
            allowed_components = [c.strip() for c in webhook.component_filter.split(',')]
            if alert.component not in allowed_components:
                return False
        
        return True
    
    async def _send_ruliu_notification(
        self, 
        webhook: WebhookConfig, 
        alert: AlertRecord,
        diagnosis: Optional[DiagnosisResult] = None,
        include_ai: bool = True
    ) -> bool:
        """
        发送如流通知（基础告警信息）
        使用如流机器人 API: /api/msg/groupmsgsend
        
        Args:
            webhook: Webhook 配置
            alert: 告警记录
            diagnosis: 诊断结果
            include_ai: 是否包含AI解读（False时只发送基础信息）
            
        Returns:
            是否发送成功
        """
        # 构建如流消息（不包含AI解读）
        message = self._build_ruliu_robot_message(alert, diagnosis, webhook, include_ai=False)
        
        # 如流URL本身已包含access_token，直接使用
        url = webhook.url
        
        # 构建请求头
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 发送请求到如流机器人 API
        return await self._send_webhook_request(url, message, headers)
    
    async def _send_ruliu_ai_interpretation(
        self,
        webhook: WebhookConfig,
        alert: AlertRecord,
        diagnosis: DiagnosisResult
    ) -> bool:
        """
        发送如流AI解读（单独消息）
        
        Args:
            webhook: Webhook 配置
            alert: 告警记录
            diagnosis: 诊断结果
            
        Returns:
            是否发送成功
        """
        import time
        
        # 构建AI解读消息
        content = f"##### 【AI解读】{alert.alert_type}\n\n{diagnosis.ai_interpretation}"
        
        message = {
            "message": {
                "header": {
                    "toid": int(webhook.group_id) if webhook and webhook.group_id else int(settings.RULIU_GROUP_ID or 0),
                    "totype": "GROUP",
                    "msgtype": "MD",
                    "clientmsgid": int(time.time() * 1000),
                    "role": "robot"
                },
                "body": [
                    {
                        "type": "MD",
                        "content": content
                    }
                ]
            }
        }
        
        # 如流URL本身已包含access_token，直接使用
        url = webhook.url
        headers = {'Content-Type': 'application/json'}
        
        # 发送请求
        return await self._send_webhook_request(url, message, headers)
    
    async def _send_feishu_notification(
        self, 
        webhook: WebhookConfig, 
        alert: AlertRecord,
        diagnosis: Optional[DiagnosisResult] = None,
        include_ai: bool = True
    ) -> bool:
        """
        发送飞书通知（基础告警信息）
        
        Args:
            webhook: Webhook 配置
            alert: 告警记录
            diagnosis: 诊断结果
            include_ai: 是否包含AI解读（False时只发送基础信息）
            
        Returns:
            是否发送成功
        """
        # 构建飞书消息（不包含AI解读，传递webhook以获取关键词）
        message = self._build_feishu_message(alert, diagnosis, webhook, include_ai=False)
        
        # 如果配置了签名密钥，添加签名
        if webhook.secret:
            import time
            import hmac
            import hashlib
            import base64
            
            timestamp = int(time.time())
            string_to_sign = f'{timestamp}\n{webhook.secret}'
            hmac_code = hmac.new(
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
            
            message['timestamp'] = timestamp
            message['sign'] = sign
        
        # 发送请求
        return await self._send_webhook_request(webhook.url, message)
    
    async def _send_feishu_ai_interpretation(
        self,
        webhook: WebhookConfig,
        alert: AlertRecord,
        diagnosis: DiagnosisResult
    ) -> bool:
        """
        发送飞书AI解读（单独消息）
        
        Args:
            webhook: Webhook 配置
            alert: 告警记录
            diagnosis: 诊断结果
            
        Returns:
            是否发送成功
        """
        # 构建标题（包含"告警"关键词）
        title = f"硬件告警AI解读 - {alert.alert_type}"
        
        # 构建AI解读消息
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": diagnosis.ai_interpretation
                }
            }
        ]
        
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title  # 标题包含"告警"关键词
                    },
                    "template": "blue"  # 蓝色主题表示信息
                },
                "elements": elements
            }
        }
        
        # 如果配置了签名密钥，添加签名
        if webhook.secret:
            import time
            import hmac
            import hashlib
            import base64
            
            timestamp = int(time.time())
            string_to_sign = f'{timestamp}\n{webhook.secret}'
            hmac_code = hmac.new(
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
            
            message['timestamp'] = timestamp
            message['sign'] = sign
        
        # 发送请求
        return await self._send_webhook_request(webhook.url, message)
    
    def _build_ruliu_robot_message(
        self, 
        alert: AlertRecord,
        diagnosis: Optional[DiagnosisResult] = None,
        webhook: Optional[WebhookConfig] = None,
        include_ai: bool = False
    ) -> Dict[str, Any]:
        """
        构建如流机器人消息格式（基础告警信息，不包含AI解读）
        参考文档：以机器人身份发送消息到群聊
        
        Args:
            alert: 告警记录
            diagnosis: 诊断结果
            webhook: Webhook 配置
            include_ai: 是否包含AI解读（默认False，AI解读单独发送）
            
        Returns:
            如流机器人消息
        """
        import time
        
        # 严重程度颜色映射
        severity_colors = {
            'FAIL': 'red',
            'ERROR': 'orange',
            'WARN': 'yellow',
            'GOOD': 'green'
        }
        
        color = severity_colors.get(alert.severity, 'grey')
        
        # 从alert和raw_data提取附加信息
        raw_data = alert.raw_data or {}
        cluster_id = alert.cluster_id  # 从alert对象获取
        is_cce = cluster_id is not None and cluster_id.startswith('cce-')  # 判断是否CCE
        
        # CCE和物理机的字段不同
        if is_cce:
            # CCE: hostname是节点名称（如cce-xrg955qz-ktg4ihz6），不显示
            hostname = None
        else:
            # 物理机: case_dev_name是主机名
            hostname = raw_data.get('case_dev_name')
        
        error_code = raw_data.get('case_code') or raw_data.get('error_code')
        
        # 从文件名提取IP（如果alert.ip是hostname）
        ip_address = alert.ip
        if alert.file_path and ip_address and not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_address):
            # IP不是标准格式，尝试从文件名提取
            filename = Path(alert.file_path).name
            ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
            match = re.search(ip_pattern, filename)
            if match:
                ip_address = match.group(1)
        
        # 构建 Markdown 消息内容
        content_parts = [
            f"##### 【硬件告警】{alert.alert_type}",
            "",
            f"**严重程度**: <font color=\"{color}\">{alert.severity}</font>",
        ]
        
        # CCE集群信息
        if is_cce and cluster_id:
            content_parts.append(f"**集群ID**: {cluster_id}")
        
        # 主机信息（仅物理机显示）
        if hostname:
            content_parts.append(f"**主机名**: {hostname}")
        
        # 基本信息
        content_parts.append(f"**组件类型**: {alert.component or 'N/A'}")
        content_parts.append(f"**IP地址**: {ip_address or 'N/A'}")
        
        # 错误代码
        if error_code:
            content_parts.append(f"**故障码**: {error_code}")
        
        content_parts.append(f"**告警时间**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 添加诊断结果（不包含AI解读）
        if diagnosis:
            content_parts.append("")
            content_parts.append("**诊断结果**:")
            
            if diagnosis.manual_matched:
                content_parts.append(f"- 手册匹配: {diagnosis.manual_name_zh or '已匹配'}")
                content_parts.append(f"- 危害等级: {diagnosis.danger_level or 'N/A'}")
                if diagnosis.manual_solution:
                    solution = diagnosis.manual_solution[:100] + "..." if len(diagnosis.manual_solution) > 100 else diagnosis.manual_solution
                    content_parts.append(f"- 解决方案: {solution}")
            
            if diagnosis.api_task_id:
                content_parts.append(f"- API诊断: 任务ID {diagnosis.api_task_id}")
                content_parts.append(f"- 诊断状态: {diagnosis.api_status or 'N/A'}")
                # 添加诊断统计和详情
                if diagnosis.api_diagnosis:
                    api_data = diagnosis.api_diagnosis
                    if isinstance(api_data, dict):
                        error_items = api_data.get('error_items', [])
                        warning_items = api_data.get('warning_items', [])
                        
                        # 显示统计
                        error_count = len(error_items) if isinstance(error_items, list) else 0
                        warning_count = len(warning_items) if isinstance(warning_items, list) else 0
                        content_parts.append(f"- 错误项: {error_count}个, 警告项: {warning_count}个")
                        
                        # 显示前3个错误项详情
                        if error_items and isinstance(error_items, list) and len(error_items) > 0:
                            content_parts.append("")
                            content_parts.append("**错误项详情** (前3个):")
                            for i, item in enumerate(error_items[:3], 1):
                                item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                                item_desc = item.get('description', '')
                                # 截断过长的描述
                                if len(item_desc) > 50:
                                    item_desc = item_desc[:50] + "..."
                                content_parts.append(f"{i}. {item_name}")
                                if item_desc:
                                    content_parts.append(f"   {item_desc}")
                        
                        # 显示前3个警告项详情
                        if warning_items and isinstance(warning_items, list) and len(warning_items) > 0:
                            content_parts.append("")
                            content_parts.append("**警告项详情** (前3个):")
                            for i, item in enumerate(warning_items[:3], 1):
                                item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                                item_desc = item.get('description', '')
                                # 截断过长的描述
                                if len(item_desc) > 50:
                                    item_desc = item_desc[:50] + "..."
                                content_parts.append(f"{i}. {item_name}")
                                if item_desc:
                                    content_parts.append(f"   {item_desc}")
        
        # 提示AI解读将单独发送
        if diagnosis and diagnosis.ai_interpretation:
            content_parts.append("")
            content_parts.append("*AI解读将在下一条消息中发送*")
        
        content = "\n".join(content_parts)
        
        # 如流机器人消息格式
        message = {
            "message": {
                "header": {
                    "toid": int(webhook.group_id) if webhook and webhook.group_id else int(settings.RULIU_GROUP_ID or 0),
                    "totype": "GROUP",
                    "msgtype": "MD",
                    "clientmsgid": int(time.time() * 1000),
                    "role": "robot"
                },
                "body": [
                    {
                        "type": "MD",
                        "content": content
                    }
                ]
            }
        }
        
        return message
    
    def _build_feishu_message(
        self, 
        alert: AlertRecord,
        diagnosis: Optional[DiagnosisResult] = None,
        webhook: Optional[WebhookConfig] = None,
        include_ai: bool = False
    ) -> Dict[str, Any]:
        """
        构建飞书消息格式（基础告警信息，不包含AI解读）
        
        Args:
            alert: 告警记录
            diagnosis: 诊断结果
            webhook: Webhook配置（用于获取关键词）
            include_ai: 是否包含AI解读（默认False，AI解读单独发送）
            
        Returns:
            飞书消息
        """
        # 严重程度标签
        severity_tags = {
            'FAIL': '🔴 严重',
            'ERROR': '🟠 错误',
            'WARN': '🟡 警告',
            'GOOD': '🟢 正常'
        }
        
        severity_tag = severity_tags.get(alert.severity, '⚪ 未知')
        
        # 从alert和raw_data提取附加信息
        raw_data = alert.raw_data or {}
        cluster_id = alert.cluster_id  # 从alert对象获取
        is_cce = cluster_id is not None and cluster_id.startswith('cce-')  # 判断是否CCE
        
        # CCE和物理机的字段不同
        if is_cce:
            # CCE: hostname是节点名称（如cce-xrg955qz-ktg4ihz6），不显示
            hostname = None
        else:
            # 物理机: case_dev_name是主机名
            hostname = raw_data.get('case_dev_name')
        
        error_code = raw_data.get('case_code') or raw_data.get('error_code')
        
        # 从文件名提取IP（如果alert.ip是hostname）
        ip_address = alert.ip
        if alert.file_path and ip_address and not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip_address):
            # IP不是标准格式，尝试从文件名提取
            filename = Path(alert.file_path).name
            ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
            match = re.search(ip_pattern, filename)
            if match:
                ip_address = match.group(1)
        
        # 构建标题（必须包含"告警"关键词，飞书会检查header.title）
        title = f"硬件告警 - {alert.alert_type}"
        
        # 构建富文本内容（不再需要在elements中显示标题，header会显示）
        elements = [
            {
                "tag": "hr"
            }
        ]
        
        # 基本信息字段
        fields = [
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**严重程度**\n{severity_tag}"
                }
            }
        ]
        
        # CCE集群ID
        if is_cce and cluster_id:
            fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**集群ID**\n{cluster_id}"
                }
            })
        
        # 主机名（仅物理机显示）
        if hostname:
            fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**主机名**\n{hostname}"
                }
            })
        
        # 组件和IP
        fields.extend([
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**组件类型**\n{alert.component or 'N/A'}"
                }
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**IP地址**\n{ip_address or 'N/A'}"
                }
            }
        ])
        
        # 错误代码
        if error_code:
            fields.append({
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**故障码**\n{error_code}"
                }
            })
        
        # 告警时间
        fields.append({
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**告警时间**\n{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            }
        })
        
        elements.append({
            "tag": "div",
            "fields": fields
        })
        
        # 添加诊断结果
        if diagnosis and diagnosis.manual_matched:
            elements.append({
                "tag": "hr"
            })
            
            diagnosis_content = f"**诊断结果**\n{diagnosis.manual_name_zh or '已匹配'}"
            if diagnosis.danger_level:
                diagnosis_content += f"\n危害等级: {diagnosis.danger_level}"
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": diagnosis_content
                }
            })
        
        # 添加API诊断结果
        if diagnosis and diagnosis.api_task_id:
            api_content = f"**API诊断结果**\n任务ID: {diagnosis.api_task_id}\n诊断状态: {diagnosis.api_status or 'N/A'}"
            
            # 添加诊断统计和详情
            if diagnosis.api_diagnosis:
                api_data = diagnosis.api_diagnosis
                if isinstance(api_data, dict):
                    error_items = api_data.get('error_items', [])
                    warning_items = api_data.get('warning_items', [])
                    
                    # 显示统计
                    error_count = len(error_items) if isinstance(error_items, list) else 0
                    warning_count = len(warning_items) if isinstance(warning_items, list) else 0
                    api_content += f"\n错误项: {error_count}个, 警告项: {warning_count}个"
                    
                    # 显示前3个错误项详情
                    if error_items and isinstance(error_items, list) and len(error_items) > 0:
                        api_content += "\n\n**错误项详情** (前3个):"
                        for i, item in enumerate(error_items[:3], 1):
                            item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                            item_desc = item.get('description', '')
                            # 截断过长的描述
                            if len(item_desc) > 50:
                                item_desc = item_desc[:50] + "..."
                            api_content += f"\n{i}. {item_name}"
                            if item_desc:
                                api_content += f"\n   {item_desc}"
                    
                    # 显示前3个警告项详情
                    if warning_items and isinstance(warning_items, list) and len(warning_items) > 0:
                        api_content += "\n\n**警告项详情** (前3个):"
                        for i, item in enumerate(warning_items[:3], 1):
                            item_name = item.get('item_name_zh') or item.get('item_name', 'N/A')
                            item_desc = item.get('description', '')
                            # 截断过长的描述
                            if len(item_desc) > 50:
                                item_desc = item_desc[:50] + "..."
                            api_content += f"\n{i}. {item_name}"
                            if item_desc:
                                api_content += f"\n   {item_desc}"
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": api_content
                }
            })
        
        # 提示AI解读将单独发送（不包含AI解读内容）
        if diagnosis and diagnosis.ai_interpretation and not include_ai:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "*AI解读将在下一条消息中发送*"
                }
            })
        
        # 飞书消息格式（使用header确保关键词在标题中）
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title  # 标题包含"告警"关键词
                    },
                    "template": "red"  # 红色主题表示告警
                },
                "elements": elements
            }
        }
        
        return message
    
    async def _send_webhook_request(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] = None) -> bool:
        """
        发送 Webhook 请求（带重试，支持代理）
        
        Args:
            url: Webhook URL
            payload: 消息内容
            headers: 请求头
            
        Returns:
            是否发送成功
        """
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        for attempt in range(self.retry_times):
            try:
                # 创建httpx客户端（自动使用环境变量中的代理配置）
                # httpx会自动读取 HTTP_PROXY, HTTPS_PROXY, NO_PROXY 环境变量
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=True) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        # 检查响应格式
                        try:
                            result = response.json()
                            
                            # 飞书 API 返回格式: {"code": 0, "msg": "success", "data": {}}
                            # 错误格式: {"code": 19024, "msg": "Key Words Not Found", "data": {}}
                            if 'code' in result:
                                if result.get('code') == 0:
                                    logger.info(f"✅ 飞书Webhook发送成功: {url}")
                                    return True
                                else:
                                    error_code = result.get('code')
                                    error_msg = result.get('msg', '未知错误')
                                    logger.error(f"❌ 飞书Webhook发送失败: code={error_code}, msg={error_msg}")
                                    logger.error(f"   URL: {url}")
                                    logger.error(f"   Payload: {payload}")
                                    return False
                            
                            # 如流 API 返回格式: {"errcode": 0, "errmsg": "ok", ...}
                            elif 'errcode' in result:
                                if result.get('errcode') == 0:
                                    logger.info(f"✅ 如流Webhook发送成功: {url}")
                                    return True
                                else:
                                    error_code = result.get('errcode')
                                    error_msg = result.get('errmsg', '未知错误')
                                    logger.error(f"❌ 如流Webhook发送失败: errcode={error_code}, errmsg={error_msg}")
                                    return False
                            
                            # 其他格式
                            elif result.get('StatusCode') == 0:
                                logger.info(f"✅ Webhook发送成功: {url}")
                                return True
                            else:
                                logger.warning(f"⚠️ Webhook响应格式未知: {result}")
                                return False
                                
                        except Exception as e:
                            # 非 JSON 响应，认为成功
                            logger.info(f"✅ Webhook发送成功（非JSON响应）: {url}")
                            return True
                    else:
                        logger.warning(f"⚠️ Webhook发送失败 (尝试 {attempt + 1}/{self.retry_times}): HTTP {response.status_code}")
                        logger.warning(f"   响应内容: {response.text[:200]}")
                        
            except httpx.TimeoutException:
                logger.error(f"⏱️ Webhook请求超时 (尝试 {attempt + 1}/{self.retry_times}): {url}")
            except Exception as e:
                logger.error(f"❌ Webhook请求异常 (尝试 {attempt + 1}/{self.retry_times}): {str(e)}")
        
        logger.error(f"❌ Webhook发送最终失败（已重试{self.retry_times}次）: {url}")
        return False
