<template>
  <div class="query-panel">
    <el-form :model="queryForm" label-width="120px">
      <!-- 指标选择 -->
      <el-form-item label="选择指标">
        <div class="metrics-select-wrapper">
          <el-select
            v-model="queryForm.metrics"
            multiple
            filterable
            placeholder="请选择要查询的指标"
            style="width: 100%;"
            @change="handleMetricsChange"
          >
            <el-option-group
              v-for="(metrics, category) in metricsByCategory"
              :key="category"
              :label="category"
            >
              <el-option
                v-for="metric in metrics"
                :key="metric.name"
                :label="`${metric.zh_name} (${metric.name})`"
                :value="metric.name"
              >
                <div class="metric-option">
                  <span class="metric-name">{{ metric.zh_name }}</span>
                  <el-tooltip :content="metric.description" placement="right">
                    <el-icon class="metric-info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
          <div class="metrics-actions">
            <el-button size="small" @click="handleSelectAll">全选</el-button>
            <el-button size="small" @click="handleClearAll">清空</el-button>
          </div>
        </div>
      </el-form-item>

      <!-- 指标级别 -->
      <el-form-item label="指标级别">
        <el-radio-group v-model="queryForm.level" @change="handleLevelChange">
          <el-radio label="cluster">集群级别</el-radio>
          <el-radio label="client">客户端级别</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 集群ID选择（集群级别和客户端级别都显示） -->
      <el-form-item label="选择集群">
        <el-select
          v-model="queryForm.instanceId"
          filterable
          placeholder="请选择 PFS 集群"
          style="width: 100%;"
          :loading="loadingConfig"
          @change="handleInstanceChange"
        >
          <el-option
            v-for="id in pfsInstanceIds"
            :key="id"
            :label="id"
            :value="id"
          />
        </el-select>
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          选择要查询的 PFS 集群 ID
        </div>
      </el-form-item>

      <!-- 客户端选择（仅客户端级别显示） -->
      <el-form-item v-if="queryForm.level === 'client'" label="选择客户端">
        <el-select
          v-model="queryForm.clientId"
          filterable
          placeholder="请选择客户端"
          style="width: 100%;"
          :loading="loadingClients"
        >
          <el-option label="所有客户端 (.*)" value=".*" />
          <el-option
            v-for="client in clients"
            :key="client.client_id"
            :label="`${client.client_id} (${client.client_ip})`"
            :value="client.client_id"
          >
            <div class="client-option">
              <span>{{ client.client_id }}</span>
              <span class="client-ip">{{ client.client_ip }}</span>
            </div>
          </el-option>
        </el-select>
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          选择特定客户端或使用 .* 匹配所有客户端
        </div>
      </el-form-item>

      <!-- 时间范围 -->
      <el-form-item label="时间范围">
        <div class="time-range-wrapper">
          <el-radio-group v-model="timeRangeType" @change="handleTimeRangeTypeChange">
            <el-radio label="quick">快捷选项</el-radio>
            <el-radio label="custom">自定义</el-radio>
          </el-radio-group>
          
          <div v-if="timeRangeType === 'quick'" class="time-quick-options">
            <el-button
              v-for="option in quickTimeOptions"
              :key="option.value"
              :type="selectedQuickTime === option.value ? 'primary' : ''"
              size="default"
              @click="handleQuickTimeSelect(option.value)"
            >
              {{ option.label }}
            </el-button>
          </div>
          
          <el-date-picker
            v-else
            v-model="customTimeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="x"
            style="width: 100%; margin-top: 12px;"
            @change="handleCustomTimeChange"
          />
        </div>
      </el-form-item>

      <!-- 对比模式 -->
      <el-form-item label="对比模式">
        <el-switch
          v-model="queryForm.compareMode"
          active-text="开启"
          inactive-text="关闭"
          @change="handleCompareModeChange"
        />
        <span class="form-tip">开启后将对比今天与昨天同期数据</span>
      </el-form-item>

      <!-- 查询按钮 -->
      <el-form-item>
        <el-button
          type="primary"
          :disabled="!canQuery"
          @click="handleQuery"
        >
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button @click="handleReset">
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Search, RefreshLeft } from '@element-plus/icons-vue'
import * as pfsApi from '@/api/pfs'
import * as configApi from '@/api/config'

