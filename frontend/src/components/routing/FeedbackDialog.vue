<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="路由错误反馈"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="feedback-container">
      <!-- 当前路由信息 -->
      <div class="current-routing">
        <h4>当前路由结果</h4>
        <div class="routing-info">
          <div class="info-item">
            <span class="label">意图类型:</span>
            <el-tag :type="getIntentType(routingInfo.intent_type)" size="small">
              {{ getIntentLabel(routingInfo.intent_type) }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">置信度:</span>
            <el-progress
              :percentage="routingInfo.confidence * 100"
              :color="getConfidenceColor(routingInfo.confidence)"
              :stroke-width="8"
              style="width: 200px"
            />
          </div>
          <div class="info-item">
            <span class="label">路由方法:</span>
            <el-tag type="info" size="small">
              {{ getRoutingMethodLabel(routingInfo.routing_method) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 反馈表单 -->
      <el-form :model="feedbackForm" label-width="100px" class="feedback-form">
        <el-form-item label="正确意图" required>
          <el-select
            v-model="feedbackForm.correct_intent"
            placeholder="请选择正确的意图类型"
            style="width: 100%"
          >
            <el-option label="SQL 查询" value="sql">
              <span class="option-content">
                <el-icon><Coin /></el-icon>
                <span>SQL 查询</span>
              </span>
            </el-option>
            <el-option label="报告查询" value="rag_report">
              <span class="option-content">
                <el-icon><Document /></el-icon>
                <span>报告查询</span>
              </span>
            </el-option>
            <el-option label="知识查询" value="rag_knowledge">
              <span class="option-content">
                <el-icon><Reading /></el-icon>
                <span>知识查询</span>
              </span>
            </el-option>
            <el-option label="对话" value="chat">
              <span class="option-content">
                <el-icon><ChatDotRound /></el-icon>
                <span>对话</span>
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="反馈备注">
          <el-input
            v-model="feedbackForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请描述为什么当前路由结果不正确（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <!-- 提示信息 -->
      <el-alert
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          您的反馈将帮助我们改进路由准确率
        </template>
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        @click="submitFeedback"
        :loading="submitting"
        :disabled="!feedbackForm.correct_intent"
      >
        提交反馈
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Coin,
  Document,
  Reading,
  ChatDotRound
} from '@element-plus/icons-vue'
import { submitRoutingFeedback } from '@/api/routing'

const props = defineProps({
  modelValue: Boolean,
  routingInfo: {
    type: Object,
    default: () => ({
      routing_log_id: null,
      intent_type: '',
      confidence: 0,
      routing_method: ''
    })
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const submitting = ref(false)
const feedbackForm = ref({
  correct_intent: '',
  comment: ''
})

// 监听对话框打开，重置表单
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    feedbackForm.value = {
      correct_intent: '',
      comment: ''
    }
  }
})

// 提交反馈
const submitFeedback = async () => {
  if (!feedbackForm.value.correct_intent) {
    ElMessage.warning('请选择正确的意图类型')
    return
  }

  if (!props.routingInfo.routing_log_id) {
    ElMessage.error('缺少路由日志ID')
    return
  }

  submitting.value = true
  try {
    const response = await submitRoutingFeedback({
      routing_log_id: props.routingInfo.routing_log_id,
      correct_intent: feedbackForm.value.correct_intent,
      comment: feedbackForm.value.comment
    })

    if (response.success) {
      ElMessage.success('反馈提交成功，感谢您的反馈！')
      emit('update:modelValue', false)
      emit('success')
    } else {
      ElMessage.error(response.message || '反馈提交失败')
    }
  } catch (error) {
    console.error('反馈提交失败:', error)
    ElMessage.error('反馈提交失败')
  } finally {
    submitting.value = false
  }
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
    sql: 'SQL 查询',
    rag_report: '报告查询',
    rag_knowledge: '知识查询',
    chat: '对话'
  }
  return labels[intent] || intent
}

const getRoutingMethodLabel = (method) => {
  const labels = {
    forced_rule: '强制规则',
    routing_rule: '路由规则',
    ernie_api: 'ERNIE 分类',
    similarity: '语义相似度',
    keyword: '关键词规则'
  }
  return labels[method] || method
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.feedback-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.current-routing {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.current-routing h4 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.routing-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-item .label {
  font-size: 14px;
  color: #606266;
  min-width: 80px;
}

.feedback-form {
  margin-top: 8px;
}

.option-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-content .el-icon {
  font-size: 16px;
}
</style>
