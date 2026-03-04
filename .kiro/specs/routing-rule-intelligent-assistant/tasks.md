# 实现计划: 路由规则创建智能辅助

## 概述

本实现计划将路由规则创建智能辅助功能分解为可执行的任务。该功能通过智能化手段降低路由规则创建的门槛，提高规则创建的准确性和效率。

核心功能包括：智能输入模式切换、自然语言到正则表达式的AI转换、实时验证和冲突检测、测试匹配、智能字段辅助、规则模板、正则表达式可视化、规则预览和影响预测、错误恢复和草稿管理。

技术栈：FastAPI（后端）、Vue 3 + Element Plus（前端）、ERNIE API（AI转换）、MySQL（数据存储）、pytest-hypothesis（属性测试）。

## 任务列表

- [x] 1. 数据库设计和初始化
  - [x] 1.1 更新 mysql-init.sql 添加 rule_templates 表
    - 在 `backend/config/mysql-init.sql` 中添加表定义
    - 定义表结构：id, name, category, description, pattern, intent_type, priority, metadata, is_system, created_by, created_at, updated_at
    - 添加索引：idx_category, idx_intent_type
    - _需求: 8.1, 8.2_
  
  - [x] 1.2 更新 mysql-init.sql 添加 rule_drafts 表
    - 在 `backend/config/mysql-init.sql` 中添加表定义
    - 定义表结构：id, user_id, draft_data (JSON), created_at, updated_at
    - 添加索引：idx_user_id, idx_updated_at
    - _需求: 18.1, 18.2, 18.5_
  
  - [x] 1.3 创建 SQLAlchemy 模型
    - 创建 `backend/app/models/rule_template.py` 定义 RuleTemplate 模型
    - 创建 `backend/app/models/rule_draft.py` 定义 RuleDraft 模型
    - 在 `backend/app/models/__init__.py` 中导出新模型
    - _需求: 8.1, 18.1_
  
  - [x] 1.4 初始化规则模板数据
    - 创建数据初始化脚本 `backend/scripts/init_rule_templates.py`
    - 插入至少10个常见场景模板（IP查询、实例ID查询、统计查询、报告查询、知识查询等）
    - 验证模板数据的完整性
    - _需求: 8.1, 8.2_


- [x] 2. 后端服务层实现
  - [x] 2.1 实现自然语言转换服务
    - 创建 `backend/app/services/routing/nl_converter.py`
    - 实现 `NLConverter` 类，调用ERNIE API进行自然语言到正则表达式的转换
    - 实现匹配示例生成逻辑（至少3个示例）
    - 实现置信度计算
    - 添加错误处理和重试机制（最多3次，指数退避）
    - _需求: 2.1, 2.2, 2.3, 2.7_
  
  - [x] 2.2 实现正则表达式验证服务
    - 创建 `backend/app/services/routing/regex_validator.py`
    - 实现 `RegexValidator` 类，验证正则表达式语法
    - 实现语法错误检测和错误位置定位
    - 实现复杂度评分算法（基于元素数量和嵌套深度）
    - _需求: 3.1, 3.2, 3.3, 12.6_
  
  - [x] 2.3 实现冲突检测服务
    - 创建 `backend/app/services/routing/conflict_detector.py`
    - 实现 `ConflictDetector` 类，检测规则冲突
    - 实现完全相同模式检测
    - 实现语义相似度检测（使用Embedding模型，阈值0.8）
    - 实现正则表达式包含关系检测
    - 实现冲突严重程度评估（高、中、低）
    - _需求: 3.4, 3.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
  
  - [x] 2.4 实现匹配测试服务
    - 创建 `backend/app/services/routing/match_tester.py`
    - 实现 `MatchTester` 类，测试正则表达式匹配
    - 实现单个查询匹配测试
    - 实现批量查询匹配测试
    - 实现匹配文本和位置提取
    - 实现匹配成功率统计
    - _需求: 4.2, 4.3, 4.5, 4.6, 11.2, 11.4, 11.5_
  
  - [x] 2.5 实现智能辅助服务
    - 创建 `backend/app/services/routing/intelligent_assistant.py`
    - 实现 `IntelligentAssistant` 类
    - 实现描述生成功能（基于匹配模式和意图类型）
    - 实现关键词提取功能（从自然语言和正则表达式）
    - 实现表推荐功能（基于关键词和向量检索）
    - 实现优先级建议功能（基于规则类型）
    - _需求: 5.1, 5.2, 5.5, 6.1, 6.2, 6.3, 7.2, 7.3, 13.1, 13.2, 13.3, 13.4_
  
  - [x] 2.6 实现影响预测服务
    - 创建 `backend/app/services/routing/impact_predictor.py`
    - 实现 `ImpactPredictor` 类
    - 实现历史查询数据分析（过去30天）
    - 实现受影响查询数量和百分比计算
    - 实现预期准确率变化预测
    - 实现使用频率预测
    - _需求: 16.1, 16.2, 16.3, 16.4, 16.5_
  
  - [x] 2.7 实现模板管理服务
    - 创建 `backend/app/services/routing/template_manager.py`
    - 实现 `TemplateManager` 类
    - 实现模板查询功能（支持分类过滤）
    - 实现模板应用功能
    - 实现自定义模板保存功能
    - 实现模板导入导出功能
    - _需求: 8.1, 8.3, 8.4, 8.6, 8.7_
  
  - [x] 2.8 实现草稿管理服务
    - 创建 `backend/app/services/routing/draft_manager.py`
    - 实现 `DraftManager` 类
    - 实现草稿保存功能
    - 实现草稿查询功能
    - 实现草稿恢复功能
    - 实现草稿删除功能
    - _需求: 18.1, 18.2, 18.5, 18.6, 18.7_


