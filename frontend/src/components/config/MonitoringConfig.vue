<template>
  <div class="monitoring-config">
    <!-- EIP监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
            <el-icon :size="16"><Connection /></el-icon>
          </div>
          EIP监控配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <label class="config-label">
            <el-icon><List /></el-icon>
            EIP实例ID列表（每行一个）
          </label>
          <el-input
            v-model="eipConfig.text"
            type="textarea"
            :rows="8"
            placeholder="请输入EIP实例ID，每行一个&#10;例如：&#10;ip-78pdlyjv&#10;ip-1euzxzkm"
            :disabled="!isAdmin"
          />
          <p class="config-hint">当前配置: {{ eipConfig.ids.length }} 个EIP实例</p>
          <el-input
            v-model="eipConfig.description"
            placeholder="EIP监控配置认证例表"
            :disabled="!isAdmin"
          />
        </div>
        <el-button 
          type="success" 
          @click="saveEipConfig" 
          :loading="saving.eip"
          :disabled="!isAdmin"
          class="save-button"
        >
          <el-icon><Check /></el-icon>
          保存EIP配置
        </el-button>
      </div>
    </div>

    <!-- BCC监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706);">
            <el-icon :size="16"><Monitor /></el-icon>
          </div>
          BCC监控配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <label class="config-label">
            <el-icon><List /></el-icon>
            BCC实例ID列表（每行一个）
          </label>
          <el-input
            v-model="bccConfig.text"
            type="textarea"
            :rows="8"
            placeholder="请输入BCC实例ID，每行一个&#10;例如：&#10;i-Y2GKgIOK&#10;i-arpvOdwJ"
            :disabled="!isAdmin"
          />
          <p class="config-hint">当前配置: {{ bccConfig.ids.length }} 个BCC实例</p>
          <el-input
            v-model="bccConfig.description"
            placeholder="配置说明（可选）"
            :disabled="!isAdmin"
          />
        </div>
        <el-button 
          type="warning" 
          @click="saveBccConfig" 
          :loading="saving.bcc"
          :disabled="!isAdmin"
          class="save-button"
        >
          <el-icon><Check /></el-icon>
          保存BCC配置
        </el-button>
      </div>
    </div>

    <!-- BOS监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, #3b82f6, #2563eb);">
            <el-icon :size="16"><Coin /></el-icon>
          </div>
          BOS监控配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <label class="config-label">
            <el-icon><List /></el-icon>
            Bucket名称列表（每行一个）
          </label>
          <el-input
            v-model="bosConfig.text"
            type="textarea"
            :rows="8"
            placeholder="请输入Bucket名称，每行一个&#10;例如：&#10;halo-ad-algo-al&#10;halo-ad-algo-de"
            :disabled="!isAdmin"
          />
          <p class="config-hint">当前配置: {{ bosConfig.ids.length }} 个Bucket</p>
          <el-input
            v-model="bosConfig.description"
            placeholder="配置说明（可选）"
            :disabled="!isAdmin"
          />
        </div>
        <el-button 
          type="primary" 
          @click="saveBosConfig" 
          :loading="saving.bos"
          :disabled="!isAdmin"
          class="save-button"
        >
          <el-icon><Check /></el-icon>
          保存BOS配置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Monitor, Coin, List, Check } from '@element-plus/icons-vue'
import * as configApi from '@/api/config'

// 用户权限
const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))

// 配置数据
const eipConfig = ref({ text: '', ids: [], description: '' })
const bccConfig = ref({ text: '', ids: [], description: '' })
const bosConfig = ref({ text: '', ids: [], description: '' })

// 保存状态
const saving = ref({
  eip: false,
  bcc: false,
  bos: false
})

// 监听文本变化，更新ID数组
watch(() => eipConfig.value.text, (newText) => {
  eipConfig.value.ids = newText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
})

watch(() => bccConfig.value.text, (newText) => {
  bccConfig.value.ids = newText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
})

watch(() => bosConfig.value.text, (newText) => {
  bosConfig.value.ids = newText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
})

// 加载配置
const loadConfig = async () => {
  try {
    const res = await configApi.loadConfig('monitoring')
    if (res.config && Object.keys(res.config).length > 0) {
      // EIP配置
      if (res.config.eip_instance_ids) {
        eipConfig.value.text = Array.isArray(res.config.eip_instance_ids) 
          ? res.config.eip_instance_ids.join('\n')
          : res.config.eip_instance_ids
      }
      if (res.config.eip_description) {
        eipConfig.value.description = res.config.eip_description
      }
      
      // BCC配置
      if (res.config.bcc_instance_ids) {
        bccConfig.value.text = Array.isArray(res.config.bcc_instance_ids)
          ? res.config.bcc_instance_ids.join('\n')
          : res.config.bcc_instance_ids
      }
      if (res.config.bcc_description) {
        bccConfig.value.description = res.config.bcc_description
      }
      
      // BOS配置
      if (res.config.bos_bucket_names) {
        bosConfig.value.text = Array.isArray(res.config.bos_bucket_names)
          ? res.config.bos_bucket_names.join('\n')
          : res.config.bos_bucket_names
      }
      if (res.config.bos_description) {
        bosConfig.value.description = res.config.bos_description
      }
    }
  } catch (error) {
    console.error('加载监控配置失败:', error)
  }
}

