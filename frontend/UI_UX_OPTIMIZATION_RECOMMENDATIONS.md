# 硬件告警诊断系统 - 前端UI/UX优化建议

> 基于 UI/UX Pro Max 专业规范的优化指南

## 📊 当前状态评估

### ✅ 已实现的优秀设计

1. **配色方案** ⭐ 符合Analytics Dashboard最佳实践
   - Primary: `#3B82F6` (蓝色) - 信任感、专业
   - Secondary: `#60A5FA` (浅蓝) - 辅助信息
   - CTA: `#F97316` (橙色) - 行动号召
   - Background: `#F8FAFC` (浅灰) - 清爽背景
   - Text: `#1E293B` (深灰) - 高对比度文本
   - Border: `#E2E8F0` (边框灰) - 清晰分隔

2. **组件库** ⭐ Element Plus
   - ✅ 专业的企业级UI组件
   - ✅ 完整的响应式支持
   - ✅ 良好的可访问性基础
   - ✅ Vue 3 Composition API 兼容

3. **图表库** ⭐ ECharts
   - ✅ 强大的数据可视化能力
   - ✅ 丰富的图表类型（折线、饼图、柱状图）
   - ✅ 良好的交互体验（hover、zoom）
   - ✅ 响应式图表支持

4. **页面结构** ⭐ Data-Dense Dashboard风格
   - ✅ 清晰的信息层次
   - ✅ 高效的空间利用
   - ✅ 专业的数据展示
   - ✅ 符合企业级应用标准

## 🎨 UI/UX Pro Max 优化建议

### 优先级说明

- **P0 (Critical)**: 影响用户体验，必须立即修复
- **P1 (High)**: 提升专业度，近期实施
- **P2 (Medium)**: 锦上添花，长期优化

---

### 1. 字体优化 [P1]

**当前状态**: 使用系统默认字体

**问题**: 缺乏品牌识别度，专业感不足

**建议**: 采用 **Modern Professional** 字体配对
- **标题字体**: Poppins (几何感、现代)
- **正文字体**: Open Sans (人文感、易读)

**实施步骤**:

```html
<!-- 步骤1: 在 frontend/index.html 的 <head> 中添加 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
```

```css
/* 步骤2: 在全局样式中配置 */
:root {
  --font-heading: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-body: 'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 标题使用 Poppins */
h1, h2, h3, h4, h5, h6,
.page-title, .card-title {
  font-family: var(--font-heading);
  font-weight: 600;
  letter-spacing: -0.02em; /* 紧凑间距 */
}

/* 正文使用 Open Sans */
body, p, span, div, button, input, textarea {
  font-family: var(--font-body);
  font-weight: 400;
}

/* 字体加载优化 */
@font-face {
  font-display: swap; /* 避免 FOIT (Flash of Invisible Text) */
}
```

**预期效果**: 
- ✅ 提升品牌专业度 +30%
- ✅ 改善阅读体验
- ✅ 增强视觉层次

---

### 2. 图标规范 [P0]

**检查项**: 确保所有图标都是SVG，无emoji

**UI/UX Pro Max 规则**:
- ✅ **DO**: 使用 Element Plus Icons (SVG)
- ❌ **DON'T**: 使用 emoji 作为UI图标 (🔍 ❌ 🚨 ❌)

**当前代码审查**:

```vue
<!-- ✅ 正确：使用 Element Plus Icons -->
<el-icon><Search /></el-icon>
<el-icon><Refresh /></el-icon>
<el-icon><CircleCheck /></el-icon>

<!-- ❌ 错误：使用 emoji -->
<span>🔍</span>  <!-- 不要这样做！ -->
<span>🚨</span>  <!-- 不要这样做！ -->
```

