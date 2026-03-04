import axios from '@/utils/axios'

// 统一的任务管理API
export const getTaskStatus = (taskId) => {
  return axios.get(`/api/v1/tasks/${taskId}/status`)
}

export const getAllTasks = (params = {}) => {
  return axios.get('/api/v1/tasks', { params })
}

export const downloadReport = (moduleType, taskId, reportType) => {
  return axios.get(`/api/v1/reports/${moduleType}/${taskId}/download/${reportType}`, {
    responseType: 'blob'
  })
}

export const getReportInfo = (moduleType, taskId) => {
  return axios.get(`/api/v1/reports/${moduleType}/${taskId}/info`)
}
