<template>
  <div class="card" :class="[`card-${variant}`, { 'card-interactive': interactive }]">
    <!-- 头部 -->
    <div v-if="title || $slots.header" class="card-header">
      <div class="card-title">
        <div v-if="icon" class="card-title-icon">
          <el-icon :size="18"><component :is="icon" /></el-icon>
        </div>
        <span>{{ title }}</span>
      </div>
      <div v-if="$slots.header" class="card-header-action">
        <slot name="header" />
      </div>
    </div>

    <!-- 内容 -->
    <div class="card-body">
      <slot />
    </div>

    <!-- 底部 -->
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  icon: String,
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'primary', 'success', 'warning', 'error'].includes(v)
  },
  interactive: Boolean
})
</script>

<style scoped>
.card {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: var(--transition-all);
}

.card:hover {
  border-color: var(--border-color-light);
  box-shadow: var(--card-shadow-hover);
}

.card-interactive {
  cursor: pointer;
}

.card-interactive:active {
  transform: scale(0.98);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.card-title-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-lg);
  background: var(--color-primary-500);
  color: white;
}

.card-header-action {
  display: flex;
  gap: var(--spacing-2);
}

.card-body {
  padding: var(--spacing-4);
}

.card-footer {
  padding: var(--spacing-4);
  border-top: 1px solid var(--border-color);
  background: var(--bg-hover);
}

/* 变体样式 */
.card-primary .card-title-icon {
  background: var(--color-primary-500);
}

.card-success .card-title-icon {
  background: var(--color-success);
}

.card-warning .card-title-icon {
  background: var(--color-warning);
}

.card-error .card-title-icon {
  background: var(--color-error);
}
</style>
