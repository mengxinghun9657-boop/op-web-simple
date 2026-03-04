import axios from '@/utils/axios'

// Excel 文件上传分析
export const analyzeData = (formData) => {
  return axios.post('/api/v1/operational/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// API 查询分析
export const analyzeApiData = (params) => {
  return axios.post('/api/v1/operational/analyze-api', params)
}

// 获取分析结果
export const getResult = (taskId) => {
  return axios.get(`/api/v1/operational/result/${taskId}`)
}

// 获取默认配置
export const getOperationalDefaults = () => {
  return axios.get('/api/v1/operational/config/defaults')
}

// 获取报告列表
export const getReportList = () => {
  return axios.get('/api/v1/operational/reports')
}

// 删除报告
export const deleteReport = (filename) => {
  return axios.delete(`/api/v1/operational/reports/${filename}`)
}

// 批量清理报告
export const cleanReports = (strategy) => {
  return axios.post('/api/v1/operational/reports/clean', { strategy })
}

// 获取报告统计
export const getReportStats = () => {
  return axios.get('/api/v1/operational/reports/stats')
}


// 获取 IQL 模板列表
export const getIQLTemplates = () => {
  return axios.get('/api/v1/operational/iql-templates')
}
