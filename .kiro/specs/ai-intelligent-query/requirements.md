# Requirements Document

## Introduction

AI 智能查询功能旨在提升用户体验，使用户能够通过自然语言提问直接获取信息，而无需手动选择表、字段和过滤条件。系统将自动理解用户意图，从多个数据源检索信息并以自然语言形式返回结果。

**数据源包括**：
1. **结构化数据**（MySQL 数据库）：CMDB 物理机/虚机信息、任务历史、用户数据、监控数据等
2. **分析报告**（MinIO 存储）：资源分析报告、监控分析报告（BCC/BOS）、运营分析报告等 HTML/JSON 文件

系统采用 **RAG（检索增强生成）+ Text-to-SQL** 混合架构，根据查询意图自动选择合适的数据源和检索方式。

## Glossary

- **AI_Query_System**: AI 智能查询系统，负责处理自然语言查询请求
- **NL_Query**: Natural Language Query，用户输入的自然语言查询文本
- **Intent_Router**: 意图路由器，负责判断查询类型并路由到相应处理器（实时数据查询/报告检索/普通对话）
- **SQL_Generator**: SQL 生成器，负责将自然语言转换为 SQL 语句
- **Query_Executor**: 查询执行器，负责安全地执行 SQL 查询
- **Report_Retriever**: 报告检索器，负责从 MinIO 检索和解析分析报告
- **Vector_Store**: 向量数据库，存储报告内容的向量表示用于语义检索
- **Embedding_Model**: 向量化模型，将文本转换为向量表示
- **Security_Validator**: 安全验证器，负责验证 SQL 语句的安全性
- **Audit_Logger**: 审计日志记录器，负责记录所有查询操作
- **Table_Whitelist**: 表白名单，允许查询的数据库表列表
- **Schema_Context**: 数据库模式上下文，包含表结构、字段、关系等元数据
- **Report_Index**: 报告索引，存储 MinIO 中所有报告的元数据（任务ID、类型、时间、路径等）
- **ERNIE_API**: 百度文心一言 API，用于自然语言理解和生成
- **RBAC_System**: Role-Based Access Control，基于角色的访问控制系统
- **MinIO_Storage**: MinIO 对象存储，存储分析报告（HTML/JSON 格式）
- **Knowledge_Base**: 知识库，存储用户手动添加的知识条目（运维经验、故障处理方案、操作规范等）
- **Knowledge_Entry**: 知识条目，包含标题、内容、标签、分类等字段的结构化知识单元
- **Knowledge_Manager**: 知识库管理器，负责知识条目的增删改查和向量化
- **Vector_Storage**: 向量存储目录，存储向量数据库文件（FAISS 索引文件或 Chroma 数据库文件）
- **Session_Token**: 会话令牌，用于维护用户的对话历史和知识库管理会话

## Requirements

### Requirement 1: 自然语言查询处理

**User Story:** 作为系统用户，我希望使用自然语言提问来查询数据，以便快速获取所需信息而无需了解数据库结构。

#### Acceptance Criteria

1. WHEN 用户提交 NL_Query THEN THE AI_Query_System SHALL 接收并解析查询文本
2. WHEN NL_Query 长度超过 1000 个字符 THEN THE AI_Query_System SHALL 拒绝请求并返回错误提示
3. WHEN NL_Query 为空或仅包含空白字符 THEN THE AI_Query_System SHALL 拒绝请求并返回错误提示
4. WHEN 用户提交查询请求 THEN THE AI_Query_System SHALL 支持流式响应（SSE）逐步返回处理状态和结果
5. WHEN 使用流式响应 THEN THE AI_Query_System SHALL 依次返回：analyzing_intent（意图分析）、querying_data（数据查询）、generating_answer（生成回答）、completed（完成）
6. WHEN 查询处理时间超过 15 秒 THEN THE AI_Query_System SHALL 返回超时提示但保持连接继续处理
7. WHEN 查询最终完成时间超过 30 秒 THEN THE AI_Query_System SHALL 强制终止并返回部分结果

### Requirement 2: 意图识别与路由

**User Story:** 作为系统架构师，我希望系统能够识别不同类型的查询意图，以便将请求路由到正确的处理器。

#### Acceptance Criteria

1. WHEN 接收到 NL_Query THEN THE Intent_Router SHALL 使用 ERNIE_API 进行意图分类而不是简单的关键词匹配
2. WHEN 调用 ERNIE_API 进行意图分类 THEN THE Intent_Router SHALL 使用专门的意图分类 Prompt 返回 JSON 格式结果包含 intent_type（sql/rag_report/rag_knowledge/chat/mixed）和 confidence（置信度）
3. WHEN 意图分类置信度低于 0.7 THEN THE Intent_Router SHALL 使用语义相似度作为辅助判断，计算用户 Query 与预定义典型问题的相似度
4. WHEN 查询同时涉及多个数据源（如"当前的报告生成任务怎么失败了"）THEN THE Intent_Router SHALL 返回 mixed 类型并标注需要调用的处理器列表
5. WHEN 查询不包含明显关键词但语义属于实时查询（如"CMDB里有哪些机器"）THEN THE Intent_Router SHALL 通过 LLM 理解语义并正确路由到 SQL_Generator
6. WHEN Intent_Router 无法确定查询意图且置信度低于 0.5 THEN THE AI_Query_System SHALL 请求用户澄清查询内容
7. THE Intent_Router SHALL 维护一个典型问题库包含至少 50 个示例 Query-Intent 对用于语义相似度辅助判断
8. WHEN 意图分类失败或超时 THEN THE Intent_Router SHALL 降级到基于关键词的规则路由

### Requirement 3: SQL 生成

**User Story:** 作为系统开发者，我希望系统能够准确地将自然语言转换为 SQL 查询，以便自动化数据检索过程。

#### Acceptance Criteria

