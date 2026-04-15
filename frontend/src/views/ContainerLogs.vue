<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Document /></el-icon>
          </div>
          容器日志
        </div>
        <div class="page-subtitle">实时查看容器运行日志 / 连接容器终端</div>
      </div>
    </div>

    <!-- 主内容区 -->
    <el-card shadow="never" class="logs-card">
      <!-- 容器选择 Tabs -->
      <el-tabs v-model="activeContainer" type="border-card" @tab-change="handleTabChange">
        <el-tab-pane label="后端服务" name="backend">
          <template #label>
            <span class="tab-label">
              <el-icon><Monitor /></el-icon>
              后端服务
              <el-tag v-if="isConnected && activeContainer === 'backend'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="后端 Worker" name="backend_worker">
          <template #label>
            <span class="tab-label">
              <el-icon><Monitor /></el-icon>
              后端 Worker
              <el-tag v-if="isConnected && activeContainer === 'backend_worker'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="MySQL" name="mysql">
          <template #label>
            <span class="tab-label">
              <el-icon><Coin /></el-icon>
              MySQL
              <el-tag v-if="isConnected && activeContainer === 'mysql'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="Redis" name="redis">
          <template #label>
            <span class="tab-label">
              <el-icon><Collection /></el-icon>
              Redis
              <el-tag v-if="isConnected && activeContainer === 'redis'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="MinIO" name="minio">
          <template #label>
            <span class="tab-label">
              <el-icon><Box /></el-icon>
              MinIO
              <el-tag v-if="isConnected && activeContainer === 'minio'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
        <el-tab-pane label="前端服务" name="frontend">
          <template #label>
            <span class="tab-label">
              <el-icon><Monitor /></el-icon>
              前端服务
              <el-tag v-if="isConnected && activeContainer === 'frontend'" type="success" size="small" effect="dark" class="live-tag">LIVE</el-tag>
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <!-- 控制栏 -->
      <div class="logs-toolbar">
        <div class="toolbar-left">
          <el-button
            :type="isConnected ? 'danger' : 'primary'"
            @click="toggleConnection"
            :loading="connecting"
          >
            <el-icon v-if="!isConnected"><VideoPlay /></el-icon>
            <el-icon v-else><VideoPause /></el-icon>
            {{ isConnected ? '停止刷新' : '开始刷新' }}
          </el-button>
          <el-button @click="clearLogs" :disabled="logs.length === 0">
            <el-icon><Delete /></el-icon>
            清空日志
          </el-button>
          <el-button type="success" @click="openTerminal">
            <el-icon><Promotion /></el-icon>
            连接终端
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-tag type="info" effect="plain">
            当前容器: {{ containerNames[activeContainer] }}
          </el-tag>
          <el-tag :type="connectionStatus.type" effect="plain" class="status-tag">
            {{ connectionStatus.text }}
          </el-tag>
          <span class="log-count">共 {{ logs.length }} 行 (最多显示500行)</span>
        </div>
      </div>

      <!-- 日志显示区域 -->
      <div ref="logsContainer" class="logs-container" @scroll="handleScroll">
        <div v-if="logs.length === 0" class="empty-logs">
          <el-empty description="暂无日志">
            <template #description>
              <p>点击"开始刷新"按钮开始加载日志</p>
            </template>
          </el-empty>
        </div>
        <div v-else class="logs-content">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-line"
            :class="getLogLevelClass(log)"
          >
            <span class="log-index">{{ index + 1 }}</span>
            <span class="log-text" v-text="log"></span>
          </div>
        </div>
      </div>

      <!-- 底部提示 -->
      <div class="logs-footer">
        <el-alert
          v-if="logs.length >= 500"
          title="已达到最大显示行数限制(500行)，将循环覆盖旧日志"
          type="warning"
          :closable="false"
          show-icon
        />
        <div class="footer-info">
          <span>提示: 日志内容支持鼠标选择复制</span>
          <el-link type="primary" @click="scrollToBottom" v-if="!isAtBottom && logs.length > 0">
            滚动到底部
          </el-link>
        </div>
      </div>
    </el-card>

    <!-- Web Terminal 对话框 -->
    <el-dialog
      v-model="terminalVisible"
      :title="`终端 - ${containerNames[activeContainer]}`"
      fullscreen
      destroy-on-close
      class="terminal-dialog"
      @opened="initTerminal"
      @close="closeTerminal"
    >
      <div ref="terminalEl" class="terminal-wrapper"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  Monitor,
  Coin,
  Collection,
  Box,
  VideoPlay,
  VideoPause,
  Delete,
  Promotion
} from '@element-plus/icons-vue'

