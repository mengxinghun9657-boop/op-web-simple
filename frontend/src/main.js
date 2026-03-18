import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router/index'
import './router/permission'
import permissionDirective from './directives/permission'

// 设计系统样式 - 按顺序导入
// 1. 统一设计系统（必须最先导入，定义所有基础变量）
import './styles/unified-design-system.css'
// 2. 组件样式（基于统一设计系统）
import './styles/google-components.css'   // Google Blue 通用组件样式
import './styles/google-pages.css'        // Google Blue 页面统一样式
import './styles/bento-grid.css'          // Bento 卡片布局样式
import './styles/monitoring-pages.css'    // 监控页面样式
import './styles/dialog-system.css'       // 统一弹窗设计系统
import './styles/main-layout-google.css'  // MainLayout Google 风格
// 3. 主样式（覆盖 Element Plus，最后导入）
import './assets/styles/main.css'

// 主题管理器
import { themeManager } from './utils/themeManager'
// 光效管理器
import glowEffectManager from './utils/glowEffectManager'
// 错误处理
import errorHandler from './utils/errorHandler'
import ErrorToast from './components/common/ErrorToast.vue'

const app = createApp(App)

// 全局错误处理
app.config.errorHandler = errorHandler.globalErrorHandler

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.directive('permission', permissionDirective)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// 注册全局错误提示组件
app.component('ErrorToast', ErrorToast)

app.mount('#app')

// 初始化主题系统
themeManager.init()

// 初始化光效系统
glowEffectManager.initGlowEffects()

// 初始化全局错误处理
errorHandler.setupGlobalErrorHandlers()

// 配置 axios 拦截器
import axios from './utils/axios'
errorHandler.setupAxiosInterceptors(axios)