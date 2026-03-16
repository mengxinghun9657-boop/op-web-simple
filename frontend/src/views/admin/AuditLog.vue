<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Document /></el-icon>
          </div>
          系统审计日志
        </div>
        <div class="page-subtitle">查看和导出系统操作日志</div>
      </div>
      <div class="page-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
        <el-button type="success" plain icon="Download" @click="exportCSV">导出日志</el-button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="content-card">
      <div class="content-card-body">
        <el-table :data="filteredLogs" v-loading="loading" class="google-table">
          <el-table-column prop="created_at" label="时间" width="180" />
          <el-table-column prop="username" label="操作人" width="120" />
          <el-table-column prop="action" label="动作" width="120">
            <template #default="{ row }">
              <el-tag :type="getActionTagType(row.action)">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="resource" label="资源对象" />
          <el-table-column prop="ip_address" label="IP地址" width="140" />
        </el-table>

        <div class="table-footer">
          <el-pagination
            background
            layout="total, prev, pager, next, sizes"
            :total="totalLogs"
            :page-size="pageSize"
            :page-sizes="[20, 50, 100, 200]"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            class="google-pagination"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Download, Document } from '@element-plus/icons-vue'
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
        limit: 1000
      }
    })

    if (response.success && response.data && response.data.list) {
      logs.value = response.data.list
    } else {
      logs.value = []
      ElMessage.warning('审计日志数据格式异常')
    }
  } catch (error) {
    ElMessage.error('获取审计日志失败')
  } finally {
    loading.value = false
  }
}

// 过滤后的日志列表
const filteredLogs = computed(() => {
  let result = logs.value

  if (dateRange.value && dateRange.value.length === 2) {
    // 实现日期过滤逻辑
  }

  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return result.slice(start, end)
})

const totalLogs = computed(() => logs.value.length)

const getActionTagType = (action) => {
  if (action === 'DELETE') return 'danger'
  if (action === 'LOGIN') return 'success'
  if (action === 'CREATE') return 'primary'
  if (action === 'UPDATE') return 'warning'
  return 'info'
}

const exportCSV = () => {
  ElMessage.info('导出功能开发中...')
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
</style>