1. WHEN SQL_Generator 接收到数据查询请求 THEN THE SQL_Generator SHALL 先使用向量检索从完整 Schema_Context 中筛选最相关的表结构（Top-K 表，K ≤ 5）
2. WHEN 筛选出相关表结构 THEN THE SQL_Generator SHALL 仅将这些表的结构信息传递给 ERNIE_API 而不是所有表结构
3. WHEN 调用 ERNIE_API 生成 SQL THEN THE SQL_Generator SHALL 提供筛选后的 Schema_Context 和用户查询
4. WHEN 生成 SQL 语句 THEN THE SQL_Generator SHALL 确保生成的 SQL 仅包含 SELECT 语句
5. WHEN 生成 SQL 语句 THEN THE SQL_Generator SHALL 确保查询的表在 Table_Whitelist 中
6. WHEN 生成的 SQL 为明细查询（SELECT * 或 SELECT 字段列表）THEN THE SQL_Generator SHALL 自动添加 LIMIT 子句限制返回行数不超过 100 行
7. WHEN 生成的 SQL 为聚合查询（包含 COUNT、SUM、AVG、MAX、MIN、GROUP BY）THEN THE SQL_Generator SHALL 不添加 LIMIT 子句
8. WHEN ERNIE_API 返回无效或不安全的 SQL THEN THE SQL_Generator SHALL 拒绝该 SQL 并返回错误提示
9. WHEN Schema 向量检索失败 THEN THE SQL_Generator SHALL 降级到使用完整 Schema_Context 但限制在 10 个最常用的表

### Requirement 4: SQL 安全验证

**User Story:** 作为系统安全管理员，我希望所有 SQL 查询都经过严格的安全验证，以防止数据泄露和恶意操作。

#### Acceptance Criteria

1. WHEN Security_Validator 接收到 SQL 语句 THEN THE Security_Validator SHALL 验证该语句仅为 SELECT 类型
2. WHEN SQL 语句包含 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、TRUNCATE 或其他修改操作 THEN THE Security_Validator SHALL 拒绝该语句并记录安全事件
3. WHEN SQL 语句查询的表不在 Table_Whitelist 中 THEN THE Security_Validator SHALL 拒绝该语句
4. WHEN SQL 语句为明细查询且不包含 LIMIT 子句 THEN THE Security_Validator SHALL 拒绝该语句
5. WHEN SQL 语句的 LIMIT 值超过 100 THEN THE Security_Validator SHALL 拒绝该语句
6. WHEN SQL 语句包含多条语句（使用分号分隔）THEN THE Security_Validator SHALL 拒绝该语句
7. WHEN SQL 语句包含复杂的笛卡尔积（多表 JOIN 但缺少 ON 条件）THEN THE Security_Validator SHALL 拒绝该语句并提示优化查询
8. WHEN SQL 语句通过所有安全检查 THEN THE Security_Validator SHALL 标记该语句为可执行
9. THE Security_Validator SHALL 在 MySQL 用户层面配置 MAX_EXECUTION_TIME=5000（5秒）作为额外保护
10. WHEN SQL 语句包含子查询嵌套超过 3 层 THEN THE Security_Validator SHALL 拒绝该语句并提示简化查询

### Requirement 5: 查询执行

**User Story:** 作为系统用户，我希望系统能够安全地执行查询并返回结果，以便获取所需的数据信息。

#### Acceptance Criteria

1. WHEN Query_Executor 接收到已验证的 SQL 语句 THEN THE Query_Executor SHALL 在只读数据库连接上执行该语句
2. WHEN SQL 执行时间超过 5 秒 THEN THE Query_Executor SHALL 终止查询并返回超时错误
3. WHEN SQL 执行成功 THEN THE Query_Executor SHALL 返回查询结果集
4. WHEN SQL 执行失败 THEN THE Query_Executor SHALL 返回错误信息并记录到 Audit_Logger
5. WHEN 查询结果为空 THEN THE Query_Executor SHALL 返回空结果集标识

### Requirement 6: 结果自然语言转换

**User Story:** 作为系统用户，我希望查询结果以自然语言形式呈现，以便更容易理解数据含义。

#### Acceptance Criteria

1. WHEN Query_Executor 返回查询结果集 THEN THE AI_Query_System SHALL 调用 ERNIE_API 将结果转换为自然语言回答
2. WHEN 结果集包含多行数据 THEN THE AI_Query_System SHALL 生成结构化的自然语言描述
3. WHEN 结果集为空 THEN THE AI_Query_System SHALL 返回友好的"未找到数据"提示
4. WHEN 自然语言生成失败 THEN THE AI_Query_System SHALL 返回原始查询结果的表格形式

### Requirement 7: 权限集成

**User Story:** 作为系统管理员，我希望查询功能与现有 RBAC 权限体系集成，以确保用户只能访问其有权限的数据。

#### Acceptance Criteria

1. WHEN 用户提交查询请求 THEN THE AI_Query_System SHALL 验证用户身份和认证状态
2. WHEN 用户未认证 THEN THE AI_Query_System SHALL 拒绝请求并返回 401 未授权错误
3. WHEN 用户已认证 THEN THE AI_Query_System SHALL 根据用户角色从 RBAC_System 获取可访问的表列表
4. WHEN 生成的 SQL 查询的表不在用户可访问表列表中 THEN THE AI_Query_System SHALL 拒绝查询并返回权限错误
5. WHEN 用户角色变更 THEN THE AI_Query_System SHALL 在下次查询时应用新的权限规则

### Requirement 8: 审计与日志

**User Story:** 作为系统审计员，我希望所有查询操作都被完整记录，以便进行安全审计和问题追溯。

#### Acceptance Criteria

1. WHEN 用户提交查询请求 THEN THE Audit_Logger SHALL 记录用户 ID、时间戳、原始 NL_Query
2. WHEN SQL_Generator 生成 SQL 语句 THEN THE Audit_Logger SHALL 记录生成的 SQL 文本
3. WHEN Query_Executor 执行查询 THEN THE Audit_Logger SHALL 记录执行状态、执行时间、返回行数
4. WHEN Security_Validator 拒绝查询 THEN THE Audit_Logger SHALL 记录拒绝原因和安全事件详情
5. WHEN 查询过程发生错误 THEN THE Audit_Logger SHALL 记录错误类型和错误消息
6. WHEN 记录审计日志 THEN THE Audit_Logger SHALL 确保日志持久化存储且不可篡改

### Requirement 9: 数据库模式管理

**User Story:** 作为系统开发者，我希望系统能够维护和更新数据库模式信息，以便 SQL 生成器能够准确理解表结构。

#### Acceptance Criteria

