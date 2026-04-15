import axios from '@/utils/axios'

export const getCCEMonitoringConfig = () => axios.get('/api/v1/cce-monitoring/config')
export const getCCEClusters = () => axios.get('/api/v1/cce-monitoring/clusters')
export const queryCCECluster = (cluster_id) => axios.get('/api/v1/cce-monitoring/query', { params: { cluster_id } })
export const queryCCEClusterCharts = (cluster_id, period_hours, step) =>
  axios.get('/api/v1/cce-monitoring/query-charts', { params: { cluster_id, period_hours, step } })
export const queryCCEAllClusters = () => axios.get('/api/v1/cce-monitoring/query-all')
export const queryPendingPVCs = (cluster_id) =>
  axios.get('/api/v1/cce-monitoring/pending-pvcs', { params: cluster_id ? { cluster_id } : {} })
