<template>
  <div class="task-history-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-icon">
        <el-icon :size="24"><Clock /></el-icon>
      </div>
      <div class="page-header-content">
        <h2 class="page-title">历史任务</h2>
        <p class="page-subtitle">查看和管理所有任务执行记录</p>
      </div>
    </div>

    <!-- 筛选卡片 -->
    <Card
      title="筛选条件"
      icon="Search"
      class="animate-slide-in-up"
    >
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="任务状态">
          <el-select v-model="filters.status" placeholder="全部" clearable class="filter-select">
            <el-option label="全部" value="" />
            <el-option label="等待中" value="pending" />
            <el-option label="进行中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="filters.task_type" placeholder="全部" clearable class="filter-select">
            <el-option label="全部" value="" />
            <el-option
              v-for="option in taskTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">
            <el-icon><RefreshLeft /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </Card>

    <!-- 任务列表 -->
    <Card
      class="animate-slide-in-up"
    >
      <template #header>
        <div class="card-header-content">
          <span class="card-header-title">
            <el-icon><List /></el-icon>
            任务列表
          </span>
          <el-tag type="info">共 {{ total }} 条</el-tag>
        </div>
      </template>

      <el-table :data="tasks" v-loading="loading" class="modern-table">
        <el-table-column prop="id" label="任务ID" width="200" fixed="left">
          <template #default="{ row }">
            <span class="task-id">{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="任务类型" width="140">
          <template #default="{ row }">
            <el-tag :type="taskTypeColors[row.task_type] || 'primary'">
              {{ taskTypeLabels[row.task_type] || row.task_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusColors[row.status]">
              {{ statusLabels[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="getProgressStatus(row.status)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column label="进度详情" width="140" align="center">
          <template #default="{ row }">
            <span class="progress-detail">{{ getProgressText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="200">
          <template #default="{ row }">
            <span class="message-text">{{ row.message }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="创建者" width="100">
          <template #default="{ row }">
            <el-tag type="primary">{{ row.username || 'system' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="完成时间" width="180">
          <template #default="{ row }">
            <span class="time-text time-success">{{ row.completed_at ? formatTime(row.completed_at) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" @click="showDetail(row)">
                <el-icon><View /></el-icon>详情
              </el-button>
              <el-button size="small" type="primary" :disabled="row.status !== 'completed'" @click="downloadResult(row)">
                <el-icon><Download /></el-icon>下载
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="fetchTasks"
          @size-change="fetchTasks"
          layout="total, sizes, prev, pager, next, jumper"
        />
      </div>
    </Card>

    <!-- 任务详情弹窗 -->
    <el-dialog v-model="detailVisible" title="任务详情" width="700px" class="unified-dialog">
      <el-descriptions :column="2" border v-if="currentTask" class="modern-descriptions">
        <el-descriptions-item label="任务ID" :span="2">
          <span class="task-id">{{ currentTask.id }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <el-tag :type="taskTypeColors[currentTask.task_type] || 'primary'">
            {{ taskTypeLabels[currentTask.task_type] || currentTask.task_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusColors[currentTask.status]">
            {{ statusLabels[currentTask.status] }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进度" :span="2">
          <el-progress :percentage="currentTask.progress" :status="getProgressStatus(currentTask.status)" />
        </el-descriptions-item>
        <el-descriptions-item label="总集群数">{{ currentTask.total_items }}</el-descriptions-item>
        <el-descriptions-item label="已完成">{{ currentTask.completed_items }}</el-descriptions-item>
        <el-descriptions-item label="消息" :span="2">{{ currentTask.message }}</el-descriptions-item>
        <el-descriptions-item label="创建者">
          <el-tag type="primary">{{ currentTask.username || 'system' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间" :span="2">
          {{ currentTask.completed_at ? formatTime(currentTask.completed_at) : '尚未完成' }}
        </el-descriptions-item>
        <el-descriptions-item label="结果URL" :span="2" v-if="currentTask.result_url">
          <el-link :href="currentTask.result_url" target="_blank" type="primary">{{ currentTask.result_url }}</el-link>
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2" v-if="currentTask.error_message">
          <el-alert type="error" :closable="false" show-icon>
            <pre class="error-pre">{{ currentTask.error_message }}</pre>
          </el-alert>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="currentTask?.status !== 'completed'" @click="downloadResult(currentTask)">
          <el-icon><Download /></el-icon>下载结果
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>


<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, RefreshLeft, View, Download, Clock, List } from '@element-plus/icons-vue'
import axios from '@/utils/axios'
import { Card } from '@/components/common'
import { debounce } from 'lodash-es'

const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const detailVisible = ref(false)
const currentTask = ref(null)

const filters = reactive({ status: '', task_type: '' })

const statusColors = { pending: 'warning', processing: '', completed: 'success', failed: 'danger' }
const statusLabels = { pending: '等待中', processing: '进行中', completed: '已完成', failed: '失败' }

// 统一的任务类型映射（中文显示，英文值）
const TASK_TYPE_MAP = {
  operational: '运营分析',
  resource: '资源分析',
  monitoring: '监控分析',
  monitoring_bcc: 'BCC监控',
  monitoring_bos: 'BOS监控',
  monitoring_eip: 'EIP监控',
  eip: 'EIP分析',
  prometheus: '集群数据采集',
  prometheus_batch: '批量采集',
  prometheus_single: '单集群采集'
}

const taskTypeColors = {
  operational: 'warning', resource: 'success', monitoring: '',
  monitoring_bcc: '', monitoring_bos: '', monitoring_eip: 'info',
  eip: 'info', prometheus: 'danger', prometheus_batch: 'danger', prometheus_single: 'danger'
}

// 使用统一的映射表
const taskTypeLabels = TASK_TYPE_MAP

// 生成筛选下拉框选项（使用统一映射）
const taskTypeOptions = Object.entries(TASK_TYPE_MAP).map(([value, label]) => ({
  value,  // 英文值，发送给后端
  label   // 中文显示，用户看到的
}))

// 智能进度显示逻辑
function getProgressText(task) {
  const { status, completed_items, total_items, progress } = task
  
  // 已完成：显示"已完成"
  if (status === 'completed') {
    return '已完成'
  }
  
  // 失败：显示"失败"
  if (status === 'failed') {
    return '失败'
  }
  
  // 等待中：显示"等待中"
  if (status === 'pending') {
    return '等待中'
  }
  
  // 进行中：显示实际进度
  if (status === 'processing') {
    // 如果有具体的项目数，显示 "5/10"
    if (completed_items > 0 || total_items > 0) {
      return `${completed_items}/${total_items}`
    }
    // 否则显示百分比
    return `${progress}%`
  }
  
  return '-'
}

async function fetchTasks() {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const params = { skip, limit: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.task_type) params.task_type = filters.task_type
    const response = await axios.get('/api/v1/tasks', { params })
    tasks.value = response.tasks || response || []
    total.value = response.total || tasks.value.length
  } catch (error) {
    console.error('查询任务列表失败:', error)
    ElMessage.error('查询任务列表失败')
  } finally {
    loading.value = false
  }
}

// 防抖的fetchTasks函数（用于自动筛选）
const debouncedFetch = debounce(() => {
  fetchTasks()
}, 300)

// 监听筛选条件变化（自动筛选）
watch(
  () => [filters.status, filters.task_type],
  () => {
    // 重置到第一页
    currentPage.value = 1
    // 触发筛选（防抖）
    debouncedFetch()
  }
)

function resetFilters() {
  filters.status = ''
  filters.task_type = ''
  currentPage.value = 1
  fetchTasks() // 立即触发，不防抖
}

function showDetail(task) {
  currentTask.value = task
  detailVisible.value = true
}

async function downloadResult(task) {
  try {
    const taskId = typeof task === 'string' ? task : task.id
    const taskType = typeof task === 'string' ? currentTask.value?.task_type : task.task_type
    const resultUrl = typeof task === 'string' ? currentTask.value?.result_url : task.result_url
    
    if (resultUrl) {
      let downloadUrl = resultUrl
      if (resultUrl.startsWith('html_reports/')) {
        downloadUrl = `/api/v1/reports/proxy/${resultUrl}?download=true`
      } else if (!resultUrl.includes('download=')) {
        downloadUrl = resultUrl + (resultUrl.includes('?') ? '&' : '?') + 'download=true'
      }
      window.open(downloadUrl, '_blank')
      return
    }
    
    let downloadUrl = ''
    switch (taskType) {
      case 'operational': downloadUrl = `/api/v1/operational/download/${taskId}`; break
      case 'resource': downloadUrl = `/api/v1/resource/download/${taskId}`; break
      case 'monitoring': case 'monitoring_bcc': case 'monitoring_bos':
        downloadUrl = `/api/v1/monitoring/download/${taskId}`; break
      case 'eip': case 'monitoring_eip': downloadUrl = `/api/v1/eip/download/${taskId}`; break
      case 'prometheus': case 'prometheus_batch': case 'prometheus_single':
        const response = await axios.get(`/api/v1/prometheus/${taskId}/download`)
        if (response.download_url) { window.open(response.download_url, '_blank'); return }
        ElMessage.warning('下载链接不可用'); return
      default: ElMessage.warning(`不支持的任务类型: ${taskType}`); return
    }
    window.open(downloadUrl, '_blank')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

function getProgressStatus(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

onMounted(() => { fetchTasks() })
</script>


<style scoped>
.task-history-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  animation: slideInUp var(--duration-slow) var(--ease-out);
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));
  border-radius: var(--radius-lg);
  color: white;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-4);
}

.filter-select {
  min-width: 180px;
}

.card-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding: var(--spacing-4) 0 0;
  border-top: 1px solid var(--border-color);
  margin-top: var(--spacing-4);
}

/* 任务ID样式 */
.task-id {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: var(--font-size-sm);
  color: var(--color-primary-500);
}

/* 进度详情 */
.progress-detail {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-primary-500);
}

/* 消息文本 */
.message-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 时间文本 */
.time-text {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.time-success {
  color: var(--color-success);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: var(--spacing-2);
}

/* 错误信息 */
.error-pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: var(--font-size-sm);
}

/* 现代表格样式 */
.modern-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-elevated);
  --el-table-row-hover-bg-color: var(--bg-spotlight);
  --el-table-border-color: var(--border-color);
}

.modern-table :deep(.el-table__inner-wrapper::before) {
  background-color: var(--border-color);
}

.modern-table :deep(th.el-table__cell) {
  background-color: var(--bg-elevated);
  color: var(--text-primary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.modern-table :deep(td.el-table__cell) {
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.modern-table :deep(.el-table__row) {
  transition: background-color var(--transition-fast);
}

.modern-table :deep(.el-table__row:hover td.el-table__cell) {
  background-color: var(--bg-spotlight);
}

/* 弹窗样式 - 使用统一弹窗系统 */
.unified-dialog :deep(.el-dialog) {
  background-color: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
}

.unified-dialog :deep(.el-dialog__header) {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--border-color);
}

.unified-dialog :deep(.el-dialog__title) {
  color: var(--text-primary);
  font-weight: 600;
}

.unified-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-5);
}

.unified-dialog :deep(.el-dialog__footer) {
  padding: var(--spacing-4) var(--spacing-5);
  border-top: 1px solid var(--border-color);
}

/* 描述列表 */
.modern-descriptions :deep(.el-descriptions__label) {
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
  font-weight: 500;
}

.modern-descriptions :deep(.el-descriptions__content) {
  background-color: var(--bg-container);
  color: var(--text-primary);
}

.modern-descriptions :deep(.el-descriptions__cell) {
  border-color: var(--border-color);
}

/* 响应式 */
@media (max-width: 768px) {
  .filter-form {
    flex-direction: column;
    width: 100%;
  }
  
  .filter-form .el-form-item {
    margin-right: 0;
    width: 100%;
  }
}
</style>
