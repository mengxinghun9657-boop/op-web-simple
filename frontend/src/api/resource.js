import axios from '@/utils/axios'

export const analyzeResource = (formData) => {
  return axios.post('/api/v1/resource/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const getTaskStatus = (taskId) => {
  return axios.get(`/api/v1/tasks/${taskId}/status`)
}

export const getClusterMetrics = (params) => {
  return axios.post('/api/v1/resource/cluster/metrics', params)
}
