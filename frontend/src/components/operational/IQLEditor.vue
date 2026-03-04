<template>
  <div class="iql-editor">
    <el-form-item label="IQL 查询语句">
      <div class="editor-wrapper">
        <el-input
          ref="inputRef"
          v-model="localValue"
          type="textarea"
          :rows="6"
          :autosize="{ minRows: 6, maxRows: 12 }"
          resize="both"
          placeholder='例如: 最后修改时间 > "2025-01-01" AND 流程状态 = "已完成"'
          @input="handleInput"
          @blur="handleBlur"
        />
        
        <!-- 语法验证提示 -->
        <div v-if="validation.errors.length > 0" class="validation-errors">
          <el-alert
            v-for="(error, index) in validation.errors"
            :key="index"
            type="error"
            :closable="false"
            show-icon
          >
            {{ error }}
          </el-alert>
        </div>
        
        <!-- 语法帮助按钮 -->
        <div class="editor-actions">
          <el-popover trigger="click" width="600" placement="right">
            <template #reference>
              <el-button link type="primary">
                <el-icon><QuestionFilled /></el-icon>
                语法帮助
              </el-button>
            </template>
            <IQLSyntaxHelp />
          </el-popover>
          
          <el-button link type="primary" @click="formatIQL">
            <el-icon><MagicStick /></el-icon>
            格式化
          </el-button>
        </div>
      </div>
    </el-form-item>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { validateIQL } from '@/utils/iqlGenerator'
import { debounce } from 'lodash-es'
import { QuestionFilled, MagicStick } from '@element-plus/icons-vue'
import IQLSyntaxHelp from './IQLSyntaxHelp.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)
const localValue = ref(props.modelValue || '')

// 语法验证结果
const validation = ref({ valid: true, errors: [] })

// 防抖的验证函数
const debouncedValidate = debounce(() => {
  validation.value = validateIQL(localValue.value)
}, 500)

const handleInput = () => {
  emit('update:modelValue', localValue.value)
  debouncedValidate()
}

const handleBlur = () => {
  // 立即验证
  validation.value = validateIQL(localValue.value)
}

const formatIQL = () => {
  // 简单的格式化：在AND/OR前后添加换行
  let formatted = localValue.value
  formatted = formatted.replace(/\s+AND\s+/gi, '\nAND ')
  formatted = formatted.replace(/\s+OR\s+/gi, '\nOR ')
  localValue.value = formatted
  emit('update:modelValue', formatted)
}

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  if (newVal !== localValue.value) {
    localValue.value = newVal || ''
  }
})
</script>

<style scoped>
.iql-editor {
  width: 100%;
}

.editor-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  width: 100%; /* 确保占满父容器宽度 */
}

.editor-wrapper :deep(.el-textarea) {
  position: relative;
  width: 100%; /* 确保textarea占满宽度 */
}

.editor-wrapper :deep(.el-textarea__inner) {
  min-height: 150px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  border-radius: var(--radius-lg);
  border: 2px solid var(--border-color);
  transition: all var(--transition-fast);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(249, 250, 251, 0.9));
  width: 100%; /* 确保输入框占满宽度 */
}

.editor-wrapper :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary-300);
}

.editor-wrapper :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
  background: white;
}

.validation-errors {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.validation-errors :deep(.el-alert) {
  border-radius: var(--radius-md);
}

.editor-actions {
  display: flex;
  gap: var(--spacing-3);
  align-items: center;
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--border-color);
}

/* 修复按钮对比度问题 */
.editor-actions .el-button {
  transition: all var(--transition-fast);
  color: var(--color-primary-600); /* 增强文字颜色 */
  font-weight: 500;
}

.editor-actions .el-button:hover {
  transform: translateY(-1px);
  color: var(--color-primary-700); /* hover时更深 */
  background-color: var(--color-primary-50); /* 添加浅色背景 */
}

/* 深色模式下的按钮样式 */
:deep(.dark) .editor-actions .el-button {
  color: var(--color-primary-400);
}

:deep(.dark) .editor-actions .el-button:hover {
  color: var(--color-primary-300);
  background-color: rgba(64, 158, 255, 0.1);
}
</style>
