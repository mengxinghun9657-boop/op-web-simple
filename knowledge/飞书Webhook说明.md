# 飞书Webhook使用说明

## 硬件告警诊断系统 - 飞书Webhook使用示例

### 配置说明

在 `.env` 文件中配置飞书Webhook参数：

```bash
# 飞书Webhook配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_token
```

### 获取Webhook URL

1. 在飞书群组中，点击右上角设置
2. 选择"群机器人" > "添加机器人"
3. 选择"自定义机器人"
4. 配置机器人名称和描述
5. **关键词设置**：添加关键词"告警"（必须，否则消息发送失败）
6. 复制生成的Webhook URL

### Python代码示例

```python
import httpx
from typing import Dict, Any

async def send_feishu_notification(
    webhook_url: str,
    alert_type: str,
    severity: str,
    cluster_id: str = None,
    hostname: str = None,
    component: str = None,
    ip_address: str = None,
    timestamp: str = None,
    diagnosis_result: str = None,
    ai_interpretation: str = None
) -> bool:
    """
    发送飞书通知
    
    Args:
        webhook_url: 飞书Webhook URL
        alert_type: 告警类型
        severity: 严重程度
        cluster_id: 集群ID（CCE集群）
        hostname: 主机名（物理机）
        component: 组件类型
        ip_address: IP地址
        timestamp: 告警时间
        diagnosis_result: 诊断结果
        ai_interpretation: AI解读
        
    Returns:
        是否发送成功
    """
    # 严重程度标签
    severity_tags = {
        'FAIL': '🔴 严重',
        'ERROR': '🟠 错误',
        'WARN': '🟡 警告',
        'GOOD': '🟢 正常'
    }
    
    severity_tag = severity_tags.get(severity, '⚪ 未知')
    
    # 构建卡片消息
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**【硬件告警】{alert_type}**"
            }
        },
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
    if cluster_id:
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
    if component:
        fields.append({
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**组件类型**\n{component}"
            }
        })
    
    if ip_address:
        fields.append({
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**IP地址**\n{ip_address}"
            }
        })
    
    # 告警时间
    if timestamp:
        fields.append({
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": f"**告警时间**\n{timestamp}"
            }
        })
    
    elements.append({
        "tag": "div",
        "fields": fields
    })
    
    # 添加诊断结果
    if diagnosis_result:
        elements.append({
            "tag": "hr"
        })
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**诊断结果**\n{diagnosis_result}"
            }
        })
    
    # 添加AI解读摘要
    if ai_interpretation:
        ai_summary = ai_interpretation[:150] + "..." if len(ai_interpretation) > 150 else ai_interpretation
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**AI解读**\n{ai_summary}"
            }
        })
    
    # 添加告警关键词（飞书要求）
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": "告警通知 | 硬件诊断系统"
            }
        ]
    })
    
    # 飞书消息格式
    message = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=message)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    print(f"✅ 飞书通知发送成功")
                    return True
                else:
                    print(f"⚠️ 飞书通知响应异常: {result}")
                    return False
            else:
                print(f"❌ 飞书通知发送失败: {response.status_code}, {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ 飞书通知异常: {str(e)}")
        return False


# 使用示例
async def main():
    # 配置参数
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_token"
    
    # CCE集群告警示例
    success = await send_feishu_notification(
        webhook_url=webhook_url,
        alert_type="GPU带宽下降",
        severity="ERROR",
        cluster_id="cce-xrg955qz",
        component="gpu",
        ip_address="10.90.0.235",
        timestamp="2026-02-10 15:30:00",
        diagnosis_result="手册匹配: GPU带宽下降\n危害等级: 严重\n解决方案: 检查GPU硬件状态,必要时更换GPU",
        ai_interpretation="GPU报告DriverError_EccError_GSPError_Xid错误，初步判定为GPU带宽下降，可能由硬件故障或驱动异常引发。建议重启节点观察是否恢复，必要时更换GPU。"
    )
    
    if success:
        print("CCE集群告警通知发送成功！")
    
    # 物理机告警示例
    success = await send_feishu_notification(
        webhook_url=webhook_url,
        alert_type="ECC内存错误超限",
        severity="FAIL",
        hostname="cdhmlcc001-bbc-cdonlinea-com-1561923",
        component="memory",
        ip_address="10.90.1.23",
        timestamp="2026-02-10 15:35:00",
        diagnosis_result="手册匹配: ECC内存错误超限\n危害等级: 中等\n解决方案: 检查内存模块,必要时更换内存条",
        ai_interpretation="主板检测到内存模块的ECC纠错机制触发次数超过阈值，表明内存存在硬件级错误或稳定性问题。建议立即检查并更换故障内存。"
    )
    
    if success:
        print("物理机告警通知发送成功！")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 消息格式说明

#### 1. 卡片消息结构

飞书卡片消息由以下部分组成：

- **标题区**：显示告警类型
- **分隔线**：`{"tag": "hr"}`
- **字段区**：显示告警详细信息（支持多列布局）
- **诊断结果区**：显示手册匹配和API诊断结果
- **AI解读区**：显示AI分析摘要
- **备注区**：包含"告警"关键词（必须）

#### 2. Markdown语法支持

飞书Markdown支持：

- **粗体**：`**加粗文本**`
- **换行**：使用`\n`
- **链接**：`[链接文本](URL)`

#### 3. 字段布局

```python
# 单列布局
{
    "tag": "div",
    "text": {
        "tag": "lark_md",
        "content": "**标题**\n内容"
    }
}

