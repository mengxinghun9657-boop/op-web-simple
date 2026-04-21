<template>
  <div class="ai-config">
    <!-- 主配置卡片 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-secondary">
            <el-icon :size="16"><Cpu /></el-icon>
          </div>
          AI 模型配置
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
          label-width="130px"
          class="config-form"
          @submit.prevent="handleSave"
        >
          <el-form-item label="API 地址" prop="api_url">
            <el-input
              v-model="form.api_url"
              placeholder="http://llms-se.baidu-int.com:8200/chat/completions"
              :disabled="!isAdmin"
            />
            <div class="form-tip">兼容 OpenAI Chat Completions 格式的接口地址</div>
          </el-form-item>

          <el-form-item label="认证 Token" prop="api_key">
            <div class="token-input-wrapper">
              <el-input
                v-model="form.api_key"
                :type="tokenVisible ? 'textarea' : 'password'"
                :rows="3"
                placeholder="Bearer Token，留空则使用环境变量配置"
                :disabled="!isAdmin"
                class="token-input"
              />
              <el-button
                class="token-toggle-btn"
                :icon="tokenVisible ? Hide : View"
                circle
                size="small"
                @click="tokenVisible = !tokenVisible"
                :title="tokenVisible ? '隐藏 Token' : '显示 Token'"
              />
            </div>
            <div class="form-tip">请求头中 Authorization: Bearer &lt;token&gt;，留空则使用服务器环境变量</div>
          </el-form-item>

          <el-form-item label="模型名称" prop="model">
            <el-select
              v-model="form.model"
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入模型名称"
              :disabled="!isAdmin"
              style="width: 100%"
            >
              <el-option-group label="ERNIE Turbo（速度优先）">
                <el-option label="ernie-4.5-turbo-32k（推荐，32k）" value="ernie-4.5-turbo-32k" />
                <el-option label="ernie-4.5-turbo-128k（128k）" value="ernie-4.5-turbo-128k" />
                <el-option label="ernie-4.5-turbo-128k-preview（128k，效果更强）" value="ernie-4.5-turbo-128k-preview" />
              </el-option-group>
              <el-option-group label="ERNIE X1（深度思考）">
                <el-option label="ernie-x1-turbo-32k（32k）" value="ernie-x1-turbo-32k" />
                <el-option label="ernie-x1-turbo-32k-preview（32k，效果更强）" value="ernie-x1-turbo-32k-preview" />
                <el-option label="ernie-x1-32k-preview（32k）" value="ernie-x1-32k-preview" />
              </el-option-group>
              <el-option-group label="ERNIE 开源">
                <el-option label="ernie-4.5-21b-a3b（21B MoE，120k）" value="ernie-4.5-21b-a3b" />
                <el-option label="ernie-4.5-0.3b（轻量，120k）" value="ernie-4.5-0.3b" />
                <el-option label="ernie-4.5-8k-preview（5k）" value="ernie-4.5-8k-preview" />
              </el-option-group>
              <el-option-group label="DeepSeek">
                <el-option label="deepseek-v3.2（671B，非思考，128k）" value="deepseek-v3.2" />
                <el-option label="deepseek-v3.1-250821（最新版，混合推理，128k）" value="deepseek-v3.1-250821" />
                <el-option label="deepseek-v3.2-think（671B，思考模式，144k）" value="deepseek-v3.2-think" />
                <el-option label="deepseek-v3.1-think-250821（最新思考版）" value="deepseek-v3.1-think-250821" />
                <el-option label="deepseek-chat（原版 V3，64k）" value="deepseek-chat" />
                <el-option label="deepseek-reasoner（R1，推理模型）" value="deepseek-reasoner" />
                <el-option label="deepseek-reasoner-250528（R1-0528，增强推理）" value="deepseek-reasoner-250528" />
              </el-option-group>
              <el-option-group label="Qwen / 通义千问">
                <el-option label="qwen3-235b-a22b-thinking-2507（235B 思考版，128k）" value="qwen3-235b-a22b-thinking-2507" />
                <el-option label="qwen3-next-80b-a3b-instruct（80B 非思考，128k）" value="qwen3-next-80b-a3b-instruct" />
              </el-option-group>
              <el-option-group label="GPT 系列">
                <el-option label="gpt-4o" value="gpt-4o" />
                <el-option label="gpt-4o-mini" value="gpt-4o-mini" />
                <el-option label="gpt-4.1-2025-04-14" value="gpt-4.1-2025-04-14" />
                <el-option label="gpt-4.1-mini-2025-04-14" value="gpt-4.1-mini-2025-04-14" />
                <el-option label="gpt-5-2025-08-07" value="gpt-5-2025-08-07" />
                <el-option label="gpt-5-mini-2025-08-07" value="gpt-5-mini-2025-08-07" />
              </el-option-group>
              <el-option-group label="Claude 系列">
                <el-option label="claude-sonnet-4-6（200k）" value="claude-sonnet-4-6" />
                <el-option label="claude-opus-4-6（200k，最强）" value="claude-opus-4-6" />
                <el-option label="claude-haiku-4-5-20251001（200k，最快）" value="claude-haiku-4-5-20251001" />
              </el-option-group>
              <el-option-group label="Gemini 系列">
                <el-option label="gemini-2.5-pro（1M，思考模型）" value="gemini-2.5-pro" />
              </el-option-group>
              <el-option-group label="Doubao / 豆包">
                <el-option label="doubao-seed-1.6（256k）" value="doubao-seed-1.6" />
                <el-option label="doubao-seed-1.6-thinking（256k，深度思考）" value="doubao-seed-1.6-thinking" />
              </el-option-group>
            </el-select>
            <div class="form-tip">优先使用此模型，额度耗尽时系统自动降级到备用模型</div>
          </el-form-item>

          <el-form-item label="测试连接">
            <el-button @click="handleTestConnection" :loading="testing" :disabled="!isAdmin || !form.api_url">
              <el-icon><Connection /></el-icon>
              测试连接
            </el-button>
            <span v-if="testResult !== null" class="result-text" :class="testResultClass === 'test-success' ? 'is-success' : testResultClass === 'test-error' ? 'is-error' : ''">
              <el-icon v-if="testResultClass === 'test-success'"><CircleCheck /></el-icon>
              <el-icon v-else-if="testResultClass === 'test-error'"><CircleClose /></el-icon>
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
            <li>配置用于运营分析报告 AI 解读、告警诊断、资源分析等功能</li>
            <li>所有模型均通过内网网关统一访问，接口格式兼容 OpenAI Chat Completions API</li>
            <li>未配置时自动使用服务器环境变量 ERNIE_API_URL / ERNIE_API_KEY / ERNIE_MODEL</li>
            <li>主模型额度耗尽时，系统自动按降级链切换到下一个可用模型（共 15 级）</li>
            <li>支持 ERNIE / DeepSeek / Qwen / GPT / Claude / Gemini / Doubao 等所有网关模型</li>
          </ul>
        </div>
      </div>

      <div class="bento-card info-card">
        <div class="bento-card-header">
          <div class="bento-card-title">
            <div class="bento-card-title-icon icon-bg-success">
              <el-icon :size="16"><List /></el-icon>
            </div>
            自动降级顺序
          </div>
        </div>
        <div class="bento-card-body">
          <ol class="fallback-list">
            <li v-for="(m, i) in fallbackModels" :key="m" :class="{ 'primary-model': i === 0 }">
              {{ m }}
            </li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Check, Connection, InfoFilled, List, View, Hide, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { loadConfig, saveConfig } from '@/api/config'
