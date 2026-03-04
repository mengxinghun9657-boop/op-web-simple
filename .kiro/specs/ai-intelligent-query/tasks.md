# Implementation Plan: AI 智能查询功能

## Overview

本实现计划将 AI 智能查询功能分解为渐进式的开发任务，按照依赖关系组织。每个任务都是可独立测试的单元，确保逐步构建可工作的系统。

**技术栈**：Python + FastAPI + MySQL + Redis + MinIO + FAISS/Chroma + Vue3

**实现策略**：
1. 先实现基础设施（数据库、配置、客户端）
2. 再实现核心组件（审计、安全、执行）
3. 然后实现 AI 功能（意图路由、SQL 生成、报告检索）
4. 最后实现高级功能（知识库、多轮对话、前端）

## Tasks

### 阶段 1：基础设施搭建

- [x] 1. 创建数据库表结构和初始化脚本
  - 创建 `knowledge_entries` 表（知识库条目）
  - 创建 `audit_logs` 表（审计日志）
  - 创建 `report_index` 表（报告索引）
  - 编写 MySQL 初始化脚本 `mysql/init/01_create_tables.sql`
  - 添加必要的索引以优化查询性能
  - _Requirements: 8.1, 8.2, 13.1, 17.7_

- [x] 2. 配置向量数据库初始化
  - 创建向量存储目录结构 `/app/vector_store`
  - 实现 FAISS 索引初始化逻辑（`VectorStore` 类）
  - 实现向量存储的加载和保存方法
  - 添加向量数据库健康检查
  - _Requirements: 26.1, 26.2, 26.4_


- [x] 3. 配置 ERNIE API 和 Embedding API 客户端
  - 创建 `ERNIEClient` 类封装百度文心一言 API 调用
  - 创建 `EmbeddingModel` 类封装向量化模型
  - 实现 API 调用的重试机制（最多 2 次）
  - 实现超时控制和错误处理
  - 添加 API 调用日志记录
  - _Requirements: 2.1, 3.3, 11.3_

- [x] 4. 更新 Docker Compose 配置
  - 在 `docker-compose.yml` 中添加 `backend_vector_store` volume
  - 配置环境变量（ERNIE API、Embedding API、向量数据库类型）
  - 更新 `.env.example` 文件添加新的配置项
  - 验证 Docker 容器能够正常启动
  - _Requirements: 26.1, 26.12_

### 阶段 2：核心组件实现

- [x] 5. 实现审计日志记录器（Audit Logger）
  - 创建 `AuditLogger` 类
  - 实现查询提交日志记录方法
  - 实现查询成功/失败/超时日志记录方法
  - 实现 SQL 安全拒绝事件记录方法
  - 实现知识库操作日志记录方法
  - 确保日志持久化到 MySQL `audit_logs` 表
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 6. 实现 Embedding Model 封装
  - 创建 `EmbeddingModel` 类
  - 实现文本向量化方法 `encode(text: str) -> np.ndarray`
  - 支持批量向量化 `encode_batch(texts: List[str]) -> List[np.ndarray]`
  - 实现向量相似度计算方法（余弦相似度）
  - 添加向量缓存机制（Redis）以提升性能
  - _Requirements: 13.5, 22.1_


- [x] 7. 实现向量存储管理器（Vector Store Manager）
  - [x] 7.1 实现向量添加方法 `add(id, embedding, metadata)`
    - 支持单个和批量添加
    - 更新 ID 映射和元数据
    - _Requirements: 17.9, 17.10_
  
  - [ ]* 7.2 编写向量添加的属性测试
    - **Property 1: 向量添加后可检索**
    - **Validates: Requirements 17.9, 17.10**
  
  - [x] 7.3 实现向量检索方法 `search(embedding, top_k, filter)`
    - 支持相似度阈值过滤
    - 支持元数据过滤（is_deleted=false）
    - 返回结果按相似度排序
    - _Requirements: 13.6, 22.2, 22.4_
  
  - [ ]* 7.4 编写向量检索的属性测试
    - **Property 14: 向量检索Top-K限制**
    - **Validates: Requirements 13.6**
  
  - [x] 7.5 实现向量更新和删除方法
    - 更新元数据 `update_metadata(id, metadata)`
    - 软删除标记 `mark_deleted(id)`
    - _Requirements: 19.4, 20.5_