// 保存EIP配置
const saveEipConfig = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可以修改配置')
    return
  }

  saving.value.eip = true
  try {
    const config = {
      eip_instance_ids: eipConfig.value.ids,
      eip_description: eipConfig.value.description || null,
      bcc_instance_ids: bccConfig.value.ids,
      bcc_description: bccConfig.value.description || null,
      bos_bucket_names: bosConfig.value.ids,
      bos_description: bosConfig.value.description || null
    }
    
    await configApi.saveConfig('monitoring', config)
    ElMessage.success('EIP监控配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value.eip = false
  }
}

// 保存BCC配置
const saveBccConfig = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可以修改配置')
    return
  }

  saving.value.bcc = true
  try {
    const config = {
      eip_instance_ids: eipConfig.value.ids,
      eip_description: eipConfig.value.description || null,
      bcc_instance_ids: bccConfig.value.ids,
      bcc_description: bccConfig.value.description || null,
      bos_bucket_names: bosConfig.value.ids,
      bos_description: bosConfig.value.description || null
    }
    
    await configApi.saveConfig('monitoring', config)
    ElMessage.success('BCC监控配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value.bcc = false
  }
}

// 保存BOS配置
const saveBosConfig = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可以修改配置')
    return
  }

  saving.value.bos = true
  try {
    const config = {
      eip_instance_ids: eipConfig.value.ids,
      eip_description: eipConfig.value.description || null,
      bcc_instance_ids: bccConfig.value.ids,
      bcc_description: bccConfig.value.description || null,
      bos_bucket_names: bosConfig.value.ids,
      bos_description: bosConfig.value.description || null
    }
    
    await configApi.saveConfig('monitoring', config)
    ElMessage.success('BOS监控配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value.bos = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.monitoring-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: var(--spacing-6);
}

/* 配置区域 */
.config-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.config-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
  padding-right: var(--spacing-4);
}

.config-label .el-icon {
  font-size: 18px;
  color: var(--color-primary);
}

.config-hint {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-top: var(--spacing-2);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

/* 增强textarea样式 */
.config-section :deep(.el-textarea__inner) {
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  padding: var(--spacing-3);
  transition: var(--transition-all);
}

.config-section :deep(.el-textarea__inner:hover) {
  border-color: var(--input-border-hover);
}

.config-section :deep(.el-textarea__inner:focus) {
  border-color: var(--input-border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.config-section :deep(.el-textarea__inner::placeholder) {
  color: var(--text-disabled);
  font-family: var(--font-family-sans);
}

/* 增强input样式 */
.config-section :deep(.el-input__wrapper) {
  background: var(--input-bg) !important;
  border: 1px solid var(--input-border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 12px 16px !important;
  min-height: 44px !important;
  box-shadow: none !important;
  transition: var(--transition-all) !important;
}

.config-section :deep(.el-input__wrapper:hover) {
  border-color: var(--input-border-hover) !important;
}

.config-section :deep(.el-input__wrapper.is-focus) {
  border-color: var(--input-border-focus) !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

.config-section :deep(.el-input__inner) {
  color: var(--text-primary) !important;
  font-size: var(--font-size-sm) !important;
  line-height: 1.5 !important;
  height: auto !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* 修复输入框图标间距 */
.config-section :deep(.el-input__wrapper) {
  padding-left: 12px !important;
  padding-right: 12px !important;
}

.config-section :deep(.el-input__prefix) {
  left: 12px !important;
}

.config-section :deep(.el-input__suffix) {
  right: 12px !important;
}

.config-section :deep(.el-input--prefix .el-input__wrapper) {
  padding-left: 40px !important;
}

.config-section :deep(.el-input--suffix .el-input__wrapper) {
  padding-right: 40px !important;
}

.config-section :deep(.el-input--prefix .el-input__inner) {
  padding-left: 40px !important;
}

.config-section :deep(.el-input--suffix .el-input__inner) {
  padding-right: 40px !important;
}

/* 增强按钮样式 */
.save-button {
  width: 100%;
  margin-top: var(--spacing-4);
}

.config-section :deep(.el-button) {
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: 600;
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.config-section :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

.config-section :deep(.el-button:active) {
  transform: translateY(0);
}

.config-section :deep(.el-button .el-icon) {
  font-size: 18px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .monitoring-config {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .monitoring-config {
    gap: var(--spacing-4);
  }
  
  .config-section {
    gap: var(--spacing-3);
  }
}
</style>
