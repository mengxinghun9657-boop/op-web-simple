import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'
import Dashboard from '@/views/Dashboard.vue'
import Login from '@/views/Login.vue'
import NProgress from 'nprogress'

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
      { path: 'cluster-fetch', name: 'ClusterDataFetch', component: () => import('@/views/ClusterDataFetch.vue'), meta: { title: '多集群数据获取' } },
      { path: 'task-history', name: 'TaskHistory', component: () => import('@/views/TaskHistory.vue'), meta: { title: '历史任务' } },
      { path: 'admin/users', name: 'UserManagement', component: () => import('@/views/admin/UserManagement.vue'), meta: { title: '用户管理', roles: ['super_admin', 'admin'] } },
      { path: 'admin/audit', name: 'AuditLog', component: () => import('@/views/admin/AuditLog.vue'), meta: { title: '审计日志', roles: ['super_admin', 'admin'] } },
      { path: 'minio', name: 'MinIO', component: () => import('@/views/MinIO.vue'), meta: { title: 'MinIO存储', roles: ['super_admin', 'admin'] } },
      { path: 'ai-query', name: 'AIIntelligentQuery', component: () => import('@/views/AIIntelligentQuery.vue'), meta: { title: 'AI 智能查询' } },
      { path: 'knowledge-management', name: 'KnowledgeManagement', component: () => import('@/views/KnowledgeManagement.vue'), meta: { title: '知识库管理', roles: ['super_admin'] } },
      { path: 'report-browser', name: 'ReportIndexBrowser', component: () => import('@/views/ReportIndexBrowser.vue'), meta: { title: '报告索引浏览' } },
      { path: 'system-config', name: 'SystemConfig', component: () => import('@/views/SystemConfig.vue'), meta: { title: '系统配置', roles: ['super_admin', 'admin'] } },
      // 路由规则管理
      { path: 'routing/suggestions/review', name: 'SuggestionReview', component: () => import('@/views/routing/SuggestionReview.vue'), meta: { title: '规则建议审核', roles: ['super_admin', 'admin'] } },
      { path: 'routing/rules', name: 'RoutingRules', component: () => import('@/views/routing/RoutingRules.vue'), meta: { title: '路由规则管理', roles: ['super_admin', 'admin'] } },
      { path: 'routing/statistics', name: 'RoutingStatistics', component: () => import('@/views/routing/RoutingStatistics.vue'), meta: { title: '路由统计' } },
      // 硬件告警管理
      { path: 'alerts', name: 'AlertList', component: () => import('@/views/alerts/AlertList.vue'), meta: { title: '硬件告警管理' } },
      { path: 'alerts/:id', name: 'AlertDetail', component: () => import('@/views/alerts/AlertDetail.vue'), meta: { title: '告警详情' } },
      { path: 'alerts/statistics', name: 'AlertStatistics', component: () => import('@/views/alerts/Statistics.vue'), meta: { title: '告警统计分析' } },
      { path: 'alerts/webhooks', name: 'WebhookConfig', component: () => import('@/views/alerts/WebhookConfig.vue'), meta: { title: 'Webhook配置', roles: ['super_admin', 'admin'] } }
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
  
  console.log('路由守卫:', { to: to.path, from: from.path, token: !!token, user: user?.username })
  
  // 公开页面直接放行
  if (to.meta.public) {
    // 如果已登录且访问登录页，重定向到首页
    if (token && to.name === 'Login') {
      console.log('已登录，从登录页重定向到首页')
      return next('/')
    }
    return next()
  }
  
  // 需要认证但未登录
  if (!token) {
    console.log('未登录，重定向到登录页')
    return next('/login')
  }
  
  // 角色权限校验
  if (to.meta.roles?.length && user) {
    if (!to.meta.roles.includes(user.role)) {
      console.log('权限不足，重定向到403')
      return next('/403')
    }
  }
  
  console.log('路由守卫通过，继续导航')
  next()
})

router.afterEach(() => NProgress.done())

export default router
