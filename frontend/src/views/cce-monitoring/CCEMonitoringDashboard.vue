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
          @change="onPeriodChange"
        >
          <el-option label="1m" value="1m" />
          <el-option label="5m" value="5m" />
          <el-option label="15m" value="15m" />
          <el-option label="1h" value="1h" />
        </el-select>
        <!-- P1：自动刷新 -->
        <el-select
          v-model="autoRefreshSec"
          style="width: 100px; margin-right: 8px"
          @change="onAutoRefreshChange"
        >
          <el-option label="不自动刷新" :value="0" />
          <el-option label="30 秒" :value="30" />
          <el-option label="1 分钟" :value="60" />
          <el-option label="5 分钟" :value="300" />
        </el-select>
        <el-button type="primary" :loading="loadingInstant" @click="refresh" :disabled="!selectedCluster">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 未配置提示 -->
    <el-alert v-if="configError" :title="configError" type="warning" :closable="false" show-icon style="margin-bottom: 16px" />

    <!-- 集群基础信息卡片 -->
    <div v-if="selectedCluster" class="content-card cluster-info-card" style="margin-bottom: 16px">
      <div class="content-card-header">
        <div class="content-card-title">集群信息</div>
        <div class="content-card-extra" style="display:flex;gap:8px;align-items:center">
          <el-tag v-if="clusterDetail" :type="clusterDetail.clusterPhase === 'running' ? 'success' : 'danger'" size="small">
            {{ clusterDetail.clusterPhase || '未知' }}
          </el-tag>
          <!-- KubeConfig 下载，管理员可见 -->
          <el-dropdown trigger="click" :loading="downloadingKubeconfig" @command="handleDownloadKubeconfig">
            <el-button size="small" :loading="downloadingKubeconfig">
              下载 KubeConfig <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="vpc">内网（VPC）</el-dropdown-item>
                <el-dropdown-item command="public">外网（EIP）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <div v-if="loadingDetail" style="padding: 12px; color: var(--text-secondary)">加载集群信息...</div>
      <div v-else-if="clusterDetail" class="cluster-info-grid">
        <div class="cluster-info-item">
          <span class="info-label">集群名称</span>
          <span class="info-value">{{ clusterDetail.clusterName || selectedCluster }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">K8S 版本</span>
          <span class="info-value mono">{{ clusterDetail.k8sVersion || '-' }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">Master 类型</span>
          <span class="info-value">{{ clusterDetail.masterType === 'managed' ? '托管型' : clusterDetail.masterType === 'custom' ? '自定义' : (clusterDetail.masterType || '-') }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">网络模式</span>
          <span class="info-value mono">{{ clusterDetail.networkMode || '-' }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">节点总数</span>
          <span class="info-value">{{ clusterDetail.nodeNum ?? '-' }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">Pod 网段</span>
          <span class="info-value mono">{{ clusterDetail.clusterPodCIDR || '-' }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">Service 网段</span>
          <span class="info-value mono">{{ clusterDetail.clusterIPServiceCIDR || '-' }}</span>
        </div>
        <div class="cluster-info-item">
          <span class="info-label">kube-proxy</span>
          <span class="info-value mono">{{ clusterDetail.kubeProxyMode || '-' }}</span>
        </div>
      </div>
      <div v-else style="padding: 12px; color: var(--text-secondary); font-size: 13px">
        集群基础信息不可用（需在系统设置中配置 BCE AK/SK）
      </div>
    </div>

    <!-- 未选集群 -->
    <div v-if="!selectedCluster && !configError" class="empty-hint">
      <el-empty description="请从右上角选择一个集群查看监控数据" />
    </div>

    <template v-if="selectedCluster && clusterData">
      <!-- ── 通用指标区域循环渲染 ── -->
      <template v-for="catKey in CATEGORY_ORDER" :key="catKey">
        <div class="content-card" v-if="clusterData.categories?.[catKey]">
          <div class="content-card-header">
            <div class="content-card-title">{{ clusterData.categories[catKey].label }}</div>
            <!-- 节点状态额外标签 -->
            <div class="content-card-extra" v-if="catKey === 'node_condition'">
              <el-tag type="success" v-if="allNodeCondNormal">全部正常</el-tag>
              <el-tag type="danger" v-else>存在异常节点</el-tag>
            </div>
          </div>
          <div class="content-card-body metrics-grid">
            <div
              v-for="m in clusterData.categories[catKey].metrics"
              :key="m.key"
              class="metric-card"
              :class="[getMetricClass(catKey, m), m.key === 'pending_pvc_count' && m.value > 0 ? 'metric-card--clickable' : '']"
              @click="m.key === 'pending_pvc_count' && m.value > 0 ? openPvcDrawer() : null"
            >
              <div class="metric-label">{{ m.label }}</div>
              <div class="metric-value">
                <span v-if="m.value !== null">{{ formatValue(m) }}</span>
                <span v-else class="metric-null">-</span>
              </div>
              <!-- 百分比进度条 -->
              <template v-if="m.unit === '%' && m.value !== null && catKey === 'usage'">
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
      </template>
    </template>

    <!-- ── 趋势图区 ── -->
    <div class="content-card" v-if="selectedCluster">
      <div class="content-card-header">
        <div class="content-card-title">趋势图</div>
        <div class="content-card-extra">
          <el-text type="info" size="small" v-if="lastRefreshTime">
            上次刷新：{{ lastRefreshTime }}
            <span v-if="autoRefreshSec > 0" class="auto-refresh-badge">
              <el-icon><CircleCheck /></el-icon>自动刷新
            </span>
          </el-text>
        </div>
      </div>
      <div class="content-card-body">
        <div v-if="loadingCharts" class="chart-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <div v-else-if="chartError" class="chart-empty">
          <el-empty :description="chartError" :image-size="60" />
        </div>
        <div v-else-if="chartsEmpty" class="chart-empty">
          <el-empty description="暂无趋势数据，请确认 Prometheus 可以正常查询" :image-size="80" />
        </div>
        <div v-else class="charts-grid">
          <div v-for="(chart, key) in chartData.charts" :key="key" class="chart-item">
            <div class="chart-title" :style="{ borderLeft: `3px solid ${chartColor(key)}` }">
              {{ chart.label }} <span class="chart-unit">{{ chart.unit }}</span>
            </div>
            <div :ref="el => setChartRef(el, key)" class="chart-canvas"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Pending PVC 详情 Drawer -->
  <el-drawer
    v-model="pvcDrawerVisible"
    title="Pending PVC 详情"
    size="60%"
    destroy-on-close
  >
    <template #header>
      <div style="display:flex;align-items:center;gap:10px">
        <span>Pending PVC 详情</span>
        <el-tag type="danger" effect="dark">{{ pvcList.length }} 条</el-tag>
        <span class="text-disabled" style="font-size:var(--text-sm)">集群: {{ selectedCluster }}</span>
      </div>
    </template>
    <div v-if="pvcLoading" style="text-align:center;padding:40px">
      <el-icon class="is-loading" :size="32"><Refresh /></el-icon>
      <div class="text-disabled" style="margin-top:var(--space-2)">加载中...</div>
    </div>
    <el-table v-else :data="pvcList" stripe border size="small" style="width:100%">
      <el-table-column prop="namespace" label="Namespace" min-width="160" show-overflow-tooltip  resizable/>
      <el-table-column prop="pvc" label="PVC 名称" min-width="220" show-overflow-tooltip  resizable/>
      <el-table-column prop="storageClass" label="StorageClass" min-width="130" show-overflow-tooltip resizable>
        <template #default="{ row }">
          <span>{{ row.storageClass || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="capacity" label="容量" width="80" resizable>
        <template #default="{ row }">
          <span>{{ row.capacity || '-' }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-drawer>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Refresh, ArrowDown, CircleCheck } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getCCEClusters, getCCEMonitoringConfig, queryCCECluster, queryCCEClusterCharts, queryPendingPVCs } from '@/api/cceMonitoring'
import { getCCEClusterDetail, downloadKubeconfig } from '@/api/cmdb'

// category 展示顺序
const CATEGORY_ORDER = ['basic', 'capacity', 'usage', 'node_condition', 'network', 'disk_io', 'load', 'components', 'apiserver']

// P2：Datadog 调色板
const DD_COLORS = ['#632ca6', '#00a4bd', '#e5a111', '#e5273b', '#00c984', '#9d66b7', '#0085c2', '#f2a900', '#c23b22', '#00875a']

// 按图表 key 的插入顺序分配固定颜色
const chartColorMap = {}
let colorIndex = 0
const chartColor = (key) => {
  if (!(key in chartColorMap)) {
    chartColorMap[key] = DD_COLORS[colorIndex % DD_COLORS.length]
    colorIndex++
  }
  return chartColorMap[key]
}

// ── 状态 ──────────────────────────────────────────────────────────────────
const clusterIds = ref([])
const selectedCluster = ref('')
const periodHours = ref(3)
const step = ref('5m')
const autoRefreshSec = ref(0)
const clusterData = ref(null)
const chartData = ref(null)
const configError = ref('')
const chartError = ref('')
const lastRefreshTime = ref('')
const loadingInstant = ref(false)
const loadingCharts = ref(false)
const clusterDetail = ref(null)
const loadingDetail = ref(false)
const downloadingKubeconfig = ref(false)

// Pending PVC Drawer
const pvcDrawerVisible = ref(false)
const pvcLoading = ref(false)
const pvcList = ref([])

let autoRefreshTimer = null

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

const formatXLabel = (timestamp, totalHours) => {
  const d = new Date(timestamp)
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  if (totalHours > 24) {
    const mo = (d.getMonth() + 1).toString().padStart(2, '0')
    const dd = d.getDate().toString().padStart(2, '0')
    return `${mo}-${dd} ${hh}:${mm}`
  }
  return `${hh}:${mm}`
}

const renderCharts = async () => {
  if (!chartData.value?.charts) return
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

    const color = chartColor(key)
    const xData = chart.data.map(p => formatXLabel(p.timestamp, periodHours.value))
    const yData = chart.data.map(p => p.value)

    inst.setOption({
      grid: { top: 10, right: 16, bottom: 30, left: 52 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { fontSize: 10, interval: Math.floor(xData.length / 6), color: '#8c8c8c' },
        axisLine: { lineStyle: { color: '#e0e0e0' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 10, formatter: v => chart.unit === '%' ? `${v}%` : v, color: '#8c8c8c' },
        splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'line',
        data: yData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color },
        areaStyle: { color, opacity: 0.06 },
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
  if (m.unit === 'MB/s' || m.unit === 'GB') return m.value.toFixed(1)
  if (Number.isInteger(m.value)) return m.value
  return Number(m.value.toFixed(2))
}

const progressColor = (v) => {
  if (v >= 90) return '#f56c6c'
  if (v >= 75) return '#e6a23c'
  return '#67c23a'
}

const getMetricClass = (catKey, m) => {
  if (m.value === null) return ''

  if (catKey === 'basic') {
    if (m.key === 'pod_failed' && m.value > 0) return 'metric-card--danger'
    if (m.key === 'pod_pending' && m.value > 0) return 'metric-card--warning'
    return ''
  }

  if (catKey === 'usage') {
    if (m.unit !== '%') return ''
    if (m.value >= 90) return 'metric-card--danger'
    if (m.value >= 75) return 'metric-card--warning'
    return 'metric-card--ok'
  }

  if (catKey === 'node_condition') {
    return m.value > 0 ? 'metric-card--danger' : 'metric-card--ok'
  }

  if (catKey === 'apiserver') {
    if (m.key === 'read_success_rate' || m.key === 'write_success_rate') {
      if (m.value < 95) return 'metric-card--danger'
      if (m.value < 99) return 'metric-card--warning'
      return 'metric-card--ok'
    }
    if (m.key === 'get_p50_latency' || m.key === 'write_p50_latency') {
      if (m.value > 5) return 'metric-card--danger'
      if (m.value > 1) return 'metric-card--warning'
      return 'metric-card--ok'
    }
    return ''
  }

  if (catKey === 'components') {
    if (m.key === 'etcd_has_leader') return m.value === 0 ? 'metric-card--danger' : 'metric-card--ok'
    if (m.key === 'etcd_leader_changes' && m.value > 3) return 'metric-card--warning'
    if (m.key === 'pod_restarts_1h') {
      if (m.value > 50) return 'metric-card--danger'
      if (m.value > 10) return 'metric-card--warning'
      return ''
    }
    if (m.key === 'pending_pods_unschedulable' && m.value > 0) return 'metric-card--warning'
    if (m.key === 'pending_pvc_count' && m.value > 0) return 'metric-card--warning'
    return ''
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
  chartError.value = ''
  destroyCharts()
  try {
    const resp = await queryCCEClusterCharts(selectedCluster.value, periodHours.value, step.value)
    if (resp.success && !resp.data?.error) {
      chartData.value = resp.data
      loadingCharts.value = false
      await renderCharts()
      return
    }
    chartError.value = resp.data?.error || resp.error || '趋势图查询失败'
  } catch (e) {
    chartError.value = `趋势图查询异常：${e?.message || '未知错误'}`
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
  chartError.value = ''
  refresh()
  fetchClusterDetail(selectedCluster.value)
}

// P1b：时间范围切换同时刷新指标卡片
const onPeriodChange = () => {
  fetchInstant()
  fetchCharts()
}

// P1a：自动刷新控制
const startAutoRefresh = () => {
  stopAutoRefresh()
  if (autoRefreshSec.value > 0) {
    autoRefreshTimer = setInterval(refresh, autoRefreshSec.value * 1000)
  }
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const onAutoRefreshChange = () => {
  startAutoRefresh()
}

const fetchClusters = async () => {
  try {
    const resp = await getCCEClusters()
    if (resp.success) {
      clusterIds.value = resp.data.cluster_ids || []
      if (clusterIds.value.length > 0) {
        selectedCluster.value = clusterIds.value[0]
        refresh()
        fetchClusterDetail(clusterIds.value[0])
      }
    }
  } catch {
    ElMessage.error('获取集群列表失败')
  }
}

const fetchClusterDetail = async (clusterId) => {
  if (!clusterId) return
  loadingDetail.value = true
  clusterDetail.value = null
  try {
    const resp = await getCCEClusterDetail(clusterId)
    if (resp.success) {
      clusterDetail.value = resp.cluster
    }
  } catch {
    // 静默：AK/SK 未配置时不报错，只是不展示集群信息
  } finally {
    loadingDetail.value = false
  }
}

const handleDownloadKubeconfig = async (type) => {
  downloadingKubeconfig.value = true
  try {
    await downloadKubeconfig(selectedCluster.value, type)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || 'KubeConfig 下载失败')
  } finally {
    downloadingKubeconfig.value = false
  }
}

const openPvcDrawer = async () => {
  pvcDrawerVisible.value = true
  pvcLoading.value = true
  pvcList.value = []
  try {
    const resp = await queryPendingPVCs(selectedCluster.value)
    if (resp.success) {
      pvcList.value = resp.data.items || []
    }
  } catch (e) {
    ElMessage.error('获取 Pending PVC 失败')
  } finally {
    pvcLoading.value = false
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

const handleResize = () => {
  Object.values(chartInstances).forEach(inst => inst?.resize())
}

onMounted(async () => {
  await fetchConfig()
  await fetchClusters()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  stopAutoRefresh()
  destroyCharts()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
:deep(.el-progress-bar__inner) {
  background: var(--progress-color, var(--color-success)) !important;
  background-image: none !important;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  padding: 4px 0;
}

.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 8px;
  padding: 14px 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: box-shadow 0.2s;
}
.metric-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.metric-card--clickable { cursor: pointer; }
.metric-card--clickable:hover { box-shadow: 0 2px 12px rgba(250,173,20,0.3); }
.metric-card--ok      { border-color: var(--color-success-border); background: var(--color-success-bg); }
.metric-card--warning { border-color: var(--color-warning-border); background: var(--color-warning-bg); }
.metric-card--danger  { border-color: var(--color-error-border); background: var(--color-error-bg); }

.metric-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.3;
}
.metric-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  line-height: 1.2;
}
.metric-null { font-size: 20px; color: var(--text-disabled); }
.metric-unit { font-size: var(--text-xs); color: var(--text-tertiary); }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 20px;
}
.chart-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-3) 14px var(--space-2);
}
.chart-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
  padding-left: var(--space-2);
}
.chart-unit {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
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

/* 集群信息卡片 */
.cluster-info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px 16px;
  padding: 12px 0 4px;
}
.cluster-info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.info-label {
  font-size: var(--text-xs);
  color: var(--text-secondary, #8c8c8c);
  font-weight: var(--font-medium);
  letter-spacing: 0.02em;
}
.info-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}
.info-value.mono {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--text-sm);
}
.auto-refresh-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-1);
  color: var(--color-success);
  font-size: var(--text-sm);
}
</style>
