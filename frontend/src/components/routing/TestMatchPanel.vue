<template>
  <div class="test-match-panel">
    <div class="test-input mb-4">
      <el-input
        v-model="testQueriesText"
        type="textarea"
        :rows="5"
        placeholder="请输入测试查询（每行一个）&#10;例如：&#10;查询192.168.1.1的信息&#10;服务器状态如何&#10;10.0.0.1有什么问题"
      />
      
      <div class="mt-2 flex justify-between">
        <div>
          <el-button 
            type="primary" 
            :loading="testing"
            :disabled="!hasQueries"
            @click="handleTest"
          >
            <i class="el-icon-search mr-1"></i>
            测试匹配
          </el-button>
          
          <el-button @click="handleImport">
            <i class="el-icon-upload2 mr-1"></i>
            导入文件
          </el-button>
        </div>
        
        <el-button 
          v-if="testResults"
          @click="handleExport"
        >
          <i class="el-icon-download mr-1"></i>
          导出结果
        </el-button>
      </div>
    </div>

    <!-- 测试结果 -->
    <div v-if="testResults" class="test-results">
      <!-- 统计信息 -->
      <div class="statistics mb-4 p-4 bg-gray-50 rounded">
        <div class="flex items-center justify-between">
          <div>
            <span class="font-medium">匹配率：</span>
            <span class="text-2xl font-bold ml-2" :class="getMatchRateClass()">
              {{ (testResults.match_rate * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="text-sm text-gray-600">
            匹配 {{ testResults.matched_count }} / 总计 {{ testResults.total_count }}
          </div>
        </div>
        
        <el-progress
          :percentage="testResults.match_rate * 100"
          :color="getMatchRateColor()"
          class="mt-2"
        />
      </div>

      <!-- 结果列表 -->
      <div class="results-list">
        <div
          v-for="(result, index) in testResults.results"
          :key="index"
          class="result-item mb-2 p-3 border rounded"
          :class="result.matched ? 'border-green-300 bg-green-50' : 'border-gray-300'"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center mb-1">
                <el-tag 
                  :type="result.matched ? 'success' : 'info'" 
                  size="small"
                  class="mr-2"
                >
                  {{ result.matched ? '匹配' : '不匹配' }}
                </el-tag>
                <span class="text-sm text-gray-500">
                  置信度: {{ (result.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              
              <div class="query-text">
                <span v-if="!result.matched">{{ result.query }}</span>
                <span v-else v-html="highlightMatch(result)"></span>
              </div>
              
              <div v-if="result.matched && result.match_position" class="text-xs text-gray-500 mt-1">
                匹配位置: {{ result.match_position[0] }} - {{ result.match_position[1] }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="输入测试查询后将显示匹配结果"
      :image-size="100"
    />

    <!-- 文件导入对话框 -->
    <input
      ref="fileInput"
      type="file"
      accept=".txt,.csv"
      style="display: none"
      @change="handleFileChange"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { testMatch } from '@/api/routing-assistant'

export default {
  name: 'TestMatchPanel',
  props: {
    regex: {
      type: String,
      required: true
    }
  },
  emits: ['test', 'save-test-case'],
  setup(props, { emit }) {
    const testQueriesText = ref('')
    const testing = ref(false)
    const testResults = ref(null)
    const fileInput = ref(null)

    const hasQueries = computed(() => {
      return testQueriesText.value.trim().length > 0
    })

    const getMatchRateClass = () => {
      const rate = testResults.value?.match_rate || 0
      if (rate >= 0.8) return 'text-green-600'
      if (rate >= 0.5) return 'text-yellow-600'
      return 'text-red-600'
    }

    const getMatchRateColor = () => {
      const rate = testResults.value?.match_rate || 0
      if (rate >= 0.8) return '#67c23a'
      if (rate >= 0.5) return '#e6a23c'
      return '#f56c6c'
    }

    const handleTest = async () => {
      if (!props.regex) {
        ElMessage.warning('请先输入正则表达式')
        return
      }

      const queries = testQueriesText.value
        .split('\n')
        .map(q => q.trim())
        .filter(q => q.length > 0)

      if (queries.length === 0) {
        ElMessage.warning('请输入至少一个测试查询')
        return
      }

      testing.value = true

      try {
        const response = await testMatch(props.regex, queries)
        
        if (response.success) {
          testResults.value = response.data
          emit('test', response.data)
          ElMessage.success('测试完成')
        } else {
          ElMessage.error(response.message || '测试失败')
        }
      } catch (error) {
        console.error('测试失败:', error)
        ElMessage.error('测试失败，请稍后重试')
      } finally {
        testing.value = false
      }
    }

    const highlightMatch = (result) => {
      if (!result.matched || !result.matched_text) {
        return result.query
      }

      const [start, end] = result.match_position
      const before = result.query.substring(0, start)
      const match = result.query.substring(start, end)
      const after = result.query.substring(end)

      return `${before}<span class="bg-yellow-200 font-medium">${match}</span>${after}`
    }

    const handleImport = () => {
      fileInput.value?.click()
    }

    const handleFileChange = (event) => {
      const file = event.target.files[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (e) => {
        testQueriesText.value = e.target.result
        ElMessage.success('文件导入成功')
      }
      reader.onerror = () => {
        ElMessage.error('文件读取失败')
      }
      reader.readAsText(file)

      // 清空input，允许重复选择同一文件
      event.target.value = ''
    }

    const handleExport = () => {
      if (!testResults.value) return

      const content = testResults.value.results
        .map(r => `${r.matched ? '✓' : '✗'} ${r.query}`)
        .join('\n')

      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `test-results-${Date.now()}.txt`
      a.click()
      URL.revokeObjectURL(url)

      ElMessage.success('结果已导出')
    }

    return {
      testQueriesText,
      testing,
      testResults,
      fileInput,
      hasQueries,
      getMatchRateClass,
      getMatchRateColor,
      handleTest,
      highlightMatch,
      handleImport,
      handleFileChange,
      handleExport
    }
  }
}
</script>

<style scoped>
.test-match-panel {
  width: 100%;
}

.result-item {
  transition: all 0.3s;
}

.result-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.query-text {
  font-family: 'Courier New', monospace;
  font-size: 14px;
}
</style>
