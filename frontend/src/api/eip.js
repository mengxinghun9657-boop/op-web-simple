import axios from '@/utils/axios'

export const analyzeEIP = (data) => axios.post('/api/v1/eip/analyze', data)
export const getTaskStatus = (taskId) => axios.get(`/api/v1/tasks/${taskId}/status`)
