# 如流/飞书回调服务

支持如流和飞书双平台的机器人回调服务，复用主项目中 `webhook_notifier.py` 的核心逻辑。

## 架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   如流服务器     │     │   飞书服务器     │     │                 │
│  (用户@机器人)   │     │  (用户@机器人)   │     │                 │
└────────┬────────┘     └────────┬────────┘     │                 │
         │                       │              │   MySQL数据库    │
         ▼                       ▼              │   (告警/CMDB)   │
┌─────────────────────────────────────────┐    │                 │
│         ruliu_callback.py               │◀───┘                 │
│  Flask服务                              │                      │
│  - /ruliu/callback (如流回调接口)        │                      │
│  - /feishu/callback (飞书回调接口)       │                      │
└────────────────────┬────────────────────┘                      │
                     │ 写入结果文件 (.json)                       │
                     ▼                                            │
┌─────────────────────────────────────────┐                      │
│         webhook_sender.py               │──────────────────────┘
│  独立进程                               │      (查询告警/CMDB)
│  - 轮询结果文件目录
│  - 根据 platform 字段选择发送器
│  - 发送到如流/飞书
└─────────────────────────────────────────┘
```

## 配置文件

### 环境变量

创建 `.env` 文件：

```bash
# MySQL配置（查询告警和CMDB）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=cluster_manager

# 如流配置（可选，如果不需要如流可不配置）
RULIU_TOKEN=your_ruliu_token
RULIU_ENCODING_AES_KEY=your_aes_key
RULIU_ACCESS_TOKEN=your_access_token

# 飞书配置（可选，如果不需要飞书可不配置）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx
FEISHU_SECRET=your_feishu_secret  # 可选，用于签名验证

# Webhook发送服务配置
WEBHOOK_URL=http://apiin.im.baidu.com/api/msg/groupmsgsend?access_token=xxx
```

## 安装

```bash
# 安装依赖
pip install flask pymysql requests pycryptodome

# 创建日志目录
sudo mkdir -p /var/log/ruliu-callback/results
sudo chown -R $USER:$USER /var/log/ruliu-callback

# 复制服务文件
sudo cp ruliu_callback.py /opt/ruliu-callback/
sudo cp webhook_sender.py /opt/ruliu-callback/
sudo cp .env /opt/ruliu-callback/
```

## 启动服务

### 方式1：直接启动

```bash
# 终端1：启动回调服务
python ruliu_callback.py

# 终端2：启动发送服务
python webhook_sender.py
```

### 方式2：使用systemd（推荐）

```bash
# 复制systemd服务文件
sudo cp webhook-sender.service /etc/systemd/system/
sudo cp ruliu-callback.service /etc/systemd/system/

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable ruliu-callback webhook-sender
sudo systemctl start ruliu-callback webhook-sender

# 查看状态
sudo systemctl status ruliu-callback
sudo systemctl status webhook-sender
```

## 飞书机器人配置

### 1. 创建飞书机器人

1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 添加机器人能力
4. 获取 **Webhook地址** 和 **签名密钥**（如果启用了签名验证）

### 2. 配置事件订阅

在飞书开放平台 → 事件订阅中配置：

- **请求地址**: `http://your-server:8120/feishu/callback`
- **订阅事件**: `接收消息` (im.message.receive_v1)

### 3. 配置环境变量

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
export FEISHU_SECRET="your_secret"  # 如果启用了签名验证
```

## 如流机器人配置

### 1. 创建如流机器人

1. 打开 [如流开放平台](https://qy.im.baidu.com/)
2. 创建机器人应用
3. 获取 **Token** 和 **EncodingAESKey**

### 2. 配置回调URL

在如流开放平台配置：

- **回调URL**: `http://your-server:8120/ruliu/callback`

### 3. 配置环境变量

```bash
export RULIU_TOKEN="your_token"
export RULIU_ENCODING_AES_KEY="your_aes_key"
export WEBHOOK_URL="http://apiin.im.baidu.com/api/msg/groupmsgsend?access_token=xxx"
```

## 支持的命令

两个平台支持相同的命令：

| 命令 | 说明 | 示例 |
|------|------|------|
| `告警列表` | 查询所有未完成告警 | `@机器人 告警列表` |
| `<IP> 告警列表` | 查询指定IP的今日告警 | `@机器人 10.90.0.189 告警列表` |
| `<IP> 历史告警列表` | 查询指定IP的所有历史告警 | `@机器人 10.90.0.189 历史告警列表` |
| `<查询内容>` | 查询服务器/实例/节点信息 | `@机器人 10.90.0.189` |
| `创建卡片 <级别> <模块> <标题> <内容>` | 创建iCafe卡片 | `@机器人 创建卡片 P0 GPU 服务异常 GPU驱动报错` |
| `帮助` | 显示帮助信息 | `@机器人 帮助` |

## 日志查看

```bash
# 查看回调服务日志
tail -f /var/log/ruliu-callback/ruliu_callback.log

# 查看发送服务日志
tail -f /var/log/ruliu-callback/webhook_sender.log

# 查看结果文件
ls -la /var/log/ruliu-callback/results/
```

## 复用的项目逻辑

### 飞书签名生成

复用 `webhook_notifier.py` 中的 `_generate_sign` 方法：

```python
def _generate_sign(self) -> tuple:
    timestamp = int(time.time())
    string_to_sign = f'{timestamp}\n{self.secret}'
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return timestamp, sign
```

### 飞书消息格式

复用 `webhook_notifier.py` 中的 `interactive` 卡片格式：

```python
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "硬件告警助手"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "消息内容"}
            }
        ]
    }
}
```

## 多平台支持实现

### 结果文件格式

```json
{
    "platform": "feishu",  // 或 "ruliu"
    "group_id": "群ID",
    "from_user": "用户ID",
    "content": "回复内容",
    "timestamp": "2026-04-10T19:05:13",
    "status": "pending"
}
```

### 发送器类设计

```python
class WebhookSender:
    """发送器基类"""
    def send(self, result_data: Dict[str, Any]) -> bool:
        raise NotImplementedError

class RuliuSender(WebhookSender):
    """如流发送器"""
    ...

class FeishuSender(WebhookSender):
    """飞书发送器"""
    ...
```

## 注意事项

1. **签名验证**：飞书支持可选的签名验证，如流必须验证签名
2. **消息格式**：飞书使用 `interactive` 卡片格式，如流使用 `MD` 格式
3. **群ID**：飞书使用 `chat_id`，如流使用 `groupid`
4. **用户ID**：两个平台的用户ID体系不同，但都支持 `@用户` 功能
5. **并发处理**：当前是单线程顺序处理，如需高并发可引入 Celery

## 故障排查

### 飞书消息发送失败

1. 检查 `FEISHU_WEBHOOK_URL` 是否正确
2. 检查是否启用了签名验证（需要配置 `FEISHU_SECRET`）
3. 查看日志：`tail -f /var/log/ruliu-callback/webhook_sender.log`

### 如流消息发送失败

1. 检查 `WEBHOOK_URL` 是否包含正确的 `access_token`
2. 检查 `RULIU_TOKEN` 和 `RULIU_ENCODING_AES_KEY` 是否正确
3. 查看日志：`tail -f /var/log/ruliu-callback/ruliu_callback.log`

### 数据库查询失败

1. 检查MySQL连接配置
2. 确认数据库可访问：`mysql -h localhost -u root -p`
3. 检查表是否存在：`SHOW TABLES;`
