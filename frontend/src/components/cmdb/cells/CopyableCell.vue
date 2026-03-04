<template>
  <div class="copyable-cell" @click.stop>
    <span class="cell-text">{{ displayValue }}</span>
    <el-icon 
      v-if="displayValue" 
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

const copyToClipboard = async () => {
  const text = props.row[props.fieldConfig.key]
  
  if (!text) {
    ElMessage.warning('内容为空，无法复制')
    return
  }
  
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${props.fieldConfig.label}已复制到剪贴板`)
  } catch (err) {
    // 降级方案：使用传统方法
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
.copyable-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  position: relative;
}

.cell-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-icon {
  opacity: 0;
  transition: opacity var(--transition-fast);
  cursor: pointer;
  color: var(--color-primary);
  font-size: 14px;
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
