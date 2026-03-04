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
