<template>
  <div class="ai-query-page">
    <div class="page-header">
      <h1>AI 智能查询</h1>
      <p class="subtitle">使用自然语言查询数据库、报告和知识库</p>
    </div>

    <div class="query-container">
      <!-- 查询输入区 -->
      <div class="query-input-section">
        <div class="input-wrapper">
          <textarea
            v-model="queryText"
            placeholder="输入您的问题，例如：查询所有物理机信息、最近的资源分析报告..."
            rows="3"
            :disabled="isQuerying"
            @keydown.ctrl.enter="submitQuery"
          ></textarea>
          <div class="input-actions">
            <button 
              class="btn-primary" 
              @click="submitQuery"
              :disabled="!queryText.trim() || isQuerying"
            >
              <span v-if="!isQuerying">🔍 查询</span>
              <span v-else>⏳ 处理中...</span>
            </button>
            <button 
              class="btn-secondary" 
              @click="clearQuery"
              :disabled="isQuerying"
            >
              清空
            </button>
          </div>
        </div>

        <!-- 查询示例 -->
        <div class="query-examples">
          <span class="label">示例：</span>
          <button 
            v-for="example in queryExamples" 
            :key="example"
            class="example-btn"
            @click="queryText = example"
            :disabled="isQuerying"
          >
            {{ example }}
          </button>
        </div>
      </div>

      <!-- 处理状态显示 -->
      <div v-if="isQuerying" class="status-indicator">
        <div class="status-item" :class="{ active: currentStatus === 'analyzing_intent' }">
          <span class="icon">🧠</span>
          <span class="text">分析意图</span>
        </div>
        <div class="status-item" :class="{ active: currentStatus === 'querying_data' }">
          <span class="icon">🔍</span>
          <span class="text">查询数据</span>
        </div>
        <div class="status-item" :class="{ active: currentStatus === 'generating_answer' }">
          <span class="icon">✨</span>
          <span class="text">生成回答</span>
        </div>
        <div class="status-item" :class="{ active: currentStatus === 'completed' }">
          <span class="icon">✅</span>
          <span class="text">完成</span>
        </div>
      </div>

      <!-- 查询结果显示 -->
      <div v-if="queryResult" class="result-section">
        <div class="result-header">
          <h3>查询结果</h3>
          <div class="header-badges">
            <span class="source-badge" :class="`source-${queryResult.source_type}`">
              {{ getSourceLabel(queryResult.source_type) }}
            </span>
            <span class="time-badge">{{ queryResult.execution_time_ms }}ms</span>
          </div>
          <el-button
            type="warning"
            size="small"
            plain
            @click="showFeedbackDialog"
            v-if="queryResult.routing_log_id"
          >
            <el-icon><WarningFilled /></el-icon>
            路由错误反馈
          </el-button>
        </div>

        <!-- 路由信息 -->
        <div v-if="queryResult.intent_type" class="routing-info-box">
          <div class="routing-item">
            <span class="routing-label">意图类型:</span>
            <el-tag :type="getIntentTagType(queryResult.intent_type)" size="small">
              {{ getIntentLabel(queryResult.intent_type) }}
            </el-tag>
          </div>
          <div class="routing-item">
            <span class="routing-label">置信度:</span>
            <el-progress
              :percentage="queryResult.confidence * 100"
              :color="getConfidenceColor(queryResult.confidence)"
              :stroke-width="6"
              style="width: 150px"
            />
          </div>
          <div class="routing-item" v-if="queryResult.routing_method">
            <span class="routing-label">路由方法:</span>
            <el-tag type="info" size="small">
              {{ getRoutingMethodLabel(queryResult.routing_method) }}
            </el-tag>
          </div>
        </div>

        <!-- 自然语言回答 -->
        <div class="answer-box">
          <h4>📝 回答</h4>
          <div class="answer-content" v-html="formatAnswer(queryResult.answer)"></div>
        </div>

        <!-- SQL 查询（如果有） -->
        <div v-if="queryResult.sql" class="sql-box">
          <h4>💻 执行的 SQL</h4>
          <pre><code>{{ queryResult.sql }}</code></pre>
        </div>

        <!-- 查询结果数据（如果有） -->
        <div v-if="queryResult.query_results && queryResult.query_results.length > 0" class="data-box">
          <h4>📊 数据结果（共 {{ queryResult.query_results.length }} 条）</h4>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th v-for="col in Object.keys(queryResult.query_results[0])" :key="col">
                    {{ col }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in queryResult.query_results.slice(0, 10)" :key="idx">
                  <td v-for="col in Object.keys(row)" :key="col">
                    {{ row[col] }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="queryResult.query_results.length > 10" class="more-data-hint">
              还有 {{ queryResult.query_results.length - 10 }} 条数据未显示
            </div>
          </div>
        </div>

        <!-- 引用的报告（如果有） -->
        <div v-if="queryResult.referenced_reports && queryResult.referenced_reports.length > 0" class="reports-box">
          <h4>📄 引用的报告（{{ queryResult.referenced_reports.length }} 份）</h4>
          <div class="report-list">
            <div v-for="report in queryResult.referenced_reports" :key="report.task_id" class="report-item">
              <div class="report-header">
                <span class="report-type">{{ getReportTypeLabel(report.report_type) }}</span>
                <span class="report-date">{{ formatDate(report.generated_at) }}</span>
              </div>
              <div class="report-summary">{{ report.summary }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 错误显示 -->
      <div v-if="errorMessage" class="error-box">
        <h4>❌ 查询失败</h4>
        <p>{{ errorMessage }}</p>
      </div>

      <!-- 查询历史 -->
      <div v-if="queryHistory.length > 0" class="history-section">
        <h3>📜 查询历史</h3>
        <div class="history-list">
          <div 
            v-for="(item, idx) in queryHistory" 
            :key="idx"
            class="history-item"
            @click="queryText = item.query"
          >
            <span class="history-query">{{ item.query }}</span>
            <span class="history-time">{{ formatTime(item.timestamp) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 反馈对话框 -->
    <FeedbackDialog
      v-model="feedbackDialogVisible"
      :routing-info="currentRoutingInfo"
      @success="handleFeedbackSuccess"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue';
import { WarningFilled } from '@element-plus/icons-vue';
import FeedbackDialog from '@/components/routing/FeedbackDialog.vue';
import { intelligentQuery } from '@/api/ai';

export default {
  name: 'AIIntelligentQuery',
  components: {
    FeedbackDialog
  },
  setup() {
    const queryText = ref('');
    const isQuerying = ref(false);
    const currentStatus = ref('');
    const queryResult = ref(null);
    const errorMessage = ref('');
    const queryHistory = ref([]);

    // 反馈对话框
    const feedbackDialogVisible = ref(false);
    const currentRoutingInfo = ref({
      routing_log_id: null,
      intent_type: '',
      confidence: 0,
      routing_method: ''
    });

    const queryExamples = [
      '查询所有物理机信息',
      '统计任务状态分布',
      '最近的资源分析报告',
      '如何创建 BCC 实例'
    ];

    const submitQuery = async () => {
      if (!queryText.value.trim() || isQuerying.value) return;

      isQuerying.value = true;
      currentStatus.value = 'analyzing_intent';
      queryResult.value = null;
      errorMessage.value = '';

      try {
        // 使用 ai.js 的 intelligentQuery 函数
        await intelligentQuery(
          queryText.value,
          // SSE 事件处理回调
          (event) => {
            currentStatus.value = event.status;

            if (event.status === 'completed') {
              queryResult.value = event.data;
              isQuerying.value = false;

              // 添加到历史记录
              queryHistory.value.unshift({
                query: queryText.value,
                timestamp: new Date()
              });
              if (queryHistory.value.length > 10) {
                queryHistory.value = queryHistory.value.slice(0, 10);
              }
            } else if (event.status === 'error') {
              errorMessage.value = event.error?.message || '查询失败';
              isQuerying.value = false;
            }
          },
          // 错误处理回调
          (error) => {
            console.error('Query error:', error);
            errorMessage.value = error.message || '查询失败';
            isQuerying.value = false;
          }
        );

      } catch (error) {
        console.error('Query error:', error);
        errorMessage.value = error.message || '查询失败';
        isQuerying.value = false;
      }
    };

    const clearQuery = () => {
      queryText.value = '';
      queryResult.value = null;
      errorMessage.value = '';
    };

    const formatAnswer = (answer) => {
      if (!answer) return '';
      // 简单的 Markdown 格式化
      return answer
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
    };

    const getSourceLabel = (sourceType) => {
      const labels = {
        database: '数据库',
        report: '报告',
        knowledge: '知识库',
        mixed: '混合'
      };
      return labels[sourceType] || sourceType;
    };

    const getReportTypeLabel = (reportType) => {
      const labels = {
        resource_analysis: '资源分析',
        bcc_monitoring: 'BCC 监控',
        bos_monitoring: 'BOS 监控',
        operational_analysis: '运营分析'
      };
      return labels[reportType] || reportType;
    };

    const formatDate = (dateStr) => {
      const date = new Date(dateStr);
      return date.toLocaleDateString('zh-CN');
    };

    const formatTime = (date) => {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    };

    const getIntentTagType = (intent) => {
      const types = {
        sql: 'success',
        rag_report: 'warning',
        rag_knowledge: 'info',
        chat: ''
      }
      return types[intent] || ''
    };

    const getIntentLabel = (intent) => {
      const labels = {
        sql: 'SQL 查询',
        rag_report: '报告查询',
        rag_knowledge: '知识查询',
        chat: '对话'
      }
      return labels[intent] || intent
    };

    const getRoutingMethodLabel = (method) => {
      const labels = {
        forced_rule: '强制规则',
        routing_rule: '路由规则',
        ernie_api: 'ERNIE 分类',
        similarity: '语义相似度',
        keyword: '关键词规则'
      }
      return labels[method] || method
    };

    const getConfidenceColor = (confidence) => {
      if (confidence >= 0.8) return '#67c23a'
      if (confidence >= 0.6) return '#e6a23c'
      return '#f56c6c'
    };

    const showFeedbackDialog = () => {
      if (!queryResult.value) return;
      
      currentRoutingInfo.value = {
        routing_log_id: queryResult.value.routing_log_id,
        intent_type: queryResult.value.intent_type,
        confidence: queryResult.value.confidence || 0,
        routing_method: queryResult.value.routing_method || ''
      };
      
      feedbackDialogVisible.value = true;
    };

    const handleFeedbackSuccess = () => {
      // 反馈成功后可以做一些处理，比如刷新数据
      console.log('反馈提交成功');
    };

    return {
      queryText,
      isQuerying,
      currentStatus,
      queryResult,
      errorMessage,
      queryHistory,
      queryExamples,
      feedbackDialogVisible,
      currentRoutingInfo,
      submitQuery,
      clearQuery,
      formatAnswer,
      getSourceLabel,
      getReportTypeLabel,
      formatDate,
      formatTime,
      getIntentTagType,
      getIntentLabel,
      getRoutingMethodLabel,
      getConfidenceColor,
      showFeedbackDialog,
      handleFeedbackSuccess,
      WarningFilled
    };
  }
};
</script>

<style scoped>
.ai-query-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
}

.query-container {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.query-input-section {
  margin-bottom: 2rem;
}

.input-wrapper textarea {
  width: 100%;
  padding: 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  resize: vertical;
  transition: border-color 0.3s;
}

.input-wrapper textarea:focus {
  outline: none;
  border-color: #4CAF50;
}

.input-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.query-examples {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.query-examples .label {
  color: #666;
  font-size: 0.9rem;
}

.example-btn {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s;
}

.example-btn:hover:not(:disabled) {
  background: #e8f5e9;
  border-color: #4CAF50;
}

.status-indicator {
  display: flex;
  justify-content: space-around;
  margin: 2rem 0;
  padding: 1.5rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  opacity: 0.3;
  transition: opacity 0.3s;
}

.status-item.active {
  opacity: 1;
}

.status-item .icon {
  font-size: 2rem;
}

.status-item .text {
  font-size: 0.9rem;
  color: #666;
}

.result-section {
  margin-top: 2rem;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.source-badge, .time-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.source-badge {
  background: #e3f2fd;
  color: #1976d2;
}

.source-database { background: #e8f5e9; color: #2e7d32; }
.source-report { background: #fff3e0; color: #f57c00; }
.source-knowledge { background: #f3e5f5; color: #7b1fa2; }
.source-mixed { background: #e0f2f1; color: #00796b; }

.time-badge {
  background: #f5f5f5;
  color: #666;
}

.routing-info-box {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.routing-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.routing-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.answer-box, .sql-box, .data-box, .reports-box {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: #fafafa;
  border-radius: 8px;
  border-left: 4px solid #4CAF50;
}

.answer-box h4, .sql-box h4, .data-box h4, .reports-box h4 {
  margin-bottom: 1rem;
  color: #333;
}

.answer-content {
  line-height: 1.6;
  color: #444;
}

.sql-box pre {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

th, td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

th {
  background: #f5f5f5;
  font-weight: 600;
}

.more-data-hint {
  margin-top: 1rem;
  text-align: center;
  color: #666;
  font-size: 0.9rem;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.report-item {
  padding: 1rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.report-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.report-type {
  font-weight: 600;
  color: #4CAF50;
}

.report-date {
  color: #666;
  font-size: 0.9rem;
}

.report-summary {
  color: #444;
  line-height: 1.5;
}

.error-box {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #ffebee;
  border-radius: 8px;
  border-left: 4px solid #f44336;
}

.error-box h4 {
  margin-bottom: 0.5rem;
  color: #c62828;
}

.error-box p {
  color: #d32f2f;
}

.history-section {
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 2px solid #e0e0e0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #f9f9f9;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s;
}

.history-item:hover {
  background: #e8f5e9;
}

.history-query {
  color: #333;
}

.history-time {
  color: #999;
  font-size: 0.85rem;
}
</style>
