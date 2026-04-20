<template>
  <div class="date-range-picker">
    <el-form-item label="时间范围">
      <div class="date-picker-wrapper">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="shortcuts"
          @change="handleDateChange"
          style="width: 100%"
        />
        <el-select
          v-model="timeField"
          placeholder="时间字段"
          style="width: 140px; margin-left: 12px"
          @change="handleDateChange"
        >
          <el-option label="创建时间" value="创建时间" />
          <el-option label="最后修改时间" value="最后修改时间" />
          <el-option label="完成时间" value="完成时间" />
        </el-select>
      </div>
    </el-form-item>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { generateTimeCondition, mergeTimeCondition, removeTimeCondition } from '@/utils/iqlGenerator'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const dateRange = ref(getDefaultDateRange())
const timeField = ref('创建时间')
// 记录上一次使用的时间字段，切换时用于清除旧条件
let prevTimeField = '创建时间'

// 默认设置为最近7天
function getDefaultDateRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 7)
  return [start, end]
}

// 快捷日期选项
const shortcuts = [
  {
    text: '今天',
    value: () => {
      const today = new Date()
      return [today, today]
    }
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return [start, end]
    }
  },
  {
    text: '本月',
    value: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      return [start, end]
    }
  },
  {
    text: '上月',
    value: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const end = new Date(now.getFullYear(), now.getMonth(), 0)
      return [start, end]
    }
  },
  {
    text: '本季度',
    value: () => {
      const now = new Date()
      const quarter = Math.floor(now.getMonth() / 3)
      const start = new Date(now.getFullYear(), quarter * 3, 1)
      const end = new Date(now.getFullYear(), quarter * 3 + 3, 0)
      return [start, end]
    }
  },
  {
    text: '本年度',
    value: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), 0, 1)
      const end = new Date(now.getFullYear(), 11, 31)
      return [start, end]
    }
  }
]

const handleDateChange = () => {
  if (!dateRange.value) {
    // 清空日期：移除当前字段和旧字段的时间条件
    let iql = removeTimeCondition(props.modelValue, timeField.value)
    if (prevTimeField !== timeField.value) {
      iql = removeTimeCondition(iql, prevTimeField)
    }
    prevTimeField = timeField.value
    emit('update:modelValue', iql)
    return
  }

  try {
    const [start, end] = dateRange.value
    const timeCondition = generateTimeCondition(timeField.value, start, end)

    // 先移除旧字段的时间条件，再合并新字段条件
    let base = props.modelValue
    if (prevTimeField !== timeField.value) {
      base = removeTimeCondition(base, prevTimeField)
    }
    prevTimeField = timeField.value

    const newIql = mergeTimeCondition(base, timeCondition, timeField.value)
    emit('update:modelValue', newIql)
  } catch (error) {
    console.error('生成时间条件失败:', error)
  }
}

// 组件挂载时自动应用默认时间范围
onMounted(() => {
  // 如果父组件传入的IQL为空,则自动应用默认时间范围
  if (!props.modelValue || !props.modelValue.includes(timeField.value)) {
    handleDateChange()
  }
})
</script>

<style scoped>
.date-range-picker {
  width: 100%;
}

.date-picker-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  width: 100%;
}

.date-picker-wrapper :deep(.el-date-editor) {
  transition: all var(--transition-fast);
}

.date-picker-wrapper :deep(.el-date-editor:hover) {
  border-color: var(--color-primary-400);
}

.date-picker-wrapper :deep(.el-date-editor.is-active) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.date-picker-wrapper :deep(.el-select) {
  transition: all var(--transition-fast);
}

.date-picker-wrapper :deep(.el-select:hover .el-select__wrapper) {
  border-color: var(--color-primary-400);
}

.date-picker-wrapper :deep(.el-select .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

@media (max-width: 768px) {
  .date-picker-wrapper {
    flex-direction: column;
    align-items: stretch;
  }
  
  .date-picker-wrapper .el-select {
    margin-left: 0 !important;
    width: 100% !important;
  }
}
</style>
