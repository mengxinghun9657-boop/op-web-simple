<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><UploadFilled /></el-icon>
          </div>
          运营数据分析
        </div>
        <div class="page-subtitle">上传数据文件或通过API查询,生成专业的运营分析报告</div>
      </div>
    </div>

    <!-- 数据来源选择 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Switch /></el-icon>
          数据来源
        </div>
      </div>
      <div class="content-card-body">
        <el-radio-group v-model="dataSource" size="large" @change="handleSourceChange">
          <el-radio-button label="excel">
            <el-icon><Upload /></el-icon>
            <span>Excel 上传</span>
          </el-radio-button>
          <el-radio-button label="api">
            <el-icon><Connection /></el-icon>
            <span>API 查询</span>
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- Excel 上传模式 -->
    <div class="content-card" v-if="dataSource === 'excel'">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Upload /></el-icon>
          数据文件上传
          <el-tooltip placement="right" effect="light" :width="300">
            <template #content>
              <div class="upload-help-content">
                <p>• 上传Excel文件后，系统将自动进行数据分析</p>
                <p>• 分析完成后会生成包含AI智能解读的报告</p>
                <p>• AI解读位于报告底部，提供数据洞察和建议</p>
              </div>
            </template>
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
      </div>
      <div class="content-card-body">
        <FileUpload @file-selected="handleFile" />
        <div class="upload-actions">
          <el-button type="primary" size="large" :loading="store.loading" :disabled="!file" @click="startExcelAnalysis">
            <el-icon v-if="!store.loading"><DataAnalysis /></el-icon>
            {{ store.loading ? '分析中（含AI解读）...' : '开始分析' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- API 查询模式 -->
    <div class="content-card" v-if="dataSource === 'api'">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Connection /></el-icon>
          API 查询参数
          <el-tooltip placement="right" effect="light" :width="400">
            <template #content>
              <div class="api-help-content">
                <p>• 任何用户都可以调用API，但调用API所使用的用户名需要有对应空间的权限，否则会报没有空间权限</p>
                <p>• 权限需跟空间权限一致：只读权限不可以调用API、新建权限可以新建卡片、编辑权限可以新建以及修改卡片、管理员权限可以调用新建修改查询等API</p>
                <p>• 密码是邮箱密码或者是虚拟密码，建议使用虚拟密码</p>
                <p>• <a href="https://ku.baidu-int.com/knowledge/HFVrC7hq1Q/_SKPgSwp2G/NbX2gitgSF/RhtGsvv5GGK_hs" target="_blank" class="help-link">获取虚拟密码</a></p>
                <p style="margin-top: 8px; color: #67c23a;">• 不填写用户名密码将使用默认配置</p>
              </div>
            </template>
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="content-card-extra">
          <QueryHistory @load="loadHistoryQuery" />
        </div>
      </div>
      <div class="content-card-body">
        <el-form :model="apiForm" label-width="120px" class="api-form">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="空间代码">
                <el-input v-model="apiForm.spacecode" placeholder="HMLCC" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="用户名">
                <el-input v-model="apiForm.username" placeholder="留空使用默认配置" clearable />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="密码">
                <el-input v-model="apiForm.password" type="password" placeholder="留空使用默认配置" show-password clearable />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="起始页码">
                <el-input-number v-model="apiForm.page" :min="1" :max="100" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="每页记录数">
                <el-input-number v-model="apiForm.pgcount" :min="1" :max="100" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- 查询条件构建器 -->
    <div class="content-card" v-if="dataSource === 'api'">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Filter /></el-icon>
          查询条件
        </div>
      </div>
      <div class="content-card-body">
        <QueryBuilder v-model="apiForm.iql" />
      </div>
    </div>

    <!-- IQL 查询语句 -->
    <div class="content-card" v-if="dataSource === 'api'">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Document /></el-icon>
          IQL 查询语句
          <el-tooltip placement="right" effect="light" :width="300">
            <template #content>
              <div class="iql-help-content">
                <p>• 上方的查询条件会自动生成IQL语句</p>
                <p>• 您也可以在此直接编辑IQL语句</p>
                <p>• 点击"语法帮助"查看完整的IQL语法说明</p>
              </div>
            </template>
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="content-card-extra">
          <QueryHistory @load="loadHistoryQuery" />
        </div>
      </div>
      <div class="content-card-body">
        <IQLEditor v-model="apiForm.iql" />
      </div>
    </div>

    <!-- 查询模板 -->
    <div class="content-card" v-if="dataSource === 'api'">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Collection /></el-icon>
          查询模板
        </div>
      </div>
      <div class="content-card-body">
        <el-form :model="apiForm" label-width="120px" class="api-form">
          <el-form-item label="系统模板">
            <div class="template-selector-wrapper">
              <el-select v-model="selectedTemplate" @change="applyTemplate" placeholder="选择系统模板" clearable style="flex: 1">
                <el-option v-for="t in iqlTemplates" :key="t.id" :label="t.name" :value="t.id">
                  <div class="template-option">
                    <span class="template-name">{{ t.name }}</span>
                    <span class="template-desc">{{ t.description }}</span>
                  </div>
                </el-option>
              </el-select>
            </div>
          </el-form-item>

          <!-- 自定义模板 -->
          <el-form-item label="自定义模板">
            <CustomTemplates :current-iql="apiForm.iql" @load="loadCustomTemplate" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 开始查询按钮 -->
    <div class="content-card" v-if="dataSource === 'api'">
      <div class="content-card-body">
        <div class="upload-actions">
          <el-button type="primary" size="large" :loading="store.loading" :disabled="!apiForm.iql" @click="startApiAnalysis">
            <el-icon v-if="!store.loading"><DataAnalysis /></el-icon>
            {{ store.loading ? '查询分析中...' : '开始查询分析' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分析结果 -->
    <transition name="fade-slide">
      <div class="content-card" v-if="store.taskId" style="grid-column: span 2;">
        <StateDisplay
          v-if="store.loading"
          state="loading"
          loading-text="正在生成分析报告..."
        >
          <ProgressBar :percentage="progress" />
          <p class="loading-hint">请稍候，这可能需要几分钟时间</p>
        </StateDisplay>
        
        <div v-else-if="store.result" class="result-container">
          <div class="result-header">
            <div class="result-status">
              <div class="status-dot"></div>
              <span class="status-text">分析完成</span>
              <span v-if="store.result.total_records" class="record-count">（共 {{ store.result.total_records }} 条记录）</span>
            </div>
            <div class="result-actions">
              <el-button type="primary" @click="downloadReport"><el-icon><Download /></el-icon>下载报告</el-button>
              <el-button @click="openReport"><el-icon><FullScreen /></el-icon>全屏查看</el-button>
            </div>
          </div>
          <div class="report-preview">
            <div v-if="iframeLoading" class="preview-loading"><el-icon class="spin-icon"><Loading /></el-icon><p>报告加载中...</p></div>
            <div v-if="reportUrl" class="preview-frame"><iframe :src="reportUrl" @load="handleIframeLoad" @error="handleIframeError"></iframe></div>
            <div v-else class="preview-empty">
              <el-icon class="empty-icon"><Warning /></el-icon>
              <h3>报告预览不可用</h3>
              <p>请点击下载按钮获取完整报告文件</p>
              <el-button type="primary" @click="downloadReport"><el-icon><Download /></el-icon>立即下载</el-button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>


<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, FullScreen, Loading, UploadFilled, DataAnalysis, Warning, Upload, Connection, Switch, QuestionFilled, Filter, Document, Collection } from '@element-plus/icons-vue'
import { Card, StateDisplay } from '@/components/common'
import { useOperationalStore } from '@/stores/operational'
import { getFullBackendUrl } from '@/utils/config'
import { getOperationalDefaults, getIQLTemplates } from '@/api/operational'
import FileUpload from '@/components/common/FileUpload.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import DateRangePicker from '@/components/operational/DateRangePicker.vue'
import QueryBuilder from '@/components/operational/QueryBuilder.vue'
import IQLEditor from '@/components/operational/IQLEditor.vue'
import QueryHistory from '@/components/operational/QueryHistory.vue'
import CustomTemplates from '@/components/operational/CustomTemplates.vue'
import { useQueryHistory } from '@/composables/useQueryHistory'

const route = useRoute()
const router = useRouter()
const store = useOperationalStore()
const file = ref(null)
const progress = ref(0)
const iframeLoading = ref(false)
const dataSource = ref('excel')

// 定时器引用，用于清理
let pollTimer = null

// 查询历史
const { addHistory } = useQueryHistory()

// IQL 模板相关
const iqlTemplates = ref([])
const selectedTemplate = ref('')
const syntaxHelp = ref({ operators: [], common_fields: [], field_examples: {} })

// API 查询表单
const apiForm = ref({
  spacecode: 'HMLCC',
  username: '',
  password: '',
  iql: '',
  page: 1,
  pgcount: 100
})

// 表单验证 - 只要求 spacecode 和 iql 必填，用户名密码可选（留空使用默认配置）
const isApiFormValid = computed(() => {
  return apiForm.value.spacecode && apiForm.value.iql
})

// 应用模板
const applyTemplate = (templateId) => {
  const template = iqlTemplates.value.find(t => t.id === templateId)
  if (template && template.template) {
    apiForm.value.iql = template.template
    
    // 提示用户
    ElMessage.success({
      message: `已应用模板: ${template.name}`,
      duration: 3000
    })
    
    // 如果模板有参数，提示用户修改
    if (template.params && template.params.length > 0) {
      ElMessage.info({
        message: '请根据实际需求修改模板中的参数',
        duration: 5000,
        showClose: true
      })
    }
  }
}

// 加载默认配置和模板
onMounted(async () => {
  // 优先从 URL 参数恢复任务状态
  const taskIdFromUrl = route.query.taskId
  
  if (taskIdFromUrl) {
    // 恢复任务状态
    store.taskId = taskIdFromUrl
    store.loading = true
    progress.value = 0
    
    // 开始轮询结果
    poll(taskIdFromUrl).then(() => {
      ElMessage.success('任务已完成')
    }).catch(() => {
      ElMessage.error('任务恢复失败，请重新分析')
      store.loading = false
    })
  }
  
  // 加载默认配置和模板
  try {
    const [defaults, templatesData] = await Promise.all([
      getOperationalDefaults(),
      getIQLTemplates()
    ])
    if (defaults) {
      apiForm.value.spacecode = defaults.spacecode || 'HMLCC'
      apiForm.value.iql = defaults.default_iql || ''
      apiForm.value.page = defaults.default_page || 1
      apiForm.value.pgcount = defaults.default_pgcount || 100
    }
    if (templatesData) {
      iqlTemplates.value = templatesData.templates || []
      syntaxHelp.value = templatesData.syntax_help || {}
    }
  } catch (e) {
    console.warn('加载配置失败:', e)
  }
})

const handleSourceChange = () => {
  // 先清空 UI 状态
  progress.value = 0
  file.value = null
  
  // 使用 nextTick 确保 UI 更新后再清空 store 状态
  nextTick(() => {
    store.reset()
  })
}

const handleFile = (f) => { file.value = f }

const startExcelAnalysis = async () => {
  if (!file.value) { ElMessage.warning('请先选择文件'); return }
  const formData = new FormData()
  formData.append('file', file.value)
  progress.value = 0
  const timer = setInterval(() => { if (progress.value < 90) progress.value += 5 }, 500)
  try {
    const res = await store.analyzeData(formData)
    
    // 保存 taskId 到 URL 参数
    router.replace({
      query: { ...route.query, taskId: res.task_id }
    })
    
    await poll(res.task_id)
    ElMessage.success({
      message: '分析完成！报告包含AI智能解读，请滚动到底部查看',
      duration: 5000,
      showClose: true
    })
  } catch (error) {
    ElMessage.error('分析失败: ' + (error.message || '未知错误'))
  } finally {
    clearInterval(timer)
    progress.value = 100
  }
}

const startApiAnalysis = async () => {
  if (!isApiFormValid.value) { ElMessage.warning('请填写完整的查询参数'); return }
  progress.value = 0
  const timer = setInterval(() => { if (progress.value < 90) progress.value += 3 }, 500)
  try {
    const res = await store.analyzeApiData(apiForm.value)
    
    // 保存 taskId 到 URL 参数
    router.replace({
      query: { ...route.query, taskId: res.task_id }
    })
    
    // 保存查询历史
    addHistory({
      spacecode: apiForm.value.spacecode,
      username: apiForm.value.username,
      iql: apiForm.value.iql,
      page: apiForm.value.page,
      pgcount: apiForm.value.pgcount,
      recordCount: null // 将在结果返回后更新
    })
    
    await poll(res.task_id)
    
    // 检查任务状态
    if (store.result?.status === 'failed') {
      const errorMsg = store.result?.error || '分析失败'
      
      // 根据错误类型提供不同的提示
      if (errorMsg.includes('认证') || errorMsg.includes('权限') || errorMsg.includes('Cookie')) {
        ElMessage.error({
          message: '认证失败，请检查用户名和密码是否正确',
          duration: 5000,
          showClose: true
        })
      } else if (errorMsg.includes('空间') || errorMsg.includes('spacecode')) {
        ElMessage.error({
          message: '空间代码错误或无权限访问该空间',
          duration: 5000,
          showClose: true
        })
      } else if (errorMsg.includes('IQL') || errorMsg.includes('语法')) {
        ElMessage.error({
          message: 'IQL 语法错误，请检查查询语句',
          duration: 5000,
          showClose: true
        })
      } else {
        ElMessage.error('分析失败: ' + errorMsg)
      }
      return
    }
    
    // 更新历史记录的记录数
    if (store.result?.total_records) {
      addHistory({
        spacecode: apiForm.value.spacecode,
        username: apiForm.value.username,
        iql: apiForm.value.iql,
        page: apiForm.value.page,
        pgcount: apiForm.value.pgcount,
        recordCount: store.result.total_records
      })
    }
    
    ElMessage.success({
      message: '分析完成！报告包含AI智能解读，请滚动到底部查看',
      duration: 5000,
      showClose: true
    })
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message
    ElMessage.error('分析失败: ' + errorMsg)
  } finally {
    clearInterval(timer)
    progress.value = 100
  }
}

// 加载历史查询
const loadHistoryQuery = (historyItem) => {
  apiForm.value.spacecode = historyItem.spacecode
  apiForm.value.username = historyItem.username || ''
  apiForm.value.iql = historyItem.iql
  apiForm.value.page = historyItem.page
  apiForm.value.pgcount = historyItem.pgcount
  ElMessage.success('已加载历史查询')
}

// 加载自定义模板
const loadCustomTemplate = (iql) => {
  apiForm.value.iql = iql
}

const poll = async (taskId) => {
  return new Promise((resolve) => {
    // 清理旧的定时器
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    
    pollTimer = setInterval(async () => {
      const isComplete = await store.fetchResult(taskId)
      if (isComplete) { 
        clearInterval(pollTimer)
        pollTimer = null
        resolve() 
      }
    }, 2000)
  })
}

const reportUrl = computed(() => {
  const htmlFile = store.result?.html_file || store.result?.html_report || store.result?.result_url
  if (!htmlFile) return null
  if (htmlFile.startsWith('html_reports/')) return `/api/v1/reports/proxy/${htmlFile}`
  return getFullBackendUrl(htmlFile)
})

watch(reportUrl, (newUrl) => { if (newUrl) iframeLoading.value = true })

const handleIframeLoad = () => { iframeLoading.value = false }
const handleIframeError = () => { iframeLoading.value = false; ElMessage.error('报告加载失败，请尝试下载') }
const openReport = () => { if (reportUrl.value) window.open(reportUrl.value, '_blank'); else ElMessage.warning('报告文件不存在') }
const downloadReport = () => {
  if (!store.taskId) { ElMessage.warning('没有可下载的报告'); return }
  window.open(getFullBackendUrl(`/api/v1/operational/download/${store.taskId}`), '_blank')
  ElMessage.success('开始下载报告')
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>


<style scoped>
/* 帮助图标 */
.help-icon {
  margin-left: var(--space-2);
  color: var(--primary);
  cursor: pointer;
  font-size: 16px;
  vertical-align: middle;
  transition: all var(--transition-fast);
}

.help-icon:hover {
  color: var(--primary);
  transform: scale(1.1);
}

.upload-help-content,
.api-help-content,
.iql-help-content {
  font-size: 13px;
  line-height: 1.8;
  padding: var(--space-2);
}

.upload-help-content p,
.api-help-content p,
.iql-help-content p {
  margin: var(--space-2) 0;
}

.api-help-content .help-link {
  color: var(--primary);
  text-decoration: underline;
  transition: color var(--transition-fast);
}

.api-help-content .help-link:hover {
  color: var(--primary);
}

/* API 表单 */
.api-form {
  margin-bottom: var(--space-4);
}

.api-form .el-form-item {
  margin-bottom: var(--space-5);
}

.api-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

/* 模板选择器 */
.template-selector-wrapper {
  display: flex;
  gap: var(--space-3);
  width: 100%;
}

.template-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-1) 0;
}

.template-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.template-desc {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  line-height: 1.4;
}

/* 上传操作 */
.upload-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.upload-actions .el-button {
  min-width: 160px;
  height: 44px;
  font-weight: 500;
  transition: all var(--transition-fast);
}

/* 加载状态 */
.spin-icon {
  font-size: 48px;
  color: var(--primary);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
}

/* 结果展示 */
.result-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5) var(--space-6);
  border-bottom: 2px solid var(--border-color);
  background: linear-gradient(to bottom, var(--bg-container), var(--bg-secondary));
}