- [-] 3. 后端API接口实现
  - [x] 3.1 实现自然语言转换API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/convert` 端点
    - 实现请求参数验证（natural_language, intent_type）
    - 调用 NLConverter 服务
    - 实现响应格式化（regex, explanation, examples, confidence）
    - 添加错误处理（ERNIE_API_ERROR）
    - _需求: 2.1, 2.2, 2.3_
  
  - [x] 3.2 实现正则表达式验证API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/validate` 端点
    - 实现请求参数验证（regex, intent_type, exclude_rule_id）
    - 调用 RegexValidator 和 ConflictDetector 服务
    - 实现响应格式化（is_valid, syntax_errors, conflicts, complexity_score）
    - 添加错误处理（VALIDATION_TIMEOUT）
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 3.3 实现测试匹配API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/test-match` 端点
    - 实现请求参数验证（regex, test_queries）
    - 调用 MatchTester 服务
    - 实现响应格式化（results, match_rate, total_count, matched_count）
    - 添加错误处理（EMPTY_TEST_QUERIES）
    - _需求: 4.2, 4.3, 4.5, 4.6_
  
  - [x] 3.4 实现关键词提取API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/extract-keywords` 端点
    - 实现请求参数验证（pattern, pattern_type）
    - 调用 IntelligentAssistant 服务的关键词提取功能
    - 实现响应格式化（keywords with word, weight, type）
    - _需求: 6.1, 6.2, 6.3, 6.4_
  
  - [x] 3.5 实现表推荐API
    - 在 `backend/app/api/v1/routing.py` 中添加 `GET /api/v1/routing/recommend-tables` 端点
    - 实现查询参数验证（keywords, intent_type）
    - 调用 IntelligentAssistant 服务的表推荐功能
    - 实现响应格式化（tables with name, category, description, field_count, relevance_score, reason）
    - 添加错误处理（TABLE_RECOMMENDATION_ERROR）
    - _需求: 7.1, 7.2, 7.3, 7.6_
  
  - [x] 3.6 实现规则模板API
    - 在 `backend/app/api/v1/routing.py` 中添加 `GET /api/v1/routing/templates` 端点
    - 实现查询参数验证（category）
    - 调用 TemplateManager 服务
    - 实现响应格式化（templates列表）
    - 添加错误处理（TEMPLATE_LOAD_ERROR）
    - _需求: 8.1, 8.2, 8.4_
  
  - [x] 3.7 实现智能描述生成API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/generate-description` 端点
    - 实现请求参数验证（pattern, intent_type, keywords）
    - 调用 IntelligentAssistant 服务的描述生成功能
    - 实现响应格式化（description, purpose, applicable_scenarios）
    - _需求: 5.1, 5.2, 5.5_
  
  - [x] 3.8 实现优先级建议API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/suggest-priority` 端点
    - 实现请求参数验证（pattern, intent_type, keywords）
    - 调用 IntelligentAssistant 服务的优先级建议功能
    - 实现响应格式化（suggested_priority, priority_range, category, reason, conflicts）
    - _需求: 13.1, 13.2, 13.3, 13.4, 13.5, 13.7_
  
  - [x] 3.9 实现规则影响预测API
    - 在 `backend/app/api/v1/routing.py` 中添加 `POST /api/v1/routing/predict-impact` 端点
    - 实现请求参数验证（pattern, intent_type）
    - 调用 ImpactPredictor 服务
    - 实现响应格式化（affected_query_count, affected_query_percentage, sample_queries, expected_accuracy_change, expected_usage_frequency, warning）
    - 添加错误处理（HISTORY_QUERY_ERROR）
    - _需求: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_
  
  - [x] 3.10 实现草稿管理API
    - 在 `backend/app/api/v1/routing.py` 中添加草稿相关端点
    - `POST /api/v1/routing/drafts` - 保存草稿
    - `GET /api/v1/routing/drafts` - 查询草稿列表
    - `GET /api/v1/routing/drafts/{id}` - 获取草稿详情
    - `DELETE /api/v1/routing/drafts/{id}` - 删除草稿
    - 调用 DraftManager 服务
    - 添加错误处理（DRAFT_LOAD_ERROR）
    - _需求: 18.1, 18.2, 18.4, 18.5, 18.6, 18.7_