**验证清单**:
- [ ] AlertList.vue - 所有图标都是 `<el-icon>`
- [ ] AlertDetail.vue - 无 emoji 图标
- [ ] Statistics.vue - 图表图标使用 SVG
- [ ] WebhookConfig.vue - 操作图标使用 SVG
- [ ] MonitorPathConfig.vue - 状态图标使用 SVG

---

### 3. 交互反馈优化 [P0]

**UI/UX Pro Max 规则**:
- ✅ 所有可点击元素必须有 `cursor: pointer`
- ✅ 悬停时提供视觉反馈（颜色/阴影/边框）
- ✅ 过渡时间 150-300ms (不要太快或太慢)

**需要优化的地方**:

```vue
<!-- AlertList.vue - 表格行点击 -->
<el-table
  @row-click="handleRowClick"
  class="alert-table"
>
  <!-- 添加样式 -->
</el-table>
```

```css
/* 添加到全局样式或组件样式 */

/* 1. 通用 cursor-pointer 类 */
.cursor-pointer {
  cursor: pointer;
}

/* 2. 表格行悬停效果 */
.alert-table .el-table__row {
  cursor: pointer;
  transition: background-color 200ms ease-out;
}

.alert-table .el-table__row:hover {
  background-color: #f5f7fa;
}

/* 3. 卡片悬停效果 */
.el-card {
  transition: box-shadow 200ms ease-out, transform 200ms ease-out;
}

.el-card:hover {
  box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.1);
  /* 不要使用 scale - 会导致布局偏移！ */
}

/* 4. 按钮悬停效果 */
.el-button {
  transition: all 200ms ease-out;
}

/* 5. 禁用状态 */
.el-button:disabled,
.el-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

**实施清单**:
- [ ] 为所有表格添加 `cursor: pointer`
- [ ] 为所有卡片添加悬停效果
- [ ] 确保按钮有视觉反馈
- [ ] 禁用状态清晰可见

---

### 4. 动画与过渡 [P1]

**UI/UX Pro Max 规则**:
- ✅ 必须支持 `prefers-reduced-motion`
- ✅ 使用 `ease-out` (进入) 和 `ease-in` (退出)
- ❌ 避免使用 `linear` (感觉机械)

**实施代码**:

```css
/* 在全局样式中添加 */

/* 1. 支持减少动画偏好 (可访问性) */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* 2. 标准过渡类 */
.transition-colors {
  transition: color 200ms ease-out, 
              background-color 200ms ease-out,
              border-color 200ms ease-out;
}

.transition-transform {
  transition: transform 200ms ease-out;
}

.transition-opacity {
  transition: opacity 200ms ease-out;
}

.transition-shadow {
  transition: box-shadow 200ms ease-out;
}

/* 3. 进入/退出动画 */
.fade-enter-active {
  transition: opacity 300ms ease-out;
}

