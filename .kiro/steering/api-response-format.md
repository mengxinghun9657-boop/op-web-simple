---
inclusion: always
---

# API 响应格式统一规范

---

## 【Global Contract - MUST NOT CHANGE】

### ⚠️ 全局不可变契约（最重要）

**这一层是绝对不允许自行修改的东西，违反以下规则视为严重错误！**

#### 1. 统一响应格式（强制）

所有 API Response **必须**统一为：

```json
{
  "success": boolean,
  "data": object | array | null,
  "message": string,
  "error": string | null
}
```

**MUST NOT**:
- ❌ 使用 `code` 字段代替 `success`
- ❌ 使用 `result` 字段代替 `data`
- ❌ 直接返回数组或对象（必须包装在 `data` 中）
- ❌ 混用 `msg` / `message` / `error_message`

#### 2. API 契约不可变规则

API URL、method、request/response schema 一旦定义，后续迭代中：

**MUST**:
- ✅ 只能新增字段
- ✅ 新增可选参数
- ✅ 扩展枚举值

**MUST NOT**:
- ❌ 删除字段
- ❌ 重命名字段
- ❌ 改变字段类型
- ❌ 改变字段语义

**若必须变更**：
- 必须新建版本（`/api/v2/...`）
- 旧版本保持兼容至少 3 个月

#### 3. 前后端分离原则

**Frontend MUST**:
- ✅ 只能通过 API 层访问数据
- ✅ 使用 TypeScript 接口定义 API 响应

**Frontend MUST NOT**:
- ❌ 依赖数据库结构
- ❌ 假设后端内部实现
- ❌ 直接访问后端模型字段

---

## 【API Design Rules】

### API 设计流程（强制执行）

#### 1. 设计先行原则

每新增一个 API，**必须先输出**：

