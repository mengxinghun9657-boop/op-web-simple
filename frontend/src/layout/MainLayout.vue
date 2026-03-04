<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': isCollapsed }">
    <!-- 侧边导航 - 玻璃拟态 -->
    <aside class="sidebar glass-panel" :class="{ collapsed: isCollapsed }">
      <!-- Logo -->
      <div class="sidebar-header">
        <div class="logo-icon">
          <el-icon :size="20"><DataAnalysis /></el-icon>
        </div>
        <transition name="fade-text">
          <span v-if="!isCollapsed" class="logo-text">云资源运维分析平台</span>
        </transition>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <template v-for="item in menuItems" :key="item.name">
          <!-- 外部链接 -->
          <div
            v-if="item.external"
            @click="openExternal(item.path)"
            class="nav-item"
            :class="{ 'nav-item-collapsed': isCollapsed }"
          >
            <div class="nav-item-icon">
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
            </div>
            <transition name="fade-text">
              <span v-if="!isCollapsed" class="nav-label">{{ item.name }}</span>
            </transition>
            <el-icon v-if="!isCollapsed" :size="12" class="external-icon"><TopRight /></el-icon>
            <!-- 折叠时的 Tooltip -->
            <el-tooltip v-if="isCollapsed" :content="item.name" placement="right" :show-after="200">
              <span class="nav-tooltip-trigger"></span>
            </el-tooltip>
          </div>

          <!-- 子菜单组 -->
          <div v-else-if="item.children" class="nav-group">
            <div 
              class="nav-group-title"
              :class="{ 'nav-item-collapsed': isCollapsed }"
              @click="toggleGroup(item.name)"
            >
              <div class="nav-item-icon">
                <el-icon :size="18"><component :is="item.icon" /></el-icon>
              </div>
              <transition name="fade-text">
                <span v-if="!isCollapsed" class="nav-label">{{ item.name }}</span>
              </transition>
              <el-icon 
                v-if="!isCollapsed" 
                :size="14" 
                class="expand-icon"
                :class="{ 'expanded': expandedGroups.includes(item.name) }"
              >
                <ArrowRight />
              </el-icon>
              <!-- 折叠时的 Tooltip -->
              <el-tooltip v-if="isCollapsed" :content="item.name" placement="right" :show-after="200">
                <span class="nav-tooltip-trigger"></span>
              </el-tooltip>
            </div>
            
            <!-- 子菜单项 -->
            <transition name="slide-fade">
              <div v-show="!isCollapsed && expandedGroups.includes(item.name)" class="nav-group-children">
                <template v-for="child in item.children" :key="child.path">
                  <router-link :to="child.path" custom v-slot="{ navigate, isActive }">
                    <div
                      @click="navigate"
                      class="nav-item nav-item-child"
                      :class="{ active: isActive }"
                    >
                      <div class="nav-item-icon" :class="{ 'icon-active': isActive }">
                        <el-icon :size="16"><component :is="child.icon" /></el-icon>
                      </div>
                      <span class="nav-label">{{ child.name }}</span>
                    </div>
                  </router-link>
                </template>
              </div>
            </transition>
          </div>

          <!-- 普通内部路由 -->
          <router-link v-else :to="item.path" custom v-slot="{ navigate, isActive }">
            <div
              @click="navigate"
              class="nav-item"
              :class="{ 
                active: isActive,
                'nav-item-collapsed': isCollapsed
              }"
            >
              <div class="nav-item-icon" :class="{ 'icon-active': isActive }">
                <el-icon :size="18"><component :is="item.icon" /></el-icon>
              </div>
              <transition name="fade-text">
                <span v-if="!isCollapsed" class="nav-label">{{ item.name }}</span>
              </transition>
              <!-- 折叠时的 Tooltip -->
              <el-tooltip v-if="isCollapsed" :content="item.name" placement="right" :show-after="200">
                <span class="nav-tooltip-trigger"></span>
              </el-tooltip>
            </div>
          </router-link>
        </template>
      </nav>

      <!-- 折叠按钮 -->
      <div class="sidebar-footer" @click="toggleSidebar">
        <el-icon :size="16"><component :is="isCollapsed ? 'Expand' : 'Fold'" /></el-icon>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-wrapper">
      <!-- 顶部栏 - 玻璃拟态 -->
      <header class="header-bar glass-header">
        <div class="header-left">
          <!-- 面包屑导航 -->
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRouteName !== '仪表盘'">
              {{ currentRouteName }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 主题切换 -->
          <el-tooltip :content="isDark ? '切换浅色主题' : '切换深色主题'" placement="bottom">
            <div class="header-icon-btn" @click="toggleTheme">
              <el-icon :size="18"><component :is="isDark ? 'Sunny' : 'Moon'" /></el-icon>
            </div>
          </el-tooltip>

          <!-- 通知按钮 -->
          <el-tooltip content="通知" placement="bottom">
            <div class="header-icon-btn">
              <el-badge :value="0" :hidden="true">
                <el-icon :size="18"><Bell /></el-icon>
              </el-badge>
            </div>
          </el-tooltip>

          <!-- 用户信息 -->
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-info glass-card-light">
              <el-avatar :size="32" class="user-avatar">
                <el-icon :size="16"><User /></el-icon>
              </el-avatar>
              <div class="user-detail">
                <span class="user-name">{{ userStore.user?.username || '管理员' }}</span>
                <span class="user-role">{{ roleLabels[userStore.user?.role] || '系统管理员' }}</span>
              </div>
              <el-icon :size="12" class="dropdown-arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="user-dropdown-menu">
                <el-dropdown-item command="profile" disabled>
                  <el-icon><User /></el-icon>
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <div class="main-content">
        <router-view v-slot="{ Component, route }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  MagicStick, ArrowDown, SwitchButton, TopRight, FolderOpened, Bell,
  DataAnalysis, Odometer, Grid, TrendCharts, Cpu, Monitor, Connection, 
  Clock, User, Document, Link, Expand, Fold, Sunny, Moon, Setting,
  ChatDotRound, Collection, DataLine, ArrowRight
} from '@element-plus/icons-vue'
import { API_DOCS_URL } from '@/utils/config'
import { useUserStore } from '@/stores/user'
import { themeManager } from '@/utils/themeManager'