1. WHEN 系统启动 THEN THE AI_Query_System SHALL 从数据库加载 Schema_Context 包括表名、字段名、数据类型、主外键关系
2. WHEN Schema_Context 加载失败 THEN THE AI_Query_System SHALL 记录错误并使用缓存的模式信息
3. WHEN 数据库结构发生变更 THEN THE AI_Query_System SHALL 提供手动刷新 Schema_Context 的接口
4. WHEN SQL_Generator 请求模式信息 THEN THE AI_Query_System SHALL 返回仅包含 Table_Whitelist 中表的模式信息

### Requirement 10: 错误处理与用户反馈

**User Story:** 作为系统用户，我希望在查询失败时能够获得清晰的错误提示，以便了解问题并调整查询。

#### Acceptance Criteria

1. WHEN 查询过程发生错误 THEN THE AI_Query_System SHALL 返回用户友好的错误消息
2. WHEN 错误为安全验证失败 THEN THE AI_Query_System SHALL 提示用户查询不符合安全规则但不暴露技术细节
3. WHEN 错误为权限不足 THEN THE AI_Query_System SHALL 提示用户无权访问相关数据
4. WHEN 错误为超时 THEN THE AI_Query_System SHALL 提示用户查询过于复杂并建议简化查询
5. WHEN 错误为 SQL 生成失败 THEN THE AI_Query_System SHALL 提示用户重新表述查询问题

### Requirement 11: 性能与并发

**User Story:** 作为系统运维人员，我希望系统能够在低并发场景下稳定运行，以满足当前业务需求。

#### Acceptance Criteria

1. WHEN 系统同时处理 2 个查询请求 THEN THE AI_Query_System SHALL 正常响应所有请求
2. WHEN 单个查询请求处理时间超过 8 秒 THEN THE AI_Query_System SHALL 返回超时响应
3. WHEN ERNIE_API 调用失败或超时 THEN THE AI_Query_System SHALL 重试最多 2 次
4. WHEN 数据库连接池耗尽 THEN THE AI_Query_System SHALL 返回服务繁忙错误并记录日志

### Requirement 12: API 接口设计

**User Story:** 作为前端开发者，我希望有清晰的 API 接口来调用智能查询功能，以便集成到现有系统中。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 POST /api/v1/ai/intelligent-query 接口接收查询请求
2. WHEN 接收到请求 THEN THE AI_Query_System SHALL 验证请求体包含必需的 query 字段
3. WHEN 请求成功 THEN THE AI_Query_System SHALL 返回 JSON 格式响应包含自然语言回答、数据来源类型（database/report/mixed）、原始查询结果、执行的 SQL 语句（如有）、引用的报告列表（如有）
4. WHEN 请求失败 THEN THE AI_Query_System SHALL 返回标准错误响应包含错误代码和错误消息
5. THE AI_Query_System SHALL 提供 GET /api/v1/ai/query-tables 接口返回用户可查询的表列表
6. THE AI_Query_System SHALL 提供 GET /api/v1/ai/report-index 接口返回可检索的报告列表（包含任务ID、报告类型、生成时间、摘要等元数据）

### Requirement 13: 报告检索与向量化

**User Story:** 作为系统用户，我希望能够查询历史分析报告的内容，以便快速获取过往的分析结论和建议。

#### Acceptance Criteria

1. WHEN 系统启动 THEN THE Report_Retriever SHALL 从 MinIO_Storage 加载所有报告的元数据并建立 Report_Index
2. WHEN 接收到报告检索请求 THEN THE Report_Retriever SHALL 提取查询中的时间信息（如"上周"、"昨天"、"最近"）
3. WHEN 查询包含明确时间范围 THEN THE Report_Retriever SHALL 仅检索该时间范围内的报告
4. WHEN 查询不包含时间信息 THEN THE Report_Retriever SHALL 默认仅检索最近 30 天的报告
5. WHEN 使用 Embedding_Model 将查询文本向量化 THEN THE Report_Retriever SHALL 在向量检索时应用时间衰减函数（越新的报告权重越高）
6. WHEN 在 Vector_Store 中检索 THEN THE Report_Retriever SHALL 返回最相关的 Top-K 报告片段（K ≤ 5）并按相似度和时间综合排序
7. WHEN 检索到相关报告 THEN THE Report_Retriever SHALL 从 MinIO_Storage 获取完整报告内容
8. WHEN 报告内容为 HTML 格式 THEN THE Report_Retriever SHALL 提取文本内容并过滤 HTML 标签
9. WHEN 报告内容为 JSON 格式 THEN THE Report_Retriever SHALL 解析 JSON 并提取关键字段（摘要、结论、建议等）
10. WHEN 检索结果为空 THEN THE Report_Retriever SHALL 返回"未找到相关报告"提示
11. WHEN 返回报告给 ERNIE_API THEN THE Report_Retriever SHALL 在回答中标注报告的生成时间以提醒用户数据时效性

### Requirement 14: 报告向量化与索引管理

**User Story:** 作为系统开发者，我希望系统能够自动将新生成的报告向量化并加入索引，以便用户能够检索到最新的分析内容。

#### Acceptance Criteria

1. WHEN 新的分析报告上传到 MinIO_Storage THEN THE AI_Query_System SHALL 自动触发报告向量化流程
2. WHEN 报告向量化开始 THEN THE Report_Retriever SHALL 按照分层提取策略提取报告内容（摘要层、结论层、详情层）
3. WHEN 内容提取完成 THEN THE Report_Retriever SHALL 使用 Embedding_Model 为每个层级生成独立的向量表示
4. WHEN 向量生成完成 THEN THE Report_Retriever SHALL 将向量存储到 Vector_Store 并更新 Report_Index
5. WHEN 报告类型为资源分析 THEN THE Report_Retriever SHALL 提取：摘要（集群数量、健康状态统计）、关键结论（严重/警告集群列表、风险等级）、优化建议（具体操作步骤）
6. WHEN 报告类型为监控分析（BCC/BOS）THEN THE Report_Retriever SHALL 提取：摘要（实例/Bucket 数量、监控周期）、关键结论（异常实例列表、指标异常详情）、趋势分析（历史对比）
7. WHEN 报告类型为运营分析 THEN THE Report_Retriever SHALL 提取：摘要（数据统计、时间范围）、关键结论（问题分类、优先级排序）、详细数据（Top 问题列表）
8. WHEN 向量化失败 THEN THE AI_Query_System SHALL 记录错误日志但不影响报告的正常存储和访问
9. WHEN 报告向量化成功 THEN THE Knowledge_Manager SHALL 自动创建对应的知识条目并标记 source 为 "auto" 和 source_type 为报告类型
10. WHEN 自动创建的知识条目 THEN THE Knowledge_Manager SHALL 设置 auto_generated 字段为 true 并记录 source_id 为任务 ID
11. WHEN 创建知识条目 THEN THE Knowledge_Manager SHALL 将内容按层级存储：title（摘要）、content（关键结论）、metadata（详细数据的引用路径）
12. WHEN 提取的内容超过 5000 字符 THEN THE Report_Retriever SHALL 仅保留摘要和关键结论，详细数据存储为 MinIO 引用链接

