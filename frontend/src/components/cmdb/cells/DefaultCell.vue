<template>
  <span class="default-cell">{{ displayValue }}</span>
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
</script>

<style scoped>
.default-cell {
  color: var(--text-primary);
}
</style>
