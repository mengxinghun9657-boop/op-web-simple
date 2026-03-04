<template>
  <div class="suggestion-review-page">
    <div class="page-header">
      <h1>规则建议审核</h1>
      <p class="subtitle">审核自动生成的路由规则建议</p>
    </div>

    <div class="content-container">
      <!-- 筛选和操作栏 -->
      <div class="filter-bar">
        <div class="filters">
          <el-select
            v-model="filters.intentType"
            placeholder="筛选意图类型"
            clearable
            class="filter-select"
            @change="loadSuggestions"
          >
            <el-option label="SQL查询" value="sql" />
            <el-option label="报告查询" value="rag_report" />
            <el-option label="知识查询" value="rag_knowledge" />
            <el-option label="对话" value="chat" />
          </el-select>

          <el-select
            v-model="filters.status"
            placeholder="筛选状态"
            clearable
            class="filter-select-small"
            @change="loadSuggestions"
          >
            <el-option label="待审核" value="pending" />
            <el-option label="已采纳" value="adopted" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </div>

        <div class="actions">
          <el-button
            type="primary"
            :disabled="selectedSuggestions.length === 0"
            @click="handleBatchApprove"
            class="action-btn"
          >
            <span class="btn-text-full">批量采纳 ({{ selectedSuggestions.length }})</span>
            <span class="btn-text-short">批量 ({{ selectedSuggestions.length }})</span>
          </el-button>
          <el-button @click="loadSuggestions" class="action-btn">
            <el-icon><Refresh /></el-icon>
            <span class="btn-text">刷新</span>
          </el-button>
        </div>
      </div>

      <!-- 建议列表表格 -->
      <div class="table-container">
        <el-table
          v-loading="loading"
          :data="suggestions"
          @selection-change="handleSelectionChange"
          class="suggestions-table"
        >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="pattern" label="查询模式" min-width="200">
          <template #default="{ row }">
            <div class="pattern-cell">
              <el-tag size="small" type="info">{{ row.suggested_intent }}</el-tag>
              <span class="pattern-text">{{ row.pattern }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.confidence * 100)"
              :color="getConfidenceColor(row.confidence)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>

        <el-table-column prop="support_count" label="支持数" width="90" align="center">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.support_count }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button size="small" @click="showEdit(row)" v-if="row.status === 'pending'">编辑</el-button>
            <el-button size="small" @click="showTest(row)" v-if="row.status === 'pending'">测试</el-button>
            <el-button
              size="small"
              type="success"
              @click="handleApprove(row)"
              v-if="row.status === 'pending'"
            >
              采纳
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleReject(row)"
              v-if="row.status === 'pending'"
            >
              拒绝
            </el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadSuggestions"
          @current-change="loadSuggestions"
        />
      </div>
    </div>

    <!-- 详情对话框 -->
    <SuggestionDetailDialog
      v-model="detailDialogVisible"
      :suggestion="currentSuggestion"
    />

    <!-- 编辑对话框 -->
    <SuggestionEditDialog
      v-model="editDialogVisible"
      :suggestion="currentSuggestion"
      @success="handleEditSuccess"
    />

    <!-- 测试对话框 -->
    <SuggestionTestDialog
      v-model="testDialogVisible"
      :suggestion="currentSuggestion"
    />

    <!-- 采纳确认对话框 -->
    <el-dialog
      v-model="approveDialogVisible"
      title="确认采纳规则建议"
      width="500px"
    >
      <div v-if="currentSuggestion">
        <p><strong>查询模式：</strong>{{ currentSuggestion.pattern }}</p>
        <p><strong>意图类型：</strong>{{ currentSuggestion.suggested_intent }}</p>
        <p><strong>置信度：</strong>{{ (currentSuggestion.confidence * 100).toFixed(1) }}%</p>
        <p><strong>支持数：</strong>{{ currentSuggestion.support_count }}</p>
        <el-alert
          title="采纳后将自动创建正式的路由规则并更新向量索引"
          type="info"
          :closable="false"
          style="margin-top: 16px"
        />
      </div>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmApprove" :loading="approving">
          确认采纳
        </el-button>
      </template>
    </el-dialog>

    <!-- 拒绝对话框 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝规则建议"
      width="500px"
    >
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="拒绝原因" required>
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入拒绝原因..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="rejecting">
          确认拒绝
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量采纳确认对话框 -->
    <el-dialog
      v-model="batchApproveDialogVisible"
      title="批量采纳规则建议"
      width="600px"
    >
      <div>
        <p>确认批量采纳以下 <strong>{{ selectedSuggestions.length }}</strong> 条规则建议？</p>
        <el-table :data="selectedSuggestions" max-height="300" style="margin-top: 16px">
          <el-table-column prop="pattern" label="查询模式" />
          <el-table-column prop="suggested_intent" label="意图类型" width="120" />
        </el-table>
        <el-alert
          title="批量采纳后将自动创建正式的路由规则并更新向量索引"
          type="warning"
          :closable="false"
          style="margin-top: 16px"
        />
      </div>
      <template #footer>
        <el-button @click="batchApproveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmBatchApprove" :loading="batchApproving">
          确认批量采纳
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getPendingSuggestions,
  approveSuggestion,
  rejectSuggestion,
  batchApproveSuggestions
} from '@/api/routing'
import SuggestionDetailDialog from '@/components/routing/SuggestionDetailDialog.vue'
import SuggestionEditDialog from '@/components/routing/SuggestionEditDialog.vue'
import SuggestionTestDialog from '@/components/routing/SuggestionTestDialog.vue'

