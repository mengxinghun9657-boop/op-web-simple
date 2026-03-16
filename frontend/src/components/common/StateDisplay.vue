<template>
  <div class="state-display" :class="`state-display-${state}`">
    <!-- 加载状态 -->
    <div v-if="state === 'loading'" class="state-content">
      <div class="state-spinner">
        <div class="spinner"></div>
      </div>
      <div class="state-text">{{ loadingText }}</div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="state === 'empty'" class="state-content">
      <div class="state-icon">
        <el-icon :size="48"><DataAnalysis /></el-icon>
      </div>
      <div class="state-text">{{ emptyText }}</div>
      <div v-if="$slots.action" class="state-action">
        <slot name="action" />
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="state === 'error'" class="state-content">
      <div class="state-icon state-icon-error">
        <el-icon :size="48"><CircleCloseFilled /></el-icon>
      </div>
      <div class="state-text">{{ errorText }}</div>
      <div v-if="errorDetail" class="state-detail">{{ errorDetail }}</div>
      <div v-if="$slots.action" class="state-action">
        <slot name="action" />
      </div>
    </div>

    <!-- 成功状态 -->
    <div v-else-if="state === 'success'" class="state-content">
      <div class="state-icon state-icon-success">
        <el-icon :size="48"><SuccessFilled /></el-icon>
      </div>
      <div class="state-text">{{ successText }}</div>
      <div v-if="$slots.action" class="state-action">
        <slot name="action" />
      </div>
    </div>

    <!-- 自定义内容 -->
    <div v-else class="state-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { DataAnalysis, CircleCloseFilled, SuccessFilled } from '@element-plus/icons-vue'

defineProps({
  state: {
    type: String,
    default: 'empty',
    validator: (v) => ['loading', 'empty', 'error', 'success', 'custom'].includes(v)
  },
  loadingText: {
    type: String,
    default: '加载中...'
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  errorText: {
    type: String,
    default: '加载失败'
  },
  errorDetail: String,
  successText: {
    type: String,
    default: '操作成功'
  }
})
</script>

<style scoped>
.state-display {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: var(--space-6);
}

.state-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  text-align: center;
}

.state-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--bg-hover);
  color: var(--text-tertiary);
}

.state-icon-success {
  background: rgba(30, 142, 62, 0.1);
  color: var(--color-success);
}

.state-icon-error {
  background: rgba(217, 48, 37, 0.1);
  color: var(--color-error);
}

.state-text {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
}

.state-detail {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 300px;
}

.state-action {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
</style>
