<template>
  <div class="op-page">

    <!-- 页面头部 -->
    <div class="op-header">
      <div class="op-header-left">
        <div class="op-header-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div>
          <h1 class="op-title">运营数据分析</h1>
          <p class="op-subtitle">上传数据文件或通过 API 查询，生成专业的运营分析报告</p>
        </div>
      </div>
    </div>

    <!-- 数据来源选择 -->
    <div class="op-card">
      <div class="op-card-header">
        <div class="op-card-title">
          <span class="op-card-accent accent-primary"></span>
          <el-icon class="op-card-icon"><Switch /></el-icon>
          数据来源
        </div>
      </div>
      <div class="op-card-body">
        <div class="source-tabs">
          <button
            class="source-tab"
            :class="{ active: dataSource === 'excel' }"
            @click="dataSource = 'excel'; handleSourceChange()"
          >
            <el-icon><Upload /></el-icon>
            <span>Excel 上传</span>
          </button>
          <button
            class="source-tab"
            :class="{ active: dataSource === 'api' }"
            @click="dataSource = 'api'; handleSourceChange()"
          >
            <el-icon><Connection /></el-icon>
            <span>API 查询</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Excel 上传模式 -->
    <transition name="op-fade-up">
      <div class="op-card" v-if="dataSource === 'excel'" key="excel">
        <div class="op-card-header">
          <div class="op-card-title">
            <span class="op-card-accent accent-blue"></span>
            <el-icon class="op-card-icon"><Upload /></el-icon>
            数据文件上传
            <el-tooltip placement="right" effect="light">
              <template #content>
                <div class="op-tooltip-content">
                  <p>• 上传 Excel 文件后，系统将自动进行数据分析</p>
                  <p>• 分析完成后会生成包含 AI 智能解读的报告</p>
                  <p>• AI 解读位于报告底部，提供数据洞察和建议</p>
                </div>
              </template>
              <el-icon class="op-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
        </div>
        <div class="op-card-body">
          <FileUpload @file-selected="handleFile" />
          <div class="op-action-bar">
            <el-button
              class="op-primary-btn"
              :loading="store.loading"
              :disabled="!file"
              @click="startExcelAnalysis"
            >
              <el-icon v-if="!store.loading"><DataAnalysis /></el-icon>
              {{ store.loading ? '分析中（含 AI 解读）...' : '开始分析' }}
            </el-button>
          </div>
        </div>
      </div>
    </transition>

    <!-- API 模式 -->
    <transition name="op-fade-up">
      <div v-if="dataSource === 'api'" key="api" class="op-api-flow">

        <!-- 查询参数 -->
        <div class="op-card">
          <div class="op-card-header">
            <div class="op-card-title">
              <span class="op-card-accent accent-blue"></span>
              <el-icon class="op-card-icon"><Connection /></el-icon>
              查询参数
              <el-tooltip placement="right" effect="light">
                <template #content>
                  <div class="op-tooltip-content">
                    <p>• 用户名和密码从系统配置中读取，无需手动填写</p>
                    <p>• 空间代码是 iCafe 空间的唯一标识符</p>
                    <p>• 页码和每页记录数用于控制分页查询范围</p>
                  </div>
                </template>
                <el-icon class="op-help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="op-card-extra">
              <QueryHistory @load="loadHistoryQuery" />
            </div>
          </div>
          <div class="op-card-body">
            <div class="op-param-grid">
              <div class="op-param-item">
                <label class="op-param-label">空间代码</label>
                <el-input v-model="apiForm.spacecode" placeholder="HMLCC" class="op-input" />
              </div>
              <div class="op-param-item">
                <label class="op-param-label">起始页码</label>
                <el-input-number v-model="apiForm.page" :min="1" :max="100" class="op-input-number" />
              </div>
              <div class="op-param-item">
                <label class="op-param-label">每页记录数</label>
                <el-input-number v-model="apiForm.pgcount" :min="1" :max="100" class="op-input-number" />
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤连接线 -->
        <div class="op-flow-line">
          <div class="op-flow-dot"></div>
          <div class="op-flow-dash"></div>
          <div class="op-flow-dot"></div>
        </div>

        <!-- 查询条件 -->
        <div class="op-card">
          <div class="op-card-header">
            <div class="op-card-title">
              <span class="op-card-accent accent-purple"></span>
              <el-icon class="op-card-icon"><Filter /></el-icon>
              查询条件
            </div>
          </div>
          <div class="op-card-body">
            <QueryBuilder ref="queryBuilderRef" v-model="apiForm.iql" />
            <div class="op-apply-bar">
              <span class="op-apply-hint">修改条件后点击「应用」生成 IQL 语句</span>
              <el-button class="op-apply-btn" @click="applyQueryConditions">
                <el-icon><Check /></el-icon>
                应用条件
              </el-button>
            </div>
          </div>
        </div>

        <!-- 步骤连接线 -->
        <div class="op-flow-line">
          <div class="op-flow-dot"></div>
          <div class="op-flow-dash"></div>
          <div class="op-flow-dot"></div>
        </div>

        <!-- IQL 查询语句 -->
        <div class="op-card">
          <div class="op-card-header">
            <div class="op-card-title">
              <span class="op-card-accent accent-green"></span>
              <el-icon class="op-card-icon"><Document /></el-icon>
              IQL 查询语句
              <el-tooltip placement="right" effect="light">
                <template #content>
                  <div class="op-tooltip-content">
                    <p>• 上方的查询条件点击「应用」后会生成 IQL 语句</p>
                    <p>• 您也可以在此直接编辑 IQL 语句</p>
                  </div>
                </template>
                <el-icon class="op-help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </div>
          <div class="op-card-body">
            <IQLEditor v-model="apiForm.iql" />
            <div class="op-action-bar">
              <el-button
                class="op-primary-btn"
                :loading="store.loading"
                :disabled="!apiForm.iql"
                @click="startApiAnalysis"
              >
                <el-icon v-if="!store.loading"><DataAnalysis /></el-icon>
                {{ store.loading ? '查询分析中...' : '开始查询分析' }}
              </el-button>
            </div>
          </div>
        </div>

      </div>
    </transition>

    <!-- 分析结果 -->
    <transition name="op-result-slide">
      <div class="op-card op-result-card" v-if="store.taskId">
        <StateDisplay
          v-if="store.loading"
          state="loading"
          loading-text="正在生成分析报告..."
        >
          <ProgressBar :percentage="progress" />
          <p class="op-loading-hint">请稍候，这可能需要几分钟时间</p>
        </StateDisplay>

        <div v-else-if="store.result" class="result-container">
          <div class="op-result-header">
            <div class="op-result-status">
              <div class="op-status-dot"></div>
              <span class="op-status-text">分析完成</span>
              <span v-if="store.result.total_records" class="op-record-count">
                共 {{ store.result.total_records }} 条记录
              </span>
            </div>
            <div class="op-result-actions">
              <el-button class="op-ghost-btn" @click="openReport">
                <el-icon><FullScreen /></el-icon>全屏查看
              </el-button>
              <el-button class="op-primary-btn" @click="downloadReport">
                <el-icon><Download /></el-icon>下载报告
              </el-button>
            </div>
          </div>
          <div class="report-preview">
            <div v-if="iframeLoading" class="preview-loading">
              <el-icon class="spin-icon"><Loading /></el-icon>
              <p>报告加载中...</p>
            </div>
            <div v-if="reportUrl" class="preview-frame">
              <iframe :src="reportUrl" @load="handleIframeLoad" @error="handleIframeError"></iframe>
            </div>
            <div v-else class="preview-empty">
              <el-icon class="empty-icon"><Warning /></el-icon>
              <h3>报告预览不可用</h3>
              <p>请点击下载按钮获取完整报告文件</p>
              <el-button class="op-primary-btn" @click="downloadReport">
                <el-icon><Download /></el-icon>立即下载
              </el-button>
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
import { Download, FullScreen, Loading, DataAnalysis, Warning, Upload, Connection, Switch, QuestionFilled, Filter, Document, Check } from '@element-plus/icons-vue'
import { Card, StateDisplay } from '@/components/common'
import { useOperationalStore } from '@/stores/operational'
import { getFullBackendUrl } from '@/utils/config'
import { getOperationalDefaults } from '@/api/operational'
import FileUpload from '@/components/common/FileUpload.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import DateRangePicker from '@/components/operational/DateRangePicker.vue'
import QueryBuilder from '@/components/operational/QueryBuilder.vue'
import IQLEditor from '@/components/operational/IQLEditor.vue'
import QueryHistory from '@/components/operational/QueryHistory.vue'
import { useQueryHistory } from '@/composables/useQueryHistory'

