<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { Connection, Loading, Document, ArrowLeft, InfoFilled, Download } from '@element-plus/icons-vue'
import { Card, StateDisplay } from '@/components/common'
import { getFullBackendUrl } from '@/utils/config'

const router = useRouter()
const eipIdsText = ref('')
const auth = ref({ ak: '', sk: '' })
const analyzing = ref(false)
const progress = ref(0)
const statusMessage = ref('准备就绪 - 输入EIP ID列表并开始分析')
const reportUrl = ref('')
const iframeLoading = ref(false)
const logs = ref([])
const loadingConfig = ref(false)

const eipIds = computed(() => eipIdsText.value.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#')))
const addLog = (msg) => { logs.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`) }

// 加载EIP配置
const loadEIPConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await axios.get('/api/v1/config/load?module=monitoring')
    
    if (response.config && response.config.eip_instance_ids && response.config.eip_instance_ids.length > 0) {
      const ids = Array.isArray(response.config.eip_instance_ids) 
        ? response.config.eip_instance_ids 
        : response.config.eip_instance_ids.split(',').map(id => id.trim())
      eipIdsText.value = ids.join('\n')
      ElMessage.success(`已加载 ${ids.length} 个EIP实例ID配置`)
    } else {
      ElMessage.warning('未找到配置的EIP实例ID')
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingConfig.value = false
  }
}

const startAnalysis = async () => {
  if (eipIds.value.length === 0) { ElMessage.warning('请先输入EIP ID列表'); return }
  analyzing.value = true; progress.value = 0; reportUrl.value = ''; logs.value = []
  statusMessage.value = '正在启动 EIP 带宽分析...'; addLog(`开始分析 ${eipIds.value.length} 个EIP...`)
  try {
    const response = await axios.post('/api/v1/eip/analyze', {
      eip_ids: eipIds.value, hours: 6,
      ak: auth.value.ak.trim() || undefined, sk: auth.value.sk.trim() || undefined
    })
    const taskId = response.task_id; addLog(`任务已创建: ${taskId}`)
    await loadReport(taskId)
  } catch (error) {
    ElMessage.error(`分析启动失败: ${error.response?.data?.detail || error.message}`)
    statusMessage.value = '分析启动失败'; addLog(`错误: ${error.message}`); analyzing.value = false
  }
}

const loadReport = async (taskId) => {
  try {
    const response = await axios.get(`/api/v1/eip/result/${taskId}`)
    reportUrl.value = getFullBackendUrl(response.html_file); iframeLoading.value = true
    progress.value = 100; statusMessage.value = 'EIP带宽分析完成'
    addLog('报告已加载'); ElMessage.success('EIP带宽分析完成'); analyzing.value = false
  } catch (error) {
    ElMessage.error('加载报告失败'); addLog(`错误: ${error.message}`); analyzing.value = false
  }
}

const downloadReport = () => {
  if (reportUrl.value) {
    const link = document.createElement('a'); link.href = reportUrl.value
    link.download = reportUrl.value.split('/').pop() || 'eip_report.html'
    document.body.appendChild(link); link.click(); document.body.removeChild(link)
  }
}

// 组件挂载时自动加载配置
onMounted(() => {
  loadEIPConfig()
})
</script>

<template>
  <div class="monitoring-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-icon eip">
        <el-icon :size="24"><Connection /></el-icon>
      </div>
      <div class="page-header-content">
        <h2 class="page-title">EIP带宽监控分析</h2>
        <p class="page-subtitle">监控EIP入向/出向带宽及丢包统计</p>
      </div>
      <el-button @click="router.push('/monitoring')">
        <el-icon><ArrowLeft /></el-icon>返回监控分析
      </el-button>
    </div>
    
    <!-- 认证配置 -->
    <Card
      title="BCE认证配置（可选）"
      icon="Connection"
      class="animate-slide-in-up"
    >
      <el-form :model="auth" label-width="120px">
        <el-form-item label="AK (Access Key)">
          <el-input v-model="auth.ak" placeholder="留空则使用默认配置" />
        </el-form-item>
        <el-form-item label="SK (Secret Key)">
          <el-input v-model="auth.sk" type="password" placeholder="留空则使用默认配置" show-password />
        </el-form-item>
      </el-form>
    </Card>
    
    <!-- EIP ID列表 -->
    <Card
      title="EIP ID列表"
      icon="Connection"
      class="animate-slide-in-up"
    >
      <div class="input-label-row">
        <span></span>
        <el-button size="small" @click="loadEIPConfig" :loading="loadingConfig">
          <el-icon><Download /></el-icon>
          加载配置
        </el-button>
      </div>
      <div class="config-hint-box">
        <el-icon><InfoFilled /></el-icon>
        <span>提示：您可以在 <router-link to="/system-config?section=monitoring" class="config-link">系统配置</router-link> 中设置默认EIP实例ID</span>
      </div>
      <el-input 
        v-model="eipIdsText" 
        type="textarea" 
        :rows="8" 
        placeholder="请输入EIP ID列表，每行一个" 
      />
      <p class="input-hint">当前已输入 {{ eipIds.length }} 个EIP ID</p>
    </Card>

    <!-- 功能说明和操作 -->
    <div class="action-grid">
      <Card title="功能说明" class="animate-slide-in-up">
        <ul class="feature-list">
          <li>监控指标: 入向/出向带宽、丢包数统计</li>
          <li>数据源: 百度云BCM API</li>
          <li>输出格式: 交互式HTML报告</li>
          <li>监控周期: 最近6小时数据</li>
        </ul>
      </Card>
      <Card class="action-card animate-slide-in-up">
        <el-button 
          type="primary" 
          size="large" 
          @click="startAnalysis" 
          :loading="analyzing" 
          :disabled="analyzing"
          class="action-button"
        >
          开始分析
        </el-button>
      </Card>
    </div>

    <!-- 进度 -->
    <Card
      v-if="analyzing || logs.length > 0"
      title="分析进度"
      class="animate-slide-in-up"
    >
      <StateDisplay
        v-if="analyzing"
        state="loading"
        :loading-text="statusMessage"
      >
        <div class="progress-section">
          <el-progress :percentage="progress" :stroke-width="10" />
        </div>
      </StateDisplay>
      <div v-if="logs.length > 0" class="log-container">
        <p v-for="(log, index) in logs" :key="index" class="log-line">{{ log }}</p>
      </div>
    </Card>
    
    <!-- 报告预览 -->
    <Card
      v-if="reportUrl"
      title="报告预览"
      class="bento-span-full animate-slide-in-up"
    >
      <template #header>
        <el-button type="success" @click="downloadReport">
          <el-icon><Document /></el-icon>下载报告
        </el-button>
      </template>
      <div class="report-preview">
        <div v-if="iframeLoading" class="report-loading">
          <el-icon class="spin-icon"><Loading /></el-icon>
        </div>
        <iframe :src="reportUrl" @load="iframeLoading = false" class="report-frame" />
      </div>
    </Card>
  </div>
</template>

<style scoped>
.monitoring-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  animation: slideInUp var(--duration-slow) var(--ease-out);
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  color: white;
}

.page-header-icon.eip {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-dark));
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0;
}

.input-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--spacing-2);
}

.input-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.action-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--spacing-6);
}

@media (max-width: 768px) {
  .action-grid {
    grid-template-columns: 1fr;
  }
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  padding: var(--spacing-2) 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.feature-list li::before {
  content: "•";
  color: var(--color-primary);
  font-weight: bold;
  display: inline-block;
  width: 1em;
  margin-left: -1em;
}

.action-card {
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-button {
  width: 100%;
  height: 56px;
  font-size: var(--font-size-lg);
}

.progress-section {
  margin-bottom: var(--spacing-4);
}

.log-container {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  max-height: 240px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--font-size-xs);
}

.log-line {
  color: var(--text-secondary);
  margin: var(--spacing-1) 0;
  white-space: pre-wrap;
}

.report-preview {
  position: relative;
  min-height: 600px;
}

.report-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg-strong);
  backdrop-filter: blur(8px);
  z-index: 10;
}

.spin-icon {
  font-size: 48px;
  color: var(--color-primary-500);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.report-frame {
  width: 100%;
  min-height: 600px;
  border: none;
  border-radius: var(--radius-lg);
  background: white;
}

/* 配置提示框 */
.config-hint-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-3);
}

.config-link {
  color: var(--color-primary-500);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--duration-fast);
}

.config-link:hover {
  color: var(--color-primary-600);
  text-decoration: underline;
}
</style>