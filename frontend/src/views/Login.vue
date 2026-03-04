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
        <Card class="login-card">
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
        </Card>
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
import { Card } from '@/components/common'

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
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // userStore.login 内部已使用 users.js 的 login() 函数
        await userStore.login(form)
        ElMessage.success('登录成功')
        const redirect = route.query.redirect || '/'
        router.push(redirect)
      } catch (error) {
        // 错误已由拦截器处理
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  inset: 0;
  background-image: url('data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.03"%3E%3Ccircle cx="30" cy="30" r="1"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E');
  opacity: 0.5;
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  height: 600px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border-radius: var(--radius-2xl);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* 左侧品牌区域 */
.login-brand {
  flex: 1;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12);
  position: relative;
  overflow: hidden;
}

.login-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
}

.brand-icon {
  width: 96px;
  height: 96px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-8);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  margin: 0 0 var(--spacing-4);
  color: white;
}

.brand-subtitle {
  font-size: var(--font-size-lg);
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 var(--spacing-8);
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  text-align: left;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--font-size-base);
}

.feature-dot {
  width: 8px;
  height: 8px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  flex-shrink: 0;
}

/* 右侧登录表单 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-8);
  background: var(--bg-container);
}

.login-card {
  width: 100%;
  max-width: 400px;
  box-shadow: none;
  border: none;
}

.login-header {
  margin-bottom: var(--spacing-8);
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2);
}

.login-subtitle {
  font-size: var(--font-size-base);
  color: var(--text-tertiary);
  margin: 0;
}

.login-input :deep(.el-input__wrapper) {
  height: 48px;
  border-radius: var(--radius-lg);
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-8);
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: 500;
  border-radius: var(--radius-lg);
}

.login-footer {
  margin-top: var(--spacing-8);
  text-align: center;
}

.login-footer p {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    height: auto;
    max-width: 90%;
  }
  
  .login-brand {
    padding: var(--spacing-8);
  }
  
  .brand-title {
    font-size: 28px;
  }
  
  .brand-features {
    display: none;
  }
  
  .login-form-wrapper {
    padding: var(--spacing-6);
  }
}
</style>
