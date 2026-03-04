<template>
  <div class="draft-manager">
    <!-- 自动保存提示 -->
    <div v-if="autoSaveEnabled" class="auto-save-indicator">
      <el-icon :class="{ 'saving': isSaving }">
        <component :is="isSaving ? 'Loading' : 'CircleCheck'" />
      </el-icon>
      <span class="save-text">
        {{ isSaving ? '正在保存...' : lastSaveTime ? `已保存于 ${lastSaveTime}` : '自动保存已启用' }}
      </span>
    </div>

    <!-- 草稿列表对话框 -->
    <el-dialog
      v-model="draftsDialogVisible"
      title="草稿列表"
      width="700px"
      :close-on-click-modal="false"
    >
      <div v-loading="loading" class="drafts-list">
        <el-empty v-if="drafts.length === 0" description="暂无草稿" />
        
        <div
          v-for="draft in drafts"
          :key="draft.id"
          class="draft-item"
          @click="handleSelectDraft(draft)"
        >
          <div class="draft-header">
            <div class="draft-info">
              <span class="draft-pattern">{{ draft.draft_data.pattern || '未命名规则' }}</span>
              <el-tag
                v-if="draft.draft_data.intent_type"
                size="small"
                :type="getIntentTypeColor(draft.draft_data.intent_type)"
              >
                {{ getIntentTypeLabel(draft.draft_data.intent_type) }}
              </el-tag>
            </div>
            <div class="draft-actions">
              <el-button
                size="small"
                type="primary"
                @click.stop="handleRestoreDraft(draft)"
              >
                恢复
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click.stop="handleDeleteDraft(draft)"
              >
                删除
              </el-button>
            </div>
          </div>
          
          <div class="draft-meta">
            <span class="draft-time">
              <el-icon><Clock /></el-icon>
              {{ formatTime(draft.updated_at) }}
            </span>
            <span v-if="draft.draft_data.description" class="draft-desc">
              {{ draft.draft_data.description }}
            </span>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="draftsDialogVisible = false">关闭</el-button>
        <el-button type="danger" @click="handleClearAllDrafts">
          清空所有草稿
        </el-button>
      </template>
    </el-dialog>

    <!-- 恢复草稿确认对话框 -->
    <el-dialog
      v-model="restoreConfirmVisible"
      title="恢复草稿"
      width="400px"
    >
      <div class="restore-confirm">
        <el-icon class="warning-icon"><Warning /></el-icon>
        <p>当前表单有未保存的内容，恢复草稿将覆盖这些内容。是否继续？</p>
      </div>
      
      <template #footer>
        <el-button @click="restoreConfirmVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRestore">
          确认恢复
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, CircleCheck, Clock, Warning } from '@element-plus/icons-vue'
import { saveDraft, getDrafts, deleteDraft } from '@/api/routing-assistant'
import { throttle } from '@/utils/debounce'

const props = defineProps({
  ruleData: {
    type: Object,
    required: true
  },
  autoSaveInterval: {
    type: Number,
    default: 30000 // 30秒
  },
  autoSaveEnabled: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['restore', 'save-success'])

// 状态
const loading = ref(false)
const isSaving = ref(false)
const drafts = ref([])
const draftsDialogVisible = ref(false)
const restoreConfirmVisible = ref(false)
const selectedDraft = ref(null)
const lastSaveTime = ref('')
const autoSaveTimer = ref(null)
const localStorageKey = 'routing_rule_draft_local'

// 计算属性
const hasUnsavedChanges = computed(() => {
  return props.ruleData.pattern || props.ruleData.intent_type || props.ruleData.description
})

// 节流保存函数（30秒）
const throttledSave = throttle(() => {
  saveDraftToServer()
  saveDraftToLocal()
}, props.autoSaveInterval)

// 方法
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleString('zh-CN')
}

const getIntentTypeLabel = (intentType) => {
  const labels = {
    sql: 'SQL查询',
    rag_knowledge: '知识库检索',
    rag_report: '报告检索',
    chat: '普通对话'
  }
  return labels[intentType] || intentType
}

const getIntentTypeColor = (intentType) => {
  const colors = {
    sql: 'primary',
    rag_knowledge: 'success',
    rag_report: 'warning',
    chat: 'info'
  }
  return colors[intentType] || ''
}

// 保存草稿到服务器
const saveDraftToServer = async () => {
  if (!hasUnsavedChanges.value) return
  
  isSaving.value = true
  try {
    const response = await saveDraft({
      draft_data: props.ruleData
    })
    
    if (response.success) {
      lastSaveTime.value = new Date().toLocaleTimeString('zh-CN')
      emit('save-success')
    }
  } catch (error) {
    console.error('保存草稿失败:', error)
  } finally {
    isSaving.value = false
  }
}

// 保存草稿到本地存储
const saveDraftToLocal = () => {
  if (!hasUnsavedChanges.value) return
  
  try {
    const draftData = {
      ...props.ruleData,
      savedAt: new Date().toISOString()
    }
    localStorage.setItem(localStorageKey, JSON.stringify(draftData))
  } catch (error) {
    console.error('保存本地草稿失败:', error)
  }
}

