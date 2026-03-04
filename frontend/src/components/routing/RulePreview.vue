<template>
  <div class="rule-preview">
    <el-alert
      v-if="hasConflicts"
      title="检测到规则冲突"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    >
      <template #default>
        <div>此规则与 {{ conflictCount }} 个现有规则存在冲突，请仔细检查后再保存。</div>
      </template>
    </el-alert>

    <el-alert
      v-if="impactData && impactData.affected_query_percentage > 10"
      title="高影响规则"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    >
      <template #default>
        <div>此规则预计将影响 {{ impactData.affected_query_percentage.toFixed(1) }}% 的历史查询。</div>
      </template>
    </el-alert>

    <div class="preview-sections">
      <!-- 基本信息 -->
      <el-card class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>基本信息</span>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="规则名称" :span="2">
            {{ ruleData.pattern || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="意图类型">
            <el-tag :type="getIntentTypeColor(ruleData.intent_type)">
              {{ getIntentTypeLabel(ruleData.intent_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="getPriorityColor(ruleData.priority)">
              {{ ruleData.priority }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-switch
              :model-value="ruleData.is_active"
              disabled
              active-text="启用"
              inactive-text="禁用"
            />
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 匹配模式 -->
      <el-card class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Search /></el-icon>
            <span>匹配模式</span>
          </div>
        </template>
        
        <div class="pattern-display">
          <div class="pattern-label">正则表达式:</div>
          <div class="pattern-value">
            <code>{{ ruleData.pattern }}</code>
          </div>
          
          <div v-if="ruleData.natural_language" class="pattern-label" style="margin-top: 12px;">
            原始自然语言:
          </div>
          <div v-if="ruleData.natural_language" class="pattern-value">
            {{ ruleData.natural_language }}
          </div>
          
          <div v-if="ruleData.explanation" class="pattern-label" style="margin-top: 12px;">
            模式说明:
          </div>
          <div v-if="ruleData.explanation" class="pattern-value">
            {{ ruleData.explanation }}
          </div>
        </div>
      </el-card>

      <!-- 智能辅助信息 -->
      <el-card class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><MagicStick /></el-icon>
            <span>智能辅助信息</span>
          </div>
        </template>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="规则描述" v-if="ruleData.description">
            {{ ruleData.description }}
          </el-descriptions-item>
          
          <el-descriptions-item label="关键词" v-if="keywords.length > 0">
            <el-space wrap>
              <el-tag
                v-for="keyword in keywords"
                :key="keyword"
                size="small"
                effect="plain"
              >
                {{ keyword }}
              </el-tag>
            </el-space>
          </el-descriptions-item>
          
          <el-descriptions-item label="推荐表" v-if="recommendedTables.length > 0">
            <el-space wrap>
              <el-tag
                v-for="table in recommendedTables"
                :key="table"
                size="small"
                type="success"
                effect="plain"
              >
                {{ table }}
              </el-tag>
            </el-space>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 测试结果 -->
      <el-card v-if="testResults" class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><CircleCheck /></el-icon>
            <span>测试结果</span>
          </div>
        </template>
        
        <div class="test-summary">
          <el-statistic
            title="匹配率"
            :value="testResults.match_rate"
            suffix="%"
          >
            <template #prefix>
              <el-icon :color="testResults.match_rate >= 80 ? '#67c23a' : '#e6a23c'">
                <TrendCharts />
              </el-icon>
            </template>
          </el-statistic>
          
          <el-divider direction="vertical" style="height: 60px;" />
          
          <div class="test-count">
            <div class="count-label">测试查询</div>
            <div class="count-value">{{ testResults.total_count }}</div>
          </div>
          
          <el-divider direction="vertical" style="height: 60px;" />
          
          <div class="test-count">
            <div class="count-label">匹配成功</div>
            <div class="count-value success">{{ testResults.matched_count }}</div>
          </div>
          
          <el-divider direction="vertical" style="height: 60px;" />
          
          <div class="test-count">
            <div class="count-label">匹配失败</div>
            <div class="count-value failed">
              {{ testResults.total_count - testResults.matched_count }}
            </div>
          </div>
        </div>
        
        <div v-if="testResults.results && testResults.results.length > 0" class="test-examples">
          <div class="examples-title">测试示例（前5条）:</div>
          <div
            v-for="(result, index) in testResults.results.slice(0, 5)"
            :key="index"
            class="test-example"
          >
            <el-icon :color="result.matched ? '#67c23a' : '#f56c6c'">
              <component :is="result.matched ? 'CircleCheck' : 'CircleClose'" />
            </el-icon>
            <span class="example-query">{{ result.query }}</span>
            <span v-if="result.matched_text" class="example-match">
              匹配: <code>{{ result.matched_text }}</code>
            </span>
          </div>
        </div>
      </el-card>

      <!-- 冲突警告 -->
      <el-card v-if="conflicts && conflicts.length > 0" class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Warning /></el-icon>
            <span>冲突警告</span>
          </div>
        </template>
        
        <div
          v-for="(conflict, index) in conflicts"
          :key="index"
          class="conflict-item"
        >
          <el-alert
            :title="`与规则 #${conflict.rule_id} 存在${conflict.severity}冲突`"
            :type="conflict.severity === '高' ? 'error' : 'warning'"
            :closable="false"
            show-icon
          >
            <template #default>
              <div class="conflict-details">
                <div><strong>冲突规则:</strong> {{ conflict.pattern }}</div>
                <div><strong>冲突类型:</strong> {{ conflict.conflict_type }}</div>
                <div><strong>详细说明:</strong> {{ conflict.description }}</div>
              </div>
            </template>
          </el-alert>
        </div>
      </el-card>

      <!-- 影响预测 -->
      <el-card v-if="impactData" class="preview-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>影响预测</span>
          </div>
        </template>
        
        <el-row :gutter="16">
          <el-col :span="8">
            <el-statistic
              title="受影响查询数"
              :value="impactData.affected_query_count"
            />
          </el-col>
          <el-col :span="8">
            <el-statistic
              title="影响百分比"
              :value="impactData.affected_query_percentage"
              suffix="%"
              :precision="1"
            />
          </el-col>
          <el-col :span="8">
            <el-statistic
              title="预期使用频率"
              :value="impactData.expected_usage_frequency"
              suffix="次/天"
            />
          </el-col>
        </el-row>
        
        <div v-if="impactData.sample_queries && impactData.sample_queries.length > 0" class="impact-samples">
          <div class="samples-title">示例查询（前5条）:</div>
          <div
            v-for="(query, index) in impactData.sample_queries.slice(0, 5)"
            :key="index"
            class="sample-query"
          >
            <el-icon><Right /></el-icon>
            <span>{{ query }}</span>
          </div>
        </div>
        
        <el-alert
          v-if="impactData.warning"
          :title="impactData.warning"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 16px;"
        />
      </el-card>
    </div>

    <!-- 操作按钮 -->
    <div class="preview-actions">
      <el-button @click="handleBack">
        <el-icon><Back /></el-icon>
        返回编辑
      </el-button>
      <el-button
        type="primary"
        @click="handleConfirm"
        :loading="saving"
      >
        <el-icon><Check /></el-icon>
        确认保存
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Document,
  Search,
  MagicStick,
  CircleCheck,
  CircleClose,
  Warning,
  DataAnalysis,
  TrendCharts,
  Right,
  Back,
  Check
} from '@element-plus/icons-vue'

const props = defineProps({
  ruleData: {
    type: Object,
    required: true
  },
  testResults: {
    type: Object,
    default: null
  },
  conflicts: {
    type: Array,
    default: () => []
  },
  impactData: {
    type: Object,
    default: null
  },
  saving: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['back', 'confirm'])

// 计算属性
const keywords = computed(() => {
  if (Array.isArray(props.ruleData.keywords)) {
    return props.ruleData.keywords
  }
  if (props.ruleData.metadata?.keywords) {
    return props.ruleData.metadata.keywords
  }
  return []
})

const recommendedTables = computed(() => {
  if (Array.isArray(props.ruleData.recommended_tables)) {
    return props.ruleData.recommended_tables
  }
  if (props.ruleData.metadata?.recommended_tables) {
    return props.ruleData.metadata.recommended_tables
  }
  return []
})

const hasConflicts = computed(() => {
  return props.conflicts && props.conflicts.length > 0
})

const conflictCount = computed(() => {
  return props.conflicts ? props.conflicts.length : 0
})

// 方法
const getIntentTypeLabel = (intentType) => {
  const labelMap = {
    sql: 'SQL查询',
    rag_knowledge: '知识库检索',
    rag_report: '报告检索',
    chat: '普通对话'
  }
  return labelMap[intentType] || intentType
}

const getIntentTypeColor = (intentType) => {
  const colorMap = {
    sql: 'primary',
    rag_knowledge: 'success',
    rag_report: 'warning',
    chat: 'info'
  }
  return colorMap[intentType] || ''
}

const getPriorityColor = (priority) => {
  if (priority >= 90) return 'danger'
  if (priority >= 50) return 'warning'
  return 'info'
}

const handleBack = () => {
  emit('back')
}

const handleConfirm = () => {
  emit('confirm')
}
</script>

<style scoped>
.rule-preview {
  padding: 16px;
}

.preview-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.preview-section {
  border: 1px solid #e4e7ed;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.pattern-display {
  padding: 8px 0;
}

.pattern-label {
  font-weight: 600;
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.pattern-value {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
}

.pattern-value code {
  font-family: 'Courier New', monospace;
  color: #e6a23c;
  font-weight: 600;
}

.test-summary {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 16px 0;
}

.test-count {
  text-align: center;
}

.count-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.count-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.count-value.success {
  color: #67c23a;
}

.count-value.failed {
  color: #f56c6c;
}

.test-examples {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.examples-title,
.samples-title {
  font-weight: 600;
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
}

.test-example {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  margin-bottom: 4px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}

.example-query {
  flex: 1;
  color: #303133;
}

.example-match {
  color: #67c23a;
  font-size: 12px;
}

.example-match code {
  background-color: #fff;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.conflict-item {
  margin-bottom: 12px;
}

.conflict-item:last-child {
  margin-bottom: 0;
}

.conflict-details {
  font-size: 13px;
  line-height: 1.8;
}

.conflict-details div {
  margin-bottom: 4px;
}

.impact-samples {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.sample-query {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  margin-bottom: 4px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}
</style>
