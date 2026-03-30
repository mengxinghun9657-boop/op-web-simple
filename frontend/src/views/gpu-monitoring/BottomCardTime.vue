<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><DataLine /></el-icon>
          </div>
          bottom卡时数据
        </div>
        <div class="page-subtitle">按 bottom 规则统计 GPU Pod、队列和型号占用，自动过滤平均利用率大于 70% 的记录</div>
      </div>
      <div class="page-actions">
        <el-button @click="handlePreview" :loading="loading">
          <el-icon><Search /></el-icon>
          即时预览
        </el-button>
        <el-button type="primary" @click="handleAnalyze" :loading="analyzing">
          <el-icon><DataLine /></el-icon>
          生成分析报告
        </el-button>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">查询条件</div>
      </div>
      <div class="content-card-body">
        <el-form class="filter-form">
          <el-form-item label="集群ID列表">
            <div class="cluster-input-wrap">
              <div class="input-label-row">
                <span class="cluster-hint">每行一个，支持多集群聚合分析</span>
                <el-button size="small" @click="loadClusterConfig" :loading="loadingConfig">
                  <el-icon><Download /></el-icon>
                  加载系统配置
                </el-button>
              </div>
              <el-input
                v-model="clusterIdsText"
                type="textarea"
                :rows="5"
                placeholder="请输入集群ID，每行一个&#10;例如：&#10;cce-xrg955qz&#10;cce-9m1ht29q"
                class="cluster-textarea"
              />
              <p class="cluster-count">当前已输入 {{ clusterIds.length }} 个集群ID</p>
            </div>
          </el-form-item>
          <el-form-item label="时间范围">
            <el-date-picker
              v-model="dateRange"
              type="datetimerange"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              value-format="YYYY-MM-DDTHH:mm:ss.SSS[Z]"
              class="range-picker"
            />
          </el-form-item>
          <el-form-item label="采样步长">
            <el-select v-model="step" class="small-select">
              <el-option label="1m" value="1m" />
              <el-option label="5m" value="5m" />
              <el-option label="10m" value="10m" />
              <el-option label="15m" value="15m" />
              <el-option label="30m" value="30m" />
              <el-option label="1h" value="1h" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标型号">
            <el-select v-model="targetModels" multiple collapse-tags collapse-tags-tooltip class="model-select">
              <el-option label="H800" value="H800" />
              <el-option label="L20" value="L20" />
              <el-option label="H20" value="H20" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template v-if="result">
      <div class="stats-grid">
        <div class="content-card stat-card">
          <div class="content-card-body">
            <div class="stat-label">Bottom Pod 数量</div>
            <div class="stat-value">{{ result.summary.pod_count }}</div>
          </div>
        </div>
        <div class="content-card stat-card">
          <div class="content-card-body">
            <div class="stat-label">队列数量</div>
            <div class="stat-value">{{ result.summary.namespace_count }}</div>
          </div>
        </div>
        <div class="content-card stat-card">
          <div class="content-card-body">
            <div class="stat-label">总卡时</div>
            <div class="stat-value">{{ result.summary.total_gpu_hours }}</div>
          </div>
        </div>
        <div class="content-card stat-card">
          <div class="content-card-body">
            <div class="stat-label">总 Bottom</div>
            <div class="stat-value">{{ result.summary.total_bottom }}</div>
          </div>
        </div>
      </div>

      <div class="chart-grid">
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">型号 Bottom 分布</div>
          </div>
          <div class="content-card-body">
            <div ref="modelChartRef" class="chart-block"></div>
          </div>
        </div>

        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">队列 Bottom TOP 10</div>
          </div>
          <div class="content-card-body">
            <div ref="namespaceChartRef" class="chart-block"></div>
          </div>
        </div>

        <div class="content-card chart-card-wide">
          <div class="content-card-header">
            <div class="content-card-title">Pod Bottom TOP 10</div>
          </div>
          <div class="content-card-body">
            <div ref="podChartRef" class="chart-block chart-block-lg"></div>
          </div>
        </div>
      </div>

      <div class="summary-grid">
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">GPU 型号 Bottom 汇总</div>
          </div>
          <div class="content-card-body">
            <el-table :data="result.model_summary" size="small" class="google-table">
              <el-table-column prop="model" label="型号" min-width="120" />
              <el-table-column prop="gpu_hours" label="卡时(h)" min-width="120" />
              <el-table-column prop="bottom" label="Bottom" min-width="120" />
            </el-table>
          </div>
        </div>
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">队列汇总</div>
          </div>
          <div class="content-card-body">
            <el-table :data="result.namespaces" size="small" class="google-table">
              <el-table-column prop="namespace" label="队列" min-width="180" show-overflow-tooltip />
              <el-table-column prop="total_gpus" label="GPU卡数" width="100" />
              <el-table-column prop="pod_count" label="Pod数" width="90" />
              <el-table-column prop="total_gpu_hours" label="总卡时(h)" width="120" />
              <el-table-column prop="total_bottom" label="Bottom" width="120" />
            </el-table>
          </div>
        </div>
      </div>

      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">Pod Bottom 明细</div>
          <div class="content-card-extra">
            <el-tag type="info">{{ result.summary.start_time }} ~ {{ result.summary.end_time }}</el-tag>
            <el-tag type="success">{{ (result.summary.cluster_ids || []).join(', ') }}</el-tag>
          </div>
        </div>
        <div class="content-card-body">
          <el-table :data="result.pods" class="google-table" height="560">
            <el-table-column prop="namespace" label="队列" min-width="180" show-overflow-tooltip />
            <el-table-column prop="pod" label="Pod" min-width="260" show-overflow-tooltip />
            <el-table-column prop="gpu_count" label="GPU卡数" width="100" />
            <el-table-column prop="model" label="型号" width="120" />
            <el-table-column prop="avg_util_percent" label="平均利用率(%)" width="130" />
            <el-table-column prop="gpu_hours" label="卡时(h)" width="120" />
            <el-table-column prop="bottom" label="Bottom" width="120" />
          </el-table>
        </div>
      </div>
    </template>

    <div v-if="reportUrl" class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">报告预览</div>
        <div class="content-card-extra">
          <el-button @click="downloadReport('html')" :disabled="!latestTaskId">
            <el-icon><Download /></el-icon>
            下载 HTML
          </el-button>
          <el-button @click="downloadReport('excel')" :disabled="!latestTaskId">
            <el-icon><Download /></el-icon>
            下载 Excel
          </el-button>
          <el-button type="success" @click="openReport">
            <el-icon><Download /></el-icon>
            打开报告
          </el-button>
        </div>
      </div>
      <div class="content-card-body report-body">
        <iframe :src="reportUrl" class="report-frame" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { DataLine, Download, Search } from '@element-plus/icons-vue'