- [x] 8. 实现 SQL 安全验证器（Security Validator）
  - [x] 8.1 实现 SELECT 类型验证
    - 检查 SQL 是否仅为 SELECT 语句
    - 拒绝 INSERT、UPDATE、DELETE、DROP 等操作
    - _Requirements: 4.1, 4.2_
  
  - [ ]* 8.2 编写 SQL 类型安全的属性测试
    - **Property 5: SQL类型安全验证**
    - **Validates: Requirements 4.1, 4.2**
  
  - [x] 8.3 实现表白名单验证
    - 提取 SQL 中的表名
    - 验证所有表都在白名单中
    - 验证用户权限
    - _Requirements: 4.3, 7.4_
  
  - [x] 8.4 实现 LIMIT 子句验证
    - 检查明细查询是否包含 LIMIT
    - 验证 LIMIT 值不超过 100
    - _Requirements: 4.4, 4.5_
  
  - [ ]* 8.5 编写 LIMIT 规则的属性测试
    - **Property 8: LIMIT规则验证**
    - **Validates: Requirements 4.4, 4.5**


  - [x] 8.6 实现笛卡尔积检测
    - 检测多表 JOIN 缺少 ON 条件
    - 检测逗号分隔多表缺少 WHERE 条件
    - _Requirements: 4.7_
  
  - [ ]* 8.7 编写笛卡尔积检测的属性测试
    - **Property 9: 笛卡尔积检测**
    - **Validates: Requirements 4.7**
  
  - [x] 8.8 实现子查询嵌套深度检测
    - 递归计算子查询嵌套层数
    - 拒绝嵌套超过 3 层的查询
    - _Requirements: 4.10_
  
  - [ ]* 8.9 编写子查询嵌套深度的属性测试
    - **Property 10: 子查询嵌套深度限制**
    - **Validates: Requirements 4.10**
  
  - [x] 8.10 实现多条语句检测
    - 检测分号分隔的多条 SQL
    - 拒绝批量执行
    - _Requirements: 4.6_

- [x] 9. 实现查询执行器（Query Executor）
  - 创建只读数据库连接池
  - 实现 SQL 执行方法 `execute_query(sql, user_id)`
  - 设置 MySQL 执行超时（5 秒）
  - 实现超时控制和错误处理
  - 记录执行结果到审计日志
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Checkpoint - 核心组件验证
  - 运行所有单元测试和属性测试
  - 验证审计日志正确记录
  - 验证 SQL 安全验证器拒绝不安全的 SQL
  - 验证查询执行器能够执行安全的 SQL
  - 确保所有测试通过，询问用户是否有问题


### 阶段 3：意图路由与 SQL 生成

- [x] 11. 实现意图路由器（Intent Router）
  - [x] 11.1 创建 `IntentRouter` 类
    - 加载典型问题库（50+ 示例）
    - 实现意图分类 Prompt 模板
    - _Requirements: 2.1, 2.2, 2.7_
  
  - [x] 11.2 实现 ERNIE API 意图分类
    - 调用 ERNIE API 进行意图分类
    - 解析返回的 JSON 结果（intent_type, confidence）
    - _Requirements: 2.2_
  
  - [ ]* 11.3 编写意图分类返回格式的属性测试
    - **Property 3: 意图分类返回格式**
    - **Validates: Requirements 2.2**
  
  - [x] 11.4 实现语义相似度辅助判断
    - 当置信度 < 0.7 时，计算与典型问题的相似度
    - 选择相似度最高的意图类型
    - _Requirements: 2.3_
  
  - [x] 11.5 实现关键词规则降级路由
    - 当置信度 < 0.5 时，使用关键词匹配
    - 定义关键词规则（"查询"→sql, "报告"→rag_report）
    - _Requirements: 2.8_
  
  - [x] 11.6 实现混合查询支持
    - 识别同时涉及多个数据源的查询
    - 返回需要调用的处理器列表
    - _Requirements: 2.4_

- [x] 12. 实现 Schema RAG（表结构向量检索）
  - [x] 12.1 创建 `SchemaVectorStore` 类
    - 加载数据库 Schema 信息（表名、字段、类型、关系）
    - 为每个表生成描述文本
    - 向量化表描述并存储
    - _Requirements: 3.1, 3.2, 9.1_
  
  - [x] 12.2 实现 Schema 向量检索方法
    - 向量化用户查询
    - 检索最相关的 Top-5 表
    - 过滤用户无权访问的表
    - _Requirements: 3.1, 3.2_
  
  - [ ]* 12.3 编写 Schema RAG 返回数量的属性测试
    - **Property 4: Schema RAG返回数量限制**
    - **Validates: Requirements 3.1**


  - [x] 12.4 实现 Schema 刷新接口
    - 提供手动刷新 Schema 的 API 接口
    - 支持增量更新
    - _Requirements: 9.3_

