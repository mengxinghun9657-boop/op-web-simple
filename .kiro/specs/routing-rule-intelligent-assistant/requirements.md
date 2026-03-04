# 需求文档 - 路由规则创建智能辅助

## 简介

本文档定义了路由规则创建智能辅助功能的需求。当前路由规则创建界面存在用户体验问题：用户不知道如何编写正则表达式，不清楚自然语言和正则表达式的区别，缺少实时验证和测试功能，描述、关键词等字段的作用不明确。

本次优化将通过智能输入模式切换、自然语言到正则表达式的自动转换、实时验证、测试匹配、智能字段辅助和快速示例模板等功能，降低路由规则创建的门槛，提高准确性和效率。

## 术语表

- **Pattern**: 匹配模式，用于识别用户查询的规则表达式
- **Regex**: 正则表达式，用于精确匹配文本模式的形式化语言
- **Natural_Language_Pattern**: 自然语言模式，用户用日常语言描述的匹配规则
- **ERNIE**: 百度文心大模型，用于自然语言理解和转换
- **Intent_Type**: 意图类型，包括 sql、rag_knowledge、rag_report、chat
- **Metadata**: 元数据，包含推荐表名、关键词等辅助信息
- **Validation**: 验证，检查正则表达式语法和规则冲突
- **Confidence**: 置信度，表示匹配结果的可信程度（0-1）
- **Rule_Template**: 规则模板，预定义的常见场景规则

## 需求

### 需求 1: 智能输入模式切换

**用户故事**: 作为用户，我希望能够选择使用自然语言或正则表达式来创建规则，这样我可以根据自己的技能水平选择合适的方式。

#### 验收标准

1. THE System SHALL 提供"自然语言模式"和"正则表达式模式"两种输入模式
2. THE System SHALL 默认使用自然语言模式
3. WHEN 用户切换输入模式 THEN THE System SHALL 保留已输入的内容
4. THE System SHALL 在界面上清晰标识当前使用的模式
5. THE System SHALL 为每种模式提供不同的输入提示和帮助文本

### 需求 2: 自然语言到正则表达式自动转换

**用户故事**: 作为不熟悉正则表达式的用户，我希望系统能够将我的自然语言描述自动转换为正则表达式，这样我不需要学习复杂的正则语法。

#### 验收标准

1. WHEN 用户在自然语言模式下输入描述 THEN THE System SHALL 调用 ERNIE API 生成对应的正则表达式
2. THE System SHALL 显示生成的正则表达式和匹配说明
3. THE System SHALL 提供至少 3 个匹配示例
4. WHEN 生成失败 THEN THE System SHALL 显示错误提示并建议使用关键词模式
5. THE System SHALL 允许用户编辑生成的正则表达式
6. THE System SHALL 在生成过程中显示加载状态
7. THE ERNIE_API SHALL 在 5 秒内返回转换结果

### 需求 3: 正则表达式实时验证

**用户故事**: 作为用户，我希望在输入正则表达式时能够实时看到验证结果，这样可以及时发现和修正错误。

#### 验收标准

1. WHEN 用户输入正则表达式 THEN THE System SHALL 实时验证语法正确性
2. WHEN 正则表达式语法错误 THEN THE System SHALL 显示具体的错误信息和位置
3. WHEN 正则表达式语法正确 THEN THE System SHALL 显示成功提示
4. THE System SHALL 检测与现有规则的潜在冲突
5. WHEN 检测到规则冲突 THEN THE System SHALL 显示冲突的规则列表
6. THE Validation SHALL 在用户停止输入 500 毫秒后执行

### 需求 4: 测试匹配功能

**用户故事**: 作为用户，我希望能够在保存规则前测试它是否能正确匹配我的查询，这样可以确保规则的准确性。

#### 验收标准

1. THE System SHALL 在规则创建对话框中提供测试输入框
2. WHEN 用户输入测试查询 THEN THE System SHALL 实时显示是否匹配当前规则
3. THE System SHALL 显示匹配的置信度分数
4. THE System SHALL 高亮显示匹配的部分
5. THE System SHALL 支持同时测试多个查询（每行一个）
6. THE System SHALL 显示每个测试查询的匹配结果
7. THE System SHALL 提供"保存为测试用例"功能

### 需求 5: 智能描述生成

**用户故事**: 作为用户，我希望系统能够根据我的匹配模式自动生成规则描述，这样我不需要手动编写描述文本。

#### 验收标准

1. WHEN 用户输入匹配模式 THEN THE System SHALL 自动生成建议描述
2. THE System SHALL 基于匹配模式和意图类型生成描述
3. THE System SHALL 允许用户编辑生成的描述
4. WHEN 用户选择意图类型 THEN THE System SHALL 更新建议描述
5. THE Generated_Description SHALL 包含规则的目的和适用场景

### 需求 6: 智能关键词提取

**用户故事**: 作为用户，我希望系统能够从我的匹配模式中自动提取关键词，这样我不需要手动输入关键词列表。

#### 验收标准

