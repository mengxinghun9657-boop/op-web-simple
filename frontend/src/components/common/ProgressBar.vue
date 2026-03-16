<template>
  <div class="progress-bar-wrapper">
    <div class="progress-bar">
      <div class="progress-bar-fill" :style="{ width: percentage + '%' }">
        <div class="progress-bar-shine"></div>
      </div>
    </div>
    <div class="progress-bar-text">{{ percentage }}%</div>
  </div>
</template>

<script setup>
defineProps({ percentage: { type: Number, default: 0 } })
</script>

<style scoped>
.progress-bar-wrapper {
  width: 100%;
  max-width: 28rem;
}

.progress-bar {
  height: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--color-secondary), var(--color-error));
  transition: width var(--transition-normal);
  position: relative;
  border-radius: var(--radius-full);
}

.progress-bar-shine {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.3);
  animation: pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.progress-bar-text {
  text-align: right;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}
</style>
