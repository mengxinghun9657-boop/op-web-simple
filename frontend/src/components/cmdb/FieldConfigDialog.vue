<template>
  <el-dialog
    v-model="visible"
    title="字段配置"
    width="900px"
    :close-on-click-modal="false"
    class="field-config-dialog"
  >
    <div class="dialog-content">
      <!-- 搜索和操作栏 -->
      <div class="toolbar">
        <el-input
          v-model="searchText"
          placeholder="搜索字段..."
          clearable
          style="width: 250px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        
        <div class="toolbar-actions">
          <el-button @click="selectAll">全选</el-button>
          <el-button @click="deselectAll">全不选</el-button>
          <el-button @click="resetToDefault">恢复默认</el-button>
        </div>
      </div>

      <!-- 字段分组列表 -->
      <div class="field-groups">
        <el-collapse v-model="activeGroups" accordion>
          <el-collapse-item
            v-for="group in filteredGroups"
            :key="group.name"
            :name="group.name"
          >
            <template #title>
              <div class="group-header">
                <span class="group-name">{{ group.name }}</span>
                <span class="group-count">
                  {{ getGroupSelectedCount(group) }} / {{ group.fields.length }}
                </span>
              </div>
            </template>
            
            <!-- 可拖拽的字段列表 -->
            <draggable
              v-model="group.fields"
              item-key="key"
              handle=".drag-handle"
              animation="200"
              @end="onDragEnd"
              class="field-list"
            >
              <template #item="{ element: field }">
                <div class="field-item">
                  <div class="field-left">
                    <el-icon class="drag-handle"><Rank /></el-icon>
                    <el-checkbox
                      v-model="field.visible"
                      @change="onFieldToggle"
                    >
                      <span class="field-label">{{ field.label }}</span>
                      <span class="field-key">{{ field.key }}</span>
                    </el-checkbox>
                  </div>
                  
                  <div class="field-right">
                    <el-tag v-if="field.sortable" size="small" type="info">可排序</el-tag>
                    <el-tag v-if="field.copyable" size="small" type="success">可复制</el-tag>
                    <el-tag v-if="field.type" size="small">{{ getTypeLabel(field.type) }}</el-tag>
                  </div>
                </div>
              </template>
            </draggable>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 已选字段预览 -->
      <div class="selected-preview">
        <div class="preview-header">
          <span>已选字段 ({{ selectedCount }})</span>
          <el-button text @click="showPreview = !showPreview">
            {{ showPreview ? '收起' : '展开' }}
          </el-button>
        </div>
        <div v-if="showPreview" class="preview-content">
          <el-tag
            v-for="field in selectedFields"
            :key="field.key"
            closable
            @close="removeField(field)"
            class="preview-tag"
          >
            {{ field.label }}
          </el-tag>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleConfirm">
          确定
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Search, Rank } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import { serverFieldDefinitions, instanceFieldDefinitions, getDefaultVisibleFields } from '@/config/cmdbFields'

