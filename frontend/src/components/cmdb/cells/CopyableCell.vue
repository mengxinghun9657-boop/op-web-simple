<template>
  <div class="copyable-cell" @click.stop>
    <span class="cell-text">{{ displayValue }}</span>
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
  const value = props.row[props.fieldConfig.key]

  // 处理null、undefined、空字符串
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  // 处理数字
  if (typeof value === 'number') {
    return value.toString()
  }

  // 处理布尔值
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  // 处理对象和数组
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
})

const copyToClipboard = async () => {
  const text = props.row[props.fieldConfig.key]

  if (!text && text !== 0) {
    ElMessage.warning('内容为空，无法复制')
    return
  }

  const textToCopy = typeof text === 'object' ? JSON.stringify(text) : String(text)

  try {
    await navigator.clipboard.writeText(textToCopy)
    ElMessage.success(`${props.fieldConfig.label}已复制到剪贴板`)
  } catch (err) {
    // 降级方案：使用传统方法
    const textarea = document.createElement('textarea')
    textarea.value = textToCopy
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
.copyable-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  position: relative;
  width: 100%;
  min-width: 0;
}

.cell-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.copy-icon {
  opacity: 0;
  transition: opacity var(--transition-fast);
  cursor: pointer;
  color: var(--color-primary);
  font-size: var(--text-base);
  flex-shrink: 0;
}

.copyable-cell:hover .copy-icon {
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
