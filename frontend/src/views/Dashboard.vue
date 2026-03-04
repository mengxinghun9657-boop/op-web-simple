<template>
  <div class="dashboard">
    <!-- 指标卡片 - Bento Grid -->
    <div class="bento-metrics">
      <div v-for="(card, index) in stats" :key="index" class="bento-metric-card">
        <div class="bento-metric-header">
          <span class="bento-metric-label">{{ card.title }}</span>
          <div class="bento-metric-icon" :class="`bento-metric-icon-${card.iconClass}`">
            <el-icon :size="18"><component :is="card.icon" /></el-icon>
          </div>
        </div>
        <div class="bento-metric-body">
          <span class="bento-metric-value">{{ card.value }}</span>
          <span v-if="card.trend !== 0" class="bento-metric-trend" :class="card.trend > 0 ? 'bento-metric-trend-up' : 'bento-metric-trend-down'">
            <el-icon :size="12"><component :is="card.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
            {{ Math.abs(card.trend) }}%
          </span>
        </div>
      </div>
      <!-- 系统运行时长 -->
      <div class="bento-metric-card">
        <div class="bento-metric-header">
          <span class="bento-metric-label">系统运行</span>
          <div class="bento-metric-icon bento-metric-icon-secondary">
            <el-icon :size="18"><Timer /></el-icon>
          </div>
        </div>
        <div class="bento-metric-body">
          <span class="bento-metric-value">{{ systemUptime }}</span>
        </div>
      </div>
      <!-- 存储使用量 -->
      <div class="bento-metric-card">
        <div class="bento-metric-header">
          <span class="bento-metric-label">存储使用</span>
          <div class="bento-metric-icon bento-metric-icon-info">
            <el-icon :size="18"><FolderOpened /></el-icon>
          </div>
        </div>
        <div class="bento-metric-body">
          <span class="bento-metric-value">{{ storageUsage }}</span>
          <span class="bento-metric-sub">{{ storageFiles }} 文件</span>
        </div>
      </div>
    </div>

    <!-- CMDB资源概览 - Bento Card -->
    <div v-if="cmdbStats" class="bento-card bento-span-full">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon">
            <el-icon :size="16"><Grid /></el-icon>
          </div>
          CMDB 资源概览
        </div>
        <router-link to="/cmdb" class="bento-card-action">
          查看详情
          <el-icon :size="12"><ArrowRight /></el-icon>
        </router-link>
      </div>
      <div class="bento-card-body">
        <div class="bento-stats">
          <div class="bento-stat-item glass-card-light">
            <div class="bento-stat-value">{{ cmdbStats.servers }}</div>
            <div class="bento-stat-label">物理服务器</div>
          </div>
          <div class="bento-stat-item glass-card-light">
            <div class="bento-stat-value">{{ cmdbStats.instances }}</div>
            <div class="bento-stat-label">虚拟实例</div>
          </div>
          <div class="bento-stat-item glass-card-light">
            <div class="bento-stat-value">{{ cmdbStats.active_instances }}</div>
            <div class="bento-stat-label">运行中实例</div>
          </div>
          <div class="bento-stat-item glass-card-light">
            <div class="bento-stat-value">{{ cmdbStats.vcpus_used }}/{{ cmdbStats.vcpus_total }}</div>
            <div class="bento-stat-label">vCPU 使用</div>
            <div class="resource-progress">
              <el-progress 
                :percentage="cmdbStats.vcpu_usage" 
                :stroke-width="6" 
                :show-text="false" 
                :color="getProgressColor(cmdbStats.vcpu_usage)" 
              />
            </div>
          </div>
          <div class="bento-stat-item glass-card-light">
            <div class="bento-stat-value">{{ cmdbStats.memory_used_gb }}/{{ cmdbStats.memory_total_gb }} GB</div>
            <div class="bento-stat-label">内存使用</div>
            <div class="resource-progress">
              <el-progress 
                :percentage="cmdbStats.memory_usage" 
                :stroke-width="6" 
                :show-text="false"
                :color="getProgressColor(cmdbStats.memory_usage)" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表和任务 - Bento Content Grid -->
    <div class="bento-content">
      <!-- 系统概览图表 -->
      <div class="bento-card chart-card">
        <div class="bento-card-header">
          <div class="bento-card-title">
            <div class="bento-card-title-icon" style="background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));">
              <el-icon :size="16"><TrendCharts /></el-icon>
            </div>
            系统资源监控
          </div>
          <div class="chart-legend" v-if="systemHealthData?.current">
            <span class="legend-item">
              <span class="legend-dot" style="background: var(--color-primary-500)"></span>
              CPU {{ systemHealthData.current.cpu }}%
            </span>
            <span class="legend-item">
              <span class="legend-dot" style="background: var(--color-success)"></span>
              内存 {{ systemHealthData.current.memory }}%
            </span>
            <span class="legend-item">
              <span class="legend-dot" style="background: var(--color-secondary-500)"></span>
              磁盘 {{ systemHealthData.current.disk }}%
            </span>
          </div>
        </div>
        <div class="bento-card-body">
          <ChartView v-if="systemHealthData" :options="systemHealthOptions" height="280px" />
          <div v-else class="bento-loading">
            <div class="bento-loading-spinner"></div>
            <span>加载中...</span>
          </div>
        </div>
      </div>

      <!-- AI 助手 -->
      <AIChat />
    </div>

    <!-- 最近任务 -->
    <div class="bento-card task-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, var(--color-warning), var(--color-warning-dark));">
            <el-icon :size="16"><Clock /></el-icon>
          </div>
          最近任务
        </div>
        <router-link to="/task-history" class="bento-card-action">
          查看全部
          <el-icon :size="12"><ArrowRight /></el-icon>
        </router-link>
      </div>
      <div class="bento-card-body">
        <div v-if="recentTasks.length" class="bento-list">
          <div v-for="task in recentTasks" :key="task.id" class="bento-list-item">
            <div class="bento-list-item-info">
              <span class="bento-list-item-title">{{ task.name }}</span>
              <span class="bento-list-item-subtitle">{{ task.created_at }}</span>
            </div>
            <span class="glass-tag" :class="`glass-tag-${getStatusClass(task.status)}`">
              {{ getStatusText(task.status) }}
            </span>
          </div>
        </div>
        <div v-else class="bento-empty">
          <el-icon class="bento-empty-icon"><Document /></el-icon>
          <span class="bento-empty-text">暂无任务记录</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, TrendCharts, Clock, Document, ArrowRight, Grid, Top, Bottom, CircleCheck, Timer, FolderOpened } from '@element-plus/icons-vue'
