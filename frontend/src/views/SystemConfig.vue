<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Setting /></el-icon>
          </div>
          系统配置管理
        </div>
        <div class="page-subtitle">集中管理CMDB、监控、分析等模块的配置</div>
      </div>
      <div class="page-actions">
        <span class="user-tag">
          <el-icon><User /></el-icon>
          {{ currentUser?.full_name || currentUser?.username }}
        </span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="config-container">
      <!-- 左侧导航 -->
      <aside class="config-sidebar">
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
            <span>监控 & 分析配置</span>
          </el-menu-item>
          <el-menu-item index="prometheus_runtime">
            <el-icon><Connection /></el-icon>
            <span>Prometheus配置</span>
          </el-menu-item>
          <el-menu-item index="pfs">
            <el-icon><Histogram /></el-icon>
            <span>PFS配置</span>
          </el-menu-item>
          <el-menu-item index="icafe">
            <el-icon><Postcard /></el-icon>
            <span>iCafe配置</span>
          </el-menu-item>
          <el-menu-item index="bce_sync">
            <el-icon><Connection /></el-icon>
            <span>BCE同步配置</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <!-- 右侧内容区 -->
      <main class="config-content">
        <component :is="currentComponent" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, User, DataBoard, Monitor, Histogram, Postcard, Connection } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import CMDBConfig from '@/components/config/CMDBConfig.vue'
import MonitoringConfig from '@/components/config/MonitoringConfig.vue'
import PrometheusRuntimeConfig from '@/components/config/PrometheusRuntimeConfig.vue'
import PFSConfig from '@/components/config/PFSConfig.vue'
import APIServerConfig from '@/components/config/APIServerConfig.vue'
import ICafeConfig from '@/components/config/ICafeConfig.vue'
import BCESyncConfig from '@/components/config/BCESyncConfig.vue'

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
    prometheus_runtime: PrometheusRuntimeConfig,
    pfs: PFSConfig,
    apiserver: APIServerConfig,
    icafe: ICafeConfig,
    bce_sync: BCESyncConfig
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
/* 用户标签 */
.user-tag {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: rgba(26, 115, 232, 0.1);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--primary);
  font-weight: 500;
}

/* 主容器 */
.config-container {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-6);
  align-items: start;
}

/* 左侧导航 */
.config-sidebar {
  padding: var(--space-5);
  height: fit-content;
  position: sticky;
  top: var(--space-6);
  background: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.config-menu {
  border: none;
  background-color: transparent;
}

.config-menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
  padding: var(--space-4);
  color: var(--text-primary) !important;
  transition: all var(--transition-normal);
  font-weight: 500;
  font-size: var(--text-base);
  min-height: 48px;
  height: auto;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: var(--space-3);
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
  background: rgba(26, 115, 232, 0.1) !important;
  color: var(--primary) !important;
}

.config-menu :deep(.el-menu-item:hover .el-icon) {
  color: var(--primary) !important;
}

.config-menu :deep(.el-menu-item.is-active),
.config-menu :deep(.el-menu-item.is-active:hover),
.config-menu :deep(.el-menu-item.is-active:focus) {
  background: linear-gradient(135deg, var(--primary), #1557c0) !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(26, 115, 232, 0.25);
}

.config-menu :deep(.el-menu-item.is-active .el-icon),
.config-menu :deep(.el-menu-item.is-active:hover .el-icon) {
  color: #ffffff !important;
}

.config-menu :deep(.el-menu-item.is-active span),
.config-menu :deep(.el-menu-item.is-active:hover span) {
  color: #ffffff !important;
}

/* 确保激活状态下所有文字都是白色 */
.config-menu :deep(.el-menu-item.is-active *) {
  color: #ffffff !important;
}

/* 右侧内容区 */
.config-content {
  padding: var(--space-6);
  min-height: 600px;
  background: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  overflow-x: auto;
  overflow-y: auto;
}

/* 响应式 */
@media (max-width: 1024px) {
  .config-container {
    grid-template-columns: 220px 1fr;
    gap: var(--space-4);
  }

  .config-sidebar {
    padding: var(--space-4);
  }
}

@media (max-width: 768px) {
  .config-container {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .config-sidebar {
    position: static;
    padding: var(--space-3);
  }

  .config-menu {
    display: flex;
    overflow-x: auto;
    gap: var(--space-2);
    padding-bottom: var(--space-2);
  }

  .config-menu :deep(.el-menu-item) {
    flex-shrink: 0;
    margin-right: 0;
    margin-bottom: 0;
    min-width: 140px;
  }

  .config-menu :deep(.el-menu-item:hover),
  .config-menu :deep(.el-menu-item.is-active) {
    /* 移动端不使用 transform */
  }

  .config-content {
    padding: var(--space-4);
  }
}
</style>
