<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          告警统计分析
        </div>
        <div class="page-subtitle">可视化展示告警趋势和分布情况</div>
      </div>
    </div>

    <!-- 时间范围选择 -->
    <div class="content-card">
      <div class="content-card-body">
        <el-form inline>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 400px"
            @change="handleDateRangeChange"
          />
        </el-form-item>

        <el-form-item label="快捷选择">
          <el-button-group>
            <el-button @click="setQuickRange('today')">今天</el-button>
            <el-button @click="setQuickRange('week')">最近7天</el-button>
            <el-button @click="setQuickRange('month')">最近30天</el-button>
          </el-button-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchAllData">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </el-form-item>
      </el-form>
      </div>
    </div>

    <!-- 统计图表 -->
    <el-row :gutter="20">
      <!-- 告警趋势图 -->
      <el-col :span="24">
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">告警趋势</div>
            <div class="content-card-extra">
              <el-radio-group v-model="trendGroupBy" size="small" @change="fetchTrendData">
                <el-radio-button label="hour">按小时</el-radio-button>
                <el-radio-button label="day">按天</el-radio-button>
                <el-radio-button label="week">按周</el-radio-button>
                <el-radio-button label="month">按月</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="content-card-body">
            <div ref="trendChartRef" class="chart" style="height: 400px"></div>
          </div>
        </div>
      </el-col>

      <!-- 告警类型分布 -->
      <el-col :span="24">
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">告警类型分布</div>
            <div class="content-card-extra">
              <el-select v-model="distributionDimension" size="small" @change="fetchDistributionData">
                <el-option label="按告警类型" value="alert_type" />
                <el-option label="按组件" value="component" />
                <el-option label="按严重程度" value="severity" />
                <el-option label="按集群" value="cluster" />
              </el-select>
            </div>
          </div>
          <div class="content-card-body">
            <div ref="distributionChartRef" class="chart" style="height: 500px"></div>
          </div>
        </div>
      </el-col>

      <!-- 节点告警排行 -->
      <el-col :span="24">
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">节点告警排行 TOP 10</div>
            <div class="content-card-extra">
              <el-radio-group v-model="topNodesOrderBy" size="small" @change="fetchTopNodesData">
                <el-radio-button label="total">总数</el-radio-button>
                <el-radio-button label="critical">严重</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="content-card-body">
            <div ref="topNodesChartRef" class="chart" style="height: 450px"></div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Refresh, DataAnalysis } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getAlertTrend, getAlertDistribution, getTopNodes } from '@/api/statistics'

// 时间范围
const dateRange = ref([])
const timeRange = ref({
  start_time: '',
  end_time: ''
})

// 图表配置
const trendGroupBy = ref('day')
const distributionDimension = ref('alert_type')
const topNodesOrderBy = ref('total')

// 图表实例
const trendChartRef = ref(null)
const distributionChartRef = ref(null)
const topNodesChartRef = ref(null)
let trendChart = null
let distributionChart = null
let topNodesChart = null

// 设置快捷时间范围
const setQuickRange = (type) => {
  const end = new Date()
  const start = new Date()
  
  switch (type) {
    case 'today':
      start.setHours(0, 0, 0, 0)
      break
    case 'week':
      start.setDate(start.getDate() - 7)
      break
    case 'month':
      start.setDate(start.getDate() - 30)
      break
  }
  
  dateRange.value = [start, end]
  handleDateRangeChange(dateRange.value)
}

// 处理时间范围变化
const handleDateRangeChange = (value) => {
  if (value && value.length === 2) {
    timeRange.value.start_time = value[0].toISOString()
    timeRange.value.end_time = value[1].toISOString()
    fetchAllData()
  }
}

// 获取趋势数据
const fetchTrendData = async () => {
  if (!timeRange.value.start_time) return
  
  try {
    const response = await getAlertTrend({
      ...timeRange.value,
      group_by: trendGroupBy.value
    })
    
    if (response.success) {
      renderTrendChart(response.data)
    }
  } catch (error) {
    console.error('获取趋势数据失败:', error)
  }
}

