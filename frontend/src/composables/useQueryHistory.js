/**
 * Query History Composable
 * 
 * 管理运营分析查询历史记录
 * 使用localStorage持久化存储，最多保存10条记录
 */

import { ref, computed } from 'vue'

const STORAGE_KEY = 'operational_query_history'
const MAX_HISTORY = 10

/**
 * 查询历史管理 Composable
 * 
 * @returns {Object} 查询历史管理对象
 * @returns {Ref<Array>} histories - 历史记录列表
 * @returns {Function} addHistory - 添加历史记录
 * @returns {Function} removeHistory - 移除历史记录
 * @returns {Function} clearAll - 清空所有历史记录
 * @returns {ComputedRef<number>} historyCount - 历史记录数量
 * 
 * @example
 * const { histories, addHistory, removeHistory, clearAll, historyCount } = useQueryHistory()
 * 
 * // 添加查询记录
 * addHistory({
 *   spacecode: 'HMLCC',
 *   username: 'v_liuxiang',
 *   iql: '负责人 = v_liuxiang',
 *   page: 1,
 *   pgcount: 100,
 *   recordCount: 50
 * })
 */
export function useQueryHistory() {
  const histories = ref([])

  /**
   * 从localStorage加载历史记录
   */
  const loadHistories = () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        histories.value = JSON.parse(stored)
      }
    } catch (error) {
      console.warn('加载查询历史失败:', error)
      histories.value = []
    }
  }

  /**
   * 保存历史记录到localStorage
   * 优雅降级：如果localStorage不可用或空间不足，不影响功能
   */
  const saveHistories = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(histories.value))
    } catch (error) {
      if (error.name === 'QuotaExceededError') {
        console.warn('localStorage空间不足，清理旧记录')
        // 只保留最近5条
        histories.value = histories.value.slice(0, 5)
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(histories.value))
        } catch (e) {
          console.warn('保存查询历史失败:', e)
        }
      } else {
        console.warn('保存查询历史失败:', error)
      }
    }
  }

  /**
   * 添加历史记录
   * 
   * @param {Object} query - 查询对象
   * @param {string} query.spacecode - 空间代码
   * @param {string} query.username - 用户名（可选）
   * @param {string} query.iql - IQL查询语句
   * @param {number} query.page - 起始页码
   * @param {number} query.pgcount - 每页记录数
   * @param {number} [query.recordCount] - 查询结果记录数（可选）
   */
  const addHistory = (query) => {
    if (!query || !query.iql) {
      return
    }

    const newHistory = {
      timestamp: Date.now(),
      spacecode: query.spacecode || '',
      username: query.username || '',
      iql: query.iql,
      page: query.page || 1,
      pgcount: query.pgcount || 100,
      recordCount: query.recordCount || null
    }

    // 检查是否与最近一条相同（避免重复）
    if (histories.value.length > 0) {
      const last = histories.value[0]
      if (last.iql === newHistory.iql && last.spacecode === newHistory.spacecode) {
        // 更新时间戳和记录数
        last.timestamp = newHistory.timestamp
        if (newHistory.recordCount !== null) {
          last.recordCount = newHistory.recordCount
        }
        saveHistories()
        return
      }
    }

    // 添加到开头
    histories.value.unshift(newHistory)

    // 限制最大数量
    if (histories.value.length > MAX_HISTORY) {
      histories.value = histories.value.slice(0, MAX_HISTORY)
    }

    saveHistories()
  }

  /**
   * 移除历史记录
   * 
   * @param {number} index - 要移除的记录索引
   */
  const removeHistory = (index) => {
    if (index >= 0 && index < histories.value.length) {
      histories.value.splice(index, 1)
      saveHistories()
    }
  }

  /**
   * 清空所有历史记录
   */
  const clearAll = () => {
    histories.value = []
    saveHistories()
  }

  /**
   * 历史记录数量
   */
  const historyCount = computed(() => histories.value.length)

  // 初始化时加载
  loadHistories()

  return {
    histories,
    addHistory,
    removeHistory,
    clearAll,
    historyCount
  }
}
