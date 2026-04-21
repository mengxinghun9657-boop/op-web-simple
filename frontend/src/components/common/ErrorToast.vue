<template>
  <transition-group name="toast" tag="div" class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="toast"
      :class="`toast-${toast.type}`"
    >
      <div class="toast-icon">
        <el-icon :size="20">
          <CircleClose v-if="toast.type === 'error'" />
          <WarningFilled v-else-if="toast.type === 'warning'" />
          <CircleCheck v-else-if="toast.type === 'success'" />
          <InfoFilled v-else />
        </el-icon>
      </div>
      <div class="toast-content">
        <div class="toast-title">{{ toast.title }}</div>
        <div v-if="toast.message" class="toast-message">{{ toast.message }}</div>
        <button
          v-if="toast.retryable"
          class="toast-retry"
          @click="handleRetry(toast)"
        >
          重试
        </button>
      </div>
      <button class="toast-close" @click="removeToast(toast.id)">×</button>
    </div>
  </transition-group>
</template>

<script>
import { ref } from 'vue';
import { CircleClose, WarningFilled, CircleCheck, InfoFilled } from '@element-plus/icons-vue';

export default {
  name: 'ErrorToast',
  components: { CircleClose, WarningFilled, CircleCheck, InfoFilled },
  setup() {
    const toasts = ref([]);
    let toastId = 0;

    const addToast = (options) => {
      const id = ++toastId;
      const toast = {
        id,
        type: options.type || 'error',
        title: options.title || '错误',
        message: options.message || '',
        retryable: options.retryable || false,
        retryFn: options.retryFn || null,
        duration: options.duration || 5000
      };

      toasts.value.push(toast);

      // 自动移除
      if (toast.duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, toast.duration);
      }

      return id;
    };

    const removeToast = (id) => {
      const index = toasts.value.findIndex(t => t.id === id);
      if (index > -1) {
        toasts.value.splice(index, 1);
      }
    };

    const handleRetry = (toast) => {
      if (toast.retryFn) {
        toast.retryFn();
      }
      removeToast(toast.id);
    };

    return {
      toasts,
      addToast,
      removeToast,
      handleRetry
    };
  }
};
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-5);
  right: var(--space-5);
  z-index: var(--z-notification);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border-left: 4px solid;
  min-width: 300px;
}

.toast-error {
  border-left-color: var(--color-error);
}

.toast-warning {
  border-left-color: var(--color-warning);
}

.toast-success {
  border-left-color: var(--color-success);
}

.toast-info {
  border-left-color: var(--color-info);
}

.toast-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toast-error .toast-icon {
  color: var(--color-error);
}

.toast-warning .toast-icon {
  color: var(--color-warning);
}

.toast-success .toast-icon {
  color: var(--color-success);
}

.toast-info .toast-icon {
  color: var(--color-info);
}

.toast-content {
  flex: 1;
}

.toast-title {
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-1);
  color: var(--text-primary);
}

.toast-message {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.4;
}

.toast-retry {
  margin-top: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.toast-retry:hover {
  background: var(--primary-dark);
}

.toast-close {
  background: none;
  border: none;
  font-size: var(--text-lg);
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  transition: color var(--transition-fast);
}

.toast-close:hover {
  color: var(--text-primary);
}

/* 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all var(--transition-normal);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