// Props
const props = defineProps({
  metrics: {
    type: Array,
    default: () => []
  },
  level: {
    type: String,
    default: 'cluster'
  },
  instanceId: {
    type: String,
    default: null
  },
  clientId: {
    type: String,
    default: '.*'
  },
  timeRange: {
    type: Object,
    default: () => ({
      start: Date.now() - 4 * 3600 * 1000,
      end: Date.now()
    })
  },
  compareMode: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['update:metrics', 'update:level', 'update:instanceId', 'update:clientId', 'update:timeRange', 'update:compareMode', 'query'])

// 查询表单
const queryForm = ref({
  metrics: props.metrics,
  level: props.level,
  instanceId: props.instanceId,
  clientId: props.clientId || '.*',
  compareMode: props.compareMode
})

// PFS 集群 ID 列表
const pfsInstanceIds = ref([])
const loadingConfig = ref(false)
const pfsRegion = ref('cd')

// 指标数据
const metricsByCategory = ref({})
const loadingMetrics = ref(false)

// 客户端数据
const clients = ref([])
const loadingClients = ref(false)

// 时间范围
const timeRangeType = ref('quick')
const selectedQuickTime = ref('4h')
const customTimeRange = ref([props.timeRange.start, props.timeRange.end])

const quickTimeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近4小时', value: '4h' },
  { label: '最近24小时', value: '24h' }
]

// 计算属性
const canQuery = computed(() => {
  return queryForm.value.metrics.length > 0 &&
         queryForm.value.instanceId &&  // 必须选择集群ID
         (queryForm.value.level === 'cluster' || queryForm.value.clientId)
})

// 加载 PFS 配置（获取集群ID列表）
const loadPFSConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await configApi.loadConfig('pfs')
    if (response.success && response.data.config) {
      const config = response.data.config
      // 向后兼容：如果是单个ID，转换为数组
      let pfsIds = config.pfs_instance_ids || []
      if (!pfsIds.length && config.pfs_instance_id) {
        pfsIds = [config.pfs_instance_id]
      }
      pfsInstanceIds.value = pfsIds.length ? pfsIds : ['pfs-mTYGr6']
      pfsRegion.value = config.region || 'cd'
      
      // 如果没有选择集群ID，默认选择第一个
      if (!queryForm.value.instanceId && pfsInstanceIds.value.length > 0) {
        queryForm.value.instanceId = pfsInstanceIds.value[0]
        emit('update:instanceId', pfsInstanceIds.value[0])
      }
    }
  } catch (error) {
    console.error('加载 PFS 配置失败:', error)
    pfsInstanceIds.value = ['pfs-mTYGr6']
    queryForm.value.instanceId = 'pfs-mTYGr6'
    emit('update:instanceId', 'pfs-mTYGr6')
  } finally {
    loadingConfig.value = false
  }
}

// 加载指标列表
const loadMetrics = async () => {
  loadingMetrics.value = true
  try {
    const response = await pfsApi.getMetrics(queryForm.value.level)
    if (response.success) {
      metricsByCategory.value = response.data
    }
  } catch (error) {
    console.error('加载指标列表失败:', error)
    ElMessage.error('加载指标列表失败')
  } finally {
    loadingMetrics.value = false
  }
}

// 加载客户端列表
const loadClients = async () => {
  if (!queryForm.value.instanceId) return
  loadingClients.value = true
  clients.value = []
  try {
    const response = await pfsApi.getClients(pfsRegion.value, queryForm.value.instanceId)
    if (response.success) {
      clients.value = response.data
    }
  } catch (error) {
    console.error('加载客户端列表失败:', error)
    ElMessage.error('加载客户端列表失败')
  } finally {
    loadingClients.value = false
  }
}

// 处理指标变化
const handleMetricsChange = (value) => {
  emit('update:metrics', value)
}

// 全选指标
const handleSelectAll = () => {
  const allMetrics = []
  Object.values(metricsByCategory.value).forEach(metrics => {
    metrics.forEach(metric => {
      allMetrics.push(metric.name)
    })
  })
  queryForm.value.metrics = allMetrics
  emit('update:metrics', allMetrics)
  ElMessage.success(`已选择 ${allMetrics.length} 个指标`)
}

