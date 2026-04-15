<script setup>
import { ref, computed } from 'vue'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { Connection, Download, Search, Loading, List, InfoFilled } from '@element-plus/icons-vue'
import { StateDisplay } from '@/components/common'

const clusterIdsText = ref(`cce-3nusu9su
cce-9m1ht29q
cce-elwhlymq
cce-48c915gn
cce-ld2ckre2
cce-216ima4l
cce-2ys5dxch
cce-75n0j16r
cce-hcbs74xg
cce-xrg955qz
cce-pog0r4mg
cce-gzk0qlzk
cce-p6w3c5z8
cce-uk1zi507
cce-k5sn275j
cce-4nmy1x1s`)
const logs = ref([])
const fetching = ref(false)
const progress = ref(0)
const taskIdRef = ref(null)
const statusMessage = ref('准备就绪')

const clusterIds = computed(() => {
  return clusterIdsText.value.split('\n')
    .map(id => id.trim())
    .filter(id => id.length > 0 && !id.startsWith('#'))
})

const addLog = (msg, isError = false) => {
  const time = new Date().toLocaleTimeString()
  logs.value.push({ time, msg, isError })
}

const fetchClusterData = async () => {
  if (clusterIds.value.length === 0) {
    ElMessage.warning('请输入集群ID列表')
    return
  }

  fetching.value = true
  progress.value = 0
  taskIdRef.value = null
  statusMessage.value = `正在获取 ${clusterIds.value.length} 个集群数据...`
  addLog(`开始获取 ${clusterIds.value.length} 个集群的数据`)

  try {
    const response = await axios.post('/api/v1/prometheus/cluster/metrics/batch', { cluster_ids: clusterIds.value })

    addLog(`成功获取 ${clusterIds.value.length} 个集群的监控数据`)
    taskIdRef.value = response.task_id || `batch-${Date.now()}`
    statusMessage.value = '集群数据获取完成'
    progress.value = 100
    fetching.value = false

    ElMessage.success('集群数据获取完成')

  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '获取失败'
    ElMessage.error(`数据获取失败: ${errorMsg}`)
    statusMessage.value = '数据获取失败'
    addLog(`错误: ${errorMsg}`, true)
    fetching.value = false
  }
}

const exportData = async () => {
  if (clusterIds.value.length === 0) {
    ElMessage.warning('请先输入集群ID并获取数据')
    return
  }

  try {
    const response = await axios.post('/api/v1/prometheus/cluster/export', { cluster_ids: clusterIds.value })

    if (response.success) {
      const url = `/results/${response.file}`
      window.open(url, '_blank')
      addLog(`已导出数据文件: ${response.file}`)
      ElMessage.success('数据导出成功')
    }
  } catch (error) {
    ElMessage.error('数据导出失败')
    addLog(`导出失败: ${error.message}`, true)
  }
}

const testConnection = async () => {
  addLog('正在测试连接...')
  try {
    const res = await axios.post('/api/v1/prometheus/config/test')
    ElMessage.success(res.message || '连接测试成功')
    addLog('连接测试成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '连接测试失败，请检查 Prometheus 配置')
    addLog(`连接测试失败: ${error.message}`, true)
  }
}
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
          多集群数据获取
        </div>
        <div class="page-subtitle">批量采集 Prometheus 集群监控指标</div>
      </div>
    </div>

    <!-- 集群配置卡片 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><List /></el-icon>
          集群ID配置
        </div>
      </div>
      <div class="content-card-body">
        <div class="tip-box">
          <el-icon><InfoFilled /></el-icon>
          <span>每行输入一个集群ID,以 # 开头的行为注释</span>
        </div>

        <el-input
          v-model="clusterIdsText"
          type="textarea"
          :rows="8"
          placeholder="请输入集群ID列表,每行一个"
          class="cluster-input"
        />

        <div class="action-bar">
          <el-button
            type="primary"
            :icon="Loading"
            @click="fetchClusterData"
            :loading="fetching"
            :disabled="clusterIds.length === 0 || fetching"
          >
            <span>获取数据 ({{ clusterIds.length }})</span>
          </el-button>
          <el-button
            type="success"
            :icon="Download"
            @click="exportData"
            :disabled="!taskIdRef || fetching"
          >
            <span>导出 JSON</span>
          </el-button>
          <el-button
            type="info"
            :icon="Search"
            @click="testConnection"
          >
            <span>测试连接</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 执行结果 -->
    <div v-if="fetching || logs.length > 0" class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><List /></el-icon>
          执行日志
        </div>
      </div>
      <div class="content-card-body">
        <StateDisplay
          v-if="fetching"
          state="loading"
          :loading-text="statusMessage"
        >
          <div class="progress-section">
            <el-progress :percentage="progress" :stroke-width="8" />
          </div>
        </StateDisplay>

        <div v-if="logs.length > 0" class="log-container">
          <p
            v-for="(log, index) in logs"
            :key="index"
            :class="['log-line', log.isError ? 'error' : 'success']"
          >
            <span class="log-time">[{{ log.time }}]</span> {{ log.msg }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tip-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: rgba(26, 115, 232, 0.1);
  border: 1px solid rgba(26, 115, 232, 0.2);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.cluster-input {
  margin-bottom: var(--space-4);
}

.cluster-input :deep(.el-textarea__inner) {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--text-sm);
}

.action-bar {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
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
}

.log-line {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--text-xs);
  margin: var(--space-1) 0;
  white-space: pre-wrap;
}

.log-line.success { color: var(--color-success); }
.log-line.error { color: var(--color-error); }
.log-time { color: var(--text-tertiary); }
</style>
