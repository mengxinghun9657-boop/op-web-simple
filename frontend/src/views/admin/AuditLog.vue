<template>
  <div class="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6 h-full flex flex-col">
    <div class="flex justify-between items-center mb-6">
      <h3 class="text-lg font-semibold text-white">系统审计日志</h3>
      <div class="flex gap-3">
        <el-date-picker 
          v-model="dateRange" 
          type="daterange" 
          range-separator="至" 
          start-placeholder="开始日期" 
          end-placeholder="结束日期"
          class="custom-date-picker"
        />
        <el-button type="success" plain icon="Download" @click="exportCSV">导出日志</el-button>
      </div>
    </div>

    <el-table :data="filteredLogs" style="width: 100%" height="100%" v-loading="loading"
      :header-cell-style="{ background: 'rgba(30, 41, 59, 0.5)', color: '#fff' }"
      :cell-style="{ background: 'transparent', color: '#ccc' }"
    >
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column prop="username" label="操作人" width="120" />
      <el-table-column prop="action" label="动作" width="120">
        <template #default="{ row }">
          <span :class="getActionColor(row.action)">{{ row.action }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="resource" label="资源对象" />
      <el-table-column prop="ip_address" label="IP地址" width="140" />
    </el-table>

    <div class="mt-4 flex justify-end">
      <el-pagination 
        background 
        layout="total, prev, pager, next, sizes" 
        :total="totalLogs" 
        :page-size="pageSize"
        :page-sizes="[20, 50, 100, 200]"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from '@/utils/axios'

const dateRange = ref([])
const logs = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)

// 获取审计日志
const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/v1/audit-logs', {
      params: {
        skip: 0,
        limit: 1000 // 获取所有日志用于前端筛选
      }
    })
    
    // 添加调试日志
    console.log('🔍 审计日志响应:', response)
    console.log('🔍 response.success:', response.success)
    console.log('🔍 response.data:', response.data)
    console.log('🔍 response.data?.list:', response.data?.list)
    
    // 修复：正确解析响应格式 {success, data: {list, total, page, page_size}, message}
    if (response.success && response.data && response.data.list) {
      logs.value = response.data.list
    } else {
      logs.value = []
      ElMessage.warning('审计日志数据格式异常')
    }
  } catch (error) {
    ElMessage.error('获取审计日志失败')
    console.error('❌ 获取审计日志错误:', error)
    console.error('❌ error.response:', error.response)
    console.error('❌ error.response?.data:', error.response?.data)
  } finally {
    loading.value = false
  }
}

// 过滤后的日志列表
const filteredLogs = computed(() => {
  let result = logs.value
  
  // TODO: 根据日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    // 实现日期过滤逻辑
  }
  
  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return result.slice(start, end)
})

// 总数
const totalLogs = computed(() => {
  return logs.value.length
})

const getActionColor = (action) => {
  if (action === 'DELETE') return 'text-red-400 font-bold'
  if (action === 'LOGIN') return 'text-green-400'
  if (action === 'CREATE') return 'text-blue-400'
  if (action === 'UPDATE') return 'text-yellow-400'
  return 'text-white'
}

const exportCSV = () => {
  // TODO: 实现CSV导出
  ElMessage.info('导出功能开发中...')
}

// 组件挂载时获取日志
onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
:deep(.custom-date-picker .el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
