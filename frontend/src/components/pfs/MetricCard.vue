<template>
  <div class="metric-card" :class="statusClass">
    <div class="card-header">
      <div class="metric-info">
        <h3 class="metric-name">{{ metric.zh_name }}</h3>
        <p class="metric-desc">{{ metric.desc }}</p>
      </div>
      <el-icon class="status-icon" :class="statusClass">
        <component :is="statusIcon" />
      </el-icon>
    </div>
    
    <div class="card-body">
      <div class="metric-value">
        <span class="value">{{ formattedValue }}</span>
        <span class="unit">{{ metric.unit_zh }}</span>
      </div>
      
      <div class="metric-stats">
        <div class="stat-item">
          <span class="stat-label">平均</span>
          <span class="stat-value">{{ formatValue(metric.statistics?.avg) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">最大</span>
          <span class="stat-value">{{ formatValue(metric.statistics?.max) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">P95</span>
          <span class="stat-value">{{ formatValue(metric.statistics?.p95) }}</span>
        </div>
      </div>
    </div>
    
    <div class="card-footer">
      <el-tag :type="statusTagType" size="small">
        {{ statusText }}
      </el-tag>
      <div class="trend-indicator" :class="trendClass">
        <el-icon><component :is="trendIcon" /></el-icon>
        <span>{{ trendText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheck, Warning, CircleClose, TrendCharts, Top, Bottom } from '@element-plus/icons-vue'

const props = defineProps({
  metric: {
    type: Object,
    required: true
  }
})

// 格式化数值
const formatValue = (value) => {
  if (value === null || value === undefined) return '-'
  
  // 根据单位格式化
  if (props.metric.unit === 'bytes' || props.metric.unit === 'binBps') {
    return formatBytes(value)
  } else if (props.metric.unit === 'percentunit') {
    return (value * 100).toFixed(2) + '%'
  } else if (props.metric.unit === 'µs') {
    return value.toFixed(2)
  } else {
    return value.toFixed(2)
  }
}

// 格式化字节
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 当前值（使用最新数据点或平均值）
const formattedValue = computed(() => {
  const latestValue = props.metric.data_points?.[props.metric.data_points.length - 1]?.value
  return formatValue(latestValue || props.metric.statistics?.avg)
})

// 状态判断
const status = computed(() => {
  const value = props.metric.statistics?.avg
  const config = props.metric
  
  if (!value || !config.warn_threshold) return 'normal'
  
  // 容量类指标（使用率）
  if (config.unit === 'percentunit') {
    if (value >= config.critical_threshold) return 'critical'
    if (value >= config.warn_threshold) return 'warning'
    return 'normal'
  }
  
  // 延迟类指标（数值越大越差）
  if (config.unit === 'µs') {
    if (value >= config.critical_threshold) return 'critical'
    if (value >= config.warn_threshold) return 'warning'
    return 'normal'
  }
  
  // 吞吐/QPS类指标（负阈值表示下降百分比）
  if (config.warn_threshold < 0) {
    // 这里需要对比历史数据，暂时返回 normal
    return 'normal'
  }
  
  return 'normal'
})

const statusClass = computed(() => `status-${status.value}`)

const statusIcon = computed(() => {
  switch (status.value) {
    case 'critical': return CircleClose
    case 'warning': return Warning
    default: return CircleCheck
  }
})

const statusTagType = computed(() => {
  switch (status.value) {
    case 'critical': return 'danger'
    case 'warning': return 'warning'
    default: return 'success'
  }
})

const statusText = computed(() => {
  switch (status.value) {
    case 'critical': return '严重'
    case 'warning': return '警告'
    default: return '正常'
  }
})

// 趋势判断（需要对比数据）
const trend = computed(() => {
  // TODO: 实现趋势判断逻辑
  return 'stable'
})

const trendClass = computed(() => `trend-${trend.value}`)

const trendIcon = computed(() => {
  switch (trend.value) {
    case 'up': return Top
    case 'down': return Bottom
    default: return TrendCharts
  }
})

const trendText = computed(() => {
  switch (trend.value) {
    case 'up': return '上升'
    case 'down': return '下降'
    default: return '稳定'
  }
})
</script>

<style scoped>
.metric-card {
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: var(--spacing-4);
  transition: all 0.3s ease;
}

.metric-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.metric-card.status-normal {
  border-left: 4px solid var(--color-success);
}

.metric-card.status-warning {
  border-left: 4px solid var(--color-warning);
}

.metric-card.status-critical {
  border-left: 4px solid var(--color-danger);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-3);
}

.metric-info {
  flex: 1;
}

.metric-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-1) 0;
}

.metric-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.status-icon {
  font-size: 24px;
}

.status-icon.status-normal {
  color: var(--color-success);
}

.status-icon.status-warning {
  color: var(--color-warning);
}

.status-icon.status-critical {
  color: var(--color-danger);
}

.card-body {
  margin-bottom: var(--spacing-3);
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
}

.value {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--text-primary);
}

.unit {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
}

.metric-stats {
  display: flex;
  gap: var(--spacing-4);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.stat-value {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-color);
}

.trend-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
}

.trend-indicator.trend-up {
  color: var(--color-danger);
}

.trend-indicator.trend-down {
  color: var(--color-success);
}

.trend-indicator.trend-stable {
  color: var(--text-secondary);
}
</style>
