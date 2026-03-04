import router from './index'
import { useUserStore } from '@/stores/user'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

const whiteList = ['/login', '/register', '/forgot-password']

router.beforeEach((to, from, next) => {
  NProgress.start()
  const userStore = useUserStore()
  
  if (userStore.isAuthenticated) {
    if (to.path === '/login') {
      next({ path: '/' })
      NProgress.done()
    } else {
      // 检查角色权限
      const requiredRole = to.meta.roles
      if (requiredRole && requiredRole.length > 0) {
        if (!requiredRole.includes(userStore.userRole)) {
          next('/403')
        } else {
          next()
        }
      } else {
        next()
      }
    }
  } else {
    if (whiteList.indexOf(to.path) !== -1) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
      NProgress.done()
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})
