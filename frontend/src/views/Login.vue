<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-background"></div>

    <div class="login-container">
      <!-- 左侧品牌区域 -->
      <div class="login-brand">
        <div class="brand-content">
          <div class="brand-icon">
            <el-icon :size="48"><DataAnalysis /></el-icon>
          </div>
          <h1 class="brand-title">云资源运维分析平台</h1>
          <p class="brand-subtitle">企业级云资源监控与智能分析系统</p>
          <div class="brand-features">
            <div class="brand-feature">
              <div class="feature-dot"></div>
              <span>实时资源监控与告警</span>
            </div>
            <div class="brand-feature">
              <div class="feature-dot"></div>
              <span>智能运营数据分析</span>
            </div>
            <div class="brand-feature">
              <div class="feature-dot"></div>
              <span>企业级安全防护</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="login-form-wrapper">
        <div class="login-card">
          <div class="login-header">
            <h2 class="login-title">系统登录</h2>
            <p class="login-subtitle">请输入您的账号信息</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
            <el-form-item prop="username">
              <el-input 
                v-model="form.username" 
                placeholder="用户名 / 邮箱" 
                prefix-icon="User"
                class="login-input"
                autocomplete="username"
                name="username"
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input 
                v-model="form.password" 
                type="password" 
                placeholder="密码" 
                prefix-icon="Lock"
                show-password
                class="login-input"
                autocomplete="current-password"
                name="password"
              />
            </el-form-item>

            <div class="login-options">
              <el-checkbox v-model="form.remember" label="记住登录状态" />
            </div>

            <el-button 
              type="primary" 
              class="login-button" 
              :loading="loading"
              @click="handleLogin"
            >
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form>

          <div class="login-footer">
            <p>请使用管理员分配的账号登录系统</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  remember: false
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  try {
    // 表单验证
    const valid = await formRef.value.validate()
    if (!valid) return
  } catch (error) {
    // 表单验证失败，不显示"登录失败"提示
    // Element Plus 会自动显示字段级别的验证错误
    return
  }
  
  // 表单验证通过，开始登录
  loading.value = true

  try {
    // userStore.login 内部已使用 users.js 的 login() 函数
    const result = await userStore.login(form)
    
    ElMessage.success('登录成功')
    
    // 确保跳转在 ElMessage 之后执行
    const redirect = route.query.redirect || '/'
    
    // 使用 router.replace 避免导航重复错误
    router.replace(redirect).catch(err => {
      // 忽略导航重复或取消的错误
      if (err.name !== 'NavigationDuplicated' && err.name !== 'NavigationCancelled') {
        // Navigation error
      }
    })
  } catch (error) {
    // 只在真正的登录错误时显示错误消息
    if (!error.name || (error.name !== 'NavigationDuplicated' && error.name !== 'NavigationCancelled')) {
      ElMessage.error(error.message || '登录失败，请重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/**
 * 登录页面 - Google Blue 浅色主题
 * 参考 Google Sign-in 和 Linear 登录页设计
 */
.login-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 浅色背景，使用统一设计系统变量 */
  background: var(--bg-secondary);
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  inset: 0;
  /* 浅色点阵背景 */
  background-image: url('data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%231a73e8" fill-opacity="0.03"%3E%3Ccircle cx="30" cy="30" r="1"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E');
  opacity: 1;
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  min-height: 560px;
  background: var(--bg-primary);
  border-radius: var(--radius-2xl);
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* 左侧品牌区域 - Google Blue 渐变 */
.login-brand {
  flex: 1;
  background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-primary-700) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-12);
  position: relative;
  overflow: hidden;
}

.login-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255, 255, 255, 0.15) 0%, transparent 50%);
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: #ffffff;
}

.brand-icon {
  width: 88px;
  height: 88px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-6);
  box-shadow: var(--shadow-md);
}

.brand-title {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  margin: 0 0 var(--space-3);
  color: #ffffff;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  font-size: var(--text-base);
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 var(--space-8);
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  text-align: left;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--text-sm);
}

.feature-dot {
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  flex-shrink: 0;
}

/* 右侧登录表单 - 纯白背景 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  background: var(--bg-primary);
}

.login-card {
  width: 100%;
  max-width: 360px;
}

.login-header {
  margin-bottom: var(--space-8);
  text-align: center;
}

.login-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0 0 var(--space-2);
}

.login-subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}

/* 输入框样式 */
.login-input :deep(.el-input__wrapper) {
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--bg-primary) !important;
  border: 1px solid var(--border-primary) !important;
  box-shadow: none !important;
  transition: border-color var(--duration-normal) var(--ease-standard) !important;
}

.login-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-neutral-400) !important;
}

.login-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary-600) !important;
  box-shadow: var(--shadow-glow-primary) !important;
}

.login-input :deep(.el-input__inner) {
  color: var(--text-primary) !important;
  font-size: var(--text-base) !important;
}

.login-input :deep(.el-input__inner::placeholder) {
  color: var(--text-disabled) !important;
}

.login-input :deep(.el-input__prefix) {
  color: var(--text-tertiary) !important;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.login-options :deep(.el-checkbox__label) {
  color: var(--text-secondary) !important;
  font-size: var(--text-sm) !important;
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-md);
}

.login-footer {
  margin-top: var(--space-8);
  text-align: center;
}

.login-footer p {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    min-height: auto;
    max-width: 90%;
    margin: var(--space-4);
  }

  .login-brand {
    padding: var(--space-8);
  }

  .brand-title {
    font-size: var(--text-2xl);
  }

  .brand-features {
    display: none;
  }

  .login-form-wrapper {
    padding: var(--space-6);
  }
}
</style>
