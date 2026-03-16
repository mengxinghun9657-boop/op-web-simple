/**
 * AI 功能 API
 */
import axios from '@/utils/axios'

// ==================== AI 对话 ====================

/**
 * AI 对话
 * @param {Object} data - 对话数据
 * @param {Array} data.messages - 消息历史
 * @param {Object} data.context_data - 上下文数据
 * @param {number} data.temperature - 温度参数 (0-1)
 * @param {number} data.max_tokens - 最大token数
 * @returns {Promise} AI 回复
 */
export const chatWithAI = (data) => {
  return axios.post('/api/v1/ai/chat', data)
}

/**
 * 获取对话历史
 * @param {number} limit - 返回数量
 * @returns {Promise} 对话历史
 */
export const getChatHistory = (limit = 50) => {
  return axios.get('/api/v1/ai/history', { params: { limit } })
}

/**
 * 清空对话历史
 * @returns {Promise} 清空结果
 */
export const clearChatHistory = () => {
  return axios.delete('/api/v1/ai/history')
}

/**
 * 查询数据库数据
 * @param {Object} data - 查询数据
 * @param {string} data.table - 表名
 * @param {Object} data.filters - 过滤条件
 * @param {number} data.limit - 返回数量
 * @param {Array} data.columns - 指定列
 * @returns {Promise} 查询结果
 */
export const queryDatabase = (data) => {
  return axios.post('/api/v1/ai/query-data', data)
}

/**
 * 获取所有可查询的表
 * @returns {Promise} 表列表
 */
export const getAvailableTables = () => {
  return axios.get('/api/v1/ai/tables')
}
