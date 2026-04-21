<template>
  <div class="iql-syntax-help">
    <el-input
      v-model="searchText"
      placeholder="搜索字段..."
      clearable
      style="margin-bottom: 16px"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>
    
    <el-collapse v-model="activeNames">
      <el-collapse-item
        v-for="category in filteredCategories"
        :key="category.name"
        :title="category.name"
        :name="category.name"
      >
        <div class="field-list">
          <div
            v-for="field in category.fields"
            :key="field.name"
            class="field-item"
          >
            <div class="field-header">
              <span class="field-name">{{ field.name }}</span>
              <el-tag size="small" type="info">{{ field.type }}</el-tag>
            </div>
            <div class="field-operators">
              <span class="operators-label">支持操作符：</span>
              <el-tag
                v-for="op in field.operators"
                :key="op"
                size="small"
                class="operator-tag"
              >
                {{ op }}
              </el-tag>
            </div>
            <div class="field-example">
              <span class="example-label">示例：</span>
              <code class="example-code">{{ field.example }}</code>
            </div>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const searchText = ref('')
const activeNames = ref(['常用字段'])

const categories = [
  {
    name: '常用字段',
    fields: [
      {
        name: '负责人',
        type: '人员',
        operators: ['=', '!=', 'in', 'not in', 'is empty', 'is not empty'],
        example: '负责人 = v_liuxiang'
      },
      {
        name: '流程状态',
        type: '状态',
        operators: ['<', '<=', '=', '>', '>=', '!=', 'in', 'not in', 'is empty', 'is not empty'],
        example: '流程状态 in (新建, 开发中, 进行中)'
      },
      {
        name: '类型',
        type: '类型',
        operators: ['=', '!=', 'in', 'not in', 'is empty', 'is not empty'],
        example: '类型 in (Bug, Story, Task)'
      },
      {
        name: '所属计划',
        type: '计划',
        operators: ['=', '!=', 'in', 'not in', 'is empty', 'is not empty'],
        example: '所属计划 = 测试/测试1/测试3'
      }
    ]
  },
  {
    name: '时间字段',
    fields: [
      {
        name: '创建时间',
        type: '日期时间',
        operators: ['>', '<', '=', 'is empty', 'is not empty'],
        example: '创建时间 > "2025-01-01 00:00:00" AND 创建时间 < "2025-01-31 23:59:59"'
      },
      {
        name: '最后修改时间',
        type: '日期时间',
        operators: ['>', '<', '=', 'is empty', 'is not empty'],
        example: '最后修改时间 > "2025-01-01 00:00:00"'
      },
      {
        name: '完成时间',
        type: '日期时间',
        operators: ['>', '<', '=', 'is empty', 'is not empty'],
        example: '完成时间 < "2025-01-31 23:59:59"'
      }
    ]
  },
  {
    name: '文本字段',
    fields: [
      {
        name: '标题',
        type: '文本',
        operators: ['~', '!~', 'is empty', 'is not empty'],
        example: '标题 ~ "测试"'
      },
      {
        name: '关键字',
        type: '文本',
        operators: ['~'],
        example: '关键字 ~ 测试'
      },
      {
        name: '测试『Label』标签',
        type: '标签',
        operators: ['=', '!=', 'in', 'not in', 'is empty', 'is not empty'],
        example: '测试『Label』标签 = aaa'
      }
    ]
  },
  {
    name: '其他字段',
    fields: [
      {
        name: '测试『数字』',
        type: '数字',
        operators: ['<', '>', '=', 'is empty', 'is not empty'],
        example: '测试『数字』 > 1'
      },
      {
        name: '测试『URL』',
        type: 'URL',
        operators: ['~', '!~', '=', 'is empty', 'is not empty'],
        example: '测试『URL』 = "www.baidu.com"'
      }
    ]
  }
]

const filteredCategories = computed(() => {
  if (!searchText.value) {
    return categories
  }
  
  const search = searchText.value.toLowerCase()
  return categories
    .map(category => ({
      ...category,
      fields: category.fields.filter(field =>
        field.name.toLowerCase().includes(search) ||
        field.type.toLowerCase().includes(search)
      )
    }))
    .filter(category => category.fields.length > 0)
})
</script>

<style scoped>
.iql-syntax-help {
  max-height: 600px;
  overflow-y: auto;
}

.iql-syntax-help :deep(.el-input__wrapper) {
  transition: all var(--transition-fast);
}

.iql-syntax-help :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary-400);
}

.iql-syntax-help :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.field-item {
  padding: var(--spacing-4);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(249, 250, 251, 0.9));
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.field-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, var(--color-primary-500), var(--color-secondary-500));
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.field-item:hover {
  border-color: var(--color-primary-300);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.08);
  transform: translateX(2px);
}

.field-item:hover::before {
  opacity: 1;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-3);
}

.field-name {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  font-size: var(--font-size-base);
  letter-spacing: -0.01em;
}

.field-operators {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
  padding: var(--spacing-2) 0;
}

.operators-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.operator-tag {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.operator-tag:hover {
  transform: scale(1.05);
}

.field-example {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: rgba(64, 158, 255, 0.03);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary-400);
}

.example-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  flex-shrink: 0;
  font-weight: var(--font-medium);
}

.example-code {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: var(--font-size-sm);
  color: var(--color-primary-600);
  background-color: rgba(255, 255, 255, 0.8);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  word-break: break-all;
  line-height: 1.5;
}

/* 滚动条样式 */
.iql-syntax-help::-webkit-scrollbar {
  width: 6px;
}

.iql-syntax-help::-webkit-scrollbar-track {
  background: var(--bg-elevated);
  border-radius: 3px;
}

.iql-syntax-help::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
  transition: background var(--transition-fast);
}

.iql-syntax-help::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
</style>
