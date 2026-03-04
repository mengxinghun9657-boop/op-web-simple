<template>
  <transition-group name="toast" tag="div" class="toast-container">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="toast"
      :class="`toast-${toast.type}`"
    >
      <div class="toast-icon">
        {{ getIcon(toast.type) }}
      </div>
      <div class="toast-content">
        <div class="toast-title">{{ toast.title }}</div>
        <div v-if="toast.message" class="toast-message">{{ toast.message }}</div>
        <button
          v-if="toast.retryable"
          class="toast-retry"
          @click="handleRetry(toast)"
        >
          🔄 重试
        </button>
      </div>
      <button class="toast-close" @click="removeToast(toast.id)">✕</button>
    </div>
  </transition-group>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'ErrorToast',
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

    const getIcon = (type) => {
      const icons = {
        error: '❌',
        warning: '⚠️',
        success: '✅',
        info: 'ℹ️'
      };
      return icons[type] || icons.info;
    };

    return {
      toasts,
      addToast,
      removeToast,
      handleRetry,
      getIcon
    };
  }
};
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid;
  min-width: 300px;
}

.toast-error {
  border-left-color: #f44336;
}

.toast-warning {
  border-left-color: #ff9800;
}

.toast-success {
  border-left-color: #4caf50;
}

.toast-info {
  border-left-color: #2196f3;
}

.toast-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.toast-content {
  flex: 1;
}

.toast-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: #333;
}

.toast-message {
  font-size: 14px;
  color: #666;
  line-height: 1.4;
}

.toast-retry {
  margin-top: 8px;
  padding: 4px 12px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.3s;
}

.toast-retry:hover {
  background: #1976d2;
}

.toast-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.toast-close:hover {
  color: #333;
}

/* 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
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
