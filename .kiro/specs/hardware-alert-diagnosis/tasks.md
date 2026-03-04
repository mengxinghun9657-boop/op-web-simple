# 硬件告警智能诊断系统 - 任务列表

## 1. 数据库设计与迁移

- [x] 1.1 创建告警记录表和诊断结果表迁移脚本
  - 文件：`backend/alembic/versions/001_init_alert_tables.py`
  - 已完成基础表结构

- [x] 1.2 创建监控路径配置表迁移脚本
  - 文件：`backend/alembic/versions/002_add_monitor_paths_table.py`
  - 创建 `monitor_paths` 表
  - 字段：id, path, description, enabled, priority, file_pattern, created_at, updated_at
  - 添加唯一约束和索引

## 2. 后端模型与Schema

- [x] 2.1 创建告警相关数据库模型
  - 文件：`backend/app/models/alert.py`
  - 已完成 `AlertRecord`, `DiagnosisResult`, `WebhookConfig`, `MonitorPath` 模型

- [x] 2.2 创建监控路径Pydantic模型
  - 文件：`backend/app/schemas/monitor_path.py`
  - 定义 `MonitorPathCreate`, `MonitorPathUpdate`, `MonitorPathResponse`
  - 添加字段验证规则

- [x] 2.3 创建统一API响应模型
  - 文件：`backend/app/schemas/response.py`
  - 定义 `APIResponse`, `PaginatedData` 等基础响应格式

## 3. 后端API接口实现

### 3.1 告警管理API（已完成）

- [x] 3.1.1 实现获取告警列表接口
  - 接口：`GET /api/v1/alerts`
  - 支持分页和多条件筛选

- [x] 3.1.2 实现获取告警详情接口
  - 接口：`GET /api/v1/alerts/{alert_id}`
  - 返回告警和诊断结果

- [x] 3.1.3 实现手动触发诊断接口
  - 接口：`POST /api/v1/alerts/{alert_id}/diagnose`
  - 支持强制重新诊断

### 3.2 Webhook管理API（已完成）

- [x] 3.2.1 实现获取Webhook列表接口
  - 接口：`GET /api/v1/webhooks`

- [x] 3.2.2 实现创建Webhook接口
  - 接口：`POST /api/v1/webhooks`

- [x] 3.2.3 实现更新Webhook接口
  - 接口：`PUT /api/v1/webhooks/{webhook_id}`

- [x] 3.2.4 实现删除Webhook接口
  - 接口：`DELETE /api/v1/webhooks/{webhook_id}`

- [x] 3.2.5 实现测试Webhook接口
  - 接口：`POST /api/v1/webhooks/{webhook_id}/test`

### 3.3 监控路径配置API（已完成）

- [x] 3.3.1 实现获取监控路径列表接口
  - 接口：`GET /api/v1/monitor-paths`
  - 支持分页
  - 返回所有监控路径配置

- [x] 3.3.2 实现创建监控路径接口
  - 接口：`POST /api/v1/monitor-paths`
  - 验证路径格式
  - 检查路径唯一性
  - 创建后触发文件监控服务重新加载

- [x] 3.3.3 实现更新监控路径接口
  - 接口：`PUT /api/v1/monitor-paths/{path_id}`
  - 支持部分更新
  - 更新后触发文件监控服务重新加载

- [x] 3.3.4 实现删除监控路径接口
  - 接口：`DELETE /api/v1/monitor-paths/{path_id}`
  - 删除后触发文件监控服务重新加载

- [x] 3.3.5 实现测试监控路径接口
  - 接口：`POST /api/v1/monitor-paths/{path_id}/test`
  - 检查路径存在性
  - 检查读写权限
  - 返回文件数量和示例文件

- [x] 3.3.6 实现批量启用/禁用接口
  - 接口：`POST /api/v1/monitor-paths/batch-update`
  - 支持批量更新enabled状态
  - 更新后触发文件监控服务重新加载

### 3.4 统计分析API（已完成）

- [x] 3.4.1 实现告警趋势统计接口
  - 接口：`GET /api/v1/alerts/statistics/trend`
  - 支持按时间分组（day/hour/week/month）
  - 支持按集群、组件筛选
  - 返回趋势数据和汇总统计