// 状态
const loading = ref(false)
const suggestions = ref([])
const selectedSuggestions = ref([])
const currentSuggestion = ref(null)

// 筛选
const filters = reactive({
  intentType: '',
  status: 'pending'
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const detailDialogVisible = ref(false)
const editDialogVisible = ref(false)
const testDialogVisible = ref(false)
const approveDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const batchApproveDialogVisible = ref(false)

// 操作状态
const approving = ref(false)
const rejecting = ref(false)
const batchApproving = ref(false)

// 拒绝表单
const rejectForm = reactive({
  reason: ''
})

// 加载建议列表
const loadSuggestions = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      intent_type: filters.intentType || undefined,
      status: filters.status || undefined
    }
    
    const response = await getPendingSuggestions(params)
    
    if (response.success) {
      suggestions.value = response.data.list
      pagination.total = response.data.total
    } else {
      ElMessage.error(response.message || '加载失败')
    }
  } catch (error) {
    console.error('加载建议列表失败:', error)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedSuggestions.value = selection.filter(s => s.status === 'pending')
}

// 显示详情
const showDetail = (suggestion) => {
  currentSuggestion.value = suggestion
  detailDialogVisible.value = true
}

// 显示编辑
const showEdit = (suggestion) => {
  currentSuggestion.value = suggestion
  editDialogVisible.value = true
}

// 编辑成功
const handleEditSuccess = () => {
  loadSuggestions()
}

// 显示测试
const showTest = (suggestion) => {
  currentSuggestion.value = suggestion
  testDialogVisible.value = true
}

// 采纳建议
const handleApprove = (suggestion) => {
  currentSuggestion.value = suggestion
  approveDialogVisible.value = true
}

// 确认采纳
const confirmApprove = async () => {
  approving.value = true
  try {
    const response = await approveSuggestion(currentSuggestion.value.id)
    
    if (response.success) {
      ElMessage.success(`规则已采纳，创建的规则ID: ${response.data.created_rule_id}`)
      approveDialogVisible.value = false
      loadSuggestions()
    } else {
      ElMessage.error(response.message || '采纳失败')
    }
  } catch (error) {
    console.error('采纳建议失败:', error)
    ElMessage.error('采纳失败')
  } finally {
    approving.value = false
  }
}

// 拒绝建议
const handleReject = (suggestion) => {
  currentSuggestion.value = suggestion
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

// 确认拒绝
const confirmReject = async () => {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }
  
  rejecting.value = true
  try {
    const response = await rejectSuggestion(currentSuggestion.value.id, {
      reason: rejectForm.reason
    })
    
    if (response.success) {
      ElMessage.success('规则已拒绝')
      rejectDialogVisible.value = false
      loadSuggestions()
    } else {
      ElMessage.error(response.message || '拒绝失败')
    }
  } catch (error) {
    console.error('拒绝建议失败:', error)
    ElMessage.error('拒绝失败')
  } finally {
    rejecting.value = false
  }
}

