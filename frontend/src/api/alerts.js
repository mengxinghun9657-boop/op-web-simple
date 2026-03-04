/**
 * 告警管理 API
 */
import axios from '@/utils/axios'

/**
 * 获取告警列表
 * @param {Object} params - 查询参数
 * @returns {Promise}
 */
export const getAlerts = (params) => {
  return axios.get('/api/v1/alerts', { params })
}

/**
 * 获取告警详情
 * @param {number} alertId - 告警ID
 * @returns {Promise}
 */
export const getAlertDetail = (alertId) => {
  return axios.get(`/api/v1/alerts/${alertId}`)
}

/**
 * 触发诊断
 * @param {number} alertId - 告警ID
 * @param {boolean} force - 是否强制重新诊断
 * @returns {Promise}
 */
export const diagnoseAlert = (alertId, force = false) => {
  return axios.post(`/api/v1/alerts/${alertId}/diagnose`, null, {
    params: { force }
  })
}

/**
 * 获取筛选选项
 * @returns {Promise}
 */
export const getFilterOptions = () => {
  return axios.get('/api/v1/alerts/filter-options')
}

/**
 * 重新发送单个告警通知
 * @param {number} alertId - 告警ID
 * @returns {Promise}
 */
export const resendNotification = (alertId) => {
  return axios.post(`/api/v1/alerts/${alertId}/resend-notification`)
}

/**
 * 批量重新发送未通知的告警
 * @returns {Promise}
 */
export const batchResendNotifications = () => {
  return axios.post('/api/v1/alerts/batch-resend-notification')
}

/**
 * 更新告警状态
 * @param {number} alertId - 告警ID
 * @param {Object} data - 状态更新数据 { status, resolution_notes }
 * @returns {Promise}
 */
export const updateAlertStatus = (alertId, data) => {
  return axios.put(`/api/v1/alerts/${alertId}/status`, data)
}