- [x] 4. 前端API客户端实现
  - [x] 4.1 创建路由辅助API客户端
    - 创建 `frontend/src/api/routing-assistant.js`
    - 实现 `convertNaturalLanguage(naturalLanguage, intentType)` 方法
    - 实现 `validateRegex(regex, intentType, excludeRuleId)` 方法
    - 实现 `testMatch(regex, testQueries)` 方法
    - 实现 `extractKeywords(pattern, patternType)` 方法
    - 实现 `recommendTables(keywords, intentType)` 方法
    - 实现 `getTemplates(category)` 方法
    - 实现 `generateDescription(pattern, intentType, keywords)` 方法
    - 实现 `suggestPriority(pattern, intentType, keywords)` 方法
    - 实现 `predictImpact(pattern, intentType)` 方法
    - 实现草稿管理方法（saveDraft, getDrafts, getDraft, deleteDraft）
    - 统一错误处理和响应格式
    - _需求: 所有API相关需求_


- [x] 5. 前端核心组件实现
  - [x] 5.1 实现智能输入组件
    - 创建 `frontend/src/components/routing/IntelligentInput.vue`
    - 实现模式切换UI（自然语言/正则表达式）
    - 实现自然语言输入框和转换按钮
    - 实现正则表达式编辑器（带语法高亮）
    - 实现转换加载状态显示
    - 实现转换结果显示（正则表达式、解释、示例）
    - 实现模式切换时保留内容
    - 实现防抖优化（500ms）
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.6, 3.6_
  
  - [x] 5.2 实现验证组件
    - 创建 `frontend/src/components/routing/ValidationPanel.vue`
    - 实现验证结果显示区域
    - 实现语法错误显示（错误信息、位置、建议）
    - 实现冲突警告显示（冲突规则列表、严重程度）
    - 实现复杂度评分显示
    - 实现成功提示显示
    - 实现详情展开/收起功能
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 10.5, 10.6, 12.6_
  
  - [x] 5.3 实现测试组件
    - 创建 `frontend/src/components/routing/TestMatchPanel.vue`
    - 实现测试查询输入框（支持多行）
    - 实现单个测试和批量测试按钮
    - 实现测试结果列表显示
    - 实现匹配文本高亮显示
    - 实现匹配率统计显示
    - 实现"保存为测试用例"功能
    - 实现文件导入功能
    - 实现结果导出功能
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_
  
  - [x] 5.4 实现辅助组件
    - 创建 `frontend/src/components/routing/AssistantPanel.vue`
    - 实现描述生成区域（显示生成的描述、允许编辑）
    - 实现关键词提取和编辑区域（显示关键词列表、支持添加/删除/编辑、显示权重）
    - 实现表推荐区域（显示推荐表列表、支持搜索和过滤、支持多选）
    - 实现优先级建议区域（显示建议优先级、显示理由、允许调整）
    - 实现响应式更新（意图类型改变时更新描述）
    - _需求: 5.1, 5.2, 5.3, 5.4, 6.1, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 13.1, 13.5, 13.6_
  
  - [x] 5.5 实现模板选择器组件
    - 创建 `frontend/src/components/routing/TemplateSelector.vue`
    - 实现模板列表显示（分类、名称、描述）
    - 实现模板搜索和过滤功能
    - 实现模板预览对话框
    - 实现应用模板功能
    - 实现自定义模板保存功能
    - 实现模板导入导出功能
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_
  
  - [x] 5.6 实现可视化组件
    - 创建 `frontend/src/components/routing/RegexVisualizer.vue`
    - 集成正则表达式可视化库（如 regexper 或 railroad-diagrams）
    - 实现铁路图显示
    - 实现正则元素高亮（字符类、量词、分组等）
    - 实现交互式点击（点击图表高亮对应文本）
    - 实现复杂度评分显示
    - _需求: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [x] 5.7 实现预览组件
    - 创建 `frontend/src/components/routing/RulePreview.vue`
    - 实现规则完整信息显示（所有字段）
    - 实现生成的正则表达式显示（自然语言模式）
    - 实现推荐表和关键词显示
    - 实现测试结果摘要显示
    - 实现冲突警告显示
    - 实现影响预测显示
    - 实现返回编辑按钮
    - _需求: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_


