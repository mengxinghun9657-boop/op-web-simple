<template>
  <span>{{ formattedDate }}</span>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
span {
  white-space: nowrap;
}
</style>
