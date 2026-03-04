<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { Coin, Loading, Document, ArrowLeft, InfoFilled, Download } from '@element-plus/icons-vue'
import { Card, StateDisplay } from '@/components/common'
import { getFullBackendUrl } from '@/utils/config'

const router = useRouter()
const bucketsText = ref('')
const auth = ref({ ak: '', sk: '' })
const analyzing = ref(false)
const progress = ref(0)
const statusMessage = ref('准备就绪 - 配置认证信息并开始分析')
const reportUrl = ref('')
const iframeLoading = ref(false)
const logs = ref([])
const loadingConfig = ref(false)

// 定时器引用，用于清理
let pollTimer = null

const buckets = computed(() => bucketsText.value.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#')))
const addLog = (msg) => { logs.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`) }

// 加载BOS配置
const loadBOSConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await axios.get('/api/v1/config/load?module=monitoring')
    
    if (response.config && response.config.bos_bucket_names && response.config.bos_bucket_names.length > 0) {
      const names = Array.isArray(response.config.bos_bucket_names)
        ? response.config.bos_bucket_names
        : response.config.bos_bucket_names.split(',').map(name => name.trim())
      bucketsText.value = names.join('\n')
      ElMessage.success(`已加载 ${names.length} 个Bucket配置`)
    } else {
      ElMessage.warning('未找到配置的Bucket名称')
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingConfig.value = false
  }
}

const startAnalysis = async () => {
  analyzing.value = true; progress.value = 0; reportUrl.value = ''; logs.value = []
  statusMessage.value = '正在启动 BOS 分析...'
  addLog(`开始BOS存储空间分析... (${buckets.value.length || '使用默认'} 个Bucket)`)
  try {
    const response = await axios.post('/api/v1/monitoring/bos/analyze', {
      buckets: buckets.value,
      ak: auth.value.ak.trim() || undefined, sk: auth.value.sk.trim() || undefined
    })
    const taskId = response.task_id; addLog(`任务已创建: ${taskId}`); statusMessage.value = `任务已创建: ${taskId}`
    await pollTaskStatus(taskId)
  } catch (error) {
    ElMessage.error(`分析启动失败: ${error.response?.data?.detail || error.message}`)
    statusMessage.value = '分析启动失败'; addLog(`错误: ${error.message}`); analyzing.value = false
  }
}

const pollTaskStatus = (taskId) => {
  return new Promise((resolve) => {
    // 清理旧的定时器
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    
    pollTimer = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/monitoring/result/${taskId}`)
        progress.value = response.progress || 50; statusMessage.value = response.message || '正在分析...'
        if (response.status === 'completed') {
          clearInterval(pollTimer); pollTimer = null; progress.value = 100
          reportUrl.value = getFullBackendUrl(response.html_file); iframeLoading.value = true
          addLog('BOS分析完成'); ElMessage.success('BOS存储分析完成'); analyzing.value = false; resolve()
        } else if (response.status === 'failed') {
          clearInterval(pollTimer); pollTimer = null; addLog(`分析失败: ${response.message}`)
          ElMessage.error(`分析失败: ${response.message}`); analyzing.value = false; resolve()
        }
      } catch (error) {
        clearInterval(pollTimer); pollTimer = null; addLog(`轮询错误: ${error.message}`)
        ElMessage.error('轮询任务状态失败'); analyzing.value = false; resolve()
      }
    }, 2000)
  })
}

const downloadReport = () => {
  if (reportUrl.value) {
    const link = document.createElement('a'); link.href = reportUrl.value
    link.download = reportUrl.value.split('/').pop() || 'bos_report.html'
    document.body.appendChild(link); link.click(); document.body.removeChild(link)
  }
}

// 组件卸载时清理定时器
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="monitoring-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-icon bos">
        <el-icon :size="24"><Coin /></el-icon>
      </div>
      <div class="page-header-content">
        <h2 class="page-title">BOS存储空间分析</h2>
        <p class="page-subtitle">分析BOS存储桶容量和使用情况</p>
      </div>
      <el-button @click="router.push('/monitoring')">
        <el-icon><ArrowLeft /></el-icon>返回监控分析
      </el-button>
    </div>
    
    <!-- 认证配置 -->
    <Card
      title="BCE认证配置（可选）"
      icon="Coin"
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

    <!-- Bucket列表 -->
    <Card
      title="Bucket列表（可选）"
      icon="Coin"
      class="animate-slide-in-up"
    >
      <div class="input-label-row">
        <span></span>
        <el-button size="small" @click="loadBOSConfig" :loading="loadingConfig">
          <el-icon><Download /></el-icon>
          加载配置
        </el-button>
      </div>
      <div class="config-hint-box">
        <el-icon><InfoFilled /></el-icon>
        <span>提示：您可以在 <router-link to="/system-config?section=monitoring" class="config-link">系统配置</router-link> 中设置默认Bucket名称</span>
      </div>
      <el-input 
        v-model="bucketsText" 
        type="textarea" 
        :rows="6" 
        placeholder="请输入Bucket名称列表，每行一个&#10;留空则使用默认测试数据" 
      />
      <p class="input-hint">当前已输入 {{ buckets.length }} 个Bucket（留空使用默认）</p>
    </Card>

    <!-- 功能说明和操作 -->
    <div class="action-grid">
      <Card title="功能说明" class="animate-slide-in-up">
        <ul class="feature-list">
          <li>分析指标: 存储容量、对象数量、存储类型分布</li>
          <li>数据源: 百度云BOS API</li>
          <li>输出格式: 交互式HTML报告</li>
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

.page-header-icon.bos {
  background: linear-gradient(135deg, var(--color-success), var(--color-success-dark));
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
  color: var(--color-success);
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
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-3);
}

.config-link {
  color: var(--color-success);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--duration-fast);
}

.config-link:hover {
  color: var(--color-success-dark);
  text-decoration: underline;
}
</style>