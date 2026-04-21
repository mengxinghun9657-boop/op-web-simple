<template>
  <div class="boolean-cell" @click.stop>
    <span class="glass-tag" :class="value ? 'glass-tag-success' : 'glass-tag-default'">
      {{ value ? '是' : '否' }}
    </span>
    <el-icon
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

const value = computed(() => {
  const val = props.row[props.fieldConfig.key]
  // 处理各种布尔值表示
  if (val === true || val === 1 || val === '1' || val === 'true' || val === 'True') {
    return true
  }
  return false
})

const displayValue = computed(() => {
  return value.value ? '是' : '否'
})

const copyToClipboard = async () => {
  const text = displayValue.value

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
.boolean-cell {
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

.boolean-cell:hover .copy-icon {
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