# 多列布局（is_short: True表示占半列）
{
    "tag": "div",
    "fields": [
        {
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": "**字段1**\n值1"
            }
        },
        {
            "is_short": True,
            "text": {
                "tag": "lark_md",
                "content": "**字段2**\n值2"
            }
        }
    ]
}
```

### 关键词配置

**⚠️ 重要提示**：飞书自定义机器人要求消息中必须包含配置的关键词，否则消息发送失败。

在创建机器人时，必须配置关键词"告警"，并在消息的`note`区域包含该关键词：

```python
{
    "tag": "note",
    "elements": [
        {
            "tag": "plain_text",
            "content": "告警通知 | 硬件诊断系统"  # 包含"告警"关键词
        }
    ]
}
```

### 常见问题

#### Q1: 消息发送失败，返回"关键词校验失败"？

**原因**：消息内容中未包含配置的关键词"告警"

**解决方案**：
1. 确认机器人配置中设置了关键词"告警"
2. 确认消息的`note`区域包含"告警"关键词
3. 或者在消息标题中包含"告警"关键词

#### Q2: 如何测试Webhook是否可用？

```bash
curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_token" \
  -H "Content-Type: application/json" \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "告警测试消息"
    }
  }'
```

#### Q3: 消息格式不正确？

参考飞书官方文档：[自定义机器人使用指南](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)

#### Q4: 如何添加按钮或交互元素？

```python
# 添加按钮
{
    "tag": "action",
    "actions": [
        {
            "tag": "button",
            "text": {
                "tag": "plain_text",
                "content": "查看详情"
            },
            "type": "primary",
            "url": "https://example.com/alert/123"
        }
    ]
}
```

### 测试验证

```bash
# 运行测试脚本
python3 test_webhook_notification.py
```

预期结果：
- ✅ 飞书群组收到卡片式告警通知
- ✅ 消息包含告警类型、严重程度、诊断结果、AI解读等信息
- ✅ 卡片布局清晰，字段对齐
- ✅ 包含"告警"关键词，通过校验

### 参考资料

- [飞书自定义机器人指南](https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN)
- [飞书消息卡片搭建工具](https://open.feishu.cn/tool/cardbuilder)
- [飞书开放平台](https://open.feishu.cn/)
