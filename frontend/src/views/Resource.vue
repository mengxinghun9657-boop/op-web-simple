<template>
  <div class="resource-page page-container">

    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          资源分析引擎
        </div>
        <div class="page-subtitle">多集群 · 多维度 · 智能洞察，支持 40+ 核心指标与 AI 智能解读</div>
      </div>
      <div class="page-actions">
        <div class="header-stats">
          <span class="header-stat-item">
            <span class="header-stat-value">{{ clusterIds.length || '--' }}</span>
            <span class="header-stat-label">已配置集群</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 步骤引导 -->
    <div class="steps-bar content-card" style="margin-bottom: 20px;">
      <div v-for="(step, i) in steps" :key="i" :class="['step-node', { active: currentStep === i, done: currentStep > i }]">
        <div class="step-circle">
          <el-icon v-if="currentStep > i"><Check /></el-icon>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <span class="step-label">{{ step }}</span>
        <div v-if="i < steps.length - 1" class="step-line"></div>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="main-grid">

      <!-- 左侧：配置面板 -->
      <div class="config-panel">

        <!-- Step 1：数据源 -->
        <div :class="['panel-card', 'step-card', { 'step-active': currentStep >= 0 }]">
          <div class="panel-card-header">
            <div class="step-badge">01</div>
            <div class="panel-card-title">选择数据源</div>
          </div>
          <div class="panel-card-body">
            <div class="source-tabs">
              <button
                :class="['source-tab', dataSourceType === 'fetch' ? 'source-tab-active' : '']"
                @click="dataSourceType = 'fetch'"
              >
                <el-icon><Download /></el-icon>
                <span>在线获取</span>
              </button>
              <button
                :class="['source-tab', dataSourceType === 'upload' ? 'source-tab-active' : '']"
                @click="dataSourceType = 'upload'"
              >
                <el-icon><Upload /></el-icon>
                <span>上传文件</span>
              </button>
            </div>

            <!-- 在线获取 -->
            <div v-if="dataSourceType === 'fetch'" class="source-body">
              <div class="field-header">
                <span class="field-label"><el-icon><List /></el-icon> 集群 ID 列表</span>
                <el-button size="small" text type="primary" @click="loadResourceConfig" :loading="loadingConfig">
                  <el-icon><RefreshRight /></el-icon> 加载配置
                </el-button>
              </div>
              <div class="hint-strip">
                <el-icon><InfoFilled /></el-icon>
                <span>可在 <router-link to="/system-config?section=analysis" class="inline-link">系统配置</router-link> 中设置默认集群 ID</span>
              </div>
              <el-input
                v-model="clusterIdsText"
                type="textarea"
                :rows="5"
                placeholder="请输入集群 ID，每行一个"
                class="cluster-textarea"
              />
              <div class="field-footer">
                <span class="count-badge">{{ clusterIds.length }} 个集群</span>
              </div>

              <div class="fetch-actions">
                <el-button
                  type="primary"
                  class="btn-fetch"
                  :loading="fetchingData"
                  :disabled="clusterIds.length === 0"
                  @click="fetchClusterData"
                >
                  <el-icon><Download /></el-icon>
                  获取集群数据
                </el-button>
                <el-button
                  class="btn-export"
                  :disabled="!clusterDataFetched"
                  @click="exportClusterData"
                >
                  <el-icon><Share /></el-icon>
                  导出 JSON
                </el-button>
                <el-button class="btn-test" text @click="testConnection">
                  <el-icon><Connection /></el-icon>
                  测试连接
                </el-button>
              </div>

              <!-- 获取进度 -->
              <div v-if="fetchingData" class="fetch-progress">
                <div class="fetch-progress-header">
                  <span class="fetch-progress-label">{{ fetchStatusMsg }}</span>
                  <span class="fetch-progress-pct">{{ fetchProgress }}%</span>
                </div>
                <div class="fetch-progress-track">
                  <div class="fetch-progress-fill" :style="{ width: fetchProgress + '%' }"></div>
                </div>
              </div>

              <!-- 成功状态 -->
              <div v-if="clusterDataFetched && !fetchingData" class="fetch-success">
                <el-icon><CircleCheck /></el-icon>
                <span>已获取 {{ clusterIds.length }} 个集群数据</span>
              </div>
            </div>

            <!-- 上传文件 -->
            <div v-if="dataSourceType === 'upload'" class="source-body">
              <div class="upload-zone" @click="triggerUpload">
                <el-icon class="upload-zone-icon"><FolderOpened /></el-icon>
                <p class="upload-zone-title">{{ multiclusterFileName || '点击上传 Multi-Cluster 数据' }}</p>
                <p class="upload-zone-hint">支持 JSON / YAML 格式</p>
                <FileUpload accept=".json,.yaml,.yml" @file-selected="handleMulticlusterSelect" button-text="选择文件" />
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2：Excel 数据源 -->
        <div :class="['panel-card', 'step-card', { 'step-active': currentStep >= 1 }]">
          <div class="panel-card-header">
            <div class="step-badge">02</div>
            <div class="panel-card-title">Excel 数据源 <span class="optional-tag">可选</span></div>
          </div>
          <div class="panel-card-body">
            <p class="panel-card-desc">补充存储 / 网络 / 实例（BCC/GPU）数据，增强分析深度</p>
            <div class="excel-upload-row">
              <div :class="['excel-file-display', excelFileName ? 'has-file' : '']">
                <el-icon><Document /></el-icon>
                <span>{{ excelFileName || '未选择文件' }}</span>
              </div>
              <FileUpload accept=".xlsx,.xls" @file-selected="handleExcelSelect" button-text="选择文件" />
            </div>
            <div class="excel-sheets">
              <span class="sheet-tag"><el-icon><Grid /></el-icon>存储</span>
              <span class="sheet-tag"><el-icon><Connection /></el-icon>网络</span>
              <span class="sheet-tag"><el-icon><Cpu /></el-icon>实例 (BCC/GPU)</span>
            </div>
          </div>
        </div>

        <!-- Step 3：开始分析 -->
        <div :class="['panel-card', 'step-card', { 'step-active': currentStep >= 2 }]">
          <div class="panel-card-header">
            <div class="step-badge">03</div>
            <div class="panel-card-title">生成分析报告</div>
          </div>
          <div class="panel-card-body">
            <div v-if="!canAnalyze" class="analyze-block-hint">
              <el-icon><Warning /></el-icon>
              <span>{{ analyzeErrorMsg }}</span>
            </div>
            <el-button
              type="primary"
              size="large"
              style="width: 100%; height: 48px; font-size: var(--text-base); font-weight: var(--font-semibold);"
              :disabled="!canAnalyze || analyzing"
              :loading="analyzing"
              @click="startAnalysis"
            >
              <el-icon v-if="!analyzing"><TrendCharts /></el-icon>
              {{ analyzing ? '分析中，请稍候...' : '开始分析并生成报告' }}
            </el-button>

            <!-- 分析进度 -->
            <div v-if="analyzing" class="analyze-progress">
              <div class="analyze-progress-header">
                <span>{{ statusMessage }}</span>
                <span>{{ analyzeProgress }}%</span>
              </div>
              <div class="analyze-progress-track">
                <div class="analyze-progress-fill" :style="{ width: analyzeProgress + '%' }">
                  <div class="analyze-progress-glow"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- 右侧：功能说明 + 报告区 -->
      <div class="result-panel">

        <!-- 功能亮点（无报告时显示） -->
        <div v-if="!analysisResult && !analyzing" class="feature-panel">
          <div class="feature-panel-title">分析能力概览</div>
          <div class="feature-list">
            <div v-for="f in features" :key="f.label" class="feature-row">
              <div :class="['feature-dot', f.color]"></div>
              <div class="feature-text">
                <span class="feature-label">{{ f.label }}</span>
                <span class="feature-desc">{{ f.desc }}</span>
              </div>
            </div>
          </div>
          <div class="empty-hint">
            <el-icon><DataAnalysis /></el-icon>
            <span>完成左侧配置后点击"开始分析"</span>
          </div>
        </div>

        <!-- 分析中骨架 -->
        <div v-if="analyzing && !analysisResult" class="analyzing-panel">
          <div class="analyzing-icon-wrap">
            <div class="analyzing-ring"></div>
            <el-icon class="analyzing-icon"><TrendCharts /></el-icon>
          </div>
          <p class="analyzing-title">AI 正在解读报告</p>
          <p class="analyzing-desc">{{ statusMessage }}</p>
          <div class="analyzing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>

        <!-- 报告展示 -->
        <div v-if="analysisResult && !analyzing" class="report-panel">
          <div class="report-panel-header">
            <div class="report-panel-title">
              <el-icon class="report-done-icon"><CircleCheck /></el-icon>
              分析报告已生成
            </div>
            <div class="report-panel-actions">
              <el-button size="small" type="primary" plain @click="downloadReport">
                <el-icon><Download /></el-icon> 下载
              </el-button>
              <el-button size="small" @click="openReport">
                <el-icon><FullScreen /></el-icon> 全屏
              </el-button>
            </div>
          </div>
          <div class="report-iframe-wrap">
            <div v-if="reportLoading" class="report-loading">
              <el-icon class="spin-icon"><Loading /></el-icon>
            </div>
            <iframe
              v-if="reportUrl"
              :src="reportUrl"
              class="report-iframe"
              @load="reportLoading = false"
            />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Cpu, DataAnalysis, TrendCharts, Download, Upload, List, FullScreen,
  Connection, FolderOpened, Document, Check, InfoFilled,
  RefreshRight, CircleCheck, Share, Grid, Warning
} from '@element-plus/icons-vue'
import FileUpload from '@/components/common/FileUpload.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import axios from '@/utils/axios'
import { getFullBackendUrl } from '@/utils/config'

