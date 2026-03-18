<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Cpu /></el-icon>
          </div>
          资源分析配置
        </div>
        <div class="page-subtitle">配置数据源并生成集群资源分析报告</div>
      </div>
    </div>

    <!-- 数据源配置 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Setting /></el-icon>
          Multi-Cluster数据源配置
        </div>
      </div>
      <div class="content-card-body">
        <!-- 数据源选择 -->
        <div class="source-selector">
          <div :class="['source-option', dataSourceType === 'fetch' ? 'source-option-active' : '']" @click="dataSourceType = 'fetch'">
            <el-icon class="source-icon"><Download /></el-icon>
            <div class="source-info"><div class="source-title">在线获取</div><div class="source-desc">通过集群ID列表获取数据</div></div>
          </div>
          <div :class="['source-option', dataSourceType === 'upload' ? 'source-option-active' : '']" @click="dataSourceType = 'upload'">
            <el-icon class="source-icon"><Upload /></el-icon>
            <div class="source-info"><div class="source-title">上传文件</div><div class="source-desc">选择本地JSON/YAML文件</div></div>
          </div>
        </div>

        <!-- 在线获取 -->
        <div v-if="dataSourceType === 'fetch'" class="source-content">
          <div class="input-section">
            <div class="input-label-row">
              <label class="input-label"><el-icon><List /></el-icon>集群ID列表（每行一个）</label>
              <el-button size="small" @click="loadResourceConfig" :loading="loadingConfig">
                <el-icon><Download /></el-icon>
                加载配置
              </el-button>
            </div>
            <div class="config-hint-box">
              <el-icon><InfoFilled /></el-icon>
              <span>提示：您可以在 <router-link to="/system-config?section=analysis" class="config-link">系统配置</router-link> 中设置默认集群ID</span>
            </div>
            <el-input v-model="clusterIdsText" type="textarea" :rows="6" placeholder="请输入集群ID列表，每行一个" />
            <p class="input-hint">当前已输入 {{ clusterIds.length }} 个集群ID</p>
          </div>
          <div class="action-grid">
            <el-button type="primary" @click="fetchClusterData" :loading="fetchingData" :disabled="clusterIds.length === 0">
              <el-icon><Download /></el-icon>获取集群数据
            </el-button>
            <el-button type="success" @click="exportClusterData" :disabled="!clusterDataFetched">
              <el-icon><Download /></el-icon>导出JSON
            </el-button>
            <el-button @click="showCookieDialog = true"><el-icon><Setting /></el-icon>Cookie配置</el-button>
            <el-button @click="testConnection"><el-icon><Connection /></el-icon>测试连接</el-button>
          </div>
          <div v-if="fetchingData" class="progress-section">
            <el-progress :percentage="fetchProgress" :stroke-width="12" />
            <p class="progress-text">{{ fetchStatusMsg }}</p>
          </div>
          <div v-if="clusterDataFetched" class="success-section">
            <el-icon><SuccessFilled /></el-icon>
            <span>集群数据已获取，共 {{ clusterIds.length }} 个集群</span>
          </div>
        </div>

        <!-- 上传JSON文件 -->
        <div v-if="dataSourceType === 'upload'" class="source-content">
          <div class="upload-section">
            <el-icon class="upload-icon"><FolderOpened /></el-icon>
            <p class="upload-title">上传Multi-Cluster数据文件</p>
            <p class="upload-hint">支持JSON/YAML格式</p>
            <div class="upload-input">
              <el-input v-model="multiclusterFileName" placeholder="未选择文件" readonly>
                <template #prefix><el-icon><Document /></el-icon></template>
              </el-input>
              <FileUpload accept=".json,.yaml,.yml" @file-selected="handleMulticlusterSelect" button-text="选择文件" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Excel数据源 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Document /></el-icon>
          Excel数据源（可选）
        </div>
      </div>
      <div class="content-card-body">
        <div class="upload-input">
          <el-input v-model="excelFileName" placeholder="未选择文件（可选）" readonly>
            <template #prefix><el-icon><Document /></el-icon></template>
          </el-input>
          <FileUpload accept=".xlsx,.xls" @file-selected="handleExcelSelect" button-text="选择文件" />
        </div>
        <p class="input-hint">Excel工作表：存储 | 网络 | 实例（BCC/GPU）</p>
      </div>
    </div>

    <!-- 功能说明 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><InfoFilled /></el-icon>
          功能说明
        </div>
      </div>
      <div class="content-card-body">
        <div class="feature-grid">
          <div class="feature-item"><el-icon class="feature-icon feature-icon-primary"><Check /></el-icon><span>Multi-Cluster数据：支持在线获取或上传JSON/YAML</span></div>
          <div class="feature-item"><el-icon class="feature-icon feature-icon-success"><Check /></el-icon><span>Excel数据：存储/网络/实例工作表</span></div>
          <div class="feature-item"><el-icon class="feature-icon feature-icon-info"><Check /></el-icon><span>BCC分类：L20/H20/H800显卡 + 普通BCC</span></div>
          <div class="feature-item"><el-icon class="feature-icon feature-icon-warning"><Check /></el-icon><span>多维度分析：40+关键指标</span></div>
        </div>
      </div>
    </div>

    <!-- 分析按钮 -->
    <el-button type="primary" size="large" class="analyze-button" :loading="analyzing" :disabled="!canAnalyze" @click="startAnalysis">
      <el-icon><TrendCharts /></el-icon>{{ analyzing ? '分析中...' : '开始分析并生成报告' }}
    </el-button>
    <div v-if="!canAnalyze" class="error-hint"><p>{{ analyzeErrorMsg }}</p></div>

    <!-- 分析进度 -->
    <div v-if="analyzing" class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon class="spin-icon"><Loading /></el-icon>
          分析进度
        </div>
      </div>
      <div class="content-card-body">
        <ProgressBar :percentage="analyzeProgress" />
        <p class="progress-text">{{ statusMessage }}</p>
      </div>
    </div>

    <!-- 分析结果 -->
    <div v-if="analysisResult && !analyzing" class="content-card" style="grid-column: span 2;">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon class="success-icon"><SuccessFilled /></el-icon>
          分析完成
        </div>
        <div class="content-card-extra">
          <el-button type="primary" @click="downloadReport"><el-icon><Download /></el-icon>下载报告</el-button>
          <el-button @click="openReport"><el-icon><FullScreen /></el-icon>全屏查看</el-button>
        </div>
      </div>
      <div class="content-card-body report-body">
        <div v-if="reportLoading" class="report-loading"><el-icon class="spin-icon"><Loading /></el-icon></div>
        <iframe v-if="reportUrl" :src="reportUrl" class="report-frame" @load="reportLoading = false" />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!analyzing && !analysisResult" class="empty-state">
      <div class="empty-state-icon">
        <el-icon><DataAnalysis /></el-icon>
      </div>
      <div class="empty-state-title">请选择或获取Multi-Cluster数据开始分析</div>
    </div>

    <!-- Cookie配置对话框 -->
    <el-dialog v-model="showCookieDialog" title="Cookie配置" width="600px" class="google-dialog" append-to-body>
      <el-form class="google-form">
        <el-form-item label="Cookie值" label-width="80px">
          <el-input v-model="cookieValue" type="textarea" :rows="6" placeholder="粘贴从浏览器复制的Cookie值" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCookieDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCookie">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>