- [x] 13. 实现 SQL 生成器（SQL Generator）
  - [x] 13.1 创建 `SQLGenerator` 类
    - 集成 Schema RAG 和 ERNIE API
    - 实现 SQL 生成 Prompt 模板
    - _Requirements: 3.3_
  
  - [x] 13.2 实现 SQL 生成方法 `generate_sql(query, user_permissions)`
    - 调用 Schema RAG 获取相关表结构
    - 构建 SQL 生成 Prompt
    - 调用 ERNIE API 生成 SQL
    - 提取 SQL 文本
    - _Requirements: 3.3, 3.4_
  
  - [x] 13.3 实现明细查询自动添加 LIMIT
    - 检测是否为明细查询（无聚合函数）
    - 自动添加 LIMIT 100
    - _Requirements: 3.6_
  
  - [ ]* 13.4 编写明细查询自动添加 LIMIT 的属性测试
    - **Property 6: 明细查询自动添加LIMIT**
    - **Validates: Requirements 3.6**
  
  - [x] 13.5 实现聚合查询不添加 LIMIT
    - 检测聚合函数（COUNT、SUM、AVG、MAX、MIN、GROUP BY）
    - 不添加 LIMIT 子句
    - _Requirements: 3.7_
  
  - [ ]* 13.6 编写聚合查询不添加 LIMIT 的属性测试
    - **Property 7: 聚合查询不添加LIMIT**
    - **Validates: Requirements 3.7**
  
  - [x] 13.7 实现 Schema RAG 失败降级
    - 当向量检索失败时，使用完整 Schema（限制 10 个常用表）
    - _Requirements: 3.9_


- [x] 14. 实现对话上下文管理器（Context Manager）
  - 创建 `ContextManager` 类
  - 实现对话历史存储（Redis，最近 5 轮）
  - 实现代词引用检测（"它们"、"这些"、"上面的"）
  - 实现实体提取和替换
  - 实现会话超时清理（30 分钟）
  - _Requirements: 27.1, 27.2, 27.3, 27.4, 27.5, 27.6, 27.8_

- [ ]* 15. 编写代词引用检测的属性测试
  - **Property 21: 代词引用检测**
  - **Validates: Requirements 27.2**

- [x] 16. Checkpoint - 意图路由和 SQL 生成验证
  - 测试意图路由器能够正确分类不同类型的查询
  - 测试 Schema RAG 返回相关表结构
  - 测试 SQL 生成器生成正确的 SQL
  - 测试明细查询自动添加 LIMIT
  - 测试聚合查询不添加 LIMIT
  - 确保所有测试通过，询问用户是否有问题

### 阶段 4：报告检索

- [x] 17. 实现报告索引管理
  - [x] 17.1 创建报告索引加载方法
    - 从 MinIO 扫描所有报告文件
    - 提取报告元数据（任务ID、类型、生成时间）
    - 存储到 MySQL `report_index` 表
    - _Requirements: 13.1_
  
  - [x] 17.2 实现报告向量化流程
    - 提取报告内容（HTML/JSON）
    - 按分层策略提取（摘要层、结论层、详情层）
    - 向量化摘要层和结论层
    - 存储向量到 Vector Store
    - _Requirements: 14.1, 14.2, 14.3, 14.4_


  - [x] 17.3 实现资源分析报告内容提取
    - 摘要层：集群数量、健康状态统计
    - 结论层：严重/警告集群列表、关键建议
    - 详情层：所有集群详细指标
    - _Requirements: 24.1_
  
  - [x] 17.4 实现监控分析报告内容提取（BCC/BOS）
    - 摘要层：实例/Bucket 数量、监控周期
    - 结论层：异常实例列表、关键指标异常
    - 详情层：所有实例监控数据
    - _Requirements: 24.2_
  
  - [x] 17.5 实现运营分析报告内容提取
    - 摘要层：数据时间范围、总问题数
    - 结论层：Top 10 问题列表、趋势分析
    - 详情层：所有问题完整信息
    - _Requirements: 24.3_
  
  - [ ]* 17.6 编写分层内容提取的属性测试
    - **Property 15: 分层内容提取**
    - **Validates: Requirements 14.2**

