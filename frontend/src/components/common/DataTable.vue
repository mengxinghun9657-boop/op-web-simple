<template>
  <div class="data-table-wrapper">
    <!-- 表格头部 -->
    <div v-if="$slots.header" class="data-table-header">
      <slot name="header" />
    </div>

    <!-- 表格容器 -->
    <div class="data-table-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="data-table-loading">
        <el-skeleton :rows="5" animated />
      </div>

      <!-- 空状态 -->
      <div v-else-if="!data || data.length === 0" class="data-table-empty">
        <div class="data-table-empty-icon">
          <el-icon :size="48"><DataAnalysis /></el-icon>
        </div>
        <div class="data-table-empty-text">{{ emptyText }}</div>
        <div v-if="$slots.empty" class="data-table-empty-action">
          <slot name="empty" />
        </div>
      </div>

      <!-- 表格 -->
      <el-table
        v-else
        :data="data"
        :stripe="stripe"
        :border="border"
        :default-sort="defaultSort"
        :highlight-current-row="highlightCurrentRow"
        class="data-table"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
      >
        <!-- 选择列 -->
        <el-table-column
          v-if="selectable"
          type="selection"
          width="50"
          align="center"
        />

        <!-- 动态列 -->
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth || 120"
          :align="col.align || 'left'"
          :sortable="col.sortable"
          :class-name="col.className"
        >
          <template #default="{ row }">
            <slot :name="`col-${col.prop}`" :row="row">
              {{ row[col.prop] }}
            </slot>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column
          v-if="$slots.actions"
          label="操作"
          width="120"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <slot name="actions" :row="row" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div v-if="pagination" class="data-table-pagination">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { DataAnalysis } from '@element-plus/icons-vue'

defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    required: true
  },
  loading: Boolean,
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  stripe: {
    type: Boolean,
    default: true
  },
  border: {
    type: Boolean,
    default: false
  },
  selectable: Boolean,
  highlightCurrentRow: Boolean,
  defaultSort: Object,
  pagination: Object
})

const emit = defineEmits([
  'sort-change',
  'selection-change',
  'page-change',
  'page-size-change'
])

const handleSortChange = (data) => {
  emit('sort-change', data)
}

const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

const handlePageChange = (page) => {
  emit('page-change', page)
}

const handlePageSizeChange = (pageSize) => {
  emit('page-size-change', pageSize)
}
</script>

<style scoped>
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.data-table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-card);
}

.data-table-container {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-card);
  overflow: hidden;
}

.data-table-loading {
  padding: var(--spacing-6);
}

.data-table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12) var(--spacing-6);
  color: var(--text-tertiary);
}

.data-table-empty-icon {
  margin-bottom: var(--spacing-4);
  opacity: 0.5;
}

.data-table-empty-text {
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-4);
}

.data-table-empty-action {
  display: flex;
  gap: var(--spacing-2);
}

:deep(.data-table) {
  background: transparent;
  border: none;
}

:deep(.data-table .el-table__header) {
  background: var(--bg-spotlight);
}

:deep(.data-table .el-table__header th) {
  background: var(--bg-spotlight);
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
  border-color: var(--border-color);
}

:deep(.data-table .el-table__body tr) {
  background: transparent;
}

:deep(.data-table .el-table__body tr:hover > td) {
  background: var(--bg-hover);
}

:deep(.data-table .el-table__body td) {
  border-color: var(--border-color);
  color: var(--text-primary);
}

:deep(.data-table .el-table__row) {
  transition: var(--transition-colors);
}

.data-table-pagination {
  display: flex;
  justify-content: flex-end;
  padding: var(--spacing-4);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-top: none;
  border-radius: 0 0 var(--radius-card) var(--radius-card);
}

:deep(.data-table-pagination .el-pagination) {
  display: flex;
  gap: var(--spacing-2);
}
</style>