- [x] 3.4.2 实现告警类型分布接口
  - 接口：`GET /api/v1/alerts/statistics/distribution`
  - 支持按不同维度统计（alert_type/component/severity/cluster）
  - 返回分布数据和百分比

- [x] 3.4.3 实现集群/节点告警排行接口
  - 接口：`GET /api/v1/alerts/statistics/top-nodes`
  - 支持按总数或严重程度排序
  - 返回Top N节点的告警统计

- [x] 3.4.4 实现筛选选项接口
  - 接口：`GET /api/v1/alerts/filter-options`
  - 返回所有可用的筛选选项（告警类型、组件、集群等）
  - 用于前端动态生成筛选器

## 4. 文件监控服务改造（已完成）

- [x] 4.1 改造文件监控服务支持动态配置
  - 文件：`backend/app/services/alert/file_watcher.py`
  - 从数据库加载监控路径配置
  - 支持多路径监控（每个路径独立Observer）
  - 实现优先级排序

- [x] 4.2 实现文件模式匹配功能
  - 支持通配符模式（如 `*.txt`, `alert_*.log`）
  - 使用 `fnmatch` 模块进行匹配

- [x] 4.3 实现热重载功能
  - 实现 `reload_paths()` 方法
  - 停止所有现有监控
  - 重新加载配置并启动监控

- [x] 4.4 实现路径管理方法
  - `add_watch_path()` - 添加监控路径
  - `remove_watch_path()` - 移除监控路径
  - 记录详细日志

## 5. 核心服务实现（部分完成）

- [x] 5.1 告警解析服务
  - 支持CCE集群和物理机两种格式
  - 自动识别集群类型
  - 智能提取IP地址

- [x] 5.2 手册匹配服务
  - 精确匹配和模糊匹配
  - 返回故障解决方案

- [x] 5.3 诊断API服务（仅CCE集群）
  - BCE认证集成
  - 任务创建和状态轮询
  - 73个诊断项解析

- [x] 5.4 AI解读服务
  - 厂内ERNIE API集成
  - Markdown格式报告生成

- [x] 5.5 Webhook通知服务
  - 飞书和如流支持
  - 分段发送优化
  - 差异化通知内容

## 6. 前端API封装（已完成）

- [x] 6.1 创建告警管理API文件
  - 文件：`frontend/src/api/alerts.js`
  - 封装告警相关API调用

- [x] 6.2 创建Webhook管理API文件
  - 文件：`frontend/src/api/webhooks.js`
  - 封装Webhook相关API调用

- [x] 6.3 创建监控路径API文件
  - 文件：`frontend/src/api/monitor-paths.js`
  - 封装监控路径相关API调用

- [x] 6.4 创建统计分析API文件
  - 文件：`frontend/src/api/statistics.js`
  - 封装统计分析相关API调用

## 7. 前端页面实现（已完成）

- [x] 7.1 创建告警列表页面
  - 文件：`frontend/src/views/alerts/AlertList.vue`
  - 实现表格展示、筛选、分页
  - 添加操作按钮（查看详情、重新诊断）

- [x] 7.2 创建告警详情页面
  - 文件：`frontend/src/views/alerts/AlertDetail.vue`
  - 显示告警基本信息
  - 显示诊断结果（手册、API、AI解读）
  - 操作历史时间线

- [x] 7.3 创建Webhook配置页面
  - 文件：`frontend/src/views/alerts/WebhookConfig.vue`
  - Webhook列表管理
  - 添加/编辑/删除/测试功能

- [x] 7.4 创建监控路径配置页面
  - 文件：`frontend/src/views/alerts/MonitorPathConfig.vue`
  - 路径列表表格
  - 添加/编辑/删除/测试功能
  - 批量操作和启用/禁用开关

- [x] 7.5 创建统计报表页面
  - 文件：`frontend/src/views/alerts/Statistics.vue`
  - 告警趋势图（折线图）
  - 告警类型分布（饼图）
  - 组件告警统计（柱状图）
  - 集群告警热力图

## 8. 前端路由配置（已完成）

- [x] 8.1 添加告警管理路由
  - 路由路径：`/alerts`, `/alerts/:id`

- [x] 8.2 添加Webhook配置路由
  - 路由路径：`/alerts/webhooks`