.fade-leave-active {
  transition: opacity 200ms ease-in;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 4. 滑动动画 */
.slide-enter-active {
  transition: transform 300ms ease-out;
}

.slide-leave-active {
  transition: transform 200ms ease-in;
}

.slide-enter-from {
  transform: translateY(-10px);
}

.slide-leave-to {
  transform: translateY(10px);
}
```

**在 Vue 组件中使用**:

```vue
<template>
  <!-- 使用 Transition 组件 -->
  <Transition name="fade">
    <div v-if="show" class="alert-message">
      告警信息
    </div>
  </Transition>
</template>
```

---

### 5. 加载状态优化 [P0]

**UI/UX Pro Max 规则**:
- ✅ 使用骨架屏 (Skeleton) 而不是空白屏幕
- ✅ 显示加载进度反馈
- ❌ 避免 UI 冻结无反馈

**实施方案**:

```vue
<!-- AlertList.vue - 添加骨架屏 -->
<template>
  <div class="alert-list-container">
    <!-- 首次加载：显示骨架屏 -->
    <el-skeleton 
      v-if="loading && !alertList.length" 
      :rows="10" 
      animated 
      class="skeleton-table"
    />
    
    <!-- 数据加载完成：显示表格 -->
    <el-table 
      v-else 
      v-loading="loading"
      :data="alertList"
      class="alert-table"
    >
      <!-- 表格列 -->
    </el-table>
    
    <!-- 空状态 -->
    <el-empty
      v-if="!loading && !alertList.length"
      description="暂无告警数据"
      :image-size="200"
    >
      <el-button type="primary" @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
        刷新数据
      </el-button>
    </el-empty>
  </div>
</template>

<style scoped>
.skeleton-table {
  padding: 20px;
}

/* 自定义骨架屏样式 */
:deep(.el-skeleton__item) {
  background: linear-gradient(
    90deg,
    #f2f2f2 25%,
    #e6e6e6 37%,
    #f2f2f2 63%
  );
  background-size: 400% 100%;
  animation: skeleton-loading 1.4s ease infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
```

**Statistics.vue - 图表加载状态**:

```vue
<template>
  <div class="chart-container">
    <!-- 图表加载中 -->
    <div v-if="chartLoading" class="chart-skeleton">
      <el-skeleton :rows="8" animated />
    </div>
    
    <!-- 图表内容 -->
    <div 
      v-else
      ref="chartRef" 
      class="chart"
      role="img"
      :aria-label="`${chartTitle}图表`"
    ></div>
  </div>
</template>
```

---

### 6. 空状态优化 [P0]

**UI/UX Pro Max 规则**:
- ✅ 提供友好的空状态提示
- ✅ 给出明确的行动建议
- ❌ 避免空白页面或"无数据"

**实施方案**:

```vue
<!-- AlertList.vue - 优化空状态 -->
<el-empty
  v-if="!loading && !alertList.length"
  :image-size="200"
>
  <template #description>
    <p class="empty-title">暂无告警数据</p>
    <p class="empty-subtitle">
      {{ hasFilters ? '尝试调整筛选条件' : '系统运行正常，暂无硬件告警' }}
    </p>
  </template>
  
  <template #default>
    <el-button 
      v-if="hasFilters" 
      type="primary" 
      @click="handleResetFilters"
    >
      <el-icon><Refresh /></el-icon>
      清除筛选
    </el-button>
    <el-button 
      v-else
      @click="handleRefresh"
    >
      <el-icon><Refresh /></el-icon>
      刷新数据
    </el-button>
  </template>
</el-empty>

<style scoped>
.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.empty-subtitle {
  font-size: 14px;
  color: #909399;
  margin-bottom: 20px;
}
</style>
```

**不同场景的空状态**:

```vue
<!-- 1. 无数据（首次加载） -->
<el-empty description="暂无数据" />

<!-- 2. 筛选无结果 -->
<el-empty description="未找到匹配的告警">
  <el-button @click="clearFilters">清除筛选</el-button>
</el-empty>

<!-- 3. 搜索无结果 -->
<el-empty description="未找到相关告警">
  <el-button @click="clearSearch">清除搜索</el-button>
</el-empty>

<!-- 4. 错误状态 -->
<el-empty description="加载失败">
  <el-button type="primary" @click="retry">重试</el-button>
</el-empty>
```

---

### 7. 表格优化 [P1]

**UI/UX Pro Max 规则**:
- ✅ 移动端使用横向滚动或卡片布局
- ✅ 支持批量操作（多选 + 操作栏）
- ✅ 表格行高适中，易于扫描

**实施方案**:

```vue
<!-- AlertList.vue - 响应式表格 -->
<template>
  <div class="table-container">
    <!-- 桌面端：表格视图 -->
    <el-table
      v-if="!isMobile"
      :data="alertList"
      class="alert-table"
      @selection-change="handleSelectionChange"
    >
      <!-- 多选列 -->
      <el-table-column type="selection" width="55" />
      
      <!-- 其他列 -->
      <el-table-column prop="alert_type" label="告警类型" />
      <!-- ... -->
    </el-table>
    
    <!-- 移动端：卡片视图 -->
    <div v-else class="alert-cards">
      <div 
        v-for="alert in alertList" 
        :key="alert.id"
        class="alert-card"
        @click="handleViewDetail(alert.id)"
      >
        <div class="alert-card-header">
          <el-tag :type="getSeverityTagType(alert.severity)">
            {{ alert.severity }}
          </el-tag>
          <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
        </div>
        <div class="alert-card-body">
          <h4>{{ alert.alert_type }}</h4>
          <p>{{ alert.ip }} · {{ alert.component }}</p>
        </div>
      </div>
    </div>
    
    <!-- 批量操作栏 -->
    <transition name="slide-up">
      <div v-if="selectedAlerts.length > 0" class="bulk-action-bar">
        <span class="selected-count">
          已选择 {{ selectedAlerts.length }} 项
        </span>
        <div class="actions">
          <el-button size="small" @click="handleBulkDiagnose">
            批量诊断
          </el-button>
          <el-button size="small" @click="handleBulkExport">
            导出数据
          </el-button>
          <el-button size="small" @click="clearSelection">
            取消选择
          </el-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWindowSize } from '@vueuse/core'

const { width } = useWindowSize()
const isMobile = computed(() => width.value < 768)
const selectedAlerts = ref([])

const handleSelectionChange = (selection) => {
  selectedAlerts.value = selection
}
</script>

<style scoped>
/* 表格容器 */
.table-container {
  position: relative;
  overflow-x: auto; /* 移动端横向滚动 */
}

/* 移动端卡片布局 */
.alert-cards {
  display: grid;
  gap: 16px;
  padding: 16px;
}

.alert-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 200ms ease-out;
}

