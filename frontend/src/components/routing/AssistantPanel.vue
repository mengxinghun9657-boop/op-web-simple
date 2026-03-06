<template>
  <div class="assistant-panel">
    <!-- 描述生成 -->
    <div class="description-section mb-4">
      <div class="flex items-center justify-between mb-2">
        <span class="font-medium">规则描述</span>
        <el-button 
          size="small" 
          :loading="generating"
          @click="handleGenerateDescription"
        >
          <i class="el-icon-magic-stick mr-1"></i>
          智能生成
        </el-button>
      </div>
      <el-input
        v-model="description"
        type="textarea"
        :rows="3"
        placeholder="描述此规则的用途和适用场景"
        @input="$emit('update:description', description)"
      />
    </div>

    <!-- 关键词 -->
    <div class="keywords-section mb-4">
      <div class="flex items-center justify-between mb-2">
        <span class="font-medium">关键词</span>
        <el-button 
          size="small"
          :loading="extracting"
          @click="handleExtractKeywords"
        >
          <i class="el-icon-search mr-1"></i>
          提取关键词
        </el-button>
      </div>
      <div class="keywords-list">
        <el-tag
          v-for="(keyword, index) in keywords"
          :key="index"
          closable
          class="mr-2 mb-2"
          @close="removeKeyword(index)"
        >
          {{ keyword.word }} ({{ (keyword.weight * 100).toFixed(0) }}%)
        </el-tag>
        <el-input
          v-if="showKeywordInput"
          v-model="newKeyword"
          size="small"
          class="w-32"
          @keyup.enter="addKeyword"
          @blur="addKeyword"
        />
        <el-button
          v-else
          size="small"
          @click="showKeywordInput = true"
        >
          + 添加
        </el-button>
      </div>
    </div>

    <!-- 表推荐 -->
    <div class="tables-section mb-4">
      <div class="flex items-center justify-between mb-2">
        <span class="font-medium">推荐表</span>
        <el-button 
          size="small"
          :loading="recommending"
          @click="handleRecommendTables"
        >
          <i class="el-icon-data-analysis mr-1"></i>
          智能推荐
        </el-button>
      </div>
      <el-select
        v-model="selectedTables"
        multiple
        filterable
        placeholder="选择相关表"
        class="w-full"
        @change="$emit('update:tables', selectedTables)"
      >
        <el-option
          v-for="table in recommendedTables"
          :key="table.name"
          :label="`${table.name} (${table.category})`"
          :value="table.name"
        >
          <div class="flex items-center justify-between">
            <span>{{ table.name }}</span>
            <el-tag size="small" type="info">{{ (table.relevance_score * 100).toFixed(0) }}%</el-tag>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- 优先级建议 -->
    <div class="priority-section">
      <div class="flex items-center justify-between mb-2">
        <span class="font-medium">优先级</span>
        <el-button 
          size="small"
          :loading="suggesting"
          @click="handleSuggestPriority"
        >
          <i class="el-icon-star-off mr-1"></i>
          智能建议
        </el-button>
      </div>
      <el-slider
        v-model="priority"
        :min="1"
        :max="100"
        show-input
        @change="$emit('update:priority', priority)"
      />
      <div v-if="prioritySuggestion" class="text-sm text-gray-600 mt-2">
        <p>建议: {{ prioritySuggestion.suggested_priority }} ({{ prioritySuggestion.category }})</p>
        <p>{{ prioritySuggestion.reason }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  extractKeywords, 
  recommendTables, 
  generateDescription,
  suggestPriority 
} from '@/api/routing-assistant'

