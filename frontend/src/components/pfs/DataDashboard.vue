<template>
  <div class="data-dashboard">
    <!-- 图表区域 -->
    <div v-if="hasData" class="charts-section">
      <!-- 普通模式：按分类显示图表 -->
      <template v-if="!compareMode">
        <div
          v-for="category in metricCategories"
          :key="category"
          class="chart-container"
        >
          <div class="chart-header">
            <h3 class="chart-title">{{ category }} - 趋势图</h3>
            <el-button-group>
              <el-button
                :type="chartType === 'line' ? 'primary' : ''"
                size="small"
                @click="chartType = 'line'"
              >
                折线图
              </el-button>
              <el-button
                :type="chartType === 'area' ? 'primary' : ''"
                size="small"
                @click="chartType = 'area'"
              >
                面积图
              </el-button>
            </el-button-group>
          </div>
          <div :ref="el => setCategoryChartRef(category, el)" class="chart" style="height: 400px;"></div>
        </div>
      </template>

      <!-- 对比模式：对比图表 -->
      <div v-if="compareMode" class="chart-container">
        <div class="chart-header">
          <h3 class="chart-title">对比分析图</h3>
        </div>
        <div ref="compareChartRef" class="chart" style="height: 400px;"></div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div v-if="hasData" class="table-section">
      <div class="table-header">
        <h3 class="table-title">{{ compareMode ? '对比分析数据' : '详细数据' }}</h3>
        <div class="table-actions">
          <el-button size="small" @click="exportTableData">
            <el-icon><Download /></el-icon>
            导出表格
          </el-button>
        </div>
      </div>
      
      <!-- 对比模式表格 -->
      <el-table
        v-if="compareMode"
        :data="tableData"
        stripe
        border
        :max-height="500"
        style="width: 100%"
      >
        <el-table-column prop="metric_name" label="指标名称" width="200" />
        <el-table-column prop="zh_name" label="中文名称" width="200" />
        <el-table-column label="今天" width="150">
          <template #default="{ row }">
            {{ formatValue(row.today_avg, row.unit) }}
          </template>
        </el-table-column>
        <el-table-column label="昨天同期" width="150">
          <template #default="{ row }">
            {{ formatValue(row.yesterday_avg, row.unit) }}
          </template>
        </el-table-column>
        <el-table-column label="变化" width="120" sortable :sort-method="(a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent)">
          <template #default="{ row }">
            <span :style="{ color: getChangeColor(row.change_direction) }">
              {{ row.change_direction === 'up' ? '↑' : row.change_direction === 'down' ? '↓' : '→' }}
              {{ Math.abs(row.change_percent).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="概述" width="120">
          <template #default="{ row }">
            <el-tag :type="getChangeStatusTagType(row.change_status)" size="small">
              {{ getChangeStatusText(row.change_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unit_zh" label="单位" width="100" />
      </el-table>
      
      <!-- 普通模式表格 -->
      <template v-else>
        <!-- 有客户端数据：按客户端分组展示 -->
        <template v-if="hasClientData">
          <div class="client-filter">
            <span class="client-filter-label">筛选客户端：</span>
            <el-select
              v-model="selectedClientFilter"
              clearable
              placeholder="全部客户端"
              size="small"
              style="width: 240px;"
            >
              <el-option
                v-for="cid in allClientIds"
                :key="cid"
                :label="cid"
                :value="cid"
              />
            </el-select>
          </div>
          <div
            v-for="clientId in filteredClientIds"
            :key="clientId"
            class="client-table-block"
          >
            <div class="client-table-title">
              <el-icon><Connection /></el-icon>
              客户端：{{ clientId }}
              <el-tag size="small" type="info" style="margin-left: 8px;">
                {{ clientTableData(clientId).length }} 条
              </el-tag>
            </div>
            <el-table
              :data="clientTableData(clientId)"
              stripe
              border
              :max-height="400"
              style="width: 100%"
            >
              <el-table-column prop="timestamp" label="时间" width="180" sortable>
                <template #default="{ row }">
                  {{ formatTimestamp(row.timestamp) }}
                </template>
              </el-table-column>
              <el-table-column prop="metric_name" label="指标名称" width="200" />
              <el-table-column prop="metric_zh_name" label="中文名称" width="200" />
              <el-table-column prop="value" label="数值" width="150" sortable>
                <template #default="{ row }">
                  {{ formatValue(row.value, row.unit) }}
                </template>
              </el-table-column>
              <el-table-column prop="unit_zh" label="单位" width="100" />
              <el-table-column prop="client_ip" label="客户端IP" width="150" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.status)" size="small">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>

        <!-- 集群级别：原有单表格 -->
        <el-table
          v-else
          :data="tableData"
          stripe
          border
          :max-height="500"
          style="width: 100%"
        >
          <el-table-column prop="timestamp" label="时间" width="180" sortable>
            <template #default="{ row }">
              {{ formatTimestamp(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column prop="metric_name" label="指标名称" width="200" />
          <el-table-column prop="metric_zh_name" label="中文名称" width="200" />
          <el-table-column prop="value" label="数值" width="150" sortable>
            <template #default="{ row }">
              {{ formatValue(row.value, row.unit) }}
            </template>
          </el-table-column>
          <el-table-column prop="unit_zh" label="单位" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="暂无数据"
      :image-size="150"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Connection } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps({
  metricsData: {
    type: Array,
    default: () => []
  },
  compareMode: {
    type: Boolean,
    default: false
  }
})

// 图表实例
const chartRef = ref(null)
const compareChartRef = ref(null)
const categoryChartRefs = ref({})
let chartInstances = {}
let compareChartInstance = null

// 设置分类图表引用
const setCategoryChartRef = (category, el) => {
  if (el) {
    categoryChartRefs.value[category] = el
  }
}

// 图表类型
const chartType = ref('line')

// 计算属性
const hasData = computed(() => props.metricsData.length > 0)

// 获取所有指标分类
const metricCategories = computed(() => {
  const categories = new Set()
  props.metricsData.forEach(metric => {
    if (metric.category) {
      categories.add(metric.category)
    }
  })
  return Array.from(categories)
})

// 按分类分组指标
const metricsByCategory = computed(() => {
  const grouped = {}
  props.metricsData.forEach(metric => {
    const category = metric.category || '其他'
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push(metric)
  })
  return grouped
})

const hasClientData = computed(() => {
  return props.metricsData.some(metric =>
    metric.data_points?.some(point => point.labels?.ClientId || point.client_id)
  )
})

// 客户端筛选
const selectedClientFilter = ref('')

// 所有客户端 ID（去重排序）
const allClientIds = computed(() => {
  const ids = new Set()
  props.metricsData.forEach(metric => {
    metric.data_points?.forEach(point => {
      const cid = point.client_id || point.labels?.ClientId
      if (cid) ids.add(cid)
    })
  })
  return Array.from(ids).sort()
})

// 筛选后的客户端列表
const filteredClientIds = computed(() => {
  if (selectedClientFilter.value) return [selectedClientFilter.value]
  return allClientIds.value
})

// 指定客户端的表格数据
const clientTableData = (clientId) => {
  const data = []
  props.metricsData.forEach(metricResult => {
    const dataPoints = metricResult.data_points || []
    dataPoints.forEach(point => {
      const cid = point.client_id || point.labels?.ClientId || ''
      if (cid !== clientId) return
      data.push({
        timestamp: point.timestamp,
        metric_name: metricResult.metric_name,
        metric_zh_name: metricResult.zh_name,
        value: point.value,
        unit: metricResult.unit,
        unit_zh: metricResult.unit_zh,
        client_id: cid,
        client_ip: point.client_ip || point.labels?.ClientIp || '-',
        status: determineStatus(point.value, metricResult)
      })
    })
  })
  return data.sort((a, b) => b.timestamp - a.timestamp)
}

const tableData = computed(() => {
  // 对比模式：显示对比数据
  if (props.compareMode && props.metricsData.length > 0) {
    // 检查是否是对比数据格式（包含 today/yesterday 字段）
    const firstMetric = props.metricsData[0]
    if (firstMetric.today && firstMetric.yesterday) {
      return props.metricsData.map(metric => ({
        metric_name: metric.metric_name,
        zh_name: metric.zh_name,
        unit: metric.unit,           // 英文单位，用于格式化
        unit_zh: metric.unit_zh,     // 中文单位，用于显示
        today_avg: metric.today.avg,
        yesterday_avg: metric.yesterday.avg,
        change_percent: metric.change.percent,
        change_direction: metric.change.direction,
        change_status: metric.change.status,
        today_status: metric.today.status,
        yesterday_status: metric.yesterday.status
      }))
    }
  }
  
  // 普通模式：显示详细数据点
  const data = []
  
  props.metricsData.forEach(metricResult => {
    // 后端返回的是 PFSMetricResult，字段在顶层
    const dataPoints = metricResult.data_points || []
    
    dataPoints.forEach(point => {
      data.push({
        timestamp: point.timestamp,
        metric_name: metricResult.metric_name,
        metric_zh_name: metricResult.zh_name,
        value: point.value,
        unit: metricResult.unit,
        unit_zh: metricResult.unit_zh,
        client_id: point.client_id || point.labels?.ClientId || '-',
        client_ip: point.client_ip || point.labels?.ClientIp || '-',
        status: determineStatus(point.value, metricResult)
      })
    })
  })
  
  return data.sort((a, b) => b.timestamp - a.timestamp)
})

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  // timestamp 是秒级时间戳，需要转换为毫秒
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化数值
const formatValue = (value, unit) => {
  if (value === null || value === undefined) return '-'
  
  if (unit === 'bytes' || unit === 'binBps' || unit === '字节') {
    return formatBytes(value)
  } else if (unit === 'percentunit' || unit === '百分比') {
    return (value * 100).toFixed(2) + '%'
  } else if (unit === 'µs' || unit === '微秒') {
    return value.toFixed(2) + ' µs'
  } else if (unit === 'ops' || unit === 'iops') {
    return value.toFixed(2) + ' ops'
  } else {
    return value.toFixed(2)
  }
}

// 格式化字节
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 判断状态
const determineStatus = (value, metric) => {
  if (!value || !metric.warn_threshold) return 'normal'
  
  if (metric.unit === 'percentunit') {
    if (value >= metric.critical_threshold) return 'critical'
    if (value >= metric.warn_threshold) return 'warning'
  } else if (metric.unit === 'µs') {
    if (value >= metric.critical_threshold) return 'critical'
    if (value >= metric.warn_threshold) return 'warning'
  }
  
  return 'normal'
}

const getStatusTagType = (status) => {
  switch (status) {
    case 'critical': return 'danger'
    case 'warning': return 'warning'
    default: return 'success'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'critical': return '严重'
    case 'warning': return '警告'
    default: return '正常'
  }
}

// 对比模式相关函数
const getChangeColor = (direction) => {
  switch (direction) {
    case 'up': return '#f56c6c'
    case 'down': return '#67c23a'
    default: return '#909399'
  }
}

const getChangeStatusTagType = (status) => {
  switch (status) {
    case 'critical': return 'danger'
    case 'warning': return 'warning'
    default: return 'success'
  }
}

const getChangeStatusText = (status) => {
  switch (status) {
    case 'critical': return '剧烈变化'
    case 'warning': return '波动'
    default: return '稳定'
  }
}

// 初始化图表
const initChart = () => {
  if (!hasData.value) return
  
  // 清理旧图表
  Object.values(chartInstances).forEach(instance => {
    instance?.dispose()
  })
  chartInstances = {}
  
  if (compareChartInstance) {
    compareChartInstance.dispose()
    compareChartInstance = null
  }
  
  // 对比模式：创建对比图表
  if (props.compareMode) {
    nextTick(() => {
      if (compareChartRef.value) {
        compareChartInstance = echarts.init(compareChartRef.value)
        updateCompareChart()
      }
    })
  } else {
    // 普通模式：为每个分类创建图表
    nextTick(() => {
      metricCategories.value.forEach(category => {
        const chartEl = categoryChartRefs.value[category]
        if (chartEl) {
          chartInstances[category] = echarts.init(chartEl)
          updateCategoryChart(category)
        }
      })
    })
  }
}

// 图表配色 - 与项目 Google Blue 设计系统对齐
const DD_COLORS = ['#1a73e8', '#06b6d4', '#f9ab00', '#d93025', '#1e8e3e', '#9c27b0', '#0288d1', '#e65100']

// 更新分类图表
const updateCategoryChart = (category) => {
  const chartInstance = chartInstances[category]
  if (!chartInstance) return

  const categoryMetrics = metricsByCategory.value[category] || []
  if (categoryMetrics.length === 0) return

  const series = []
  const legend = []

  // 判断是否有客户端维度数据
  const isClientLevel = categoryMetrics.some(m =>
    m.data_points?.some(p => p.client_id || p.labels?.ClientId)
  )

  if (isClientLevel) {
    // 客户端级别：每个指标 × 每个客户端 = 一条 series
    categoryMetrics.forEach((metricResult) => {
      const dataPoints = metricResult.data_points || []

      // 按 clientId 分组
      const byClient = {}
      dataPoints.forEach(point => {
        const cid = point.client_id || point.labels?.ClientId || 'unknown'
        if (!byClient[cid]) byClient[cid] = []
        byClient[cid].push(point)
      })

      const clientIds = Object.keys(byClient).sort()
      clientIds.forEach((cid, cidx) => {
        const color = DD_COLORS[(legend.length) % DD_COLORS.length]
        const seriesName = clientIds.length === 1
          ? metricResult.zh_name
          : `${metricResult.zh_name} [${cid}]`

        const data = byClient[cid].map(p => [p.timestamp * 1000, p.value])

        legend.push(seriesName)
        series.push({
          name: seriesName,
          type: chartType.value === 'area' ? 'line' : chartType.value,
          data,
          smooth: false,
          symbol: 'none',
          lineStyle: { width: 1.5, color },
          itemStyle: { color },
          areaStyle: chartType.value === 'area' ? { color, opacity: 0.06 } : undefined,
          emphasis: { focus: 'series' },
          // 存储单位供 tooltip 用
          _unit: metricResult.unit
        })
      })
    })
  } else {
    // 集群级别：原有逻辑，按指标分 series
    categoryMetrics.forEach((metricResult, idx) => {
      const dataPoints = metricResult.data_points || []
      const color = DD_COLORS[idx % DD_COLORS.length]

      const data = dataPoints.map(point => [
        point.timestamp * 1000,
        point.value
      ])

      legend.push(metricResult.zh_name)

      series.push({
        name: metricResult.zh_name,
        type: chartType.value === 'area' ? 'line' : chartType.value,
        data: data,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color },
        itemStyle: { color },
        areaStyle: chartType.value === 'area' ? { color, opacity: 0.06 } : undefined,
        emphasis: { focus: 'series' },
        _unit: metricResult.unit
      })
    })
  }

  const option = {
    title: {
      text: `${category}指标趋势`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        let result = `<div style="font-weight: bold;">${formatTimestamp(params[0].value[0] / 1000)}</div>`
        params.forEach(param => {
          const s = series.find(s => s.name === param.seriesName)
          const value = formatValue(param.value[1], s?._unit)
          result += `<div>${param.marker} ${param.seriesName}: ${value}</div>`
        })
        return result
      }
    },
    legend: {
      data: legend,
      top: 30,
      type: 'scroll'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: { color: '#80868b' },
      axisLine: { lineStyle: { color: '#dadce0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#80868b' },
      splitLine: { lineStyle: { color: '#f1f3f4', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: series,
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        bottom: 10
      }
    ]
  }

  chartInstance.setOption(option)
}

// 更新对比图表
const updateCompareChart = () => {
  if (!compareChartInstance) return
  
  const series = []
  const legend = []
  
  // 为每个指标创建今天和昨天两条线
  props.metricsData.forEach(metric => {
    // 今天的数据
    if (metric.today && metric.today.data_points) {
      const todayData = metric.today.data_points.map(point => [
        point.timestamp * 1000,
        point.value
      ])
      
      legend.push(`${metric.zh_name} (今天)`)
      series.push({
        name: `${metric.zh_name} (今天)`,
        type: 'line',
        data: todayData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#1a73e8' },
        itemStyle: { color: '#1a73e8' },
        areaStyle: { color: '#1a73e8', opacity: 0.06 },
        emphasis: { focus: 'series' }
      })
    }
    
    // 昨天的数据 - 时间轴对齐到今天
    if (metric.yesterday && metric.yesterday.data_points) {
      const yesterdayData = metric.yesterday.data_points.map(point => {
        // 将昨天的时间戳调整到今天的时间轴（+24小时）
        const alignedTimestamp = (point.timestamp + 24 * 3600) * 1000
        return [alignedTimestamp, point.value]
      })
      
      legend.push(`${metric.zh_name} (昨天)`)
      series.push({
        name: `${metric.zh_name} (昨天)`,
        type: 'line',
        data: yesterdayData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#f9ab00', type: 'dashed' },
        itemStyle: { color: '#f9ab00' },
        emphasis: { focus: 'series' }
      })
    }
  })
  
  const option = {
    title: {
      text: '对比分析图',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      confine: true,
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        
        // 显示相对时间（HH:mm）
        const date = new Date(params[0].value[0])
        const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        
        let result = `<div style="font-weight: bold;">时间: ${timeStr}</div>`
        
        // 按指标分组，避免重复显示
        const metricGroups = {}
        params.forEach(param => {
          const metricName = param.seriesName.replace(' (今天)', '').replace(' (昨天)', '')
          if (!metricGroups[metricName]) {
            metricGroups[metricName] = { today: null, yesterday: null }
          }
          
          if (param.seriesName.includes('(今天)')) {
            metricGroups[metricName].today = param
          } else if (param.seriesName.includes('(昨天)')) {
            metricGroups[metricName].yesterday = param
          }
        })
        
        // 按指标显示今天和昨天的数据
        Object.entries(metricGroups).forEach(([metricName, data]) => {
          const metric = props.metricsData.find(m => m.zh_name === metricName)
          result += `<div style="margin-top: 8px; font-weight: bold;">${metricName}</div>`
          
          if (data.today) {
            const value = formatValue(data.today.value[1], metric?.unit)
            result += `<div>${data.today.marker} 今天: ${value}</div>`
          }
          if (data.yesterday) {
            const value = formatValue(data.yesterday.value[1], metric?.unit)
            result += `<div>${data.yesterday.marker} 昨天: ${value}</div>`
          }
        })
        
        return result
      }
    },
    legend: {
      data: legend,
      top: 30,
      type: 'scroll'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        color: '#80868b',
        formatter: (value) => {
          const date = new Date(value)
          return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        }
      },
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#80868b' },
      splitLine: { lineStyle: { color: '#f1f3f4', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: series,
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        bottom: 10
      }
    ]
  }
  
  compareChartInstance.setOption(option)
}

// 导出表格数据
const exportTableData = () => {
  try {
    // 构建CSV内容
    const headers = ['时间', '指标名称', '中文名称', '数值', '单位']
    if (hasClientData.value) {
      headers.push('客户端ID', '客户端IP')
    }
    headers.push('状态')
    
    let csv = '\uFEFF' + headers.join(',') + '\n'
    
    tableData.value.forEach(row => {
      const values = [
        formatTimestamp(row.timestamp),
        row.metric_name,
        row.metric_zh_name,
        formatValue(row.value, row.unit),
        row.unit_zh
      ]
      
      if (hasClientData.value) {
        values.push(row.client_id, row.client_ip)
      }
      
      values.push(getStatusText(row.status))
      
      csv += values.join(',') + '\n'
    })
    
    // 创建下载链接
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `pfs_data_${Date.now()}.csv`
    link.click()
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 监听数据变化
watch(() => props.metricsData, () => {
  nextTick(() => {
    initChart()
  })
}, { deep: true })

watch(chartType, () => {
  // 更新所有分类图表
  metricCategories.value.forEach(category => {
    updateCategoryChart(category)
  })
})

// 监听窗口大小变化
const handleResize = () => {
  Object.values(chartInstances).forEach(instance => {
    instance?.resize()
  })
  compareChartInstance?.resize()
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  Object.values(chartInstances).forEach(instance => {
    instance?.dispose()
  })
  compareChartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.data-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.charts-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.chart-container {
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: var(--spacing-4);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.chart-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.chart {
  width: 100%;
}

.table-section {
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: var(--spacing-4);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.table-actions {
  display: flex;
  gap: var(--spacing-2);
}

.client-filter {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.client-filter-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  white-space: nowrap;
}

.client-table-block {
  margin-bottom: var(--spacing-5);
}

.client-table-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: var(--spacing-2);
}
</style>
