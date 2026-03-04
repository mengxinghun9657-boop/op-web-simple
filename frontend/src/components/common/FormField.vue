<template>
  <div class="form-field" :class="{ 'form-field-error': error }">
    <!-- 标签 -->
    <label v-if="label" class="form-field-label">
      <span class="form-field-label-text">{{ label }}</span>
      <span v-if="required" class="form-field-required">*</span>
    </label>

    <!-- 输入框 -->
    <div class="form-field-input-wrapper">
      <input
        v-if="type !== 'textarea'"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        class="form-field-input"
        @input="$emit('update:modelValue', $event.target.value)"
        @blur="$emit('blur')"
        @focus="$emit('focus')"
      />
      <textarea
        v-else
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :rows="rows"
        class="form-field-input form-field-textarea"
        @input="$emit('update:modelValue', $event.target.value)"
        @blur="$emit('blur')"
        @focus="$emit('focus')"
      />
      
      <!-- 清除按钮 -->
      <button
        v-if="clearable && modelValue && !disabled"
        type="button"
        class="form-field-clear-btn"
        @click="$emit('update:modelValue', '')"
      >
        <el-icon :size="16"><Close /></el-icon>
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="form-field-error-msg">
      <el-icon :size="14"><CircleCloseFilled /></el-icon>
      <span>{{ error }}</span>
    </div>

    <!-- 帮助文本 -->
    <div v-if="help && !error" class="form-field-help">
      {{ help }}
    </div>
  </div>
</template>

<script setup>
import { Close, CircleCloseFilled } from '@element-plus/icons-vue'

defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: String,
  placeholder: String,
  type: {
    type: String,
    default: 'text'
  },
  error: String,
  help: String,
  required: Boolean,
  disabled: Boolean,
  readonly: Boolean,
  clearable: Boolean,
  rows: {
    type: Number,
    default: 3
  }
})

defineEmits(['update:modelValue', 'blur', 'focus'])
</script>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.form-field-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.form-field-label-text {
  cursor: pointer;
}

.form-field-required {
  color: var(--color-error);
}

.form-field-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.form-field-input {
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-input);
  color: var(--text-primary);
  font-size: var(--font-size-base);
  font-family: var(--font-family-sans);
  transition: var(--transition-all);
}

.form-field-input::placeholder {
  color: var(--text-disabled);
}

.form-field-input:hover:not(:disabled) {
  border-color: var(--input-border-hover);
}

.form-field-input:focus {
  outline: none;
  border-color: var(--input-border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-field-input:disabled {
  background: var(--bg-hover);
  color: var(--text-disabled);
  cursor: not-allowed;
}

.form-field-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-field-clear-btn {
  position: absolute;
  right: var(--spacing-3);
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: var(--spacing-1);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-colors);
}

.form-field-clear-btn:hover {
  color: var(--text-secondary);
}

.form-field-error .form-field-input {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.form-field-error .form-field-input:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-field-error-msg {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-error);
}

.form-field-help {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