const route = useRoute()
const router = useRouter()

const steps = ['选择数据源', '补充 Excel', '生成报告']
const features = [
  { label: 'Multi-Cluster 数据', desc: '支持在线获取或上传 JSON/YAML', color: 'dot-blue' },
  { label: 'Excel 多工作表', desc: '存储 / 网络 / 实例（BCC/GPU）', color: 'dot-green' },
  { label: 'GPU 分类分析', desc: 'L20 / H20 / H800 + 普通 BCC', color: 'dot-purple' },
  { label: '40+ 核心指标', desc: '全维度资源使用率洞察', color: 'dot-orange' },
  { label: 'AI 智能解读', desc: '自动生成文字报告摘要', color: 'dot-cyan' },
]

const dataSourceType = ref('fetch')
const clusterIdsText = ref('')
const fetchingData = ref(false)
const fetchProgress = ref(0)
const fetchStatusMsg = ref('')
const clusterDataFetched = ref(false)
const clusterDataTaskId = ref(null)
const multiclusterFile = ref(null)
const multiclusterFileName = ref('')
const excelFile = ref(null)
const excelFileName = ref('')
const analyzing = ref(false)
const analyzeProgress = ref(0)
const statusMessage = ref('准备就绪')
const taskId = ref(null)
const analysisResult = ref(null)
const reportLoading = ref(false)
const loadingConfig = ref(false)

