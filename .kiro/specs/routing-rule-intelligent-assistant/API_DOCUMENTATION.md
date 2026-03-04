# 路由规则智能辅助 - API文档

## 概述

本文档描述路由规则智能辅助系统的后端API接口。

所有API遵循统一响应格式：
```json
{
  "success": boolean,
  "data": object | array | null,
  "message": string,
  "error": string | null
}
```

## 基础URL

```
http://服务器IP:8000/api/v1/routing
```

## 认证

所有API需要JWT认证，在请求头中包含：
```
Authorization: Bearer <token>
```

## API端点

### 1. 自然语言转换

**POST** `/convert`

将自然语言描述转换为正则表达式。

**请求体：**
```json
{
  "natural_language": "查询IP地址",
  "intent_type": "sql"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "regex": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
    "explanation": "匹配IP地址格式",
    "examples": ["192.168.1.1", "10.0.0.1", "172.16.0.1"],
    "confidence": 0.9
  }
}
```

**错误码：**
- `400`: 输入为空或无效
- `500`: ERNIE API调用失败

---

### 2. 正则表达式验证

**POST** `/validate`

验证正则表达式语法并检测冲突。

**请求体：**
```json
{
  "regex": "\\d+",
  "intent_type": "sql",
  "exclude_rule_id": 1  // 可选，编辑时排除自身
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "syntax_errors": [],
    "conflicts": [],
    "complexity_score": 3
  }
}
```

---

### 3. 测试匹配

**POST** `/test-match`

测试正则表达式是否匹配查询。

**请求体：**
```json
{
  "regex": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
  "test_queries": ["查询192.168.1.1", "查询服务器"]
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "query": "查询192.168.1.1",
        "matched": true,
        "matched_text": "192.168.1.1",
        "confidence": 0.95,
        "match_position": {"start": 2, "end": 13}
      },
      {
        "query": "查询服务器",
        "matched": false,
        "matched_text": null,
        "confidence": 0,
        "match_position": null
      }
    ],
    "match_rate": 0.5,
    "total_count": 2,
    "matched_count": 1
  }
}
```

---

### 4. 关键词提取

**POST** `/extract-keywords`

从自然语言或正则表达式中提取关键词。

**请求体：**
```json
{
  "pattern": "查询服务器IP地址",
  "pattern_type": "natural_language"  // 或 "regex"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "keywords": [
      {"word": "服务器", "weight": 0.9, "type": "noun"},
      {"word": "IP", "weight": 0.85, "type": "noun"},
      {"word": "地址", "weight": 0.8, "type": "noun"}
    ]
  }
}
```

---

### 5. 表推荐

**GET** `/recommend-tables`

根据关键词推荐相关数据库表。

**查询参数：**
- `keywords`: 关键词列表（逗号分隔）
- `intent_type`: 意图类型

**响应：**
```json
{
  "success": true,
  "data": {
    "tables": [
      {
        "name": "iaas_servers",
        "category": "CMDB",
        "description": "服务器信息表",
        "field_count": 145,
        "relevance_score": 0.92,
        "reason": "包含服务器和IP相关字段"
      }
    ]
  }
}
```

---

### 6. 规则模板

**GET** `/templates`

获取规则模板列表。

**查询参数：**
- `category`: 模板分类（可选）

**响应：**
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": 1,
        "name": "IP地址查询",
        "category": "网络",
        "description": "匹配IP地址格式的查询",
        "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
        "intent_type": "sql",
        "priority": 90
      }
    ]
  }
}
```

---

### 7. 智能描述生成

**POST** `/generate-description`

生成规则描述。

**请求体：**
```json
{
  "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
  "intent_type": "sql",
  "keywords": ["IP", "地址"]
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "description": "匹配IP地址格式的查询",
    "purpose": "识别包含IP地址的查询",
    "applicable_scenarios": ["服务器查询", "网络诊断"]
  }
}
```

---

### 8. 优先级建议

**POST** `/suggest-priority`

建议规则优先级。

**请求体：**
```json
{
  "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
  "intent_type": "sql",
  "keywords": ["IP", "地址"]
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "suggested_priority": 95,
    "priority_range": {"min": 90, "max": 100},
    "category": "强制规则",
    "reason": "IP地址是精确匹配模式，应设置高优先级",
    "conflicts": []
  }
}
```

---

### 9. 规则影响预测

**POST** `/predict-impact`

预测规则对历史查询的影响。

**请求体：**
```json
{
  "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
  "intent_type": "sql"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "affected_query_count": 150,
    "affected_query_percentage": 15.5,
    "sample_queries": ["查询192.168.1.1", "查询10.0.0.1"],
    "expected_accuracy_change": 5.2,
    "expected_usage_frequency": 50,
    "warning": "此规则将影响15%的历史查询，请谨慎操作"
  }
}
```

---

### 10. 草稿管理

#### 保存草稿
**POST** `/drafts`

**请求体：**
```json
{
  "draft_data": {
    "pattern": "test_\\w+",
    "intent_type": "sql",
    "priority": 50
  }
}
```

#### 获取草稿列表
**GET** `/drafts`

#### 获取草稿详情
**GET** `/drafts/{id}`

#### 删除草稿
**DELETE** `/drafts/{id}`

---

## 错误处理

所有错误响应格式：
```json
{
  "success": false,
  "data": null,
  "message": "错误描述",
  "error": "详细错误信息"
}
```

常见错误码：
- `400`: 请求参数错误
- `401`: 未授权
- `404`: 资源不存在
- `422`: 验证失败
- `500`: 服务器内部错误

## 速率限制

- 每个用户每分钟最多100次请求
- 超过限制返回429状态码

## 版本控制

当前API版本：v1

版本信息包含在URL中：`/api/v1/routing/...`

## 更新日志

### v1.0.0 (2026-03-02)
- 初始版本发布
- 包含10个核心API端点
