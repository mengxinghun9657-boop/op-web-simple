<template>
  <div class="analysis-config">
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #ef4444, #b91c1c);">
            <el-icon :size="16"><Monitor /></el-icon>
          </div>
          APIServer 告警配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <el-form label-width="150px" class="inline-form">
            <el-form-item label="自动检查">
              <el-switch v-model="configForm.auto_check_enabled" :disabled="!isAdmin" />
            </el-form-item>
            <el-form-item label="检查间隔(分钟)">
              <el-input-number v-model="configForm.check_interval_minutes" :min="1" :max="1440" :disabled="!isAdmin || !configForm.auto_check_enabled" />
            </el-form-item>
            <el-form-item label="统计窗口(分钟)">
              <el-input-number v-model="configForm.window_minutes" :min="1" :max="60" :disabled="!isAdmin" />
            </el-form-item>
          </el-form>
          <div class="rule-table">
            <table class="config-table">
              <thead>
                <tr>
                  <th>告警类型</th>
                  <th>启用</th>
                  <th>Warning 阈值</th>
                  <th>Critical 阈值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rule in configForm.rules" :key="rule.key">
                  <td>
                    <div class="rule-name">{{ rule.label }}</div>
                    <div class="rule-desc">{{ rule.description }}</div>
                  </td>
                  <td><el-switch v-model="rule.enabled" :disabled="!isAdmin" /></td>
                  <td><el-input-number v-model="rule.warning_threshold" :disabled="!isAdmin || !rule.enabled" :step="0.1" /></td>
                  <td><el-input-number v-model="rule.critical_threshold" :disabled="!isAdmin || !rule.enabled" :step="0.1" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <el-button type="primary" @click="save" :loading="saving" :disabled="!isAdmin">
          <el-icon><Check /></el-icon>
          保存配置
        </el-button>
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
        <div class="info-item">Prometheus URL、Token、Instance ID、集群ID列表和默认步长统一从“Prometheus配置”读取。</div>
        <div class="info-item">这里仅保留 APIServer 模块自己的业务参数，例如告警检测窗口。</div>
        <div class="info-item">告警通知沿用当前 Webhook 配置，组件名统一按 APIServer 发送。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, Check, InfoFilled } from '@element-plus/icons-vue'
import { getAPIServerConfig, saveAPIServerConfig } from '@/api/apiserverAlerts'

const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))
const saving = ref(false)
const configForm = ref({ auto_check_enabled: false, check_interval_minutes: 10, window_minutes: 5, rules: [] })

const load = async () => {
  try {
    const res = await getAPIServerConfig()
    const config = res.data || {}
    configForm.value.auto_check_enabled = Boolean(config.auto_check_enabled)
    configForm.value.check_interval_minutes = Number(config.check_interval_minutes || 10)
    configForm.value.window_minutes = Number(config.window_minutes || 5)
    configForm.value.rules = config.rules || []
  } catch {
    // keep defaults
  }
}

const save = async () => {
  if (!isAdmin.value) return
  saving.value = true
  try {
    await saveAPIServerConfig({
      auto_check_enabled: configForm.value.auto_check_enabled,
      check_interval_minutes: configForm.value.check_interval_minutes,
      window_minutes: configForm.value.window_minutes,
      rules: configForm.value.rules
    })
    ElMessage.success('APIServer 告警配置保存成功')
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
.rule-table { overflow-x: auto; }
.config-table { width: 100%; border-collapse: collapse; }
.config-table th, .config-table td { padding: 12px; border-bottom: 1px solid var(--border-color); text-align: left; vertical-align: top; }
.config-table th { background: var(--bg-secondary); font-size: var(--font-size-sm); color: var(--text-secondary); }
.rule-name { font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.rule-desc { font-size: var(--font-size-sm); color: var(--text-tertiary); line-height: 1.6; max-width: 360px; }
.info-item { color: var(--text-secondary); line-height: 1.8; margin-bottom: 12px; }
</style>