let pollTaskTimer = null
let pollResultTimer = null

const clusterIds = computed(() => clusterIdsText.value.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#')))
const canAnalyze = computed(() => dataSourceType.value === 'fetch' ? clusterDataFetched.value : !!multiclusterFile.value)
const analyzeErrorMsg = computed(() => {
  if (dataSourceType.value === 'fetch' && !clusterDataFetched.value)
    return clusterIds.value.length === 0 ? '请输入集群 ID 后获取集群数据' : '请先点击"获取集群数据"按钮'
  if (dataSourceType.value === 'upload' && !multiclusterFile.value) return '请上传 Multi-Cluster 数据 JSON 文件'
  return ''
})
const currentStep = computed(() => {
  if (analysisResult.value) return 3
  if (canAnalyze.value) return 2
  if (dataSourceType.value === 'upload' && multiclusterFile.value) return 1
  if (clusterIdsText.value.trim()) return 1
  return 0
})

onMounted(() => {
  const taskIdFromUrl = route.query.taskId
  if (taskIdFromUrl) {
    taskId.value = taskIdFromUrl
    analyzing.value = true
    analyzeProgress.value = 0
    statusMessage.value = '正在恢复任务状态...'
    pollResult(taskIdFromUrl).then(() => { ElMessage.success('任务已完成') }).catch(() => {
      ElMessage.error('任务恢复失败，请重新分析'); analyzing.value = false
    })
  }
  const savedTaskId = localStorage.getItem('resource_cluster_task_id')
  const savedFetched = localStorage.getItem('resource_cluster_fetched')
  const savedClusterIds = localStorage.getItem('resource_cluster_ids')
  if (savedTaskId && savedFetched === 'true') {
    clusterDataTaskId.value = savedTaskId
    clusterDataFetched.value = true
    if (savedClusterIds) clusterIdsText.value = savedClusterIds
  }
  loadResourceConfig()
})

const fetchClusterData = async () => {
  if (clusterIds.value.length === 0) { ElMessage.warning('请先输入集群 ID'); return }
  fetchingData.value = true; fetchProgress.value = 0; fetchStatusMsg.value = '正在启动批量采集任务...'; clusterDataFetched.value = false
  try {
    const response = await axios.post('/api/v1/prometheus/cluster/metrics/batch', { cluster_ids: clusterIds.value })
    const data = response.data || response
    clusterDataTaskId.value = data.task_id; fetchStatusMsg.value = `任务已启动 (${data.task_id})`; fetchProgress.value = 5
    await pollTaskStatus(data.task_id)
  } catch (error) { fetchingData.value = false; ElMessage.error('启动采集任务失败: ' + (error.response?.data?.detail || error.message)) }
}

const pollTaskStatus = async (id) => {
  if (pollTaskTimer) { clearInterval(pollTaskTimer); pollTaskTimer = null }
  pollTaskTimer = setInterval(async () => {
    try {
      const response = await axios.get(`/api/v1/prometheus/cluster/task/${id}`)
      if (response.progress !== undefined) fetchProgress.value = response.progress
      fetchStatusMsg.value = response.message || '处理中...'
      if (response.status === 'completed') {
        clearInterval(pollTaskTimer); pollTaskTimer = null; fetchProgress.value = 100
        fetchStatusMsg.value = '数据获取完成'; clusterDataFetched.value = true
        localStorage.setItem('resource_cluster_task_id', id)
        localStorage.setItem('resource_cluster_fetched', 'true')
        localStorage.setItem('resource_cluster_ids', clusterIdsText.value)
        ElMessage.success(`成功获取 ${response.completed_clusters} 个集群的监控数据`)
        setTimeout(() => { fetchingData.value = false }, 1000)
      } else if (response.status === 'failed') {
        clearInterval(pollTaskTimer); pollTaskTimer = null; fetchingData.value = false
        ElMessage.error(`采集失败: ${response.error || '未知错误'}`)
      }
    } catch (error) { clearInterval(pollTaskTimer); pollTaskTimer = null; fetchingData.value = false; ElMessage.error('查询任务状态失败') }
  }, 2000)
}

const exportClusterData = async () => {
  if (!clusterDataFetched.value || !clusterDataTaskId.value) { ElMessage.warning('请先获取集群数据'); return }
  try {
    const response = await axios.post('/api/v1/prometheus/cluster/export', { task_id: clusterDataTaskId.value, cluster_ids: clusterIds.value })
    if (response.success && response.file) {
      const link = document.createElement('a'); link.href = getFullBackendUrl(`/api/v1/prometheus/cluster/download/${response.file}`); link.download = response.file
      document.body.appendChild(link); link.click(); document.body.removeChild(link); ElMessage.success(`数据已导出: ${response.file}`)
    }
  } catch (error) { ElMessage.error('导出失败: ' + (error.response?.data?.detail || error.message)) }
}

const testConnection = async () => {
  try { const res = await axios.post('/api/v1/prometheus/config/test'); ElMessage.success(res.message || '连接测试成功') }
  catch { ElMessage.error('连接测试失败，请检查 Prometheus 配置') }
}
const handleMulticlusterSelect = (file) => { multiclusterFile.value = file; multiclusterFileName.value = file.name; ElMessage.success(`已选择: ${file.name}`) }
const handleExcelSelect = (file) => { excelFile.value = file; excelFileName.value = file.name }
const triggerUpload = () => {}

const loadResourceConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await axios.get('/api/v1/config/load?module=prometheus_runtime')
    const ids = response.config?.cluster_ids || response.data?.config?.cluster_ids
    if (ids && ids.length > 0) {
      const arr = Array.isArray(ids) ? ids : ids.split(',').map(id => id.trim()).filter(id => id)
      if (arr.length > 0) { clusterIdsText.value = arr.join('\n'); ElMessage.success(`已加载 ${arr.length} 个集群 ID`) }
      else ElMessage.warning('配置的集群 ID 列表为空')
    } else {
      ElMessage.warning('未找到配置的集群 ID，请先在系统配置中添加')
    }
  } catch (error) { ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message)) }
  finally { loadingConfig.value = false }
}

