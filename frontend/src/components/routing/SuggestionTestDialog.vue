<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="测试规则建议"
    width="800px"
    :close-on-click-modal="false"
  >
    <div class="test-container">
      <!-- 测试查询输入 -->
      <div class="input-section">
        <h4>测试查询</h4>
        <el-input
          v-model="testQueries"
          type="textarea"
          :rows="6"
          placeholder="请输入测试查询，每行一个查询&#10;例如：&#10;查询所有物理机&#10;物理机信息统计&#10;服务器列表"
        />
        <div class="actions">
          <el-button type="primary" @click="runTest" :loading="testing">
            <el-icon><CaretRight /></el-icon>
            运行测试
          </el-button>
          <el-button @click="clearResults">清空结果</el-button>
        </div>
      </div>

      <!-- 测试结果 -->
      <div class="results-section" v-if="testResults.length > 0">
        <h4>测试结果</h4>
        <div class="summary">
          <el-tag type="success">改进: {{ improvedCount }}</el-tag>
          <el-tag type="info">无变化: {{ unchangedCount }}</el-tag>
          <el-tag type="warning">变差: {{ worseCount }}</el-tag>
        </div>

        <el-table :data="testResults" border class="results-table">
          <el-table-column prop="query" label="查询" min-width="200" />
          
          <el-table-column label="无建议" width="150">
            <template #default="{ row }">
              <div class="result-cell">
                <el-tag size="small" :type="getIntentType(row.without_suggestion.intent)">
                  {{ getIntentLabel(row.without_suggestion.intent) }}
                </el-tag>
                <span class="confidence">
                  {{ (row.without_suggestion.confidence * 100).toFixed(0) }}%
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="有建议" width="150">
            <template #default="{ row }">
              <div class="result-cell">
                <el-tag size="small" :type="getIntentType(row.with_suggestion.intent)">
                  {{ getIntentLabel(row.with_suggestion.intent) }}
                </el-tag>
                <span class="confidence">
                  {{ (row.with_suggestion.confidence * 100).toFixed(0) }}%
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="改进" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.improvement ? 'success' : 'info'"
                size="small"
              >
                {{ row.improvement ? '✓ 改进' : '无变化' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-if="!testing && testResults.length === 0"
        description="输入测试查询并运行测试"
        :image-size="120"
      />
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { testSuggestion } from '@/api/routing'
import { ElMessage } from 'element-plus'
import { CaretRight } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  suggestion: Object
})

const emit = defineEmits(['update:modelValue'])

const testing = ref(false)
const testQueries = ref('')
const testResults = ref([])

// 统计
const improvedCount = computed(() => 
  testResults.value.filter(r => r.improvement).length
)

const unchangedCount = computed(() => 
  testResults.value.filter(r => !r.improvement && !r.worse).length
)

const worseCount = computed(() => 
  testResults.value.filter(r => r.worse).length
)

// 运行测试
const runTest = async () => {
  if (!testQueries.value.trim()) {
    ElMessage.warning('请输入测试查询')
    return
  }
  
  const queries = testQueries.value
    .split('\n')
    .map(q => q.trim())
    .filter(q => q.length > 0)
  
  if (queries.length === 0) {
    ElMessage.warning('请输入有效的测试查询')
    return
  }
  
  testing.value = true
  try {
    const response = await testSuggestion(props.suggestion.id, {
      test_queries: queries
    })
    
    if (response.success) {
      testResults.value = response.data.results.map(result => ({
        ...result,
        improvement: result.with_suggestion.confidence > result.without_suggestion.confidence,
        worse: result.with_suggestion.confidence < result.without_suggestion.confidence
      }))
      
      ElMessage.success('测试完成')
    } else {
      ElMessage.error(response.message || '测试失败')
    }
  } catch (error) {
    console.error('测试失败:', error)
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

// 清空结果
const clearResults = () => {
  testResults.value = []
}

// 工具函数
const getIntentType = (intent) => {
  const types = {
    sql: 'success',
    rag_report: 'warning',
    rag_knowledge: 'info',
    chat: ''
  }
  return types[intent] || ''
}

const getIntentLabel = (intent) => {
  const labels = {
    sql: 'SQL',
    rag_report: '报告',
    rag_knowledge: '知识',
    chat: '对话'
  }
  return labels[intent] || intent
}
</script>

<style scoped>
.test-container {
  min-height: 400px;
}

.input-section {
  margin-bottom: 24px;
}

.input-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 12px;
}

.results-section {
  margin-top: 24px;
}

.results-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.summary {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.results-table {
  margin-top: 12px;
}

.result-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.confidence {
  font-size: 12px;
  color: #909399;
}
</style>
