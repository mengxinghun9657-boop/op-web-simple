# Specs 目录说明

本目录包含项目的所有功能规格文档（Spec）。每个 spec 包含需求文档、设计文档和任务列表。

## 📋 Spec 状态总览

### ✅ 已完成的 Spec

| Spec 名称 | 状态 | 完成时间 | 说明 |
|-----------|------|----------|------|
| `ai-intelligent-query` | ❎未完成 | 2025-12 | AI 智能查询功能（未部署embedding模型） |
| `cmdb-field-config-and-system-config` | ✅ 已完成 | 2025-12 | CMDB 字段配置和系统配置管理 |
| `frontend-ui-modernization` | ✅ 已完成 | 2025-12 | 前端界面现代化重构 |
| `icafe-integration` | ✅ 已完成 | 2025-12 | iCafe API 集成（运营分析） |
| `report-enhancement` | ✅ 已完成 | 2025-12 | 报告增强（AI 解读、趋势分析） |
| `task-history-and-operational-improvements` | ✅ 已完成 | 2025-12 | 任务历史和运营分析优化 |
| `ui-enhancements` | ✅ 已完成 | 2025-12 | UI 增强（主题切换、骨架屏等） |

### ⏳ 进行中的 Spec

| Spec 名称 | 状态 | 开始时间 | 说明 |
|-----------|------|----------|------|
| `fix-report-index-mock-data` | ⏳ 待实施 | 2026-02-02 | 修复报告索引模拟数据问题 |

### 📝 待开发的 Spec

| Spec 名称 | 状态 | 说明 |
|-----------|------|------|
| `ai-rag-upgrade` | 📝 仅需求 | AI RAG 升级（知识库增强） |
| `system-consistency-and-ux-improvements` | 📝 仅需求 | 系统一致性和 UX 改进 |

---

## 📂 Spec 目录结构

每个 spec 目录包含以下文件：

```
.kiro/specs/{spec-name}/
├── requirements.md  # 需求文档（用户故事、验收标准）
├── design.md        # 设计文档（架构、API、实现方案）
└── tasks.md         # 任务列表（可执行的编码任务）
```

---

## 🎯 当前优先级

### 高优先级（P0）
1. **fix-report-index-mock-data** - 修复报告索引返回模拟数据的问题

### 中优先级（P1）
2. **ai-rag-upgrade** - 增强知识库功能
3. **system-consistency-and-ux-improvements** - 系统一致性优化

---

## 📖 如何使用 Spec

### 1. 查看 Spec 状态
```bash
# 查看所有 spec
ls -la .kiro/specs/

# 查看特定 spec 的任务列表
cat .kiro/specs/fix-report-index-mock-data/tasks.md
```

### 2. 开始实施 Spec
```bash
# 1. 阅读需求文档
cat .kiro/specs/{spec-name}/requirements.md

# 2. 阅读设计文档
cat .kiro/specs/{spec-name}/design.md

# 3. 按照任务列表逐个实施
cat .kiro/specs/{spec-name}/tasks.md
```

### 3. 更新任务状态
在 `tasks.md` 中使用 Markdown 复选框语法：
- `- [ ]` - 未开始
- `- [x]` - 已完成
- `- [-]` - 进行中
- `- [~]` - 已排队

---

## 🔄 Spec 生命周期

```
创建 → 需求评审 → 设计评审 → 任务分解 → 实施 → 测试 → 完成 → 归档
```

### 归档规则
- 已完成的 spec 保留在目录中作为历史记录
- 不删除已完成的 spec，便于追溯和参考
- 定期更新本 README.md 中的状态表

---

## 📝 创建新 Spec

### 1. 创建目录结构
```bash
mkdir -p .kiro/specs/{spec-name}
cd .kiro/specs/{spec-name}
```

### 2. 创建必需文件
```bash
touch requirements.md design.md tasks.md
```

### 3. 填写文档内容
- **requirements.md**: 用户故事、验收标准、非功能需求
- **design.md**: 架构设计、API 设计、实现方案、测试策略
- **tasks.md**: 可执行的编码任务列表

### 4. 更新本 README.md
在"待开发的 Spec"表格中添加新 spec 的信息。

---

## 🎓 最佳实践

### 需求文档（requirements.md）
- ✅ 使用用户故事格式："作为...，我希望...，以便..."
- ✅ 每个需求包含明确的验收标准
- ✅ 区分功能需求和非功能需求
- ✅ 标注优先级（P0/P1/P2）

### 设计文档（design.md）
- ✅ 包含架构图和数据流图
- ✅ 详细的 API 设计（请求/响应格式）
- ✅ 数据库设计（表结构、索引）
- ✅ 错误处理和边界情况
- ✅ 性能优化方案

### 任务列表（tasks.md）
- ✅ 任务粒度适中（1-4 小时完成）
- ✅ 任务之间依赖关系清晰
- ✅ 每个任务引用对应的需求
- ✅ 包含测试任务（单元测试、集成测试）
- ✅ 设置检查点（Checkpoint）验证阶段性成果

---

## 📞 联系方式

如有关于 spec 的问题，请联系项目负责人或在项目会议中讨论。

---

**最后更新**: 2026-02-02