const startAnalysis = async () => {
  if (!canAnalyze.value) { ElMessage.warning('请先完成数据准备'); return }
  analyzing.value = true; analyzeProgress.value = 0; statusMessage.value = '正在准备数据...'
  const progressTimer = setInterval(() => { if (analyzeProgress.value < 90) analyzeProgress.value += 5 }, 500)
  try {
    let requestData = {}
    if (dataSourceType.value === 'fetch') {
      requestData.task_id = clusterDataTaskId.value
      if (excelFile.value) {
        const formData = new FormData(); formData.append('file', excelFile.value)
        const uploadRes = await axios.post('/api/v1/resource/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
        requestData.excel_file_name = uploadRes.data?.filename || uploadRes.filename
      }
    } else {
      const formData = new FormData(); formData.append('file', multiclusterFile.value)
      const uploadRes = await axios.post('/api/v1/resource/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      requestData.multicluster_file_name = uploadRes.data?.filename || uploadRes.filename
      if (excelFile.value) {
        const excelFormData = new FormData(); excelFormData.append('file', excelFile.value)
        const excelUploadRes = await axios.post('/api/v1/resource/upload', excelFormData, { headers: { 'Content-Type': 'multipart/form-data' } })
        requestData.excel_file_name = excelUploadRes.data?.filename || excelUploadRes.filename
      }
    }
    const analysisRes = await axios.post('/api/v1/resource/analyze', requestData)
    taskId.value = analysisRes.data?.task_id || analysisRes.task_id
    statusMessage.value = '正在分析数据...'
    router.replace({ query: { ...route.query, taskId: taskId.value } })
    await pollResult(taskId.value); clearInterval(progressTimer); analyzeProgress.value = 100; ElMessage.success('资源分析报告生成完成')
  } catch (error) { clearInterval(progressTimer); ElMessage.error('分析失败: ' + (error.response?.data?.detail || error.message)) }
  finally { analyzing.value = false }
}

const pollResult = async (id) => {
  return new Promise((resolve, reject) => {
    if (pollResultTimer) { clearInterval(pollResultTimer); pollResultTimer = null }
    pollResultTimer = setInterval(async () => {
      try {
        const res = await axios.get(`/api/v1/resource/result/${id}`)
        if (res.status === 'processing') {
          statusMessage.value = res.message || '正在分析中...'
          if (res.progress) analyzeProgress.value = Math.min(res.progress, 95)
          return
        }
        if (res.success === true || (res.result && res.result.html_report)) {
          clearInterval(pollResultTimer); pollResultTimer = null
          analysisResult.value = res; reportLoading.value = true; statusMessage.value = '分析完成'; resolve()
        } else if (res.success === false && res.status === 'failed') {
          clearInterval(pollResultTimer); pollResultTimer = null; reject(new Error(res.error || '分析失败'))
        }
      } catch (error) {
        if (error.response?.status === 404) { statusMessage.value = '正在初始化任务...'; return }
        clearInterval(pollResultTimer); pollResultTimer = null; reject(error)
      }
    }, 2000)
  })
}

const reportUrl = computed(() => {
  const htmlFile = analysisResult.value?.html_file || analysisResult.value?.result?.html_report
  return htmlFile ? getFullBackendUrl(htmlFile) : null
})
const downloadReport = () => {
  if (!taskId.value) { ElMessage.warning('没有可下载的报告'); return }
  const link = document.createElement('a'); link.href = getFullBackendUrl(`/api/v1/resource/download/${taskId.value}`); link.download = `resource_report_${taskId.value}.html`
  document.body.appendChild(link); link.click(); document.body.removeChild(link); ElMessage.success('报告下载已开始')
}
const openReport = () => { if (reportUrl.value) window.open(reportUrl.value, '_blank'); else ElMessage.warning('报告不可用') }

onUnmounted(() => {
  if (pollTaskTimer) { clearInterval(pollTaskTimer); pollTaskTimer = null }
  if (pollResultTimer) { clearInterval(pollResultTimer); pollResultTimer = null }
})
</script>

<style scoped>
/* ======== 页面容器 ======== */
.resource-page {
  min-height: 100vh;
  padding-bottom: 48px;
}

/* ======== 页头统计 ======== */
.header-stats {
  display: flex;
  gap: 16px;
}
.header-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.header-stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--primary);
  line-height: 1;
}
.header-stat-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* ======== 步骤条 ======== */
.steps-bar {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  gap: 0;
}
.step-node {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}
.step-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-tertiary);
  background: var(--bg-primary);
  transition: all 0.3s;
  flex-shrink: 0;
}
.step-node.active .step-circle {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-bg);
  box-shadow: 0 0 0 3px var(--primary-light);
}
.step-node.done .step-circle {
  border-color: var(--color-success);
  background: var(--color-success);
  color: var(--text-inverse);
}
.step-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  white-space: nowrap;
  transition: color 0.3s;
}
.step-node.active .step-label { color: var(--primary); font-weight: var(--font-semibold); }
.step-node.done .step-label { color: var(--color-success); }
.step-line {
  width: 48px;
  height: 2px;
  background: var(--border-color);
  margin: 0 12px;
  border-radius: 1px;
}

