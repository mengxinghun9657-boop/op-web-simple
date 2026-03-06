<template>
  <div class="pfs-monitoring-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-icon class="header-icon"><Folder /></el-icon>
          <div>
            <h1 class="page-title">PFS 监控分析</h1>
            <p class="page-subtitle">并行文件系统容量、吞吐、QPS、延迟监控</p>
          </div>
        </div>
        <div class="header-right">
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
    </div>

    <!-- 查询面板 -->
    <div class="query-panel">
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

    <!-- 数据展示区域 -->
    <div v-if="hasData" class="data-display">
      <!-- 概览卡片 -->
      <div class="overview-cards">
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
      
      console.log('✅ PFS 配置加载成功:', pfsConfig.value)
    }
  } catch (error) {
    console.error('❌ 加载 PFS 配置失败:', error)
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
      
      // 🔍 调试日志：查看后端返回的数据结构
      console.log('=== PFS 查询调试信息 ===')
      console.log('1. 后端返回数据:', response)
      console.log('2. 数据数组长度:', response.data?.length)
      console.log('3. 第一个指标完整结构:', JSON.stringify(response.data?.[0], null, 2))
      console.log('4. 第一个指标的 statistics:', response.data?.[0]?.statistics)
      console.log('5. metricsData 赋值前:', metricsData.value.length)
      
      if (response.success) {
        metricsData.value = response.data
        console.log('6. metricsData 赋值后:', metricsData.value.length)
        console.log('7. overviewMetrics 计算结果:', metricsData.value.length)
        ElMessage.success(`查询成功，共 ${response.data.length} 个指标`)
      } else {
        ElMessage.error(response.error || '查询失败')
      }
    }
  } catch (error) {
    console.error('查询失败:', error)
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
          console.log(`导出进度: ${progress}% - ${message}`)
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
    console.error('导出失败:', error)
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
.pfs-monitoring-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  padding: var(--spacing-6);
  min-height: 100vh;
  background: var(--bg-base);
}

/* 页面头部 */
.page-header {
  animation: slideInUp 0.3s ease-out;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 36px;
  color: var(--color-primary);
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: var(--spacing-1) 0 0 0;
  line-height: 1.5;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

/* 查询面板 */
.query-panel {
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: var(--spacing-6);
}

/* 数据展示区域 */
.data-display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 概览卡片 */
.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-4);
}

/* 动画 */
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

/* 响应式 */
@media (max-width: 768px) {
  .pfs-monitoring-page {
    padding: var(--spacing-4);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .overview-cards {
    grid-template-columns: 1fr;
  }
}
</style>