// 容器名称映射
const containerNames = {
  backend: '后端服务 (cluster-backend-api)',
  backend_worker: '后端 Worker (cluster-backend-worker)',
  mysql: 'MySQL (cluster-mysql)',
  redis: 'Redis (cluster-redis)',
  minio: 'MinIO (cluster-minio)',
  frontend: '前端服务 (cluster-frontend)'
}

// 当前选中的容器
const activeContainer = ref('backend')

// 日志数据
const logs = ref([])
const maxLogLines = 500

// 连接状态
const isConnected = ref(false)
const connecting = ref(false)
const eventSource = ref(null)

// 滚动相关
const logsContainer = ref(null)
const isAtBottom = ref(true)
const autoScroll = ref(true)

// ===== Web Terminal 相关 =====
const terminalVisible = ref(false)
const terminalEl = ref(null)
let terminal = null
let fitAddon = null
let terminalWs = null
let resizeObserver = null

// 计算连接状态显示
const connectionStatus = computed(() => {
  if (isConnected.value) {
    return { type: 'success', text: '已连接' }
  } else if (connecting.value) {
    return { type: 'warning', text: '连接中...' }
  } else {
    return { type: 'info', text: '未连接' }
  }
})

// 切换连接状态
const toggleConnection = async () => {
  if (isConnected.value) {
    disconnect()
  } else {
    await connect()
  }
}

// 检查并刷新Token
const ensureValidToken = async () => {
  const token = localStorage.getItem('token')
  if (!token) throw new Error('未登录')

  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const timeUntilExp = payload.exp * 1000 - Date.now()
    if (timeUntilExp < 5 * 60 * 1000) {
      const { useUserStore } = await import('@/stores/user')
      const userStore = useUserStore()
      await userStore.refreshTokenAction()
    }
  } catch (error) {
    console.error('Token检查失败:', error)
  }
}

// 建立日志连接
const connect = async () => {
  try {
    connecting.value = true
    logs.value = []
    await ensureValidToken()

    const container = activeContainer.value
    const token = localStorage.getItem('token')
    const url = `/api/v1/logs/stream/${container}?token=${token}`

    eventSource.value = new EventSource(url)

    eventSource.value.onopen = () => {
      isConnected.value = true
      connecting.value = false
      ElMessage.success(`已连接到 ${containerNames[container]}`)
    }

    eventSource.value.onmessage = (event) => {
      addLog(event.data)
    }

    eventSource.value.onerror = (error) => {
      console.error('EventSource error:', error)
      if (error.target && error.target.readyState === EventSource.CLOSED) {
        handleReconnect()
      } else if (isConnected.value) {
        ElMessage.error('连接断开，请重试')
        disconnect()
      }
    }
  } catch (error) {
    console.error('连接失败:', error)
    ElMessage.error('连接失败: ' + error.message)
    connecting.value = false
  }
}

// Token 过期后重连
const handleReconnect = async () => {
  try {
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    await userStore.refreshTokenAction()
    disconnect()
    await connect()
  } catch (refreshError) {
    console.error('Token刷新失败:', refreshError)
    ElMessage.error('登录已过期，请重新登录')
    const { useUserStore } = await import('@/stores/user')
    const userStore = useUserStore()
    userStore.logout()
    const router = await import('@/router')
    router.default.push('/login')
  }
}

// 断开日志连接
const disconnect = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  isConnected.value = false
  connecting.value = false
  ElMessage.info('已断开连接')
}

// 添加日志行
const addLog = (logLine) => {
  if (logs.value.length >= maxLogLines) {
    logs.value.shift()
  }
  logs.value.push(logLine)
  if (autoScroll.value) {
    nextTick(() => scrollToBottom())
  }
}

// 清空日志
const clearLogs = () => {
  logs.value = []
  ElMessage.success('日志已清空')
}

// Tab 切换
const handleTabChange = () => {
  if (isConnected.value) disconnect()
  logs.value = []
}

// 滚动事件
const handleScroll = () => {
  if (!logsContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = logsContainer.value
  isAtBottom.value = scrollHeight - scrollTop - clientHeight < 10
  autoScroll.value = isAtBottom.value
}

// 滚动到底部
const scrollToBottom = () => {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    isAtBottom.value = true
    autoScroll.value = true
  }
}

