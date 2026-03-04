// 统一的任务状态轮询工具
import { getTaskStatus } from '@/api/tasks'

export const pollTaskStatus = (taskId, onUpdate, onComplete, onError) => {
  let pollCount = 0
  let failCount = 0
  const maxPolls = 120 // 最多轮询2分钟
  const maxFails = 3 // 最多连续失败3次
  
  const poll = setInterval(async () => {
    try {
      pollCount++
      
      if (pollCount > maxPolls) {
        clearInterval(poll)
        onError?.('任务超时')
        return
      }
      
      const response = await getTaskStatus(taskId)
      const { status, progress, message, error } = response
      
      // 成功获取状态，重置失败计数
      failCount = 0
      
      // 更新进度
      onUpdate?.({ status, progress, message })
      
      // 检查是否完成
      if (status === 'completed') {
        clearInterval(poll)
        onComplete?.(response)
      } else if (status === 'failed') {
        clearInterval(poll)
        onError?.(error || message || '任务失败')
      }
      
    } catch (error) {
      failCount++
      console.error(`轮询任务状态失败 (${failCount}/${maxFails}):`, error)
      
      if (failCount >= maxFails) {
        clearInterval(poll)
        onError?.('获取任务状态失败')
      }
    }
  }, 2000) // 每2秒轮询一次
  
  return poll // 返回定时器ID，用于手动清除
}
