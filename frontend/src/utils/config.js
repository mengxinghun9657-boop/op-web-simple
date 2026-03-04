/**
 * 前端配置文件
 * 集中管理所有URL和环境变量
 */

// 后端API基础URL
// 生产环境使用相对路径（通过Nginx代理），开发环境使用完整URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

// Swagger API文档地址
// 如果是相对路径，则拼接 /docs；如果是完整URL，则拼接完整URL
export const API_DOCS_URL = API_BASE_URL ? `${API_BASE_URL}/docs` : '/docs'

/**
 * 将相对路径转换为完整的后端URL
 * @param {string} path - 相对路径，如 '/reports/xxx.html'
 * @returns {string} 完整URL
 */
export const getFullBackendUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  // 生产环境使用相对路径
  if (!API_BASE_URL) {
    return path.startsWith('/') ? path : '/' + path
  }
  // 开发环境拼接完整URL
  return `${API_BASE_URL}${path.startsWith('/') ? path : '/' + path}`
}

/**
 * 获取环境信息
 */
export const isDevelopment = import.meta.env.MODE === 'development'
export const isProduction = import.meta.env.MODE === 'production'
