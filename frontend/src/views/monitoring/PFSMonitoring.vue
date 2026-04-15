<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Folder /></el-icon>
          </div>
          PFS 监控分析
        </div>
        <div class="page-subtitle">并行文件系统容量、吞吐、QPS、延迟监控</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleRefresh" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="handleExport" :disabled="!hasData">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <!-- 查询面板 -->
    <div class="content-card">
      <div class="content-card-body">
        <QueryPanel
          v-model:metrics="selectedMetrics"
          v-model:level="metricLevel"
          v-model:instance-id="selectedInstanceId"
          v-model:client-id="selectedClientId"
          v-model:time-range="timeRange"
          v-model:compare-mode="compareMode"
          @query="handleQuery"
        />
      </div>
    </div>

    <!-- 数据展示区域 -->
    <div v-if="hasData" class="data-display">
      <!-- 概览卡片（仅普通模式显示） -->
      <div v-if="!compareMode" class="overview-cards">
        <MetricCard
          v-for="metric in overviewMetrics"
          :key="metric.metric_name"
          :metric="metric"
        />
      </div>

      <!-- 数据大屏 -->
      <DataDashboard
        :metrics-data="metricsData"
        :compare-mode="compareMode"
      />
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="请选择指标并点击查询按钮"
      :image-size="200"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Refresh, Download } from '@element-plus/icons-vue'
import QueryPanel from '@/components/pfs/QueryPanel.vue'
import MetricCard from '@/components/pfs/MetricCard.vue'
import DataDashboard from '@/components/pfs/DataDashboard.vue'
import * as pfsApi from '@/api/pfs'
import * as configApi from '@/api/config'
import { pollTaskStatus } from '@/utils/taskPoller'

// PFS 配置
const pfsConfig = ref({
  instance_ids: ['pfs-mTYGr6'],
  region: 'cd',
  instance_type: 'plusl2'
})

// 查询参数
const selectedMetrics = ref([])
const metricLevel = ref('cluster')
const selectedInstanceId = ref(null)
const selectedClientId = ref('.*')
const timeRange = ref({
  start: Date.now() - 4 * 3600 * 1000, // 最近4小时
  end: Date.now()
})
const compareMode = ref(false)

// 数据状态
const loading = ref(false)
const metricsData = ref([])
const exportProgress = ref(0)
const exportMessage = ref('')
let pollTimer = null

// 加载 PFS 配置
const loadPFSConfig = async () => {
  try {
    const response = await configApi.loadConfig('pfs')
    if (response.success && response.data.config) {
      const config = response.data.config
      // 向后兼容：如果是单个ID，转换为数组
      let pfsIds = config.pfs_instance_ids || []
      if (!pfsIds.length && config.pfs_instance_id) {
        pfsIds = [config.pfs_instance_id]
      }
      
      pfsConfig.value = {
        instance_ids: pfsIds.length ? pfsIds : ['pfs-mTYGr6'],
        region: config.region || 'cd',
        instance_type: config.instance_type || 'plusl2'
      }
      
      // 默认选择第一个集群ID
      if (!selectedInstanceId.value && pfsConfig.value.instance_ids.length > 0) {
        selectedInstanceId.value = pfsConfig.value.instance_ids[0]
      }
      
    }
  } catch (error) {
    ElMessage.warning('加载配置失败，使用默认配置')
  }
}

// 组件挂载时加载配置
onMounted(() => {
  loadPFSConfig()
})

// 计算属性
const hasData = computed(() => metricsData.value.length > 0)

const overviewMetrics = computed(() => {
  // 显示所有查询到的指标（不限制数量）
  return metricsData.value
})

// 查询数据
const handleQuery = async () => {
  if (selectedMetrics.value.length === 0) {
    ElMessage.warning('请至少选择一个指标')
    return
  }
  
  if (!selectedInstanceId.value) {
    ElMessage.warning('请选择 PFS 集群')
    return
  }

  loading.value = true
  try {
    // 根据对比模式选择不同的 API
    if (compareMode.value) {
      // 对比模式：调用 /compare API
      const request = {
        metrics: selectedMetrics.value,
        level: metricLevel.value,
        region: pfsConfig.value.region,
        instance_type: pfsConfig.value.instance_type,
        instance_id: selectedInstanceId.value,
        client_id: selectedClientId.value,
        time_range_hours: Math.floor((timeRange.value.end - timeRange.value.start) / 3600000), // 转换为小时
        step: '5m'
      }

      const response = await pfsApi.compareMetrics(request)
      
      if (response.success) {
        // 对比模式返回的数据结构不同，需要转换
        metricsData.value = response.data.metrics || []
        ElMessage.success(`对比分析完成，共 ${metricsData.value.length} 个指标`)
      } else {
        ElMessage.error(response.error || '对比分析失败')
      }
    } else {
      // 普通查询模式：调用 /query API
      const request = {
        metrics: selectedMetrics.value,
        level: metricLevel.value,
        region: pfsConfig.value.region,
        instance_type: pfsConfig.value.instance_type,
        instance_id: selectedInstanceId.value,
        client_id: selectedClientId.value,
        start_time: Math.floor(timeRange.value.start / 1000),
        end_time: Math.floor(timeRange.value.end / 1000),
        step: '5m'
      }

      const response = await pfsApi.queryMetrics(request)

      if (response.success) {
        metricsData.value = response.data
        console.log('[PFS] 查询结果:', response.message)
        ElMessage.success(response.message || `查询成功，共 ${response.data.length} 个指标`)
      } else {
        ElMessage.error(response.error || '查询失败')
      }
    }
  } catch (error) {
    ElMessage.error('查询失败：' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 刷新数据
const handleRefresh = () => {
  if (hasData.value) {
    handleQuery()
  } else {
    ElMessage.info('请先进行查询')
  }
}

// 导出数据
const handleExport = async () => {
  if (!hasData.value) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  if (!selectedInstanceId.value) {
    ElMessage.warning('请选择 PFS 集群')
    return
  }

  try {
    const request = {
      metrics: selectedMetrics.value,
      level: metricLevel.value,
      region: pfsConfig.value.region,
      instance_type: pfsConfig.value.instance_type,
      instance_id: selectedInstanceId.value,
      client_id: selectedClientId.value,
      start_time: Math.floor(timeRange.value.start / 1000),
      end_time: Math.floor(timeRange.value.end / 1000),
      step: '5m',
      format: 'csv'
    }

    const response = await pfsApi.exportData(request)
    
    if (response.success) {
      const { task_id } = response.data
      ElMessage.success('导出任务已创建')
      
      // 使用 taskPoller 轮询任务状态
      pollTimer = pollTaskStatus(
        task_id,
        // 进度回调
        ({ status, progress, message }) => {
          exportProgress.value = progress
          exportMessage.value = message
        },
        // 成功回调
        (taskData) => {
          ElMessage.success('导出完成')
          // 下载文件
          if (taskData.result_url) {
            const filename = taskData.result_url.split('/').pop()
            window.open(`/api/v1/pfs/download/${filename}`, '_blank')
          }
        },
        // 失败回调
        (error) => {
          ElMessage.error(`导出失败: ${error}`)
        }
      )
    } else {
      ElMessage.error(response.error || '导出失败')
    }
  } catch (error) {
    ElMessage.error('导出失败：' + (error.message || '未知错误'))
  }
}

// 组件销毁时清除轮询
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<style scoped>
/* 数据展示区域 */
.data-display {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* 概览卡片 */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-4);
}

/* 响应式 */
@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }
}
</style>