/* ======== 主体网格 ======== */
.main-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  align-items: start;
}

/* ======== 通用卡片 ======== */
.panel-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.panel-card.step-active {
  border-color: var(--color-primary-300);
  box-shadow: 0 0 0 1px var(--color-primary-100), 0 4px 16px rgba(0,0,0,0.06);
}
.panel-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}
.step-badge {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--primary);
  color: var(--text-inverse);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
.panel-card-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.optional-tag {
  font-size: var(--text-xs);
  font-weight: var(--font-normal);
  color: var(--text-tertiary);
  background: var(--bg-tertiary, rgba(0,0,0,0.06));
  padding: 1px 6px;
  border-radius: 4px;
}
.panel-card-body {
  padding: 16px;
}
.panel-card-desc {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0 0 12px;
}

/* ======== 数据源 Tab ======== */
.source-tabs {
  display: flex;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 3px;
  gap: 3px;
  margin-bottom: 14px;
}
.source-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 12px;
  border: none;
  border-radius: 6px;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
}
.source-tab:hover { color: var(--text-primary); }
.source-tab-active {
  background: var(--bg-primary);
  color: var(--primary);
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.source-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ======== 字段 ======== */
.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.field-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}
.hint-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  background: var(--primary-bg);
  border: 1px solid var(--color-primary-200);
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.inline-link {
  color: var(--primary);
  font-weight: var(--font-semibold);
  text-decoration: none;
}
.inline-link:hover { text-decoration: underline; }
.cluster-textarea :deep(.el-textarea__inner) {
  font-family: 'Menlo', 'Monaco', monospace;
  font-size: var(--text-sm);
  background: var(--bg-secondary);
  border-color: var(--border-color);
  border-radius: 8px;
  resize: vertical;
}
.field-footer {
  display: flex;
  justify-content: flex-end;
}
.count-badge {
  font-size: var(--text-xs);
  color: var(--primary);
  background: var(--primary-bg);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: var(--font-semibold);
}