1. WHEN 用户输入匹配模式 THEN THE System SHALL 自动提取关键词
2. THE System SHALL 从自然语言描述中提取名词和动词
3. THE System SHALL 从正则表达式中提取字面量文本
4. THE System SHALL 显示提取的关键词列表
5. THE System SHALL 允许用户添加、删除或编辑关键词
6. THE System SHALL 为每个关键词显示权重建议

### 需求 7: 智能表推荐

**用户故事**: 作为用户，我希望系统能够根据我的查询意图推荐合适的数据库表，这样我不需要记住所有表名。

#### 验收标准

1. WHEN 用户选择 sql 意图类型 THEN THE System SHALL 显示表推荐功能
2. THE System SHALL 基于匹配模式中的关键词推荐相关表
3. THE System SHALL 显示每个表的名称、描述和字段数量
4. THE System SHALL 支持搜索和过滤表列表
5. THE System SHALL 允许用户选择多个推荐表
6. THE System SHALL 区分 CMDB 表和监控数据表
7. WHEN 匹配模式包含"物理机"关键词 THEN THE System SHALL 优先推荐 iaas_servers 表
8. WHEN 匹配模式包含"虚拟机"或"实例"关键词 THEN THE System SHALL 优先推荐 iaas_instances 表

### 需求 8: 快速示例模板

**用户故事**: 作为用户，我希望能够使用预定义的模板快速创建常见场景的规则，这样可以节省时间并确保规则的正确性。

#### 验收标准

1. THE System SHALL 提供至少 10 个常见场景的规则模板
2. THE System SHALL 包含以下模板类型：IP 查询、实例 ID 查询、统计查询、报告查询、知识查询
3. WHEN 用户选择模板 THEN THE System SHALL 自动填充所有字段
4. THE System SHALL 显示每个模板的描述和适用场景
5. THE System SHALL 允许用户在应用模板后修改字段
6. THE System SHALL 支持用户保存自定义模板
7. THE System SHALL 支持模板的导入和导出

### 需求 9: 上下文感知帮助

**用户故事**: 作为用户，我希望在填写每个字段时能够看到相关的帮助信息和示例，这样我可以更好地理解字段的作用。

#### 验收标准

1. THE System SHALL 为每个表单字段提供帮助图标
2. WHEN 用户点击帮助图标 THEN THE System SHALL 显示详细的字段说明
3. THE System SHALL 为每个字段提供至少 2 个示例
4. THE System SHALL 根据当前输入内容提供上下文相关的帮助
5. THE System SHALL 提供字段间的关联说明
6. THE System SHALL 在字段下方显示简短的内联提示

### 需求 10: 规则冲突检测

**用户故事**: 作为用户，我希望在创建规则时能够知道是否与现有规则冲突，这样可以避免创建重复或矛盾的规则。

#### 验收标准

1. WHEN 用户输入匹配模式 THEN THE System SHALL 检测与现有规则的冲突
2. THE System SHALL 检测完全相同的匹配模式
3. THE System SHALL 检测语义相似的匹配模式（相似度 > 0.8）
4. THE System SHALL 检测正则表达式的包含关系
5. WHEN 检测到冲突 THEN THE System SHALL 显示冲突规则的详细信息
6. THE System SHALL 显示冲突的严重程度（高、中、低）
7. THE System SHALL 允许用户选择覆盖、合并或取消

### 需求 11: 批量测试功能

**用户故事**: 作为用户，我希望能够使用一组测试查询批量测试规则，这样可以全面验证规则的准确性。

#### 验收标准

1. THE System SHALL 提供批量测试功能
2. THE System SHALL 支持从文本框输入多个测试查询（每行一个）
3. THE System SHALL 支持从文件导入测试查询
4. THE System SHALL 显示每个测试查询的匹配结果
5. THE System SHALL 统计匹配成功率
6. THE System SHALL 高亮显示未匹配的查询
7. THE System SHALL 支持导出测试结果

### 需求 12: 正则表达式可视化

**用户故事**: 作为用户，我希望能够看到正则表达式的可视化表示，这样可以更好地理解它的匹配逻辑。

#### 验收标准

1. WHEN 用户输入正则表达式 THEN THE System SHALL 显示可视化图表
2. THE System SHALL 使用铁路图（Railroad Diagram）表示正则表达式结构
3. THE System SHALL 高亮显示不同的正则元素（字符类、量词、分组等）
4. THE System SHALL 提供交互式的可视化图表
5. WHEN 用户点击可视化图表的某个部分 THEN THE System SHALL 高亮对应的正则表达式文本
6. THE System SHALL 显示正则表达式的复杂度评分

### 需求 13: 智能优先级建议

**用户故事**: 作为用户，我希望系统能够根据规则的特征自动建议合适的优先级，这样我不需要手动判断优先级。

#### 验收标准

1. WHEN 用户输入匹配模式和意图类型 THEN THE System SHALL 自动建议优先级
2. THE System SHALL 为强制规则（如 IP 地址、实例 ID）建议 90-100 优先级
3. THE System SHALL 为业务规则建议 50-89 优先级
4. THE System SHALL 为通用规则建议 1-49 优先级
5. THE System SHALL 显示优先级建议的理由
6. THE System SHALL 允许用户调整建议的优先级
7. THE System SHALL 检测优先级冲突并提供调整建议

