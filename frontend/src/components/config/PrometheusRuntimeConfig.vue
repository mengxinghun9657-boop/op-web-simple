<template>
  <div class="analysis-config">
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-primary">
            <el-icon :size="16"><Connection /></el-icon>
          </div>
          Prometheus 配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <el-form label-width="140px" class="config-form">
            <el-form-item label="Prometheus URL">
              <el-input v-model="configForm.grafana_url" :disabled="!isAdmin" placeholder="https://cprom.cd.baidubce.com/select/prometheus" />
            </el-form-item>
            <el-form-item label="认证 Token">
              <div class="token-input-wrapper">
                <el-input
                  v-model="configForm.token"
                  :type="tokenVisible ? 'textarea' : 'password'"
                  :rows="4"
                  :disabled="!isAdmin"
                  placeholder="Bearer eyJ..."
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
            </el-form-item>
            <el-form-item label="Instance ID">
              <el-input v-model="configForm.instance_id" :disabled="!isAdmin" placeholder="cprom-j5i12oxuqj1z7" />
            </el-form-item>
            <el-form-item label="默认步长">
              <el-select v-model="configForm.step" :disabled="!isAdmin" style="width: 160px;">
                <el-option label="1 分钟" value="1m" />
                <el-option label="5 分钟" value="5m" />
                <el-option label="15 分钟" value="15m" />
                <el-option label="1 小时" value="1h" />
              </el-select>
            </el-form-item>
            <el-form-item label="默认集群ID">
              <el-input v-model="configForm.text" type="textarea" :rows="8" :disabled="!isAdmin" placeholder="请输入集群ID，每行一个" />
              <div class="form-tip">资源分析、bottom、APIServer 告警默认共用这份集群ID列表。</div>
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="save" :loading="saving" :disabled="!isAdmin">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon">
            <el-icon :size="16"><InfoFilled /></el-icon>
          </div>
          配置说明
        </div>
      </div>
      <div class="bento-card-body">
        <div class="info-item">统一维护同一个 cProm 的 URL、Token、Instance ID 和默认集群ID。</div>
        <div class="info-item">资源分析、bottom 卡时数据、APIServer 监控告警都会优先读取这份配置。</div>
        <div class="info-item">如果后续需要模块级覆盖，再在各自模块里加业务参数即可。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Check, InfoFilled, View, Hide } from '@element-plus/icons-vue'
import * as configApi from '@/api/config'

const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))
const saving = ref(false)
const tokenVisible = ref(false)
const configForm = ref({
  text: '',
  ids: [],
  grafana_url: 'https://cprom.cd.baidubce.com/select/prometheus',
  token: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lc3BhY2UiOiJjcHJvbS1qNWkxMm94dXFqMXo3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0ODk3MjczNTI2LCJpc3MiOiJjcHJvbSJ9.wbsW3Cs3PkTfgx_lsBHONGFqY7CFENSU-2NXChlT304',
  instance_id: 'cprom-j5i12oxuqj1z7',
  step: '5m'
})

watch(() => configForm.value.text, (newText) => {
  configForm.value.ids = newText.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#'))
})

const load = async () => {
  try {
    const res = await configApi.loadConfig('prometheus_runtime')
    const config = res.data?.config || res.config || {}
    if (config.cluster_ids) {
      configForm.value.text = Array.isArray(config.cluster_ids) ? config.cluster_ids.join('\n') : String(config.cluster_ids).replace(/,/g, '\n')
    }
    configForm.value.grafana_url = config.grafana_url || configForm.value.grafana_url
    configForm.value.token = config.token || configForm.value.token
    configForm.value.instance_id = config.instance_id || configForm.value.instance_id
    configForm.value.step = config.step || configForm.value.step
  } catch {
    // keep defaults
  }
}

const save = async () => {
  if (!isAdmin.value) return
  saving.value = true
  try {
    await configApi.saveConfig('prometheus_runtime', {
      cluster_ids: configForm.value.ids.join(','),
      grafana_url: configForm.value.grafana_url,
      token: configForm.value.token,
      instance_id: configForm.value.instance_id,
      step: configForm.value.step
    })
    ElMessage.success('Prometheus 配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.analysis-config { display: grid; grid-template-columns: 2fr 1fr; gap: var(--spacing-6); }
.config-section { display: flex; flex-direction: column; gap: var(--spacing-4); }
.info-item { color: var(--text-secondary); line-height: 1.8; margin-bottom: 12px; }
.token-input-wrapper { position: relative; width: 100%; }
.token-input { width: 100%; }
.token-toggle-btn { position: absolute; top: 6px; right: 6px; z-index: 1; }
</style>
