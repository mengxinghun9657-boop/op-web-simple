<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { Monitor, Loading, Document, ArrowLeft, InfoFilled, Download } from '@element-plus/icons-vue'
import { StateDisplay } from '@/components/common'
import { getFullBackendUrl } from '@/utils/config'

const router = useRouter()
const instanceIdsText = ref('')
const analyzing = ref(false)
const progress = ref(0)
const statusMessage = ref('准备就绪 - 配置认证信息并开始监控')
const reportUrl = ref('')
const iframeLoading = ref(false)
const logs = ref([])
const loadingConfig = ref(false)

// 定时器引用，用于清理
let pollTimer = null

const instanceIds = computed(() => instanceIdsText.value.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#')))
const addLog = (msg) => { logs.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`) }

// 加载BCC配置
const loadBCCConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await axios.get('/api/v1/config/load?module=monitoring')

    // 获取 bcc_instance_ids 配置
    const bccIds = response.config?.bcc_instance_ids || response.data?.config?.bcc_instance_ids

    // 检查配置是否存在且非空
    if (bccIds && bccIds !== '' && bccIds.length > 0) {
      // 处理数组或字符串格式
      const ids = Array.isArray(bccIds)
        ? bccIds
        : bccIds.split(',').map(id => id.trim()).filter(id => id)

      if (ids.length > 0) {
        instanceIdsText.value = ids.join('\n')
        ElMessage.success(`已加载 ${ids.length} 个BCC实例ID配置`)
      } else {
        ElMessage.warning('配置的BCC实例ID列表为空，请先在系统配置中添加')
      }
    } else {
      ElMessage.warning('未找到配置的BCC实例ID，请先在系统配置中添加')
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingConfig.value = false
  }
}

const startMonitoring = async () => {
  analyzing.value = true; progress.value = 0; reportUrl.value = ''; logs.value = []
  statusMessage.value = '正在启动 BCC 监控任务...'
  addLog(`开始BCC实例监控分析... (${instanceIds.value.length || '使用默认'} 个实例)`)
  try {
    const response = await axios.post('/api/v1/monitoring/bcc/analyze', {
      instance_ids: instanceIds.value, days: 1
    })
    const taskId = response.task_id; addLog(`任务已创建: ${taskId}`); statusMessage.value = `任务已创建: ${taskId}`
    await pollTaskStatus(taskId)
  } catch (error) {
    ElMessage.error(`监控启动失败: ${error.response?.data?.detail || error.message}`)
    statusMessage.value = '监控启动失败'; addLog(`错误: ${error.message}`); analyzing.value = false
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
        progress.value = response.progress || (response.status === 'completed' ? 100 : 50)
        statusMessage.value = response.message || '正在获取数据...'
        if (response.status === 'completed') {
          clearInterval(pollTimer); pollTimer = null; progress.value = 100
          reportUrl.value = getFullBackendUrl(response.html_file); iframeLoading.value = true
          addLog('BCC监控报告生成完成'); ElMessage.success('BCC监控报告生成完成')
          statusMessage.value = 'BCC监控分析完成'; analyzing.value = false; resolve()
        } else if (response.status === 'failed') {
          clearInterval(pollTimer); pollTimer = null; addLog(`监控失败: ${response.message}`)
          ElMessage.error(`监控失败: ${response.message}`); analyzing.value = false; resolve()
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
    link.download = reportUrl.value.split('/').pop() || 'bcc_report.html'
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

// 组件挂载时自动加载配置
onMounted(() => {
  loadBCCConfig()
})
</script>

<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          BCC实例监控分析
        </div>
        <div class="page-subtitle">监控BCC实例CPU、内存、磁盘等指标</div>
      </div>
      <div class="page-actions">
        <el-button @click="router.push('/monitoring')">
          <el-icon><ArrowLeft /></el-icon>返回监控分析
        </el-button>
      </div>
    </div>
    
    <!-- 实例ID列表 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Monitor /></el-icon>
          实例ID列表（可选）
        </div>
        <div class="content-card-extra">
          <el-button size="small" @click="loadBCCConfig" :loading="loadingConfig">
            <el-icon><Download /></el-icon>
            加载配置
          </el-button>
        </div>
      </div>
      <div class="content-card-body">
        <div class="config-hint-box">
          <el-icon><InfoFilled /></el-icon>
          <span>提示：您可以在 <router-link to="/system-config?section=monitoring" class="config-link">系统配置</router-link> 中设置默认BCC实例ID</span>
        </div>
        <el-input
          v-model="instanceIdsText"
          type="textarea"
          :rows="6"
          placeholder="请输入BCC实例ID列表，每行一个&#10;留空则使用默认测试数据"
        />
        <p class="input-hint">当前已输入 {{ instanceIds.length }} 个实例ID（留空使用默认）</p>
      </div>
    </div>

    <!-- 功能说明和操作 -->
    <div class="action-grid">
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">功能说明</div>
        </div>
        <div class="content-card-body">
          <ul class="feature-list">
            <li>监控指标: CPU使用率、内存使用率、磁盘IO、网络流量</li>
            <li>数据源: 百度云BCM API</li>
            <li>输出格式: 交互式HTML报告</li>
            <li>监控周期: 最近1天数据</li>
          </ul>
        </div>
      </div>
      <div class="content-card action-card">
        <div class="content-card-body">
          <el-button
            type="primary"
            size="large"
            @click="startMonitoring"
            :loading="analyzing"
            :disabled="analyzing"
            class="action-button"
          >
            开始监控
          </el-button>
        </div>
      </div>
    </div>

    <!-- 进度 -->
    <div v-if="analyzing || logs.length > 0" class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">监控进度</div>
      </div>
      <div class="content-card-body">
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
      </div>
    </div>
    
    <!-- 报告预览 -->
    <div v-if="reportUrl" class="content-card" style="grid-column: span 2;">
      <div class="content-card-header">
        <div class="content-card-title">报告预览</div>
        <div class="content-card-extra">
          <el-button type="success" @click="downloadReport">
            <el-icon><Document /></el-icon>下载报告
          </el-button>
        </div>
      </div>
      <div class="content-card-body report-body">
        <div class="report-preview">
          <div v-if="iframeLoading" class="report-loading">
            <el-icon class="spin-icon"><Loading /></el-icon>
          </div>
          <iframe :src="reportUrl" @load="iframeLoading = false" class="report-frame" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 配置提示框 */
.config-hint-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(26, 115, 232, 0.1);
  border: 1px solid rgba(26, 115, 232, 0.3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.config-link {
  color: var(--primary);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--transition-fast);
}

.config-link:hover {
  color: var(--primary);
  text-decoration: underline;
}

.input-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
}

.action-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-6);
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
  padding: var(--space-2) 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.feature-list li::before {
  content: "•";
  color: var(--primary);
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
  font-size: var(--text-lg);
}

.progress-section {
  margin-bottom: var(--space-4);
}

.log-container {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  max-height: 240px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--text-xs);
}

.log-line {
  color: var(--text-secondary);
  margin: var(--space-1) 0;
  white-space: pre-wrap;
}

.report-body {
  position: relative;
  min-height: 600px;
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
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  z-index: 10;
}

.spin-icon {
  font-size: 48px;
  color: var(--primary);
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
</style>