import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/eip'

export const useEipStore = defineStore('eip', () => {
  const loading = ref(false)
  const task = ref(null)

  async function analyzeEIP(data) {
    loading.value = true
    try {
      const response = await api.analyzeEIP(data)
      const res = response.data || response  // 兼容axios拦截器
      task.value = res
    } finally {
      loading.value = false
    }
  }

  return { loading, task, analyzeEIP }
})