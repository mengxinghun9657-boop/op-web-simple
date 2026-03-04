import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/operational'

export const useOperationalStore = defineStore('operational', () => {
  const loading = ref(false)
  const taskId = ref(null)
  const result = ref(null)

  async function analyzeData(formData) {
    loading.value = true
    result.value = null
    try {
      const res = await api.analyzeData(formData)
      taskId.value = res.task_id
      return res
    } catch (e) {
      loading.value = false
      throw e
    }
  }

  async function analyzeApiData(params) {
    loading.value = true
    result.value = null
    try {
      const res = await api.analyzeApiData(params)
      taskId.value = res.task_id
      return res
    } catch (e) {
      loading.value = false
      throw e
    }
  }

  async function fetchResult(id) {
    try {
      const res = await api.getResult(id)
      
      // 处理 processing 状态 - 继续轮询
      if (res.status === 'processing') {
        // 可以在这里更新进度信息（如果需要）
        return false
      }
      
      // 处理完成状态 - 停止轮询
      if (res.status === 'completed' || res.status === 'success') {
        result.value = res
        loading.value = false
        return true
      }
      
      // 处理失败状态 - 停止轮询
      if (res.status === 'failed') {
        result.value = res
        loading.value = false
        return true
      }
      
      // 其他状态继续轮询
      return false
    } catch (e) {
      // 如果是404错误，继续轮询（文件还未创建）
      if (e.response?.status === 404) {
        return false
      }
      // 其他错误，停止轮询
      console.error('获取任务结果失败:', e)
      loading.value = false
      return true
    }
  }

  function reset() {
    loading.value = false
    taskId.value = null
    result.value = null
  }

  return { loading, taskId, result, analyzeData, analyzeApiData, fetchResult, reset }
})
