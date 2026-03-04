<template>
  <div class="alert-list-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">硬件告警管理</h1>
      <p class="page-description">实时监控硬件告警,快速定位和诊断问题</p>
    </div>

    <!-- 筛选器 -->
    <el-card class="filter-card" shadow="never">
      <el-form :model="filters" inline>
        <el-form-item label="告警类型">
          <el-select
            v-model="filters.alert_type"
            placeholder="全部"
            clearable
            style="width: 180px"
          >
            <el-option
              v-for="type in filterOptions.alert_types"
              :key="type"
              :label="type"
              :value="type"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="严重程度">
          <el-select
            v-model="filters.severity"
            placeholder="全部"
            clearable
            style="width: 150px"
          >
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </el-form-item>

        <el-form-item label="组件类型">
          <el-select
            v-model="filters.component"
            placeholder="全部"
            clearable
            style="width: 150px"
          >
            <el-option
              v-for="comp in filterOptions.components"
              :key="comp"
              :label="comp"
              :value="comp"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="处理状态">
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 150px"
          >
            <el-option
              v-for="stat in filterOptions.statuses"
              :key="stat"
              :label="statusLabels[stat]"
              :value="stat"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 360px"
            @change="handleDateRangeChange"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card class="table-card" shadow="never">
      <!-- 操作栏 -->
      <div class="table-toolbar" style="margin-bottom: 16px;">
        <el-button
          type="warning"
          :icon="Notification"
          @click="handleBatchResendNotifications"
          :loading="batchResending"
        >
          批量补发通知
        </el-button>
        <el-tooltip
          content="为所有未发送通知的告警补发webhook通知（适用于首次部署时webhook未配置的情况）"
          placement="top"
        >
          <el-icon style="margin-left: 8px; cursor: help;">
            <QuestionFilled />
          </el-icon>
        </el-tooltip>
      </div>

      <!-- 首次加载：显示骨架屏 -->
      <el-skeleton 
        v-if="loading && !alertList.length" 
        :rows="10" 
        animated 
        class="skeleton-table"
      />
      
      <!-- 数据加载完成：显示表格 -->
      <el-table
        v-else-if="alertList.length > 0"
        v-loading="loading"
        :data="alertList"
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
        class="alert-table"
        aria-label="硬件告警列表"
      >
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="alert_type" label="告警类型" min-width="180" />
        
        <el-table-column prop="component" label="组件" width="120">
          <template #default="{ row }">
            <el-tag :type="getComponentTagType(row.component)" size="small">
              {{ row.component }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="severity" label="严重程度" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getSeverityTagType(row.severity)" 
              size="small"
              :aria-label="`严重程度：${getSeverityLabel(row.severity)}`"
            >
              {{ getSeverityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="ip" label="节点IP" width="140" />
        
        <el-table-column prop="cluster_id" label="集群ID" width="150" show-overflow-tooltip />
        
        <el-table-column prop="timestamp" label="发生时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.timestamp) }}
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusTagType(row.status)" 
              size="small"
              :class="{ 'resolved-tag': row.status === 'resolved' }"
            >
              {{ statusLabels[row.status] }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="诊断" width="80" align="center">
          <template #default="{ row }">
            <el-icon 
              v-if="row.has_diagnosis" 
              color="#67C23A" 
              :size="18"
              aria-label="已诊断"
            >
              <CircleCheck />
            </el-icon>
            <el-icon 
              v-else 
              color="#909399" 
              :size="18"
              aria-label="未诊断"
            >
              <CircleClose />
            </el-icon>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click.stop="handleViewDetail(row.id)"
              aria-label="查看告警详情"
              class="action-button"
            >
              查看详情
            </el-button>
            <el-button
              type="success"
              size="small"
              :icon="Edit"
              @click.stop="handleChangeStatus(row)"
              aria-label="修改状态"
            >
              修改状态
            </el-button>
            <el-button
              type="info"
              size="small"
              :icon="EditPen"
              @click.stop="handleAddNote(row)"
              aria-label="添加备注"
            >
              添加备注
            </el-button>
            <el-button
              link
              type="warning"
              size="small"
              @click.stop="handleDiagnose(row.id)"
              :loading="diagnosingIds.includes(row.id)"
              aria-label="重新诊断告警"
            >
              重新诊断
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 空状态 -->
      <el-empty
        v-else-if="!loading && !alertList.length"
        :image-size="200"
      >
        <template #description>
          <p class="empty-title">暂无告警数据</p>
          <p class="empty-subtitle">
            {{ hasFilters ? '尝试调整筛选条件' : '系统运行正常，暂无硬件告警' }}
          </p>
        </template>
        
        <template #default>
          <el-button 
            v-if="hasFilters" 
            type="primary" 
            @click="handleReset"
          >
            <el-icon><Refresh /></el-icon>
            清除筛选
          </el-button>
          <el-button 
            v-else
            @click="fetchAlerts"
          >
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </template>
      </el-empty>

      <!-- 分页 -->
      <div v-if="alertList.length > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 状态编辑对话框 -->
    <el-dialog
      v-model="statusDialogVisible"
      title="修改告警状态"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="statusFormRef"
        :model="statusForm"
        label-width="100px"
        @submit.prevent="handleStatusSubmit"
      >
        <el-form-item label="告警类型">
          <el-input v-model="statusForm.alertType" readonly />
        </el-form-item>
        
        <el-form-item label="当前状态">
          <el-tag :type="getStatusTagType(statusForm.currentStatus)">
            {{ statusLabels[statusForm.currentStatus] }}
          </el-tag>
        </el-form-item>
        
        <el-form-item label="新状态" required>
          <el-select v-model="statusForm.newStatus" style="width: 100%">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已诊断" value="diagnosed" />
            <el-option label="已通知" value="notified" />
            <el-option label="已处理" value="resolved" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleStatusCancel">取消</el-button>
          <el-button type="primary" @click="handleStatusSubmit">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 备注编辑对话框 -->
    <el-dialog
      v-model="noteDialogVisible"
      title="添加告警备注"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="noteFormRef"
        :model="noteForm"
        label-width="100px"
        @submit.prevent="handleNoteSubmit"
      >
        <el-form-item label="告警类型">
          <el-input v-model="noteForm.alertType" readonly />
        </el-form-item>
        
        <el-form-item label="备注内容" required>
          <el-input
            v-model="noteForm.notes"
            type="textarea"
            :rows="6"
            placeholder="请输入备注内容，如：问题描述、处理过程、解决方案等"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleNoteCancel">取消</el-button>
          <el-button type="primary" @click="handleNoteSubmit">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, CircleCheck, CircleClose, Notification, QuestionFilled, Edit, EditPen } from '@element-plus/icons-vue'
import { getAlerts, getFilterOptions, diagnoseAlert, batchResendNotifications, updateAlertStatus } from '@/api/alerts'

const router = useRouter()

// 状态标签映射
const statusLabels = {
  pending: '待处理',
  processing: '处理中',
  diagnosed: '已诊断',
  notified: '已通知',
  failed: '失败',
  resolved: '已处理'
}

// 数据
const loading = ref(false)
const alertList = ref([])
const filterOptions = reactive({
  alert_types: [],
  components: [],
  clusters: [],
  severity_levels: [],
  statuses: []
})

// 筛选条件
const filters = reactive({
  alert_type: '',
  severity: '',
  component: '',
  status: '',
  start_time: '',
  end_time: ''
})

const dateRange = ref([])

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 正在诊断的告警ID列表
const diagnosingIds = ref([])

// 批量补发通知状态
const batchResending = ref(false)

// 状态编辑对话框
const statusDialogVisible = ref(false)
const statusForm = reactive({
  alertId: null,
  alertType: '',
  currentStatus: '',
  newStatus: ''
})

// 备注编辑对话框
const noteDialogVisible = ref(false)
const noteForm = reactive({
  alertId: null,
  alertType: '',
  notes: ''
})

const statusFormRef = ref(null)
const noteFormRef = ref(null)

// 检查是否有筛选条件
const hasFilters = computed(() => {
  return !!(
    filters.alert_type ||
    filters.severity ||
    filters.component ||
    filters.status ||
    filters.start_time ||
    filters.end_time
  )
})

// 获取严重程度标签文本
const getSeverityLabel = (severity) => {
  const labels = {
    critical: '严重',
    warning: '警告',
    info: '信息'
  }
  return labels[severity] || severity
}

// 获取筛选选项
const fetchFilterOptions = async () => {
  try {
    const response = await getFilterOptions()
    if (response.success) {
      Object.assign(filterOptions, response.data)
    }
  } catch (error) {
    console.error('获取筛选选项失败:', error)
  }
}

// 获取告警列表
const fetchAlerts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...filters
    }
    
    const response = await getAlerts(params)
    if (response.success) {
      alertList.value = response.data.list
      pagination.total = response.data.total
    }
  } catch (error) {
    console.error('获取告警列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理时间范围变化
const handleDateRangeChange = (value) => {
  if (value && value.length === 2) {
    filters.start_time = value[0].toISOString()
    filters.end_time = value[1].toISOString()
  } else {
    filters.start_time = ''
    filters.end_time = ''
  }
}

// 查询
const handleSearch = () => {
  pagination.page = 1
  fetchAlerts()
}

// 重置
const handleReset = () => {
  Object.assign(filters, {
    alert_type: '',
    severity: '',
    component: '',
    status: '',
    start_time: '',
    end_time: ''
  })
  dateRange.value = []
  pagination.page = 1
  fetchAlerts()
}

// 分页变化
const handleSizeChange = () => {
  pagination.page = 1
  fetchAlerts()
}

const handlePageChange = () => {
  fetchAlerts()
}

// 查看详情
const handleViewDetail = (id) => {
  router.push(`/alerts/${id}`)
}

// 行点击
const handleRowClick = (row) => {
  handleViewDetail(row.id)
}

// 重新诊断
const handleDiagnose = async (id) => {
  diagnosingIds.value.push(id)
  try {
    const response = await diagnoseAlert(id, { force: true })
    if (response.success) {
      ElMessage.success('诊断任务已创建')
      // 3秒后刷新列表
      setTimeout(() => {
        fetchAlerts()
      }, 3000)
    }
  } catch (error) {
    console.error('触发诊断失败:', error)
  } finally {
    diagnosingIds.value = diagnosingIds.value.filter(item => item !== id)
  }
}

// 批量补发通知
const handleBatchResendNotifications = async () => {
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      '此操作将为所有未发送通知的告警补发webhook通知。是否继续？',
      '批量补发通知',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    batchResending.value = true
    const response = await batchResendNotifications()
    
    if (response.success) {
      const { total, success, failed } = response.data
      if (success > 0) {
        ElMessage.success(`批量补发完成：成功 ${success} 个，失败 ${failed} 个，共 ${total} 个`)
      } else if (total === 0) {
        ElMessage.info('没有需要补发的告警通知')
      } else {
        ElMessage.warning(`批量补发失败：失败 ${failed} 个，共 ${total} 个`)
      }
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量补发通知失败:', error)
      ElMessage.error('批量补发通知失败')
    }
  } finally {
    batchResending.value = false
  }
}

// 获取组件标签类型
const getComponentTagType = (component) => {
  const typeMap = {
    GPU: 'danger',
    Memory: 'warning',
    CPU: 'success',
    Motherboard: 'info'
  }
  return typeMap[component] || ''
}

// 获取严重程度标签类型
const getSeverityTagType = (severity) => {
  const typeMap = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[severity] || ''
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    pending: 'info',
    processing: 'warning',
    diagnosed: 'success',
    notified: 'success',
    failed: 'danger',
    resolved: 'success'
  }
  return typeMap[status] || ''
}

// 修改状态
const handleChangeStatus = (alert) => {
  statusForm.alertId = alert.id
  statusForm.alertType = alert.alert_type
  statusForm.currentStatus = alert.status
  statusForm.newStatus = alert.status === 'resolved' ? 'pending' : 'resolved'
  statusDialogVisible.value = true
}

// 添加备注
const handleAddNote = (alert) => {
  noteForm.alertId = alert.id
  noteForm.alertType = alert.alert_type
  noteForm.notes = ''
  noteDialogVisible.value = true
}

// 提交状态更新
const handleStatusSubmit = async () => {
  try {
    const response = await updateAlertStatus(statusForm.alertId, {
      status: statusForm.newStatus
    })
    
    if (response.success) {
      ElMessage.success('告警状态更新成功')
      statusDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    console.error('更新告警状态失败:', error)
    ElMessage.error('更新告警状态失败')
  }
}

// 提交备注
const handleNoteSubmit = async () => {
  try {
    const response = await updateAlertStatus(noteForm.alertId, {
      resolution_notes: noteForm.notes
    })
    
    if (response.success) {
      ElMessage.success('备注添加成功')
      noteDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    console.error('添加备注失败:', error)
    ElMessage.error('添加备注失败')
  }
}

// 取消状态编辑
const handleStatusCancel = () => {
  statusDialogVisible.value = false
  statusForm.alertId = null
  statusForm.alertType = ''
  statusForm.currentStatus = ''
  statusForm.newStatus = ''
}

// 取消备注编辑
const handleNoteCancel = () => {
  noteDialogVisible.value = false
  noteForm.alertId = null
  noteForm.alertType = ''
  noteForm.notes = ''
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 初始化
onMounted(() => {
  fetchFilterOptions()
  fetchAlerts()
})
</script>

<style scoped>
.alert-list-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px 0;
}

.page-description {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-card :deep(.el-card__body) {
  padding: 20px;
}

.table-card :deep(.el-card__body) {
  padding: 20px;
}

.alert-table {
  cursor: pointer;
}

.alert-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.alert-table :deep(.el-table__row:hover) {
  background-color: #f8fafc;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 操作按钮样式优化 */
.action-button {
  margin-right: 8px;
  font-weight: 500;
}

/* 确保按钮文字清晰可见 */
.alert-table :deep(.el-button--primary) {
  background-color: #409eff;
  border-color: #409eff;
  color: #ffffff;
}

.alert-table :deep(.el-button--primary:hover) {
  background-color: #66b1ff;
  border-color: #66b1ff;
  color: #ffffff;
}

.alert-table :deep(.el-button--primary:active) {
  background-color: #3a8ee6;
  border-color: #3a8ee6;
  color: #ffffff;
}

/* 已处理状态特殊样式 */
.resolved-tag {
  background-color: #67c23a !important;
  border-color: #67c23a !important;
  color: #ffffff !important;
}

/* 对话框样式 */
.dialog-footer {
  text-align: right;
}
</style>
