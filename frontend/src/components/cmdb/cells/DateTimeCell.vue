<template>
  <div class="datetime-cell" @click.stop>
    <span class="cell-text">{{ formattedDate }}</span>
    <el-icon
      v-if="formattedDate && formattedDate !== '-'"
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

const formattedDate = computed(() => {
  const value = props.row[props.fieldConfig.key]
  if (!value) return '-'

  try {
    const date = new Date(value)
    if (isNaN(date.getTime())) return value

    // 格式化为 YYYY-MM-DD HH:mm:ss
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch (e) {
    return value
  }
})

const copyToClipboard = async () => {
  const text = formattedDate.value

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
.datetime-cell {
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
  font-size: 14px;
  flex-shrink: 0;
}

.datetime-cell:hover .copy-icon {
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