- [x] 6. 前端主对话框集成
  - [x] 6.1 修改规则创建对话框
    - 修改 `frontend/src/views/routing/RoutingRules.vue` 中的创建对话框
    - 集成 IntelligentInput 组件
    - 集成 ValidationPanel 组件
    - 集成 TestMatchPanel 组件
    - 集成 AssistantPanel 组件
    - 集成 TemplateSelector 组件
    - 集成 RegexVisualizer 组件
    - 实现组件间数据流和事件传递
    - 实现表单验证和提交逻辑
    - _需求: 所有UI相关需求_
  
  - [x] 6.2 实现上下文帮助系统
    - 为每个表单字段添加帮助图标
    - 实现帮助内容弹出框（详细说明、示例）
    - 实现内联提示文本
    - 实现字段间关联说明
    - 实现上下文相关的动态帮助
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 6.3 实现规则预览流程
    - 在保存前显示预览对话框
    - 集成 RulePreview 组件
    - 实现预览数据收集和格式化
    - 实现从预览返回编辑功能
    - 实现从预览直接保存功能
    - _需求: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_
  
  - [x] 6.4 实现草稿管理功能
    - 实现自动保存逻辑（每30秒）
    - 实现关闭对话框时的保存提示
    - 实现打开对话框时的草稿恢复提示
    - 实现草稿列表管理界面
    - 实现草稿删除功能
    - 使用 localStorage 作为本地缓存
    - _需求: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7_


- [x] 7. 交互式教程实现
  - [x] 7.1 创建教程组件
    - 创建 `frontend/src/components/routing/InteractiveTutorial.vue`
    - 实现教程步骤定义（至少5个步骤）
    - 实现高亮和提示引导
    - 实现步骤导航（上一步、下一步、跳过）
    - 实现进度指示器
    - _需求: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [x] 7.2 集成教程到创建对话框
    - 检测首次使用（使用 localStorage）
    - 在首次打开时自动显示教程
    - 实现"重新查看教程"入口
    - 实现教程完成后的总结和最佳实践
    - _需求: 17.1, 17.4, 17.6, 17.7_

