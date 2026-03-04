<template>
  <div class="validation-panel">
    <div v-if="validationResult" class="validation-content">
      <!-- 验证成功 -->
      <el-alert
        v-if="validationResult.is_valid && !hasConflicts"
        type="success"
        :closable="false"
        class="mb-4"
      >
        <template #title>
          <i class="el-icon-circle-check mr-2"></i>
          正则表达式验证通过
        </template>
      </el-alert>

      <!-- 语法错误 -->
      <el-alert
        v-if="!validationResult.is_valid"
        type="error"
        :closable="false"
        class="mb-4"
      >
        <template #title>
          <i class="el-icon-circle-close mr-2"></i>
          正则表达式语法错误
        </template>
        <div class="mt-2">
          <div 
            v-for="(error, index) in validationResult.syntax_errors" 
            :key="index"
            class="error-item mb-2"
          >
            <p class="font-medium">{{ error.message }}</p>
            <p v-if="error.position !== undefined" class="text-sm text-gray-600">
              位置：第 {{ error.position }} 个字符
            </p>
            <p v-if="error.suggestion" class="text-sm text-blue-600">
              建议：{{ error.suggestion }}
            </p>
          </div>
        </div>
      </el-alert>

      <!-- 冲突警告 -->
      <el-alert
        v-if="hasConflicts"
        :type="getConflictAlertType()"
        :closable="false"
        class="mb-4"
      >
        <template #title>
          <i class="el-icon-warning mr-2"></i>
          检测到规则冲突 ({{ validationResult.conflicts.length }} 个)
        </template>
        <div class="mt-2">
          <el-collapse v-model="activeConflicts" accordion>
            <el-collapse-item
              v-for="(conflict, index) in validationResult.conflicts"
              :key="index"
              :name="index"
            >
              <template #title>
                <div class="flex items-center">
                  <el-tag 
                    :type="getSeverityType(conflict.severity)" 
                    size="small"
                    class="mr-2"
                  >
                    {{ conflict.severity }}
                  </el-tag>
                  <span>规则 #{{ conflict.rule_id }} - {{ conflict.conflict_type }}</span>
                </div>
              </template>
              <div class="conflict-detail p-2">
                <p class="mb-2">
                  <span class="font-medium">冲突模式：</span>
                  <code class="bg-gray-100 px-2 py-1 rounded">{{ conflict.pattern }}</code>
                </p>
                <p class="text-sm text-gray-600">{{ conflict.description }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-alert>

      <!-- 复杂度评分 -->
      <div class="complexity-score p-4 bg-gray-50 rounded">
        <div class="flex items-center justify-between">
          <span class="font-medium">复杂度评分：</span>
          <div class="flex items-center">
            <el-progress
              :percentage="(validationResult.complexity_score / 10) * 100"
              :color="getComplexityColor(validationResult.complexity_score)"
              :show-text="false"
              class="w-32 mr-2"
            />
            <span :class="getComplexityClass(validationResult.complexity_score)">
              {{ validationResult.complexity_score.toFixed(1) }} / 10
            </span>
          </div>
        </div>
        <p class="text-sm text-gray-600 mt-2">
          {{ getComplexityDescription(validationResult.complexity_score) }}
        </p>
      </div>

      <!-- 详情展开/收起 -->
      <div v-if="showDetails" class="details-toggle mt-4">
        <el-button 
          text 
          type="primary"
          @click="toggleDetails"
        >
          {{ detailsExpanded ? '收起详情' : '展开详情' }}
          <i :class="detailsExpanded ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
        </el-button>
        
        <div v-if="detailsExpanded" class="details-content mt-4 p-4 bg-gray-50 rounded">
          <pre class="text-sm">{{ JSON.stringify(validationResult, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="输入正则表达式后将显示验证结果"
      :image-size="100"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'ValidationPanel',
  props: {
    validationResult: {
      type: Object,
      default: null
    },
    showDetails: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const activeConflicts = ref(null)
    const detailsExpanded = ref(false)

    const hasConflicts = computed(() => {
      return props.validationResult?.conflicts?.length > 0
    })

    const getConflictAlertType = () => {
      if (!props.validationResult?.conflicts) return 'warning'
      
      const hasHigh = props.validationResult.conflicts.some(c => c.severity === '高')
      if (hasHigh) return 'error'
      
      const hasMedium = props.validationResult.conflicts.some(c => c.severity === '中')
      if (hasMedium) return 'warning'
      
      return 'info'
    }

    const getSeverityType = (severity) => {
      const map = {
        '高': 'danger',
        '中': 'warning',
        '低': 'info'
      }
      return map[severity] || 'info'
    }

    const getComplexityColor = (score) => {
      if (score <= 3) return '#67c23a'
      if (score <= 6) return '#e6a23c'
      return '#f56c6c'
    }

    const getComplexityClass = (score) => {
      if (score <= 3) return 'text-green-600 font-medium'
      if (score <= 6) return 'text-yellow-600 font-medium'
      return 'text-red-600 font-medium'
    }

    const getComplexityDescription = (score) => {
      if (score <= 3) return '简单：易于理解和维护'
      if (score <= 6) return '中等：需要一定的正则表达式知识'
      return '复杂：建议简化或添加详细注释'
    }

    const toggleDetails = () => {
      detailsExpanded.value = !detailsExpanded.value
    }

    return {
      activeConflicts,
      detailsExpanded,
      hasConflicts,
      getConflictAlertType,
      getSeverityType,
      getComplexityColor,
      getComplexityClass,
      getComplexityDescription,
      toggleDetails
    }
  }
}
</script>

<style scoped>
.validation-panel {
  width: 100%;
}

.error-item {
  padding: 8px;
  background-color: #fef0f0;
  border-left: 3px solid #f56c6c;
  border-radius: 4px;
}

.conflict-detail code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.details-content pre {
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
