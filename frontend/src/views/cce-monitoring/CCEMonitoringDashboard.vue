<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon"><el-icon><Monitor /></el-icon></div>
          CCE 集群实时监控
        </div>
        <div class="page-subtitle">实时查询 Prometheus 展示集群健康状态，与 APIServer 监控共用同一套 Prometheus 配置</div>
      </div>
      <div class="page-actions">
        <el-select
          v-model="selectedCluster"
          placeholder="选择集群"
          style="width: 260px; margin-right: 8px"
          filterable
          @change="onClusterChange"
        >
          <el-option v-for="id in clusterIds" :key="id" :label="id" :value="id" />
        </el-select>
        <el-select
          v-model="periodHours"
          style="width: 120px; margin-right: 8px"
          :teleported="false"
          @change="onPeriodChange"
        >
          <el-option label="近 1 小时" :value="1" />
          <el-option label="近 3 小时" :value="3" />
          <el-option label="近 6 小时" :value="6" />
          <el-option label="近 12 小时" :value="12" />
          <el-option label="近 24 小时" :value="24" />
          <el-option label="近 3 天" :value="72" />
        </el-select>
        <el-select
          v-model="step"
          style="width: 90px; margin-right: 8px"
          :teleported="false"
          @change="onPeriodChange"
        >
          <el-option label="1m" value="1m" />
          <el-option label="5m" value="5m" />
          <el-option label="15m" value="15m" />
          <el-option label="1h" value="1h" />
        </el-select>
        <el-button type="primary" :loading="loadingInstant" @click="refresh" :disabled="!selectedCluster">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 未配置提示 -->
    <el-alert v-if="configError" :title="configError" type="warning" :closable="false" show-icon style="margin-bottom: 16px" />

    <!-- 未选集群 -->
    <div v-if="!selectedCluster && !configError" class="empty-hint">
      <el-empty description="请从右上角选择一个集群查看监控数据" />
    </div>

    <template v-if="selectedCluster && clusterData">
      <!-- ── 基础资源 ── -->
      <div class="content-card" v-if="clusterData.categories?.basic">
        <div class="content-card-header">
          <div class="content-card-title">{{ clusterData.categories.basic.label }}</div>
        </div>
        <div class="content-card-body metrics-grid">
          <div
            v-for="m in clusterData.categories.basic.metrics"
            :key="m.key"
            class="metric-card"
          >
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value">
              <span v-if="m.value !== null">{{ formatValue(m) }}</span>
              <span v-else class="metric-null">-</span>
            </div>
            <div class="metric-unit">{{ m.unit }}</div>
          </div>
        </div>
      </div>

      <!-- ── 资源使用率 ── -->
      <div class="content-card" v-if="clusterData.categories?.usage">
        <div class="content-card-header">
          <div class="content-card-title">{{ clusterData.categories.usage.label }}</div>
        </div>
        <div class="content-card-body metrics-grid">
          <div
            v-for="m in clusterData.categories.usage.metrics"
            :key="m.key"
            class="metric-card"
            :class="getUsageClass(m)"
          >
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value">
              <span v-if="m.value !== null">{{ formatValue(m) }}</span>
              <span v-else class="metric-null">-</span>
            </div>
            <template v-if="m.unit === '%' && m.value !== null">
              <div :style="{ '--progress-color': progressColor(m.value) }">
                <el-progress
                  :percentage="Math.min(100, Math.round(m.value))"
                  :show-text="false"
                  :stroke-width="5"
                  style="margin-top: 4px"
                />
              </div>
            </template>
            <div v-else class="metric-unit">{{ m.unit }}</div>
          </div>
        </div>
      </div>

      <!-- ── 节点状态 ── -->
      <div class="content-card" v-if="clusterData.categories?.node_condition">
        <div class="content-card-header">
          <div class="content-card-title">{{ clusterData.categories.node_condition.label }}</div>
          <div class="content-card-extra">
            <el-tag type="success" v-if="allNodeCondNormal">全部正常</el-tag>
            <el-tag type="danger" v-else>存在异常节点</el-tag>
          </div>
        </div>
        <div class="content-card-body metrics-grid">
          <div
            v-for="m in clusterData.categories.node_condition.metrics"
            :key="m.key"
            class="metric-card"
            :class="m.value > 0 ? 'metric-card--danger' : 'metric-card--ok'"
          >
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value">
              <span v-if="m.value !== null">{{ m.value }}</span>
              <span v-else class="metric-null">-</span>
            </div>
            <div class="metric-unit">{{ m.unit }}</div>
          </div>
        </div>
      </div>

      <!-- ── APIServer 健康 ── -->
      <div class="content-card" v-if="clusterData.categories?.apiserver">
        <div class="content-card-header">
          <div class="content-card-title">{{ clusterData.categories.apiserver.label }}</div>
        </div>
        <div class="content-card-body metrics-grid">
          <div
            v-for="m in clusterData.categories.apiserver.metrics"
            :key="m.key"
            class="metric-card"
            :class="getApiClass(m)"
          >
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value">
              <span v-if="m.value !== null">{{ formatValue(m) }}</span>
              <span v-else class="metric-null">-</span>
            </div>
            <div class="metric-unit">{{ m.unit }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── 趋势图区（独立于 clusterData，避免竞态）── -->
    <div class="content-card" v-if="selectedCluster">
      <div class="content-card-header">
        <div class="content-card-title">趋势图</div>
        <div class="content-card-extra">
          <el-text type="info" size="small" v-if="lastRefreshTime">上次刷新：{{ lastRefreshTime }}</el-text>
        </div>
      </div>
      <div class="content-card-body">
        <div v-if="loadingCharts" class="chart-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <div v-else-if="chartsEmpty" class="chart-empty">
          <el-empty description="暂无趋势数据，请确认 Prometheus 可以正常查询" :image-size="80" />
        </div>
        <div v-else class="charts-grid">
          <div v-for="(chart, key) in chartData.charts" :key="key" class="chart-item">
            <div class="chart-title">{{ chart.label }} <span class="chart-unit">{{ chart.unit }}</span></div>
            <div :ref="el => setChartRef(el, key)" class="chart-canvas"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getCCEClusters, getCCEMonitoringConfig, queryCCECluster, queryCCEClusterCharts } from '@/api/cceMonitoring'