### Requirement 15: 混合查询支持

**User Story:** 作为系统用户，我希望能够同时查询实时数据和历史报告，以便获得更全面的信息。

#### Acceptance Criteria

1. WHEN 用户查询同时涉及实时数据和报告内容 THEN THE AI_Query_System SHALL 并行执行 SQL 查询和报告检索
2. WHEN 实时数据查询和报告检索都完成 THEN THE AI_Query_System SHALL 将两部分结果合并并传递给 ERNIE_API
3. WHEN ERNIE_API 接收到混合结果 THEN THE ERNIE_API SHALL 生成综合性的自然语言回答，明确区分实时数据和历史报告来源
4. WHEN 混合查询中某一部分失败 THEN THE AI_Query_System SHALL 返回成功部分的结果并标注失败部分
5. WHEN 混合查询结果过多 THEN THE AI_Query_System SHALL 优先返回实时数据，报告内容作为补充参考

### Requirement 16: 报告内容缓存

**User Story:** 作为系统运维人员，我希望系统能够缓存常用报告内容，以提升查询响应速度。

#### Acceptance Criteria

1. WHEN Report_Retriever 从 MinIO_Storage 获取报告内容 THEN THE Report_Retriever SHALL 将内容缓存到 Redis
2. WHEN 缓存的报告被再次请求 THEN THE Report_Retriever SHALL 优先从 Redis 读取而不是 MinIO_Storage
3. WHEN 缓存的报告超过 24 小时 THEN THE Report_Retriever SHALL 自动清除缓存
4. WHEN Redis 缓存空间不足 THEN THE Report_Retriever SHALL 使用 LRU 策略清除最少使用的报告缓存
5. WHEN 缓存读取失败 THEN THE Report_Retriever SHALL 降级到直接从 MinIO_Storage 读取

### Requirement 17: 知识库管理 - 创建知识条目

**User Story:** 作为超级管理员，我希望能够手动添加运维知识条目，以便将团队经验沉淀到系统中供 AI 检索使用。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/entries 接口用于创建知识条目
2. WHEN 用户访问知识库管理界面 THEN THE AI_Query_System SHALL 验证用户角色为超级管理员（SUPER_ADMIN）
3. WHEN 用户角色不是超级管理员 THEN THE AI_Query_System SHALL 返回 403 权限错误并拒绝访问
4. WHEN 超级管理员首次访问知识库管理界面 THEN THE AI_Query_System SHALL 要求输入知识库管理密码
5. WHEN 知识库管理密码验证失败 THEN THE AI_Query_System SHALL 拒绝访问并记录失败尝试到 Audit_Logger
6. WHEN 知识库管理密码验证成功 THEN THE AI_Query_System SHALL 创建会话令牌有效期 30 分钟
7. WHEN 用户提交知识条目 THEN THE Knowledge_Manager SHALL 验证必填字段包含 title（标题）和 content（内容）
8. WHEN 知识条目包含 title 和 content THEN THE Knowledge_Manager SHALL 接受可选字段包括 category（分类）、tags（标签数组）、priority（优先级）、author（作者）
9. WHEN 知识条目创建成功 THEN THE Knowledge_Manager SHALL 自动使用 Embedding_Model 生成向量表示
10. WHEN 向量生成完成 THEN THE Knowledge_Manager SHALL 将向量存储到 Vector_Store 并将条目元数据存储到 MySQL
11. WHEN 知识条目创建成功 THEN THE Knowledge_Manager SHALL 返回包含条目 ID 和创建时间的响应
12. WHEN 知识条目内容超过 10000 字符 THEN THE Knowledge_Manager SHALL 拒绝请求并提示内容过长

### Requirement 18: 知识库管理 - 查询知识条目

**User Story:** 作为系统用户，我希望能够浏览和搜索知识库中的条目，以便直接查看运维知识而不依赖 AI 检索。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 GET /api/v1/knowledge/entries 接口用于列出知识条目
2. WHEN 用户请求知识条目列表 THEN THE Knowledge_Manager SHALL 支持分页参数 page 和 page_size（默认 20 条/页）
3. WHEN 用户请求知识条目列表 THEN THE Knowledge_Manager SHALL 支持按 category、tags、author、source（auto/manual）过滤
4. WHEN 用户请求知识条目列表 THEN THE Knowledge_Manager SHALL 支持按 created_at、updated_at、priority 排序
5. THE AI_Query_System SHALL 提供 GET /api/v1/knowledge/entries/{id} 接口用于获取单个知识条目详情
6. WHEN 用户请求不存在的知识条目 THEN THE Knowledge_Manager SHALL 返回 404 错误
7. THE AI_Query_System SHALL 提供 GET /api/v1/knowledge/search 接口用于全文搜索知识条目
8. WHEN 用户提交搜索关键词 THEN THE Knowledge_Manager SHALL 在 title 和 content 字段中进行模糊匹配
9. WHEN 用户请求知识条目 THEN THE Knowledge_Manager SHALL 根据用户权限过滤可见条目
10. WHEN 返回知识条目列表 THEN THE Knowledge_Manager SHALL 包含 source 字段标识条目来源（auto/manual）
11. WHEN 返回自动生成的条目 THEN THE Knowledge_Manager SHALL 包含 source_type（报告类型）和 source_id（任务ID）字段

### Requirement 19: 知识库管理 - 更新知识条目

