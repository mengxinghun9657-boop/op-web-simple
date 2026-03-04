/**
 * 路由管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getPendingSuggestions,
  getSuggestionHistory,
  getRoutingRules,
  getRoutingStatistics
} from '@/api/routing'

export const useRoutingStore = defineStore('routing', () => {
  // 状态
  const suggestions = ref([])
  const suggestionHistory = ref([])
  const rules = ref([])
  const statistics = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 计算属性
  const pendingSuggestionsCount = computed(() => {
    return suggestions.value.filter(s => s.status === 'pending').length
  })

  const activeRulesCount = computed(() => {
    return rules.value.filter(r => r.is_active).length
  })

  // 方法
  const fetchPendingSuggestions = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await getPendingSuggestions(params)
      if (response.success) {
        suggestions.value = response.data.list || []
        return response.data
      } else {
        throw new Error(response.message || '获取建议列表失败')
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchSuggestionHistory = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await getSuggestionHistory(params)
      if (response.success) {
        suggestionHistory.value = response.data.list || []
        return response.data
      } else {
        throw new Error(response.message || '获取审核历史失败')
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchRoutingRules = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await getRoutingRules(params)
      if (response.success) {
        rules.value = response.data.list || []
        return response.data
      } else {
        throw new Error(response.message || '获取规则列表失败')
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchStatistics = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await getRoutingStatistics(params)
      if (response.success) {
        statistics.value = response.data
        return response.data
      } else {
        throw new Error(response.message || '获取统计数据失败')
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // 状态
    suggestions,
    suggestionHistory,
    rules,
    statistics,
    loading,
    error,
    // 计算属性
    pendingSuggestionsCount,
    activeRulesCount,
    // 方法
    fetchPendingSuggestions,
    fetchSuggestionHistory,
    fetchRoutingRules,
    fetchStatistics,
    clearError
  }
})