const props = defineProps({
  modelValue: Boolean,
  viewMode: {
    type: String,
    required: true,
    validator: (value) => ['servers', 'instances'].includes(value)
  },
  visibleFields: {
    type: Array,
    required: true
  },
  fieldOrder: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const searchText = ref('')
const activeGroups = ref([])
const showPreview = ref(false)

// 字段分组数据（深拷贝，避免修改原始数据）
const fieldGroups = ref([])

// 初始化字段分组
const initFieldGroups = () => {
  const definitions = props.viewMode === 'servers' ? serverFieldDefinitions : instanceFieldDefinitions
  
  // 深拷贝字段定义
  fieldGroups.value = JSON.parse(JSON.stringify(definitions)).map(group => ({
    name: group.group,
    fields: group.fields.map(field => ({
      ...field,
      visible: props.visibleFields.includes(field.key)
    }))
  }))
  
  // 应用自定义顺序
  if (props.fieldOrder.length > 0) {
    applyFieldOrder()
  }
}

// 应用字段顺序
const applyFieldOrder = () => {
  fieldGroups.value.forEach(group => {
    group.fields.sort((a, b) => {
      const indexA = props.fieldOrder.indexOf(a.key)
      const indexB = props.fieldOrder.indexOf(b.key)
      
      // 如果都在自定义顺序中，按自定义顺序排序
      if (indexA !== -1 && indexB !== -1) {
        return indexA - indexB
      }
      
      // 如果只有一个在自定义顺序中，在自定义顺序中的排前面
      if (indexA !== -1) return -1
      if (indexB !== -1) return 1
      
      // 都不在自定义顺序中，保持原顺序
      return 0
    })
  })
}

// 过滤后的分组
const filteredGroups = computed(() => {
  if (!searchText.value) return fieldGroups.value
  
  const keyword = searchText.value.toLowerCase()
  return fieldGroups.value.map(group => ({
    ...group,
    fields: group.fields.filter(field =>
      field.label.toLowerCase().includes(keyword) ||
      field.key.toLowerCase().includes(keyword)
    )
  })).filter(group => group.fields.length > 0)
})

// 已选字段
const selectedFields = computed(() => {
  const fields = []
  fieldGroups.value.forEach(group => {
    group.fields.forEach(field => {
      if (field.visible) {
        fields.push(field)
      }
    })
  })
  return fields
})

// 已选字段数量
const selectedCount = computed(() => selectedFields.value.length)

// 获取分组已选数量
const getGroupSelectedCount = (group) => {
  return group.fields.filter(f => f.visible).length
}

// 获取类型标签
const getTypeLabel = (type) => {
  const typeMap = {
    'resource': '资源',
    'status': '状态',
    'datetime': '时间',
    'boolean': '布尔',
    'memory': '内存'
  }
  return typeMap[type] || type
}

// 全选
const selectAll = () => {
  fieldGroups.value.forEach(group => {
    group.fields.forEach(field => {
      field.visible = true
    })
  })
}

// 全不选
const deselectAll = () => {
  fieldGroups.value.forEach(group => {
    group.fields.forEach(field => {
      field.visible = false
    })
  })
}

// 恢复默认
const resetToDefault = () => {
  const defaultFields = getDefaultVisibleFields(props.viewMode)
  fieldGroups.value.forEach(group => {
    group.fields.forEach(field => {
      field.visible = defaultFields.includes(field.key)
    })
  })
}

// 移除字段
const removeField = (field) => {
  fieldGroups.value.forEach(group => {
    const targetField = group.fields.find(f => f.key === field.key)
    if (targetField) {
      targetField.visible = false
    }
  })
}

// 字段切换
const onFieldToggle = () => {
  // 可以在这里添加额外的逻辑
}

// 拖拽结束
const onDragEnd = () => {
  // 拖拽结束后，字段顺序已经改变
}

// 确定
const handleConfirm = () => {
  // 收集可见字段和顺序
  const visibleFields = []
  const fieldOrder = []
  
  fieldGroups.value.forEach(group => {
    group.fields.forEach(field => {
      fieldOrder.push(field.key)
      if (field.visible) {
        visibleFields.push(field.key)
      }
    })
  })
  
  emit('confirm', {
    visibleFields,
    fieldOrder
  })
  
  visible.value = false
}

// 取消
const handleCancel = () => {
  visible.value = false
}

// 监听对话框打开，初始化数据
watch(visible, (newVal) => {
  if (newVal) {
    initFieldGroups()
    activeGroups.value = [fieldGroups.value[0]?.name]
  }
})
</script>

<style scoped>
.field-config-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.dialog-content {
  display: flex;
  flex-direction: column;
  height: 600px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
}

.toolbar-actions {
  display: flex;
  gap: var(--spacing-2);
}

/* 字段分组 */
.field-groups {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: var(--spacing-4);
}

.group-name {
  font-weight: 600;
  color: var(--text-primary);
}

.group-count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 字段列表 */
.field-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-3) 0;
}

.field-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3);
  background-color: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.field-item:hover {
  background-color: var(--bg-spotlight);
  border-color: var(--color-primary);
}

.field-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  flex: 1;
}

.drag-handle {
  cursor: move;
  color: var(--text-tertiary);
  font-size: 18px;
}

.drag-handle:hover {
  color: var(--color-primary);
}

.field-label {
  font-weight: 500;
  color: var(--text-primary);
  margin-right: var(--spacing-2);
}

.field-key {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-family: 'Courier New', monospace;
}

.field-right {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;
}

/* 已选字段预览 */
.selected-preview {
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  font-weight: 600;
  color: var(--text-primary);
}

.preview-content {
  padding: var(--spacing-3) var(--spacing-4);
  max-height: 150px;
  overflow-y: auto;
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.preview-tag {
  cursor: pointer;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}

/* 拖拽时的样式 */
.field-list .sortable-ghost {
  opacity: 0.5;
  background-color: var(--color-primary-light);
}

.field-list .sortable-drag {
  opacity: 0.8;
}

/* 折叠面板样式 */
:deep(.el-collapse) {
  border: none;
}

:deep(.el-collapse-item__header) {
  background-color: var(--bg-elevated);
  border: none;
  padding: var(--spacing-3) var(--spacing-4);
  font-size: var(--font-size-base);
}

:deep(.el-collapse-item__wrap) {
  background-color: transparent;
  border: none;
}

:deep(.el-collapse-item__content) {
  padding: 0 var(--spacing-4);
}

/* 滚动条样式 */
.field-groups::-webkit-scrollbar,
.preview-content::-webkit-scrollbar {
  width: 6px;
}

.field-groups::-webkit-scrollbar-thumb,
.preview-content::-webkit-scrollbar-thumb {
  background-color: var(--border-color);
  border-radius: 3px;
}

.field-groups::-webkit-scrollbar-thumb:hover,
.preview-content::-webkit-scrollbar-thumb:hover {
  background-color: var(--text-tertiary);
}
</style>
