<template>
  <span>{{ formattedMemory }}</span>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
span {
  white-space: nowrap;
}
</style>
