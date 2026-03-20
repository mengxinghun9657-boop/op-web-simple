<template>
  <div class="icafe-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>iCafe 配置</span>
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存配置
          </el-button>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        @submit.prevent="handleSave"
      >
        <el-form-item label="API 地址" prop="api_url">
          <el-input
            v-model="form.api_url"
            placeholder="iCafe API 地址"
          />
          <div class="form-tip">默认使用内网 API 地址：http://icafeapi.baidu-int.com/api/v2</div>
        </el-form-item>

        <el-form-item label="空间ID" prop="space_id">
          <el-input
            v-model="form.space_id"
            placeholder="iCafe 空间标识"
          />
          <div class="form-tip">长安HMLCC售后服务支持空间ID：HMLCC</div>
        </el-form-item>

        <el-form-item label="用户名" prop="username" required>
          <el-input
            v-model="form.username"
            placeholder="请输入 iCafe 用户名"
            maxlength="50"
          />
          <div class="form-tip">建议使用虚拟账户，如：v_zhangxingpei</div>
        </el-form-item>

        <el-form-item label="密码" prop="password" required>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入 iCafe 密码"
            show-password
            maxlength="200"
          />
          <div class="form-tip">建议使用虚拟密码，可通过 iCafe 服务号获取</div>
        </el-form-item>

        <el-form-item label="测试连接">
          <el-button @click="handleTestConnection" :loading="testing">
            测试连接
          </el-button>
          <span v-if="testResult" :class="testResultClass" style="margin-left: 12px;">
            {{ testResult }}
          </span>
        </el-form-item>
      </el-form>

      <!-- 使用说明 -->
      <el-divider content-position="left">使用说明</el-divider>
      <div class="usage-info">
        <el-alert
          title="配置说明"
          type="info"
          :closable="false"
          show-icon
        >
          <ul>
            <li>iCafe 是百度内部的项目管理平台，用于创建和跟踪任务卡片</li>
            <li>配置完成后，可在告警列表中为每个告警快速创建对应的 iCafe 卡片</li>
            <li>卡片会自动填充告警信息、诊断结果等内容</li>
            <li>虚拟账户申请：<a href="https://ku.baidu-int.com/knowledge/HFVrC7hq1Q/_SKPgSwp2G/NbX2gitgSF/KtfcNN4FUlpsxj" target="_blank">申请专用(虚拟)账户</a></li>
          </ul>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { loadConfig, saveConfig, testICafeConnection } from '@/api/config'

// 表单数据
const form = reactive({
  api_url: 'http://icafeapi.baidu-int.com/api/v2',
  space_id: 'HMLCC',
  username: '',
  password: '',
  description: 'iCafe API配置，用于创建告警相关的任务卡片'
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 状态
const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref('')
const testResultClass = ref('')

// 加载配置
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
        description: config.description || 'iCafe API配置，用于创建告警相关的任务卡片'
      })
    }
  } catch (error) {
    console.error('加载 iCafe 配置失败:', error)
  }
}

// 保存配置
const handleSave = async () => {
  try {
    // 表单验证
    await formRef.value.validate()
    
    saving.value = true
    
    const configData = {
      api_url: form.api_url,
      space_id: form.space_id,
      username: form.username,
      password: form.password,
      description: form.description
    }
    
    const response = await saveConfig('icafe', configData)
    
    if (response.success) {
      ElMessage.success('iCafe 配置保存成功')
      // 清除测试结果
      testResult.value = ''
    }
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存 iCafe 配置失败:', error)
      ElMessage.error('保存配置失败')
    }
  } finally {
    saving.value = false
  }
}

// 测试连接
const handleTestConnection = async () => {
  try {
    // 先验证表单
    await formRef.value.validate()
    
    testing.value = true
    testResult.value = ''
    
    // 使用当前表单数据测试连接
    const testConfig = {
      api_url: form.api_url,
      space_id: form.space_id,
      username: form.username,
      password: form.password
    }
    
    // 调用后端测试连接API
    const response = await testICafeConnection(testConfig)
    
    if (response.success) {
      testResult.value = '✅ 连接测试成功'
      testResultClass.value = 'test-success'
    } else {
      testResult.value = `❌ 连接测试失败：${response.message}`
      testResultClass.value = 'test-error'
    }
  } catch (error) {
    if (error !== 'validation failed') {
      const errorMsg = error.response?.data?.message || error.message || '未知错误'
      testResult.value = `❌ 连接测试失败：${errorMsg}`
      testResultClass.value = 'test-error'
    }
  } finally {
    testing.value = false
  }
}

// 初始化
onMounted(() => {
  loadICafeConfig()
})
</script>

<style scoped>
.icafe-config {
  max-width: 800px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.usage-info {
  margin-top: 20px;
}

.usage-info ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.usage-info li {
  margin-bottom: 4px;
  line-height: 1.5;
}

.test-success {
  color: #67c23a;
  font-weight: 500;
}

.test-error {
  color: #f56c6c;
  font-weight: 500;
}
</style>