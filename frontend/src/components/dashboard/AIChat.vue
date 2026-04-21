<template>
  <div class="bento-card ai-chat-card">
    <div class="bento-card-header">
      <div class="bento-card-title">
        <div class="bento-card-title-icon icon-bg-secondary">
          <el-icon :size="16"><ChatDotRound /></el-icon>
        </div>
        AI 助手
      </div>
      <div class="chat-actions">
        <el-button size="small" @click="clearHistory">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </div>
    </div>
    
    <div class="bento-card-body">
      <!-- 消息历史 -->
      <div class="chat-history" ref="historyRef">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="chat-message"
          :class="`chat-message-${msg.role}`"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            <el-icon v-else><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(msg.content)"></div>
            <div class="message-time">{{ formatTime(msg.created_at || msg.timestamp) }}</div>
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-if="loading" class="chat-message chat-message-assistant">
          <div class="message-avatar">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-loading">
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
              <span class="loading-dot"></span>
            </div>
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="messages.length === 0 && !loading" class="chat-empty">
          <el-icon class="empty-icon"><ChatDotRound /></el-icon>
          <p class="empty-text">你好！我是 AI 助手</p>
          <p class="empty-hint">有什么可以帮助你的吗？</p>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="chat-input-wrapper">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!inputMessage.trim()"
          @click="sendMessage"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, User, Delete, Promotion } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const historyRef = ref(null)

// 加载历史消息
const loadHistory = async () => {
  try {
    const response = await axios.get('/api/v1/ai/history', {
      params: { limit: 50 }
    })
    // axios拦截器已经返回了response.data，所以response就是{success, data}
    if (response.success) {
      messages.value = response.data.map(msg => ({
        ...msg,
        timestamp: new Date(msg.created_at)
      }))
      await nextTick()
      scrollToBottom()
    }
  } catch (error) {
    console.error('加载历史失败:', error)
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return
  
  const userMessage = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date()
  }
  
  messages.value.push(userMessage)
  const currentInput = inputMessage.value
  inputMessage.value = ''
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  // 调用 AI API
  loading.value = true
  try {
    const response = await axios.post('/api/v1/ai/chat', {
      messages: [{ role: 'user', content: currentInput }],
      temperature: 0.6,
      max_tokens: 1000
    })
    // axios拦截器已经返回了response.data，所以response就是{success, data}
    
    if (response.success) {
      messages.value.push({
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date()
      })
      
      await nextTick()
      scrollToBottom()
    }
  } catch (error) {
    ElMessage.error('AI 响应失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    // 移除用户消息
    messages.value.pop()
  } finally {
    loading.value = false
  }
}

// 清空历史
const clearHistory = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有对话历史吗？',
      '确认清空',
      {
        confirmButtonText: '清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await axios.delete('/api/v1/ai/history')
    // axios拦截器已经返回了response.data，所以response就是{success, data}
    if (response.success) {
      messages.value = []
      ElMessage.success('对话已清空')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (historyRef.value) {
    historyRef.value.scrollTop = historyRef.value.scrollHeight
  }
}

// 格式化消息（支持 Markdown 简单格式）
const formatMessage = (content) => {
  if (!content) return ''
  
  // 简单的 Markdown 格式化
  let formatted = content
  
  // 代码块
  formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  
  // 行内代码
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>')
  
  // 粗体
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  
  // 换行
  formatted = formatted.replace(/\n/g, '<br>')
  
  return formatted
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.ai-chat-card {
  height: 600px; /* 固定高度，确保足够的显示空间 */
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

.chat-actions {
  display: flex;
  gap: var(--spacing-2);
}

.bento-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  overflow: hidden;
  padding: var(--spacing-4);
  min-height: 0; /* 关键：允许 flex 子元素正确收缩 */
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  padding: var(--spacing-2);
  min-height: 0; /* 关键：允许滚动 */
}

.chat-message {
  display: flex;
  gap: var(--spacing-3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));
  color: white;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
}

.chat-message-user .message-avatar {
  background: linear-gradient(135deg, var(--color-secondary-500), var(--color-success));
}

.message-content {
  flex: 1;
  max-width: 75%;
}

.message-text {
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-lg);
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  line-height: 1.7;
  word-break: break-word;
}

.message-text :deep(code) {
  background: rgba(64, 158, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: var(--spacing-2) 0;
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
}

.chat-message-user .message-text {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(103, 194, 58, 0.12));
  border-color: var(--color-primary-300);
}

.message-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--spacing-1);
  padding: 0 var(--spacing-2);
}

.message-loading {
  display: flex;
  gap: 6px;
  padding: var(--spacing-3);
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary-500);
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12) var(--spacing-4);
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  color: var(--color-primary-400);
  margin-bottom: var(--spacing-4);
  opacity: 0.6;
}

.empty-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2);
}

.empty-hint {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: 0;
  max-width: 300px;
}

/* 输入框 */
.chat-input-wrapper {
  display: flex;
  gap: var(--spacing-3);
  align-items: flex-end;
  padding-top: var(--spacing-3);
  border-top: 2px solid var(--border-color);
}

.chat-input-wrapper :deep(.el-textarea) {
  flex: 1;
}

.chat-input-wrapper :deep(.el-textarea__inner) {
  resize: none;
  border-radius: var(--radius-lg);
  border: 2px solid var(--border-color);
  transition: all var(--transition-fast);
}

.chat-input-wrapper :deep(.el-textarea__inner:hover) {
  border-color: var(--color-primary-400);
}

.chat-input-wrapper :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.chat-input-wrapper .el-button {
  height: 44px;
  min-width: 80px;
}

/* 滚动条样式 */
.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-track {
  background: var(--bg-elevated);
  border-radius: 3px;
}

.chat-history::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
  transition: background var(--transition-fast);
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
</style>
