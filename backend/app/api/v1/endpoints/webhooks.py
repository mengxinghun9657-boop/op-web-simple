"""
Webhook 管理 API
"""
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.alert import WebhookConfig
from app.schemas.response import APIResponse
from app.schemas.alert.webhook import (
    WebhookConfigCreate,
    WebhookConfigUpdate,
    WebhookConfigResponse
)

import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks", response_model=APIResponse)
async def get_webhooks(db: Session = Depends(get_db)):
    """获取Webhook配置列表"""
    try:
        webhooks = db.query(WebhookConfig).all()
        webhook_list = [WebhookConfigResponse.from_orm(w) for w in webhooks]
        
        return APIResponse(
            success=True,
            data={"list": [w.dict() for w in webhook_list]},
            message="获取成功"
        )
    except Exception as e:
        logger.error(f"获取Webhook列表失败: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            message="获取Webhook列表失败"
        )


@router.post("/webhooks", response_model=APIResponse)
async def create_webhook(
    webhook: WebhookConfigCreate,
    db: Session = Depends(get_db)
):
    """创建Webhook配置"""
    try:
        # 创建配置
        db_webhook = WebhookConfig(**webhook.dict())
        db.add(db_webhook)
        db.commit()
        db.refresh(db_webhook)
        
        webhook_data = WebhookConfigResponse.from_orm(db_webhook)
        
        return APIResponse(
            success=True,
            data=webhook_data.dict(),
            message="Webhook创建成功"
        )
    except Exception as e:
        logger.error(f"创建Webhook失败: {e}")
        db.rollback()
        return APIResponse(
            success=False,
            error=str(e),
            message="创建Webhook失败"
        )


