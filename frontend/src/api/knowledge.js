/**
 * 知识库管理 API
 */
import axios from '@/utils/axios'

// ==================== 认证 ====================

/**
 * 验证管理员密码
 * @param {Object} data - 密码数据
 * @param {string} data.password - 管理员密码
 * @returns {Promise} 验证结果和token
 */
export const verifyPassword = (data) => {
  return axios.post('/api/v1/knowledge/auth/verify', data)
}

/**
 * 退出登录
 * @param {string} token - 会话token
 * @returns {Promise} 退出结果
 */
export const logout = (token) => {
  return axios.post('/api/v1/knowledge/auth/logout', {}, {
    headers: { 'X-Knowledge-Token': token }
  })
}

// ==================== 知识条目管理 ====================

/**
 * 获取知识条目列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.category - 分类过滤
 * @param {string} params.source - 来源过滤 (manual/auto)
 * @param {string} token - 会话token
 * @returns {Promise} 知识条目列表
 */
export const getKnowledgeEntries = (params, token) => {
  return axios.get('/api/v1/knowledge/entries', {
    params,
    headers: { 'X-Knowledge-Token': token }
  })
}

/**
 * 创建知识条目
 * @param {Object} data - 知识条目数据
 * @param {string} data.title - 标题
 * @param {string} data.content - 内容
 * @param {string} data.category - 分类
 * @param {Array} data.tags - 标签
 * @param {string} data.priority - 优先级 (low/medium/high)
 * @param {string} token - 会话token
 * @returns {Promise} 创建结果
 */
export const createKnowledgeEntry = (data, token) => {
  return axios.post('/api/v1/knowledge/entries', data, {
    headers: { 'X-Knowledge-Token': token }
  })
}

/**
 * 更新知识条目
 * @param {number} entryId - 条目ID
 * @param {Object} data - 更新数据
 * @param {string} token - 会话token
 * @returns {Promise} 更新结果
 */
export const updateKnowledgeEntry = (entryId, data, token) => {
  return axios.put(`/api/v1/knowledge/entries/${entryId}`, data, {
    headers: { 'X-Knowledge-Token': token }
  })
}

/**
 * 删除知识条目
 * @param {number} entryId - 条目ID
 * @param {string} token - 会话token
 * @returns {Promise} 删除结果
 */
export const deleteKnowledgeEntry = (entryId, token) => {
  return axios.delete(`/api/v1/knowledge/entries/${entryId}`, {
    headers: { 'X-Knowledge-Token': token }
  })
}

/**
 * 获取分类列表
 * @param {string} token - 会话token
 * @returns {Promise} 分类列表
 */
export const getCategories = (token) => {
  return axios.get('/api/v1/knowledge/categories', {
    headers: { 'X-Knowledge-Token': token }
  })
}
