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
import './styles/design-tokens.css'      // 设计令牌（CSS变量）
import './styles/glassmorphism.css'      // 玻璃拟态组件
import './styles/bento-grid.css'         // Bento Grid 布局
import './styles/monitoring-pages.css'   // 监控页面样式
import './styles/feedback-system.css'    // 反馈系统样式
import './styles/enterprise-effects.css' // 企业风格特效
import './styles/dialog-system.css'      // 统一弹窗设计系统
import './assets/styles/main.css'        // 主样式（包含所有主题修复，覆盖 Element Plus）

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