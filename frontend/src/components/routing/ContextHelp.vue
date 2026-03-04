<template>
  <el-popover
    :placement="placement"
    :width="width"
    trigger="hover"
    :show-after="showAfter"
  >
    <template #reference>
      <el-icon class="help-icon" :class="iconClass">
        <QuestionFilled />
      </el-icon>
    </template>
    
    <div class="help-content">
      <div v-if="title" class="help-title">{{ title }}</div>
      <div class="help-description">{{ description }}</div>
      
      <div v-if="examples && examples.length > 0" class="help-examples">
        <div class="examples-title">示例：</div>
        <div
          v-for="(example, index) in examples"
          :key="index"
          class="example-item"
        >
          <code>{{ example }}</code>
        </div>
      </div>
      
      <div v-if="tips && tips.length > 0" class="help-tips">
        <div class="tips-title">提示：</div>
        <ul class="tips-list">
          <li v-for="(tip, index) in tips" :key="index">{{ tip }}</li>
        </ul>
      </div>
      
      <div v-if="relatedFields && relatedFields.length > 0" class="help-related">
        <div class="related-title">相关字段：</div>
        <div class="related-fields">
          <el-tag
            v-for="field in relatedFields"
            :key="field"
            size="small"
            effect="plain"
          >
            {{ field }}
          </el-tag>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { QuestionFilled } from '@element-plus/icons-vue'

defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    required: true
  },
  examples: {
    type: Array,
    default: () => []
  },
  tips: {
    type: Array,
    default: () => []
  },
  relatedFields: {
    type: Array,
    default: () => []
  },
  placement: {
    type: String,
    default: 'right'
  },
  width: {
    type: Number,
    default: 300
  },
  showAfter: {
    type: Number,
    default: 200
  },
  iconClass: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.help-icon {
  color: #409eff;
  cursor: help;
  font-size: 14px;
  margin-left: 4px;
  vertical-align: middle;
  transition: color 0.3s;
}

.help-icon:hover {
  color: #66b1ff;
}

.help-content {
  font-size: 13px;
  line-height: 1.6;
}

.help-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
}

.help-description {
  color: #606266;
  margin-bottom: 12px;
}

.help-examples {
  margin-bottom: 12px;
}

.examples-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}

.example-item {
  margin-bottom: 4px;
}

.example-item code {
  display: block;
  padding: 6px 8px;
  background-color: #f5f7fa;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #e6a23c;
}

.help-tips {
  margin-bottom: 12px;
}

.tips-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}

.tips-list li {
  margin-bottom: 4px;
}

.help-related {
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.related-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}

.related-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
