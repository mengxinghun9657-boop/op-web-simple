import axios from '@/utils/axios'

export const analyzeBCC = (data) => axios.post('/api/v1/monitoring/bcc/analyze', data)
export const analyzeBOS = (data) => axios.post('/api/v1/monitoring/bos/analyze', data)

export const getTaskStatus = (taskId) => axios.get(`/api/v1/tasks/${taskId}/status`)
export const getBCCResult = (taskId) => axios.get(`/api/v1/monitoring/bcc/result/${taskId}`)
export const getBOSResult = (taskId) => axios.get(`/api/v1/monitoring/bos/result/${taskId}`)
