import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/resource'

export const useResourceStore = defineStore('resource', () => {
  const loading = ref(false)
  const metrics = ref({})

  async function fetchMetrics(params) {
    loading.value = true
    try {
      const response = await api.getClusterMetrics(params)
      const res = response.data || response  // 兼容axios拦截器
      metrics.value = res.data // 假设后端返回结构
    } finally {
      loading.value = false
    }
  }

  return { loading, metrics, fetchMetrics }
})