- [x] 8.3 添加监控路径配置路由
  - 路由路径：`/alerts/monitor-paths`

- [x] 8.4 添加统计报表路由
  - 路由路径：`/alerts/statistics`

## 9. 前端UI/UX优化（建议实施）

- [ ] 9.1 全局样式优化
  - 创建 `frontend/src/styles/ui-ux-pro.css`
  - 添加Modern Professional字体（Poppins + Open Sans）
  - 配置标准过渡动画
  - 添加prefers-reduced-motion支持

- [ ] 9.2 交互反馈优化
  - 为所有可点击元素添加cursor-pointer
  - 优化表格行悬停效果
  - 优化卡片悬停效果
  - 确保所有按钮有视觉反馈

- [ ] 9.3 图表配色优化
  - 统一ECharts配色方案
  - 使用专业的渐变色
  - 优化图表可读性

- [ ] 9.4 加载与空状态优化
  - 添加骨架屏组件
  - 优化空状态提示
  - 改进加载动画

- [ ] 9.5 可访问性优化
  - 添加ARIA标签
  - 支持键盘导航
  - 优化屏幕阅读器支持

- [ ] 9.6 响应式优化
  - 优化移动端布局
  - 测试不同屏幕尺寸
  - 优化触摸交互

## 10. 测试（待实现）

- [ ] 10.1 后端单元测试
  - 测试所有API接口
  - 测试核心服务逻辑
  - 测试文件监控服务

- [ ] 10.2 前端功能测试
  - 测试所有页面加载
  - 测试CRUD操作
  - 测试图表展示

- [ ] 10.3 集成测试
  - 测试端到端流程（文件监控→解析→诊断→通知）
  - 测试配置变更的热重载
  - 测试多路径监控

## 10. 文档更新（部分完成）

- [x] 10.1 更新设计文档
  - 文件：`mcp/.kiro/specs/hardware-alert-diagnosis/design.md`
  - 已添加监控路径配置功能设计
  - 已标记待实现的统计分析API

- [ ] 10.2 更新功能逻辑文档
  - 文件：`mcp/功能逻辑.md`
  - 添加硬件告警诊断系统完整说明
  - 记录实现细节和注意事项

- [ ] 10.3 更新README
  - 文件：`mcp/README.md`
  - 添加硬件告警诊断系统功能说明
  - 添加部署和使用指南

## 11. 部署（待实施）

- [ ] 11.1 执行数据库迁移
  - 在测试环境执行迁移
  - 验证表结构
  - 在生产环境执行迁移

- [ ] 11.2 配置初始数据
  - 添加默认监控路径 `/data/HAS_file/changan/`
  - 导入故障手册数据
  - 配置Webhook

- [ ] 11.3 重启服务
  - 重启后端服务
  - 验证文件监控服务正常运行
  - 验证前端页面可访问

---

## 任务优先级说明

- **P0（核心功能-已完成）**: 
  - 数据库设计 ✅
  - 后端模型和Schema ✅
  - 告警管理API ✅
  - Webhook管理API ✅
  - 监控路径配置API ✅
  - 统计分析API ✅
  - 文件监控服务 ✅
  - 核心服务（解析、匹配、诊断、AI、通知）✅

- **P1（重要功能-待实现）**: 
  - 前端页面实现 ⏳
  - 前端路由配置 ⏳

- **P2（次要功能-待实现）**: 
  - 测试 ⏳
  - 文档完善 ⏳
  - 部署 ⏳

## 当前进度

**已完成**：
- ✅ 后端核心功能（数据库、模型、API、服务）- 100%
- ✅ 监控路径配置功能 - 100%
- ✅ 告警管理基础API - 100%
- ✅ Webhook管理API - 100%
- ✅ 统计分析API - 100%
- ✅ 前端API封装 - 100%
- ✅ 前端页面实现 - 100%
- ✅ 前端路由配置 - 100%

**待开始**：
- ⏳ 完整测试 - 0%
- ⏳ 部署 - 0%

## 预计工时

- ✅ 后端核心开发：已完成（5-6天）
- ✅ 统计分析API：已完成（1天）
- ✅ 前端开发：已完成（1天）
- ⏳ 测试与部署：1-2天
- **剩余工时：1-2天**
