import axios from '@/utils/axios'

export const getHASInspection = () => axios.get('/api/v1/gpu-monitoring/has-inspection')
export const collectHASInspection = () => axios.post('/api/v1/gpu-monitoring/has-inspection/collect')

export const getGrafanaInfo = () => axios.get('/api/v1/gpu-monitoring/grafana')

export const queryBottomCardTime = (data) => axios.post('/api/v1/gpu-monitoring/bottom-card-time/query', data)
export const analyzeBottomCardTime = (data) => axios.post('/api/v1/gpu-monitoring/bottom-card-time/analyze', data)
