<template>
  <span class="glass-tag" :class="value ? 'glass-tag-success' : 'glass-tag-default'">
    {{ value ? '是' : '否' }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

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
</script>