- [x] 18. 实现报告检索器（Report Retriever）
  - [x] 18.1 创建 `ReportRetriever` 类
    - 集成向量存储和 MinIO 客户端
    - 实现时间信息提取方法
    - _Requirements: 13.2, 13.3_
  
  - [x] 18.2 实现报告向量检索方法
    - 向量化查询文本
    - 应用时间过滤
    - 应用时间衰减函数（越新权重越高）
    - 返回 Top-5 报告片段
    - _Requirements: 13.5, 13.6_
  
  - [ ]* 18.3 编写时间范围过滤的属性测试
    - **Property 13: 时间范围过滤**
    - **Validates: Requirements 13.3**


  - [x] 18.4 实现报告内容获取方法
    - 检查 Redis 缓存
    - 从 MinIO 获取完整报告
    - 提取文本内容（HTML/JSON）
    - 缓存到 Redis（24 小时）
    - _Requirements: 13.7, 13.8, 13.9, 16.1, 16.2_
  
  - [x] 18.5 实现报告缓存降级
    - 当 Redis 失败时，直接从 MinIO 读取
    - 实现 LRU 缓存清理策略
    - _Requirements: 16.4, 16.5_

- [x] 19. 实现自动报告向量化（后台任务）
  - 监听 MinIO 新报告上传事件
  - 自动触发报告向量化流程
  - 自动创建知识条目（source=auto）
  - 记录向量化失败日志
  - _Requirements: 14.1, 14.8, 14.9, 14.10, 14.11_

- [x] 20. Checkpoint - 报告检索验证
  - 测试报告索引正确加载
  - 测试报告内容提取（三层策略）
  - 测试报告向量检索返回相关结果
  - 测试报告缓存机制
  - 测试自动向量化流程
  - 确保所有测试通过，询问用户是否有问题

### 阶段 5：知识库管理

- [x] 21. 实现知识库管理器（Knowledge Manager）
  - [x] 21.1 创建 `KnowledgeManager` 类
    - 集成向量存储和数据库连接
    - 实现必填字段验证
    - _Requirements: 17.7_
  
  - [ ]* 21.2 编写知识条目必填字段验证的属性测试
    - **Property 16: 知识条目必填字段验证**
    - **Validates: Requirements 17.7**


  - [x] 21.3 实现知识条目创建方法 `create_entry(entry_data, user_id)`
    - 验证必填字段（title, content）
    - 向量化内容
    - 存储到 MySQL 和向量存储
    - 记录审计日志
    - _Requirements: 17.7, 17.8, 17.9, 17.10, 17.11_
  
  - [ ]* 21.4 编写知识条目内容长度限制的属性测试
    - **Property 17: 知识条目内容长度限制**
    - **Validates: Requirements 17.12**
  
  - [x] 21.5 实现知识条目查询方法
    - 列表查询（分页、过滤、排序）
    - 单个条目查询
    - 全文搜索
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.7, 18.8_
  
  - [x] 21.6 实现知识条目更新方法 `update_entry(entry_id, updates, user_id)`
    - 验证用户权限
    - 重新生成向量
    - 更新 MySQL 和向量存储
    - 支持部分更新（PATCH）
    - 标记手动编辑（manually_edited=true）
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.8, 19.9, 19.10_
  
  - [x] 21.7 实现知识条目软删除方法 `soft_delete_entry(entry_id, user_id)`
    - 验证用户权限
    - MySQL 标记 deleted_at
    - 向量存储标记 is_deleted=true
    - 记录审计日志
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.8_
  
  - [ ]* 21.8 编写软删除一致性的属性测试
    - **Property 18: 软删除一致性**
    - **Validates: Requirements 20.4, 20.5, 20.6**


  - [x] 21.9 实现知识条目向量检索方法 `search_entries(query, top_k, threshold)`
    - 向量化查询
    - 检索 Top-K 条目（K ≤ 3）
    - 过滤低相似度结果（< 0.6）
    - 过滤已删除条目
    - _Requirements: 22.1, 22.2, 22.3, 22.4_
  
  - [x] 21.10 实现定时清理任务
    - 物理删除软删除超过 30 天的条目
    - 每周执行一次
    - _Requirements: 20.7_

