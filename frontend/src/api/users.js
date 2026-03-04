/**
 * 用户管理 API
 */
import axios from '@/utils/axios'

/**
 * 用户登录
 * @param {Object} data - 登录信息
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @returns {Promise} 登录响应
 */
export const login = (data) => {
  return axios.post('/api/v1/auth/login', data)
}

/**
 * 刷新 Token
 * @param {string} refreshToken - 刷新令牌
 * @returns {Promise} 新的 Token
 */
export const refreshToken = (refreshToken) => {
  return axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
}

/**
 * 获取当前用户信息
 * @returns {Promise} 用户信息
 */
export const getCurrentUser = () => {
  return axios.get('/api/v1/users/me')
}

/**
 * 获取用户列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码，默认 1
 * @param {number} params.page_size - 每页数量，默认 20
 * @returns {Promise} 用户列表
 */
export const getUsers = (params = { page: 1, page_size: 20 }) => {
  return axios.get('/api/v1/users', { params })
}

/**
 * 创建用户
 * @param {Object} data - 用户信息
 * @returns {Promise} 创建结果
 */
export const createUser = (data) => {
  return axios.post('/api/v1/users', data)
}

/**
 * 更新用户信息
 * @param {number} userId - 用户ID
 * @param {Object} data - 更新数据
 * @returns {Promise} 更新结果
 */
export const updateUser = (userId, data) => {
  return axios.put(`/api/v1/users/${userId}`, data)
}

/**
 * 删除用户
 * @param {number} userId - 用户ID
 * @returns {Promise} 删除结果
 */
export const deleteUser = (userId) => {
  return axios.delete(`/api/v1/users/${userId}`)
}

/**
 * 重置用户密码
 * @param {number} userId - 用户ID
 * @param {Object} data - 密码数据
 * @param {string} data.new_password - 新密码
 * @returns {Promise} 重置结果
 */
export const resetPassword = (userId, data) => {
  return axios.post(`/api/v1/users/${userId}/reset-password`, data)
}

/**
 * 获取审计日志
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码，默认 1
 * @param {number} params.page_size - 每页数量，默认 20
 * @returns {Promise} 审计日志列表
 */
export const getAuditLogs = (params = { page: 1, page_size: 20 }) => {
  return axios.get('/api/v1/audit-logs', { params })
}
