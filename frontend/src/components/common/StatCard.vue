<template>
  <div class="stat-card" :class="`stat-card-${variant}`">
    <div class="stat-card-header">
      <div class="stat-card-title">{{ title }}</div>
      <div class="stat-card-icon">
        <el-icon :size="20"><component :is="icon" /></el-icon>
      </div>
    </div>

    <div class="stat-card-body">
      <div class="stat-card-value">{{ value }}</div>
      <div v-if="trend !== undefined" class="stat-card-trend" :class="trend > 0 ? 'trend-up' : 'trend-down'">
        <el-icon :size="14"><component :is="trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
        <span>{{ Math.abs(trend) }}%</span>
      </div>
    </div>

    <div v-if="subtitle" class="stat-card-subtitle">{{ subtitle }}</div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  value: [String, Number],
  subtitle: String,
  icon: String,
  trend: Number,
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'success', 'warning', 'error', 'info'].includes(v)
  }
})
</script>

<style scoped>
.stat-card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-card);
  padding: var(--spacing-4);
  transition: var(--transition-all);
}

.stat-card:hover {
  border-color: var(--border-color-light);
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-2px);
}

.stat-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-3);
}

.stat-card-title {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

.stat-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  color: white;
}

.stat-card-primary .stat-card-icon {
  background: var(--color-primary-500);
}

.stat-card-success .stat-card-icon {
  background: var(--color-success);
}

.stat-card-warning .stat-card-icon {
  background: var(--color-warning);
}

.stat-card-error .stat-card-icon {
  background: var(--color-error);
}

.stat-card-info .stat-card-icon {
  background: var(--color-info);
}

.stat-card-body {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.stat-card-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-card-trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.stat-card-trend.trend-up {
  color: var(--color-success);
}

.stat-card-trend.trend-down {
  color: var(--color-error);
}

.stat-card-subtitle {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