- [x] 22. 实现知识库管理二次验证
  - [x] 22.1 创建密码验证接口 `POST /api/v1/knowledge/auth/verify`
    - 验证用户密码与 MySQL 中的哈希匹配
    - 生成知识库管理会话令牌（JWT，30 分钟）
    - 记录验证失败到审计日志
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5_
  
  - [ ]* 22.2 编写密码验证正确性的属性测试
    - **Property 19: 密码验证正确性**
    - **Validates: Requirements 25.3**
  
  - [x] 22.3 实现密码失败锁定机制
    - 记录失败次数到 Redis
    - 连续 5 次失败后锁定 30 分钟
    - _Requirements: 25.6_
  
  - [ ]* 22.4 编写密码失败锁定的属性测试
    - **Property 20: 密码失败锁定机制**
    - **Validates: Requirements 25.6**
  
  - [x] 22.5 实现会话令牌验证中间件
    - 验证请求包含有效的会话令牌
    - 令牌过期时要求重新验证
    - _Requirements: 25.7, 25.8_
  
  - [x] 22.6 实现注销接口 `POST /api/v1/knowledge/auth/logout`
    - 立即失效会话令牌
    - _Requirements: 25.9, 25.10_


- [x] 23. 实现分类与标签管理
  - 实现分类列表接口 `GET /api/v1/knowledge/categories`
  - 实现创建分类接口 `POST /api/v1/knowledge/categories`（仅超级管理员）
  - 实现标签列表接口 `GET /api/v1/knowledge/tags`
  - 实现自动创建标签逻辑
  - 实现标签使用次数更新
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.7_

- [x] 24. 实现向量数据库备份与恢复
  - 实现备份接口 `POST /api/v1/knowledge/vector-store/backup`
  - 实现恢复接口 `POST /api/v1/knowledge/vector-store/restore`
  - 实现重建接口 `POST /api/v1/knowledge/vector-store/rebuild`
  - 备份文件上传到 MinIO `vector-backups/` 目录
  - _Requirements: 26.6, 26.7, 26.8, 26.9, 26.10, 26.11_

- [x] 25. Checkpoint - 知识库管理验证
  - 测试知识条目创建、查询、更新、删除
  - 测试密码二次验证和会话管理
  - 测试软删除和定时清理
  - 测试向量检索返回相关知识条目
  - 测试备份和恢复功能
  - 确保所有测试通过，询问用户是否有问题

### 阶段 6：API 接口实现

- [x] 26. 实现主查询接口
  - [x] 26.1 创建 `POST /api/v1/ai/intelligent-query` 接口
    - 验证用户身份和权限
    - 验证请求体包含 query 字段
    - 验证查询长度（≤1000 字符）
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 7.2, 12.1, 12.2_
  
  - [ ]* 26.2 编写输入验证边界的属性测试
    - **Property 1: 输入验证边界**
    - **Validates: Requirements 1.2, 1.3**


  - [ ]* 26.3 编写未认证请求拒绝的属性测试
    - **Property 11: 未认证请求拒绝**
    - **Validates: Requirements 7.2**
  
  - [x] 26.4 实现 SSE 流式响应
    - 返回 analyzing_intent 状态
    - 返回 querying_data 状态
    - 返回 generating_answer 状态
    - 返回 completed 状态和最终结果
    - _Requirements: 1.4, 1.5_
  
  - [ ]* 26.5 编写流式响应状态序列的属性测试
    - **Property 2: 流式响应状态序列**
    - **Validates: Requirements 1.4, 1.5**
  
  - [x] 26.6 实现查询处理主流程
    - 调用 Intent Router 进行意图分类
    - 根据意图类型路由到对应处理器
    - SQL 查询：Schema RAG → SQL Generator → Security Validator → Query Executor
    - 报告检索：Report Retriever
    - 知识库检索：Knowledge Manager
    - 混合查询：并行执行多个处理器
    - _Requirements: 2.1, 15.1, 15.2_
  
  - [x] 26.7 实现结果自然语言转换
    - 调用 ERNIE API 生成自然语言回答
    - 标注数据来源（database/report/knowledge/mixed）
    - 标注报告生成时间
    - _Requirements: 6.1, 6.2, 6.3, 13.11_
  
  - [x] 26.8 实现超时控制
    - 15 秒提示但继续处理
    - 30 秒强制终止返回部分结果
    - _Requirements: 1.6, 1.7_


