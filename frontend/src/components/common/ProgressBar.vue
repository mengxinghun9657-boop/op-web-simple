<template>
  <div class="w-full max-w-md h-4 bg-gray-700 rounded-full overflow-hidden relative shadow-inner">
    <div 
      class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-300 relative"
      :style="{ width: percentage + '%' }"
    >
      <div class="absolute inset-0 bg-white/30 animate-pulse-fast"></div>
    </div>
  </div>
  <div class="text-right text-xs text-gray-400 mt-1">{{ percentage }}%</div>
</template>

<script setup>
defineProps({ percentage: { type: Number, default: 0 } })
</script>

<style scoped>
.animate-pulse-fast { animation: pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
</style>