import ChartView from '@/components/common/ChartView.vue'
import AIChat from '@/components/dashboard/AIChat.vue'
import { getDashboardStats, getRecentTasks, getSystemHealth } from '@/api/dashboard'

const statsData = ref(null)
const recentTasks = ref([])
const systemHealthData = ref(null)
const cmdbStats = ref(null)

const getProgressColor = (percent) => {
  if (percent >= 90) return 'var(--color-error)'
  if (percent >= 70) return 'var(--color-warning)'
  return 'var(--color-success)'
}

const stats = computed(() => {
  const data = statsData.value
  if (!data) {
    return [
      { title: '完成任务', value: '-', icon: 'CircleCheck', iconClass: 'success', trend: 0 },
      { title: '今日分析', value: '-', icon: 'TrendCharts', iconClass: 'primary', trend: 0 },
      { title: '生成报告', value: '-', icon: 'Document', iconClass: 'info', trend: 0 },
      { title: '本周任务', value: '-', icon: 'Clock', iconClass: 'warning', trend: 0 }
    ]
  }
  return [
    { title: '完成任务', value: data.completed_tasks.value + data.completed_tasks.unit, icon: 'CircleCheck', iconClass: 'success', trend: data.completed_tasks.trend },
    { title: '今日分析', value: data.today_analysis.value + data.today_analysis.unit, icon: 'TrendCharts', iconClass: 'primary', trend: data.today_analysis.trend },
    { title: '生成报告', value: data.reports.value + data.reports.unit, icon: 'Document', iconClass: 'info', trend: data.reports.trend },
    { title: '本周任务', value: data.weekly_tasks.value + data.weekly_tasks.unit, icon: 'Clock', iconClass: 'warning', trend: data.weekly_tasks.trend }
  ]
})

const systemUptime = computed(() => statsData.value?.system_uptime?.value || '-')
const storageUsage = computed(() => statsData.value?.storage_usage?.value || '-')
const storageFiles = computed(() => statsData.value?.storage_usage?.files || 0)

