# PFS 监控模块 - 实施任务清单

## 任务概览

本任务清单基于设计文档，采用**最大化复用现有功能**的原则，分 7 个阶段实施。

**核心复用策略**：
- 配置管理：复用 `SystemConfig` 模型
- 任务管理：继承 `PrometheusTaskService`
- 缓存机制：复用 `redis_client.py`
- 文件存储：复用 `minio_client.py`
- 前端组件：复用 `taskPoller.js`、`DataTable.vue`、`axios.js`
- API 响应：复用 `APIResponse` 统一格式

---

## Phase 0: 数据库初始化（前置任务）

### 0.1 MySQL 表结构设计

- [x] 0.1.1 检查现有表结构
  - 文件：`backend/config/mysql-init.sql`
  - 确认：`system_config` 表已存在且支持 `module='pfs'`
  - 确认：`tasks` 表已存在且支持扩展 `task_type`
  - 说明：PFS 模块**不需要新建表**，完全复用现有表结构

- [x] 0.1.2 验证字段完整性
  - 表：`system_config`
    - 必需字段：`id`, `module`, `config_key`, `config_value`, `description`, `created_at`, `updated_at`
    - 验证：`config_value` 字段类型为 `TEXT`，支持存储 JSON 配置
  - 表：`tasks`
    - 必需字段：`id`, `task_type`, `status`, `progress`, `message`, `result_data`, `created_at`, `updated_at`
    - 验证：`task_type` 支持字符串类型，可扩展新值
    - 验证：`result_data` 字段类型为 `TEXT` 或 `JSON`，支持存储导出结果

- [x] 0.1.3 在 PFS 客户端中定义默认配置
  - 文件：`backend/app/core/pfs_prometheus_client.py`
  - 功能：直接在代码中定义默认配置常量（从 `pfswatcher.py` 复制）
  - 配置项：
    ```python
    # 默认配置（从 pfswatcher.py 复制）
    DEFAULT_CONFIG = {
        "grafana_url": "https://cprom.cd.baidubce.com/select/prometheus",
        "token": "eyJhbGci...",  # 从脚本复制完整 Token
        "instance_id": "cprom-pmdfwwqqln0w7",
        "pfs_instance_id": "pfs-mTYGr6",
        "region": "cd",
        "instance_type": "plusl2",
        "step": "5m",
        "default_client": ".*"
    }
    ```
  - 加载逻辑：
    - 优先从数据库 `system_config` 表读取（`module='pfs'`）
    - 如果数据库没有配置，使用 `DEFAULT_CONFIG`
    - 用户可以在前端系统配置页面修改并保存到数据库

---

## Phase 1: 后端基础架构（Week 1）

### 1.1 数据模型定义

- [x] 1.1.1 创建 PFS 数据模型文件
  - 文件：`backend/app/models/pfs.py`
  - 内容：
    - `PFSConfig`：PFS 配置模型
    - `PFSMetric`：指标定义模型
    - `PFSMetricData`：指标数据点模型
    - `PFSMetricResult`：查询结果模型
    - `PFSQueryRequest`：查询请求模型
    - `PFSCompareRequest`：对比请求模型
  - 参考：设计文档 4.3 节

- [x] 1.1.2 扩展 Task 枚举类型
  - 文件：`backend/app/models/task.py`
  - 修改：在 `TaskType` 枚举中新增 `PFS_EXPORT = "pfs_export"`
  - 说明：复用现有 Task 模型，只需新增枚举值

### 1.2 Prometheus 客户端

- [x] 1.2.1 创建 PFS Prometheus 客户端
  - 文件：`backend/app/core/pfs_prometheus_client.py`
  - 功能：
    - 从 SystemConfig 加载配置（`module='pfs'`）
    - 封装 Prometheus API 调用（query_range、get_label_values）
    - 认证管理（Token + InstanceId）
    - 错误处理和重试机制
  - 参考：`app/core/prometheus_config.py` 的实现模式
  - 参考：设计文档 6.1 节

