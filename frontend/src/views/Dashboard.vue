<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          系统仪表盘
        </div>
        <div class="page-subtitle">实时监控系统运行状态和资源使用情况</div>
      </div>
    </div>

    <!-- 指标卡片 - 统一样式 -->
    <div class="stats-grid">
      <div v-for="(card, index) in stats" :key="index" class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">{{ card.title }}</div>
          <div :class="`stat-card-icon ${card.iconClass}`">
            <el-icon :size="20"><component :is="card.icon" /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ card.value }}</div>
        <div v-if="card.trend !== 0" :class="`stat-card-trend ${card.trend > 0 ? 'up' : 'down'}`">
          <el-icon><component :is="card.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
          {{ Math.abs(card.trend) }}%
        </div>
      </div>
      <!-- 系统运行时长 -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">系统运行</div>
          <div class="stat-card-icon info">
            <el-icon :size="20"><Timer /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ systemUptime }}</div>
      </div>
      <!-- 存储使用量 -->
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">存储使用</div>
          <div class="stat-card-icon warning">
            <el-icon :size="20"><FolderOpened /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ storageUsage }}</div>
        <div class="stat-card-trend">
          {{ storageFiles }} 文件
        </div>
      </div>
    </div>

    <!-- CMDB资源概览 -->
    <div v-if="cmdbStats" class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Grid /></el-icon>
          CMDB 资源概览
        </div>
        <div class="content-card-extra">
          <router-link to="/cmdb">
            <el-button text type="primary">
              查看详情
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </router-link>
        </div>
      </div>
      <div class="content-card-body">
        <div class="cmdb-charts-grid">
          <!-- 左：服务器与实例数量柱状图 -->
          <div class="cmdb-chart-item">
            <div class="cmdb-chart-title">资源数量</div>
            <ChartView :options="cmdbBarOptions" height="200px" />
          </div>
          <!-- 中：vCPU 仪表盘 -->
          <div class="cmdb-chart-item">
            <div class="cmdb-chart-title">vCPU 使用率</div>
            <ChartView :options="cmdbVcpuGaugeOptions" height="200px" />
            <div class="cmdb-chart-label">{{ cmdbStats.vcpus_used }} / {{ cmdbStats.vcpus_total }}</div>
          </div>
          <!-- 右：内存仪表盘 -->
          <div class="cmdb-chart-item">
            <div class="cmdb-chart-title">内存使用率</div>
            <ChartView :options="cmdbMemGaugeOptions" height="200px" />
            <div class="cmdb-chart-label">{{ cmdbStats.memory_used_gb }} / {{ cmdbStats.memory_total_gb }} GB</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表和任务 -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: var(--space-4);">
      <!-- 系统概览图表 -->
      <div class="content-card">
        <div class="content-card-header">
          <div class="content-card-title">
            <el-icon><TrendCharts /></el-icon>
            系统资源监控
          </div>
          <div class="content-card-extra" v-if="systemHealthData?.current" style="display: flex; gap: var(--space-3); font-size: var(--text-xs);">
            <span style="display: flex; align-items: center; gap: 4px; color: var(--text-secondary);">
              <span class="status-dot primary"></span>
              CPU {{ systemHealthData.current.cpu }}%
            </span>
            <span style="display: flex; align-items: center; gap: 4px; color: var(--text-secondary);">
              <span class="status-dot success"></span>
              内存 {{ systemHealthData.current.memory }}%
            </span>
            <span style="display: flex; align-items: center; gap: 4px; color: var(--text-secondary);">
              <span class="status-dot info"></span>
              磁盘 {{ systemHealthData.current.disk }}%
            </span>
          </div>
        </div>
        <div class="content-card-body">
          <ChartView v-if="systemHealthData" :options="systemHealthOptions" height="280px" />
          <div v-else class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <div class="loading-state-text">加载中...</div>
          </div>
        </div>
      </div>

      <!-- AI 助手 -->
      <AIChat />
    </div>

    <!-- 最近任务 -->
    <div class="content-card" style="grid-column: span 2;">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Clock /></el-icon>
          最近任务
        </div>
        <div class="content-card-extra">
          <router-link to="/task-history">
            <el-button text type="primary">
              查看全部
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </router-link>
        </div>
      </div>
      <div class="content-card-body">
        <div v-if="recentTasks.length" style="display: flex; flex-direction: column; gap: var(--space-3);">
          <div v-for="task in recentTasks" :key="task.id" style="display: flex; justify-content: space-between; align-items: center; padding: var(--space-3); border-radius: var(--radius-lg); background: var(--bg-secondary);">
            <div>
              <div style="font-weight: var(--font-medium); color: var(--text-primary); margin-bottom: var(--space-1);">{{ task.name }}</div>
              <div style="font-size: var(--text-sm); color: var(--text-tertiary);">{{ task.created_at }}</div>
            </div>
            <span :class="`status-badge ${getStatusClass(task.status)}`">
              {{ getStatusText(task.status) }}
            </span>
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-state-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="empty-state-title">暂无任务记录</div>
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