const isCollapsed = ref(false)
const isDark = ref(true)
const expandedGroups = ref(['硬件告警', '分析报告', '路由管理', '系统管理'])
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roleLabels = {
  super_admin: '超级管理员',
  admin: '管理员',
  analyst: '分析师',
  viewer: '查看者'
}

// 切换分组展开/收起
const toggleGroup = (groupName) => {
  const index = expandedGroups.value.indexOf(groupName)
  if (index > -1) {
    expandedGroups.value.splice(index, 1)
  } else {
    expandedGroups.value.push(groupName)
  }
  // 保存状态到本地存储
  localStorage.setItem('sidebar-expanded-groups', JSON.stringify(expandedGroups.value))
}

// 所有菜单项定义(包含权限要求)
const allMenuItems = [
  { name: '仪表盘', path: '/', icon: 'Odometer' },
  { name: 'CMDB', path: '/cmdb', icon: 'Grid' },
  { name: 'AI 智能查询', path: '/ai-query', icon: 'ChatDotRound' },
  
  // 硬件告警管理组
  { 
    name: '硬件告警', 
    icon: 'Bell',
    children: [
      { name: '告警列表', path: '/alerts', icon: 'Bell' },
      { name: '告警统计', path: '/alerts/statistics', icon: 'DataLine' },
      { name: 'Webhook配置', path: '/alerts/webhooks', icon: 'Connection', roles: ['super_admin', 'admin'] },
    ]
  },
  
  // 分析报告组
  { 
    name: '分析报告', 
    icon: 'TrendCharts',
    children: [
      { name: '运营分析', path: '/operational', icon: 'TrendCharts' },
      { name: '资源分析', path: '/resource', icon: 'Cpu' },
      { name: '监控分析', path: '/monitoring', icon: 'Monitor' },
      { name: '报告索引', path: '/report-browser', icon: 'FolderOpened' },
    ]
  },
  
  // 路由管理组
  { 
    name: '路由管理', 
    icon: 'Connection',
    roles: ['super_admin', 'admin', 'analyst'],
    children: [
      { name: '路由规则', path: '/routing/rules', icon: 'Connection', roles: ['super_admin', 'admin'] },
      { name: '路由统计', path: '/routing/statistics', icon: 'DataLine', roles: ['super_admin', 'admin', 'analyst'] },
      { name: '规则审核', path: '/routing/suggestions/review', icon: 'Document', roles: ['super_admin', 'admin'] },
    ]
  },
  
  { name: '知识库管理', path: '/knowledge-management', icon: 'Collection', roles: ['super_admin'] },
  { name: '历史任务', path: '/task-history', icon: 'Clock' },
  
  // 系统管理组
  { 
    name: '系统管理', 
    icon: 'Setting',
    roles: ['super_admin', 'admin'],
    children: [
      { name: '系统配置', path: '/system-config', icon: 'Setting', roles: ['super_admin', 'admin'] },
      { name: '用户管理', path: '/admin/users', icon: 'User', roles: ['super_admin', 'admin'] },
      { name: '审计日志', path: '/admin/audit', icon: 'Document', roles: ['super_admin', 'admin'] },
      { name: 'MinIO', path: '/minio', icon: 'FolderOpened', roles: ['super_admin', 'admin'], external: false },
    ]
  },
  
  { name: 'API 文档', path: API_DOCS_URL, icon: 'Link', external: true },
]