**User Story:** 作为超级管理员，我希望能够编辑已有的知识条目（包括自动生成的），以便更新过时的信息或修正错误。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 PUT /api/v1/knowledge/entries/{id} 接口用于更新知识条目
2. WHEN 用户提交更新请求 THEN THE Knowledge_Manager SHALL 验证用户是超级管理员且已通过知识库管理密码验证
3. WHEN 用户无权限更新条目 THEN THE Knowledge_Manager SHALL 返回 403 权限错误
4. WHEN 知识条目内容被更新 THEN THE Knowledge_Manager SHALL 重新生成向量表示并更新 Vector_Store
5. WHEN 知识条目更新成功 THEN THE Knowledge_Manager SHALL 更新 updated_at 时间戳和 updated_by 字段
6. WHEN 知识条目更新成功 THEN THE Knowledge_Manager SHALL 保留原始的 created_at 和 author 字段
7. WHEN 知识条目更新失败 THEN THE Knowledge_Manager SHALL 回滚所有更改包括向量存储
8. THE Knowledge_Manager SHALL 支持部分更新（PATCH），仅更新提交的字段
9. WHEN 用户编辑自动生成的条目 THEN THE Knowledge_Manager SHALL 保留 source、source_type、source_id 字段但允许修改 title 和 content
10. WHEN 自动生成的条目被手动编辑 THEN THE Knowledge_Manager SHALL 添加 manually_edited 标记为 true

### Requirement 20: 知识库管理 - 删除知识条目

**User Story:** 作为超级管理员，我希望能够删除过时或错误的知识条目（包括自动生成的），以保持知识库的准确性。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 DELETE /api/v1/knowledge/entries/{id} 接口用于删除知识条目
2. WHEN 用户提交删除请求 THEN THE Knowledge_Manager SHALL 验证用户是超级管理员且已通过知识库管理密码验证
3. WHEN 用户无权限删除条目 THEN THE Knowledge_Manager SHALL 返回 403 权限错误
4. WHEN 知识条目删除成功 THEN THE Knowledge_Manager SHALL 在 MySQL 中标记条目为软删除（deleted_at 字段）而不是物理删除
5. WHEN 知识条目被软删除 THEN THE Knowledge_Manager SHALL 在 Vector_Store 的元数据中标记 is_deleted=true
6. WHEN 向量检索时 THEN THE Vector_Store SHALL 自动过滤 is_deleted=true 的条目
7. THE Knowledge_Manager SHALL 提供定时任务（每周执行）物理清理软删除超过 30 天的条目
8. WHEN 知识条目删除成功 THEN THE Knowledge_Manager SHALL 记录删除操作到 Audit_Logger
9. WHEN 用户请求删除不存在的条目 THEN THE Knowledge_Manager SHALL 返回 404 错误
10. WHEN 删除自动生成的条目 THEN THE Knowledge_Manager SHALL 保留原始报告文件在 MinIO_Storage 中不受影响
11. THE Knowledge_Manager SHALL 支持批量删除操作，接受条目 ID 数组

### Requirement 21: 知识库管理 - 分类与标签管理

**User Story:** 作为超级管理员，我希望能够管理知识条目的分类和标签，以便更好地组织知识库内容。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 GET /api/v1/knowledge/categories 接口返回所有知识分类列表
2. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/categories 接口用于创建新分类（仅超级管理员）
3. THE AI_Query_System SHALL 提供 GET /api/v1/knowledge/tags 接口返回所有标签列表及使用次数
4. WHEN 用户创建知识条目时使用新标签 THEN THE Knowledge_Manager SHALL 自动创建该标签
5. WHEN 知识条目被删除 THEN THE Knowledge_Manager SHALL 更新标签的使用次数
6. WHEN 标签使用次数为 0 THEN THE Knowledge_Manager SHALL 可选地自动清理未使用的标签
7. THE Knowledge_Manager SHALL 支持预定义的分类包括"故障处理"、"操作规范"、"优化建议"、"常见问题"、"最佳实践"
8. WHEN 非超级管理员用户访问分类管理接口 THEN THE Knowledge_Manager SHALL 返回 403 权限错误

### Requirement 25: 知识库管理二次验证

**User Story:** 作为系统安全管理员，我希望知识库管理功能需要二次密码验证，以防止未授权的知识库修改。

#### Acceptance Criteria

1. WHEN 超级管理员首次访问知识库管理界面 THEN THE AI_Query_System SHALL 显示密码输入对话框要求重新输入当前用户的登录密码
2. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/auth/verify 接口用于验证用户密码
3. WHEN 用户提交密码 THEN THE AI_Query_System SHALL 验证密码是否与该用户在 MySQL 中存储的密码哈希匹配
4. WHEN 密码验证成功 THEN THE AI_Query_System SHALL 生成知识库管理会话令牌（JWT）有效期 30 分钟
5. WHEN 密码验证失败 THEN THE AI_Query_System SHALL 返回 401 未授权错误并记录失败尝试到 Audit_Logger（包含用户名）
6. WHEN 密码验证失败超过 5 次 THEN THE AI_Query_System SHALL 锁定该用户的知识库访问权限 30 分钟
7. WHEN 知识库管理会话令牌过期 THEN THE AI_Query_System SHALL 要求用户重新输入密码
8. WHEN 用户执行知识库管理操作 THEN THE AI_Query_System SHALL 验证请求包含有效的知识库管理会话令牌
9. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/auth/logout 接口用于注销知识库管理会话
10. WHEN 用户注销知识库管理会话 THEN THE AI_Query_System SHALL 立即失效该会话令牌
11. WHEN 记录审计日志 THEN THE Audit_Logger SHALL 包含操作用户的用户名而不是共享的系统密码标识

### Requirement 26: 向量数据库存储管理