.result-status {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.status-dot {
  width: 12px;
  height: 12px;
  background: var(--color-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 0 0 rgba(30, 142, 62, 0.4);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(30, 142, 62, 0.4);
  }
  50% {
    opacity: 0.8;
    box-shadow: 0 0 0 8px rgba(30, 142, 62, 0);
  }
}

.status-text {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-success);
  letter-spacing: -0.01em;
}

.record-count {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  font-weight: 400;
}

.result-actions {
  display: flex;
  gap: var(--space-3);
}

.result-actions .el-button {
  transition: background-color var(--duration-fast) var(--ease-standard),
              box-shadow var(--duration-fast) var(--ease-standard);
}

.result-actions .el-button:hover {
  box-shadow: var(--shadow-sm);
}

/* 报告预览 */
.report-preview {
  flex: 1;
  position: relative;
  background: var(--bg-secondary);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  overflow: hidden;
  min-height: 600px;
}

.preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.preview-loading p {
  margin-top: var(--space-4);
  color: var(--text-primary);
  font-weight: 500;
  font-size: var(--text-base);
}

.preview-frame {
  height: 100%;
}

.preview-frame iframe {
  width: 100%;
  height: 100%;
  min-height: 600px;
  border: none;
  background: white;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  text-align: center;
  min-height: 500px;
}

.empty-icon {
  font-size: 72px;
  color: var(--color-warning);
  margin-bottom: var(--space-5);
  opacity: 0.8;
}

.preview-empty h3 {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-3);
  letter-spacing: -0.01em;
}

.preview-empty p {
  color: var(--text-tertiary);
  margin-bottom: var(--space-5);
  line-height: 1.6;
  max-width: 400px;
}

.preview-empty .el-button {
  min-width: 140px;
}

/* 过渡动画 */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
