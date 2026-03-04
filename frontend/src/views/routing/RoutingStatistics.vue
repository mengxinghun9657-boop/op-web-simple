<template>
  <div class="routing-statistics-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">路由统计</h1>
        <p class="page-subtitle">查看意图路由的统计数据和性能指标</p>
      </div>
      
      <!-- 日期筛选 -->
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :shortcuts="dateShortcuts"
          @change="loadStatistics"
        />
        <el-button type="primary" :icon="Refresh" @click="loadStatistics">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 统计内容 -->
    <div v-else class="statistics-content">
      <!-- 总体统计卡片 -->
      <div class="stats-cards">
        <div class="stat-card cursor-pointer">
          <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">总查询数</div>
            <div class="stat-value">{{ formatNumber(statistics.total_queries) }}</div>
          </div>
        </div>

        <div class="stat-card cursor-pointer">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">平均置信度</div>
            <div class="stat-value">{{ (statistics.avg_confidence * 100).toFixed(1) }}%</div>
          </div>
        </div>

        <div class="stat-card cursor-pointer">
          <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
            <el-icon><SuccessFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">高置信度</div>
            <div class="stat-value">
              {{ formatNumber(statistics.total_queries - statistics.low_confidence_count) }}
            </div>
            <div class="stat-trend">
              {{ ((1 - statistics.low_confidence_count / statistics.total_queries) * 100).toFixed(1) }}%
            </div>
          </div>
        </div>

        <div class="stat-card cursor-pointer">
          <div class="stat-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%)">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">低置信度</div>
            <div class="stat-value">{{ formatNumber(statistics.low_confidence_count) }}</div>
            <div class="stat-trend warning">
              {{ (statistics.low_confidence_count / statistics.total_queries * 100).toFixed(1) }}%
            </div>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 意图类型分布 -->
        <div class="chart-card cursor-pointer">
          <div class="chart-header">
            <h3>意图类型分布</h3>
            <el-tag type="info" size="small">饼图</el-tag>
          </div>
          <div ref="intentChartRef" class="chart-container"></div>
        </div>

        <!-- 路由方法分布 -->
        <div class="chart-card cursor-pointer">
          <div class="chart-header">
            <h3>路由方法分布</h3>
            <el-tag type="info" size="small">柱状图</el-tag>
          </div>
          <div ref="methodChartRef" class="chart-container"></div>
        </div>

        <!-- 置信度分布 -->
        <div class="chart-card full-width cursor-pointer">
          <div class="chart-header">
            <h3>置信度分布</h3>
            <el-tag type="info" size="small">折线图</el-tag>
          </div>
          <div ref="confidenceChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 低置信度记录 -->
      <div class="low-confidence-section">
        <div class="section-header">
          <h3>低置信度记录</h3>
          <el-tag type="warning">置信度 < 70%</el-tag>
        </div>

        <el-table
          :data="lowConfidenceRecords"
          border
          stripe
          class="records-table"
          v-loading="loadingRecords"
        >
          <el-table-column prop="query" label="查询" min-width="300" show-overflow-tooltip />
          
          <el-table-column label="意图类型" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getIntentType(row.intent_type)" size="small">
                {{ getIntentLabel(row.intent_type) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="置信度" width="120" align="center">
            <template #default="{ row }">
              <el-progress
                :percentage="row.confidence * 100"
                :color="getConfidenceColor(row.confidence)"
                :stroke-width="8"
              />
            </template>
          </el-table-column>

          <el-table-column label="路由方法" width="150" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="info">
                {{ getRoutingMethodLabel(row.routing_method) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="created_at" label="时间" width="180" align="center">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                link
                @click="showFeedbackDialog(row)"
              >
                反馈
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="loadLowConfidenceRecords"
            @size-change="loadLowConfidenceRecords"
          />
        </div>
      </div>
    </div>

    <!-- 反馈对话框 -->
    <el-dialog
      v-model="feedbackDialogVisible"
      title="提交路由反馈"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="feedbackForm" label-width="100px">
        <el-form-item label="当前路由">
          <el-tag :type="getIntentType(feedbackForm.current_intent)">
            {{ getIntentLabel(feedbackForm.current_intent) }}
          </el-tag>
          <span class="confidence-text">
            置信度: {{ (feedbackForm.confidence * 100).toFixed(1) }}%
          </span>
        </el-form-item>

        <el-form-item label="正确意图" required>
          <el-select v-model="feedbackForm.correct_intent" placeholder="请选择正确的意图类型">
            <el-option label="SQL 查询" value="sql" />
            <el-option label="报告查询" value="rag_report" />
            <el-option label="知识查询" value="rag_knowledge" />
            <el-option label="对话" value="chat" />
          </el-select>
        </el-form-item>

        <el-form-item label="反馈备注">
          <el-input
            v-model="feedbackForm.comment"
            type="textarea"
            :rows="3"
            placeholder="请输入反馈备注（可选）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="feedbackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback" :loading="submittingFeedback">
          提交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  TrendCharts,
  SuccessFilled,
  WarningFilled,
  Refresh
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getRoutingStatistics,
  getLowConfidenceRecords,
  submitRoutingFeedback
} from '@/api/routing'

// 数据
const loading = ref(false)
const loadingRecords = ref(false)
const statistics = ref({
  total_queries: 0,
  by_intent: {},
  by_routing_method: {},
  avg_confidence: 0,
  low_confidence_count: 0
})

const dateRange = ref([])
const dateShortcuts = [
  {
    text: '最近一周',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '最近一个月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  },
  {
    text: '最近三个月',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    }
  }
]

// 低置信度记录
const lowConfidenceRecords = ref([])
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 反馈对话框
const feedbackDialogVisible = ref(false)
const submittingFeedback = ref(false)
const feedbackForm = ref({
  routing_log_id: null,
  current_intent: '',
  confidence: 0,
  correct_intent: '',
  comment: ''
})

// 图表实例
const intentChartRef = ref(null)
const methodChartRef = ref(null)
const confidenceChartRef = ref(null)
let intentChart = null
let methodChart = null
let confidenceChart = null

// 加载统计数据
const loadStatistics = async () => {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString().split('T')[0]
      params.end_date = dateRange.value[1].toISOString().split('T')[0]
    }

    const response = await getRoutingStatistics(params)
    if (response.success) {
      statistics.value = response.data
      
      // 等待 DOM 更新后渲染图表
      await nextTick()
      renderCharts()
    } else {
      ElMessage.error(response.message || '加载统计数据失败')
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// 加载低置信度记录
const loadLowConfidenceRecords = async () => {
  loadingRecords.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString().split('T')[0]
      params.end_date = dateRange.value[1].toISOString().split('T')[0]
    }

    const response = await getLowConfidenceRecords(params)
    if (response.success) {
      lowConfidenceRecords.value = response.data.list
      pagination.value.total = response.data.total
    } else {
      ElMessage.error(response.message || '加载低置信度记录失败')
    }
  } catch (error) {
    console.error('加载低置信度记录失败:', error)
    ElMessage.error('加载低置信度记录失败')
  } finally {
    loadingRecords.value = false
  }
}

// 渲染图表
const renderCharts = () => {
  renderIntentChart()
  renderMethodChart()
  renderConfidenceChart()
}

// 渲染意图类型分布图
const renderIntentChart = () => {
  if (!intentChartRef.value) return
  
  if (!intentChart) {
    intentChart = echarts.init(intentChartRef.value)
  }

  const data = Object.entries(statistics.value.by_intent || {}).map(([name, value]) => ({
    name: getIntentLabel(name),
    value
  }))

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center'
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data,
        color: ['#667eea', '#f093fb', '#4facfe', '#fa709a']
      }
    ]
  }

  intentChart.setOption(option)
}

