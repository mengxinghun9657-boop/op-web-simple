import axios from '@/utils/axios'

export const analyzeAPIServerAlerts = () => axios.post('/api/v1/apiserver-alerts/analyze')
export const getAPIServerAlerts = (params) => axios.get('/api/v1/apiserver-alerts', { params })
export const getAPIServerAlertStats = () => axios.get('/api/v1/apiserver-alerts/stats')
export const getAPIServerMonitoringOverview = (params) => axios.get('/api/v1/apiserver-alerts/monitoring/overview', { params })
export const getAPIServerAlertDetail = (id) => axios.get(`/api/v1/apiserver-alerts/${id}`)
export const updateAPIServerAlertStatus = (id, data) => axios.put(`/api/v1/apiserver-alerts/${id}/status`, data)
export const getAPIServerConfig = () => axios.get('/api/v1/apiserver-alerts/config')
export const saveAPIServerConfig = (data) => axios.post('/api/v1/apiserver-alerts/config', data)
export const createAPIServerIcafeCard = (id, data) => axios.post(`/api/v1/apiserver-alerts/${id}/create-icafe-card`, data)
export const batchUpdateAPIServerAlertStatus = (data) => axios.put('/api/v1/apiserver-alerts/batch/status', data)