const route = useRoute()
const router = useRouter()
const store = useOperationalStore()
const file = ref(null)
const progress = ref(0)
const iframeLoading = ref(false)
const dataSource = ref('excel')
const queryBuilderRef = ref(null)

// 定时器引用，用于清理
let pollTimer = null

// 查询历史
const { addHistory } = useQueryHistory()

// API 查询表单
const apiForm = ref({
  spacecode: 'HMLCC',
  iql: '',
  page: 1,
  pgcount: 100
})

// 表单验证 - 只要求 spacecode 和 iql 必填，用户名密码可选（留空使用默认配置）
const isApiFormValid = computed(() => {
  return apiForm.value.spacecode && apiForm.value.iql
})

// 应用查询条件（由"应用条件"按钮触发）
const applyQueryConditions = () => {
  if (queryBuilderRef.value) {
    queryBuilderRef.value.applyConditions()
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
  
  // 加载默认配置
  try {
    const defaults = await getOperationalDefaults()
    if (defaults) {
      apiForm.value.spacecode = defaults.spacecode || 'HMLCC'
      apiForm.value.iql = defaults.default_iql || ''
      apiForm.value.page = defaults.default_page || 1
      apiForm.value.pgcount = defaults.default_pgcount || 100
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
  apiForm.value.iql = historyItem.iql
  apiForm.value.page = historyItem.page
  apiForm.value.pgcount = historyItem.pgcount
  ElMessage.success('已加载历史查询')
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
/* ─── 页面容器 ─────────────────────────────────────────── */
.op-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 0 0 var(--space-12);
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ─── 页面头部 ─────────────────────────────────────────── */
.op-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-8) 0 var(--space-6);
}

.op-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.op-header-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--icon-bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-inverse);
  font-size: var(--text-2xl);
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
}