// 渲染路由方法分布图
const renderMethodChart = () => {
  if (!methodChartRef.value) return
  
  if (!methodChart) {
    methodChart = echarts.init(methodChartRef.value)
  }

  const data = Object.entries(statistics.value.by_routing_method || {})
  const xData = data.map(([name]) => getRoutingMethodLabel(name))
  const yData = data.map(([, value]) => value)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisTick: {
        alignWithLabel: true
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        type: 'bar',
        barWidth: '60%',
        data: yData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ]),
          borderRadius: [10, 10, 0, 0]
        }
      }
    ]
  }

  methodChart.setOption(option)
}

// 渲染置信度分布图
const renderConfidenceChart = () => {
  if (!confidenceChartRef.value) return
  
  if (!confidenceChart) {
    confidenceChart = echarts.init(confidenceChartRef.value)
  }

  // 模拟置信度分布数据（实际应该从后端获取）
  const ranges = ['0-50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']
  const counts = [
    Math.floor(statistics.value.low_confidence_count * 0.1),
    Math.floor(statistics.value.low_confidence_count * 0.2),
    Math.floor(statistics.value.low_confidence_count * 0.7),
    Math.floor((statistics.value.total_queries - statistics.value.low_confidence_count) * 0.2),
    Math.floor((statistics.value.total_queries - statistics.value.low_confidence_count) * 0.3),
    Math.floor((statistics.value.total_queries - statistics.value.low_confidence_count) * 0.5)
  ]

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ranges
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        type: 'line',
        data: counts,
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
          ])
        },
        lineStyle: {
          color: '#667eea',
          width: 3
        },
        itemStyle: {
          color: '#667eea'
        }
      }
    ]
  }

  confidenceChart.setOption(option)
}

