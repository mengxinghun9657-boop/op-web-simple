import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginAPI, refreshToken as refreshTokenAPI } from '@/api/users'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token'))
  const refreshToken = ref(localStorage.getItem('refreshToken'))
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || 'viewer')

  // 判断是否具有特定权限
  function hasPermission(permission) {
    const role = userRole.value
    return role === 'super_admin' || role === 'admin' || role === permission
  }

  function hasRole(role) {
    return user.value?.role === role
  }

  // 登录
  async function login(credentials) {
    // 使用 users.js 的 login 函数
    const response = await loginAPI({
      username: credentials.username,
      password: credentials.password
    })
    
    // 统一响应格式处理
    if (response.success) {
      const data = response.data
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      user.value = data.user
      
      // 持久化
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refreshToken', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      
      return data
    } else {
      throw new Error(response.message || '登录失败')
    }
  }

  // 登出
  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  // 刷新Token
  async function refreshTokenAction() {
    if (!refreshToken.value) {
      throw new Error('No refresh token')
    }
    
    // 使用 users.js 的 refreshToken 函数
    const response = await refreshTokenAPI(refreshToken.value)
    
    if (response.success) {
      const data = response.data
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refreshToken', data.refresh_token)
    } else {
      throw new Error(response.message || 'Token刷新失败')
    }
  }

  return {
    token,
    refreshToken,
    user, 
    isAuthenticated, 
    userRole,
    hasPermission,
    hasRole,
    login,
    logout,
    refreshTokenAction
  }
})