<template>
  <span 
    class="glass-tag" 
    :class="statusClass"
  >
    {{ displayValue }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
/* 状态标签不换行 */
.glass-tag {
  white-space: nowrap;
}
</style>