// 获取分布数据
const fetchDistributionData = async () => {
  if (!timeRange.value.start_time) return
  
  try {
    const response = await getAlertDistribution({
      ...timeRange.value,
      dimension: distributionDimension.value
    })
    
    if (response.success) {
      renderDistributionChart(response.data)
    }
  } catch (error) {
    console.error('获取分布数据失败:', error)
  }
}

// 获取排行数据
const fetchTopNodesData = async () => {
  if (!timeRange.value.start_time) return
  
  try {
    const response = await getTopNodes({
      ...timeRange.value,
      limit: 10,
      order_by: topNodesOrderBy.value
    })
    
    if (response.success) {
      renderTopNodesChart(response.data)
    }
  } catch (error) {
    console.error('获取排行数据失败:', error)
  }
}

// 获取所有数据
const fetchAllData = () => {
  fetchTrendData()
  fetchDistributionData()
  fetchTopNodesData()
}

// 渲染趋势图
const renderTrendChart = (data) => {
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  
  const dates = data.trend.map(item => item.date)
  const critical = data.trend.map(item => item.critical)
  const warning = data.trend.map(item => item.warning)
  const info = data.trend.map(item => item.info)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['Critical', 'Warning', 'Info']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: 'Critical',
        type: 'line',
        smooth: true,
        data: critical,
        itemStyle: { color: '#F56C6C' },
        areaStyle: { opacity: 0.2 }
      },
      {
        name: 'Warning',
        type: 'line',
        smooth: true,
        data: warning,
        itemStyle: { color: '#E6A23C' },
        areaStyle: { opacity: 0.2 }
      },
      {
        name: 'Info',
        type: 'line',
        smooth: true,
        data: info,
        itemStyle: { color: '#409EFF' },
        areaStyle: { opacity: 0.2 }
      }
    ]
  }
  
  trendChart.setOption(option)
}

// 渲染分布图
const renderDistributionChart = (data) => {
  if (!distributionChart) {
    distributionChart = echarts.init(distributionChartRef.value)
  }
  
  const chartData = data.distribution.map(item => ({
    name: item.name,
    value: item.count
  }))
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'middle',
      type: 'scroll',
      itemGap: 15,
      itemWidth: 14,
      itemHeight: 14,
      textStyle: {
        fontSize: 13
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 12,
          lineHeight: 18,
          distanceToLabelLine: 5
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: true,
          length: 15,
          length2: 10,
          smooth: true
        },
        data: chartData
      }
    ]
  }
  
  distributionChart.setOption(option)
}

// 渲染排行图
const renderTopNodesChart = (data) => {
  if (!topNodesChart) {
    topNodesChart = echarts.init(topNodesChartRef.value)
  }
  
  const nodes = data.top_nodes.map(item => item.hostname || item.ip || item.cluster_id)
  const total = data.top_nodes.map(item => item.total_alerts)
  const critical = data.top_nodes.map(item => item.critical_count)
  const warning = data.top_nodes.map(item => item.warning_count)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['Critical', 'Warning', '其他']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value'
    },
    yAxis: {
      type: 'category',
      data: nodes
    },
    series: [
      {
        name: 'Critical',
        type: 'bar',
        stack: 'total',
        data: critical,
        itemStyle: { color: '#F56C6C' }
      },
      {
        name: 'Warning',
        type: 'bar',
        stack: 'total',
        data: warning,
        itemStyle: { color: '#E6A23C' }
      },
      {
        name: '其他',
        type: 'bar',
        stack: 'total',
        data: total.map((t, i) => t - critical[i] - warning[i]),
        itemStyle: { color: '#409EFF' }
      }
    ]
  }
  
  topNodesChart.setOption(option)
}

// 窗口大小变化时重新渲染
const handleResize = () => {
  trendChart?.resize()
  distributionChart?.resize()
  topNodesChart?.resize()
}

onMounted(() => {
  // 默认显示最近7天
  setQuickRange('week')
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  distributionChart?.dispose()
  topNodesChart?.dispose()
})
</script>

<style scoped>
.chart {
  width: 100%;
}
</style>