**User Story:** 作为系统运维人员，我希望向量数据库文件能够持久化存储并支持备份恢复，以确保知识库数据的安全性。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 将向量数据库文件存储在 Docker volume 挂载的持久化目录 /app/vector_store
2. WHEN 使用 FAISS 作为向量数据库 THEN THE Vector_Store SHALL 将索引文件存储为 /app/vector_store/faiss_index.bin
3. WHEN 使用 Chroma 作为向量数据库 THEN THE Vector_Store SHALL 将数据库文件存储在 /app/vector_store/chroma_db/ 目录并在元数据中存储原始文本内容
4. WHEN 系统启动 THEN THE AI_Query_System SHALL 检查向量数据库文件是否存在，不存在则创建新的空索引
5. WHEN 向量数据库文件损坏 THEN THE AI_Query_System SHALL 记录错误并尝试从 MySQL 元数据重建向量索引
6. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/vector-store/backup 接口用于备份向量数据库（仅超级管理员）
7. WHEN 执行向量数据库备份 THEN THE AI_Query_System SHALL 同时备份 MySQL 知识库元数据和向量文件，压缩后上传到 MinIO_Storage 的 vector-backups/ 目录
8. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/vector-store/restore 接口用于恢复向量数据库（仅超级管理员）
9. WHEN 执行向量数据库恢复 THEN THE AI_Query_System SHALL 从 MinIO_Storage 下载备份文件并同时恢复 MySQL 数据和向量文件
10. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/vector-store/rebuild 接口用于从 MySQL 元数据重建向量索引（仅超级管理员）
11. WHEN 执行向量索引重建 THEN THE AI_Query_System SHALL 读取所有知识条目并重新生成向量表示
12. WHEN Docker 容器重启 THEN THE AI_Query_System SHALL 自动加载持久化的向量数据库文件
13. WHEN 使用 Chroma 向量数据库 THEN THE Vector_Store SHALL 在元数据中存储原始文本内容以支持从向量库独立恢复数据

### Requirement 27: 多轮对话上下文管理

**User Story:** 作为系统用户，我希望能够进行多轮对话查询，以便逐步细化查询需求而不需要重复输入上下文。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 在用户会话中维护对话历史（最近 5 轮）
2. WHEN 用户提交新查询 THEN THE AI_Query_System SHALL 检测查询中的代词引用（"它们"、"这些"、"上面的"）
3. WHEN 检测到代词引用 THEN THE AI_Query_System SHALL 从对话历史中提取上一轮的实体或查询结果
4. WHEN 上一轮查询为 SQL 查询 THEN THE AI_Query_System SHALL 缓存查询结果的实体列表（如机器名、IP 地址）
5. WHEN 用户问"它们的 IP 是多少"THEN THE AI_Query_System SHALL 将"它们"替换为上一轮结果的实体列表并生成新的 SQL
6. WHEN 对话历史超过 5 轮 THEN THE AI_Query_System SHALL 自动清理最早的对话记录
7. WHEN 用户明确开始新话题（如"换个问题"）THEN THE AI_Query_System SHALL 清空当前会话的对话历史
8. WHEN 会话超过 30 分钟无活动 THEN THE AI_Query_System SHALL 自动清空对话历史
9. THE AI_Query_System SHALL 在 V1 版本中明确标注仅支持简单的实体引用，不支持复杂的多轮 SQL 上下文推理

### Requirement 28: 详情数据格式优化

**User Story:** 作为系统开发者，我希望传递给 AI 的详情数据格式清晰易读，以减少 AI 幻觉和提高理解准确性。

#### Acceptance Criteria

1. WHEN 从 metadata 字段加载详情层 JSON 数据 THEN THE AI_Query_System SHALL 将 JSON 转换为 Markdown 表格格式
2. WHEN JSON 数据包含数组 THEN THE AI_Query_System SHALL 将数组转换为 Markdown 列表或表格
3. WHEN JSON 数据嵌套超过 2 层 THEN THE AI_Query_System SHALL 扁平化数据结构并使用点号表示层级（如 cluster.metrics.cpu）
4. WHEN 详情数据包含数值统计 THEN THE AI_Query_System SHALL 使用 Pandas DataFrame 生成格式化的表格字符串
5. WHEN 详情数据转换为 Markdown 后超过 2000 字符 THEN THE AI_Query_System SHALL 仅保留关键字段并添加"[数据已精简]"标记
6. WHEN 传递详情数据给 ERNIE_API THEN THE AI_Query_System SHALL 在 Prompt 中明确说明数据格式为 Markdown 表格
7. WHEN 详情数据包含时间序列 THEN THE AI_Query_System SHALL 转换为易读的时间-数值对列表格式

### Requirement 22: 知识库检索集成

**User Story:** 作为系统用户，我希望 AI 在回答问题时能够检索知识库中的相关内容，以便获得团队沉淀的经验和最佳实践。

#### Acceptance Criteria

1. WHEN Intent_Router 判断查询需要知识库检索 THEN THE Knowledge_Manager SHALL 使用 Embedding_Model 将查询向量化
2. WHEN 查询向量化完成 THEN THE Knowledge_Manager SHALL 在 Vector_Store 中检索最相关的 Top-K 知识条目（K ≤ 3）
3. WHEN 检索到相关知识条目 THEN THE Knowledge_Manager SHALL 返回条目的 title、content、category、tags 和相似度分数
4. WHEN 知识条目相似度分数低于阈值（< 0.6）THEN THE Knowledge_Manager SHALL 不返回该条目
5. WHEN 知识库检索结果传递给 ERNIE_API THEN THE ERNIE_API SHALL 在回答中引用知识条目并标注来源
6. WHEN 混合查询包含知识库检索 THEN THE AI_Query_System SHALL 优先返回知识库内容，其次是报告内容，最后是实时数据
7. WHEN 知识库检索失败 THEN THE AI_Query_System SHALL 降级到仅使用报告检索和实时数据查询
8. WHEN 检索到的知识条目包含 metadata 字段（详细数据引用）THEN THE Knowledge_Manager SHALL 仅在用户明确请求详细信息时加载完整内容
9. WHEN 传递给 ERNIE_API 的上下文超过 3000 字符 THEN THE Knowledge_Manager SHALL 仅传递摘要和关键结论，省略详细数据
10. WHEN 用户查询包含"详细"、"完整"、"具体数据"等关键词 THEN THE Knowledge_Manager SHALL 加载知识条目的完整内容包括详细数据

### Requirement 24: 分层内容提取策略

**User Story:** 作为系统开发者，我希望系统能够智能地提取报告的不同层级内容，以便在保证信息完整性的同时控制 AI 上下文大小。

#### Acceptance Criteria

1. WHEN 提取资源分析报告内容 THEN THE Report_Retriever SHALL 按照以下层级提取：
   - 摘要层（≤200字）：集群总数、健康/警告/严重集群数量、分析时间
   - 结论层（≤800字）：严重集群列表（名称、风险等级、主要问题）、警告集群列表（名称、关注点）、关键建议（Top 3）
   - 详情层（完整数据）：所有集群的详细指标、完整建议列表、历史对比数据