// CMDB 柱状图：物理服务器 / 虚拟实例 / 运行中实例
const cmdbBarOptions = computed(() => {
  if (!cmdbStats.value) return {}
  const s = cmdbStats.value
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#dadce0',
      borderWidth: 1,
      textStyle: { color: '#5f6368', fontSize: 12 }
    },
    grid: { top: 16, right: 16, bottom: 32, left: 52 },
    xAxis: {
      type: 'category',
      data: ['物理服务器', '虚拟实例', '运行中实例'],
      axisLine: { lineStyle: { color: '#dadce0' } },
      axisLabel: { color: '#80868b', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#80868b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f3f4', type: 'dashed' } }
    },
    series: [{
      type: 'bar',
      data: [
        { value: s.servers, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#1a73e8' }, { offset: 1, color: '#8ab4f8' }] } } },
        { value: s.instances, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#06b6d4' }, { offset: 1, color: '#67e8f9' }] } } },
        { value: s.active_instances, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#1e8e3e' }, { offset: 1, color: '#81c995' }] } } }
      ],
      barWidth: '40%',
      borderRadius: [4, 4, 0, 0],
      label: { show: true, position: 'top', color: '#80868b', fontSize: 11 }
    }]
  }
})

// 通用 gauge 图生成函数
const makeGaugeOptions = (percentage, color, label) => ({
  series: [{
    type: 'gauge',
    startAngle: 210,
    endAngle: -30,
    min: 0,
    max: 100,
    splitNumber: 5,
    radius: '85%',
    center: ['50%', '60%'],
    axisLine: {
      lineStyle: {
        width: 14,
        color: [
          [percentage / 100, color],
          [1, '#f1f3f4']
        ]
      }
    },
    pointer: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { show: false },
    detail: {
      valueAnimation: true,
      formatter: '{value}%',
      color: '#5f6368',
      fontSize: 20,
      fontWeight: 700,
      offsetCenter: [0, '10%']
    },
    data: [{ value: percentage, name: label }],
    title: { show: false }
  }]
})

const cmdbVcpuGaugeOptions = computed(() => {
  if (!cmdbStats.value) return {}
  const pct = cmdbStats.value.vcpu_usage || 0
  const color = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#3b82f6'
  return makeGaugeOptions(pct, color, 'vCPU')
})

const cmdbMemGaugeOptions = computed(() => {
  if (!cmdbStats.value) return {}
  const pct = cmdbStats.value.memory_usage || 0
  const color = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#06b6d4'
  return makeGaugeOptions(pct, color, '内存')
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
/* CMDB 图表网格：左柱状图宽，右两个 gauge 各占一列 */
.cmdb-charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: var(--space-4);
  align-items: start;
}

.cmdb-chart-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cmdb-chart-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  align-self: flex-start;
}

.cmdb-chart-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-top: -8px;
}

/* 网格布局自适应 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr) !important;
  }
  .cmdb-charts-grid {
    grid-template-columns: 1fr 1fr;
  }
  .cmdb-charts-grid .cmdb-chart-item:first-child {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
  .cmdb-charts-grid {
    grid-template-columns: 1fr 1fr;
  }
  .cmdb-charts-grid .cmdb-chart-item:first-child {
    grid-column: span 2;
  }

  div[style*="grid-template-columns: 2fr 1fr"] {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr !important;
  }
  .cmdb-charts-grid {
    grid-template-columns: 1fr;
  }
  .cmdb-charts-grid .cmdb-chart-item:first-child {
    grid-column: span 1;
  }
}
</style>
