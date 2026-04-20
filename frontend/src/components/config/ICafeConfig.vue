<template>
  <div class="icafe-config">
    <!-- 主配置卡片 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #7c3aed, #4f46e5);">
            <el-icon :size="16"><Postcard /></el-icon>
          </div>
          iCafe 连接配置
        </div>
        <el-button type="primary" @click="handleSave" :loading="saving" :disabled="!isAdmin">
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
      </div>
      <div class="bento-card-body">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          class="config-form"
          @submit.prevent="handleSave"
        >
          <el-form-item label="API 地址" prop="api_url">
            <el-input v-model="form.api_url" placeholder="http://icafeapi.baidu-int.com/api/v2" :disabled="!isAdmin" />
            <div class="form-tip">默认使用内网 API 地址：http://icafeapi.baidu-int.com/api/v2</div>
          </el-form-item>

          <el-form-item label="空间 ID" prop="space_id">
            <el-input v-model="form.space_id" placeholder="iCafe 空间标识，如 HMLCC" :disabled="!isAdmin" />
            <div class="form-tip">长安 HMLCC 售后服务支持空间 ID：HMLCC</div>
          </el-form-item>

          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入 iCafe 用户名，如 v_zhangxingpei" :disabled="!isAdmin" maxlength="50" />
            <div class="form-tip">建议使用虚拟账户</div>
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入 iCafe 密码"
              show-password
              :disabled="!isAdmin"
              maxlength="200"
            />
            <div class="form-tip">建议使用虚拟密码，可通过 iCafe 服务号获取</div>
          </el-form-item>

          <el-form-item label="测试连接">
            <el-button @click="handleTestConnection" :loading="testing" :disabled="!isAdmin">
              <el-icon><Connection /></el-icon>
              测试连接
            </el-button>
            <span v-if="testResult" :class="testResultClass" class="test-result-text">
              {{ testResult }}
            </span>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 说明卡片 -->
    <div class="info-cards">
      <div class="bento-card info-card">
        <div class="bento-card-header">
          <div class="bento-card-title">
            <div class="bento-card-title-icon">
              <el-icon :size="16"><InfoFilled /></el-icon>
            </div>
            使用说明
          </div>
        </div>
        <div class="bento-card-body">
          <ul class="info-list">
            <li>iCafe 是百度内部的项目管理平台，用于创建和跟踪任务卡片</li>
            <li>配置完成后，运营分析模块可通过 API 直接查询 iCafe 数据</li>
            <li>卡片数据支持按负责人、状态、类型、标签等维度筛选分析</li>
            <li>建议使用虚拟账户，避免个人账户权限变更影响数据采集</li>
          </ul>
        </div>
      </div>

      <div class="bento-card info-card">
        <div class="bento-card-header">
          <div class="bento-card-title">
            <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #059669, #047857);">
              <el-icon :size="16"><Link /></el-icon>
            </div>
            快速链接
          </div>
        </div>
        <div class="bento-card-body">
          <div class="link-list">
            <a href="https://ku.baidu-int.com/knowledge/HFVrC7hq1Q/_SKPgSwp2G/NbX2gitgSF/KtfcNN4FUlpsxj" target="_blank" class="link-item">
              <el-icon><User /></el-icon>
              申请虚拟（专用）账户
            </a>
            <a href="http://icafe.baidu-int.com" target="_blank" class="link-item">
              <el-icon><Postcard /></el-icon>
              iCafe 项目管理平台
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Postcard, Check, Connection, InfoFilled, Link, User } from '@element-plus/icons-vue'
import { loadConfig, saveConfig, testICafeConnection } from '@/api/config'

const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))

const form = reactive({
  api_url: 'http://icafeapi.baidu-int.com/api/v2',
  space_id: 'HMLCC',
  username: '',
  password: '',
  description: 'iCafe API配置，用于创建告警相关的任务卡片'
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref('')
const testResultClass = ref('')

const loadICafeConfig = async () => {
  try {
    const response = await loadConfig('icafe')
    if (response.success && response.data.config) {
      const config = response.data.config
      Object.assign(form, {
        api_url: config.api_url || 'http://icafeapi.baidu-int.com/api/v2',
        space_id: config.space_id || 'HMLCC',
        username: config.username || '',
        password: config.password || '',
      })
    }
  } catch (error) {
    console.error('加载 iCafe 配置失败:', error)
  }
}

const handleSave = async () => {
  try {
    await formRef.value.validate()
    saving.value = true
    const response = await saveConfig('icafe', {
      api_url: form.api_url,
      space_id: form.space_id,
      username: form.username,
      password: form.password,
      description: form.description
    })
    if (response.success) {
      ElMessage.success('iCafe 配置保存成功')
      testResult.value = ''
    }
  } catch (error) {
    if (error !== 'validation failed') {
      ElMessage.error('保存配置失败')
    }
  } finally {
    saving.value = false
  }
}

const handleTestConnection = async () => {
  try {
    await formRef.value.validate()
    testing.value = true
    testResult.value = ''
    const response = await testICafeConnection({
      api_url: form.api_url,
      space_id: form.space_id,
      username: form.username,
      password: form.password
    })
    if (response.success) {
      testResult.value = '✅ 连接成功'
      testResultClass.value = 'test-success'
    } else {
      testResult.value = `❌ 失败：${response.message}`
      testResultClass.value = 'test-error'
    }
  } catch (error) {
    if (error !== 'validation failed') {
      testResult.value = `❌ 失败：${error.response?.data?.message || error.message || '未知错误'}`
      testResultClass.value = 'test-error'
    }
  } finally {
    testing.value = false
  }
}

onMounted(loadICafeConfig)
</script>

<style scoped>
.icafe-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6, 24px);
}

.config-form {
  max-width: 680px;
}

.form-tip {
  font-size: 12px;
  color: var(--text-secondary, #909399);
  margin-top: 4px;
  line-height: 1.5;
}

.test-result-text {
  margin-left: 12px;
  font-weight: 500;
  font-size: 14px;
}

.test-success { color: #67c23a; }
.test-error   { color: #f56c6c; }

/* 下方两个信息卡并排 */
.info-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-6, 24px);
}

.info-list {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #606266);
  line-height: 2;
}

.info-list li {
  font-size: 13px;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--primary, #1a73e8);
  text-decoration: none;
  padding: 10px 12px;
  border-radius: var(--radius-md, 6px);
  background: rgba(26, 115, 232, 0.05);
  transition: background 0.2s;
}

.link-item:hover {
  background: rgba(26, 115, 232, 0.12);
}

@media (max-width: 768px) {
  .info-cards {
    grid-template-columns: 1fr;
  }
}
</style>
