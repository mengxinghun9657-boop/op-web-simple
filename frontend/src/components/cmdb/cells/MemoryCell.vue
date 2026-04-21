<template>
  <div class="memory-cell" @click.stop>
    <span class="cell-text">{{ formattedMemory }}</span>
    <el-icon
      v-if="formattedMemory && formattedMemory !== '0'"
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
  row: Object,
  fieldConfig: Object
})

const formattedMemory = computed(() => {
  const value = props.row[props.fieldConfig.key]
  if (!value || value === 0) return '0'

  const mb = Number(value)
  if (isNaN(mb)) return value

  // 自动转换单位
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`
  }
  return `${mb} MB`
})

const copyToClipboard = async () => {
  const text = formattedMemory.value

  if (!text || text === '0') {
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
.memory-cell {
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

.memory-cell:hover .copy-icon {
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