import axios from '@/utils/axios'

const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))

const DEFAULT_API_URL = 'http://llms-se.baidu-int.com:8200/chat/completions'
const DEFAULT_MODEL = 'ernie-4.5-turbo-32k'

const form = reactive({
  api_url: DEFAULT_API_URL,
  api_key: '',
  model: DEFAULT_MODEL
})

const rules = {
  api_url: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  model: [{ required: true, message: '请选择或输入模型名称', trigger: 'blur' }]
}

const fallbackModels = [
  'ernie-4.5-turbo-32k',
  'ernie-4.5-turbo-128k',
  'ernie-4.5-turbo-128k-preview',
  'ernie-x1-turbo-32k',
  'ernie-x1-turbo-32k-preview',
  'ernie-x1-32k-preview',
  'ernie-4.5-21b-a3b',
  'ernie-4.5-0.3b',
  'deepseek-v3.2',
  'deepseek-v3.1-250821',
  'deepseek-v3.2-think',
  'deepseek-v3.1-think-250821',
  'qwen3-235b-a22b-thinking-2507',
  'qwen3-next-80b-a3b-instruct',
  'ernie-4.5-8k-preview'
]

const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref('')
const testResultClass = ref('')
const tokenVisible = ref(false)

const loadAIConfig = async () => {
  try {
    const response = await loadConfig('ai')
    if (response.success && response.data.config && Object.keys(response.data.config).length > 0) {
      const config = response.data.config
      Object.assign(form, {
        api_url: config.api_url || DEFAULT_API_URL,
        api_key: config.api_key || '',
        model: config.model || DEFAULT_MODEL
      })
    }
  } catch (error) {
    console.error('加载 AI 配置失败:', error)
  }
}

const handleSave = async () => {
  try {
    await formRef.value.validate()
    saving.value = true
    const response = await saveConfig('ai', {
      api_url: form.api_url,
      api_key: form.api_key,
      model: form.model
    })
    if (response.success) {
      ElMessage.success('AI 模型配置保存成功')
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
    const response = await axios.post('/api/v1/config/ai/test-connection', {
      api_url: form.api_url,
      api_key: form.api_key,
      model: form.model
    })
    const data = response
    if (data.success) {
      testResult.value = data.message
      testResultClass.value = 'test-success'
    } else {
      testResult.value = data.message
      testResultClass.value = 'test-error'
    }
  } catch (error) {
    if (error !== 'validation failed') {
      const msg = error.message || error.response?.data?.detail || '未知错误'
      testResult.value = msg
      testResultClass.value = 'test-error'
    }
  } finally {
    testing.value = false
  }
}

onMounted(loadAIConfig)
</script>

<style scoped>
.ai-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6, 24px);
}

.config-form {
  max-width: 680px;
}

.form-tip {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
  line-height: var(--leading-relaxed);
}

.token-input-wrapper {
  position: relative;
  width: 100%;
}

.token-input {
  width: 100%;
}

.token-toggle-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 1;
}

/* .test-result-text / .test-success / .test-error 已移至全局 google-components.css 的 .result-text.is-success/.is-error */

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
  font-size: var(--text-sm);
}

.fallback-list {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #606266);
  line-height: 1.9;
  font-size: var(--text-sm);
  font-family: monospace;
}

.fallback-list .primary-model {
  color: var(--color-info);
  font-weight: var(--font-semibold);
}

@media (max-width: 768px) {
  .info-cards {
    grid-template-columns: 1fr;
  }
}
</style>
