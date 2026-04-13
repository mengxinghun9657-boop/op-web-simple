#!/usr/bin/env python3
"""
如流/飞书 Webhook 发送服务
复用项目中 webhook_notifier.py 的核心逻辑
支持多平台：如流、飞书
"""
import os
import sys
import json
import time
import hmac
import hashlib
import base64
import logging
import glob
from datetime import datetime
from typing import Dict, Any, Optional

import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/ruliu-callback/webhook_sender.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 配置
RESULTS_DIR = '/var/log/ruliu-callback/results'
CHECK_INTERVAL = 5  # 检查间隔（秒）


class WebhookSender:
    """Webhook发送器基类"""
    
    def send(self, result_data: Dict[str, Any]) -> bool:
        """发送消息，子类实现"""
        raise NotImplementedError


class RuliuSender(WebhookSender):
    """如流发送器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, result_data: Dict[str, Any]) -> bool:
        """发送如流消息"""
        try:
            group_id = result_data.get('group_id')
            content = result_data.get('content', '')
            from_user = result_data.get('from_user')
            
            if not group_id or not content:
                logger.warning("如流消息数据不完整")
                return False
            
            # 添加@用户前缀
            if from_user:
                content = f"@{from_user}\n\n{content}"
            
            # 构建如流消息格式
            message = {
                "message": {
                    "header": {
                        "toid": int(group_id),
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
            
            # 发送请求
            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.webhook_url, json=message, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0 or result.get('code') == 'ok':
                    logger.info(f"✅ 如流消息发送成功: group_id={group_id}")
                    return True
                else:
                    logger.error(f"❌ 如流消息发送失败: {result}")
                    return False
            else:
                logger.error(f"❌ 如流请求失败: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送如流消息异常: {e}", exc_info=True)
            return False


class FeishuSender(WebhookSender):
    """飞书发送器 - 复用项目中的核心逻辑，支持多种消息类型"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_sign(self) -> tuple:
        """生成飞书签名 - 复用项目逻辑"""
        if not self.secret:
            return None, None
        
        timestamp = int(time.time())
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return timestamp, sign
    
    def _build_feishu_text_message(self, content: str, at_users: list = None, at_all: bool = False) -> Dict[str, Any]:
        """
        构建飞书文本消息格式
        支持 @ 功能
        """
        # 构建 @ 标签
        at_text = ""
        if at_users:
            for user_id, name in at_users:
                at_text += f'<at user_id="{user_id}">{name}</at> '
        if at_all:
            at_text += '<at user_id="all">所有人</at> '
        
        message = {
            "msg_type": "text",
            "content": {
                "text": at_text + content if at_text else content
            }
        }
        
        return message
    
    def _build_feishu_card_message(self, title: str, content: str, at_users: list = None, at_all: bool = False) -> Dict[str, Any]:
        """
        构建飞书卡片消息格式 - 复用项目中的 _build_feishu_message 逻辑
        使用 interactive 卡片格式，支持 Markdown 和 @ 功能
        """
        # 构建 @ 标签（卡片中使用不同的格式）
        at_text = ""
        if at_users:
            for user_id, name in at_users:
                at_text += f'<at id="{user_id}"></at> '
        if at_all:
            at_text += '<at id="all"></at> '
        
        # 构建富文本内容
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": at_text + content if at_text else content
                }
            }
        ]
        
        # 飞书消息格式（使用header确保关键词在标题中）
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"  # 蓝色主题
                },
                "elements": elements
            }
        }
        
        return message
    
    def send(self, result_data: Dict[str, Any]) -> bool:
        """发送飞书消息"""
        try:
            content = result_data.get('content', '')
            from_user = result_data.get('from_user')
            msg_type = result_data.get('msg_type', 'interactive')  # 默认卡片消息
            title = result_data.get('title', '硬件告警助手')
            at_users = result_data.get('at_users', [])
            at_all = result_data.get('at_all', False)
            
            if not content:
                logger.warning("飞书消息内容为空")
                return False
            
            # 根据消息类型构建不同格式的消息
            if msg_type == 'text':
                # 文本消息
                message = self._build_feishu_text_message(content, at_users, at_all)
            else:
                # 默认卡片消息
                message = self._build_feishu_card_message(title, content, at_users, at_all)
            
            # 如果配置了签名密钥，添加签名 - 复用项目逻辑
            if self.secret:
                timestamp, sign = self._generate_sign()
                if timestamp and sign:
                    message['timestamp'] = timestamp
                    message['sign'] = sign
            
            # 发送请求
            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.webhook_url, json=message, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # 飞书 API 返回格式: {"code": 0, "msg": "success", "data": {}}
                if result.get('code') == 0:
                    logger.info(f"✅ 飞书消息发送成功")
                    return True
                else:
                    error_code = result.get('code')
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"❌ 飞书消息发送失败: code={error_code}, msg={error_msg}")
                    return False
            else:
                logger.error(f"❌ 飞书请求失败: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送飞书消息异常: {e}", exc_info=True)
            return False


