/**
 * Webhook管理 API
 */
import axios from '@/utils/axios'

/**
 * 获取Webhook列表
 * @returns {Promise}
 */
export const getWebhooks = () => {
  return axios.get('/api/v1/webhooks')
}

/**
 * 创建Webhook
 * @param {Object} data - Webhook数据
 * @param {string} data.name - 配置名称
 * @param {string} data.type - Webhook类型(feishu/ruliu)
 * @param {string} data.url - Webhook URL
 * @param {string} data.access_token - 访问令牌(可选)
 * @param {string} data.secret - 签名密钥(可选)
 * @param {boolean} data.enabled - 是否启用
 * @param {string} data.severity_filter - 严重程度过滤(可选)
 * @param {string} data.component_filter - 组件过滤(可选)
 * @returns {Promise}
 */
export const createWebhook = (data) => {
  return axios.post('/api/v1/webhooks', data)
}

/**
 * 更新Webhook
 * @param {number} webhookId - Webhook ID
 * @param {Object} data - 更新数据
 * @returns {Promise}
 */
export const updateWebhook = (webhookId, data) => {
  return axios.put(`/api/v1/webhooks/${webhookId}`, data)
}

/**
 * 删除Webhook
 * @param {number} webhookId - Webhook ID
 * @returns {Promise}
 */
export const deleteWebhook = (webhookId) => {
  return axios.delete(`/api/v1/webhooks/${webhookId}`)
}

/**
 * 测试Webhook
 * @param {number} webhookId - Webhook ID
 * @returns {Promise}
 */
export const testWebhook = (webhookId) => {
  return axios.post(`/api/v1/webhooks/${webhookId}/test`)
}
