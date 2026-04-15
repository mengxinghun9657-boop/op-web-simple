<template>
  <div class="analysis-config">
    <!-- 资源分析配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon" style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));">
            <el-icon :size="16"><Cpu /></el-icon>
          </div>
          资源分析配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <label class="config-label">
            <el-icon><List /></el-icon>
            集群ID列表（每行一个）
          </label>
          <el-input
            v-model="resourceConfig.text"
            type="textarea"
            :rows="10"
            placeholder="请输入集群ID，每行一个&#10;例如：&#10;cce-3nusu9su&#10;cce-9m1ht29q"
            :disabled="!isAdmin"
          />
          <p class="config-hint">当前配置: {{ resourceConfig.ids.length }} 个集群ID</p>
          <el-input
            v-model="resourceConfig.description"
            placeholder="配置说明（可选）"
            :disabled="!isAdmin"
          />
        </div>
        <div class="action-row">
          <el-button
            type="success"
            @click="syncFromCCEApi"
            :loading="syncing"
            :disabled="!isAdmin"
          >
            <el-icon><Refresh /></el-icon>
            从 CCE API 同步
          </el-button>
          <el-button
            type="primary"
            @click="saveResourceConfig"
            :loading="saving"
            :disabled="!isAdmin"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 配置说明 -->
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
        <div class="info-list">
          <div class="info-item">
            <el-icon class="info-icon"><QuestionFilled /></el-icon>
            <div class="info-content">
              <div class="info-title">配置作用</div>
              <div class="info-desc">在资源分析页面，用户可以选择使用这里配置的默认集群ID，无需每次手动输入</div>
            </div>
          </div>
          <div class="info-item">
            <el-icon class="info-icon"><Lock /></el-icon>
            <div class="info-content">
              <div class="info-title">权限要求</div>
              <div class="info-desc">仅管理员和超级管理员可以修改配置，普通用户只能查看</div>
            </div>
          </div>
          <div class="info-item">
            <el-icon class="info-icon"><Edit /></el-icon>
            <div class="info-content">
              <div class="info-title">灵活使用</div>
              <div class="info-desc">用户在使用时可以选择使用配置的默认值，也可以手动输入其他集群ID</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, List, Check, InfoFilled, QuestionFilled, Lock, Edit, Refresh } from '@element-plus/icons-vue'
import * as configApi from '@/api/config'
import { getCCEClusterIds } from '@/api/cmdb'

// 用户权限
const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))

// 配置数据
const resourceConfig = ref({ text: '', ids: [], description: '' })

// 保存状态
const saving = ref(false)
const syncing = ref(false)

// 监听文本变化，更新ID数组
watch(() => resourceConfig.value.text, (newText) => {
  resourceConfig.value.ids = newText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
})

// 加载配置
const loadConfig = async () => {
  try {
    const res = await configApi.loadConfig('analysis')
    const config = res.data?.config || res.config // 兼容新旧格式
    if (config && Object.keys(config).length > 0) {
      if (config.cluster_ids) {
        resourceConfig.value.text = Array.isArray(config.cluster_ids)
          ? config.cluster_ids.join('\n')
          : config.cluster_ids.replace(/,/g, '\n')  // 将逗号转换为换行
      }
      if (config.description) {
        resourceConfig.value.description = config.description
      }
    }
  } catch (error) {
    // Silent error handling
  }
}

// 从 CCE API 同步集群 ID
const syncFromCCEApi = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可以修改配置')
    return
  }
  syncing.value = true
  try {
    const res = await getCCEClusterIds()
    const ids = res.data?.cluster_ids || res.cluster_ids || []
    if (ids.length === 0) {
      ElMessage.warning('CCE API 未返回集群ID，请确认 AK/SK 已配置')
      return
    }
    resourceConfig.value.text = ids.join('\n')
    ElMessage.success(`已从 CCE API 同步 ${ids.length} 个集群ID，请点击保存配置`)
  } catch (error) {
    ElMessage.error('从 CCE API 获取失败：' + (error.response?.data?.detail || error.message) + '，已保留原有配置')
  } finally {
    syncing.value = false
  }
}

// 保存配置
const saveResourceConfig = async () => {
  if (!isAdmin.value) {
    ElMessage.warning('仅管理员可以修改配置')
    return
  }

  // 验证配置
  if (resourceConfig.value.ids.length === 0) {
    ElMessage.warning('请至少输入一个集群ID')
    return
  }

  saving.value = true
  try {
    const config = {
      cluster_ids: resourceConfig.value.ids.join(','),  // 转换为逗号分隔字符串
      description: resourceConfig.value.description || '资源分析默认集群ID列表'
    }

    await configApi.saveConfig('analysis', config)
    ElMessage.success(`资源分析配置保存成功 (${resourceConfig.value.ids.length} 个集群ID)`)
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.analysis-config {
  display: grid;
  grid-template-columns: 2fr 1fr;
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
.action-row {
  display: flex;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
}

.action-row .el-button {
  flex: 1;
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: 600;
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.action-row .el-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

.action-row .el-button:active {
  transform: translateY(0);
}

/* 配置说明 - 增强视觉效果 */
.info-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.info-item {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  transition: var(--transition-all);
}

.info-item:hover {
  border-color: var(--border-color-light);
  box-shadow: var(--shadow-md);
  transform: translateX(2px);
}

.info-icon {
  flex-shrink: 0;
  font-size: 28px;
  color: var(--color-primary);
  margin-top: 2px;
}

.info-content {
  flex: 1;
}

.info-title {
  font-weight: 600;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  margin-bottom: var(--spacing-2);
}

.info-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 响应式 */
@media (max-width: 1200px) {
  .analysis-config {
    grid-template-columns: 1fr;
  }
  
  .info-list {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .info-item {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .analysis-config {
    gap: var(--spacing-4);
  }
  
  .config-section {
    gap: var(--spacing-3);
  }
  
  .info-list {
    flex-direction: column;
  }
  
  .info-item {
    min-width: auto;
  }
}
</style>