- [x] 8. 可访问性增强
  - [x] 8.1 实现键盘导航
    - 为所有表单字段添加 tabindex
    - 实现 Tab 键在字段间切换
    - 实现 Enter 键提交表单
    - 实现 Escape 键关闭对话框
    - 实现快捷键提示
    - _需求: 20.1, 20.3, 20.4, 20.5_
  
  - [x] 8.2 添加ARIA标签
    - 为所有交互元素添加 aria-label
    - 为表单字段添加 aria-describedby
    - 为状态变化添加 aria-live 区域
    - 为按钮添加 aria-pressed 状态
    - 为对话框添加 aria-modal 属性
    - _需求: 20.2, 20.6_
  
  - [x] 8.3 颜色对比度优化
    - 检查所有文本和背景的颜色对比度
    - 确保符合 WCAG AA 标准（至少 4.5:1）
    - 优化错误提示、警告和成功消息的颜色
    - 添加颜色之外的视觉提示（图标、边框）
    - _需求: 20.7_


- [x] 9. 性能优化
  - [x] 9.1 实现防抖和节流
    - 为验证请求实现防抖（500ms）
    - 为关键词提取实现防抖（500ms）
    - 为表推荐实现防抖（500ms）
    - 为自动保存实现节流（30秒）
    - _需求: 3.6, 19.4_
  
  - [x] 9.2 实现数据缓存
    - 实现表列表缓存（使用 Vuex 或 Pinia）
    - 实现模板列表缓存
    - 实现验证结果缓存（相同正则表达式）
    - 实现后台数据预加载
    - _需求: 19.5, 19.6_
  
  - [x] 9.3 优化API调用
    - 实现请求合并（相同请求只发送一次）
    - 实现请求取消（用户快速切换时）
    - 实现请求优先级（验证 > 辅助功能）
    - 添加加载进度指示器
    - _需求: 19.7_
  
  - [x] 9.4 性能监控
    - 添加性能埋点（响应时间、API调用时间）
    - 实现性能日志记录
    - 添加慢请求告警（超过阈值）
    - _需求: 19.1, 19.2, 19.3_


- [x] 10. 单元测试
  - [x] 10.1 后端服务层单元测试
    - 测试 NLConverter 服务（正常转换、空输入、API失败）
    - 测试 RegexValidator 服务（有效正则、无效正则、复杂度计算）
    - 测试 ConflictDetector 服务（完全相同、语义相似、包含关系）
    - 测试 MatchTester 服务（单个匹配、批量匹配、统计准确性）
    - 测试 IntelligentAssistant 服务（描述生成、关键词提取、表推荐、优先级建议）
    - 测试 ImpactPredictor 服务（影响预测、历史数据分析）
    - 测试 TemplateManager 服务（模板查询、应用、保存）
    - 测试 DraftManager 服务（草稿保存、查询、恢复、删除）
    - 使用 pytest 和 pytest-asyncio
    - 覆盖率目标：> 80%
  
  - [x] 10.2 后端API接口单元测试
    - 测试所有10个API端点的正常情况
    - 测试所有API端点的错误情况（空输入、无效参数、服务失败）
    - 测试请求参数验证
    - 测试响应格式
    - 测试错误处理
    - 使用 pytest 和 httpx
    - 覆盖率目标：> 80%
  
  - [x] 10.3 前端组件单元测试
    - 测试 IntelligentInput 组件（模式切换、转换、验证）
    - 测试 ValidationPanel 组件（显示验证结果、错误、冲突）
    - 测试 TestMatchPanel 组件（测试匹配、批量测试、统计）
    - 测试 AssistantPanel 组件（描述生成、关键词编辑、表选择）
    - 测试 TemplateSelector 组件（模板列表、搜索、应用）
    - 测试 RegexVisualizer 组件（可视化显示、交互）
    - 测试 RulePreview 组件（预览显示、返回编辑）
    - 使用 Vitest 和 @testing-library/vue
    - 覆盖率目标：> 80%