- [x] 1.2.2 实现指标配置管理
  - 位置：`pfs_prometheus_client.py` 中定义 `METRIC_CONFIG` 字典
  - 内容：从 `pfswatcher.py` 迁移 40+ 个指标配置
  - 优化：
    - 移除硬编码，改为从配置读取
    - 添加指标分类（容量、吞吐、QPS、延迟、元数据）
    - 添加告警阈值配置

### 1.3 PFS 业务服务

- [x] 1.3.1 创建 PFS 服务类
  - 文件：`backend/app/services/pfs_service.py`
  - 功能：
    - 指标目录查询（按分类分组）
    - 指标数据查询（带 Redis 缓存）
    - PromQL 构建（支持集群/客户端级别）
    - 数据解析和统计计算
    - 对比分析（今天 vs 昨天）
  - 参考：`app/services/prometheus_service.py` 的实现模式
  - 参考：设计文档 6.2 节

- [x] 1.3.2 实现 Redis 缓存机制
  - 功能：查询结果缓存 5 分钟
  - 缓存键格式：`pfs:query:{metrics}:{level}:{start}:{end}:{step}`
  - 复用：`app/core/redis_client.py` 的 `get_cache()` / `set_cache()`

- [x] 1.3.3 实现数据统计计算
  - 功能：计算 avg、min、max、p95
  - 功能：状态判断（正常/警告/严重）
  - 参考：`pfswatcher.py` 的 `calculate_stats()` 函数

### 1.4 PFS 任务服务

- [x] 1.4.1 创建 PFS 任务服务类
  - 文件：`backend/app/services/pfs_task_service.py`
  - 继承：`PrometheusTaskService`
  - 功能：
    - `create_pfs_export_task()`：创建导出任务
    - `complete_pfs_export_task()`：完成任务并上传 MinIO
    - 复用父类的三层存储架构（Redis + MySQL + MinIO）
  - 参考：设计文档 6.3 节

### 1.5 API 路由

- [x] 1.5.1 创建 PFS API 路由文件
  - 文件：`backend/app/api/v1/pfs.py`
  - 路由前缀：`/api/v1/pfs`
  - 接口列表：
    - `GET /metrics`：获取指标列表
    - `POST /query`：查询指标数据
    - `POST /compare`：对比查询
    - `POST /export`：导出数据（异步任务）
    - `GET /task/{task_id}`：查询任务状态
    - `GET /download/{filename}`：下载导出文件
  - 参考：设计文档 5.2 节

- [x] 1.5.2 实现指标列表接口
  - 接口：`GET /api/v1/pfs/metrics`
  - 功能：返回指标目录（按分类分组）
  - 支持：`level` 参数过滤（cluster/client）
  - 响应：使用 `APIResponse` 统一格式

- [x] 1.5.3 实现查询接口
  - 接口：`POST /api/v1/pfs/query`
  - 功能：查询指标数据（带 Redis 缓存）
  - 支持：时间范围选择（1h/4h/24h/custom）
  - 响应：返回数据点 + 统计值

- [x] 1.5.4 实现对比查询接口
  - 接口：`POST /api/v1/pfs/compare`
  - 功能：对比两个时间段的数据
  - 计算：变化百分比、趋势判断

- [x] 1.5.5 实现导出接口（异步任务）
  - 接口：`POST /api/v1/pfs/export`
  - 功能：
    - 创建异步任务（复用 `BackgroundTasks`）
    - 后台查询数据、生成 CSV
    - 上传到 MinIO
    - 更新任务状态（Redis + MySQL）
  - 参考：`app/api/v1/prometheus.py` 的异步任务模式
  - 参考：设计文档 6.4 节

- [x] 1.5.6 实现任务状态查询接口
  - 接口：`GET /api/v1/pfs/task/{task_id}`
  - 功能：查询任务进度和结果
  - 复用：`app/utils/task_manager.py` 的 `get_task_status()`

