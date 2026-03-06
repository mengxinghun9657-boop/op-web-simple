# PFS 监控前端显示问题修复需求文档

## Introduction

PFS 监控模块的前端存在严重的数据展示问题。虽然后端正确返回了 33 个指标的完整数据(包含 data_points 和 statistics),但前端只显示了 4 个指标卡片,且所有统计数据(平均值、最大值、P95)都显示为 "-"。此外,设计文档中规划的监控大屏(DataDashboard)虽然已实现但未被使用,导致用户无法看到趋势图表和详细数据表格。

这些问题严重影响了 PFS 监控功能的可用性,用户无法获取完整的监控数据和分析结果。

## Bug Analysis

### Current Behavior (Defect)

#### 1. 指标卡片显示不完整

1.1 WHEN 用户选择"全部指标"(33个)并点击查询 THEN 前端只显示 4 个指标卡片(文件系统已用容量、文件系统总容量、容量使用率、集群读吞吐)

1.2 WHEN 后端返回 33 个指标的完整数据 THEN 前端的 `overviewMetrics` 计算属性只取前 4 个指标(`metricsData.value.slice(0, 4)`)

#### 2. 统计数据显示错误

1.3 WHEN 后端返回的指标数据包含完整的 statistics 对象(avg, min, max, p95) THEN MetricCard 组件中所有统计值都显示为 "-"

1.4 WHEN MetricCard 组件尝试访问 `metric.statistics?.avg` THEN 由于后端返回的字段名是 `statistics` 而非 `stats`,导致数据访问失败

#### 3. 监控大屏未使用

1.5 WHEN 用户查询数据后 THEN DataDashboard 组件虽然在代码中引入并注册,但实际渲染时被 `v-if="hasData"` 条件包裹,且与 MetricCard 共享同一个数据展示区域

1.6 WHEN DataDashboard 组件存在且功能完整 THEN 用户看不到趋势图表和详细数据表格,因为页面布局只显示了概览卡片

#### 4. 字段名不匹配

1.7 WHEN 后端返回的指标对象使用 `metric_name`, `zh_name`, `desc`, `unit_zh`, `statistics` 等字段 THEN 前端组件尝试访问 `metric.name`, `metric.stats` 等不存在的字段

1.8 WHEN MetricCard 组件的 formatValue 函数尝试访问 `props.metric.unit` THEN 后端返回的字段名可能是 `unit` 或其他名称,导致单位判断失败

### Expected Behavior (Correct)

#### 1. 显示所有查询的指标

2.1 WHEN 用户选择 N 个指标并点击查询 THEN 前端应该显示所有 N 个指标的卡片,而不是只显示前 4 个

2.2 WHEN 后端返回 33 个指标的数据 THEN 前端应该渲染 33 个 MetricCard 组件,每个组件显示对应指标的数据

#### 2. 正确显示统计数据

2.3 WHEN 后端返回的 statistics 对象包含 avg, min, max, p95 字段 THEN MetricCard 组件应该正确访问并显示这些统计值

2.4 WHEN 统计值为有效数字(如 659752024539136.0) THEN 应该根据单位格式化显示(如 "600.00 TB"),而不是显示 "-"

#### 3. 展示监控大屏

2.5 WHEN 用户查询数据后 THEN 应该同时显示概览卡片和监控大屏(趋势图表 + 数据表格)

2.6 WHEN DataDashboard 组件接收到 metricsData THEN 应该渲染 ECharts 趋势图和详细数据表格

#### 4. 字段名正确匹配

2.7 WHEN 前端组件访问后端返回的数据 THEN 应该使用正确的字段名(metric_name, zh_name, desc, unit_zh, statistics)

2.8 WHEN 需要格式化数值时 THEN 应该正确获取 unit 字段并根据单位类型进行格式化

### Unchanged Behavior (Regression Prevention)

#### 1. 查询功能保持正常

3.1 WHEN 用户选择指标、时间范围并点击查询 THEN 系统应该继续正常调用后端 API 并接收响应数据

3.2 WHEN 后端返回错误 THEN 系统应该继续正常显示错误提示信息

#### 2. 数据格式化逻辑保持正确

3.3 WHEN 指标单位为 bytes 或 binBps THEN 系统应该继续使用 formatBytes 函数格式化为 KB/MB/GB/TB

3.4 WHEN 指标单位为 percentunit THEN 系统应该继续格式化为百分比显示

3.5 WHEN 指标单位为 µs THEN 系统应该继续保留两位小数并添加单位

#### 3. 状态判断逻辑保持正确

3.6 WHEN 指标值超过 critical_threshold THEN 系统应该继续显示"严重"状态(红色)

3.7 WHEN 指标值超过 warn_threshold THEN 系统应该继续显示"警告"状态(黄色)

3.8 WHEN 指标值正常 THEN 系统应该继续显示"正常"状态(绿色)

#### 4. 导出功能保持正常

3.9 WHEN 用户点击导出按钮 THEN 系统应该继续正常创建导出任务并轮询状态

3.10 WHEN 导出完成 THEN 系统应该继续正常下载 CSV 文件