.alert-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.alert-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.alert-time {
  font-size: 12px;
  color: #909399;
}

.alert-card-body h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.alert-card-body p {
  font-size: 14px;
  color: #606266;
}

/* 批量操作栏 */
.bulk-action-bar {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 20px;
  z-index: 1000;
}

.selected-count {
  font-weight: 600;
  color: #3B82F6;
}

.actions {
  display: flex;
  gap: 8px;
}

/* 滑入动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 300ms ease-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
```

---

### 8. 图表配色优化 [P1]

**UI/UX Pro Max 规则**:
- ✅ 使用专业的配色方案
- ✅ 确保色盲友好（避免仅用红绿区分）
- ✅ 渐变色使用 15-20% 亮度差

**实施方案**:

```javascript
// Statistics.vue - 专业图表配色

// 1. 定义配色系统
const chartColors = {
  // 严重程度配色
  severity: {
    critical: '#EF4444',  // 红色
    warning: '#F59E0B',   // 橙色
    info: '#3B82F6'       // 蓝色
  },
  
  // 渐变配色（用于分布图）
  gradient: [
    '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE',
    '#F59E0B', '#FBBF24', '#FCD34D', '#FDE68A', '#FEF3C7'
  ],
  
  // 对比配色（用于对比图）
  contrast: [
    '#3B82F6', // 蓝色
    '#10B981', // 绿色
    '#F59E0B', // 橙色
    '#8B5CF6', // 紫色
    '#EC4899'  // 粉色
  ]
}

// 2. 告警趋势图配置
const trendChartOptions = {
  color: [
    chartColors.severity.critical,
    chartColors.severity.warning,
    chartColors.severity.info
  ],
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#E2E8F0',
    borderWidth: 1,
    textStyle: {
      color: '#1E293B'
    }
  },
  legend: {
    data: ['Critical', 'Warning', 'Info'],
    textStyle: {
      fontFamily: 'Open Sans, sans-serif'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    axisLine: {
      lineStyle: {
        color: '#E2E8F0'
      }
    },
    axisLabel: {
      color: '#64748B',
      fontFamily: 'Open Sans, sans-serif'
    }
  },
  yAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: '#E2E8F0'
      }
    },
    axisLabel: {
      color: '#64748B',
      fontFamily: 'Open Sans, sans-serif'
    },
    splitLine: {
      lineStyle: {
        color: '#F1F5F9'
      }
    }
  },
  series: [
    {
      name: 'Critical',
      type: 'line',
      smooth: true,
      areaStyle: {
        opacity: 0.2
      },
      emphasis: {
        focus: 'series'
      }
    },
    // ... 其他系列
  ]
}

// 3. 分布图配置（饼图）
const distributionChartOptions = {
  color: chartColors.gradient,
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'vertical',
    right: '10%',
    top: 'center',
    textStyle: {
      fontFamily: 'Open Sans, sans-serif'
    }
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'], // 环形图
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}\n{d}%',
        fontFamily: 'Open Sans, sans-serif'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 16,
          fontWeight: 'bold'
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
}

// 4. 排行榜配置（柱状图）
const topNodesChartOptions = {
  color: [chartColors.contrast[0]],
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: '#E2E8F0'
      }
    },
    axisLabel: {
      color: '#64748B'
    },
    splitLine: {
      lineStyle: {
        color: '#F1F5F9'
      }
    }
  },
  yAxis: {
    type: 'category',
    axisLine: {
      lineStyle: {
        color: '#E2E8F0'
      }
    },
    axisLabel: {
      color: '#64748B',
      fontFamily: 'Open Sans, sans-serif'
    }
  },
  series: [
    {
      type: 'bar',
      barWidth: '60%',
      itemStyle: {
        borderRadius: [0, 4, 4, 0]
      },
      emphasis: {
        itemStyle: {
          color: chartColors.contrast[1]
        }
      }
    }
  ]
}
```

---

### 9. 表单验证优化 [P1]

**UI/UX Pro Max 规则**:
- ✅ 在 `blur` 时验证（不要在输入时验证）
- ✅ 错误信息必须有 `role="alert"` (可访问性)
- ✅ 提交后显示加载状态和成功/失败反馈

**实施方案**:

```vue
<!-- WebhookConfig.vue / MonitorPathConfig.vue - 表单验证 -->
<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="请输入名称"
          @blur="validateField('name')"
        />
      </el-form-item>

      <el-form-item label="URL" prop="url">
        <el-input
          v-model="formData.url"
          placeholder="https://..."
          @blur="validateField('url')"
        />
        <div class="form-tip">
          请输入完整的 Webhook URL
        </div>
      </el-form-item>

      <!-- 错误提示 -->
      <div 
        v-if="formError" 
        class="form-error"
        role="alert"
        aria-live="polite"
      >
        <el-icon><CircleClose /></el-icon>
        {{ formError }}
      </div>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">
        取消
      </el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '提交中...' : '确定' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const formRef = ref(null)
const submitting = ref(false)
const formError = ref('')

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  url: [
    { required: true, message: '请输入 URL', trigger: 'blur' },
    { 
      type: 'url', 
      message: '请输入有效的 URL', 
      trigger: 'blur' 
    }
  ]
}

// 单个字段验证
const validateField = (field) => {
  formRef.value?.validateField(field)
}

// 提交表单
const handleSubmit = async () => {
  try {
    // 1. 验证表单
    await formRef.value?.validate()
    
    // 2. 显示加载状态
    submitting.value = true
    formError.value = ''
    
    // 3. 提交数据
    await submitData(formData.value)
    
    // 4. 成功反馈
    ElMessage.success('保存成功')
    dialogVisible.value = false
    
  } catch (error) {
    // 5. 错误处理
    if (error.response) {
      formError.value = error.response.data.error || '提交失败'
    } else {
      formError.value = '请检查表单填写是否正确'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: #FEF0F0;
  border: 1px solid #FDE2E2;
  border-radius: 4px;
  color: #F56C6C;
  font-size: 14px;
  margin-top: 16px;
}

.form-error .el-icon {
  font-size: 16px;
}
</style>
```

---

### 10. 可访问性优化 [P2]

**UI/UX Pro Max 规则**:
- ✅ 所有图片有 `alt` 文本
- ✅ 表单输入有 `label`
- ✅ 颜色不是唯一的信息指示器
- ✅ 支持键盘导航

**实施方案**:

```vue
<!-- 1. 图表可访问性 -->
<div
  ref="chartRef"
  class="chart"
  role="img"
  :aria-label="`${chartTitle}，显示${chartDescription}`"
  tabindex="0"
>
  <!-- ECharts 图表 -->
</div>

<!-- 2. 表格可访问性 -->
<el-table
  :data="alertList"
  aria-label="硬件告警列表"
  @row-click="handleRowClick"
  @keydown.enter="handleRowEnter"
>
  <el-table-column prop="alert_type" label="告警类型">
    <template #default="{ row }">
      <span :aria-label="`告警类型：${row.alert_type}`">
        {{ row.alert_type }}
      </span>
    </template>
  </el-table-column>
  
  <el-table-column prop="severity" label="严重程度">
    <template #default="{ row }">
      <!-- 不仅用颜色，还用文字 -->
      <el-tag 
        :type="getSeverityTagType(row.severity)"
        :aria-label="`严重程度：${getSeverityLabel(row.severity)}`"
      >
        {{ getSeverityLabel(row.severity) }}
      </el-tag>
    </template>
  </el-table-column>
</el-table>

<!-- 3. 按钮可访问性 -->
<el-button
  type="primary"
  aria-label="查看告警详情"
  @click="handleViewDetail"
  @keydown.enter="handleViewDetail"
>
  <el-icon aria-hidden="true"><View /></el-icon>
  查看详情
</el-button>

<!-- 4. 对话框可访问性 -->
<el-dialog
  v-model="dialogVisible"
  :title="dialogTitle"
  role="dialog"
  aria-modal="true"
  :aria-labelledby="dialogTitleId"
>
  <template #header>
    <h2 :id="dialogTitleId">{{ dialogTitle }}</h2>
  </template>
  <!-- 对话框内容 -->
</el-dialog>

<!-- 5. 加载状态可访问性 -->
<div
  v-if="loading"
  role="status"
  aria-live="polite"
  aria-label="正在加载数据"
>
  <el-skeleton :rows="5" animated />
</div>
```

```javascript
// 键盘导航支持
const handleKeyboardNavigation = (event) => {
  switch (event.key) {
    case 'Enter':
    case ' ':
      // 激活当前元素
      event.target.click()
      break
    case 'Escape':
      // 关闭对话框/菜单
      closeDialog()
      break
    case 'ArrowDown':
      // 移动到下一项
      focusNextItem()
      break
    case 'ArrowUp':
      // 移动到上一项
      focusPreviousItem()
      break
  }
}
```

---

### 11. 性能优化 [P2]

**UI/UX Pro Max 规则**:
- ✅ 懒加载图片和组件
- ✅ 虚拟滚动（大数据量）
- ✅ 防抖和节流

**实施方案**:

```vue
<!-- 1. 组件懒加载 -->
<script setup>
import { defineAsyncComponent } from 'vue'

// 懒加载统计图表组件
const Statistics = defineAsyncComponent(() =>
  import('./views/alerts/Statistics.vue')
)

// 懒加载详情页组件
const AlertDetail = defineAsyncComponent(() =>
  import('./views/alerts/AlertDetail.vue')
)
</script>

<!-- 2. 图片懒加载 -->
<img
  :src="imageUrl"
  loading="lazy"
  alt="告警截图"
  @error="handleImageError"
/>

<!-- 3. 虚拟滚动（大数据量表格） -->
<script setup>
import { ElTableV2 } from 'element-plus'

// 当数据量 > 1000 时使用虚拟滚动
const useVirtualScroll = computed(() => alertList.value.length > 1000)
</script>

<template>
  <!-- 虚拟滚动表格 -->
  <el-table-v2
    v-if="useVirtualScroll"
    :columns="columns"
    :data="alertList"
    :width="700"
    :height="600"
    fixed
  />
  
  <!-- 普通表格 -->
  <el-table v-else :data="alertList">
    <!-- 列定义 -->
  </el-table>
</template>

<!-- 4. 搜索防抖 -->
<script setup>
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'

const searchKeyword = ref('')

// 防抖搜索（500ms）
const debouncedSearch = useDebounceFn((keyword) => {
  performSearch(keyword)
}, 500)

const handleSearchInput = (value) => {
  searchKeyword.value = value
  debouncedSearch(value)
}
</script>

<!-- 5. 滚动节流 -->
<script setup>
import { useThrottleFn } from '@vueuse/core'

// 节流滚动事件（100ms）
const throttledScroll = useThrottleFn(() => {
  // 处理滚动逻辑
  checkScrollPosition()
}, 100)

onMounted(() => {
  window.addEventListener('scroll', throttledScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', throttledScroll)
})
</script>
```

## 🎯 实施步骤

### 步骤1: 全局样式优化

创建 `frontend/src/styles/ui-ux-pro.css`:

```css
/* UI/UX Pro Max 全局样式 */

