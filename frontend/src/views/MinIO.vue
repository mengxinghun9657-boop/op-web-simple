<template>
  <div class="minio-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-icon minio">
        <el-icon :size="24"><Box /></el-icon>
      </div>
      <div class="page-header-content">
        <h2 class="page-title">MinIO 对象存储</h2>
        <p class="page-subtitle">管理分析报告文件存储</p>
      </div>
    </div>

    <!-- 主卡片 -->
    <Card
      title="MinIO Console"
      icon="Box"
      class="animate-slide-in-up"
    >
      <template #header>
        <el-button type="primary" size="large" @click="openConsole">
          <el-icon><Link /></el-icon>打开控制台
        </el-button>
      </template>

      <div class="console-info">
        <p class="console-desc">高性能对象存储服务</p>
      </div>

      <!-- 连接信息 -->
      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">
            <el-icon><Monitor /></el-icon>
            <span>控制台地址</span>
          </div>
          <div class="info-value">{{ consoleUrl }}</div>
        </div>
        <div class="info-item">
          <div class="info-label">
            <el-icon><FolderOpened /></el-icon>
            <span>存储桶</span>
          </div>
          <div class="info-value">op-reports</div>
        </div>
      </div>

      <!-- 凭证信息 -->
      <div class="credentials-section">
        <h4 class="credentials-title">
          <el-icon><Key /></el-icon>
          <span>访问凭证</span>
        </h4>
        <div class="credentials-grid">
          <div class="credential-item">
            <span class="credential-label">用户名</span>
            <span class="credential-value">admin</span>
          </div>
          <div class="credential-item">
            <span class="credential-label">密码</span>
            <span class="credential-value">Zhang~~1</span>
          </div>
        </div>
      </div>
    </Card>

    <!-- 功能说明 -->
    <Card
      title="功能说明"
      icon="InfoFilled"
      class="animate-slide-in-up"
    >
      <div class="features-grid">
        <div class="feature-item">
          <div class="feature-icon blue">
            <el-icon><Document /></el-icon>
          </div>
          <div class="feature-content">
            <div class="feature-title">报告存储</div>
            <div class="feature-desc">自动存储分析报告HTML文件</div>
          </div>
        </div>
        <div class="feature-item">
          <div class="feature-icon green">
            <el-icon><Download /></el-icon>
          </div>
          <div class="feature-content">
            <div class="feature-title">文件下载</div>
            <div class="feature-desc">支持批量下载历史报告</div>
          </div>
        </div>
        <div class="feature-item">
          <div class="feature-icon purple">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="feature-content">
            <div class="feature-title">存储管理</div>
            <div class="feature-desc">可视化管理存储桶和文件</div>
          </div>
        </div>
      </div>
    </Card>
  </div>
</template>

<script setup>
import { Box, Link, Monitor, FolderOpened, Key, InfoFilled, Document, Download, Setting } from '@element-plus/icons-vue'
import { Card } from '@/components/common'

const consoleUrl = `${window.location.protocol}//${window.location.hostname}:8087`
const openConsole = () => window.open(consoleUrl, '_blank')
</script>

<style scoped>
.minio-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  animation: slideInUp var(--duration-slow) var(--ease-out);
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  color: white;
}

.page-header-icon.minio {
  background: linear-gradient(135deg, #f97316, #dc2626);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0;
}

.console-info {
  margin-bottom: var(--spacing-4);
}

.console-desc {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
}

.info-item {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  border: 1px solid var(--border-color);
}

.info-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-2);
}

.info-value {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--font-size-lg);
  color: var(--text-primary);
  font-weight: 500;
}

.credentials-section {
  background: rgba(249, 115, 22, 0.1);
  border: 1px solid rgba(249, 115, 22, 0.3);
  border-radius: var(--radius-lg);
  padding: var(--spacing-5);
}

.credentials-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-4) 0;
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.credential-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--spacing-3) var(--spacing-4);
}

.credential-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.credential-value {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  font-weight: 500;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-4);
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
}

.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 20px;
}

.feature-icon.blue {
  background: rgba(59, 130, 246, 0.2);
  color: var(--color-primary);
}

.feature-icon.green {
  background: rgba(34, 197, 94, 0.2);
  color: var(--color-success);
}

.feature-icon.purple {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
}

.feature-content {
  flex: 1;
}

.feature-title {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-1);
}

.feature-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .info-grid,
  .credentials-grid {
    grid-template-columns: 1fr;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>