- [x] 1.5.7 实现文件下载接口
  - 接口：`GET /api/v1/pfs/download/{filename}`
  - 功能：从 MinIO 下载导出文件
  - 复用：`app/core/minio_client.py` 的下载方法

- [x] 1.5.8 新增客户端列表接口（支持脚本的客户端管理功能）
  - 接口：`GET /api/v1/pfs/clients`
  - 功能：
    - 查询活跃客户端列表
    - 返回 ClientId + ClientIp + 最新吞吐数据
    - 按吞吐降序排序
    - 支持搜索过滤（ClientId/IP）
  - 实现：
    - 查询最近 5 分钟的 `ClientFisReadThroughput` 或 `ClientFisWriteThroughput`
    - 提取 ClientId 和 ClientIp
    - 计算最新吞吐值
  - 参考：`pfswatcher.py` 的 `get_client_info_with_metrics()` 函数

- [x] 1.5.9 注册 PFS 路由
  - 文件：`backend/app/api/v1/__init__.py`
  - 修改：导入并注册 `pfs.router`
  - 文件：`backend/main.py`
  - 修改：`app.include_router(pfs.router, prefix=settings.API_V1_PREFIX, tags=["PFS监控"])`

---

## Phase 2: 配置管理集成（Week 1）

### 2.1 系统配置集成

- [x] 2.1.1 验证 SystemConfig 模型支持
  - 文件：`backend/app/models/system_config.py`
  - 确认：支持 `module='pfs'` 存储配置
  - 说明：无需修改，直接复用现有模型

- [x] 2.1.2 创建默认 PFS 配置
  - 文件：`backend/scripts/init_pfs_config.py`
  - 功能：初始化默认 PFS 配置到数据库
  - 配置项：
    - `grafana_config`：Grafana URL + Token（从 `pfswatcher.py` 迁移）
    - `instance_config`：Instance ID + PFS Instance ID
    - `query_defaults`：默认查询参数（step、region）
  - 加密：Token 使用加密存储

- [x] 2.1.3 配置 API 测试
  - 测试：通过 `GET /api/v1/config?module=pfs` 获取配置
  - 测试：通过 `POST /api/v1/config/save` 保存配置
  - 验证：配置正确加载到 PFS 客户端

### 2.2 前端配置页面集成

- [x] 2.2.1 在系统配置页面添加 PFS 配置卡片
  - 文件：`frontend/src/views/SystemConfig.vue`
  - 位置：在 CMDB、监控配置之后添加 PFS 配置卡片
  - 内容：
    - Grafana URL 输入框
    - Token 输入框（密码类型，脱敏显示）
    - Instance ID 输入框
    - PFS Instance ID 输入框
    - Region 选择器（cd/bj/gz）
    - Instance Type 输入框
    - 测试连接按钮
    - 保存按钮
  - 参考：现有 CMDB 配置卡片的实现

- [x] 2.2.2 实现配置加载和保存
  - 功能：从 `/api/v1/config?module=pfs` 加载配置
  - 功能：通过 `/api/v1/config/save` 保存配置
  - 验证：Token 格式验证、必填项检查

- [x] 2.2.3 实现测试连接功能
  - 功能：调用 PFS API 测试连接
  - 接口：`POST /api/v1/pfs/test-connection`（需新增）
  - 反馈：显示连接成功/失败消息

---

## Phase 3: 前端监控页面（Week 2）

### 3.1 页面结构

**重要**：前端必须包含脚本 `pfswatcher.py` 中已实现的所有功能，并进行 UI/UX 优化。

#### 脚本功能清单（必须全部实现）

