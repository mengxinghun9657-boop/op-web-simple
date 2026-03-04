<template>
  <el-dialog
    v-model="visible"
    title="选择数据表"
    width="600px"
    :close-on-click-modal="false"
    class="unified-dialog"
  >
    <div class="selector-content">
      <!-- 表选择 -->
      <div class="selector-section">
        <label class="selector-label">选择数据表</label>
        <el-select
          v-model="selectedTable"
          placeholder="请选择数据表"
          filterable
          style="width: 100%"
        >
          <el-option
            v-for="table in tables"
            :key="table.name"
            :label="`${table.name} - ${table.description}`"
            :value="table.name"
          />
        </el-select>
        <div class="selector-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>选择表后，AI 将自动分析表结构并查询相关数据</span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!selectedTable"
          @click="handleConfirm"
        >
          确定查询
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'select'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const tables = ref([])
const selectedTable = ref('')

// 加载表列表
const loadTables = async () => {
  try {
    console.log('[DataSelector] 开始加载表列表...')
    
    const response = await axios.get('/api/v1/ai/tables')
    // axios拦截器已经返回了response.data，所以response就是{success, data}
    console.log('[DataSelector] API 响应:', response)
    
    if (response.success) {
      tables.value = response.data
      console.log(`[DataSelector] 成功加载 ${response.data.length} 个表`)
    } else {
      console.error('[DataSelector] API 返回 success=false:', response)
      ElMessage.error('加载表列表失败: ' + (response.detail || response.message || '未知错误'))
    }
  } catch (error) {
    console.error('[DataSelector] 加载表列表异常:', error)
    
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('加载表列表失败: ' + errorMsg)
  }
}

// 确认选择
const handleConfirm = () => {
  if (!selectedTable.value) {
    ElMessage.warning('请选择数据表')
    return
  }

  // 只传递表名，后端会自动处理
  emit('select', {
    table: selectedTable.value
  })
  
  visible.value = false
  
  // 重置选择
  selectedTable.value = ''
}

// 监听对话框打开
watch(visible, (newVal) => {
  if (newVal && tables.value.length === 0) {
    loadTables()
  }
})
</script>

<style scoped>
.selector-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
}

.selector-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.selector-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-secondary);
}

.selector-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
}

/* 对话框样式优化 - 使用统一弹窗系统 */
.unified-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
}

.unified-dialog :deep(.el-dialog__header) {
  padding: var(--spacing-5);
  border-bottom: 1px solid var(--border-color);
}

.unified-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-5);
}

.unified-dialog :deep(.el-dialog__footer) {
  padding: var(--spacing-5);
  border-top: 1px solid var(--border-color);
}
</style>