2. WHEN 提取监控分析报告（BCC/BOS）内容 THEN THE Report_Retriever SHALL 按照以下层级提取：
   - 摘要层（≤200字）：监控实例/Bucket 数量、监控周期、异常数量统计
   - 结论层（≤800字）：异常实例列表（ID、异常类型、严重程度）、关键指标异常详情（CPU/内存/磁盘）
   - 详情层（完整数据）：所有实例的完整监控数据、历史趋势图表、详细指标值
3. WHEN 提取运营分析报告内容 THEN THE Report_Retriever SHALL 按照以下层级提取：
   - 摘要层（≤200字）：数据时间范围、总问题数、分类统计、完成率
   - 结论层（≤800字）：Top 10 问题列表（标题、类型、负责人）、问题分布分析、趋势总结
   - 详情层（完整数据）：所有问题的完整信息、详细分类统计、时间序列数据
4. WHEN 创建知识条目 THEN THE Knowledge_Manager SHALL 将摘要层存储为 title，结论层存储为 content，详情层存储为 metadata JSON 字段
5. WHEN 向量化知识条目 THEN THE Embedding_Model SHALL 仅对 title 和 content 进行向量化，不包含详情层数据
6. WHEN AI 检索返回知识条目 THEN THE AI_Query_System SHALL 默认仅传递 title 和 content 给 ERNIE_API
7. WHEN 用户查询明确需要详细数据 THEN THE AI_Query_System SHALL 从 metadata 字段加载详情层并传递给 ERNIE_API
8. WHEN 详情层数据为 HTML 格式 THEN THE Report_Retriever SHALL 提取纯文本并移除所有 HTML 标签、CSS 样式和 JavaScript 代码
9. WHEN 详情层数据为 JSON 格式 THEN THE Report_Retriever SHALL 解析 JSON 并提取关键字段，忽略冗余的元数据字段
10. WHEN 提取的任何层级内容超过字符限制 THEN THE Report_Retriever SHALL 截断内容并添加"[内容已截断，查看完整报告]"标记和 MinIO 链接

### Requirement 23: 知识库批量导入

**User Story:** 作为系统管理员，我希望能够批量导入知识条目，以便快速构建初始知识库。

#### Acceptance Criteria

1. THE AI_Query_System SHALL 提供 POST /api/v1/knowledge/import 接口用于批量导入知识条目
2. WHEN 用户上传批量导入文件 THEN THE Knowledge_Manager SHALL 支持 JSON 和 CSV 格式
3. WHEN 导入 JSON 格式 THEN THE Knowledge_Manager SHALL 验证每个条目包含必填字段 title 和 content
4. WHEN 导入 CSV 格式 THEN THE Knowledge_Manager SHALL 要求表头包含 title、content、category、tags 列
5. WHEN 批量导入开始 THEN THE Knowledge_Manager SHALL 异步处理导入任务并返回任务 ID
6. WHEN 批量导入进行中 THEN THE Knowledge_Manager SHALL 提供进度查询接口显示已导入/失败/总数
7. WHEN 单个条目导入失败 THEN THE Knowledge_Manager SHALL 记录错误但继续处理其他条目
8. WHEN 批量导入完成 THEN THE Knowledge_Manager SHALL 返回导入摘要包括成功数、失败数和错误详情
9. WHEN 批量导入的条目数量超过 1000 THEN THE Knowledge_Manager SHALL 拒绝请求并提示分批导入

## Notes

- 本需求文档基于现有 FastAPI + MySQL + Redis + MinIO + Vue3 技术栈
- 系统设计优先考虑安全性，其次是准确性和性能
- SQL 生成准确率目标为 90% 以上，通过持续优化 prompt 和 Schema_Context 提升
- 报告检索采用 RAG（检索增强生成）架构，使用向量数据库实现语义检索
- 向量数据库推荐使用 FAISS（轻量级、易部署）或 Chroma（功能完善）
- Embedding 模型推荐使用百度文心 Embedding API 或开源的 bge-small-zh 模型
- 表白名单和权限规则需要与业务团队协商确定
- 报告向量化可以采用增量更新策略，新报告生成后异步向量化
- 系统支持逐步演进：先实现 Text-to-SQL，再扩展报告检索功能

**内容提取策略详解**：

系统采用**三层内容提取策略**，平衡信息完整性和上下文效率：

1. **摘要层（Summary Layer）**：≤200 字
   - 用途：快速概览，向量检索的主要匹配目标
   - 内容：核心统计数据、时间范围、关键数量
   - 示例："本次分析共涉及5个集群，其中严重3个，警告1个，健康1个"

2. **结论层（Conclusion Layer）**：≤800 字
   - 用途：关键发现和建议，AI 回答的主要内容来源
   - 内容：问题列表（Top N）、风险等级、优先建议
   - 示例："严重集群：集群A（内存92%）、集群B（磁盘95%）..."

3. **详情层（Detail Layer）**：完整数据
   - 用途：深度分析，仅在用户明确请求时加载
   - 内容：所有指标、完整列表、历史数据、图表
   - 存储：JSON 格式存储在 metadata 字段，不参与向量化

**AI 上下文控制策略**：

- 默认查询：仅传递摘要层 + 结论层（≤1000 字）
- 详细查询：加载详情层（用户问"详细数据"、"完整信息"时）
- 多条目检索：每条目最多 1000 字，最多 3 条目，总计 ≤3000 字
- 超长内容：自动截断并提供完整报告链接

**各类报告的提取规则**：

| 报告类型 | 摘要层 | 结论层 | 详情层 |
|---------|--------|--------|--------|
| 资源分析 | 集群数、健康状态统计 | 严重/警告集群列表、Top 3 建议 | 所有集群详细指标、完整建议 |
| BCC 监控 | 实例数、异常数统计 | 异常实例列表、关键指标异常 | 所有实例监控数据、趋势图 |
| BOS 监控 | Bucket 数、存储统计 | 异常 Bucket 列表、容量告警 | 所有 Bucket 详细数据 |
| 运营分析 | 问题总数、分类统计 | Top 10 问题、趋势分析 | 所有问题完整信息、时间序列 |

**数据源说明**：
- **MySQL 数据库**：
  - 结构化数据：CMDB 物理机/虚机信息、任务历史、用户数据等
  - 知识库元数据：知识条目的标题、内容、分类、标签、作者、时间戳等