| 脚本功能 | 前端实现方式 | 优化点 |
|---------|-------------|--------|
| **1. 查询指标数据** | 查询面板 + 数据展示 | 可视化图表替代文本表格 |
| **2. 指标级别选择** | 单选按钮（集群/客户端） | 更直观的切换方式 |
| **3. 客户端选择** | 下拉选择器 + 搜索 | 支持模糊搜索、按吞吐排序 |
| **4. 时间范围选择** | 时间选择器 | 快捷选项 + 自定义范围 |
| **5. 对比模式** | 开关 + 双时间选择器 | 可视化双轴对比图 |
| **6. 指标说明目录** | 指标选择器内嵌说明 | Tooltip 显示详细信息 |
| **7. 数据导出 CSV** | 导出按钮 + 进度追踪 | 异步任务 + 下载链接 |
| **8. 配置管理** | 系统配置页面 | 集中管理、加密存储 |
| **9. 客户端管理** | 客户端列表弹窗 | 表格展示、实时吞吐 |
| **10. 统计计算** | 自动计算并展示 | 卡片显示 avg/min/max/p95 |
| **11. 状态判断** | 颜色标识 | 绿色/黄色/红色状态标签 |
| **12. 按客户端分组** | 分组表格/图表 | 支持展开/折叠 |
| **13. 详细数据查看** | 数据表格 | 支持排序、筛选、分页 |
| **14. 帮助文档** | 帮助按钮 + 弹窗 | 内嵌使用说明 |

- [x] 3.1.1 创建 PFS 监控主页面
  - 文件：`frontend/src/views/monitoring/PFSMonitoring.vue`
  - 结构：
    - 配置区域（从系统配置加载）
    - 查询区域（指标选择、时间范围）
    - 数据展示区域（概览卡片、图表、表格）
    - 操作区域（刷新、导出）
  - 参考：`frontend/src/views/monitoring/BCCMonitoring.vue` 的布局模式
  - 参考：设计文档 7.1 节

- [x] 3.1.2 创建查询面板组件
  - 文件：`frontend/src/components/pfs/QueryPanel.vue`
  - 功能（对应脚本功能）：
    - **指标选择器**（多选，按分类分组）
      - 支持按分类展开/折叠
      - 每个指标显示中文名 + 说明（Tooltip）
      - 支持全选/取消全选
      - 支持搜索过滤
    - **级别选择**（集群/客户端）
      - 单选按钮组
      - 选择客户端级别时自动显示客户端选择器
    - **客户端选择器**（复刻脚本的客户端管理功能）
      - 下拉选择器 + 搜索框
      - 显示客户端列表（ClientId + ClientIp + 最新吞吐）
      - 支持按吞吐排序
      - 支持模糊搜索（ClientId/IP）
      - 支持"所有客户端"选项
    - **时间范围选择器**（复刻脚本的时间选择功能）
      - 快捷选项：最近1小时/4小时/24小时
      - 自定义时间：日期时间选择器
      - 历史查询：支持"N天前开始，查询M小时"
    - **对比模式开关**（复刻脚本的对比功能）
      - 开关按钮
      - 开启后显示两个时间范围选择器（今天 vs 昨天）
    - **查询按钮**
      - 显示 Loading 状态
      - 显示查询参数摘要
  - 参考：设计文档 7.1 节 + `pfswatcher.py` 的交互逻辑

- [x] 3.1.3 创建指标卡片组件
  - 文件：`frontend/src/components/pfs/MetricCard.vue`
  - 功能：
    - 显示指标名称、当前值、单位
    - 状态标识（正常/警告/严重）
    - 趋势图标（上升/下降/稳定）
  - 样式：卡片式布局，支持响应式

### 3.2 API 集成

- [x] 3.2.1 创建 PFS API 客户端
  - 文件：`frontend/src/api/pfs.js`
  - 功能（对应脚本的所有查询功能）：
    - `getMetrics(level)`：获取指标列表（按分类分组）
    - `getClientList()`：获取客户端列表（带最新吞吐数据）
    - `queryMetrics(request)`：查询指标数据
    - `compareMetrics(request)`：对比查询
    - `exportData(request)`：导出数据
    - `getTaskStatus(taskId)`：查询任务状态
    - `downloadFile(filename)`：下载文件
    - `testConnection(config)`：测试连接（配置验证）
  - 复用：`frontend/src/utils/axios.js` 的封装

