# 知识库管理二次验证功能文档

## 概述

知识库管理二次验证功能为知识库管理操作提供额外的安全保护层。超级管理员在访问知识库管理功能时，需要重新输入当前用户的登录密码进行二次验证。

## 功能特性

### 1. 密码二次验证
- 超级管理员访问知识库管理时需要重新输入密码
- 密码与 MySQL 中存储的用户密码哈希进行匹配验证
- 验证成功后生成 JWT 会话令牌

### 2. 会话令牌管理
- JWT 令牌有效期：30 分钟
- 令牌存储在 Redis 中，支持快速验证
- 令牌包含用户ID、用户名、令牌类型等信息

### 3. 失败锁定机制
- 连续 5 次密码验证失败后锁定账户
- 锁定时长：30 分钟
- 锁定信息存储在 Redis 中
- 锁定期间无法进行密码验证

### 4. 审计日志
- 记录所有验证成功和失败事件
- 包含用户ID、用户名、IP地址、User Agent等信息
- 存储在 MySQL `ai_audit_logs` 表中

## API 接口

### 1. 验证密码

**接口**: `POST /api/v1/knowledge/auth/verify`

**请求头**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "password": "user_password"
}
```

**成功响应** (200):
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "验证成功",
  "expires_in": 1800,
  "failure_count": 0,
  "locked_until": null
}
```

**失败响应** (401):
```json
{
  "detail": {
    "message": "密码错误，剩余尝试次数: 3",
    "failure_count": 2,
    "locked_until": null,
    "error_code": "INVALID_PASSWORD"
  }
}
```

**锁定响应** (403):
```json
{
  "detail": {
    "message": "账户已锁定，请在 1800 秒后重试",
    "failure_count": 5,
    "locked_until": 1706270730.0,
    "error_code": "ACCOUNT_LOCKED"
  }
}
```

### 2. 注销会话

**接口**: `POST /api/v1/knowledge/auth/logout`

**请求头**:
```
Authorization: Bearer <access_token>
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "注销成功"
}
```

### 3. 获取会话信息

**接口**: `GET /api/v1/knowledge/auth/session`

**请求头**:
```
Authorization: Bearer <access_token>
```

**成功响应** (200):
```json
{
  "user_id": "1",
  "username": "admin",
  "verified_at": 1706269130.0,
  "expires_at": 1706270930.0,
  "remaining_seconds": 1800
}
```

**失败响应** (404):
```json
{
  "detail": "会话不存在或已过期"
}
```

## 使用知识库管理会话令牌

在调用知识库管理相关的 API 时，需要在请求头中包含会话令牌：

```
Authorization: Bearer <access_token>
X-Knowledge-Token: <knowledge_session_token>
```

### 示例：创建知识条目

```python
import requests

# 1. 登录获取 access_token
login_response = requests.post(
    "http://localhost:8000/api/v1/login",
    json={"username": "admin", "password": "admin"}
)
access_token = login_response.json()["access_token"]

# 2. 二次验证获取知识库管理令牌
verify_response = requests.post(
    "http://localhost:8000/api/v1/knowledge/auth/verify",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"password": "admin"}
)
knowledge_token = verify_response.json()["token"]

# 3. 使用两个令牌创建知识条目
create_response = requests.post(
    "http://localhost:8000/api/v1/knowledge/entries",
    headers={
        "Authorization": f"Bearer {access_token}",
        "X-Knowledge-Token": knowledge_token
    },
    json={
        "title": "MySQL 主从同步延迟处理方案",
        "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
        "category": "故障处理",
        "tags": ["MySQL", "主从同步"]
    }
)
```

## 中间件使用

在知识库管理相关的 API 接口中使用 `verify_knowledge_session` 依赖项：

```python
from fastapi import APIRouter, Depends
from app.core.knowledge_auth_middleware import verify_knowledge_session

router = APIRouter()

@router.post("/knowledge/entries")
async def create_entry(
    entry_data: dict,
    session: dict = Depends(verify_knowledge_session),
    db: Session = Depends(get_db)
):
    # session 包含验证后的用户信息
    user_id = session["user_id"]
    username = session["username"]
    
    # 执行知识库操作
    # ...
```

## Redis 数据结构

### 1. 失败计数

**Key**: `auth_failures:{user_id}`

**TTL**: 1800 秒（30 分钟）

**Value**:
```json
{
  "failure_count": 3,
  "locked_until": 1706270730.0
}
```

### 2. 会话令牌

**Key**: `knowledge_session:{user_id}`