// 根据用户权限过滤菜单项
const menuItems = computed(() => {
  const currentUser = userStore.user
  if (!currentUser) return allMenuItems.filter(item => !item.roles)
  
  return allMenuItems.filter(item => {
    // 没有roles限制的菜单项对所有人可见
    if (!item.roles || item.roles.length === 0) return true
    // 检查用户角色是否在允许的角色列表中
    return item.roles.includes(currentUser.role)
  })
})

// 初始化主题
onMounted(() => {
  isDark.value = themeManager.getTheme() === 'dark'
})

const openExternal = (url) => window.open(url, '_blank')

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
  // 保存侧边栏状态
  localStorage.setItem('sidebar-collapsed', isCollapsed.value)
}

const toggleTheme = () => {
  const newTheme = isDark.value ? 'light' : 'dark'
  themeManager.setTheme(newTheme)
  isDark.value = newTheme === 'dark'
  ElMessage({
    message: isDark.value ? '已切换深色主题' : '已切换浅色主题',
    type: 'success',
    duration: 1500,
    showClose: false
  })
}

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }
}

const currentRouteName = computed(() => route.meta.title || '仪表盘')

// 恢复侧边栏状态
onMounted(() => {
  const savedState = localStorage.getItem('sidebar-collapsed')
  if (savedState !== null) {
    isCollapsed.value = savedState === 'true'
  }
  
  // 恢复分组展开状态
  const savedGroups = localStorage.getItem('sidebar-expanded-groups')
  if (savedGroups) {
    try {
      expandedGroups.value = JSON.parse(savedGroups)
    } catch (e) {
      console.error('恢复分组状态失败:', e)
    }
  }
})
</script>

<style scoped>
/* ==================== 布局容器 ==================== */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-base);
}

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: 240px;
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur-strong));
  -webkit-backdrop-filter: blur(var(--glass-blur-strong));
  border-right: 1px solid var(--glass-border);
  transition: width var(--duration-normal) var(--ease-out);
  z-index: var(--z-fixed);
}

.sidebar.collapsed {
  width: 72px;
}

/* 侧边栏头部 */
.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-4);
  border-bottom: 1px solid var(--glass-border);
  gap: var(--spacing-3);
  flex-shrink: 0;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: var(--shadow-glow-primary);
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
}

/* 导航菜单 */
.sidebar-nav {
  flex: 1;
  padding: var(--spacing-3);
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-3);
  margin-bottom: var(--spacing-1);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  gap: var(--spacing-3);
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  color: #fff;
  box-shadow: var(--shadow-glow-primary);
}

.nav-item.active .nav-item-icon {
  color: #fff;
}

.nav-item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-hover);
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out);
}

.nav-item:hover .nav-item-icon {
  background: var(--bg-active);
}

