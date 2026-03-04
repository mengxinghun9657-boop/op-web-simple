import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/monitoring'

export const useMonitoringStore = defineStore('monitoring', () => {
  const loading = ref(false)
  const bccResults = ref([])
  const bosResults = ref([])

  async function analyzeBCC(data) {
    loading.value = true
    try {
      const response = await api.analyzeBCC(data)
      const res = response.data || response  // 兼容axios拦截器
      bccResults.value = res.data || [] // 假设是同步或快速返回列表
    } finally { loading.value = false }
  }

  async function analyzeBOS(data) {
    loading.value = true
    try {
      const response = await api.analyzeBOS(data)
      const res = response.data || response  // 兼容axios拦截器
      bosResults.value = res.data || []
    } finally { loading.value = false }
  }

  return { loading, bccResults, bosResults, analyzeBCC, analyzeBOS }
})