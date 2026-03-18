<template>
  <div class="custom-templates">
    <div class="templates-header">
      <span class="header-title">
        <el-icon><Collection /></el-icon>
        我的模板
      </span>
      <el-button type="primary" size="small" @click="showSaveDialog">
        <el-icon><Plus /></el-icon>
        保存当前查询
      </el-button>
    </div>

    <!-- 模板列表 -->
    <div v-if="templates.length > 0" class="templates-list">
      <div
        v-for="(template, index) in templates"
        :key="template.id"
        class="template-item"
      >
        <div class="template-content" @click="loadTemplate(template)">
          <div class="template-header">
            <span class="template-name">{{ template.name }}</span>
            <el-tag size="small" type="info">{{ formatDate(template.timestamp) }}</el-tag>
          </div>
          <div class="template-iql">{{ template.iql }}</div>
          <div v-if="template.description" class="template-desc">{{ template.description }}</div>
        </div>
        <div class="template-actions">
          <el-button
            type="primary"
            size="small"
            link
            @click="loadTemplate(template)"
          >
            <el-icon><Select /></el-icon>
            使用
          </el-button>
          <el-button
            type="danger"
            size="small"
            link
            @click="deleteTemplate(index)"
          >
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="暂无自定义模板"
      :image-size="80"
    >
      <el-button type="primary" @click="showSaveDialog">
        <el-icon><Plus /></el-icon>
        创建第一个模板
      </el-button>
    </el-empty>

    <!-- 保存模板对话框 -->
    <el-dialog
      v-model="saveDialogVisible"
      title="保存查询模板"
      width="500px"
      class="unified-dialog"
      append-to-body
    >
      <el-form :model="newTemplate" label-width="80px">
        <el-form-item label="模板名称" required>
          <el-input
            v-model="newTemplate.name"
            placeholder="例如：本月已完成任务"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newTemplate.description"
            type="textarea"
            :rows="2"
            placeholder="可选：添加模板说明"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="IQL语句">
          <el-input
            v-model="newTemplate.iql"
            type="textarea"
            :rows="4"
            readonly
            class="iql-preview"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!newTemplate.name || !newTemplate.iql"
          @click="saveTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Plus, Select, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  currentIql: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['load'])

const STORAGE_KEY = 'custom_iql_templates'
const MAX_TEMPLATES = 20

const templates = ref([])
const saveDialogVisible = ref(false)
const newTemplate = ref({
  name: '',
  description: '',
  iql: ''
})

/**
 * 从 localStorage 加载模板
 */
const loadTemplates = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      templates.value = JSON.parse(stored)
    }
  } catch (error) {
    console.warn('加载自定义模板失败:', error)
    templates.value = []
  }
}

/**
 * 保存模板到 localStorage
 */
const saveTemplates = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates.value))
  } catch (error) {
    console.warn('保存自定义模板失败:', error)
    ElMessage.error('保存失败，请检查浏览器存储空间')
  }
}

/**
 * 显示保存对话框
 */
const showSaveDialog = () => {
  if (!props.currentIql) {
    ElMessage.warning('请先输入IQL查询语句')
    return
  }

  newTemplate.value = {
    name: '',
    description: '',
    iql: props.currentIql
  }
  saveDialogVisible.value = true
}

/**
 * 保存模板
 */
const saveTemplate = () => {
  if (!newTemplate.value.name || !newTemplate.value.iql) {
    ElMessage.warning('请填写模板名称')
    return
  }

  // 检查是否超过最大数量
  if (templates.value.length >= MAX_TEMPLATES) {
    ElMessage.warning(`最多只能保存 ${MAX_TEMPLATES} 个模板`)
    return
  }

  // 检查名称是否重复
  const exists = templates.value.some(t => t.name === newTemplate.value.name)
  if (exists) {
    ElMessage.warning('模板名称已存在，请使用其他名称')
    return
  }

  const template = {
    id: Date.now(),
    name: newTemplate.value.name,
    description: newTemplate.value.description,
    iql: newTemplate.value.iql,
    timestamp: Date.now()
  }

  templates.value.unshift(template)
  saveTemplates()
  saveDialogVisible.value = false
  ElMessage.success('模板保存成功')
}

/**
 * 加载模板
 */
const loadTemplate = (template) => {
  emit('load', template.iql)
  ElMessage.success(`已加载模板：${template.name}`)
}

/**
 * 删除模板
 */
const deleteTemplate = async (index) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个模板吗？',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    templates.value.splice(index, 1)
    saveTemplates()
    ElMessage.success('模板已删除')
  } catch {
    // 用户取消
  }
}

/**
 * 格式化日期
 */
const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 小于1小时
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return minutes < 1 ? '刚刚' : `${minutes}分钟前`
  }
  
  // 小于24小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}小时前`
  }
  
  // 小于7天
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}天前`
  }
  
  // 显示完整日期
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.custom-templates {
  width: 100%;
}

.templates-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-4);
  padding-bottom: var(--spacing-3);
  border-bottom: 2px solid var(--border-color);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
}

.header-title .el-icon {
  color: var(--color-primary-500);
}

.templates-header .el-button {
  transition: all var(--transition-fast);
}

.templates-header .el-button:hover {
  transform: translateY(-1px);
}

.templates-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  max-height: 400px;
  overflow-y: auto;
  padding-right: var(--spacing-2);
}

.template-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8), rgba(249, 250, 251, 0.8));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.template-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, var(--color-primary-500), var(--color-secondary-500));
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.template-item:hover {
  border-color: var(--color-primary-400);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.12);
  transform: translateY(-2px);
}

.template-item:hover::before {
  opacity: 1;
}

.template-content {
  flex: 1;
  cursor: pointer;
  min-width: 0;
}

.template-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.template-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.template-iql {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: var(--font-size-sm);
  color: var(--color-primary-600);
  background: rgba(64, 158, 255, 0.05);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-left: 2px solid var(--color-primary-300);
}

.template-desc {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: 1.5;
}

.template-actions {
  display: flex;
  gap: var(--spacing-2);
  flex-shrink: 0;
}

.template-actions .el-button {
  transition: all var(--transition-fast);
}

.template-actions .el-button:hover {
  transform: scale(1.05);
}

/* 保存对话框 - 使用统一弹窗系统 */
.unified-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.12);
}

.unified-dialog :deep(.el-dialog__header) {
  border-bottom: 2px solid var(--border-color);
  padding: var(--spacing-5) var(--spacing-6);
}

.unified-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  font-size: var(--font-size-lg);
}

.unified-dialog :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-secondary);
}

.iql-preview :deep(.el-textarea__inner) {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: var(--font-size-sm);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

/* 滚动条样式 */
.templates-list::-webkit-scrollbar {
  width: 6px;
}

.templates-list::-webkit-scrollbar-track {
  background: var(--bg-elevated);
  border-radius: 3px;
}

.templates-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
  transition: background var(--transition-fast);
}

.templates-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
</style>