- [-] 11. 属性测试（Property-Based Testing）
  - [ ] 11.1 属性1测试：自然语言转换完整性
    - **属性1: 自然语言转换完整性**
    - **验证需求: 2.1, 2.2, 2.3**
    - 使用 pytest-hypothesis 生成随机自然语言描述和意图类型
    - 验证返回结果包含 regex, explanation, examples（至少3个）, confidence
  
  - [ ] 11.2 属性2测试：转换响应时间
    - **属性2: 转换响应时间**
    - **验证需求: 2.7**
    - 验证 ERNIE API 调用在5秒内返回结果
  
  - [ ] 11.3 属性3测试：正则表达式验证完整性
    - **属性3: 正则表达式验证完整性**
    - **验证需求: 3.1, 3.2, 3.3**
    - 使用 pytest-hypothesis 生成随机正则表达式
    - 验证返回结果包含 is_valid, syntax_errors, conflicts, complexity_score
  
  - [ ] 11.4 属性4测试：验证防抖机制
    - **属性4: 验证防抖机制**
    - **验证需求: 3.6, 19.4**
    - 模拟连续输入事件
    - 验证验证请求在停止输入500ms后才执行
  
  - [ ] 11.5 属性5测试：冲突检测完整性
    - **属性5: 冲突检测完整性**
    - **验证需求: 3.4, 3.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**
    - 使用 pytest-hypothesis 生成随机匹配模式
    - 验证识别所有类型的冲突（完全相同、语义相似、包含关系）
    - 验证每个冲突包含严重程度和详细描述
  
  - [ ] 11.6 属性6测试：测试匹配完整性
    - **属性6: 测试匹配完整性**
    - **验证需求: 4.2, 4.3, 4.5, 4.6**
    - 使用 pytest-hypothesis 生成随机正则表达式和测试查询
    - 验证每个查询返回 matched, confidence, matched_text, match_position
  
  - [ ] 11.7 属性7测试：批量测试统计准确性
    - **属性7: 批量测试统计准确性**
    - **验证需求: 11.2, 11.4, 11.5**
    - 验证匹配成功率 = 匹配查询数 / 总查询数
  
  - [ ] 11.8 属性8-9测试：智能描述生成
    - **属性8: 智能描述生成**
    - **验证需求: 5.1, 5.2, 5.5**
    - **属性9: 描述响应式更新**
    - **验证需求: 5.4**
    - 验证描述包含规则目的和适用场景
    - 验证意图类型改变时描述更新
  
  - [ ] 11.9 属性10-11测试：关键词提取
    - **属性10: 关键词提取完整性**
    - **验证需求: 6.1, 6.2, 6.4, 6.6**
    - **属性11: 正则字面量提取**
    - **验证需求: 6.3**
    - 验证从自然语言提取名词和动词
    - 验证从正则表达式提取字面量文本
    - 验证每个关键词包含权重
  
  - [ ] 11.10 属性12-13测试：表推荐
    - **属性12: 表推荐相关性**
    - **验证需求: 7.2, 7.3, 7.6**
    - **属性13: 表推荐搜索过滤**
    - **验证需求: 7.4**
    - 验证推荐表包含名称、分类、描述、字段数量、相关性评分
    - 验证搜索过滤的正确性
  
  - [ ] 11.11 属性14-15测试：模板和复杂度
    - **属性14: 模板应用完整性**
    - **验证需求: 8.3, 8.4**
    - **属性15: 正则复杂度评分**
    - **验证需求: 12.6**
    - 验证模板应用后所有字段填充正确
    - 验证复杂度评分在0-10之间
  
  - [ ] 11.12 属性16-17测试：优先级建议
    - **属性16: 优先级建议准确性**
    - **验证需求: 13.1, 13.2, 13.3, 13.4, 13.5**
    - **属性17: 优先级冲突检测**
    - **验证需求: 13.7**
    - 验证强制规则（90-100）、业务规则（50-89）、通用规则（1-49）
    - 验证优先级冲突检测
  
  - [ ] 11.13 属性18测试：规则预览完整性
    - **属性18: 规则预览完整性**
    - **验证需求: 14.2, 14.3, 14.4, 14.5, 14.6**
    - 验证预览显示所有字段、生成的正则、推荐表、测试结果、冲突警告
  
  - [ ] 11.14 属性19-21测试：自然语言理解
    - **属性19: 自然语言模式理解**
    - **验证需求: 15.1, 15.2, 15.3**
    - **属性20: 数量词理解**
    - **验证需求: 15.4**
    - **属性21: 多语言支持**
    - **验证需求: 15.7**
    - 验证理解"包含"、"以...开头"、"以...结尾"、"或"、"且"
    - 验证理解"多个"、"至少"、"最多"等数量词
    - 验证中英文混合描述
  
  - [ ] 11.15 属性22测试：影响预测准确性
    - **属性22: 影响预测准确性**
    - **验证需求: 16.1, 16.2, 16.3, 16.4, 16.5**
    - 验证基于历史数据计算受影响查询数量、百分比、准确率变化
  
  - [ ] 11.16 属性23-24测试：状态保持和草稿管理
    - **属性23: 状态保持一致性**
    - **验证需求: 1.3, 18.1, 18.2**
    - **属性24: 草稿管理完整性**
    - **验证需求: 18.5, 18.6**
    - 验证模式切换、对话框关闭、自动保存时内容保留
    - 验证草稿列表显示保存时间，支持恢复和删除
  
  - [ ] 11.17 属性25-26测试：性能要求
    - **属性25: 响应时间性能**
    - **验证需求: 19.1, 19.2, 19.3**
    - **属性26: 缓存命中率**
    - **验证需求: 19.5**
    - 验证用户输入（100ms）、验证（500ms）、ERNIE API（5s）
    - 验证重复查询从缓存获取，响应时间减少
  
  - [ ] 11.18 属性27-28测试：可访问性
    - **属性27: 键盘导航完整性**
    - **验证需求: 20.1, 20.3, 20.4, 20.5**
    - **属性28: ARIA标签完整性**
    - **验证需求: 20.2, 20.6**
    - 验证Tab键切换、Enter键提交、Escape键关闭
    - 验证所有交互元素有ARIA标签和状态通知


