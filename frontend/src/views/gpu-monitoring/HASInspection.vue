<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Bell /></el-icon>
          </div>
          HAS自动化巡检
        </div>
        <div class="page-subtitle">点击"开始采集"后直连 BCE 拉取 GPU HAS 巡检数据，写入主库并自动刷新展示</div>
      </div>
      <div class="page-actions">
        <el-button @click="collectData" :loading="syncing">
          <el-icon><Upload /></el-icon>
          开始采集
        </el-button>
        <el-button type="primary" @click="fetchData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="exportTable" :disabled="filteredInstances.length === 0">
          <el-icon><Download /></el-icon>
          导出 CSV
        </el-button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="content-card stat-card">
        <div class="content-card-body">
          <div class="stat-label">实例总数</div>
          <div class="stat-value">{{ summary.total }}</div>
        </div>
      </div>
      <div class="content-card stat-card">
        <div class="content-card-body">
          <div class="stat-label">在线实例</div>
          <div class="stat-value success">{{ summary.online }}</div>
        </div>
      </div>
      <div class="content-card stat-card">
        <div class="content-card-body">
          <div class="stat-label">离线实例</div>
          <div class="stat-value danger">{{ summary.offline }}</div>
        </div>
      </div>
      <div class="content-card stat-card">
        <div class="content-card-body">
          <div class="stat-label">最近采集时间</div>
          <div class="stat-time">{{ collectTime || '-' }}</div>
        </div>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Search /></el-icon>
          筛选条件
        </div>
      </div>
      <div class="content-card-body">
        <el-form :inline="true" class="filter-form">
          <el-form-item label="关键字">
            <el-input
              v-model="filters.keyword"
              placeholder="实例ID / 名称 / IP"
              clearable
              class="filter-input"
            />
          </el-form-item>
          <el-form-item label="GPU 型号">
            <el-select v-model="filters.gpuCard" placeholder="全部" clearable class="filter-select">
              <el-option v-for="option in gpuOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item label="在线状态">
            <el-select v-model="filters.status" placeholder="全部" clearable class="filter-select">
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="summary-grid">
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">GPU 型号分布</div>
        </div>
        <div class="content-card-body">
          <div class="tag-group">
            <el-tag v-for="(count, key) in summary.gpu_cards" :key="key" class="summary-tag">{{ key }} · {{ count }}</el-tag>
          </div>
        </div>
      </div>
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">区域分布</div>
        </div>
        <div class="content-card-body">
          <div class="tag-group">
            <el-tag v-for="(count, key) in summary.regions" :key="key" type="info" class="summary-tag">{{ key }} · {{ count }}</el-tag>
          </div>
        </div>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">巡检实例列表</div>
        <div class="content-card-extra">
          <el-tag type="info">当前 {{ filteredInstances.length }} 条</el-tag>
        </div>
      </div>
      <div class="content-card-body">
        <el-table :data="filteredInstances" v-loading="loading || syncing" class="google-table" height="560">
          <el-table-column prop="index" label="#" width="70" />
          <el-table-column prop="id" label="实例ID" min-width="160" />
          <el-table-column prop="name" label="实例名称" min-width="260" show-overflow-tooltip />
          <el-table-column prop="internal_ip" label="内网IP" width="140" />
          <el-table-column prop="gpu_card" label="GPU 型号" width="120">
            <template #default="{ row }">
              <el-tag :type="gpuTagType(row.gpu_card)">{{ row.gpu_card }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="region" label="区域" width="100" />
          <el-table-column prop="has_alive" label="HAS 状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.has_alive === 'online' ? 'success' : 'danger'">
                {{ row.has_alive === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_update" label="最近更新时间" min-width="180" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Download, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { collectHASInspection, getHASInspection } from '@/api/gpuMonitoring'
import { pollTaskStatus } from '@/utils/taskPoller'

const loading = ref(false)
const syncing = ref(false)
const collectTime = ref('')
const instances = ref([])
const summary = reactive({
  total: 0,
  online: 0,
  offline: 0,
  gpu_cards: {},
  regions: {},
})
const filters = reactive({
  keyword: '',
  gpuCard: '',
  status: '',
})

const gpuOptions = computed(() => Object.keys(summary.gpu_cards || {}))

const filteredInstances = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return instances.value.filter((item) => {
    const matchedKeyword = !keyword || [item.id, item.name, item.internal_ip].some((value) => (value || '').toLowerCase().includes(keyword))
    const matchedGpu = !filters.gpuCard || item.gpu_card === filters.gpuCard
    const matchedStatus = !filters.status || item.has_alive === filters.status
    return matchedKeyword && matchedGpu && matchedStatus
  })
})

const gpuTagType = (gpuCard) => {
  if (gpuCard === 'H20') return 'success'
  if (gpuCard === 'L20') return 'warning'
  if (gpuCard === 'H800') return 'danger'
  return 'info'
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getHASInspection()
    if (!response.success) {
      throw new Error(response.error || response.message || '获取失败')
    }
    instances.value = response.data.instances || []
    collectTime.value = response.data.collect_time || ''
    Object.assign(summary, response.data.summary || {})
  } catch (error) {
    ElMessage.error(error.message || '获取 HAS 自动化巡检数据失败')
  } finally {
    loading.value = false
  }
}

const collectData = async () => {
  syncing.value = true
  try {
    const response = await collectHASInspection()
    if (!response.success) {
      throw new Error(response.error || response.message || '采集任务创建失败')
    }

    const { task_id: taskId } = response.data || {}
    ElMessage.success('采集任务已创建，正在拉取最新巡检数据')

    pollTaskStatus(
      taskId,
      () => {},
      async () => {
        syncing.value = false
        ElMessage.success('GPU HAS 巡检数据采集完成')
        await fetchData()
      },
      (message) => {
        syncing.value = false
        ElMessage.error(message || '采集失败')
      }
    )
  } catch (error) {
    syncing.value = false
    ElMessage.error(error.message || '创建采集任务失败')
  }
}

const exportTable = () => {
  const headers = ['实例ID', '实例名称', '内网IP', 'GPU型号', '区域', '状态', '最近更新时间']
  const rows = filteredInstances.value.map((item) => [
    item.id,
    item.name,
    item.internal_ip || '',
    item.gpu_card || '',
    item.region || '',
    item.has_alive === 'online' ? '在线' : '离线',
    item.last_update || '',
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => `"${String(value ?? '').replace(/"/g, '""')}"`).join(','))
    .join('\n')

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `has_auto_inspection_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(fetchData)
</script>

<style scoped>
.stats-grid,
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.stat-card .content-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.stat-value {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.stat-value.success {
  color: var(--color-success);
}

.stat-value.danger {
  color: var(--color-danger);
}

.stat-time {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  line-height: 1.5;
}

.filter-input,
.filter-select {
  width: 220px;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.summary-tag {
  margin: 0;
}
</style>
