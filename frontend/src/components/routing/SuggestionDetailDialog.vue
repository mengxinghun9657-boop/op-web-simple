<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="规则建议详情"
    width="700px"
    :close-on-click-modal="false"
  >
    <div v-if="suggestion" v-loading="loading" class="detail-content">
      <!-- 基本信息 -->
      <div class="info-section">
        <h3>基本信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="查询模式">
            {{ suggestion.pattern }}
          </el-descriptions-item>
          <el-descriptions-item label="建议意图">
            <el-tag :type="getIntentType(suggestion.suggested_intent)">
              {{ getIntentLabel(suggestion.suggested_intent) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            <el-progress
              :percentage="Math.round(suggestion.confidence * 100)"
              :color="getConfidenceColor(suggestion.confidence)"
            />
          </el-descriptions-item>
          <el-descriptions-item label="支持数">
            <el-tag type="success">{{ suggestion.support_count }} 条反馈</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(suggestion.status)">
              {{ getStatusLabel(suggestion.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(suggestion.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 支持证据 -->
      <div class="info-section" v-if="evidence">
        <h3>支持证据</h3>
        
        <!-- 示例查询 -->
        <div class="evidence-item" v-if="evidence.sample_queries?.length">
          <h4>示例查询</h4>
          <el-tag
            v-for="(query, index) in evidence.sample_queries"
            :key="index"
            class="query-tag"
            type="info"
          >
            {{ query }}
          </el-tag>
        </div>

        <!-- 共同模式 -->
        <div class="evidence-item" v-if="evidence.common_patterns?.length">
          <h4>共同模式</h4>
          <el-tag
            v-for="(pattern, index) in evidence.common_patterns"
            :key="index"
            class="query-tag"
          >
            {{ pattern }}
          </el-tag>
        </div>

        <!-- 错误率 -->
        <div class="evidence-item" v-if="evidence.error_rate !== undefined">
          <h4>错误率</h4>
          <el-progress
            :percentage="Math.round(evidence.error_rate * 100)"
            :color="getErrorRateColor(evidence.error_rate)"
            :stroke-width="12"
          />
        </div>

        <!-- 反馈记录ID -->
        <div class="evidence-item" v-if="evidence.feedback_ids?.length">
          <h4>关联反馈记录</h4>
          <p class="feedback-count">共 {{ evidence.feedback_ids.length }} 条反馈记录</p>
        </div>
      </div>

      <!-- 审核信息（如果已审核） -->
      <div class="info-section" v-if="suggestion.status !== 'pending'">
        <h3>审核信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item
            v-if="suggestion.adopted_by"
            label="审核人"
          >
            {{ suggestion.adopted_by || suggestion.rejected_by }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="suggestion.adopted_at || suggestion.rejected_at"
            label="审核时间"
          >
            {{ formatDate(suggestion.adopted_at || suggestion.rejected_at) }}
          </el-descriptions-item>
          <el-descriptions-item
            v-if="suggestion.created_rule_id"
            label="创建的规则ID"
          >
            <el-tag type="success">{{ suggestion.created_rule_id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item
            v-if="suggestion.reject_reason"
            label="拒绝原因"
            :span="2"
          >
            {{ suggestion.reject_reason }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { getSuggestionDetail } from '@/api/routing'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  suggestion: Object
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const detailData = ref(null)

const evidence = computed(() => {
  if (!props.suggestion?.evidence) return null
  if (typeof props.suggestion.evidence === 'string') {
    try {
      return JSON.parse(props.suggestion.evidence)
    } catch {
      return null
    }
  }
  return props.suggestion.evidence
})

// 加载详情
const loadDetail = async () => {
  if (!props.suggestion?.id) return
  
  loading.value = true
  try {
    const response = await getSuggestionDetail(props.suggestion.id)
    if (response.success) {
      detailData.value = response.data
    }
  } catch (error) {
    console.error('加载详情失败:', error)
    ElMessage.error('加载详情失败')
  } finally {
    loading.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (visible && props.suggestion) {
    loadDetail()
  }
})

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
    sql: 'SQL查询',
    rag_report: '报告查询',
    rag_knowledge: '知识查询',
    chat: '对话'
  }
  return labels[intent] || intent
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.9) return '#67c23a'
  if (confidence >= 0.7) return '#e6a23c'
  return '#f56c6c'
}

const getErrorRateColor = (rate) => {
  if (rate >= 0.8) return '#f56c6c'
  if (rate >= 0.5) return '#e6a23c'
  return '#67c23a'
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    adopted: 'success',
    rejected: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待审核',
    adopted: '已采纳',
    rejected: '已拒绝'
  }
  return labels[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.detail-content {
  max-height: 600px;
  overflow-y: auto;
}

.info-section {
  margin-bottom: 24px;
}

.info-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.evidence-item {
  margin-bottom: 16px;
}

.evidence-item h4 {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
}

.query-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.feedback-count {
  color: #909399;
  font-size: 14px;
}
</style>
