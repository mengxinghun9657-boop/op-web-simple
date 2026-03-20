import axios from '@/utils/axios'

// 导入数据
export const importData = (formData, mode = 'update') => {
  return axios.post(`/api/v1/cmdb/import?mode=${mode}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 获取统计概览
export const getStats = () => axios.get('/api/v1/cmdb/stats')

// 获取服务器列表
export const getServers = (params) => axios.get('/api/v1/cmdb/servers', { params })

// 获取服务器详情
export const getServerDetail = (hostname) => axios.get(`/api/v1/cmdb/servers/${encodeURIComponent(hostname)}`)

// 获取实例列表
export const getInstances = (params) => axios.get('/api/v1/cmdb/instances', { params })

// 获取筛选选项
export const getFilters = () => axios.get('/api/v1/cmdb/filters')

// ========== API同步相关 ==========

// 从API同步数据
export const syncFromAPI = (params) => axios.post('/api/v1/cmdb/sync', null, { params })

// 获取同步日志
export const getSyncLogs = (params) => axios.get('/api/v1/cmdb/sync/logs', { params })

// ========== Cookie管理 ==========

// 获取Cookie配置
export const getCookieConfig = () => axios.get('/api/v1/cmdb/config/cookie')

// 更新Cookie配置
export const updateCookieConfig = (cookie) => axios.post('/api/v1/cmdb/config/cookie', { cookie })

// 测试Cookie有效性
export const testCookie = (cookie) => axios.post('/api/v1/cmdb/config/cookie/test', { cookie })

// ========== 定时同步配置 ==========

// 获取定时同步配置
export const getSyncSchedule = () => axios.get('/api/v1/cmdb/sync/schedule')

// 更新定时同步配置
export const updateSyncSchedule = (config) => axios.post('/api/v1/cmdb/sync/schedule', null, { params: config })

// ========== 增强搜索 ==========

// 关联性搜索
export const advancedSearch = (params) => axios.get('/api/v1/cmdb/search', { params })

// ========== BCE 数据同步 ==========

// 获取 BCE 同步配置
export const getBCEConfig = () => axios.get('/api/v1/cmdb/bce/config')

// 更新 BCE 同步配置（cookie、region、cluster_ids）
export const updateBCEConfig = (config) => axios.post('/api/v1/cmdb/bce/config', config)

// 一键同步 BCE 数据（target: all / bcc / cce）
export const syncBCE = (target = 'all') => axios.post('/api/v1/cmdb/bce/sync', null, { params: { target } })

// 获取 BCE 数据统计（本地库记录数、最新采集日期）
export const getBCEStats = () => axios.get('/api/v1/cmdb/bce/stats')

// 获取服务器 BCE 关联信息（BCC实例 + CCE节点，以 IP 关联）
export const getServerBceContext = (hostname) => axios.get(`/api/v1/cmdb/servers/${encodeURIComponent(hostname)}/bce-context`)

// ========== BCE 测试连接 ==========

// 测试 BCE 连接
export const testBCEConnection = (config) => axios.post('/api/v1/cmdb/bce/test-connection', config)

// ========== BCE 自动同步配置 ==========

// 获取 BCE 自动同步配置
export const getBCESyncConfig = () => axios.get('/api/v1/cmdb/bce/sync-config')

// 更新 BCE 自动同步配置
export const updateBCESyncConfig = (config) => axios.post('/api/v1/cmdb/bce/sync-config', config)

