<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="modal-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <!-- 内容 -->
    <div class="modal-dialog-body">
      <slot />
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="modal-dialog-footer">
        <el-button @click="$emit('update:modelValue', false)">
          {{ cancelText }}
        </el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="$emit('confirm')"
        >
          {{ confirmText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  modelValue: Boolean,
  title: String,
  width: {
    type: String,
    default: '500px'
  },
  confirmText: {
    type: String,
    default: '确认'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  loading: Boolean
})

defineEmits(['update:modelValue', 'confirm'])
</script>

<style scoped>
:deep(.modal-dialog) {
  --el-dialog-bg-color: var(--glass-bg);
  --el-dialog-border-color: var(--glass-border);
}

:deep(.modal-dialog .el-dialog) {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-modal);
  box-shadow: var(--shadow-2xl);
}

:deep(.modal-dialog .el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
}

:deep(.modal-dialog .el-dialog__title) {
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.modal-dialog .el-dialog__close) {
  color: var(--text-secondary);
}

:deep(.modal-dialog .el-dialog__close:hover) {
  color: var(--text-primary);
}

.modal-dialog-body {
  padding: var(--spacing-4) 0;
  color: var(--text-primary);
}

.modal-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-color);
}

:deep(.modal-dialog-footer .el-button) {
  min-width: 80px;
}
</style>
