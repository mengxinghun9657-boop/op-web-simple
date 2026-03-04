<template>
  <div class="query-history">
    <el-popover
      trigger="click"
      width="500"
      placement="bottom-end"
    >
      <template #reference>
        <el-button>
          <el-icon><Clock /></el-icon>
          查询历史
          <el-badge v-if="historyCount > 0" :value="historyCount" class="history-badge" />
        </el-button>
      </template>
      
      <div class="history-content">
        <div class="history-header">
          <span class="history-title">最近查询</span>
          <el-button link type="danger" size="small" @click="clearAll">
            清空全部
          </el-button>
        </div>
        
        <div v-if="histories.length === 0" class="history-empty">
          <el-empty description="暂无查询历史" :image-size="80" />
        </div>
        
        <div v-else class="history-list">
          <div
            v-for="(item, index) in histories"
            :key="index"
            class="history-item"
            @click="loadHistory(item)"
          >
            <div class="history-item-header">
              <span class="history-time">{{ formatTime(item.timestamp) }}</span>
              <el-button
                link
                type="danger"
                size="small"
                @click.stop="removeHistory(index)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="history-item-content">
              <div class="history-iql">{{ truncateIQL(item.iql) }}</div>
              <div class="history-meta">
                <el-tag size="small">{{ item.spacecode }}</el-tag>
                <span v-if="item.recordCount" class="record-count">
                  {{ item.recordCount }} 条记录
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
import { Clock, Delete } from '@element-plus/icons-vue'
import { useQueryHistory } from '@/composables/useQueryHistory'

const emit = defineEmits(['load'])

const {
  histories,
  removeHistory,
  clearAll,
  historyCount
} = useQueryHistory()

const loadHistory = (item) => {
  emit('load', item)
}

const truncateIQL = (iql) => {
  if (!iql) return ''
  return iql.length > 100 ? iql.substring(0, 100) + '...' : iql
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 小于1小时：显示分钟
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes}分钟前`
  }
  
  // 小于24小时：显示小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}小时前`
  }
  
  // 大于24小时：显示日期
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.history-content {
  max-height: 500px;
  overflow-y: auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-3);
  border-bottom: 2px solid var(--border-color);
  margin-bottom: var(--spacing-4);
}

.history-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--font-size-base);
  letter-spacing: -0.01em;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.history-item {
  padding: var(--spacing-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8), rgba(249, 250, 251, 0.8));
  position: relative;
  overflow: hidden;
}

.history-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, var(--color-primary-500), var(--color-secondary-500));
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.history-item:hover {
  background: white;
  border-color: var(--color-primary-400);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.12);
  transform: translateX(4px);
}

.history-item:hover::before {
  opacity: 1;
}

.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.history-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-weight: 500;
}

.history-iql {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-2);
  word-break: break-all;
  line-height: 1.5;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.record-count {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  padding: 2px 8px;
  background: rgba(64, 158, 255, 0.08);
  border-radius: var(--radius-sm);
}

.history-badge {
  margin-left: var(--spacing-1);
}

.history-empty {
  padding: var(--spacing-6) var(--spacing-4);
}

/* 滚动条样式 */
.history-content::-webkit-scrollbar {
  width: 6px;
}

.history-content::-webkit-scrollbar-track {
  background: var(--bg-elevated);
  border-radius: 3px;
}

.history-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
  transition: background var(--transition-fast);
}

.history-content::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
</style>