// 批量采纳
const handleBatchApprove = () => {
  if (selectedSuggestions.value.length === 0) {
    ElMessage.warning('请选择要采纳的建议')
    return
  }
  batchApproveDialogVisible.value = true
}

// 确认批量采纳
const confirmBatchApprove = async () => {
  batchApproving.value = true
  try {
    const response = await batchApproveSuggestions({
      suggestion_ids: selectedSuggestions.value.map(s => s.id)
    })
    
    if (response.success) {
      ElMessage.success(
        `批量采纳完成：成功 ${response.data.success_count} 条，失败 ${response.data.failed_count} 条`
      )
      batchApproveDialogVisible.value = false
      loadSuggestions()
    } else {
      ElMessage.error(response.message || '批量采纳失败')
    }
  } catch (error) {
    console.error('批量采纳失败:', error)
    ElMessage.error('批量采纳失败')
  } finally {
    batchApproving.value = false
  }
}

// 工具函数
const getConfidenceColor = (confidence) => {
  if (confidence >= 0.9) return '#67c23a'
  if (confidence >= 0.7) return '#e6a23c'
  return '#f56c6c'
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    adopted: 'success',
    rejected: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待审核',
    adopted: '已采纳',
    rejected: '已拒绝'
  }
  return labels[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 初始化
onMounted(() => {
  loadSuggestions()
})
</script>

<style scoped>
.suggestion-review-page {
  padding: 16px;
  min-height: 100vh;
}

@media (min-width: 768px) {
  .suggestion-review-page {
    padding: 20px;
  }
}

@media (min-width: 1024px) {
  .suggestion-review-page {
    padding: 24px;
  }
}

.page-header {
  margin-bottom: 20px;
}

@media (min-width: 768px) {
  .page-header {
    margin-bottom: 24px;
  }
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

@media (min-width: 768px) {
  .page-header h1 {
    font-size: 24px;
  }
}

.subtitle {
  color: #475569;
  font-size: 13px;
}

@media (min-width: 768px) {
  .subtitle {
    font-size: 14px;
  }
}

.content-container {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

@media (min-width: 768px) {
  .content-container {
    padding: 20px;
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding: 24px;
  }
}

.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

@media (min-width: 768px) {
  .filter-bar {
    flex-direction: row;
    align-items: center;
    margin-bottom: 20px;
  }
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

@media (min-width: 640px) {
  .filters {
    flex-direction: row;
    flex-wrap: wrap;
  }
}

@media (min-width: 768px) {
  .filters {
    width: auto;
  }
}

.filter-select {
  width: 100%;
}

@media (min-width: 640px) {
  .filter-select {
    width: 180px;
  }
}

@media (min-width: 1024px) {
  .filter-select {
    width: 200px;
  }
}

.filter-select-small {
  width: 100%;
}

@media (min-width: 640px) {
  .filter-select-small {
    width: 130px;
  }
}

@media (min-width: 1024px) {
  .filter-select-small {
    width: 150px;
  }
}

.filter-bar .actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (min-width: 768px) {
  .filter-bar .actions {
    margin-left: auto;
    gap: 12px;
  }
}

.action-btn {
  min-height: 44px;
  flex: 1;
  min-width: 0;
}

@media (min-width: 640px) {
  .action-btn {
    flex: 0 1 auto;
  }
}

.btn-text {
  margin-left: 4px;
}

@media (max-width: 639px) {
  .btn-text {
    display: none;
  }
  
  .action-btn :deep(.el-icon) {
    margin-right: 0;
  }
}

.btn-text-full {
  display: none;
}

.btn-text-short {
  display: inline;
}

@media (min-width: 640px) {
  .btn-text-full {
    display: inline;
  }
  
  .btn-text-short {
    display: none;
  }
}

.table-container {
  overflow-x: auto;
  margin-bottom: 16px;
  -webkit-overflow-scrolling: touch;
}

@media (min-width: 768px) {
  .table-container {
    margin-bottom: 20px;
  }
}

.suggestions-table {
  min-width: 900px;
}

.pattern-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pattern-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  display: flex;
  justify-content: flex-end;
}
</style>