.op-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-1);
  letter-spacing: -0.3px;
}

.op-subtitle {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0;
}

/* ─── 卡片通用 ─────────────────────────────────────────── */
.op-card {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-secondary);
  box-shadow: 0 1px 3px rgba(60, 64, 67, 0.08), 0 1px 4px rgba(60, 64, 67, 0.04);
  margin-bottom: var(--space-4);
  transition: box-shadow var(--duration-normal) cubic-bezier(0.2, 0, 0, 1),
              border-color var(--duration-normal) cubic-bezier(0.2, 0, 0, 1);
  overflow: hidden;
}

.op-card:hover {
  box-shadow: 0 2px 8px rgba(60, 64, 67, 0.12), 0 2px 6px rgba(60, 64, 67, 0.06);
  border-color: var(--border-primary);
}

.op-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5) 0;
}

.op-card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.op-card-accent {
  width: 3px;
  height: 16px;
  border-radius: 2px;
  flex-shrink: 0;
}
.accent-primary { background: var(--color-primary-600); }
.accent-blue    { background: var(--color-primary-500); }
.accent-purple  { background: #7c4dff; }
.accent-green   { background: var(--color-success); }
.accent-orange  { background: var(--color-warning); }

.op-card-icon {
  font-size: var(--text-lg);
  color: var(--text-secondary);
}

.op-card-extra {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.op-card-body {
  padding: var(--space-4) var(--space-5) var(--space-5);
}

/* ─── 帮助图标 ─────────────────────────────────────────── */
.op-help-icon {
  font-size: 15px;
  color: var(--text-disabled);
  cursor: pointer;
  transition: color var(--duration-fast) ease;
}
.op-help-icon:hover { color: var(--color-primary-600); }

.op-tooltip-content {
  font-size: var(--text-sm);
  line-height: 1.8;
  padding: 4px 2px;
  color: var(--text-secondary);
}
.op-tooltip-content p { margin: 4px 0; }

/* ─── 数据来源 tab ─────────────────────────────────────── */
.source-tabs {
  display: inline-flex;
  background: var(--bg-tertiary);
  border-radius: 10px;
  padding: 4px;
  gap: 2px;
}

.source-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: var(--space-2) var(--space-5);
  border-radius: 7px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--duration-normal) cubic-bezier(0.2, 0, 0, 1),
              color var(--duration-normal) cubic-bezier(0.2, 0, 0, 1),
              box-shadow var(--duration-normal) cubic-bezier(0.2, 0, 0, 1);
  outline: none;
  white-space: nowrap;
}