import { analyzeBottomCardTime, queryBottomCardTime } from '@/api/gpuMonitoring'
import { pollTaskStatus } from '@/utils/taskPoller'
import { getFullBackendUrl } from '@/utils/config'
import * as echarts from 'echarts'
import { getReportInfo } from '@/api/tasks'
import { loadConfig } from '@/api/config'

const now = new Date()
const twelveHoursAgo = new Date(now.getTime() - 12 * 3600 * 1000)

const clusterIdsText = ref('')
const dateRange = ref([twelveHoursAgo.toISOString(), now.toISOString()])
const step = ref('5m')
const targetModels = ref(['H800', 'L20', 'H20'])
const loading = ref(false)
const analyzing = ref(false)
const loadingConfig = ref(false)
const result = ref(null)
const reportUrl = ref('')
const latestTaskId = ref('')
const modelChartRef = ref(null)
const namespaceChartRef = ref(null)
const podChartRef = ref(null)

let modelChart = null
let namespaceChart = null
let podChart = null

const clusterIds = computed(() => clusterIdsText.value
  .split('\n')
  .map(line => line.trim())
  .filter(line => line && !line.startsWith('#'))
)

const buildPayload = () => ({
  cluster_ids: clusterIds.value,
  start_time: dateRange.value[0],
  end_time: dateRange.value[1],
  target_models: targetModels.value,
  step: step.value,
})

const loadClusterConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await loadConfig('analysis')
    const config = response.data?.config || response.config || {}
    const configuredClusterIds = config.cluster_ids
    if (!configuredClusterIds) {
      ElMessage.warning('系统配置中未找到默认集群ID')
      return
    }

    clusterIdsText.value = Array.isArray(configuredClusterIds)
      ? configuredClusterIds.join('\n')
      : String(configuredClusterIds).replace(/,/g, '\n')

    ElMessage.success(`已加载 ${clusterIds.value.length} 个集群ID`)
  } catch (error) {
    ElMessage.error('加载系统配置失败')
  } finally {
    loadingConfig.value = false
  }
}

const handlePreview = async () => {
  if (clusterIds.value.length === 0) {
    ElMessage.warning('请至少输入一个集群ID')
    return
  }
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('请选择完整的时间范围')
    return
  }

  loading.value = true
  try {
    const response = await queryBottomCardTime(buildPayload())

    if (!response.success) {
      throw new Error(response.error || response.message || '查询失败')
    }

    result.value = response.data
    ElMessage.success(`查询完成，共 ${response.data.summary.pod_count} 个 Bottom Pod`)
  } catch (error) {
    ElMessage.error(error.message || '查询 GPU 卡时数据失败')
  } finally {
    loading.value = false
  }
}

