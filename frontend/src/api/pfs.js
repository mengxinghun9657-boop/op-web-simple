import axios from '@/utils/axios'

/**
 * PFS 监控 API
 * 提供 PFS 指标查询、对比分析、数据导出等功能
 */

// 获取指标列表
export const getMetrics = (level = null) => {
  return axios.get('/api/v1/pfs/metrics', {
    params: { level }
  })
}

// 查询指标数据
export const queryMetrics = (request) => {
  return axios.post('/api/v1/pfs/query', request)
}

// 对比查询
export const compareMetrics = (request) => {
  return axios.post('/api/v1/pfs/compare', request)
}

// 导出数据（异步任务）
export const exportData = (request) => {
  return axios.post('/api/v1/pfs/export', request)
}

// 查询任务状态
export const getTaskStatus = (taskId) => {
  return axios.get(`/api/v1/pfs/task/${taskId}`)
}

// 下载导出文件
export const downloadFile = (filename) => {
  return axios.get(`/api/v1/pfs/download/${filename}`)
}

// 获取客户端列表
export const getClients = (region = 'cd', instanceId = 'pfs-mTYGr6') => {
  return axios.get('/api/v1/pfs/clients', {
    params: { region, instance_id: instanceId }
  })
}

// 测试 Prometheus 连接
export const testConnection = () => {
  return axios.post('/api/v1/pfs/test-connection')
}
