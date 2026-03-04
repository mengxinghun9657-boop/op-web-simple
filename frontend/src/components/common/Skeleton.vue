<template>
  <div class="skeleton" :style="{ width, height, borderRadius }"></div>
</template>

<script setup>
defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '20px' },
  borderRadius: { type: String, default: '4px' }
})
</script>

<style scoped>
.skeleton {
  background: linear-gradient(90deg, var(--bg-elevated) 25%, rgba(255,255,255,0.08) 50%, var(--bg-elevated) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
