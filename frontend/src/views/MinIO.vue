<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon minio-icon">
            <el-icon><Box /></el-icon>
          </div>
          MinIO 对象存储
        </div>
        <div class="page-subtitle">管理分析报告文件存储</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" size="large" @click="openConsole">
          <el-icon><Link /></el-icon>打开控制台
        </el-button>
      </div>
    </div>

    <!-- MinIO Console -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Box /></el-icon>
          MinIO Console
        </div>
      </div>
      <div class="content-card-body">
        <p class="console-desc">高性能对象存储服务</p>

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
      </div>
    </div>

    <!-- 功能说明 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><InfoFilled /></el-icon>
          功能说明
        </div>
      </div>
      <div class="content-card-body">
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { Box, Link, Monitor, FolderOpened, Key, InfoFilled, Document, Download, Setting } from '@element-plus/icons-vue'

const consoleUrl = `${window.location.protocol}//${window.location.hostname}:8087`
const openConsole = () => window.open(consoleUrl, '_blank')
</script>

<style scoped>
.minio-icon {
  background: linear-gradient(135deg, #f97316, #dc2626) !important;
}

.console-desc {
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin: 0 0 var(--space-4) 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.info-item {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  border: 1px solid var(--border-color);
}

.info-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-bottom: var(--space-2);
}

.info-value {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--text-lg);
  color: var(--text-primary);
  font-weight: 500;
}

.credentials-section {
  background: rgba(249, 115, 22, 0.1);
  border: 1px solid rgba(249, 115, 22, 0.3);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

.credentials-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.credential-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
}

.credential-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.credential-value {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: var(--text-base);
  color: var(--text-primary);
  font-weight: 500;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
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
  background: rgba(26, 115, 232, 0.2);
  color: var(--primary);
}

.feature-icon.green {
  background: rgba(30, 142, 62, 0.2);
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
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.feature-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .info-grid,
  .credentials-grid,
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>