// 显示反馈对话框
const showFeedbackDialog = (record) => {
  feedbackForm.value = {
    routing_log_id: record.id,
    current_intent: record.intent_type,
    confidence: record.confidence,
    correct_intent: '',
    comment: ''
  }
  feedbackDialogVisible.value = true
}

// 提交反馈
const submitFeedback = async () => {
  if (!feedbackForm.value.correct_intent) {
    ElMessage.warning('请选择正确的意图类型')
    return
  }

  submittingFeedback.value = true
  try {
    const response = await submitRoutingFeedback({
      routing_log_id: feedbackForm.value.routing_log_id,
      correct_intent: feedbackForm.value.correct_intent,
      comment: feedbackForm.value.comment
    })

    if (response.success) {
      ElMessage.success('反馈提交成功')
      feedbackDialogVisible.value = false
      loadLowConfidenceRecords()
    } else {
      ElMessage.error(response.message || '反馈提交失败')
    }
  } catch (error) {
    console.error('反馈提交失败:', error)
    ElMessage.error('反馈提交失败')
  } finally {
    submittingFeedback.value = false
  }
}

// 工具函数
const formatNumber = (num) => {
  return num?.toLocaleString() || '0'
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

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

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  intentChart?.resize()
  methodChart?.resize()
  confidenceChart?.resize()
}

// 生命周期
onMounted(() => {
  // 默认加载最近一周的数据
  const end = new Date()
  const start = new Date()
  start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
  dateRange.value = [start, end]
  
  loadStatistics()
  loadLowConfidenceRecords()
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  intentChart?.dispose()
  methodChart?.dispose()
  confidenceChart?.dispose()
})
</script>

<style scoped>
.routing-statistics-page {
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

@media (min-width: 640px) {
  .routing-statistics-page {
    padding: 20px;
  }
}

@media (min-width: 1024px) {
  .routing-statistics-page {
    padding: 24px;
  }
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

@media (min-width: 640px) {
  .page-header {
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 14px;
  }
}

@media (min-width: 768px) {
  .page-header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

@media (min-width: 1024px) {
  .page-header {
    padding: 24px;
    margin-bottom: 24px;
    border-radius: 16px;
  }
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.header-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

@media (min-width: 640px) {
  .header-actions {
    flex-direction: row;
    width: auto;
  }
}

.loading-container {
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.statistics-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

@media (min-width: 640px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (min-width: 1024px) {
  .stats-cards {
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s ease-out;
  min-height: 88px;
}

@media (min-width: 640px) {
  .stat-card {
    padding: 20px;
    gap: 14px;
    border-radius: 14px;
  }
}

@media (min-width: 1024px) {
  .stat-card {
    padding: 24px;
    gap: 16px;
    border-radius: 16px;
  }
}

.stat-card:hover {
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #475569;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1;
}

.stat-trend {
  font-size: 12px;
  color: #67c23a;
  margin-top: 4px;
}

.stat-trend.warning {
  color: #e6a23c;
}

/* 图表区域 */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

@media (min-width: 768px) {
  .charts-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (min-width: 1024px) {
  .charts-grid {
    gap: 20px;
  }
}

.chart-card {
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

@media (min-width: 640px) {
  .chart-card {
    padding: 20px;
    border-radius: 14px;
  }
}

@media (min-width: 1024px) {
  .chart-card {
    padding: 24px;
    border-radius: 16px;
  }
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.chart-container {
  width: 100%;
  height: 250px;
}

@media (min-width: 640px) {
  .chart-container {
    height: 300px;
  }
}

@media (min-width: 1024px) {
  .chart-container {
    height: 350px;
  }
}

/* 低置信度记录 */
.low-confidence-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

@media (min-width: 640px) {
  .low-confidence-section {
    padding: 20px;
    border-radius: 14px;
  }
}

@media (min-width: 1024px) {
  .low-confidence-section {
    padding: 24px;
    border-radius: 16px;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.records-table {
  margin-top: 16px;
}

.confidence-text {
  margin-left: 12px;
  font-size: 12px;
  color: #475569;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 全宽图表卡片 */
.chart-card.full-width {
  grid-column: 1;
}

@media (min-width: 768px) {
  .chart-card.full-width {
    grid-column: 1 / -1;
  }
}
</style>