// ── 状态 ──────────────────────────────────────────────────────────────────
const clusterIds = ref([])
const selectedCluster = ref('')
const periodHours = ref(3)
const step = ref('5m')
const clusterData = ref(null)
const chartData = ref(null)
const configError = ref('')
const lastRefreshTime = ref('')
const loadingInstant = ref(false)
const loadingCharts = ref(false)

// ── ECharts 实例管理 ──────────────────────────────────────────────────────
const chartRefs = {}
const chartInstances = {}

const setChartRef = (el, key) => {
  if (el) chartRefs[key] = el
}

const destroyCharts = () => {
  Object.values(chartInstances).forEach(inst => inst?.dispose())
  Object.keys(chartInstances).forEach(k => delete chartInstances[k])
}

const renderCharts = async () => {
  if (!chartData.value?.charts) return
  // 等两个 tick：第一个 tick 让 v-for DOM 创建，第二个 tick 确保 :ref 回调全部执行
  await nextTick()
  await nextTick()
  for (const [key, chart] of Object.entries(chartData.value.charts)) {
    if (!chart.data?.length) continue
    const el = chartRefs[key]
    if (!el) continue

    if (chartInstances[key]) {
      chartInstances[key].dispose()
    }
    const inst = echarts.init(el)
    chartInstances[key] = inst

    const xData = chart.data.map(p => {
      const d = new Date(p.timestamp)
      return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    })
    const yData = chart.data.map(p => p.value)

    inst.setOption({
      grid: { top: 10, right: 16, bottom: 30, left: 48 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { fontSize: 10, interval: Math.floor(xData.length / 6) },
        axisLine: { lineStyle: { color: '#ddd' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, formatter: v => chart.unit === '%' ? `${v}%` : v },
        splitLine: { lineStyle: { color: '#f0f0f0' } },
      },
      series: [{
        type: 'line',
        data: yData,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1a73e8' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(26,115,232,0.15)' }, { offset: 1, color: 'rgba(26,115,232,0)' }] } },
      }],
      tooltip: {
        trigger: 'axis',
        formatter: params => {
          const p = params[0]
          return `${p.name}<br/>${chart.label}: <b>${p.value}${chart.unit}</b>`
        },
      },
    })
  }
}

// ── computed ──────────────────────────────────────────────────────────────
const allNodeCondNormal = computed(() => {
  const metrics = clusterData.value?.categories?.node_condition?.metrics || []
  return metrics.every(m => m.value === null || m.value === 0)
})

const chartsEmpty = computed(() => {
  if (!chartData.value?.charts) return true
  return Object.values(chartData.value.charts).every(c => !c.data?.length)
})

// ── 工具函数 ──────────────────────────────────────────────────────────────
const formatValue = (m) => {
  if (m.value === null) return '-'
  if (m.unit === '%') return m.value.toFixed(1)
  if (m.unit === 's') return m.value.toFixed(3)
  if (Number.isInteger(m.value)) return m.value
  return m.value
}