```markdown
## API: 获取用户列表

**Endpoint**: `GET /api/v1/users`

**Request Query**:
```json
{
  "page": 1,           // 页码，默认 1
  "page_size": 20,     // 每页数量，默认 20
  "keyword": "张三"    // 可选，搜索关键词
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "list": [
      {
        "id": 1,
        "username": "zhangsan",
        "email": "zhangsan@example.com",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  },
  "message": "获取成功"
}
```
```

**MUST NOT**:
- ❌ 未输出 schema 前，直接生成前端调用代码
- ❌ 边写边改 API 结构
- ❌ "先实现再补文档"

#### 2. 字段命名规则（强制）

**Backend (Python)**:
- ✅ 使用 `snake_case`
- 示例：`user_id`, `created_at`, `is_active`

**Frontend (JavaScript/TypeScript)**:
- ✅ 使用 `camelCase`
- 示例：`userId`, `createdAt`, `isActive`

**转换规则**:
- 转换**只能**发生在前端 API adapter 层
- 使用统一的转换函数（如 `camelCase()` / `snakeCase()`）

#### 3. 分页接口统一格式

所有分页、列表接口**必须**使用：

```json
{
  "success": true,
  "data": {
    "list": [],           // 数据列表
    "total": 100,         // 总数
    "page": 1,            // 当前页
    "page_size": 20       // 每页数量
  }
}
```

**MUST NOT**:
- ❌ 使用 `items` / `results` / `records` 代替 `list`
- ❌ 使用 `count` / `totalCount` 代替 `total`
- ❌ 直接返回数组

---

## 【Frontend / Backend Responsibility】

### 职责边界（严格划分）

#### Backend 职责

**MUST 在后端实现**:
- ✅ 业务规则验证
- ✅ 权限校验
- ✅ 数据完整性检查
- ✅ 状态机、流程控制
- ✅ 数据持久化

#### Frontend 职责

**MUST 在前端实现**:
- ✅ 展示逻辑
- ✅ 表单校验（仅用于用户体验，不作为安全保障）
- ✅ 状态管理（UI 状态）
- ✅ API 编排（不包含业务判断）

#### 禁止行为

**MUST NOT**:
- ❌ 在前端实现核心业务判断（如：订单是否可以取消）
- ❌ 在后端返回"为了方便前端"的临时字段
- ❌ 在前端绕过 API 直接操作数据
- ❌ 在后端返回 HTML 片段（除非是富文本内容）

---

## 【Evolution Rules】

### 演进与扩展规则

#### 1. 新需求实现原则

**优先通过以下方式实现**:
- ✅ 新增字段（向后兼容）
- ✅ 新增 endpoint
- ✅ 新增配置项

**示例**：
```python
# ✅ 正确：新增可选字段
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar: Optional[str] = None  # 新增字段
```

#### 2. 禁止的实现方式

**MUST NOT 通过以下方式实现**:
- ❌ 修改旧字段语义
- ❌ 改变旧接口返回结构
- ❌ 复用字段表示不同含义

**反例**：
```python
# ❌ 错误：改变字段语义
# 旧：status 表示用户状态（active/inactive）
# 新：status 表示订单状态（pending/completed）
```

#### 3. 变更前置检查

Agent 在实现新需求前，**必须先判断**：

```markdown
## 变更影响分析

- [ ] 是否影响已有 API？
- [ ] 是否破坏向后兼容？
- [ ] 是否需要数据迁移？
- [ ] 前端是否需要同步修改？

**结论**: [明确说明影响范围]
```

---

## 【Work Flow】

### 实现流程（严格按顺序）

实现任何功能时，**严格按顺序输出**：

#### Step 1: 需求理解
用一句话描述需求：
```
实现用户列表查询功能，支持分页和关键词搜索
```

#### Step 2: API 设计
输出完整的 API schema + 示例（见上文 API Design Rules）

#### Step 3: 后端实现
```python
@router.get("/users")
async def get_users(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 实现代码
    pass
```

#### Step 4: 前端调用示例
```typescript
// API 定义
export const getUsers = (params: {
  page: number
  pageSize: number
  keyword?: string
}) => {
  return axios.get('/api/v1/users', { params })
}

// 使用
const response = await getUsers({ page: 1, pageSize: 20 })
console.log(response.data.list)
```

#### Step 5: 联调注意点 / 风险
```markdown
## 联调注意点
1. 确认分页参数是否正确传递
2. 验证空列表时的返回格式
3. 测试关键词搜索的特殊字符处理

## 潜在风险
- 大数据量时的性能问题（建议限制 page_size 最大值）
```

**MUST NOT**:
- ❌ 跳过任何步骤
- ❌ 步骤顺序颠倒
- ❌ 省略 API 设计直接写代码

---

## 问题背景

在项目开发过程中，由于缺乏统一的 API 响应格式规范，导致前后端数据结构不一致，出现以下问题：

1. **前端代码冗余**：大量 `response.data || response` 的兼容代码
2. **状态判断不一致**：有些用 `success`，有些用 `status`，有些没有状态字段
3. **错误处理困难**：错误信息格式不统一，难以统一处理
4. **维护成本高**：每个 API 都需要单独处理响应格式

## 统一响应格式规范（详细说明）

### 1. 标准响应格式

**所有 API 接口必须使用以下统一格式**：

```python
{
    "success": bool,      # 必需：操作是否成功
    "data": Any,          # 可选：返回的数据
    "message": str,       # 可选：提示信息
    "error": str          # 可选：错误信息（仅在 success=false 时）
}
```

### 2. Pydantic 响应模型

**后端必须定义统一的响应基类**：

```python
# backend/app/schemas/response.py
from typing import Any, Optional
from pydantic import BaseModel, Field

class APIResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool = Field(True, description="操作是否成功")
    data: Optional[Any] = Field(None, description="返回的数据")
    message: Optional[str] = Field(None, description="提示信息")
    error: Optional[str] = Field(None, description="错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例"},
                "message": "操作成功"
            }
        }

class PaginatedResponse(APIResponse):
    """分页响应格式"""
    data: Optional[dict] = Field(None, description="分页数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "items": []
                }
            }
        }
```

### 3. 使用示例

#### ✅ 正确示例

```python
from app.schemas.response import APIResponse

@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """获取用户列表"""
    users = db.query(User).all()
    
    return APIResponse(
        success=True,
        data=[user.to_dict() for user in users],
        message="获取成功"
    )

@router.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    try:
        new_user = User(**user.dict())
        db.add(new_user)
        db.commit()
        
        return APIResponse(
            success=True,
            data=new_user.to_dict(),
            message="用户创建成功"
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=str(e),
            message="用户创建失败"
        )
```

#### ❌ 错误示例

```python
# 错误 1: 直接返回字典，格式不统一
@router.get("/users")
async def get_users():
    return {"users": [...]}  # ❌ 缺少 success 字段

# 错误 2: 使用不同的字段名
@router.get("/users")
async def get_users():
    return {
        "status": "ok",      # ❌ 应该用 success
        "result": [...]      # ❌ 应该用 data
    }

# 错误 3: 成功和失败格式不一致
@router.post("/users")
async def create_user():
    if success:
        return {"data": user}           # ❌ 缺少 success
    else:
        return {"error": "failed"}      # ❌ 格式不一致
```

### 4. 任务状态响应

**对于异步任务，使用独立的 status 字段表示任务状态**：

```python
class TaskResponse(APIResponse):
    """任务响应格式"""
    data: dict = Field(..., description="任务数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "task_id": "task_123",
                    "status": "processing",  # pending/processing/completed/failed
                    "progress": 50,
                    "message": "正在处理中..."
                }
            }
        }
```

**状态字段说明**：
- `success`: API 调用是否成功（HTTP 层面）
- `status`: 任务执行状态（业务层面）
  - `pending`: 等待中
  - `processing`: 处理中
  - `completed`: 已完成
  - `failed`: 失败

### 5. 错误处理

**统一的错误响应**：

```python
from fastapi import HTTPException

# 使用 HTTPException 抛出错误
raise HTTPException(
    status_code=400,
    detail="参数错误"
)

# 或者返回 APIResponse
return APIResponse(
    success=False,
    error="参数错误",
    message="请检查输入参数"
)
```

### 6. 前端处理

**前端统一处理响应**：

```javascript
// frontend/src/utils/axios.js
axios.interceptors.response.use(
  response => {
    // 统一返回 data 字段
    return response.data
  },
  error => {
    // 统一错误处理
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.message
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 使用示例
const response = await axios.get('/api/v1/users')
if (response.success) {
  // 处理成功
  const users = response.data
} else {
  // 处理失败
  console.error(response.error)
}
```

## 迁移指南

### 现有代码迁移步骤

1. **创建响应模型**：
   ```bash
   # 创建统一响应模型文件
   touch backend/app/schemas/response.py
   ```

2. **逐步迁移 API**：
   - 优先迁移新功能的 API
   - 对现有 API 逐个模块迁移
   - 保持向后兼容（前端同时支持新旧格式）

3. **前端适配**：
   ```javascript
   // 兼容新旧格式
   const getData = (response) => {
     // 新格式：{ success: true, data: {...} }
     if (response.success !== undefined) {
       return response.data
     }
     // 旧格式：直接返回数据
     return response
   }
   ```

4. **测试验证**：
   - 单元测试验证响应格式
   - 集成测试验证前后端交互
   - 手动测试验证用户体验

## 检查清单

在提交代码前，请确认：

- [ ] 所有新增 API 使用 `APIResponse` 格式
- [ ] 响应包含 `success` 字段
- [ ] 数据统一放在 `data` 字段中
- [ ] 错误信息放在 `error` 字段中
- [ ] 任务状态使用独立的 `status` 字段
- [ ] 前端正确处理响应格式
- [ ] 添加了响应格式的单元测试

## 常见问题

### Q: 为什么要统一响应格式？
A: 
1. 降低前端处理复杂度
2. 提高代码可维护性
3. 便于统一错误处理
4. 提升开发效率

### Q: 现有 API 需要立即迁移吗？
A: 
- 新功能必须使用新格式
- 现有 API 可以逐步迁移
- 优先迁移高频使用的 API
- 保持向后兼容，避免破坏性变更

### Q: 如何处理特殊场景？
A: 
- 文件下载：使用 `FileResponse`
- 流式响应：使用 `StreamingResponse`
- 重定向：使用 `RedirectResponse`
- 其他场景：继承 `APIResponse` 扩展

## 参考资料

- [FastAPI 响应模型文档](https://fastapi.tiangolo.com/tutorial/response-model/)
- [Pydantic 模型文档](https://docs.pydantic.dev/)
- [RESTful API 设计最佳实践](https://restfulapi.net/)

---

**重要提示**：
- 本规范从现在开始强制执行
- 所有新增 API 必须遵循此规范
- Code Review 时会检查响应格式
- 违反规范的代码将被要求修改