// 清空指标
const handleClearAll = () => {
  queryForm.value.metrics = []
  emit('update:metrics', [])
  ElMessage.info('已清空选择')
}

// 处理集群切换
const handleInstanceChange = (value) => {
  emit('update:instanceId', value)
  if (queryForm.value.level === 'client') {
    loadClients()
  }
}

// 处理级别变化
const handleLevelChange = (value) => {
  emit('update:level', value)
  // 重新加载指标列表
  loadMetrics()
  // 如果切换到客户端级别，加载客户端列表
  if (value === 'client') {
    loadClients()
  }
}

// 处理时间范围类型变化
const handleTimeRangeTypeChange = () => {
  if (timeRangeType.value === 'quick') {
    handleQuickTimeSelect(selectedQuickTime.value)
  }
}

// 处理快捷时间选择
const handleQuickTimeSelect = (value) => {
  selectedQuickTime.value = value
  const now = Date.now()
  let start = now
  
  switch (value) {
    case '1h':
      start = now - 3600 * 1000
      break
    case '4h':
      start = now - 4 * 3600 * 1000
      break
    case '24h':
      start = now - 24 * 3600 * 1000
      break
  }
  
  emit('update:timeRange', { start, end: now })
}

// 处理自定义时间变化
const handleCustomTimeChange = (value) => {
  if (value && value.length === 2) {
    emit('update:timeRange', {
      start: parseInt(value[0]),
      end: parseInt(value[1])
    })
  }
}

// 处理对比模式变化
const handleCompareModeChange = (value) => {
  emit('update:compareMode', value)
}

// 处理查询
const handleQuery = () => {
  if (!canQuery.value) {
    ElMessage.warning('请完善查询条件')
    return
  }
  emit('query')
}

// 重置表单
const handleReset = () => {
  queryForm.value = {
    metrics: [],
    level: 'cluster',
    instanceId: pfsInstanceIds.value[0] || null,
    clientId: '.*',
    compareMode: false
  }
  timeRangeType.value = 'quick'
  selectedQuickTime.value = '4h'
  handleQuickTimeSelect('4h')
  
  emit('update:metrics', [])
  emit('update:level', 'cluster')
  emit('update:instanceId', queryForm.value.instanceId)
  emit('update:clientId', '.*')
  emit('update:compareMode', false)
}

// 监听 props 变化
watch(() => props.metrics, (value) => {
  queryForm.value.metrics = value
})

watch(() => props.level, (value) => {
  queryForm.value.level = value
})

watch(() => props.instanceId, (value) => {
  queryForm.value.instanceId = value
  if (queryForm.value.level === 'client') {
    loadClients()
  }
})

watch(() => props.clientId, (value) => {
  queryForm.value.clientId = value
})

watch(() => props.compareMode, (value) => {
  queryForm.value.compareMode = value
})

// 组件挂载
onMounted(() => {
  loadPFSConfig()  // 先加载配置
  loadMetrics()
})
</script>

<style scoped>
.query-panel {
  width: 100%;
}

.metrics-select-wrapper {
  width: 100%;
}

.metrics-actions {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
}

.metric-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.metric-name {
  flex: 1;
}

.metric-info {
  color: var(--color-info);
  cursor: help;
}

.client-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.client-ip {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.time-range-wrapper {
  width: 100%;
}

.time-quick-options {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
  flex-wrap: wrap;
  align-items: center;
}

.time-quick-options .el-button {
  transition: all 0.2s ease;
}

.time-quick-options .el-button--primary {
  background: var(--color-primary-600) !important;
  border-color: var(--color-primary-600) !important;
  color: white !important;
  box-shadow: 0 2px 4px rgba(26, 115, 232, 0.3) !important;
}

.time-quick-options .el-button:not(.el-button--primary) {
  background: var(--bg-primary) !important;
  border: 1px solid var(--border-primary) !important;
  color: var(--text-primary) !important;
}

.time-quick-options .el-button:not(.el-button--primary):hover {
  border-color: var(--color-primary-400) !important;
  color: var(--color-primary-600) !important;
}

.form-tip {
  margin-left: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