- [x] 12. 集成测试
  - [x] 12.1 端到端规则创建流程测试
    - 使用 Playwright 或 Cypress
    - 测试完整的规则创建流程（打开对话框 → 输入 → 转换 → 验证 → 测试 → 保存）
    - 测试自然语言模式流程
    - 测试正则表达式模式流程
    - 测试模板应用流程
    - 测试草稿保存和恢复流程
    - 覆盖率目标：> 70%
  
  - [x] 12.2 前后端交互测试
    - 测试所有API调用的正确性
    - 测试错误处理和降级策略
    - 测试并发请求处理
    - 测试请求取消和重试
  
  - [x] 12.3 数据库操作测试
    - 测试规则模板的CRUD操作
    - 测试草稿的CRUD操作
    - 测试冲突检测的数据库查询
    - 测试影响预测的历史数据查询
  
  - [x] 12.4 用户场景测试
    - 测试新用户首次使用（交互式教程）
    - 测试熟练用户快速创建规则
    - 测试错误恢复场景（API失败、网络中断）
    - 测试可访问性场景（键盘导航、屏幕阅读器）


- [x] 13. 性能测试
  - [x] 13.1 响应时间测试
    - 测试用户输入响应时间（< 100ms）
    - 测试验证响应时间（< 500ms）
    - 测试ERNIE API响应时间（< 5s）
    - 测试关键词提取响应时间
    - 测试表推荐响应时间
    - 使用 pytest-benchmark
  
  - [x] 13.2 负载测试
    - 测试并发用户创建规则（10、50、100用户）
    - 测试大量规则的冲突检测（100、500、1000规则）
    - 测试批量测试的性能（10、50、100查询）
    - 使用 locust 进行负载测试
  
  - [x] 13.3 缓存效果测试
    - 测试表列表缓存命中率
    - 测试模板列表缓存命中率
    - 测试验证结果缓存命中率
    - 测试缓存对响应时间的影响
  
  - [x] 13.4 性能优化验证
    - 验证防抖优化效果（减少API调用次数）
    - 验证请求合并效果
    - 验证数据预加载效果
    - 生成性能测试报告