export default {
  name: 'AssistantPanel',
  props: {
    pattern: String,
    intentType: String,
    patternType: String,
    currentDescription: String,
    currentKeywords: Array,
    currentTables: Array,
    currentPriority: Number
  },
  emits: ['update:description', 'update:keywords', 'update:tables', 'update:priority'],
  setup(props, { emit }) {
    const description = ref(props.currentDescription || '')
    const keywords = ref([])
    const recommendedTables = ref([])
    const selectedTables = ref(props.currentTables || [])
    const priority = ref(props.currentPriority || 50)
    const prioritySuggestion = ref(null)
    
    const generating = ref(false)
    const extracting = ref(false)
    const recommending = ref(false)
    const suggesting = ref(false)
    
    const showKeywordInput = ref(false)
    const newKeyword = ref('')

    // 监听 props 变化，同步内部状态
    watch(() => props.currentDescription, (newVal) => {
      if (newVal !== undefined) description.value = newVal
    })
    
    watch(() => props.currentTables, (newVal) => {
      if (newVal) selectedTables.value = newVal
    }, { deep: true })
    
    watch(() => props.currentPriority, (newVal) => {
      if (newVal !== undefined) priority.value = newVal
    })
    
    watch(() => props.currentKeywords, (newVal) => {
      if (newVal && newVal.length > 0) {
        // 转换为内部格式
        keywords.value = newVal.map(k => 
          typeof k === 'string' ? { word: k, weight: 0.5, type: 'custom' } : k
        )
      }
    }, { deep: true, immediate: true })

    const handleGenerateDescription = async () => {
      if (!props.pattern) {
        ElMessage.warning('请先输入匹配模式')
        return
      }
      
      generating.value = true
      try {
        const response = await generateDescription(
          props.pattern,
          props.intentType,
          keywords.value.map(k => k.word)
        )
        if (response.success) {
          description.value = response.data.description
          emit('update:description', description.value)
          ElMessage.success('描述生成成功')
        } else {
          ElMessage.error(response.message || '描述生成失败')
        }
      } catch (error) {
        console.error('描述生成失败:', error)
        ElMessage.error('描述生成失败')
      } finally {
        generating.value = false
      }
    }

    const handleExtractKeywords = async () => {
      if (!props.pattern) {
        ElMessage.warning('请先输入匹配模式')
        return
      }
      
      if (!props.patternType) {
        ElMessage.warning('无法确定模式类型')
        return
      }
      
      extracting.value = true
      try {
        const response = await extractKeywords(props.pattern, props.patternType)
        if (response.success) {
          keywords.value = response.data.keywords
          // 发送更新事件
          emit('update:keywords', keywords.value.map(k => k.word))
          ElMessage.success('关键词提取成功')
        } else {
          ElMessage.error(response.message || '关键词提取失败')
        }
      } catch (error) {
        console.error('关键词提取失败:', error)
        ElMessage.error('关键词提取失败')
      } finally {
        extracting.value = false
      }
    }

    const handleRecommendTables = async () => {
      if (keywords.value.length === 0) {
        ElMessage.warning('请先提取关键词')
        return
      }
      
      recommending.value = true
      try {
        const response = await recommendTables(
          keywords.value.map(k => k.word),
          props.intentType
        )
        if (response.success) {
          recommendedTables.value = response.data.tables
          ElMessage.success('表推荐成功')
        } else {
          ElMessage.error(response.message || '表推荐失败')
        }
      } catch (error) {
        console.error('表推荐失败:', error)
        ElMessage.error('表推荐失败')
      } finally {
        recommending.value = false
      }
    }

    const handleSuggestPriority = async () => {
      if (!props.pattern) {
        ElMessage.warning('请先输入匹配模式')
        return
      }
      
      suggesting.value = true
      try {
        const response = await suggestPriority(
          props.pattern,
          props.intentType,
          keywords.value.map(k => k.word)
        )
        if (response.success) {
          prioritySuggestion.value = response.data
          priority.value = response.data.suggested_priority
          emit('update:priority', priority.value)
          ElMessage.success('优先级建议成功')
        } else {
          ElMessage.error(response.message || '优先级建议失败')
        }
      } catch (error) {
        console.error('优先级建议失败:', error)
        ElMessage.error('优先级建议失败')
      } finally {
        suggesting.value = false
      }
    }

    const addKeyword = () => {
      if (newKeyword.value.trim()) {
        keywords.value.push({
          word: newKeyword.value.trim(),
          weight: 0.5,
          type: 'custom'
        })
        emit('update:keywords', keywords.value.map(k => k.word))
        newKeyword.value = ''
      }
      showKeywordInput.value = false
    }

    const removeKeyword = (index) => {
      keywords.value.splice(index, 1)
      emit('update:keywords', keywords.value.map(k => k.word))
    }
    
    // 监听 description 变化
    watch(description, (newVal) => {
      emit('update:description', newVal)
    })
    
    // 监听 selectedTables 变化
    watch(selectedTables, (newVal) => {
      emit('update:tables', newVal)
    }, { deep: true })
    
    // 监听 priority 变化
    watch(priority, (newVal) => {
      emit('update:priority', newVal)
    })

    return {
      description,
      keywords,
      recommendedTables,
      selectedTables,
      priority,
      prioritySuggestion,
      generating,
      extracting,
      recommending,
      suggesting,
      showKeywordInput,
      newKeyword,
      handleGenerateDescription,
      handleExtractKeywords,
      handleRecommendTables,
      handleSuggestPriority,
      addKeyword,
      removeKeyword
    }
  }
}
</script>