## Bug Condition Analysis

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type PFSQueryResponse
  OUTPUT: boolean
  
  // 当查询返回多个指标但前端只显示部分时,触发 Bug
  RETURN (
    X.data.length > 4 AND 
    frontend_displayed_cards.length == 4
  ) OR (
    X.data[i].statistics != null AND
    frontend_displayed_statistics == "-"
  ) OR (
    DataDashboard_component_exists AND
    DataDashboard_not_visible
  )
END FUNCTION
```

### Property Specification - Fix Checking

```pascal
// Property 1: 显示所有指标卡片
FOR ALL X WHERE X.data.length > 0 DO
  result ← renderMetricCards'(X)
  ASSERT result.cards_count = X.data.length
END FOR

// Property 2: 正确显示统计数据
FOR ALL X WHERE X.data[i].statistics != null DO
  result ← formatStatistics'(X.data[i].statistics)
  ASSERT result.avg != "-" AND result.max != "-" AND result.p95 != "-"
END FOR

// Property 3: 显示监控大屏
FOR ALL X WHERE X.data.length > 0 DO
  result ← renderDashboard'(X)
  ASSERT result.dashboard_visible = true AND result.charts_rendered = true
END FOR
```

### Preservation Goal

```pascal
// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT F(X) = F'(X)
END FOR

// 具体保持不变的行为:
// 1. 查询 API 调用逻辑
// 2. 数据格式化函数(formatBytes, formatValue)
// 3. 状态判断逻辑(status computation)
// 4. 导出功能流程
```

## Root Cause Analysis

### 根因 1: 硬编码的指标数量限制

**位置**: `mcp/frontend/src/views/monitoring/PFSMonitoring.vue:95`

```javascript
const overviewMetrics = computed(() => {
  // 提取关键指标用于概览卡片
  return metricsData.value.slice(0, 4)  // ❌ 硬编码只取前4个
})
```

**问题**: 无论后端返回多少个指标,前端都只显示前 4 个。

### 根因 2: 字段名访问错误

**位置**: `mcp/frontend/src/components/pfs/MetricCard.vue:52-60`

虽然代码中使用了 `metric.statistics?.avg`,但实际后端返回的数据结构可能存在嵌套或字段名不匹配的问题。需要验证后端实际返回的数据结构。

### 根因 3: DataDashboard 组件未正确集成

**位置**: `mcp/frontend/src/views/monitoring/PFSMonitoring.vue:30-36`

```vue
<div v-if="hasData" class="data-display">
  <!-- 概览卡片 -->
  <div class="overview-cards">
    <MetricCard
      v-for="metric in overviewMetrics"  <!-- 只循环4个指标 -->
      :key="metric.metric_name"
      :metric="metric"
    />
  </div>

  <!-- 数据大屏 -->
  <DataDashboard
    :metrics-data="metricsData"  <!-- 传入完整数据 -->
    :compare-mode="compareMode"
  />
</div>
```

**问题**: 虽然 DataDashboard 组件被渲染,但概览卡片只显示 4 个指标,用户可能误以为只查询到 4 个指标。

### 根因 4: 缺少数据结构验证

前端代码假设后端返回的数据结构,但没有进行验证和错误处理。当字段名不匹配时,直接返回 undefined,导致显示 "-"。

## Counterexamples

### 示例 1: 查询 33 个指标

**输入**:
```javascript
selectedMetrics = ['FsUsage', 'FsCapacity', 'FsUsageRate', ...] // 33个指标
```

**后端响应**:
```json
{
  "success": true,
  "data": [
    {
      "metric_name": "FsUsage",
      "zh_name": "文件系统已用容量",
      "desc": "PFS实例当前已使用的存储容量",
      "unit": "bytes",
      "unit_zh": "字节",
      "level": "cluster",
      "category": "容量",
      "data_points": [...],
      "statistics": {
        "avg": 659752024539136.0,
        "min": 659752024539136.0,
        "max": 659752024539136.0,
        "p95": 659752024539136.0
      }
    },
    // ... 其余 32 个指标
  ]
}
```

**当前行为(错误)**:
- 只显示 4 个 MetricCard
- 统计值显示 "-"
- DataDashboard 显示但数据不完整

**期望行为(正确)**:
- 显示 33 个 MetricCard
- 统计值显示 "600.00 TB"(格式化后)
- DataDashboard 显示完整的 33 个指标的趋势图和表格

## Fix Strategy

### 修复方案 1: 移除硬编码限制

将 `overviewMetrics` 改为返回所有指标,或者分离"概览卡片"和"所有指标卡片"的概念。

### 修复方案 2: 验证并修复字段名

1. 打印后端实际返回的数据结构
2. 确认字段名(metric_name vs name, statistics vs stats)
3. 统一前后端字段名约定

### 修复方案 3: 优化页面布局

1. 概览卡片显示关键指标(4-6个)
2. 监控大屏显示所有指标的趋势图
3. 数据表格显示所有指标的详细数据

### 修复方案 4: 添加数据验证

在组件中添加数据验证和错误处理,当字段不存在时输出警告日志。