<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cpu, DataAnalysis, TrendCharts, Download, Upload, List, FullScreen, SuccessFilled, Loading, Setting, Connection, FolderOpened, Document, Check, InfoFilled } from '@element-plus/icons-vue'
import FileUpload from '@/components/common/FileUpload.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import axios from '@/utils/axios'
import { getFullBackendUrl } from '@/utils/config'

const route = useRoute()
const router = useRouter()

const dataSourceType = ref('fetch')
const clusterIdsText = ref('')
const fetchingData = ref(false)
const fetchProgress = ref(0)
const fetchStatusMsg = ref('')
const clusterDataFetched = ref(false)
const clusterDataTaskId = ref(null)
const showCookieDialog = ref(false)
const cookieValue = ref('')
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

// 定时器引用，用于清理
let pollTaskTimer = null
let pollResultTimer = null

const clusterIds = computed(() => clusterIdsText.value.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#')))
const canAnalyze = computed(() => dataSourceType.value === 'fetch' ? clusterDataFetched.value : !!multiclusterFile.value)
const analyzeErrorMsg = computed(() => {
  if (dataSourceType.value === 'fetch' && !clusterDataFetched.value) return clusterIds.value.length === 0 ? '请输入集群ID后获取集群数据' : '请先点击"获取集群数据"按钮'
  if (dataSourceType.value === 'upload' && !multiclusterFile.value) return '请上传Multi-Cluster数据JSON文件'
  return ''
})

// 页面加载时恢复状态
onMounted(() => {
  // 优先从 URL 参数恢复分析任务状态
  const taskIdFromUrl = route.query.taskId
  
  if (taskIdFromUrl) {
    // 恢复分析任务状态
    taskId.value = taskIdFromUrl
    analyzing.value = true
    analyzeProgress.value = 0
    statusMessage.value = '正在恢复任务状态...'
    
    // 开始轮询结果
    pollResult(taskIdFromUrl).then(() => {
      ElMessage.success('任务已完成')
    }).catch(() => {
      ElMessage.error('任务恢复失败，请重新分析')
      analyzing.value = false
    })
  }
  
  // 恢复集群数据获取状态
  const savedTaskId = localStorage.getItem('resource_cluster_task_id')
  const savedFetched = localStorage.getItem('resource_cluster_fetched')
  const savedClusterIds = localStorage.getItem('resource_cluster_ids')
  
  if (savedTaskId && savedFetched === 'true') {
    clusterDataTaskId.value = savedTaskId
    clusterDataFetched.value = true
    if (savedClusterIds) {
      clusterIdsText.value = savedClusterIds
    }
  }
  
  // 自动加载配置
  loadResourceConfig()
})

const fetchClusterData = async () => {
  if (clusterIds.value.length === 0) { ElMessage.warning('请先输入集群ID'); return }
  fetchingData.value = true; fetchProgress.value = 0; fetchStatusMsg.value = '正在启动批量采集任务...'; clusterDataFetched.value = false
  try {
    const response = await axios.post('/api/v1/prometheus/cluster/metrics/batch', { cluster_ids: clusterIds.value })
    const data = response.data || response
    clusterDataTaskId.value = data.task_id; fetchStatusMsg.value = `任务已启动 (ID: ${data.task_id})`; fetchProgress.value = 5
    await pollTaskStatus(data.task_id)
  } catch (error) { fetchingData.value = false; ElMessage.error('启动采集任务失败: ' + (error.response?.data?.detail || error.message)) }
}

const pollTaskStatus = async (taskId) => {
  // 清理旧的定时器
  if (pollTaskTimer) {
    clearInterval(pollTaskTimer)
    pollTaskTimer = null
  }
  
  pollTaskTimer = setInterval(async () => {
    try {
      const response = await axios.get(`/api/v1/prometheus/cluster/task/${taskId}`)
      if (response.progress !== undefined) fetchProgress.value = response.progress
      fetchStatusMsg.value = response.message || '处理中...'
      if (response.status === 'completed') {
        clearInterval(pollTaskTimer)
        pollTaskTimer = null
        fetchProgress.value = 100
        fetchStatusMsg.value = '数据获取完成'
        clusterDataFetched.value = true
        
        // 保存状态到 localStorage
        localStorage.setItem('resource_cluster_task_id', taskId)
        localStorage.setItem('resource_cluster_fetched', 'true')
        localStorage.setItem('resource_cluster_ids', clusterIdsText.value)
        
        ElMessage.success(`成功获取 ${response.completed_clusters} 个集群的监控数据`)
        setTimeout(() => { fetchingData.value = false }, 1000)
      } else if (response.status === 'failed') {
        clearInterval(pollTaskTimer)
        pollTaskTimer = null
        fetchingData.value = false
        ElMessage.error(`采集失败: ${response.error || '未知错误'}`)
      }
    } catch (error) {
      clearInterval(pollTaskTimer)
      pollTaskTimer = null
      fetchingData.value = false
      ElMessage.error('查询任务状态失败')
    }
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

const testConnection = async () => { try { await axios.post('/api/v1/prometheus/config/test'); ElMessage.success('连接测试成功') } catch { ElMessage.error('连接测试失败，请检查Cookie配置') } }
const saveCookie = async () => {
  // 先验证 Cookie 格式
  if (!cookieValue.value || cookieValue.value.trim().length < 10) {
    ElMessage.warning('Cookie 格式不正确，请检查后重试')
    return
  }
  
  try {
    await axios.post('/api/v1/prometheus/config/cookie', { 
      cookie_string: cookieValue.value.trim() 
    })
    ElMessage.success('Cookie配置保存成功')
    showCookieDialog.value = false
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message
    
    if (errorMsg.includes('无效') || errorMsg.includes('过期')) {
      ElMessage.error({
        message: 'Cookie 无效或已过期，请重新获取',
        duration: 5000,
        showClose: true
      })
    } else {
      ElMessage.error('Cookie 保存失败: ' + errorMsg)
    }
  }
}
const handleMulticlusterSelect = (file) => { multiclusterFile.value = file; multiclusterFileName.value = file.name; ElMessage.success(`已选择: ${file.name}`) }
const handleExcelSelect = (file) => { excelFile.value = file; excelFileName.value = file.name }

// 加载资源分析配置
const loadResourceConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await axios.get('/api/v1/config/load?module=analysis')

    // 获取 cluster_ids 配置
    const clusterIds = response.config?.cluster_ids || response.data?.config?.cluster_ids

    // 检查配置是否存在且非空
    if (clusterIds && clusterIds !== '' && clusterIds.length > 0) {
      // 处理数组或字符串格式
      const ids = Array.isArray(clusterIds)
        ? clusterIds
        : clusterIds.split(',').map(id => id.trim()).filter(id => id)

      if (ids.length > 0) {
        clusterIdsText.value = ids.join('\n')
        ElMessage.success(`已加载 ${ids.length} 个集群ID配置`)
      } else {
        ElMessage.warning('配置的集群ID列表为空，请先在系统配置中添加集群ID')
      }
    } else {
      ElMessage.warning('未找到配置的集群ID，请先在系统配置中添加集群ID')
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingConfig.value = false
  }
}

const startAnalysis = async () => {
  if (!canAnalyze.value) { ElMessage.warning('请先完成数据准备'); return }
  analyzing.value = true; analyzeProgress.value = 0; statusMessage.value = '正在准备数据...'
  const progressTimer = setInterval(() => { if (analyzeProgress.value < 90) analyzeProgress.value += 5 }, 500)
  try {
    let requestData = {}
    if (dataSourceType.value === 'fetch') {
      requestData.task_id = clusterDataTaskId.value
      if (excelFile.value) { const formData = new FormData(); formData.append('file', excelFile.value); const uploadRes = await axios.post('/api/v1/resource/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); requestData.excel_file_name = uploadRes.data?.filename || uploadRes.filename }
    } else {
      const formData = new FormData(); formData.append('file', multiclusterFile.value); const uploadRes = await axios.post('/api/v1/resource/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); requestData.multicluster_file_name = uploadRes.data?.filename || uploadRes.filename
      if (excelFile.value) { const excelFormData = new FormData(); excelFormData.append('file', excelFile.value); const excelUploadRes = await axios.post('/api/v1/resource/upload', excelFormData, { headers: { 'Content-Type': 'multipart/form-data' } }); requestData.excel_file_name = excelUploadRes.data?.filename || excelUploadRes.filename }
    }
    const analysisRes = await axios.post('/api/v1/resource/analyze', requestData)
    taskId.value = analysisRes.data?.task_id || analysisRes.task_id
    statusMessage.value = '正在分析数据...'
    
    // 保存 taskId 到 URL 参数
    router.replace({
      query: { ...route.query, taskId: taskId.value }
    })
    
    await pollResult(taskId.value); clearInterval(progressTimer); analyzeProgress.value = 100; ElMessage.success('资源分析报告生成完成')
  } catch (error) { clearInterval(progressTimer); ElMessage.error('分析失败: ' + (error.response?.data?.detail || error.message)) } finally { analyzing.value = false }
}

const pollResult = async (id) => {
  return new Promise((resolve, reject) => {
    // 清理旧的定时器
    if (pollResultTimer) {
      clearInterval(pollResultTimer)
      pollResultTimer = null
    }
    
    pollResultTimer = setInterval(async () => {
      try {
        const res = await axios.get(`/api/v1/resource/result/${id}`)
        
        // 处理进行中状态（包括AI解读生成）
        if (res.status === 'processing') {
          statusMessage.value = res.message || '正在分析中...'
          if (res.progress) {
            analyzeProgress.value = Math.min(res.progress, 95) // 最多到95%，留5%给完成
          }
          return // 继续轮询
        }
        
        // 处理成功状态
        if (res.success === true || (res.result && res.result.html_report)) { 
          clearInterval(pollResultTimer); pollResultTimer = null
          analysisResult.value = res
          reportLoading.value = true
          statusMessage.value = '分析完成，报告已生成'
          resolve()
        }
        // 处理失败状态
        else if (res.success === false && res.status === 'failed') { 
          clearInterval(pollResultTimer); pollResultTimer = null
          reject(new Error(res.error || '分析失败'))
        }
        // 如果没有明确的状态，继续轮询（可能还在处理中）
      } catch (error) { 
        // 404错误说明文件还未创建，继续轮询
        if (error.response?.status === 404) {
          statusMessage.value = '正在初始化任务...'
          return
        }
        // 其他错误才停止轮询
        clearInterval(pollResultTimer); pollResultTimer = null
        reject(error)
      }
    }, 2000)
  })
}

const reportUrl = computed(() => { const htmlFile = analysisResult.value?.html_file || analysisResult.value?.result?.html_report; return htmlFile ? getFullBackendUrl(htmlFile) : null })
const downloadReport = () => { if (!taskId.value) { ElMessage.warning('没有可下载的报告'); return }; const link = document.createElement('a'); link.href = getFullBackendUrl(`/api/v1/resource/download/${taskId.value}`); link.download = `resource_report_${taskId.value}.html`; document.body.appendChild(link); link.click(); document.body.removeChild(link); ElMessage.success('报告下载已开始') }
const openReport = () => { if (reportUrl.value) window.open(reportUrl.value, '_blank'); else ElMessage.warning('报告不可用') }

// 组件卸载时清理定时器
onUnmounted(() => {
  if (pollTaskTimer) {
    clearInterval(pollTaskTimer)
    pollTaskTimer = null
  }
  if (pollResultTimer) {
    clearInterval(pollResultTimer)
    pollResultTimer = null
  }
})
</script>

<style scoped>
/* 数据源选择 */
.source-selector { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
.source-option { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-4); border: 2px solid var(--border-color); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--transition-normal); }
.source-option:hover {
  border-color: var(--primary);
  background: rgba(26, 115, 232, 0.05);
}
.source-option-active { border-color: var(--primary); background: rgba(26, 115, 232, 0.1); }
.source-icon { font-size: 32px; color: var(--primary); }
.source-title { font-weight: 600; color: var(--text-primary); }
.source-desc { font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1); }

/* 配置提示框 */
.config-hint-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(26, 115, 232, 0.1);
  border: 1px solid rgba(26, 115, 232, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.config-link {
  color: var(--primary);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--duration-fast);
}

.config-link:hover {
  color: var(--primary);
  text-decoration: underline;
}

/* 输入区域 */
.source-content { display: flex; flex-direction: column; gap: var(--space-4); }
.input-section { background: var(--bg-secondary); padding: var(--space-4); border-radius: var(--radius-lg); border: 1px solid var(--border-color); }
.input-label { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); font-weight: 600; color: var(--text-secondary); margin-bottom: var(--space-3); }
.input-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.input-hint { font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-2); }

/* 操作按钮网格 */
.action-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3); }

