/**
 * 仪表盘数据 API
 */
import axios from '@/utils/axios'

/**
 * 获取仪表盘统计数据
 * @returns {Promise} 统计数据
 */
export const getDashboardStats = () => {
  return axios.get('/api/v1/dashboard/stats')
}

/**
 * 获取最近任务列表
 * @returns {Promise} 任务列表
 */
export const getRecentTasks = () => {
  return axios.get('/api/v1/dashboard/recent-tasks')
}

/**
 * 获取系统健康度数据
 * @returns {Promise} 系统健康度数据
 */
export const getSystemHealth = () => {
  return axios.get('/api/v1/dashboard/system-health')
}

/**
 * 获取用户备忘
 * @returns {Promise} 备忘内容
 */
export const getUserNote = () => {
  return axios.get('/api/v1/dashboard/note')
}

/**
 * 保存用户备忘
 * @param {Object} data - 备忘数据
 * @param {string} data.content - 备忘内容
 * @returns {Promise} 保存结果
 */
export const saveUserNote = (data) => {
  return axios.post('/api/v1/dashboard/note', data)
}
