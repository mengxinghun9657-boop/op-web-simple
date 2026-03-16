<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { Connection, Loading, Document, ArrowLeft, InfoFilled, Download } from '@element-plus/icons-vue'
import { StateDisplay } from '@/components/common'
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

    // 获取 eip_instance_ids 配置
    const eipIds = response.config?.eip_instance_ids || response.data?.config?.eip_instance_ids

    // 检查配置是否存在且非空
    if (eipIds && eipIds !== '' && eipIds.length > 0) {
      // 处理数组或字符串格式
      const ids = Array.isArray(eipIds)
        ? eipIds
        : eipIds.split(',').map(id => id.trim()).filter(id => id)

      if (ids.length > 0) {
        eipIdsText.value = ids.join('\n')
        ElMessage.success(`已加载 ${ids.length} 个EIP实例ID配置`)
      } else {
        ElMessage.warning('配置的EIP实例ID列表为空，请先在系统配置中添加')
      }
    } else {
      ElMessage.warning('未找到配置的EIP实例ID，请先在系统配置中添加')
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
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Connection /></el-icon>
          </div>
          EIP带宽监控分析
        </div>
        <div class="page-subtitle">监控EIP入向/出向带宽及丢包统计</div>
      </div>
      <div class="page-actions">
        <el-button @click="router.push('/monitoring')">
          <el-icon><ArrowLeft /></el-icon>返回监控分析
        </el-button>
      </div>
    </div>

    <!-- 认证配置 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Connection /></el-icon>
          BCE认证配置（可选）
        </div>
      </div>
      <div class="content-card-body">
        <el-form :model="auth" label-width="120px">
          <el-form-item label="AK (Access Key)">
            <el-input v-model="auth.ak" placeholder="留空则使用默认配置" />
          </el-form-item>
          <el-form-item label="SK (Secret Key)">
            <el-input v-model="auth.sk" type="password" placeholder="留空则使用默认配置" show-password />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- EIP ID列表 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Connection /></el-icon>
          EIP ID列表
        </div>
        <div class="content-card-extra">
          <el-button size="small" @click="loadEIPConfig" :loading="loadingConfig">
            <el-icon><Download /></el-icon>
            加载配置
          </el-button>
        </div>
      </div>
      <div class="content-card-body">
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
      </div>
    </div>

    <!-- 功能说明和操作 -->
    <div class="action-grid">
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">
            <el-icon><InfoFilled /></el-icon>
            功能说明
          </div>
        </div>
        <div class="content-card-body">
          <ul class="feature-list">
            <li>监控指标: 入向/出向带宽、丢包数统计</li>
            <li>数据源: 百度云BCM API</li>
            <li>输出格式: 交互式HTML报告</li>
            <li>监控周期: 最近6小时数据</li>
          </ul>
        </div>
      </div>
      <div class="content-card action-card">
        <div class="content-card-body">
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
        </div>
      </div>
    </div>

    <!-- 进度 -->
    <div
      v-if="analyzing || logs.length > 0"
      class="content-card"
    >
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Loading /></el-icon>
          分析进度
        </div>
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
    <div
      v-if="reportUrl"
      class="content-card"
      style="grid-column: span 2;"
    >
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Document /></el-icon>
          报告预览
        </div>
        <div class="content-card-extra">
          <el-button type="success" @click="downloadReport">
            <el-icon><Document /></el-icon>下载报告
          </el-button>
        </div>
      </div>
      <div class="content-card-body">
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
  transition: color var(--duration-fast);
}

.config-link:hover {
  color: var(--primary);
  text-decoration: underline;
}
</style>