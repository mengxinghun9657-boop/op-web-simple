import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'
import Dashboard from '@/views/Dashboard.vue'
import Login from '@/views/Login.vue'
import NProgress from 'nprogress'

// 配置 NProgress - 更快的进度条
NProgress.configure({
  easing: 'ease',
  speed: 200,
  showSpinner: false,
  trickleSpeed: 50,
  minimum: 0.4
})

// 预加载常用页面组件
const preloadComponents = () => {
  // 延迟预加载，不阻塞首屏
  setTimeout(() => {
    import('@/views/CMDB.vue')
    import('@/views/alerts/AlertList.vue')
    import('@/views/TaskHistory.vue')
  }, 2000)
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', public: true }
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/errors/403.vue'),
    meta: { title: '无权限', public: true }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: Dashboard, meta: { title: '仪表盘' } },
      { path: 'cmdb', name: 'CMDB', component: () => import('@/views/CMDB.vue'), meta: { title: 'CMDB资源管理' } },
      { path: 'operational', name: 'Operational', component: () => import('@/views/Operational.vue'), meta: { title: '运营分析' } },
      { path: 'resource', name: 'Resource', component: () => import('@/views/Resource.vue'), meta: { title: '资源分析' } },
      { path: 'monitoring', name: 'Monitoring', component: () => import('@/views/MonitoringAnalysis.vue'), meta: { title: '监控分析' } },
      { path: 'monitoring/eip', name: 'EIPMonitoring', component: () => import('@/views/EIPMonitoring.vue'), meta: { title: 'EIP带宽监控' } },
      { path: 'monitoring/bos', name: 'BOSMonitoring', component: () => import('@/views/BOSMonitoring.vue'), meta: { title: 'BOS存储分析' } },
      { path: 'monitoring/bcc', name: 'BCCMonitoring', component: () => import('@/views/BCCMonitoring.vue'), meta: { title: 'BCC实例监控' } },
      { path: 'monitoring/pfs', name: 'PFSMonitoring', component: () => import('@/views/monitoring/PFSMonitoring.vue'), meta: { title: 'PFS监控分析' } },
      { path: 'cluster-fetch', name: 'ClusterDataFetch', component: () => import('@/views/ClusterDataFetch.vue'), meta: { title: '多集群数据获取' } },
      { path: 'task-history', name: 'TaskHistory', component: () => import('@/views/TaskHistory.vue'), meta: { title: '历史任务' } },
      { path: 'admin/users', name: 'UserManagement', component: () => import('@/views/admin/UserManagement.vue'), meta: { title: '用户管理', roles: ['super_admin', 'admin'] } },
      { path: 'admin/audit', name: 'AuditLog', component: () => import('@/views/admin/AuditLog.vue'), meta: { title: '审计日志', roles: ['super_admin', 'admin'] } },
      { path: 'minio', name: 'MinIO', component: () => import('@/views/MinIO.vue'), meta: { title: 'MinIO存储', roles: ['super_admin', 'admin'] } },
      { path: 'system-config', name: 'SystemConfig', component: () => import('@/views/SystemConfig.vue'), meta: { title: '系统配置', roles: ['super_admin', 'admin'] } },
      // 硬件告警管理（静态路由必须在动态路由前面）
      { path: 'alerts', name: 'AlertList', component: () => import('@/views/alerts/AlertList.vue'), meta: { title: '硬件告警管理' } },
      { path: 'alerts/statistics', name: 'AlertStatistics', component: () => import('@/views/alerts/Statistics.vue'), meta: { title: '告警统计分析' } },
      { path: 'alerts/webhooks', name: 'WebhookConfig', component: () => import('@/views/alerts/WebhookConfig.vue'), meta: { title: 'Webhook配置', roles: ['super_admin', 'admin'] } },
      { path: 'alerts/:id', name: 'AlertDetail', component: () => import('@/views/alerts/AlertDetail.vue'), meta: { title: '告警详情' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  NProgress.start()
  document.title = to.meta.title ? `${to.meta.title} - 云资源运维分析平台` : '云资源运维分析平台'

  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')

  // 公开页面直接放行
  if (to.meta.public) {
    // 如果已登录且访问登录页，重定向到首页
    if (token && to.name === 'Login') {
      return next('/')
    }
    return next()
  }

  // 需要认证但未登录
  if (!token) {
    return next('/login')
  }

  // 角色权限校验
  if (to.meta.roles?.length && user) {
    if (!to.meta.roles.includes(user.role)) {
      return next('/403')
    }
  }

  next()
})

router.afterEach(() => NProgress.done())

// 首次加载完成后预加载常用组件
router.isReady().then(() => {
  preloadComponents()
})

export default router
