/**
 * 告警统计分析 API
 */
import axios from '@/utils/axios'

/**
 * 获取告警趋势统计
 * @param {Object} params - 查询参数
 * @param {string} params.start_time - 开始时间
 * @param {string} params.end_time - 结束时间
 * @param {string} params.group_by - 分组方式(day/hour/week/month)
 * @param {string} params.cluster_id - 集群ID(可选)
 * @param {string} params.component - 组件类型(可选)
 * @returns {Promise}
 */
export const getAlertTrend = (params) => {
  return axios.get('/api/v1/alerts/statistics/trend', { params })
}

/**
 * 获取告警类型分布
 * @param {Object} params - 查询参数
 * @param {string} params.start_time - 开始时间
 * @param {string} params.end_time - 结束时间
 * @param {string} params.dimension - 维度(alert_type/component/severity/cluster)
 * @returns {Promise}
 */
export const getAlertDistribution = (params) => {
  return axios.get('/api/v1/alerts/statistics/distribution', { params })
}

/**
 * 获取集群/节点告警排行
 * @param {Object} params - 查询参数
 * @param {string} params.start_time - 开始时间
 * @param {string} params.end_time - 结束时间
 * @param {number} params.limit - 返回数量
 * @param {string} params.order_by - 排序字段(total/critical)
 * @returns {Promise}
 */
export const getTopNodes = (params) => {
  return axios.get('/api/v1/alerts/statistics/top-nodes', { params })
}