**TTL**: 1800 秒（30 分钟）

**Value**:
```json
{
  "user_id": "1",
  "username": "admin",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "verified_at": 1706269130.0,
  "expires_at": 1706270930.0
}
```

## 安全考虑

### 1. 密码验证
- 使用 bcrypt 进行密码哈希验证
- 密码不会以明文形式存储或传输
- 验证失败不会暴露具体原因（用户不存在 vs 密码错误）

### 2. 令牌安全
- JWT 令牌使用 HS256 算法签名
- 令牌包含过期时间，自动失效
- 令牌存储在 Redis 中，支持主动注销

### 3. 失败锁定
- 防止暴力破解攻击
- 锁定信息存储在 Redis 中，重启后仍然有效
- 锁定时间可配置

### 4. 审计日志
- 所有验证操作都记录到审计日志
- 包含 IP 地址和 User Agent，便于追踪
- 日志不可篡改，存储在 MySQL 中

## 配置参数

在 `KnowledgeAuthService` 类中定义的常量：

```python
SESSION_TTL = 1800  # 会话有效期：30 分钟（秒）
MAX_FAILURES = 5  # 最大失败次数
LOCKOUT_DURATION = 1800  # 锁定时长：30 分钟（秒）
JWT_SECRET = settings.SECRET_KEY  # JWT 密钥
JWT_ALGORITHM = "HS256"  # JWT 算法
```

## 错误代码

| 错误代码 | 说明 | HTTP 状态码 |
|---------|------|------------|
| `INVALID_CREDENTIALS` | 用户不存在或密码错误 | 401 |
| `INVALID_PASSWORD` | 密码错误 | 401 |
| `ACCOUNT_LOCKED` | 账户已锁定 | 403 |
| `TOKEN_EXPIRED` | 令牌已过期 | 401 |
| `INVALID_TOKEN` | 无效的令牌 | 401 |
| `INVALID_TOKEN_TYPE` | 令牌类型不匹配 | 401 |
| `SESSION_NOT_FOUND` | 会话不存在 | 401 |
| `TOKEN_MISMATCH` | 令牌不匹配 | 401 |

## 测试

运行测试脚本（需要 MySQL 和 Redis 运行）：

```bash
python3 backend/test_knowledge_auth.py
```

测试内容：
1. 密码验证成功
2. 密码验证失败
3. 密码失败锁定机制
4. 会话令牌验证
5. 会话注销

## 实现文件

- `backend/app/services/ai/knowledge_auth.py` - 认证服务核心逻辑
- `backend/app/api/v1/knowledge_auth.py` - API 接口
- `backend/app/core/knowledge_auth_middleware.py` - 中间件
- `backend/test_knowledge_auth.py` - 测试脚本
- `backend/docs/knowledge_auth.md` - 本文档

## Requirements 验证

| Requirement | 描述 | 实现位置 |
|------------|------|---------|
| 25.1 | 超级管理员首次访问需要密码验证 | `knowledge_auth.py:verify_password()` |
| 25.2 | 提供密码验证接口 | `knowledge_auth.py:POST /verify` |
| 25.3 | 验证密码与 MySQL 哈希匹配 | `knowledge_auth.py:_get_user_password_hash()` |
| 25.4 | 生成 JWT 会话令牌（30分钟） | `knowledge_auth.py:_generate_session_token()` |
| 25.5 | 记录验证失败到审计日志 | `knowledge_auth.py:verify_password()` |
| 25.6 | 5次失败后锁定30分钟 | `knowledge_auth.py:_record_failure()` |
| 25.7 | 令牌过期时要求重新验证 | `knowledge_auth.py:verify_session_token()` |
| 25.8 | 验证请求包含有效令牌 | `knowledge_auth_middleware.py:verify_knowledge_session()` |
| 25.9 | 提供注销接口 | `knowledge_auth.py:POST /logout` |
| 25.10 | 注销时立即失效令牌 | `knowledge_auth.py:logout()` |
| 25.11 | 审计日志包含用户名 | `audit_logger.py:log_auth_verify_*()` |

## 未来改进

1. **MFA 支持**：集成 TOTP 验证码进行多因素认证
2. **SSO 集成**：支持 LDAP/OAuth 等企业级认证
3. **IP 白名单**：限制特定 IP 地址访问知识库管理
4. **设备指纹**：记录和验证设备信息
5. **会话管理**：支持查看和管理所有活跃会话
6. **自适应锁定**：根据风险等级动态调整锁定策略