const progressColor = (v) => {
  if (v >= 90) return '#f56c6c'
  if (v >= 75) return '#e6a23c'
  return '#67c23a'
}

const USAGE_KEYS = new Set(['cpu_usage_pct', 'memory_usage_pct', 'cpu_request_pct', 'memory_request_pct', 'disk_usage_pct'])
const getUsageClass = (m) => {
  if (!USAGE_KEYS.has(m.key) || m.value === null) return ''
  if (m.value >= 90) return 'metric-card--danger'
  if (m.value >= 75) return 'metric-card--warning'
  return 'metric-card--ok'
}

const getApiClass = (m) => {
  if (m.value === null) return ''
  if (m.key === 'read_success_rate' || m.key === 'write_success_rate') {
    if (m.value < 95) return 'metric-card--danger'
    if (m.value < 99) return 'metric-card--warning'
    return 'metric-card--ok'
  }
  return ''
}

// ── 数据获取 ──────────────────────────────────────────────────────────────
const fetchInstant = async () => {
  if (!selectedCluster.value) return
  loadingInstant.value = true
  try {
    const resp = await queryCCECluster(selectedCluster.value)
    if (resp.success) {
      if (resp.data.error) {
        configError.value = resp.data.error
      } else {
        configError.value = ''
        clusterData.value = resp.data
        lastRefreshTime.value = new Date().toLocaleTimeString()
      }
    } else {
      ElMessage.error(resp.error || '查询失败')
    }
  } catch {
    ElMessage.error('查询集群数据失败')
  } finally {
    loadingInstant.value = false
  }
}

const fetchCharts = async () => {
  if (!selectedCluster.value) return
  loadingCharts.value = true
  destroyCharts()
  try {
    const resp = await queryCCEClusterCharts(selectedCluster.value, periodHours.value, step.value)
    if (resp.success && !resp.data.error) {
      chartData.value = resp.data
      // 先关闭 loading，让 charts-grid DOM 渲染出来，再初始化 ECharts
      loadingCharts.value = false
      await renderCharts()
      return
    }
  } catch {
    // 静默失败，趋势图不影响主面板
  }
  loadingCharts.value = false
}

const refresh = () => {
  fetchInstant()
  fetchCharts()
}

const onClusterChange = () => {
  clusterData.value = null
  chartData.value = null
  refresh()
}

const onPeriodChange = () => {
  fetchCharts()
}

const fetchClusters = async () => {
  try {
    const resp = await getCCEClusters()
    if (resp.success) {
      clusterIds.value = resp.data.cluster_ids || []
      if (clusterIds.value.length > 0) {
        selectedCluster.value = clusterIds.value[0]
        refresh()
      }
    }
  } catch {
    ElMessage.error('获取集群列表失败')
  }
}

const fetchConfig = async () => {
  try {
    const resp = await getCCEMonitoringConfig()
    if (resp.success && !resp.data.grafana_url) {
      configError.value = '尚未配置 Prometheus 连接信息，请前往 系统配置 → Prometheus 配置 填写 grafana_url / token / instance_id / cluster_ids'
    }
  } catch { /* 静默 */ }
}

// ── 窗口 resize ───────────────────────────────────────────────────────────
const handleResize = () => {
  Object.values(chartInstances).forEach(inst => inst?.resize())
}

onMounted(async () => {
  await fetchConfig()
  await fetchClusters()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  destroyCharts()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* 覆盖全局进度条颜色，让动态颜色生效 */
:deep(.el-progress-bar__inner) {
  background: var(--progress-color, #67c23a) !important;
  background-image: none !important;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  padding: 4px 0;
}

.metric-card {
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 14px 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: box-shadow 0.2s;
}
.metric-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.metric-card--ok    { border-color: #b7eb8f; background: #f6ffed; }
.metric-card--warning { border-color: #ffd591; background: #fffbe6; }
.metric-card--danger  { border-color: #ffb8b8; background: #fff1f0; }

.metric-label {
  font-size: 12px;
  color: #666;
  line-height: 1.3;
}
.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.2;
}
.metric-null { font-size: 20px; color: #bbb; }
.metric-unit { font-size: 11px; color: #999; }

/* ── 趋势图 ── */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 20px;
}
.chart-item {
  background: #fafafa;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px 14px 8px;
}
.chart-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
}
.chart-unit {
  font-size: 11px;
  color: #999;
  font-weight: normal;
}
.chart-canvas {
  width: 100%;
  height: 180px;
}
.chart-loading, .chart-empty {
  padding: 20px 0;
}

.empty-hint { padding: 60px 0; }
</style>