// 日志级别样式
const getLogLevelClass = (log) => {
  const lowerLog = log.toLowerCase()
  if (lowerLog.includes('error') || lowerLog.includes('exception') || lowerLog.includes('traceback')) {
    return 'log-error'
  } else if (lowerLog.includes('warning') || lowerLog.includes('warn')) {
    return 'log-warning'
  } else if (lowerLog.includes('info') && lowerLog.includes('success')) {
    return 'log-success'
  } else if (lowerLog.includes('debug')) {
    return 'log-debug'
  }
  return ''
}

// ===== Web Terminal 功能 =====

const openTerminal = () => {
  terminalVisible.value = true
}

const initTerminal = async () => {
  await nextTick()
  if (!terminalEl.value) return

  // 动态 import xterm（tree-shaking 友好）
  const { Terminal } = await import('xterm')
  const { FitAddon } = await import('xterm-addon-fit')
  await import('xterm/css/xterm.css')

  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
    theme: {
      background: '#1e1e1e',
      foreground: '#d4d4d4',
      cursor: '#ffffff',
      selectionBackground: '#264f78'
    },
    scrollback: 1000
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalEl.value)
  fitAddon.fit()

  // 建立 WebSocket
  const token = localStorage.getItem('token')
  const container = activeContainer.value
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/logs/exec/${container}?token=${token}`

  terminalWs = new WebSocket(wsUrl)
  terminalWs.binaryType = 'arraybuffer'

  terminalWs.onopen = () => {
    terminal.write(`\r\n\x1b[32m[已连接到 ${containerNames[container]}]\x1b[0m\r\n`)
    sendResize()
  }

  terminalWs.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      terminal.write(new Uint8Array(event.data))
    } else {
      terminal.write(event.data)
    }
  }

  terminalWs.onclose = () => {
    terminal?.write('\r\n\x1b[33m[连接已断开]\x1b[0m\r\n')
  }

  terminalWs.onerror = () => {
    terminal?.write('\r\n\x1b[31m[连接错误，请重试]\x1b[0m\r\n')
  }

  // 终端输入 → WebSocket
  terminal.onData((data) => {
    if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
      terminalWs.send(data)
    }
  })

  // 容器大小变化时自动 fit
  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
  })
  resizeObserver.observe(terminalEl.value)

  // 终端 resize → 通知后端
  terminal.onResize(({ cols, rows }) => {
    if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
      terminalWs.send(JSON.stringify({ type: 'resize', cols, rows }))
    }
  })
}

const sendResize = () => {
  if (!terminal || !terminalWs || terminalWs.readyState !== WebSocket.OPEN) return
  const { cols, rows } = terminal
  terminalWs.send(JSON.stringify({ type: 'resize', cols, rows }))
}

const closeTerminal = () => {
  resizeObserver?.disconnect()
  resizeObserver = null

  if (terminalWs) {
    terminalWs.close()
    terminalWs = null
  }

  if (terminal) {
    terminal.dispose()
    terminal = null
  }

  fitAddon = null
}

// 组件卸载
onUnmounted(() => {
  disconnect()
  closeTerminal()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.page-title-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin-left: 52px;
}

.logs-card {
  min-height: calc(100vh - 200px);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-tag {
  margin-left: 4px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.logs-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  min-width: 80px;
  text-align: center;
}

.log-count {
  font-size: 13px;
  color: var(--text-tertiary);
}

.logs-container {
  height: calc(100vh - 380px);
  min-height: 400px;
  overflow-y: auto;
  background: #1e1e1e;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.empty-logs {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logs-content {
  padding: 12px;
}

.log-line {
  display: flex;
  padding: 2px 0;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-index {
  min-width: 50px;
  color: #858585;
  text-align: right;
  padding-right: 12px;
  user-select: none;
}

.log-text {
  flex: 1;
}

.log-error {
  color: #f48771;
  background: rgba(244, 135, 113, 0.1);
}

.log-warning {
  color: #dcdcaa;
  background: rgba(220, 220, 170, 0.1);
}

.log-success {
  color: #4ec9b0;
}

.log-debug {
  color: #9cdcfe;
}

.logs-footer {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-primary);
}

.footer-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.logs-container::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.logs-container::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.logs-container::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 5px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}

/* Terminal */
.terminal-wrapper {
  width: 100%;
  height: calc(100vh - 120px);
  background: #1e1e1e;
  border-radius: 6px;
  overflow: hidden;
}
</style>

<style>
/* 覆盖 dialog body 内边距，让终端铺满 */
.terminal-dialog .el-dialog__body {
  padding: 12px;
  background: #1e1e1e;
}
</style>
