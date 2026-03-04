<template>
  <div class="system-config-page">
    <!-- 页面标题 -->
    <div class="page-header animate-slide-in-up">
      <div class="header-content">
        <div class="header-left">
          <el-icon class="header-icon"><Setting /></el-icon>
          <div>
            <h1 class="page-title">系统配置管理</h1>
            <p class="page-subtitle">集中管理CMDB、监控、分析等模块的配置</p>
          </div>
        </div>
        <div class="header-right">
          <span class="glass-tag glass-tag-primary">
            <el-icon><User /></el-icon>
            {{ currentUser?.full_name || currentUser?.username }}
          </span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="config-container animate-slide-in-up">
      <!-- 左侧导航 -->
      <aside class="config-sidebar glass-card">
        <el-menu
          :default-active="activeSection"
          class="config-menu"
          @select="handleSectionChange"
        >
          <el-menu-item index="cmdb">
            <el-icon><DataBoard /></el-icon>
            <span>CMDB配置</span>
          </el-menu-item>
          <el-menu-item index="monitoring">
            <el-icon><Monitor /></el-icon>
            <span>监控配置</span>
          </el-menu-item>
          <el-menu-item index="analysis">
            <el-icon><TrendCharts /></el-icon>
            <span>分析配置</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <!-- 右侧内容区 -->
      <main class="config-content glass-card">
        <component :is="currentComponent" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, User, DataBoard, Monitor, TrendCharts } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import CMDBConfig from '@/components/config/CMDBConfig.vue'
import MonitoringConfig from '@/components/config/MonitoringConfig.vue'
import AnalysisConfig from '@/components/config/AnalysisConfig.vue'

const router = useRouter()
const userStore = useUserStore()

// 当前激活的配置节（从query参数读取，默认为cmdb）
const activeSection = ref(router.currentRoute.value.query.section || 'cmdb')

// 当前用户
const currentUser = computed(() => userStore.user)

// 是否为管理员
const isAdmin = computed(() => {
  const role = userStore.userRole
  return role === 'super_admin' || role === 'admin'
})

// 当前显示的组件
const currentComponent = computed(() => {
  const components = {
    cmdb: CMDBConfig,
    monitoring: MonitoringConfig,
    analysis: AnalysisConfig
  }
  return components[activeSection.value] || CMDBConfig
})

// 切换配置节
const handleSectionChange = (section) => {
  activeSection.value = section
}

// 权限检查
const checkPermission = () => {
  if (!isAdmin.value) {
    ElMessage.warning('权限不足，只有管理员可以访问系统配置')
    router.push('/403')
  }
}

onMounted(() => {
  checkPermission()
})
</script>

<style scoped>
.system-config-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  min-height: 100vh;
  padding: var(--spacing-6);
  background: var(--bg-base);
}

/* 页面头部 */
.page-header {
  animation: slideInUp var(--duration-slow) var(--ease-out);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--bg-container);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 36px;
  color: var(--color-primary);
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  margin: var(--spacing-1) 0 0 0;
  line-height: 1.5;
  opacity: 0.7;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

/* 主容器 */
.config-container {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--spacing-6);
  flex: 1;
  animation: slideInUp var(--duration-slow) var(--ease-out);
  animation-delay: 0.1s;
  animation-fill-mode: both;
  align-items: start;
}

/* 左侧导航 - 增强视觉效果 */
.config-sidebar {
  padding: var(--spacing-5);
  height: fit-content;
  position: sticky;
  top: var(--spacing-6);
  background: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.config-menu {
  border: none;
  background-color: transparent;
}

.config-menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
  padding: var(--spacing-4) var(--spacing-4);
  color: var(--text-primary) !important;
  transition: all var(--transition-base);
  font-weight: 500;
  font-size: var(--font-size-base);
  min-height: 48px;
  height: auto;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  background: transparent;
}

.config-menu :deep(.el-menu-item .el-icon) {
  font-size: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary) !important;
}

.config-menu :deep(.el-menu-item:hover) {
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.08), 
    rgba(59, 130, 246, 0.12)
  ) !important;
  color: var(--color-primary) !important;
  transform: translateX(4px);
}

.config-menu :deep(.el-menu-item:hover .el-icon) {
  color: var(--color-primary) !important;
}

.config-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, 
    #3b82f6, 
    #2563eb
  ) !important;
  color: white !important;
  font-weight: 600;
  box-shadow: 
    0 4px 12px rgba(59, 130, 246, 0.25),
    0 2px 4px rgba(59, 130, 246, 0.15);
  transform: translateX(4px);
}

.config-menu :deep(.el-menu-item.is-active .el-icon) {
  color: white !important;
}

.config-menu :deep(.el-menu-item.is-active span) {
  color: white !important;
}

/* 右侧内容区 - 优化布局 */
.config-content {
  padding: var(--spacing-6);
  min-height: 600px;
  background: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow-x: auto;
  overflow-y: auto;
}

/* 动画 */
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

/* 响应式 */
@media (max-width: 1024px) {
  .config-container {
    grid-template-columns: 220px 1fr;
    gap: var(--spacing-4);
  }
  
  .config-sidebar {
    padding: var(--spacing-4);
  }
}

@media (max-width: 768px) {
  .system-config-page {
    padding: var(--spacing-4);
  }

  .config-container {
    grid-template-columns: 1fr;
    gap: var(--spacing-4);
  }

  .config-sidebar {
    position: static;
    padding: var(--spacing-3);
  }

  .config-menu {
    display: flex;
    overflow-x: auto;
    gap: var(--spacing-2);
    padding-bottom: var(--spacing-2);
  }

  .config-menu :deep(.el-menu-item) {
    flex-shrink: 0;
    margin-right: 0;
    margin-bottom: 0;
    min-width: 140px;
  }
  
  .config-menu :deep(.el-menu-item:hover),
  .config-menu :deep(.el-menu-item.is-active) {
    transform: translateX(0) translateY(-2px);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .config-content {
    padding: var(--spacing-4);
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: var(--font-size-xl);
  }
  
  .header-icon {
    font-size: 28px;
  }
}
</style>
