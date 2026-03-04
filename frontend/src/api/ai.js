/**
 * AI 功能 API
 */
import axios from '@/utils/axios'

// ==================== AI 对话 ====================

/**
 * AI 对话
 * @param {Object} data - 对话数据
 * @param {Array} data.messages - 消息历史
 * @param {Object} data.context_data - 上下文数据
 * @param {number} data.temperature - 温度参数 (0-1)
 * @param {number} data.max_tokens - 最大token数
 * @returns {Promise} AI 回复
 */
export const chatWithAI = (data) => {
  return axios.post('/api/v1/ai/chat', data)
}

/**
 * 获取对话历史
 * @param {number} limit - 返回数量
 * @returns {Promise} 对话历史
 */
export const getChatHistory = (limit = 50) => {
  return axios.get('/api/v1/ai/history', { params: { limit } })
}

/**
 * 清空对话历史
 * @returns {Promise} 清空结果
 */
export const clearChatHistory = () => {
  return axios.delete('/api/v1/ai/history')
}

/**
 * 查询数据库数据
 * @param {Object} data - 查询数据
 * @param {string} data.table - 表名
 * @param {Object} data.filters - 过滤条件
 * @param {number} data.limit - 返回数量
 * @param {Array} data.columns - 指定列
 * @returns {Promise} 查询结果
 */
export const queryDatabase = (data) => {
  return axios.post('/api/v1/ai/query-data', data)
}

/**
 * 获取所有可查询的表
 * @returns {Promise} 表列表
 */
export const getAvailableTables = () => {
  return axios.get('/api/v1/ai/tables')
}

// ==================== AI 智能查询 ====================

/**
 * AI 智能查询 (SSE 流式接口)
 * 
 * @param {string} query - 查询问题
 * @param {Function} onEvent - SSE 事件回调函数
 * @param {Function} onError - 错误回调函数
 * @returns {Promise<void>}
 * 
 * @example
 * await intelligentQuery(
 *   '查询所有物理机信息',
 *   (event) => {
 *     console.log('Status:', event.status)
 *     if (event.status === 'completed') {
 *       console.log('Result:', event.data)
 *     }
 *   },
 *   (error) => {
 *     console.error('Error:', error)
 *   }
 * )
 */
export const intelligentQuery = async (query, onEvent, onError) => {
  const token = localStorage.getItem('token')
  
  try {
    const response = await fetch(
      `/api/v1/ai/intelligent-query?query=${encodeURIComponent(query)}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream'
        }
      }
    )

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }

      // 解码数据
      const chunk = decoder.decode(value, { stream: true })
      
      // 处理 SSE 数据（可能包含多个事件）
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonData = line.substring(6) // 移除 "data: " 前缀
            const event = JSON.parse(jsonData)
            
            // 调用事件回调
            if (onEvent) {
              onEvent(event)
            }
          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError, line)
          }
        }
      }
    }
  } catch (error) {
    console.error('SSE connection error:', error)
    if (onError) {
      onError(error)
    }
  }
}

/**
 * 提交路由反馈
 * @param {Object} data - 反馈数据
 * @param {number} data.routing_log_id - 路由日志ID
 * @param {string} data.correct_intent - 正确的意图类型
 * @param {string} data.feedback_reason - 反馈原因
 * @returns {Promise} 提交结果
 */
export const submitRoutingFeedback = (data) => {
  return axios.post('/api/v1/routing/feedback', data)
}