- [x] 27. 实现辅助查询接口
  - 实现 `GET /api/v1/ai/query-tables` 接口
  - 实现 `GET /api/v1/ai/report-index` 接口
  - 根据用户权限过滤可访问的表
  - 支持报告类型和时间范围过滤
  - _Requirements: 12.5, 12.6_

- [x] 28. 实现知识库管理接口
  - 实现 `POST /api/v1/knowledge/entries` 接口（创建）
  - 实现 `GET /api/v1/knowledge/entries` 接口（列表）
  - 实现 `GET /api/v1/knowledge/entries/{id}` 接口（详情）
  - 实现 `PUT /api/v1/knowledge/entries/{id}` 接口（更新）
  - 实现 `DELETE /api/v1/knowledge/entries/{id}` 接口（删除）
  - 实现 `GET /api/v1/knowledge/search` 接口（搜索）
  - 实现 `POST /api/v1/knowledge/import` 接口（批量导入）
  - 所有接口验证超级管理员权限和会话令牌
  - _Requirements: 17.1, 18.1, 18.5, 18.7, 19.1, 20.1, 23.1, 23.2_

- [x] 29. 实现错误处理和用户反馈
  - 实现统一错误响应格式
  - 实现友好的错误提示（不暴露技术细节）
  - 实现错误日志记录
  - 实现降级策略（意图分类、Schema RAG、报告缓存）
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 30. 实现详情数据格式优化
  - 实现 JSON 到 Markdown 表格转换
  - 实现数组到 Markdown 列表转换
  - 实现嵌套 JSON 扁平化（点号表示层级）
  - 实现内容截断（超过 2000 字符）
  - _Requirements: 28.1, 28.2, 28.3, 28.4, 28.5, 28.6_

- [ ]* 31. 编写 JSON 到 Markdown 转换的属性测试
  - **Property 22: JSON到Markdown转换**
  - **Validates: Requirements 28.1**

- [ ]* 32. 编写 Markdown 内容截断的属性测试
  - **Property 23: Markdown内容截断**
  - **Validates: Requirements 28.5**


- [x] 33. Checkpoint - API 接口验证
  - 测试主查询接口端到端流程
  - 测试 SQL 查询、报告检索、知识库检索、混合查询
  - 测试 SSE 流式响应
  - 测试错误处理和降级策略
  - 测试知识库管理接口（CRUD）
  - 确保所有测试通过，询问用户是否有问题

### 阶段 7：前端集成

- [x] 34. 创建 AI 查询页面（Vue3）
  - 创建查询输入组件（文本框 + 提交按钮）
  - 实现 SSE 流式响应展示（状态指示器）
  - 实现查询结果展示（自然语言回答 + 原始数据）
  - 实现数据来源标注（database/report/knowledge/mixed）
  - 实现多轮对话支持（会话管理）
  - _Requirements: 1.4, 1.5, 6.1, 12.3_

- [x] 35. 创建知识库管理页面（Vue3）
  - 创建知识条目列表组件（分页、过滤、排序）
  - 创建知识条目创建/编辑表单
  - 创建知识条目详情展示
  - 实现密码二次验证对话框
  - 实现批量导入功能
  - 仅超级管理员可见
  - _Requirements: 17.1, 18.1, 19.1, 20.1, 23.1, 25.1_

- [x] 36. 创建报告索引浏览页面（Vue3）
  - 创建报告列表组件（按类型、时间过滤）
  - 实现报告预览功能
  - 实现报告下载链接
  - _Requirements: 12.6_

- [x] 37. 实现前端错误处理
  - 实现统一错误提示组件
  - 实现网络错误重试
  - 实现超时提示
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 38. Checkpoint - 前端集成验证
  - 测试 AI 查询页面功能完整性
  - 测试知识库管理页面功能完整性
  - 测试流式响应展示
  - 测试多轮对话
  - 测试错误处理
  - 确保所有功能正常工作，询问用户是否有问题


### 阶段 8：测试与优化

- [ ] 39. 编写集成测试
  - [ ]* 39.1 端到端 SQL 查询测试
    - 测试完整的查询流程（意图识别 → SQL 生成 → 安全验证 → 执行 → 结果转换）
  
  - [ ]* 39.2 端到端报告检索测试
    - 测试完整的报告检索流程（意图识别 → 向量检索 → 内容提取 → 结果生成）
  
  - [ ]* 39.3 端到端知识库检索测试
    - 测试完整的知识库检索流程（意图识别 → 向量检索 → 结果生成）
  
  - [ ]* 39.4 端到端混合查询测试
    - 测试混合查询的并行执行和结果合并