- [x] 3.2.2 实现数据查询逻辑
  - 功能：调用 `/api/v1/pfs/query` 接口
  - 处理：Loading 状态、错误处理
  - 缓存：前端缓存查询结果（避免重复请求）
  - 优化：支持取消请求（切换查询参数时）

- [x] 3.2.3 实现客户端列表查询（复刻脚本的客户端管理）
  - 功能：调用 `/api/v1/pfs/clients` 接口（需新增）
  - 数据：ClientId + ClientIp + 最新吞吐 + 活跃状态
  - 排序：按吞吐降序排序
  - 缓存：缓存 5 分钟

- [x] 3.2.4 实现任务轮询逻辑
  - 功能：导出任务状态轮询
  - 复用：`frontend/src/utils/taskPoller.js`
  - 流程：
    1. 调用 `/api/v1/pfs/export` 创建任务
    2. 使用 `pollTaskStatus()` 轮询任务状态
    3. 任务完成后下载文件

### 3.3 路由配置

- [x] 3.3.1 添加 PFS 监控路由
  - 文件：`frontend/src/router/index.js`
  - 路由：`/monitoring/pfs`
  - 组件：`PFSMonitoring.vue`
  - 权限：需要登录

- [x] 3.3.2 在监控分析中心添加入口
  - 文件：`frontend/src/views/MonitoringAnalysis.vue`
  - 位置：在 BCC、BOS、EIP 之后添加 PFS 卡片
  - 内容：
    - 标题：PFS 监控分析
    - 描述：并行文件系统容量、吞吐、QPS、延迟监控
    - 图标：Folder
    - 路径：`/monitoring/pfs`
  - 参考：设计文档 7.4 节

---

## Phase 4: 数据大屏展示（Week 2）

### 4.1 数据大屏组件

- [x] 4.1.1 创建数据大屏组件
  - 文件：`frontend/src/components/pfs/DataDashboard.vue`
  - 布局：
    - 顶部：关键指标卡片（容量、吞吐、QPS）
    - 中部：趋势图表（折线图、面积图）
    - 底部：数据表格（详细数据）
  - 参考：设计文档 7.2 节

- [x] 4.1.2 实现概览卡片
  - 组件：复用 `MetricCard.vue`
  - 数据：从查询结果提取关键指标
  - 布局：Grid 布局，3-4 列

### 4.2 图表集成

- [x] 4.2.1 集成 ECharts
  - 依赖：确认 `echarts` 已安装
  - 封装：创建 `useECharts` composable

- [x] 4.2.2 实现容量趋势图
  - 类型：折线图
  - 数据：容量使用率、已用容量、总容量
  - 配置：时间轴、数据缩放、Tooltip

- [x] 4.2.3 实现吞吐趋势图
  - 类型：面积图
  - 数据：读吞吐、写吞吐
  - 配置：双 Y 轴、图例、数据缩放

- [x] 4.2.4 实现 QPS 监控图
  - 类型：多线图
  - 数据：读 QPS、写 QPS、元数据 QPS
  - 配置：图例、Tooltip、数据缩放

- [x] 4.2.5 实现延迟监控图
  - 类型：柱状图或热力图
  - 数据：读延迟、写延迟、元数据延迟
  - 配置：阈值线、颜色映射

### 4.3 数据表格

- [x] 4.3.1 实现数据表格展示（复刻脚本的详细数据展示）
  - 组件：复用 `frontend/src/components/common/DataTable.vue`
  - 数据：查询结果的详细数据点
  - 功能：
    - **排序**：支持按时间、数值、客户端排序
    - **筛选**：支持按指标、客户端筛选
    - **分页**：支持分页加载（每页 50 条）
    - **按客户端分组**（复刻脚本功能）：
      - 支持按客户端分组展示
      - 显示每个客户端的统计值（avg/max）
      - 支持展开/折叠分组
  - 列：
    - 时间（格式化显示）
    - 指标名称（中文 + 英文）
    - 数值（格式化 + 单位）
    - 客户端 ID（如果是客户端级别）
    - 客户端 IP（如果是客户端级别）
    - 状态标识（正常/警告/严重）