/* 进度区域 */
.progress-section { background: rgba(26, 115, 232, 0.1); padding: var(--space-4); border-radius: var(--radius-lg); border: 1px solid rgba(26, 115, 232, 0.3); }
.progress-text { font-size: var(--text-sm); color: var(--text-secondary); text-align: center; margin-top: var(--space-3); }

/* 成功提示 */
.success-section { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-4); background: rgba(30, 142, 62, 0.1); border: 1px solid rgba(30, 142, 62, 0.3); border-radius: var(--radius-lg); color: var(--color-success); font-weight: 500; }

/* 上传区域 */
.upload-section { text-align: center; padding: var(--space-6); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); }
.upload-icon { font-size: 48px; color: var(--primary); margin-bottom: var(--space-3); }
.upload-title { font-size: var(--text-lg); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2); }
.upload-hint { font-size: var(--text-sm); color: var(--text-tertiary); margin-bottom: var(--space-4); }
.upload-input { display: flex; gap: var(--space-3); max-width: 400px; margin: 0 auto; }

/* 功能说明 */
.feature-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3); }
.feature-item { display: flex; align-items: flex-start; gap: var(--space-2); font-size: var(--text-sm); color: var(--text-secondary); }
.feature-icon { flex-shrink: 0; margin-top: 2px; }
.feature-icon-primary { color: var(--primary); }
.feature-icon-success { color: var(--color-success); }
.feature-icon-info { color: var(--color-info); }
.feature-icon-warning { color: var(--color-warning); }

/* 分析按钮 */
.analyze-button { width: 100%; height: 56px; font-size: var(--text-lg); font-weight: 600; }
.error-hint { margin-top: var(--space-3); padding: var(--space-3); background: rgba(217, 48, 37, 0.1); border: 1px solid rgba(217, 48, 37, 0.3); border-radius: var(--radius-lg); }
.error-hint p { font-size: var(--text-sm); color: var(--color-error); text-align: center; margin: 0; }

/* 加载动画 */
.spin-icon { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.success-icon { color: var(--color-success); margin-right: var(--space-2); }

/* 结果区域 */
.report-body { position: relative; min-height: 600px; }
.report-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); z-index: 10; }
.report-loading .spin-icon { font-size: 48px; color: var(--primary); }
.report-frame { width: 100%; min-height: 600px; border: none; border-radius: var(--radius-lg); background: white; }

/* 响应式 */
@media (max-width: 768px) {
  .source-selector { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: 1fr; }
  .feature-grid { grid-template-columns: 1fr; }
}
</style>