// 从本地存储加载草稿
const loadDraftFromLocal = () => {
  try {
    const draftStr = localStorage.getItem(localStorageKey)
    if (draftStr) {
      return JSON.parse(draftStr)
    }
  } catch (error) {
    console.error('加载本地草稿失败:', error)
  }
  return null
}

// 清除本地草稿
const clearLocalDraft = () => {
  try {
    localStorage.removeItem(localStorageKey)
  } catch (error) {
    console.error('清除本地草稿失败:', error)
  }
}

// 加载草稿列表
const loadDrafts = async () => {
  loading.value = true
  try {
    const response = await getDrafts()
    if (response.success) {
      drafts.value = response.data || []
    }
  } catch (error) {
    console.error('加载草稿列表失败:', error)
    ElMessage.error('加载草稿列表失败')
  } finally {
    loading.value = false
  }
}

// 显示草稿列表
const showDrafts = () => {
  loadDrafts()
  draftsDialogVisible.value = true
}

// 选择草稿
const handleSelectDraft = (draft) => {
  selectedDraft.value = draft
}

// 恢复草稿
const handleRestoreDraft = (draft) => {
  if (hasUnsavedChanges.value) {
    selectedDraft.value = draft
    restoreConfirmVisible.value = true
  } else {
    confirmRestore()
  }
}

// 确认恢复
const confirmRestore = () => {
  if (selectedDraft.value) {
    emit('restore', selectedDraft.value.draft_data)
    draftsDialogVisible.value = false
    restoreConfirmVisible.value = false
    ElMessage.success('草稿已恢复')
  }
}

// 删除草稿
const handleDeleteDraft = async (draft) => {
  try {
    await ElMessageBox.confirm('确认删除此草稿？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const response = await deleteDraft(draft.id)
    if (response.success) {
      ElMessage.success('草稿已删除')
      loadDrafts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除草稿失败:', error)
      ElMessage.error('删除草稿失败')
    }
  }
}

// 清空所有草稿
const handleClearAllDrafts = async () => {
  try {
    await ElMessageBox.confirm('确认清空所有草稿？此操作不可恢复。', '确认清空', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 逐个删除所有草稿
    for (const draft of drafts.value) {
      await deleteDraft(draft.id)
    }
    
    ElMessage.success('所有草稿已清空')
    loadDrafts()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空草稿失败:', error)
      ElMessage.error('清空草稿失败')
    }
  }
}

// 启动自动保存
const startAutoSave = () => {
  if (!props.autoSaveEnabled) return
  
  // 使用节流函数，不再需要setInterval
  // 监听数据变化时会自动触发节流保存
}

// 停止自动保存
const stopAutoSave = () => {
  // 节流函数会自动管理，无需手动清理
}

// 检查本地草稿
const checkLocalDraft = () => {
  const localDraft = loadDraftFromLocal()
  if (localDraft && !hasUnsavedChanges.value) {
    ElMessageBox.confirm(
      `检测到未保存的草稿（保存于 ${formatTime(localDraft.savedAt)}），是否恢复？`,
      '恢复草稿',
      {
        confirmButtonText: '恢复',
        cancelButtonText: '忽略',
        type: 'info'
      }
    ).then(() => {
      emit('restore', localDraft)
      clearLocalDraft()
    }).catch(() => {
      clearLocalDraft()
    })
  }
}

// 监听规则数据变化（使用节流保存）
watch(() => props.ruleData, () => {
  if (props.autoSaveEnabled && hasUnsavedChanges.value) {
    throttledSave()
  } else {
    // 即使自动保存未启用，也保存到本地
    saveDraftToLocal()
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  checkLocalDraft()
  startAutoSave()
})

onUnmounted(() => {
  stopAutoSave()
  if (hasUnsavedChanges.value) {
    saveDraftToLocal()
  }
})

// 暴露方法给父组件
defineExpose({
  showDrafts,
  saveDraftToServer,
  saveDraftToLocal,
  clearLocalDraft
})
</script>

<style scoped>
.draft-manager {
  position: relative;
}

.auto-save-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 12px;
}

.auto-save-indicator .el-icon {
  font-size: 14px;
  color: #67c23a;
}

.auto-save-indicator .el-icon.saving {
  color: #409eff;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.save-text {
  flex: 1;
}

.drafts-list {
  max-height: 500px;
  overflow-y: auto;
}

.draft-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.draft-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.draft-item:last-child {
  margin-bottom: 0;
}

.draft-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.draft-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.draft-pattern {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.draft-actions {
  display: flex;
  gap: 8px;
}

.draft-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.draft-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.draft-desc {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.restore-confirm {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.warning-icon {
  font-size: 32px;
  color: #e6a23c;
}

.restore-confirm p {
  flex: 1;
  margin: 0;
  color: #606266;
  line-height: 1.6;
}
</style>
