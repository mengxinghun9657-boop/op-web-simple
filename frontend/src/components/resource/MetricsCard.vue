<template>
  <div class="glass-card p-4 flex items-center justify-between">
    <div>
      <div class="text-gray-400 text-sm mb-1">{{ title }}</div>
      <div class="text-2xl font-bold text-white flex items-end">
        {{ value }} <span class="text-xs text-gray-500 ml-1 mb-1">{{ unit }}</span>
      </div>
    </div>
    <div class="w-10 h-10 rounded-lg flex items-center justify-center" :class="bgClass">
      <el-icon :size="20" :class="iconClass"><component :is="icon" /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  value: [Number, String],
  unit: String,
  icon: String,
  type: { type: String, default: 'primary' }
})

const bgClass = computed(() => `bg-${props.type}-500/20`)
const iconClass = computed(() => `text-${props.type}-400`)
</script>