.source-tab .el-icon {
  font-size: 15px;
}

.source-tab:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-primary);
}

.source-tab.active {
  background: var(--bg-primary);
  color: var(--color-primary-600);
  font-weight: var(--font-semibold);
  box-shadow: 0 1px 4px rgba(60, 64, 67, 0.18);
}

/* ─── API 流程包裹 ──────────────────────────────────────── */
.op-api-flow {
  display: flex;
  flex-direction: column;
}

/* ─── 步骤连接线 ──────────────────────────────────────── */
.op-flow-line {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 28px;
  gap: 0;
  margin-bottom: 0;
}

.op-flow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-primary);
  flex-shrink: 0;
}

.op-flow-dash {
  flex: 1;
  width: 1px;
  background: repeating-linear-gradient(
    to bottom,
    var(--border-primary) 0px,
    var(--border-primary) 4px,
    transparent 4px,
    transparent 8px
  );
}

/* ─── 查询参数网格 ─────────────────────────────────────── */
.op-param-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: var(--space-4);
}

.op-param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.op-param-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.op-input {
  width: 100%;
}

.op-input-number {
  width: 100%;
}

.op-input-number :deep(.el-input-number) {
  width: 100%;
}

/* ─── 应用条件栏 ─────────────────────────────────────────── */
.op-apply-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding-top: 14px;
  border-top: 1px solid var(--bg-tertiary);
}

.op-apply-hint {
  font-size: var(--text-sm);
  color: var(--text-disabled);
}

.op-apply-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-primary-600);
  background: transparent;
  color: var(--color-primary-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--duration-fast) ease, box-shadow var(--duration-fast) ease, transform 100ms ease;
  outline: none;
}

.op-apply-btn:hover {
  background: rgba(26, 115, 232, 0.06);
  box-shadow: 0 1px 4px rgba(26, 115, 232, 0.2);
  transform: translateY(-1px);
}

.op-apply-btn:active {
  transform: translateY(0);
  background: rgba(26, 115, 232, 0.12);
}

/* ─── 主操作按钮 ──────────────────────────────────────── */
.op-action-bar {
  display: flex;
  justify-content: center;
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--bg-tertiary);
}

.op-primary-btn {
  display: inline-flex !important;
  align-items: center;
  gap: 7px;
  height: 40px !important;
  min-width: 180px;
  padding: 0 var(--space-6) !important;
  border-radius: var(--radius-lg) !important;
  border: none !important;
  background: var(--icon-bg-primary) !important;
  color: var(--text-inverse) !important;
  font-size: var(--text-base) !important;
  font-weight: var(--font-medium) !important;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.28) !important;
  transition: box-shadow var(--duration-normal) cubic-bezier(0.2, 0, 0, 1),
              transform var(--duration-fast) cubic-bezier(0.2, 0, 0, 1),
              opacity var(--duration-normal) ease !important;
}

.op-primary-btn:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(26, 115, 232, 0.38) !important;
  transform: translateY(-1px);
}

.op-primary-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(26, 115, 232, 0.2) !important;
}

.op-primary-btn:disabled {
  background: linear-gradient(135deg, var(--text-disabled) 0%, var(--border-primary) 100%) !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

/* ─── Ghost 按钮 ─────────────────────────────────────── */
.op-ghost-btn {
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  height: 36px !important;
  padding: 0 var(--space-4) !important;
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-primary) !important;
  background: var(--bg-primary) !important;
  color: var(--text-secondary) !important;
  font-size: var(--text-sm) !important;
  font-weight: var(--font-medium) !important;
  transition: border-color var(--duration-fast) ease, background var(--duration-fast) ease, transform 100ms ease !important;
}