- [x] 4.3.2 实现表格导出功能
  - 功能：导出当前表格数据为 CSV
  - 实现：前端直接导出（小数据量 < 1000 条）
  - 格式：包含中文列名、完整指标信息（复刻脚本的 CSV 格式）

- [x] 4.3.3 实现统计信息展示（复刻脚本的统计计算）
  - 位置：表格上方
  - 内容：
    - 数据点总数
    - 平均值（avg）
    - 最小值（min）
    - 最大值（max）
    - P95 值
    - 状态判断（正常/警告/严重）
  - 样式：卡片式布局

- [x] 4.3.4 实现对比分析表格（复刻脚本的对比功能）
  - 显示条件：开启对比模式时显示
  - 列：
    - 指标名称
    - 今天平均值
    - 昨天平均值
    - 变化百分比
    - 变化趋势（上升/下降/稳定）
    - 状态（稳定/波动/剧变）
  - 排序：默认按变化百分比排序
  - 颜色：根据变化百分比显示不同颜色

---

## Phase 5: 对比分析功能（Week 3）

### 5.1 对比查询

- [x] 5.1.1 实现对比模式 UI
  - 位置：查询面板
  - 组件：对比模式开关
  - 功能：开启后显示两个时间范围选择器

- [x] 5.1.2 实现对比查询逻辑
  - 接口：`POST /api/v1/pfs/compare`
  - 数据：查询两个时间段的数据
  - 计算：变化百分比、趋势判断

### 5.2 对比图表

- [x] 5.2.1 实现双轴对比图
  - 类型：双 Y 轴折线图
  - 数据：今天 vs 昨天（或自定义时间段）
  - 配置：不同颜色区分、图例

- [x] 5.2.2 实现对比分析表格
  - 列：指标名称、今天平均、昨天平均、变化、状态
  - 状态：稳定/波动/剧变（根据变化百分比）
  - 排序：按变化百分比排序

---

## Phase 6: 导出功能（Week 3）

### 6.1 后台导出任务

- [x] 6.1.1 实现后台导出函数
  - 位置：`backend/app/api/v1/pfs.py`
  - 函数：`process_pfs_export_task()`
  - 流程：
    1. 创建独立数据库会话
    2. 查询 PFS 数据
    3. 生成 CSV 文件
    4. 上传到 MinIO
    5. 更新任务状态
  - 参考：`app/api/v1/prometheus.py` 的后台任务函数

- [x] 6.1.2 实现 CSV 生成
  - 格式：包含中文列名、完整指标信息
  - 列：时间、指标英文名、指标中文名、数值、单位、客户端信息
  - 编码：UTF-8 with BOM（支持 Excel 打开）

- [x] 6.1.3 实现 MinIO 上传
  - 复用：`app/core/minio_client.py` 的 `upload_file()`
  - 路径：`pfs_results/{task_id}.csv`
  - 权限：私有（需要认证下载）

### 6.2 前端导出界面

- [x] 6.2.1 实现导出按钮
  - 位置：操作区域
  - 功能：点击后创建导出任务

- [x] 6.2.2 实现导出进度显示
  - 组件：进度条 + 状态消息
  - 数据：从任务状态接口获取
  - 更新：使用 `taskPoller.js` 轮询

- [x] 6.2.3 实现下载功能
  - 功能：任务完成后显示下载按钮
  - 接口：`GET /api/v1/pfs/download/{filename}`
  - 处理：浏览器自动下载

---

## Phase 7: 测试与优化（Week 4）

### 7.1 单元测试

- [ ] 7.1.1 后端单元测试
  - 文件：`backend/tests/test_pfs_service.py`
  - 测试：
    - PFS 客户端连接测试
    - 指标查询测试
    - 数据解析测试
    - 统计计算测试

