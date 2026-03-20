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
 * @param {Array<number>} alertIds - 可选，指定告警ID列表（为空则补发所有未通知的告警）
 * @returns {Promise}
 */
export const batchResendNotifications = (alertIds = null) => {
  if (alertIds && alertIds.length > 0) {
    // FastAPI 的 list[int] Query 参数需要重复键名: ?alert_ids=1&alert_ids=2
    const searchParams = new URLSearchParams()
    alertIds.forEach(id => searchParams.append('alert_ids', id))
    return axios.post(`/api/v1/alerts/batch-resend-notification?${searchParams.toString()}`)
  }
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

/**
 * 为告警创建 iCafe 卡片
 * @param {number} alertId - 告警ID
 * @param {Object} cardData - 卡片数据
 * @returns {Promise}
 */
export const createICafeCard = (alertId, cardData) => {
  return axios.post(`/api/v1/alerts/${alertId}/create-icafe-card`, cardData)
}
/**
 * 检测需要修正cluster_id的告警记录
 * @returns {Promise}
 */
export const detectIncorrectAlerts = () => {
  return axios.get('/api/v1/alerts/detect-incorrect')
}

/**
 * 批量修正告警记录的cluster_id
 * @param {Array<number>} alertIds - 可选，告警ID列表（为空则修正所有需要修正的记录）
 * @returns {Promise}
 */
export const correctClusterIds = (alertIds = null) => {
  const data = alertIds ? { alert_ids: alertIds } : {}
  return axios.post('/api/v1/alerts/correct-cluster-ids', data)
}

/**
 * 修正单个告警记录的cluster_id
 * @param {number} alertId - 告警ID
 * @returns {Promise}
 */
export const correctSingleAlertClusterId = (alertId) => {
  return axios.post(`/api/v1/alerts/${alertId}/correct-cluster-id`)
}

/**
 * 更新告警字段
 * @param {number} alertId - 告警ID
 * @param {Object} data - 更新的字段数据
 * @returns {Promise}
 */
export const updateAlertFields = (alertId, data) => {
  return axios.put(`/api/v1/alerts/${alertId}`, data)
}

/**
 * 测试宿主机数据库连接
 * @returns {Promise}
 */
export const testHostConnection = () => {
  return axios.get('/api/v1/alerts/test-host-connection')
}

/**
 * 手动创建告警
 * @param {Object} data - 告警数据
 * @returns {Promise}
 */
export const createAlert = (data) => {
  return axios.post('/api/v1/alerts', data)
}

/**
 * 获取组件类型枚举值
 * @returns {Promise}
 */
export const getComponentEnums = () => {
  return axios.get('/api/v1/alerts/components/enum')
}

/**
 * 获取告警类型枚举值
 * @returns {Promise}
 */
export const getAlertTypeEnums = () => {
  return axios.get('/api/v1/alerts/alert-types/enum')
}