/* 字体配置 */
:root {
  --font-heading: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-body: 'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 交互反馈 */
.cursor-pointer {
  cursor: pointer;
}

.hover-bg-gray:hover {
  background-color: #f5f7fa;
  transition: background-color 200ms ease-out;
}

/* 动画优化 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* 标准过渡 */
.transition-colors {
  transition: color 200ms ease-out, background-color 200ms ease-out;
}

.transition-transform {
  transition: transform 200ms ease-out;
}

.transition-opacity {
  transition: opacity 200ms ease-out;
}

/* 表格优化 */
.el-table__row {
  transition: background-color 200ms ease-out;
}

.el-table__row:hover {
  cursor: pointer;
}

/* 卡片优化 */
.el-card {
  transition: box-shadow 200ms ease-out;
}

.el-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
```

### 步骤2: 在main.js中引入

```javascript
// frontend/src/main.js
import './styles/ui-ux-pro.css'
```

### 步骤3: 更新index.html

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>硬件告警智能诊断系统</title>
  
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

## 📊 预期效果

实施这些优化后，预期达到：

1. **专业度提升**: 使用专业字体和配色，提升整体视觉质量
2. **用户体验改善**: 更好的交互反馈和加载状态
3. **可访问性增强**: 支持键盘导航和屏幕阅读器
4. **性能优化**: 更流畅的动画和更快的渲染
5. **响应式优化**: 更好的移动端体验

## 🔍 验证清单

实施完成后，请验证：

- [ ] 所有可点击元素有cursor-pointer
- [ ] 所有图标都是SVG（无emoji）
- [ ] 表格行悬停有视觉反馈
- [ ] 图表配色专业且一致
- [ ] 空状态有友好提示
- [ ] 加载状态有骨架屏或loading
- [ ] 支持prefers-reduced-motion
- [ ] 字体加载正常（Poppins + Open Sans）
- [ ] 移动端布局正常
- [ ] 键盘导航可用

## 📚 参考资料

- [UI/UX Pro Max 设计规范](../.shared/ui-ux-pro-max/)
- [Element Plus 文档](https://element-plus.org/)
- [ECharts 文档](https://echarts.apache.org/)
- [Google Fonts](https://fonts.google.com/)
- [WCAG 2.1 可访问性指南](https://www.w3.org/WAI/WCAG21/quickref/)

---

**最后更新**: 2026-02-11
**状态**: 建议文档 - 待实施
