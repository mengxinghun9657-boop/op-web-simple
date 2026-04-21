<template>
  <div class="resource-cell" @click.stop>
    <div class="resource-header">
      <span class="resource-text">{{ usedValue }}/{{ totalValue }}</span>
      <el-icon
        v-if="usedValue || totalValue"
        class="copy-icon"
        @click="copyToClipboard"
      >
        <DocumentCopy />
      </el-icon>
    </div>
    <div class="progress-track">
      <div class="progress-bar" :style="{ width: percentage + '%', background: barColor }"></div>
    </div>
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

const usedValue = computed(() => {
  const usedKey = props.fieldConfig.usedKey || props.fieldConfig.key
  return props.row[usedKey] || 0
})

const totalValue = computed(() => {
  const totalKey = props.fieldConfig.totalKey
  return totalKey ? (props.row[totalKey] || 0) : 100
})

const percentage = computed(() => {
  if (totalValue.value === 0) return 0
  const p = Math.round((usedValue.value / totalValue.value) * 100)
  return Math.min(p, 100)
})

const barColor = computed(() => {
  const p = percentage.value
  if (p >= 90) return 'var(--color-error)'
  if (p >= 70) return 'var(--color-warning)'
  return 'var(--color-success)'
})

const copyToClipboard = async () => {
  const text = `${usedValue.value}/${totalValue.value}`

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
.resource-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  min-width: 0;
}

.resource-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
}

.resource-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-track {
  width: 100%;
  height: 4px;
  background: var(--border-primary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease, background 0.3s ease;
  min-width: 2px;
}

.copy-icon {
  opacity: 0;
  transition: opacity var(--transition-fast);
  cursor: pointer;
  color: var(--color-primary);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

.resource-cell:hover .copy-icon {
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