- [x] 14. 文档和部署
  - [x] 14.1 API文档更新
    - 更新 FastAPI 自动生成的 API 文档
    - 为每个新增端点添加详细说明和示例
    - 添加错误码说明
    - 添加请求/响应示例
  
  - [x] 14.2 用户文档编写
    - 编写功能使用指南
    - 编写自然语言模式使用说明
    - 编写正则表达式模式使用说明
    - 编写模板使用指南
    - 编写常见问题解答（FAQ）
  
  - [x] 14.3 开发者文档编写
    - 编写架构设计文档
    - 编写API接口文档
    - 编写组件使用文档
    - 编写测试指南
    - 编写部署指南
  
  - [x] 14.4 数据库迁移脚本
    - 确保迁移脚本可以在现有数据库上安全执行
    - 添加回滚脚本
    - 测试迁移脚本在开发、测试、生产环境
  
  - [x] 14.5 部署准备
    - 更新 `deploy.sh` 脚本（包含新的迁移）
    - 更新 `pack-offline.sh` 脚本
    - 更新 `mysql-init.sql`（包含新表定义）
    - 准备初始化数据脚本（规则模板）
  
  - [x] 14.6 部署验证
    - 在外网服务器部署并测试
    - 打包离线部署包
    - 在内网服务器部署并测试
    - 验证所有功能正常工作


- [x] 15. 最终检查点
  - 确保所有测试通过（单元测试、属性测试、集成测试、性能测试）
  - 确保代码覆盖率达到目标（单元测试 > 80%，属性测试 100%，集成测试 > 70%）
  - 确保所有API文档完整
  - 确保用户文档和开发者文档完整
  - 确保部署脚本和迁移脚本经过测试
  - 确保可访问性测试通过
  - 确保性能测试达到要求
  - 向用户演示功能并收集反馈

## 注意事项

1. **任务标记说明**:
   - `[ ]` - 未开始的任务
   - `[x]` - 已完成的任务
   - `[ ]*` - 可选任务（属性测试子任务）

2. **属性测试说明**:
   - 所有属性测试子任务（11.1-11.18）标记为可选（`[ ]*`）
   - 这些测试用于验证系统的正确性属性
   - 每个属性测试对应设计文档中定义的正确性属性
   - 使用 pytest-hypothesis 进行属性测试

3. **实现顺序建议**:
   - 按照任务编号顺序实现（1 → 2 → 3 → ... → 15）
   - 数据库表定义必须首先完成（直接修改 mysql-init.sql）
   - 后端服务层和API层可以并行开发
   - 前端组件开发依赖后端API完成
   - 测试可以在开发过程中逐步进行

4. **依赖关系**:
   - 任务3（后端API）依赖任务2（后端服务层）
   - 任务5-6（前端组件）依赖任务4（前端API客户端）
   - 任务12（集成测试）依赖任务1-6完成
   - 任务14（部署）依赖所有开发和测试任务完成

5. **质量要求**:
   - 所有代码必须通过 linting 检查
   - 所有API必须有完整的错误处理
   - 所有组件必须有单元测试
   - 所有功能必须有集成测试
   - 所有性能要求必须满足

6. **文档要求**:
   - 所有API必须有详细的文档和示例
   - 所有组件必须有使用说明
   - 所有复杂逻辑必须有注释
   - 所有公共方法必须有docstring

7. **部署注意事项**:
   - 新表定义已包含在 mysql-init.sql 中
   - 新功能必须向后兼容
   - 部署前必须在测试环境验证
   - 部署后必须进行烟雾测试

## 参考文档

- 需求文档: `requirements.md`
- 设计文档: `design.md`
- 功能逻辑文档: `mcp/.kiro/steering/功能逻辑.md`
- API响应格式规范: `mcp/.kiro/steering/api-response-format.md`
- 项目状态: `mcp/.kiro/steering/PROJECT_STATUS.md`