/* ======== 获取按钮组 ======== */
.fetch-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn-fetch {
  flex: 1;
  min-width: 120px;
}
.btn-export { flex: 1; min-width: 100px; }

/* ======== 获取进度 ======== */
.fetch-progress {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
}
.fetch-progress-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.fetch-progress-pct { font-weight: var(--font-semibold); color: var(--primary); }
.fetch-progress-track {
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}
.fetch-progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* ======== 成功状态 ======== */
.fetch-success {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
  border-radius: 8px;
  font-size: var(--text-sm);
  color: var(--color-success-dark);
  font-weight: var(--font-medium);
}

/* ======== 上传区 ======== */
.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: 10px;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
  position: relative;
  overflow: hidden;
}
.upload-zone:hover { border-color: var(--primary); }
.upload-zone-icon { font-size: 36px; color: var(--primary); margin-bottom: 8px; }
.upload-zone-title { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 4px; }
.upload-zone-hint { font-size: var(--text-xs); color: var(--text-tertiary); margin: 0 0 12px; }

/* ======== Excel ======== */
.excel-upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.excel-file-display {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  min-width: 0;
  overflow: hidden;
}
.excel-file-display span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.excel-file-display.has-file { color: var(--color-success-dark); border-color: var(--color-success-border); }
.excel-sheets {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.sheet-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 3px 8px;
  border-radius: 5px;
}