def get_sender(platform: str) -> Optional[WebhookSender]:
    """
    根据平台获取对应的发送器
    
    Args:
        platform: 平台类型 ('ruliu' 或 'feishu')
    
    Returns:
        WebhookSender 实例或 None
    """
    platform = platform.lower()
    
    if platform == 'ruliu':
        webhook_url = os.getenv('WEBHOOK_URL', '')
        if not webhook_url:
            logger.error("❌ 如流 WEBHOOK_URL 环境变量未设置")
            return None
        return RuliuSender(webhook_url)
    
    elif platform == 'feishu':
        webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '')
        secret = os.getenv('FEISHU_SECRET', None)  # 飞书签名密钥（可选）
        if not webhook_url:
            logger.error("❌ 飞书 FEISHU_WEBHOOK_URL 环境变量未设置")
            return None
        return FeishuSender(webhook_url, secret)
    
    else:
        logger.error(f"❌ 不支持的平台类型: {platform}")
        return None


def process_result_file(file_path: str) -> bool:
    """
    处理单个结果文件
    支持多平台：根据文件中的 platform 字段选择发送器
    
    Args:
        file_path: 结果文件路径
        
    Returns:
        是否处理成功
    """
    try:
        # 读取结果文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查状态
        if data.get('status') != 'pending':
            return True  # 已处理，跳过
        
        # 获取平台类型（默认如流）
        platform = data.get('platform', 'ruliu')
        
        # 获取对应的发送器
        sender = get_sender(platform)
        if not sender:
            logger.error(f"❌ 无法创建发送器: platform={platform}")
            data['status'] = 'failed'
            data['failed_at'] = datetime.now().isoformat()
            data['error'] = f'不支持的平台类型: {platform}'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return False
        
        # 发送消息
        logger.info(f"正在发送消息: platform={platform}, file={file_path}")
        success = sender.send(data)
        
        if success:
            # 更新状态为已发送
            data['status'] = 'sent'
            data['sent_at'] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 消息发送完成: {file_path}")
            return True
        else:
            # 更新状态为失败
            data['status'] = 'failed'
            data['failed_at'] = datetime.now().isoformat()
            data['retry_count'] = data.get('retry_count', 0) + 1
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.error(f"❌ 消息发送失败: {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"处理结果文件失败: {file_path}, {e}", exc_info=True)
        return False


def clean_old_files():
    """清理已发送的旧文件（保留7天）"""
    try:
        cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7天前
        
        for file_path in glob.glob(f"{RESULTS_DIR}/*.json"):
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"清理旧文件: {file_path}")
            except Exception as e:
                logger.warning(f"清理文件失败: {file_path}, {e}")
                
    except Exception as e:
        logger.error(f"清理旧文件失败: {e}")


def main():
    """主循环"""
    logger.info("=" * 60)
    logger.info("Webhook 发送服务启动 (支持如流/飞书)")
    logger.info("=" * 60)
    
    # 从环境变量读取配置
    ruliu_webhook_url = os.getenv('WEBHOOK_URL', '')
    feishu_webhook_url = os.getenv('FEISHU_WEBHOOK_URL', '')
    feishu_secret = os.getenv('FEISHU_SECRET', '')
    
    logger.info(f"结果目录: {RESULTS_DIR}")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info(f"如流 Webhook: {'已配置' if ruliu_webhook_url else '未配置'}")
    logger.info(f"飞书 Webhook: {'已配置' if feishu_webhook_url else '未配置'}")
    if feishu_secret:
        logger.info(f"飞书签名: 已配置")
    
    # 检查配置（至少配置一个平台）
    if not ruliu_webhook_url and not feishu_webhook_url:
        logger.error("❌ 错误: 至少配置一个 Webhook URL")
        logger.error("请设置: WEBHOOK_URL (如流) 或 FEISHU_WEBHOOK_URL (飞书)")
        sys.exit(1)
    
    # 确保结果目录存在
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    last_clean_time = time.time()
    
    while True:
        try:
            # 查找所有结果文件
            result_files = glob.glob(f"{RESULTS_DIR}/*.json")
            
            if result_files:
                logger.info(f"发现 {len(result_files)} 个结果文件")
                
                # 处理每个文件
                for file_path in sorted(result_files):
                    process_result_file(file_path)
            
            # 定期清理旧文件（每天一次）
            if time.time() - last_clean_time > (24 * 60 * 60):
                clean_old_files()
                last_clean_time = time.time()
            
            # 等待下次检查
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("服务停止")
            break
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