const handleAnalyze = async () => {
  if (clusterIds.value.length === 0) {
    ElMessage.warning('请至少输入一个集群ID')
    return
  }
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('请选择完整的时间范围')
    return
  }

  analyzing.value = true
  try {
    const response = await analyzeBottomCardTime(buildPayload())
    if (!response.success) {
      throw new Error(response.error || response.message || '分析任务创建失败')
    }

    const taskId = response.data?.task_id
    latestTaskId.value = taskId
    ElMessage.success('GPU bottom 卡时分析任务已创建')

    pollTaskStatus(
      taskId,
      () => {},
      (taskStatus) => {
        analyzing.value = false
        reportUrl.value = getFullBackendUrl(taskStatus.result_url)
        ElMessage.success('GPU bottom 卡时分析报告已生成')
      },
      (message) => {
        analyzing.value = false
        ElMessage.error(message || '分析失败')
      }
    )
  } catch (error) {
    analyzing.value = false
    ElMessage.error(error.message || '创建分析任务失败')
  }
}

const openReport = () => {
  if (reportUrl.value) {
    window.open(reportUrl.value, '_blank', 'noopener,noreferrer')
  }
}

const downloadReport = async (type) => {
  if (!latestTaskId.value) return
  try {
    const response = await getReportInfo('gpu_bottom', latestTaskId.value)
    const report = response.reports?.find(item => item.type === type)
    if (!report?.download_url) {
      ElMessage.warning(`未找到可下载的 ${type.toUpperCase()} 报告`)
      return
    }
    window.open(report.download_url, '_blank', 'noopener,noreferrer')
  } catch (error) {
    ElMessage.error('获取下载链接失败')
  }
}

const renderCharts = () => {
  if (!result.value) return

  if (!modelChart && modelChartRef.value) {
    modelChart = echarts.init(modelChartRef.value)
  }
  if (!namespaceChart && namespaceChartRef.value) {
    namespaceChart = echarts.init(namespaceChartRef.value)
  }
  if (!podChart && podChartRef.value) {
    podChart = echarts.init(podChartRef.value)
  }

  const modelData = result.value.model_summary || []
  const namespaceData = (result.value.namespaces || []).slice(0, 10)
  const podData = (result.value.pods || []).slice(0, 10)

  modelChart?.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>Bottom: {c} ({d}%)' },
    series: [
      {
        type: 'pie',
        radius: ['42%', '70%'],
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{c}' },
        data: modelData.map(item => ({ name: item.model, value: item.bottom }))
      }
    ]
  })

  namespaceChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '4%', right: '4%', bottom: '4%', top: 16, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: namespaceData.map(item => item.namespace),
      axisLabel: { width: 180, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 22,
        data: namespaceData.map(item => item.total_bottom),
        itemStyle: { color: '#3b82f6', borderRadius: [0, 6, 6, 0] }
      }
    ]
  })

  podChart?.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const idx = params?.[0]?.dataIndex ?? 0
        const item = podData[idx]
        if (!item) return ''
        return [
          `队列: ${item.namespace}`,
          `Pod: ${item.pod}`,
          `GPU卡数: ${item.gpu_count}`,
          `平均利用率: ${item.avg_util_percent}%`,
          `卡时: ${item.gpu_hours}h`,
          `${params[0].marker}Bottom: ${params[0].value}`
        ].join('<br/>')
      }
    },
    grid: { left: '4%', right: '4%', bottom: '4%', top: 16, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: podData.map(item => item.pod),
      axisLabel: { width: 260, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 20,
        data: podData.map(item => item.bottom),
        itemStyle: { color: '#10b981', borderRadius: [0, 6, 6, 0] }
      }
    ]
  })
}

watch(result, async (value) => {
  if (!value) return
  await nextTick()
  renderCharts()
})

const handleResize = () => {
  modelChart?.resize()
  namespaceChart?.resize()
  podChart?.resize()
}

window.addEventListener('resize', handleResize)

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  modelChart?.dispose()
  namespaceChart?.dispose()
  podChart?.dispose()
})
</script>

<style scoped>
.range-picker {
  width: 380px;
}

.cluster-input-wrap {
  width: 100%;
}

.input-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.cluster-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.cluster-textarea {
  width: 100%;
}

.cluster-count {
  margin: var(--space-3) 0 0;
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.small-select {
  width: 120px;
}

.model-select {
  width: 220px;
}

.stats-grid,
.summary-grid,
.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
}

.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-card-wide {
  grid-column: 1 / -1;
}

.stat-card .content-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.report-body {
  padding: 0;
}

.report-frame {
  width: 100%;
  min-height: 720px;
  border: none;
  background: #fff;
}

.chart-block {
  width: 100%;
  height: 320px;
}

.chart-block-lg {
  height: 420px;
}

@media (max-width: 960px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-card-wide {
    grid-column: auto;
  }
}
</style>
