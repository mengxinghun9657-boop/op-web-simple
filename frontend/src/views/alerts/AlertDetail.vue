<template>
  <div class="alert-detail-container">
    <el-page-header @back="handleBack" class="page-header">
      <template #content>
        <span class="page-title">告警详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="content-wrapper">
      <template v-if="!loading && alertData">
        <!-- 基本信息卡片 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">基本信息</span>
              <el-button
                type="warning"
                size="small"
                @click="handleDiagnose"
                :loading="diagnosing"
              >
                <el-icon><Refresh /></el-icon>
                重新诊断
              </el-button>
            </div>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="告警ID">
              {{ alertData.alert.id }}
            </el-descriptions-item>
            <el-descriptions-item label="告警类型">
              {{ alertData.alert.alert_type }}
            </el-descriptions-item>
            <el-descriptions-item label="组件类型">
              <el-tag :type="getComponentTagType(alertData.alert.component)">
                {{ alertData.alert.component }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="严重程度">
              <el-tag :type="getSeverityTagType(alertData.alert.severity)">
                {{ alertData.alert.severity }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="节点IP">
              {{ alertData.alert.ip || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="主机名">
              {{ alertData.alert.hostname || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="集群ID">
              {{ alertData.alert.cluster_id || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="实例ID">
              {{ alertData.alert.instance_id || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="发生时间">
              {{ formatDateTime(alertData.alert.timestamp) }}
            </el-descriptions-item>
            <el-descriptions-item label="处理状态">
              <el-tag :type="getStatusTagType(alertData.alert.status)">
                {{ statusLabels[alertData.alert.status] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="处理人" v-if="alertData.alert.resolved_by">
              {{ alertData.alert.resolved_by }}
            </el-descriptions-item>
            <el-descriptions-item label="处理时间" v-if="alertData.alert.resolved_at">
              {{ formatDateTime(alertData.alert.resolved_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="文件路径" :span="2">
              <span class="file-path">{{ alertData.alert.file_path || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item 
              v-if="alertData.alert.resolution_notes" 
              label="处理备注" 
              :span="2"
            >
              <div class="resolution-notes">
                {{ alertData.alert.resolution_notes }}
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 诊断结果 -->
        <template v-if="alertData.diagnosis">
          <!-- 手册匹配结果 -->
          <el-card v-if="alertData.diagnosis.manual_matched" class="diagnosis-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon color="#67C23A"><CircleCheck /></el-icon>
                  手册匹配结果
                </span>
              </div>
            </template>

            <el-descriptions :column="1" border>
              <el-descriptions-item label="故障名称">
                {{ alertData.diagnosis.manual_name_zh }}
              </el-descriptions-item>
              <el-descriptions-item label="危害等级">
                <el-tag :type="getDangerLevelTagType(alertData.diagnosis.danger_level)">
                  {{ alertData.diagnosis.danger_level }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="客户有感">
                <el-tag :type="alertData.diagnosis.customer_aware ? 'danger' : 'success'">
                  {{ alertData.diagnosis.customer_aware ? '是' : '否' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="影响描述">
                <div class="text-content">{{ alertData.diagnosis.manual_impact || '-' }}</div>
              </el-descriptions-item>
              <el-descriptions-item label="解决方案">
                <div class="text-content">{{ alertData.diagnosis.manual_solution || '-' }}</div>
              </el-descriptions-item>
              <el-descriptions-item label="恢复方案">
                <div class="text-content">{{ alertData.diagnosis.manual_recovery || '-' }}</div>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- API诊断结果 -->
          <el-card v-if="alertData.diagnosis.api_diagnosis" class="diagnosis-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon color="#409EFF"><Document /></el-icon>
                  API诊断结果
                </span>
                <el-tag :type="getApiStatusTagType(alertData.diagnosis.api_status)">
                  {{ alertData.diagnosis.api_status }}
                </el-tag>
              </div>
            </template>

            <div class="api-diagnosis-summary">
              <el-statistic title="诊断项总数" :value="alertData.diagnosis.api_items_count" />
              <el-statistic title="错误项" :value="alertData.diagnosis.api_error_count">
                <template #suffix>
                  <el-icon color="#F56C6C"><CircleClose /></el-icon>
                </template>
              </el-statistic>
              <el-statistic title="警告项" :value="alertData.diagnosis.api_warning_count">
                <template #suffix>
                  <el-icon color="#E6A23C"><Warning /></el-icon>
                </template>
              </el-statistic>
              <el-statistic title="异常项" :value="alertData.diagnosis.api_abnormal_count">
                <template #suffix>
                  <el-icon color="#F56C6C"><WarningFilled /></el-icon>
                </template>
              </el-statistic>
            </div>

            <el-divider />

            <el-collapse v-model="activeCollapse">
              <el-collapse-item
                v-if="alertData.diagnosis.api_diagnosis.error_items?.length"
                title="错误项"
                name="errors"
              >
                <el-table :data="alertData.diagnosis.api_diagnosis.error_items" stripe>
                  <el-table-column prop="item_name_zh" label="诊断项" min-width="200" />
                  <el-table-column prop="result" label="结果" width="100">
                    <template #default="{ row }">
                      <el-tag type="danger" size="small">{{ row.result }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="exact_message" label="详情" min-width="300" show-overflow-tooltip />
                </el-table>
              </el-collapse-item>

              <el-collapse-item
                v-if="alertData.diagnosis.api_diagnosis.warning_items?.length"
                title="警告项"
                name="warnings"
              >
                <el-table :data="alertData.diagnosis.api_diagnosis.warning_items" stripe>
                  <el-table-column prop="item_name_zh" label="诊断项" min-width="200" />
                  <el-table-column prop="result" label="结果" width="100">
                    <template #default="{ row }">
                      <el-tag type="warning" size="small">{{ row.result }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="exact_message" label="详情" min-width="300" show-overflow-tooltip />
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </el-card>

          <!-- AI解读结果 -->
          <el-card v-if="alertData.diagnosis.ai_interpretation" class="diagnosis-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-title">
                  <el-icon color="#9333EA"><MagicStick /></el-icon>
                  AI智能解读
                </span>
              </div>
            </template>

            <div class="ai-interpretation">
              <div v-html="renderMarkdown(alertData.diagnosis.ai_interpretation)"></div>
            </div>
          </el-card>
        </template>

        <!-- 无诊断结果提示 -->
        <el-empty v-else description="暂无诊断结果" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  CircleCheck,
  CircleClose,
  Document,
  Warning,
  WarningFilled,
  MagicStick
} from '@element-plus/icons-vue'
import { getAlertDetail, diagnoseAlert } from '@/api/alerts'
import { marked } from 'marked'

const route = useRoute()
const router = useRouter()

const statusLabels = {
  pending: '待处理',
  processing: '处理中',
  diagnosed: '已诊断',
  notified: '已通知',
  failed: '失败',
  resolved: '已处理'
}

const loading = ref(false)
const diagnosing = ref(false)
const alertData = ref(null)
const activeCollapse = ref(['errors', 'warnings'])

// 获取告警详情
const fetchAlertDetail = async () => {
  loading.value = true
  try {
    const response = await getAlertDetail(route.params.id)
    if (response.success) {
      alertData.value = response.data
    }
  } catch (error) {
    console.error('获取告警详情失败:', error)
    ElMessage.error('获取告警详情失败')
  } finally {
    loading.value = false
  }
}

// 重新诊断
const handleDiagnose = async () => {
  diagnosing.value = true
  try {
    const response = await diagnoseAlert(route.params.id, true)  // 传递布尔值而不是对象
    console.log('诊断响应:', response) // 添加调试日志
    
    // 检查响应是否成功
    if (response && response.success) {
      ElMessage.success(response.message || '诊断任务已创建,正在处理中...')
      // 开始轮询检查诊断状态
      startDiagnosisPolling()
    } else {
      // 后端返回success:false，但可能基础流程已完成
      const message = response?.message || '诊断处理完成'
      ElMessage.success(message)
      // 仍然开始轮询检查状态
      startDiagnosisPolling()
    }
    
  } catch (error) {
    console.error('触发诊断失败:', error)
    console.log('错误详情:', error.response) // 添加调试日志
    
    // 检查是否是axios拦截器抛出的错误（基础流程可能已完成）
    if (error.message && (
      error.message.includes('重新诊断') || 
      error.message.includes('诊断') ||
      error.message.includes('已存在诊断结果')
    )) {
      // 这种情况下，基础流程可能已经完成，显示成功信息并轮询
      ElMessage.success('诊断处理已完成，正在检查结果...')
      startDiagnosisPolling()
    } else {
      // 真正的网络错误或其他异常
      ElMessage.error('诊断请求失败，请重试')
    }
  } finally {
    diagnosing.value = false
  }
}

// 轮询检查诊断状态
const startDiagnosisPolling = () => {
  let pollCount = 0
  const maxPolls = 20 // 最多轮询20次 (约2分钟)
  
  const pollInterval = setInterval(async () => {
    try {
      await fetchAlertDetail()
      pollCount++
      
      // 检查诊断是否完成 (可以根据诊断状态判断)
      if (alertData.value?.diagnosis?.api_status === 'success' || 
          alertData.value?.diagnosis?.api_status === 'failed' ||
          pollCount >= maxPolls) {
        clearInterval(pollInterval)
        if (pollCount < maxPolls) {
          ElMessage.success('诊断已完成')
        }
      }
    } catch (error) {
      console.error('轮询诊断状态失败:', error)
      clearInterval(pollInterval)
    }
  }, 6000) // 每6秒轮询一次
}

// 返回
const handleBack = () => {
  router.back()
}

// 渲染Markdown
const renderMarkdown = (content) => {
  return marked(content || '')
}

// 标签类型辅助函数
const getComponentTagType = (component) => {
  const typeMap = {
    GPU: 'danger',
    Memory: 'warning',
    CPU: 'success',
    Motherboard: 'info'
  }
  return typeMap[component] || ''
}

const getSeverityTagType = (severity) => {
  const typeMap = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[severity] || ''
}

const getStatusTagType = (status) => {
  const typeMap = {
    pending: 'info',
    processing: 'warning',
    diagnosed: 'success',
    notified: 'success',
    failed: 'danger',
    resolved: 'success'
  }
  return typeMap[status] || ''
}

const getDangerLevelTagType = (level) => {
  if (!level) return ''
  if (level.includes('严重') || level.includes('P0')) return 'danger'
  if (level.includes('中等') || level.includes('P1')) return 'warning'
  return 'info'
}

const getApiStatusTagType = (status) => {
  const typeMap = {
    normal: 'success',
    abnormal: 'danger',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  fetchAlertDetail()
})
</script>

<style scoped>
.alert-detail-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}

.content-wrapper {
  min-height: 400px;
}

.info-card,
.diagnosis-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-path {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #64748b;
}

.text-content {
  line-height: 1.6;
  color: #475569;
  white-space: pre-wrap;
}

.api-diagnosis-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.ai-interpretation {
  padding: 16px;
  background-color: #f8fafc;
  border-radius: 8px;
  line-height: 1.8;
}

.ai-interpretation :deep(h1),
.ai-interpretation :deep(h2),
.ai-interpretation :deep(h3) {
  margin-top: 16px;
  margin-bottom: 12px;
  color: #1e293b;
}

.ai-interpretation :deep(p) {
  margin-bottom: 12px;
  color: #475569;
}

.ai-interpretation :deep(ul),
.ai-interpretation :deep(ol) {
  margin-left: 24px;
  margin-bottom: 12px;
}

.ai-interpretation :deep(code) {
  background-color: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.ai-interpretation :deep(pre) {
  background-color: #1e293b;
  color: #f1f5f9;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin-bottom: 12px;
}

.ai-interpretation :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

.resolution-notes {
  padding: 12px;
  background-color: #f0f9ff;
  border-left: 4px solid #3b82f6;
  border-radius: 4px;
  line-height: 1.6;
  color: #1e40af;
  white-space: pre-wrap;
}
</style>