- **MinIO 存储**：存储分析报告文件和向量数据库备份
  - `html_reports/resource/` - 资源分析报告
  - `html_reports/bcc/` - BCC 监控分析报告
  - `html_reports/bos/` - BOS 存储分析报告
  - `html_reports/operational/` - 运营数据分析报告
  - `excel_reports/` - Excel 格式报告
  - `vector-backups/` - 向量数据库备份文件
- **向量数据库**（FAISS/Chroma）：
  - 存储位置：Docker volume `backend_vector_store` 挂载到 `/app/vector_store`
  - FAISS 模式：`/app/vector_store/faiss_index.bin`（单文件）
  - Chroma 模式：`/app/vector_store/chroma_db/`（目录）
  - 报告内容向量：用于语义检索分析报告
  - 知识条目向量：用于检索用户添加的运维知识

**知识库管理权限说明**：
- **访问权限**：仅超级管理员（SUPER_ADMIN）可以访问知识库管理界面
- **二次验证**：超级管理员访问知识库管理时需要重新输入当前用户的登录密码进行二次验证
- **会话管理**：密码验证成功后生成 30 分钟有效期的知识库管理会话令牌
- **失败锁定**：密码验证失败 5 次后锁定该用户的知识库访问权限 30 分钟
- **操作审计**：所有知识库管理操作（创建、编辑、删除）都记录到审计日志，包含操作用户的用户名
- **未来扩展**：可集成 MFA（TOTP 验证码）或 SSO（LDAP/OAuth）进行更强的身份验证

**Docker 部署配置**：
```yaml
# docker-compose.yml 中需要添加
services:
  backend:
    volumes:
      - backend_vector_store:/app/vector_store  # 新增向量数据库持久化
    environment:
      # 移除 KNOWLEDGE_ADMIN_PASSWORD，使用用户自己的密码进行二次验证
      VECTOR_DB_TYPE: ${VECTOR_DB_TYPE:-faiss}
      VECTOR_DB_PATH: /app/vector_store

volumes:
  backend_vector_store:  # 新增 volume
```

**.env 配置文件**：
```bash
# 向量数据库配置
VECTOR_DB_TYPE=faiss  # 或 chroma
VECTOR_DB_PATH=/app/vector_store

# Embedding 模型配置
EMBEDDING_MODEL=bge-small-zh  # 或使用百度文心 Embedding API
EMBEDDING_API_URL=  # 如果使用 API
EMBEDDING_API_KEY=  # 如果使用 API

# ERNIE API 配置（用于意图分类、SQL 生成、回答生成）
ERNIE_API_URL=http://llms-se.baidu-int.com:8200/chat/completions
ERNIE_API_KEY=your-api-key-here
ERNIE_MODEL=ernie-4.5-8k-preview
```

**典型查询场景**：
1. **实时数据查询**："cdhmlcc001 这台物理机的情况" → 查询 CMDB 表
2. **报告检索**："最近的资源分析有什么优化建议" → 检索 MinIO 中的资源分析报告
3. **知识库检索**："如何处理 MySQL 主从同步延迟" → 检索知识库中的故障处理方案
4. **混合查询**："物理机 cdhmlcc001 的当前状态和历史分析报告" → 同时查询数据库和报告

**知识库条目格式示例**：

**手动创建的条目**：
```json
{
  "id": 1,
  "title": "MySQL 主从同步延迟处理方案",
  "content": "当发现 MySQL 主从同步延迟超过 10 秒时，按以下步骤排查：\n1. 检查网络连接...\n2. 查看 binlog 大小...\n3. 优化慢查询...",
  "category": "故障处理",
  "tags": ["MySQL", "主从同步", "性能优化"],
  "priority": "high",
  "source": "manual",
  "author": "admin",
  "auto_generated": false,
  "manually_edited": false,
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z"
}
```

**自动生成的条目**：
```json
{
  "id": 2,
  "title": "资源分析 - 集群A等3个集群存在严重风险 - 2026-01-23",
  "content": "本次分析共涉及5个集群，其中严重集群3个，警告集群1个，健康集群1个。\n\n严重集群：\n1. 集群A：内存使用92%，CPU使用88%，极高风险\n2. 集群B：磁盘使用95%，Pod重启频繁，极高风险\n3. 集群C：节点故障2个，服务不可用，极高风险\n\n关键建议：\n1. 立即扩容集群A的内存和CPU资源\n2. 清理集群B的磁盘空间，排查Pod重启原因\n3. 修复集群C的故障节点，恢复服务",
  "metadata": {
    "detail_level": "summary_and_conclusion",
    "full_report_url": "/cluster-files/html_reports/resource/task_12345_resource_report.html",
    "detailed_data": {
      "total_clusters": 5,
      "critical_clusters": ["集群A", "集群B", "集群C"],
      "warning_clusters": ["集群D"],
      "healthy_clusters": ["集群E"],
      "metrics_summary": {
        "集群A": {"memory": 92, "cpu": 88, "disk": 75},
        "集群B": {"memory": 78, "cpu": 65, "disk": 95},
        "集群C": {"memory": 70, "cpu": 60, "disk": 80, "failed_nodes": 2}
      }
    }
  },
  "category": "分析报告",
  "tags": ["资源分析", "集群A", "集群B", "集群C", "严重风险"],
  "priority": "high",
  "source": "auto",
  "source_type": "resource_analysis",
  "source_id": "task_12345",
  "author": "system",
  "auto_generated": true,
  "manually_edited": false,
  "created_at": "2026-01-23T15:30:00Z",
  "updated_at": "2026-01-23T15:30:00Z"
}
```

**自动生成但被手动编辑的条目**：
```json
{
  "id": 3,
  "title": "BCC 监控异常分析 - 实例 i-xxx",
  "content": "实例 i-xxx 在 2026-01-22 出现 CPU 飙升...\n[管理员补充] 已确认是定时任务导致，已优化。",
  "category": "分析报告",
  "tags": ["BCC", "监控", "CPU异常"],
  "source": "auto",
  "source_type": "bcc_analysis",
  "source_id": "task_67890",
  "author": "system",
  "auto_generated": true,
  "manually_edited": true,
  "updated_by": "admin",
  "created_at": "2026-01-22T18:00:00Z",
  "updated_at": "2026-01-23T09:00:00Z"
}
```
