<template>
  <div class="bento-card quick-note-card">
    <div class="bento-card-header">
      <div class="bento-card-title">
        <div class="bento-card-title-icon icon-bg-secondary">
          <el-icon :size="16"><ChatDotRound /></el-icon>
        </div>
        快捷备忘
      </div>
      <div class="note-actions">
        <span v-if="lastSaved" class="last-saved">{{ lastSaved }}</span>
        <el-button size="small" type="primary" @click="saveNote" :loading="saving" :disabled="!hasChanges">
          <el-icon><Check /></el-icon>保存
        </el-button>
      </div>
    </div>
    <div class="bento-card-body">
      <el-input
        v-model="noteContent"
        type="textarea"
        :rows="4"
        placeholder="输入备忘内容...（未来可与 AI 对话）"
        @input="hasChanges = true"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Check } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const noteContent = ref('')
const saving = ref(false)
const hasChanges = ref(false)
const lastSaved = ref('')

const loadNote = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/note')
    if (response.success) {
      noteContent.value = response.data.content || ''
      if (response.data.updated_at) {
        lastSaved.value = `上次保存: ${response.data.updated_at}`
      }
    }
  } catch (e) {
    console.error('加载备忘失败:', e)
  }
}

const saveNote = async () => {
  if (!hasChanges.value) return
  
  saving.value = true
  try {
    const response = await axios.post('/api/v1/dashboard/note', {
      content: noteContent.value
    })
    if (response.success) {
      hasChanges.value = false
      lastSaved.value = `上次保存: ${response.data.updated_at}`
      ElMessage.success('备忘保存成功')
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadNote()
})
</script>

<style scoped>
.quick-note-card {
  height: 100%;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.last-saved {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.quick-note-card :deep(.el-textarea__inner) {
  background: var(--bg-elevated);
  border-color: var(--border-color);
  color: var(--text-primary);
  resize: none;
}

.quick-note-card :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary-500);
}

.quick-note-card :deep(.el-textarea__inner::placeholder) {
  color: var(--text-tertiary);
}
</style>
