<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon"><el-icon><Monitor /></el-icon></div>
          APIServer 监控总览
        </div>
        <div class="page-subtitle">基于时间周期查看 APIServer 告警趋势、类型分布与集群分布</div>
      </div>
      <div class="page-actions">
        <el-radio-group v-model="periodHours" @change="fetchOverview">
          <el-radio-button :label="1">1小时</el-radio-button>
          <el-radio-button :label="6">6小时</el-radio-button>
          <el-radio-button :label="24">24小时</el-radio-button>
          <el-radio-button :label="168">7天</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="stats-grid">
      <div class="content-card stat-card"><div class="content-card-body"><div class="stat-label">总告警</div><div class="stat-value">{{ overview.summary?.total || 0 }}</div></div></div>
      <div class="content-card stat-card"><div class="content-card-body"><div class="stat-label">活跃告警</div><div class="stat-value">{{ overview.summary?.active || 0 }}</div></div></div>
      <div class="content-card stat-card"><div class="content-card-body"><div class="stat-label">严重告警</div><div class="stat-value danger">{{ overview.summary?.critical || 0 }}</div></div></div>
      <div class="content-card stat-card"><div class="content-card-body"><div class="stat-label">警告告警</div><div class="stat-value warning">{{ overview.summary?.warning || 0 }}</div></div></div>
    </div>

    <div class="chart-grid">
      <div class="content-card chart-card-wide">
        <div class="content-card-header"><div class="content-card-title">时间趋势</div></div>
        <div class="content-card-body"><div ref="timelineChartRef" class="chart-block chart-block-lg"></div></div>
      </div>
      <div class="content-card">
        <div class="content-card-header"><div class="content-card-title">指标类型分布</div></div>
        <div class="content-card-body"><div ref="metricChartRef" class="chart-block"></div></div>
      </div>
      <div class="content-card">
        <div class="content-card-header"><div class="content-card-title">集群分布</div></div>
        <div class="content-card-body"><div ref="clusterChartRef" class="chart-block"></div></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getAPIServerMonitoringOverview } from '@/api/apiserverAlerts'

const periodHours = ref(24)
const overview = ref({ summary: {}, timeline: [], metric_distribution: [], cluster_distribution: [] })
const timelineChartRef = ref(null)
const metricChartRef = ref(null)
const clusterChartRef = ref(null)
let timelineChart = null
let metricChart = null
let clusterChart = null

const fetchOverview = async () => {
  try {
    const response = await getAPIServerMonitoringOverview({ period_hours: periodHours.value })
    if (response.success) {
      overview.value = response.data
      await nextTick()
      renderCharts()
    }
  } catch {
    ElMessage.error('获取 APIServer 监控总览失败')
  }
}

const renderCharts = () => {
  if (!timelineChart && timelineChartRef.value) timelineChart = echarts.init(timelineChartRef.value)
  if (!metricChart && metricChartRef.value) metricChart = echarts.init(metricChartRef.value)
  if (!clusterChart && clusterChartRef.value) clusterChart = echarts.init(clusterChartRef.value)

  timelineChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['critical', 'warning'] },
    grid: { left: '4%', right: '4%', bottom: '4%', top: 32, containLabel: true },
    xAxis: {
      type: 'category',
      data: (overview.value.timeline || []).map(item => item.time),
      axisLabel: { color: '#8c8c8c' },
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8c8c8c' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      { name: 'critical', type: 'line', smooth: false, symbol: 'none', data: (overview.value.timeline || []).map(item => item.critical), lineStyle: { width: 1.5, color: '#e5273b' }, itemStyle: { color: '#e5273b' }, areaStyle: { color: '#e5273b', opacity: 0.06 } },
      { name: 'warning', type: 'line', smooth: false, symbol: 'none', data: (overview.value.timeline || []).map(item => item.warning), lineStyle: { width: 1.5, color: '#e5a111' }, itemStyle: { color: '#e5a111' }, areaStyle: { color: '#e5a111', opacity: 0.06 } }
    ]
  })

  metricChart?.setOption({
    tooltip: { trigger: 'item' },
    color: ['#e5273b', '#e5a111', '#00a4bd', '#632ca6', '#00c984', '#9d66b7'],
    series: [{ type: 'pie', radius: ['42%', '70%'], data: overview.value.metric_distribution || [], itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 } }]
  })

  clusterChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '4%', right: '4%', bottom: '4%', top: 16, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#8c8c8c' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: (overview.value.cluster_distribution || []).map(item => item.name),
      axisLabel: { color: '#8c8c8c' },
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
    },
    series: [{ type: 'bar', barMaxWidth: 22, data: (overview.value.cluster_distribution || []).map(item => item.value), itemStyle: { color: '#632ca6', borderRadius: [0, 3, 3, 0] } }]
  })
}

const handleResize = () => {
  timelineChart?.resize()
  metricChart?.resize()
  clusterChart?.resize()
}

watch(periodHours, fetchOverview)
onMounted(async () => {
  await fetchOverview()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  timelineChart?.dispose()
  metricChart?.dispose()
  clusterChart?.dispose()
})
</script>

<style scoped>
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:var(--space-5); margin-bottom:var(--space-6); }
.stat-card .content-card-body { display:flex; flex-direction:column; gap:var(--space-2); }
.stat-label { font-size:var(--text-sm); color:var(--text-tertiary); }
.stat-value { font-size:28px; font-weight:700; color:var(--text-primary); }
.stat-value.danger { color: var(--color-danger); }
.stat-value.warning { color: var(--color-warning); }
.chart-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--space-5); }
.chart-card-wide { grid-column:1 / -1; }
.chart-block { width:100%; height:320px; }
.chart-block-lg { height:420px; }
@media (max-width: 960px) { .chart-grid { grid-template-columns:1fr; } .chart-card-wide { grid-column:auto; } }
</style>
