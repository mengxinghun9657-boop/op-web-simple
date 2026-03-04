/**
 * 路由规则管理 API
 */
import axios from '@/utils/axios'

// ==================== 路由规则 API ====================

/**
 * 获取路由规则列表
 */
export const getRoutingRules = (params) => {
  return axios.get('/api/v1/routing/rules', { params })
}

/**
 * 创建路由规则
 */
export const createRoutingRule = (data) => {
  return axios.post('/api/v1/routing/rules', data)
}

/**
 * 更新路由规则
 */
export const updateRoutingRule = (ruleId, data) => {
  return axios.put(`/api/v1/routing/rules/${ruleId}`, data)
}

/**
 * 删除路由规则
 */
export const deleteRoutingRule = (ruleId) => {
  return axios.delete(`/api/v1/routing/rules/${ruleId}`)
}

/**
 * 测试路由规则
 */
export const testRoutingRules = (data) => {
  return axios.post('/api/v1/routing/test', data)
}

/**
 * 导出路由规则
 */
export const exportRoutingRules = () => {
  return axios.get('/api/v1/routing/rules/export', {
    responseType: 'blob'
  })
}

/**
 * 导入路由规则
 */
export const importRoutingRules = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return axios.post('/api/v1/routing/rules/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ==================== 规则建议 API ====================

/**
 * 获取待审核的规则建议列表
 */
export const getPendingSuggestions = (params) => {
  return axios.get('/api/v1/routing/suggestions/pending', { params })
}

/**
 * 获取规则建议详情
 */
export const getSuggestionDetail = (suggestionId) => {
  return axios.get(`/api/v1/routing/suggestions/${suggestionId}`)
}

/**
 * 更新规则建议
 */
export const updateSuggestion = (suggestionId, data) => {
  return axios.put(`/api/v1/routing/suggestions/${suggestionId}`, data)
}

/**
 * 测试规则建议
 */
export const testSuggestion = (suggestionId, data) => {
  return axios.post(`/api/v1/routing/suggestions/${suggestionId}/test`, data)
}

/**
 * 采纳规则建议
 */
export const approveSuggestion = (suggestionId) => {
  return axios.post(`/api/v1/routing/suggestions/${suggestionId}/approve`)
}

/**
 * 拒绝规则建议
 */
export const rejectSuggestion = (suggestionId, data) => {
  return axios.post(`/api/v1/routing/suggestions/${suggestionId}/reject`, data)
}

/**
 * 批量采纳规则建议
 */
export const batchApproveSuggestions = (data) => {
  return axios.post('/api/v1/routing/suggestions/batch-approve', data)
}

/**
 * 生成规则建议
 */
export const generateRuleSuggestions = (params) => {
  return axios.post('/api/v1/routing/suggestions/generate', null, { params })
}

/**
 * 获取审核历史
 */
export const getSuggestionHistory = (params) => {
  return axios.get('/api/v1/routing/suggestions/history', { params })
}

// ==================== 路由统计 API ====================

/**
 * 获取路由统计数据
 */
export const getRoutingStatistics = (params) => {
  return axios.get('/api/v1/routing/statistics', { params })
}

/**
 * 获取低置信度路由记录
 */
export const getLowConfidenceRecords = (params) => {
  return axios.get('/api/v1/routing/low-confidence', { params })
}

// ==================== 路由反馈 API ====================

/**
 * 提交路由反馈
 */
export const submitRoutingFeedback = (data) => {
  return axios.post('/api/v1/routing/feedback', data)
}

/**
 * 获取反馈列表
 */
export const getRoutingFeedbacks = (params) => {
  return axios.get('/api/v1/routing/feedback', { params })
}