- [ ] 7.1.2 前端单元测试
  - 文件：`frontend/tests/unit/pfs.spec.js`
  - 测试：
    - 组件渲染测试
    - API 调用测试
    - 数据处理测试

### 7.2 集成测试

- [ ] 7.2.1 端到端测试
  - 场景：完整查询流程
  - 步骤：
    1. 加载配置
    2. 选择指标
    3. 查询数据
    4. 展示图表
    5. 导出数据
    6. 下载文件

- [ ] 7.2.2 性能测试
  - 测试：大数据量查询（24 小时数据）
  - 测试：并发查询（多用户同时查询）
  - 测试：缓存命中率
  - 优化：根据测试结果优化查询和缓存策略

### 7.3 功能逻辑文档更新

- [x] 7.3.1 更新功能逻辑文档
  - 文件：`mcp/.kiro/steering/功能逻辑.md`
  - 内容：
    - PFS 监控模块概述
    - 核心功能列表（14 项功能）
    - API 接口列表
    - 数据库表结构（复用 `system_config` 和 `tasks`）
    - 前端路由和页面

- [x] 7.3.2 更新 Swagger API 文档
  - 文件：FastAPI 自动生成的 Swagger 文档
  - 确认：所有 PFS API 接口都有完整的文档注释
  - 确认：请求/响应模型都有清晰的字段说明

### 7.4 代码审查与优化

- [x] 7.4.1 代码审查
  - 检查：代码规范、注释完整性
  - 检查：错误处理、日志记录
  - 检查：安全性（Token 加密、权限控制）

- [ ] 7.4.2 性能优化
  - 优化：Redis 缓存策略
  - 优化：查询性能（限制时间范围、分页加载）
  - 优化：前端渲染性能（虚拟滚动、懒加载）

- [ ] 7.4.3 用户体验优化
  - 优化：Loading 状态提示
  - 优化：错误提示信息
  - 优化：响应式布局（移动端适配）

---

## 任务依赖关系

```
Phase 0 (数据库初始化) ⭐ 前置任务
  ├─ 0.1 MySQL 表结构设计 → 0.2 配置初始化脚本 → 0.3 集成到部署脚本
  └─ 必须完成后才能进行 Phase 1

Phase 1 (后端基础)
  ├─ 1.1 数据模型 → 1.2 Prometheus 客户端 → 1.3 PFS 服务 → 1.4 任务服务 → 1.5 API 路由
  └─ 必须完成后才能进行 Phase 2

Phase 2 (配置管理)
  ├─ 2.1 系统配置集成 → 2.2 前端配置页面
  └─ 必须完成后才能进行 Phase 3

Phase 3 (前端页面)
  ├─ 3.1 页面结构 → 3.2 API 集成 → 3.3 路由配置
  └─ 必须完成后才能进行 Phase 4

Phase 4 (数据大屏)
  ├─ 4.1 数据大屏组件 → 4.2 图表集成 → 4.3 数据表格
  └─ 可与 Phase 5 并行

Phase 5 (对比分析)
  ├─ 5.1 对比查询 → 5.2 对比图表
  └─ 可与 Phase 4 并行

Phase 6 (导出功能)
  ├─ 6.1 后台导出任务 → 6.2 前端导出界面
  └─ 依赖 Phase 1 完成

Phase 7 (测试优化)
  ├─ 7.1 单元测试 → 7.2 集成测试 → 7.3 文档完善 → 7.4 代码审查
  └─ 依赖所有功能完成
```

---

## 脚本功能对照表（验收清单）

