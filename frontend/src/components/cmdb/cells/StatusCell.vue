<template>
  <div class="status-cell" @click.stop>
    <span
      class="glass-tag"
      :class="statusClass"
    >
      {{ displayValue }}
    </span>
    <el-icon
      v-if="displayValue && displayValue !== '-'"
      class="copy-icon"
      @click="copyToClipboard"
    >
      <DocumentCopy />
    </el-icon>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'

const props = defineProps({
  row: {
    type: Object,
    required: true
  },
  fieldConfig: {
    type: Object,
    required: true
  }
})

const displayValue = computed(() => {
  return props.row[props.fieldConfig.key] || '-'
})

const statusClass = computed(() => {
  const value = props.row[props.fieldConfig.key]

  // 根据字段配置的状态映射
  if (props.fieldConfig.statusMap) {
    return props.fieldConfig.statusMap[value] || 'glass-tag-primary'
  }

  // 默认状态映射
  const statusValue = String(value).toLowerCase()

  if (['active', 'running', 'success', 'normal', '正常', '成功'].includes(statusValue)) {
    return 'glass-tag-success'
  }

  if (['error', 'failed', 'blacklisted', '失败', '错误', '加黑'].includes(statusValue)) {
    return 'glass-tag-error'
  }

  if (['warning', 'pending', '警告', '等待'].includes(statusValue)) {
    return 'glass-tag-warning'
  }

  return 'glass-tag-primary'
})

const copyToClipboard = async () => {
  const text = displayValue.value

  if (!text || text === '-') {
    ElMessage.warning('内容为空，无法复制')
    return
  }

  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${props.fieldConfig.label}已复制到剪贴板`)
  } catch (err) {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success(`${props.fieldConfig.label}已复制到剪贴板`)
    } catch (e) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}
</script>

<style scoped>
.status-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  position: relative;
  width: 100%;
  min-width: 0;
}

.glass-tag {
  white-space: nowrap;
  flex-shrink: 0;
}

.copy-icon {
  opacity: 0;
  transition: opacity var(--transition-fast);
  cursor: pointer;
  color: var(--color-primary);
  font-size: var(--text-base);
  flex-shrink: 0;
}

.status-cell:hover .copy-icon {
  opacity: 1;
}

.copy-icon:hover {
  color: var(--color-primary-hover);
  transform: scale(1.1);
}

.copy-icon:active {
  transform: scale(0.95);
}
</style>
