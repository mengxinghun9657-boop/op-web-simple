#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HAS 硬件告警 Webhook 接口

接收客户服务器上 HAS Agent 推送的硬件告警信息
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from app.core.database import get_db_connection
from app.core.logger import logger
import json
import os

router = APIRouter()


@router.post("/has/webhook")
async def receive_has_alert(request: Request):
    """
    接收 HAS 告警 webhook
    
    HAS 会发送 JSON 格式的告警数据：
    {
        "hostname": "gpu-server-01",
        "alert_type": "GPU_ERROR",
        "severity": "critical",
        "message": "GPU 0 温度过高: 95°C",
        "timestamp": "2026-02-03T12:00:00Z",
        "details": {
            "gpu_id": 0,
            "temperature": 95,
            "threshold": 85
        }
    }
    """
    try:
        # 解析请求体
        alert_data = await request.json()
        
        logger.info(f"📨 收到 HAS 告警: {alert_data.get('hostname')} - {alert_data.get('alert_type')}")
        
        # 验证必需字段
        required_fields = ['hostname', 'alert_type', 'severity', 'message']
        for field in required_fields:
            if field not in alert_data:
                raise HTTPException(status_code=400, detail=f"缺少必需字段: {field}")
        
        # 验证 severity 值
        valid_severities = ['critical', 'warning', 'info']
        if alert_data['severity'] not in valid_severities:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的 severity 值: {alert_data['severity']}，必须是 {valid_severities} 之一"
            )
        
        # 存储到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO has_alerts
            (hostname, alert_type, severity, message, alert_time, details, received_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            alert_data['hostname'],
            alert_data['alert_type'],
            alert_data['severity'],
            alert_data['message'],
            alert_data.get('timestamp', datetime.now().isoformat()),
            json.dumps(alert_data.get('details', {}), ensure_ascii=False)
        ))
        
        alert_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ HAS 告警已保存: ID={alert_id}, hostname={alert_data['hostname']}")
        
        # 可选：转发到如流（用于实时通知）
        try:
            await forward_to_ruliu(alert_data)
        except Exception as e:
            logger.warning(f"⚠️ 转发到如流失败（不影响告警保存）: {e}")
        
        return {
            "success": True,
            "message": "告警已接收",
            "alert_id": alert_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理 HAS 告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def forward_to_ruliu(alert_data: dict):
    """
    转发告警到如流（可选）
    
    参考 gpu_monitoring/gpu_monitor.py 中的实现
    """
    try:
        import httpx
        
        ruliu_webhook = os.getenv("RULIU_WEBHOOK_URL")
        group_id_str = os.getenv("RULIU_GROUP_ID", "0")
        
        if not ruliu_webhook or not group_id_str or group_id_str == "0":
            logger.debug("如流 webhook 未配置，跳过转发")
            return
        
        try:
            group_id = int(group_id_str)
        except ValueError:
            logger.error(f"无效的 RULIU_GROUP_ID: {group_id_str}")
            return
        
        # 格式化消息
        severity_emoji = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵"
        }
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 构建详细信息
        details_text = ""
        if alert_data.get('details'):
            details_text = "\n\n**详细信息**:\n"
            for key, value in alert_data['details'].items():
                details_text += f"  - {key}: {value}\n"
        
        message = f"""🚨 HAS 硬件告警 [{timestamp}]
{'='*30}

{severity_emoji.get(alert_data['severity'], '⚪')} **{alert_data['alert_type']}**

**服务器**: {alert_data['hostname']}
**严重程度**: {alert_data['severity']}
**告警信息**: {alert_data['message']}
**时间**: {alert_data.get('timestamp', 'N/A')}{details_text}
{'='*30}"""
        
        # 如流 webhook 格式（参考 gpu_monitoring）
        robot_payload = {
            "message": {
                "header": {
                    "toid": [group_id]
                },
                "body": [
                    {
                        "type": "TEXT",
                        "content": message
                    }
                ]
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ruliu_webhook,
                json=robot_payload,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('errcode') == 0:
                    fail_data = response_data.get('data', {}).get('fail', {})
                    if fail_data:
                        logger.error(f"❌ 如流发送失败: {fail_data}")
                    else:
                        logger.info("✅ 告警已转发到如流")
                else:
                    logger.error(f"如流API错误: {response_data}")
            else:
                logger.error(f"如流HTTP失败: {response.status_code}")
        
    except Exception as e:
        logger.warning(f"⚠️ 转发到如流失败: {e}")
        raise


@router.get("/has/webhook/test")
async def test_webhook():
    """
    测试 webhook 接口是否正常工作
    """
    return {
        "success": True,
        "message": "HAS Webhook 接口正常",
        "timestamp": datetime.now().isoformat()
    }