.nav-item.active .nav-item-icon {
  background: rgba(255, 255, 255, 0.2);
}

.nav-item-collapsed {
  justify-content: center;
  padding: var(--spacing-3);
}

.nav-item-collapsed .nav-item-icon {
  width: 40px;
  height: 40px;
}

.nav-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.external-icon {
  margin-left: auto;
  opacity: 0.5;
}

.nav-tooltip-trigger {
  position: absolute;
  inset: 0;
}

/* 菜单分组 */
.nav-group {
  margin-bottom: var(--spacing-1);
}

.nav-group-title {
  position: relative;
  display: flex;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-3);
  margin-bottom: var(--spacing-1);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  gap: var(--spacing-3);
  font-weight: var(--font-weight-semibold);
}

.nav-group-title:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.expand-icon {
  margin-left: auto;
  transition: transform var(--duration-fast) var(--ease-out);
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.nav-group-children {
  padding-left: var(--spacing-2);
  overflow: hidden;
}

.nav-item-child {
  padding-left: var(--spacing-6);
}

.nav-item-child .nav-item-icon {
  width: 32px;
  height: 32px;
}

/* 子菜单展开/收起动画 */
.slide-fade-enter-active {
  transition: all var(--duration-normal) var(--ease-out);
}

.slide-fade-leave-active {
  transition: all var(--duration-fast) var(--ease-in);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: var(--spacing-4);
  border-top: 1px solid var(--glass-border);
  display: flex;
  justify-content: center;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all var(--duration-fast) var(--ease-out);
  flex-shrink: 0;
}

.sidebar-footer:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

/* ==================== 主内容区 ==================== */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-base);
  overflow: hidden;
}

/* 顶部栏 */
.header-bar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-6);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--glass-border);
  flex-shrink: 0;
  z-index: var(--z-sticky);
}

.header-left {
  display: flex;
  align-items: center;
}

/* 面包屑样式覆盖 */
.header-left :deep(.el-breadcrumb) {
  font-size: var(--font-size-sm);
}

.header-left :deep(.el-breadcrumb__inner) {
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

.header-left :deep(.el-breadcrumb__inner.is-link:hover) {
  color: var(--color-primary);
}

.header-left :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.header-icon-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  background: var(--glass-bg-light);
  border: 1px solid transparent;
}

.user-info:hover {
  background: var(--bg-hover);
  border-color: var(--glass-border);
}

.user-avatar {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));
  flex-shrink: 0;
}

.user-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.dropdown-arrow {
  color: var(--text-tertiary);
  transition: transform var(--duration-fast) var(--ease-out);
}

.user-info:hover .dropdown-arrow {
  transform: rotate(180deg);
}

/* 下拉菜单样式 */
.user-dropdown-menu {
  min-width: 160px;
}

/* 内容区 */
.main-content {
  flex: 1;
  padding: var(--spacing-6);
  overflow: auto;
  scroll-behavior: smooth;
}

/* ==================== 过渡动画 ==================== */

/* 文本淡入淡出 */
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity var(--duration-fast) var(--ease-out);
}

.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}

/* 页面切换动画 */
.page-fade-enter-active {
  transition: all var(--duration-normal) var(--ease-out);
}

.page-fade-leave-active {
  transition: all var(--duration-fast) var(--ease-in);
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ==================== 滚动条 ==================== */
.sidebar-nav::-webkit-scrollbar,
.main-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-nav::-webkit-scrollbar-track,
.main-content::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
}

.sidebar-nav::-webkit-scrollbar-thumb,
.main-content::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 3px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover,
.main-content::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* ==================== 响应式适配 ==================== */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    transform: translateX(-100%);
    z-index: var(--z-modal);
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    width: 72px;
    transform: translateX(0);
  }

  .user-detail {
    display: none;
  }

  .main-content {
    padding: var(--spacing-4);
  }
}

/* ==================== 减少动画偏好 ==================== */
@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .nav-item,
  .header-icon-btn,
  .user-info {
    transition: none;
  }

  .page-fade-enter-active,
  .page-fade-leave-active,
  .fade-text-enter-active,
  .fade-text-leave-active {
    transition: none;
  }
}
</style>