- [ ]* 40. 编写审计日志完整性的属性测试
  - **Property 12: 审计日志完整性**
  - **Validates: Requirements 8.1, 8.2, 8.3**

- [ ] 41. 性能优化
  - 优化向量检索性能（使用 FAISS IVF 索引）
  - 优化数据库查询（添加索引）
  - 优化 Redis 缓存策略
  - 优化 ERNIE API 调用（批量、合并）
  - _Requirements: 11.1, 11.2_

- [ ] 42. 安全加固
  - 实施速率限制（防止滥用）
  - 实施 HTTPS/TLS 加密
  - 实施 IP 白名单（如需要）
  - 定期备份（MySQL、向量数据库）
  - _Requirements: 8.6_

- [ ] 43. 监控和日志
  - 配置结构化日志格式
  - 配置关键指标监控（响应时间、成功率、拒绝率）
  - 配置告警规则（响应时间 > 10s、失败率 > 10%）
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_


- [ ] 44. 文档编写
  - 编写 API 接口文档（OpenAPI/Swagger）
  - 编写部署文档（Docker Compose 配置、环境变量）
  - 编写用户使用指南（如何提问、典型场景）
  - 编写运维手册（备份恢复、故障排查）

- [ ] 45. 最终验证和部署准备
  - 运行所有单元测试、属性测试、集成测试
  - 验证测试覆盖率（单元测试 ≥ 80%）
  - 验证所有 23 个正确性属性都有对应的属性测试
  - 执行性能测试（2 个并发查询）
  - 执行安全测试（SQL 注入、XSS、CSRF）
  - 准备生产环境配置文件
  - 确保所有功能正常，询问用户是否可以部署

## Notes

### 任务执行说明

- **渐进式实现**：每个任务完成后都能看到可工作的进展
- **测试驱动**：核心功能都有对应的属性测试和单元测试
- **可选任务**：标记 `*` 的测试任务为可选，可以跳过以加快 MVP 开发
- **Checkpoint**：在关键阶段设置检查点，确保功能正确后再继续

### 属性测试配置

- **测试库**：使用 Python `hypothesis` 库
- **迭代次数**：每个属性测试最少运行 100 次
- **标签格式**：`# Feature: ai-intelligent-query, Property N: [属性描述]`

### 依赖关系

- 阶段 1 必须先完成（基础设施）
- 阶段 2 依赖阶段 1（核心组件依赖数据库和配置）
- 阶段 3 依赖阶段 2（意图路由依赖审计和安全组件）
- 阶段 4 依赖阶段 1、2（报告检索依赖向量存储和审计）
- 阶段 5 依赖阶段 1、2、4（知识库依赖向量存储和报告向量化）
- 阶段 6 依赖阶段 1-5（API 接口整合所有组件）
- 阶段 7 依赖阶段 6（前端依赖后端 API）
- 阶段 8 可以与阶段 7 并行（测试和优化）

### 预估工作量

- **阶段 1**：2-3 天（基础设施搭建）
- **阶段 2**：3-4 天（核心组件实现）
- **阶段 3**：4-5 天（意图路由和 SQL 生成）
- **阶段 4**：3-4 天（报告检索）
- **阶段 5**：4-5 天（知识库管理）
- **阶段 6**：3-4 天（API 接口）
- **阶段 7**：3-4 天（前端集成）
- **阶段 8**：2-3 天（测试与优化）

**总计**：约 24-32 天（按每天 6-8 小时计算）

### 技术决策

- **向量数据库**：推荐使用 FAISS（轻量级、易部署）
- **Embedding 模型**：推荐使用 bge-small-zh（开源、性能好）
- **ERNIE API**：使用百度文心一言 ernie-4.5-8k-preview 模型
- **测试框架**：pytest + hypothesis（属性测试）
- **前端框架**：Vue 3 + Composition API

### 下一步

完成任务列表审批后，可以开始执行任务：
1. 打开 `.kiro/specs/ai-intelligent-query/tasks.md` 文件
2. 点击任务旁边的 "Start task" 按钮
3. 系统将逐个引导完成每个任务