### 需求 14: 规则预览功能

**用户故事**: 作为用户，我希望在保存规则前能够预览规则的完整信息，这样可以确认所有设置都正确。

#### 验收标准

1. THE System SHALL 在保存前显示规则预览对话框
2. THE Rule_Preview SHALL 包含所有字段的值
3. THE Rule_Preview SHALL 显示生成的正则表达式（如果使用自然语言模式）
4. THE Rule_Preview SHALL 显示推荐的表和关键词
5. THE Rule_Preview SHALL 显示测试结果摘要
6. THE Rule_Preview SHALL 显示潜在的冲突警告
7. THE System SHALL 允许用户从预览界面返回编辑

### 需求 15: 自然语言模式增强

**用户故事**: 作为用户，我希望自然语言模式能够理解更复杂的描述，这样我可以用更自然的方式表达规则。

#### 验收标准

1. THE System SHALL 支持复合条件的自然语言描述
2. THE System SHALL 理解"包含"、"以...开头"、"以...结尾"等模式
3. THE System SHALL 理解"或"、"且"等逻辑关系
4. THE System SHALL 理解数量词（"多个"、"至少"、"最多"）
5. THE System SHALL 提供自然语言描述的语法提示
6. WHEN 自然语言描述不明确 THEN THE System SHALL 提供澄清问题
7. THE System SHALL 支持中文和英文混合描述

### 需求 16: 规则效果预测

**用户故事**: 作为用户，我希望在创建规则前能够看到规则可能影响的查询数量，这样可以评估规则的影响范围。

#### 验收标准

1. THE System SHALL 基于历史查询数据预测规则的影响范围
2. THE System SHALL 显示过去 30 天内可能匹配该规则的查询数量
3. THE System SHALL 显示可能受影响的查询示例
4. THE System SHALL 显示规则对路由准确率的预期影响
5. THE System SHALL 显示规则的预期使用频率
6. WHEN 规则影响范围过大 THEN THE System SHALL 显示警告
7. THE System SHALL 提供"模拟运行"功能测试规则效果

### 需求 17: 交互式教程

**用户故事**: 作为新用户，我希望有一个交互式教程指导我创建第一个规则，这样我可以快速学会使用系统。

#### 验收标准

1. THE System SHALL 为首次使用的用户显示交互式教程
2. THE Tutorial SHALL 包含至少 5 个步骤
3. THE Tutorial SHALL 使用高亮和提示引导用户操作
4. THE Tutorial SHALL 允许用户跳过或稍后查看
5. THE Tutorial SHALL 在每个步骤提供详细说明
6. THE Tutorial SHALL 在完成后提供总结和最佳实践
7. THE System SHALL 提供"重新查看教程"的入口

### 需求 18: 错误恢复机制

**用户故事**: 作为用户，我希望在创建规则过程中如果发生错误，系统能够保存我的输入，这样我不需要重新填写。

#### 验收标准

1. THE System SHALL 自动保存用户的输入到本地存储
2. THE System SHALL 每 30 秒自动保存一次
3. WHEN 用户关闭对话框 THEN THE System SHALL 提示是否保存草稿
4. WHEN 用户重新打开创建对话框 THEN THE System SHALL 提示恢复未保存的草稿
5. THE System SHALL 支持多个草稿的管理
6. THE System SHALL 显示草稿的保存时间
7. THE System SHALL 允许用户删除草稿

### 需求 19: 性能优化

**用户故事**: 作为用户，我希望规则创建界面响应迅速，这样可以提高工作效率。

#### 验收标准

1. THE System SHALL 在 100 毫秒内响应用户输入
2. THE Validation SHALL 在 500 毫秒内完成
3. THE ERNIE_API_Call SHALL 在 5 秒内返回结果
4. THE System SHALL 使用防抖（debounce）优化频繁的验证请求
5. THE System SHALL 缓存常用的表列表和模板
6. THE System SHALL 在后台预加载必要的数据
7. THE System SHALL 显示加载进度指示器

### 需求 20: 可访问性支持

**用户故事**: 作为使用辅助技术的用户，我希望规则创建界面支持键盘导航和屏幕阅读器，这样我可以无障碍地使用系统。

#### 验收标准

1. THE System SHALL 支持完整的键盘导航
2. THE System SHALL 为所有交互元素提供 ARIA 标签
3. THE System SHALL 支持 Tab 键在字段间切换
4. THE System SHALL 支持 Enter 键提交表单
5. THE System SHALL 支持 Escape 键关闭对话框
6. THE System SHALL 为屏幕阅读器提供状态通知
7. THE System SHALL 确保颜色对比度符合 WCAG AA 标准

## 迭代和反馈规则

- 本需求文档需要用户明确批准后才能进入设计阶段
- 如果用户提出修改意见，必须更新文档并重新请求批准
- 如果用户在设计或任务阶段发现需求遗漏，可以返回本阶段补充需求