const systemHealthOptions = computed(() => {
  if (!systemHealthData.value) return {}
  
  // 使用设计系统的颜色
  const primaryColor = '#3b82f6'
  const successColor = '#22c55e'
  const secondaryColor = '#06b6d4'
  
  return {
    tooltip: { 
      trigger: 'axis', 
      backgroundColor: 'var(--glass-bg-strong)',
      borderColor: 'var(--glass-border)',
      borderWidth: 1,
      textStyle: { color: 'var(--text-primary)', fontSize: 12 },
      extraCssText: 'backdrop-filter: blur(12px); border-radius: 8px;'
    },
    legend: { show: false },
    grid: { top: 10, right: 20, bottom: 30, left: 45 },
    xAxis: { 
      type: 'category', 
      data: systemHealthData.value.time, 
      axisLine: { lineStyle: { color: 'var(--border-color)' } }, 
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 11 } 
    },
    yAxis: { 
      type: 'value', 
      max: 100, 
      axisLabel: { color: 'var(--text-tertiary)', fontSize: 11, formatter: '{value}%' }, 
      splitLine: { lineStyle: { color: 'var(--border-color)', type: 'dashed' } } 
    },
    series: [
      { 
        name: 'CPU', 
        type: 'line', 
        smooth: true, 
        symbol: 'none', 
        data: systemHealthData.value.cpu, 
        lineStyle: { width: 2, color: primaryColor }, 
        itemStyle: { color: primaryColor }, 
        areaStyle: { 
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.25)' }, 
              { offset: 1, color: 'rgba(59, 130, 246, 0)' }
            ] 
          } 
        } 
      },
      { 
        name: '内存', 
        type: 'line', 
        smooth: true, 
        symbol: 'none', 
        data: systemHealthData.value.memory, 
        lineStyle: { width: 2, color: successColor }, 
        itemStyle: { color: successColor }, 
        areaStyle: { 
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [
              { offset: 0, color: 'rgba(34, 197, 94, 0.25)' }, 
              { offset: 1, color: 'rgba(34, 197, 94, 0)' }
            ] 
          } 
        } 
      },
      { 
        name: '磁盘', 
        type: 'line', 
        smooth: true, 
        symbol: 'none', 
        data: systemHealthData.value.disk, 
        lineStyle: { width: 2, color: secondaryColor }, 
        itemStyle: { color: secondaryColor }, 
        areaStyle: { 
          color: { 
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1, 
            colorStops: [
              { offset: 0, color: 'rgba(6, 182, 212, 0.25)' }, 
              { offset: 1, color: 'rgba(6, 182, 212, 0)' }
            ] 
          } 
        } 
      }
    ]
  }
})

const getStatusClass = (status) => ({ 
  completed: 'success', 
  processing: 'primary', 
  pending: 'warning', 
  failed: 'error' 
}[status] || 'primary')

const getStatusText = (status) => ({ 
  completed: '完成', 
  processing: '处理中', 
  pending: '等待', 
  failed: '失败' 
}[status] || status)

const fetchDashboardData = async () => {
  try {
    const [statsRes, tasksRes, healthRes] = await Promise.all([
      getDashboardStats(),
      getRecentTasks(),
      getSystemHealth()
    ])
    
    // 检查统计数据 - 使用统一格式
    if (!statsRes || statsRes.success === false) {
      ElMessage.warning('统计数据加载失败，请刷新重试')
    } else {
      // 统一使用 data 字段
      statsData.value = statsRes.data
      cmdbStats.value = statsRes.data?.cmdb || null
    }
    
    // 检查任务数据
    if (!tasksRes || tasksRes.success === false) {
      ElMessage.warning('任务数据加载失败')
    } else {
      recentTasks.value = tasksRes.data
    }
    
    // 检查健康数据
    if (!healthRes || healthRes.success === false) {
      console.warn('系统监控数据加载失败')
    } else {
      systemHealthData.value = healthRes.data
    }
  } catch (error) {
    ElMessage.error('数据加载失败，请检查网络连接')
    console.error('获取仪表盘数据失败:', error)
  }
}

let timer = null

// 页面可见性监听
const handleVisibilityChange = () => {
  if (document.hidden) {
    // 页面不可见时停止定时刷新
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  } else {
    // 页面可见时恢复定时刷新
    if (!timer) {
      fetchDashboardData() // 立即刷新一次
      timer = setInterval(fetchDashboardData, 30000)
    }
  }
}

onMounted(() => {
  fetchDashboardData()
  timer = setInterval(fetchDashboardData, 30000)
  
  // 监听页面可见性变化
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  
  // 移除监听器
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 图表卡片特殊样式 */
.chart-card .bento-card-body {
  padding: var(--spacing-4);
}

/* 图表图例 */
.chart-legend {
  display: flex;
  gap: var(--spacing-4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* 任务卡片 */
.task-card .bento-card-body {
  max-height: 340px;
  overflow-y: auto;
}

/* 指标子文本 */
.bento-metric-sub {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-left: var(--spacing-2);
}

/* 资源进度条 */
.resource-progress {
  margin-top: var(--spacing-2);
  width: 100%;
}

.resource-progress :deep(.el-progress-bar__outer) {
  background: var(--bg-hover);
  border-radius: var(--radius-full);
}

.resource-progress :deep(.el-progress-bar__inner) {
  border-radius: var(--radius-full);
}

/* 统计项增强 */
.bento-stat-item {
  padding: var(--spacing-4);
  border-radius: var(--radius-lg);
  text-align: center;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .bento-stats {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .bento-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .chart-legend {
    display: none;
  }
}

@media (max-width: 480px) {
  .bento-stats {
    grid-template-columns: 1fr;
  }
}
</style>