.op-ghost-btn:hover {
  border-color: var(--color-primary-600) !important;
  color: var(--color-primary-600) !important;
  background: rgba(26, 115, 232, 0.04) !important;
  transform: translateY(-1px);
}

/* ─── 模板区 ────────────────────────────────────────── */
.op-template-section {
  padding: 4px 0;
}

.op-section-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin: 0 0 10px;
}

.op-template-select {
  width: 100%;
}

.op-template-divider {
  height: 1px;
  background: var(--bg-tertiary);
  margin: var(--space-4) 0;
}

/* ─── 模板下拉选项 ─────────────────────────────────── */
.template-option {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 3px 0;
}

.template-name {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.template-desc {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  line-height: 1.4;
}

/* ─── 加载状态 ──────────────────────────────────────── */
.op-loading-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
  text-align: center;
}

.spin-icon {
  font-size: 40px;
  color: var(--color-primary-600);
  animation: op-spin 1s linear infinite;
}

@keyframes op-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ─── 结果卡片 ──────────────────────────────────────── */
.op-result-card {
  border-color: var(--border-secondary);
  overflow: hidden;
}

.op-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  background: linear-gradient(to right, var(--bg-secondary), var(--bg-primary));
  border-bottom: 1px solid var(--bg-tertiary);
}

.op-result-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.op-status-dot {
  width: 10px;
  height: 10px;
  background: var(--color-success);
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(30, 142, 62, 0.4);
  animation: op-pulse 2s infinite;
}

@keyframes op-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(30, 142, 62, 0.4); }
  50%       { box-shadow: 0 0 0 6px rgba(30, 142, 62, 0); }
}

.op-status-text {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-success);
}

.op-record-count {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 11px;
  background: var(--color-success-bg);
  color: var(--color-success);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.op-result-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* ─── 报告预览 ─────────────────────────────────────── */
.report-preview {
  flex: 1;
  position: relative;
  background: var(--bg-secondary);
  min-height: 600px;
  overflow: hidden;
}

.result-container {
  display: flex;
  flex-direction: column;
}

.preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  z-index: 10;
  gap: var(--space-3);
}

.preview-loading p {
  color: var(--text-secondary);
  font-weight: var(--font-medium);
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
  padding: 80px var(--space-6);
  text-align: center;
}

.empty-icon {
  font-size: 56px;
  color: var(--color-warning);
  margin-bottom: var(--space-4);
  opacity: 0.7;
}

.preview-empty h3 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 10px;
}

.preview-empty p {
  color: var(--text-tertiary);
  margin-bottom: var(--space-5);
  line-height: 1.6;
  max-width: 360px;
  font-size: var(--text-sm);
}

/* ─── 过渡动画 ─────────────────────────────────────── */
.op-fade-up-enter-active {
  transition: opacity 280ms cubic-bezier(0, 0, 0.2, 1),
              transform 280ms cubic-bezier(0, 0, 0.2, 1);
}
.op-fade-up-leave-active {
  transition: opacity 180ms cubic-bezier(0.4, 0, 1, 1),
              transform 180ms cubic-bezier(0.4, 0, 1, 1);
}
.op-fade-up-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.op-fade-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.op-result-slide-enter-active {
  transition: opacity 350ms cubic-bezier(0, 0, 0.2, 1),
              transform 350ms cubic-bezier(0, 0, 0.2, 1);
}
.op-result-slide-leave-active {
  transition: opacity 200ms cubic-bezier(0.4, 0, 1, 1);
}
.op-result-slide-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.op-result-slide-leave-to {
  opacity: 0;
}

/* ─── 响应式 ───────────────────────────────────────── */
@media (max-width: 640px) {
  .op-param-grid {
    grid-template-columns: 1fr;
  }

  .op-header-icon {
    width: 40px;
    height: 40px;
    font-size: var(--text-xl);
  }

  .op-title {
    font-size: var(--text-xl);
  }

  .op-apply-hint {
    display: none;
  }
}
</style>