/* ======== 分析提示 ======== */
.analyze-block-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--color-warning-dark);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: 7px;
  padding: 8px 10px;
  margin-bottom: 12px;
}

/* ======== 分析进度 ======== */
.analyze-progress {
  margin-top: 14px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.analyze-progress-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.analyze-progress-track {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}
.analyze-progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 3px;
  transition: width 0.5s ease;
  position: relative;
}
.analyze-progress-glow {
  position: absolute;
  right: 0;
  top: -2px;
  width: 12px;
  height: 10px;
  background: var(--bg-primary);
  border-radius: 50%;
  opacity: 0.6;
  filter: blur(3px);
  animation: glow-pulse 1s ease-in-out infinite;
}
@keyframes glow-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* ======== 右侧结果面板 ======== */
.result-panel {
  min-height: 500px;
}

/* 功能亮点 */
.feature-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}
.feature-panel-title {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 16px;
}
.feature-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.feature-row { display: flex; align-items: flex-start; gap: 12px; }
.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}
.dot-blue { background: var(--primary); }
.dot-green { background: var(--color-success); }
.dot-purple { background: var(--color-primary-700); }
.dot-orange { background: var(--color-warning); }
.dot-cyan { background: var(--color-info); }
.feature-text { display: flex; flex-direction: column; gap: 2px; }
.feature-label { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-primary); }
.feature-desc { font-size: var(--text-sm); color: var(--text-tertiary); }
.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  border: 1px dashed var(--border-color);
}

/* 分析中状态 */
.analyzing-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 40px;
}
.analyzing-icon-wrap {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 24px;
}
.analyzing-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: var(--primary);
  animation: spin 1.5s linear infinite;
}
.analyzing-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--primary);
  margin: auto;
  top: 0; left: 0; right: 0; bottom: 0;
}
.analyzing-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0 0 8px;
}
.analyzing-desc {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0 0 20px;
}
.analyzing-dots {
  display: flex;
  gap: 6px;
}
.analyzing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary);
  animation: dot-bounce 1.2s ease-in-out infinite;
}
.analyzing-dots span:nth-child(2) { animation-delay: 0.2s; }
.analyzing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* 报告面板 */
.report-panel {
  background: var(--bg-primary);
  border: 1px solid var(--color-success-border);
  border-radius: 12px;
  overflow: hidden;
}
.report-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}
.report-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}
.report-done-icon { color: var(--color-success); font-size: var(--text-lg); }
.report-panel-actions { display: flex; gap: 8px; }
.report-iframe-wrap {
  position: relative;
  min-height: 600px;
}
.report-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.9);
  z-index: 10;
}
.report-iframe {
  width: 100%;
  min-height: 600px;
  border: none;
  display: block;
  background: white;
}

/* ======== 动画 ======== */
.spin-icon { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ======== 响应式 ======== */
@media (max-width: 900px) {
  .main-grid { grid-template-columns: 1fr; }
  .steps-bar { padding: 12px 16px; }
  .step-line { width: 24px; margin: 0 6px; }
}
</style>
