<template>
  <div class="metrics-card">
    <div>
      <div class="metrics-card-title">{{ title }}</div>
      <div class="metrics-card-value">
        {{ value }} <span class="metrics-card-unit">{{ unit }}</span>
      </div>
    </div>
    <div class="metrics-card-icon" :class="`metrics-card-icon--${type}`">
      <el-icon :size="20"><component :is="icon" /></el-icon>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  title: String,
  value: [Number, String],
  unit: String,
  icon: String,
  type: { type: String, default: 'primary' }
})
</script>

<style scoped>
.metrics-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.metrics-card-title {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-bottom: var(--space-1);
}

.metrics-card-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

.metrics-card-unit {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-left: var(--space-1);
}

.metrics-card-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metrics-card-icon--primary {
  background: rgba(26, 115, 232, 0.1);
  color: var(--primary);
}

.metrics-card-icon--success {
  background: rgba(30, 142, 62, 0.1);
  color: var(--color-success);
}

.metrics-card-icon--warning {
  background: rgba(234, 134, 0, 0.1);
  color: var(--color-warning);
}

.metrics-card-icon--error {
  background: rgba(217, 48, 37, 0.1);
  color: var(--color-error);
}

.metrics-card-icon--info {
  background: rgba(26, 115, 232, 0.1);
  color: var(--color-info);
}
</style>