@router.put("/webhooks/{webhook_id}", response_model=APIResponse)
async def update_webhook(
    webhook_id: int,
    webhook: WebhookConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新Webhook配置"""
    try:
        db_webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id
        ).first()
        
        if not db_webhook:
            return APIResponse(
                success=False,
                error="Webhook不存在",
                message=f"未找到ID为 {webhook_id} 的Webhook"
            )
        
        # 更新字段
        update_data = webhook.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_webhook, field, value)
        
        db.commit()
        db.refresh(db_webhook)
        
        webhook_data = WebhookConfigResponse.from_orm(db_webhook)
        
        return APIResponse(
            success=True,
            data=webhook_data.dict(),
            message="Webhook更新成功"
        )
    except Exception as e:
        logger.error(f"更新Webhook失败: {e}")
        db.rollback()
        return APIResponse(
            success=False,
            error=str(e),
            message="更新Webhook失败"
        )


@router.delete("/webhooks/{webhook_id}", response_model=APIResponse)
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db)
):
    """删除Webhook配置"""
    try:
        db_webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id
        ).first()
        
        if not db_webhook:
            return APIResponse(
                success=False,
                error="Webhook不存在",
                message=f"未找到ID为 {webhook_id} 的Webhook"
            )
        
        db.delete(db_webhook)
        db.commit()
        
        return APIResponse(
            success=True,
            data={"id": webhook_id},
            message="Webhook删除成功"
        )
    except Exception as e:
        logger.error(f"删除Webhook失败: {e}")
        db.rollback()
        return APIResponse(
            success=False,
            error=str(e),
            message="删除Webhook失败"
        )


@router.post("/webhooks/{webhook_id}/test", response_model=APIResponse)
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db)
):
    """测试Webhook连接"""
    try:
        db_webhook = db.query(WebhookConfig).filter(
            WebhookConfig.id == webhook_id
        ).first()
        
        if not db_webhook:
            return APIResponse(
                success=False,
                error="Webhook不存在",
                message=f"未找到ID为 {webhook_id} 的Webhook"
            )
        
        # 根据webhook类型构建不同的测试消息
        if db_webhook.type == 'feishu':
            # 飞书测试消息（包含"告警"关键词，避免关键词验证失败）
            test_message = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "测试告警 - Webhook配置测试"  # 包含"告警"关键词
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": "**测试消息**\n这是一条测试消息，Webhook配置正常\n\n**测试时间**: " + 
                                          time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        }
                    ]
                }
            }
            
            # 如果配置了签名密钥，添加签名
            if db_webhook.secret:
                import hmac
                import hashlib
                import base64
                
                timestamp = int(time.time())
                string_to_sign = f'{timestamp}\n{db_webhook.secret}'
                hmac_code = hmac.new(
                    string_to_sign.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).digest()
                sign = base64.b64encode(hmac_code).decode('utf-8')
                
                test_message['timestamp'] = timestamp
                test_message['sign'] = sign
                
        elif db_webhook.type == 'ruliu':
            # 如流测试消息
            test_message = {
                "message": {
                    "header": {
                        "toid": int(db_webhook.group_id) if db_webhook.group_id else 0,
                        "totype": "GROUP",
                        "msgtype": "MD",
                        "clientmsgid": int(time.time() * 1000),
                        "role": "robot"
                    },
                    "body": [
                        {
                            "type": "MD",
                            "content": f"##### 【测试告警】Webhook配置测试\n\n**测试消息**: 这是一条测试消息，Webhook配置正常\n\n**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            }
        else:
            # 其他类型使用简单文本消息
            test_message = {
                "msg_type": "text",
                "content": {
                    "text": "这是一条测试消息,Webhook配置正常"
                }
            }
        
        # 发送测试请求
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(db_webhook.url, json=test_message)
            response_time = int((time.time() - start_time) * 1000)
            
            # 解析响应
            try:
                response_data = response.json()
            except:
                response_data = {"raw": response.text}
            
            if response.status_code == 200:
                # 检查飞书/如流的响应格式
                if db_webhook.type == 'feishu':
                    # 飞书返回格式: {"code": 0, "msg": "success"} 或 {"code": 19024, "msg": "Key Words Not Found"}
                    if response_data.get('code') == 0:
                        return APIResponse(
                            success=True,
                            data={
                                "status": "success",
                                "response_time": response_time,
                                "status_code": response.status_code,
                                "response": response_data
                            },
                            message="飞书Webhook测试成功"
                        )
                    else:
                        error_msg = response_data.get('msg', '未知错误')
                        return APIResponse(
                            success=False,
                            error=f"飞书返回错误: {error_msg}",
                            data={"response": response_data},
                            message=f"飞书Webhook测试失败: {error_msg}"
                        )
                elif db_webhook.type == 'ruliu':
                    # 如流返回格式: {"errcode": 0, "errmsg": "ok"}
                    if response_data.get('errcode') == 0:
                        return APIResponse(
                            success=True,
                            data={
                                "status": "success",
                                "response_time": response_time,
                                "status_code": response.status_code,
                                "response": response_data
                            },
                            message="如流Webhook测试成功"
                        )
                    else:
                        error_msg = response_data.get('errmsg', '未知错误')
                        return APIResponse(
                            success=False,
                            error=f"如流返回错误: {error_msg}",
                            data={"response": response_data},
                            message=f"如流Webhook测试失败: {error_msg}"
                        )
                else:
                    return APIResponse(
                        success=True,
                        data={
                            "status": "success",
                            "response_time": response_time,
                            "status_code": response.status_code,
                            "response": response_data
                        },
                        message="Webhook测试成功"
                    )
            else:
                return APIResponse(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    data={"response": response_data},
                    message="Webhook测试失败"
                )
                
    except httpx.TimeoutException:
        return APIResponse(
            success=False,
            error="请求超时",
            message="Webhook测试超时（10秒）"
        )
    except Exception as e:
        logger.error(f"测试Webhook失败: {e}", exc_info=True)
        return APIResponse(
            success=False,
            error=str(e),
            message="测试Webhook失败"
        )
