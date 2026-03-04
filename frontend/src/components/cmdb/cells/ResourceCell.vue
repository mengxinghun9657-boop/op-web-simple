<template>
  <div class="resource-cell">
    <span class="resource-text">{{ usedValue }}/{{ totalValue }}</span>
    <el-progress 
      :percentage="percentage" 
      :stroke-width="4" 
      :show-text="false" 
      :color="progressColor" 
    />
  </div>
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
  return Math.round((usedValue.value / totalValue.value) * 100)
})

const progressColor = computed(() => {
  const percent = percentage.value
  if (percent >= 90) return 'var(--color-error)'
  if (percent >= 70) return 'var(--color-warning)'
  return 'var(--color-success)'
})
</script>

<style scoped>
.resource-cell {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.resource-text {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}
</style>