| 脚本功能 | 对应任务 | 验收标准 |
|---------|---------|---------|
| **配置管理** | Phase 0.1, Phase 2.1 | 可在系统配置页面配置 PFS 连接 |
| **指标查询** | Phase 1.3, Phase 3.2 | 支持集群/客户端级别查询 |
| **客户端管理** | Phase 1.5.8, Phase 3.2.3 | 显示客户端列表，支持搜索和排序 |
| **时间范围选择** | Phase 3.1.2 | 支持快捷选项、自定义、历史查询 |
| **对比模式** | Phase 5.1, Phase 5.2 | 支持今天 vs 昨天对比 |
| **指标说明** | Phase 3.1.2 | 指标选择器内嵌说明 Tooltip |
| **统计计算** | Phase 1.3.3, Phase 4.3.3 | 显示 avg/min/max/p95 |
| **状态判断** | Phase 1.3.3, Phase 4.3.1 | 颜色标识正常/警告/严重 |
| **按客户端分组** | Phase 4.3.1 | 支持分组展示和展开/折叠 |
| **详细数据** | Phase 4.3.1 | 表格支持排序、筛选、分页 |
| **CSV 导出** | Phase 6.1, Phase 6.2 | 异步导出，包含中文列名 |
| **帮助文档** | Phase 3.1.1 | 帮助按钮 + 使用说明弹窗 |

---

## 验收标准

### 功能验收
- [ ] **数据库初始化**：`system_config` 和 `tasks` 表支持 PFS 模块
- [ ] **配置管理**：可以在系统配置页面配置 PFS 连接信息
- [ ] **指标查询**：可以查询集群级别和客户端级别指标
- [ ] **客户端管理**：可以查看客户端列表，支持搜索和按吞吐排序
- [ ] **时间范围**：支持快捷选项、自定义时间、历史查询
- [ ] **数据展示**：可以通过图表和表格展示监控数据
- [ ] **统计计算**：自动计算并显示 avg/min/max/p95
- [ ] **状态判断**：根据阈值显示正常/警告/严重状态
- [ ] **按客户端分组**：支持按客户端分组展示数据
- [ ] **对比分析**：可以对比不同时间段的数据
- [ ] **数据导出**：可以导出数据为 CSV 文件（包含中文列名）
- [ ] **任务管理**：导出任务状态可追踪，支持下载
- [ ] **帮助文档**：提供使用说明和帮助信息

### 脚本功能对等验收
- [ ] **所有脚本功能**：前端实现了 `pfswatcher.py` 的所有 14 项功能
- [ ] **交互优化**：命令行交互改为 Web 界面，更直观易用
- [ ] **数据可视化**：文本表格改为图表展示，更清晰美观

### 性能验收
- [ ] 查询响应时间：< 3 秒（带缓存）
- [ ] 缓存命中率：> 80%
- [ ] 导出任务：支持 24 小时数据导出
- [ ] 并发支持：支持 10+ 用户同时查询

### 用户体验验收
- [ ] 界面友好：布局清晰，操作直观
- [ ] 错误提示：错误信息明确，有解决建议
- [ ] 响应式：支持桌面和移动端访问
- [ ] 加载状态：所有异步操作有 Loading 提示

---

## 注意事项

1. **复用优先**：优先使用现有组件和服务，避免重复造轮子
2. **功能对等**：前端必须实现脚本的所有功能，不能遗漏
3. **数据库初始化**：Phase 0 是前置任务，必须先完成
4. **字段完整性**：确保 `system_config` 和 `tasks` 表字段完整
5. **配置管理**：默认配置在代码中定义，用户可在前端修改并保存到数据库
6. **Token 安全**：Token 在数据库中加密存储，前端脱敏显示
7. **错误处理**：所有 API 调用必须有错误处理和日志记录
8. **性能优化**：使用 Redis 缓存，限制查询时间范围
9. **代码规范**：遵循项目代码规范，添加完整注释
10. **测试覆盖**：关键功能必须有单元测试和集成测试
11. **文档更新**：功能实现后更新 `功能逻辑.md` 和 Swagger 文档
12. **部署方式**：使用现有的 `deploy.sh` 和 `pack-offline.sh`，无需额外部署脚本

---

**任务总数**：78 个子任务（优化后）
**预计工期**：4 周
**优先级**：P1（高优先级）

**下一步**：开始实施 Phase 0.1 数据库初始化
