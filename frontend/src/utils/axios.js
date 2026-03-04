import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 防止无限刷新循环的标志
let isRefreshing = false
export let requestsQueue = []

// 创建原始axios实例（用于刷新Token，避免循环依赖）
export const axiosRaw = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 创建axios实例
const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  timeout: 300000, // 增加到300秒(5分钟)，支持大量Bucket分析
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  response => {
    const data = response.data
    
    // 检查统一响应格式
    if (data && typeof data === 'object' && 'success' in data) {
      // 如果 success 为 false，显示错误信息
      if (data.success === false) {
        const errorMsg = data.error || data.message || '操作失败'
        ElMessage.error(errorMsg)
        return Promise.reject(new Error(errorMsg))
      }
      // 返回完整的响应对象 {success, data, message}
      return data
    }
    
    // 兼容旧格式：直接返回数据
    return data
  },
  async error => {
    const originalRequest = error.config
    
    // 网络超时重试逻辑
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      // 初始化重试计数器
      if (!originalRequest._retryCount) {
        originalRequest._retryCount = 0
      }
      
      // 最多重试2次
      if (originalRequest._retryCount < 2) {
        originalRequest._retryCount += 1
        console.log(`请求超时，正在重试 (${originalRequest._retryCount}/2)...`)
        
        // 等待1秒后重试
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        return instance(originalRequest)
      } else {
        ElMessage.error('请求超时，请检查网络连接后重试')
        return Promise.reject(error)
      }
    }
    
    // 处理 401 未授权 (Token过期)
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (originalRequest.url.includes('/auth/refresh')) {
        // 如果刷新Token本身失效，跳转登录
        const { useUserStore } = await import('@/stores/user')
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve) => {
          requestsQueue.push((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(instance(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { useUserStore } = await import('@/stores/user')
        const userStore = useUserStore()
        await userStore.refreshTokenAction()
        
        // 刷新成功，重试队列中的请求
        const newToken = localStorage.getItem('token')
        requestsQueue.forEach(cb => cb(newToken))
        requestsQueue = []
        
        // 重试当前请求
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return instance(originalRequest)
      } catch (refreshError) {
        // 刷新失败，清空队列并登出
        requestsQueue = []
        const { useUserStore } = await import('@/stores/user')
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 处理错误响应 - 统一使用 error 字段
    if (error.response) {
      const { status, data } = error.response
      
      // 优先使用统一格式的 error 字段，然后是 message，最后是 detail (兼容旧格式)
      const errorMsg = data?.error || data?.message || data?.detail
      
      switch (status) {
        case 400:
          ElMessage.error(errorMsg || '请求参数错误')
          break
        case 403:
          ElMessage.error(errorMsg || '没有权限访问')
          break
        case 404:
          ElMessage.error(errorMsg || '请求的资源不存在')
          break
        case 500:
          ElMessage.error(errorMsg || '服务器错误')
          break
        default:
          ElMessage.error(errorMsg || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default instance
