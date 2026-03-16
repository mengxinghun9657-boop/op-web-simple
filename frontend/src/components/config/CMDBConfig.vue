<template>
  <div class="cmdb-config">
    <div class="config-header">
      <h2 class="config-title">
        <el-icon><DataBoard /></el-icon>
        CMDB配置
      </h2>
      <p class="config-description">这是 CMDB 的统一配置入口。管理 CMDB 的 API 认证、数据同步和同步日志。</p>
    </div>

    <el-tabs v-model="activeTab" class="config-tabs">
      <!-- API认证标签页 -->
      <el-tab-pane label="API认证" name="auth">
        <div class="tab-content">
          <el-form :model="apiAuthForm" label-width="120px" class="config-form">
            <el-form-item label="API Cookie">
              <el-input
                v-model="apiAuthForm.cookie"
                type="textarea"
                :rows="6"
                placeholder="请输入完整的Cookie字符串（必须包含BDUSS和amisid_https）&#10;&#10;示例：&#10;BDUSS=xxx; amisid_https=xxx; BAIDUID=xxx; ..."
                :disabled="!isEditing"
              />
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                <div>
                  <div><strong>如何获取完整Cookie：</strong></div>
                  <div>1. 在浏览器中打开 <a href="https://amis.baidu.com" target="_blank" style="color: var(--color-primary);">amis.baidu.com</a> 并登录</div>
                  <div>2. 按 F12 打开开发者工具 → Network（网络）标签</div>
                  <div>3. 刷新页面，点击任意请求，在 Headers 中找到 Cookie</div>
                  <div>4. 复制完整的 Cookie 字符串（必须包含 BDUSS 和 amisid_https）</div>
                  <div style="color: var(--color-warning); margin-top: 8px;"><strong>⚠️ 重要：必须包含 BDUSS 和 amisid_https 两个字段，否则无法通过验证</strong></div>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="过期时间">
              <el-date-picker
                v-model="apiAuthForm.expiresAt"
                type="datetime"
                placeholder="选择过期时间"
                :disabled="!isEditing"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>

            <el-form-item>
              <el-space>
                <el-button
                  type="primary"
                  :loading="testing"
                  :disabled="!apiAuthForm.cookie || !isEditing"
                  @click="handleTestCookie"
                >
                  <el-icon><CircleCheck /></el-icon>
                  测试有效性
                </el-button>
                <el-button
                  type="success"
                  :loading="saving"
                  :disabled="!apiAuthForm.cookie || !isEditing"
                  @click="handleSaveCookie"
                >
                  <el-icon><Select /></el-icon>
                  保存配置
                </el-button>
                <el-button
                  v-if="isEditing && apiAuthForm.cookie"
                  type="info"
                  @click="handleValidateCookie"
                >
                  <el-icon><MagicStick /></el-icon>
                  验证Cookie格式
                </el-button>
                <el-button
                  v-if="!isEditing"
                  @click="isEditing = true"
                >
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
                <el-button
                  v-else
                  @click="handleCancelEdit"
                >
                  <el-icon><Close /></el-icon>
                  取消
                </el-button>
              </el-space>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 数据同步标签页 -->
      <el-tab-pane label="数据同步" name="sync">
        <div class="tab-content">
          <el-form :model="manualSyncForm" label-width="120px" class="config-form">
            <el-form-item label="可用区">
              <el-input
                v-model="manualSyncForm.azone"
                placeholder="例如: AZONE-cdhmlcc001"
              />
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                指定要同步的可用区，默认值：AZONE-cdhmlcc001
              </div>
            </el-form-item>

            <el-form-item label="每页数量">
              <el-input-number
                v-model="manualSyncForm.perPage"
                :min="10"
                :max="2500"
                :step="100"
                style="width: 100%;"
              />
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                每次API请求获取的数据量，默认值：2000，建议范围：1000-2500
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="syncing"
                @click="handleSyncNow"
              >
                <el-icon><Refresh /></el-icon>
                立即同步
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 自动同步标签页 -->
      <el-tab-pane label="自动同步" name="schedule">
        <div class="tab-content">
          <el-form :model="scheduleForm" label-width="120px" class="config-form">
            <el-form-item label="启用状态">
              <el-switch
                v-model="scheduleForm.enabled"
                active-text="已启用"
                inactive-text="已禁用"
              />
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                启用后，系统将按照设定的时间间隔自动从 AMIS API 同步 CMDB 数据
              </div>
            </el-form-item>

            <el-form-item label="同步间隔">
              <el-input-number
                v-model="scheduleForm.intervalHours"
                :min="1"
                :max="24"
                :step="1"
                :disabled="!scheduleForm.enabled"
                style="width: 100%;"
              />
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                设置自动同步的时间间隔（小时），建议值：6-12 小时
              </div>
            </el-form-item>

            <el-form-item label="同步可用区">
              <el-select
                v-model="scheduleForm.azones"
                multiple
                placeholder="请选择要同步的可用区"
                :disabled="!scheduleForm.enabled"
                style="width: 100%;"
              >
                <el-option label="AZONE-cdhmlcc001" value="AZONE-cdhmlcc001" />
                <el-option label="AZONE-bjhmlcc001" value="AZONE-bjhmlcc001" />
                <el-option label="AZONE-gzhmlcc001" value="AZONE-gzhmlcc001" />
              </el-select>
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                选择需要自动同步的可用区，可以选择多个
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="savingSchedule"
                @click="handleSaveSchedule"
              >
                <el-icon><Select /></el-icon>
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 同步日志标签页 -->
      <el-tab-pane label="同步日志" name="logs">
        <div class="tab-content">
          <el-table
            :data="syncLogs"
            v-loading="loadingLogs"
            class="logs-table"
          >
            <el-table-column prop="started_at" label="开始时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.started_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="azone" label="可用区" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="getStatusType(row.status)"
                  size="small"
                >
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="服务器" width="150">
              <template #default="{ row }">
                <div class="stat-cell">
                  <span class="stat-label">新增:</span>
                  <span class="stat-value">{{ row.servers_added || 0 }}</span>
                  <span class="stat-label">更新:</span>
                  <span class="stat-value">{{ row.servers_updated || 0 }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="实例" width="150">
              <template #default="{ row }">
                <div class="stat-cell">
                  <span class="stat-label">新增:</span>
                  <span class="stat-value">{{ row.instances_added || 0 }}</span>
                  <span class="stat-label">更新:</span>
                  <span class="stat-value">{{ row.instances_updated || 0 }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="duration_seconds" label="耗时" width="100">
              <template #default="{ row }">
                {{ formatDuration(row.duration_seconds) }}
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
          </el-table>

          <div class="table-footer">
            <el-button
              type="primary"
              size="small"
              :loading="loadingLogs"
              @click="loadSyncLogs"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataBoard,
  InfoFilled,
  CircleCheck,
  Select,
  Edit,
  Close,
  Refresh,
  MagicStick
} from '@element-plus/icons-vue'
import * as cmdbApi from '@/api/cmdb'
import * as configApi from '@/api/config'

// 当前激活的标签页
const activeTab = ref('auth')

// API认证表单
const apiAuthForm = ref({
  cookie: '',
  expiresAt: null
})

// 手动同步表单
const manualSyncForm = ref({
  azone: 'AZONE-cdhmlcc001',
  perPage: 2000
})

// 自动同步表单
const scheduleForm = ref({
  enabled: false,
  intervalHours: 6,
  azones: ['AZONE-cdhmlcc001']
})

// 同步日志
const syncLogs = ref([])

// 加载状态
const testing = ref(false)
const saving = ref(false)
const syncing = ref(false)
const loadingLogs = ref(false)
const isEditing = ref(false)
const savingSchedule = ref(false)

// 原始配置（用于取消编辑）
const originalConfig = ref({})

// 加载CMDB配置
const loadConfig = async () => {
  try {
    const response = await configApi.loadConfig('cmdb')
    if (response.config && Object.keys(response.config).length > 0) {
      apiAuthForm.value.cookie = response.config.api_cookie || ''
      apiAuthForm.value.expiresAt = response.config.expires_at || null
      manualSyncForm.value.azone = response.config.azone || 'AZONE-cdhmlcc001'
      manualSyncForm.value.perPage = response.config.per_page || 2000
      
      // 保存原始配置
      originalConfig.value = JSON.parse(JSON.stringify({
        apiAuthForm: apiAuthForm.value,
        manualSyncForm: manualSyncForm.value
      }))
    }
  } catch (error) {
    // 加载配置失败，静默处理
  }
  
  // 加载自动同步配置
  await loadScheduleConfig()
}

// 加载自动同步配置
const loadScheduleConfig = async () => {
  try {
    const response = await cmdbApi.getSyncSchedule()
    if (response) {
      scheduleForm.value.enabled = response.enabled || false
      scheduleForm.value.intervalHours = response.interval_hours || 6
      scheduleForm.value.azones = response.azones || ['AZONE-cdhmlcc001']
    }
  } catch (error) {
    // 加载自动同步配置失败，静默处理
  }
}

// 测试Cookie有效性
const handleTestCookie = async () => {
  if (!apiAuthForm.value.cookie) {
    ElMessage.warning('请先输入Cookie')
    return
  }

  // 自动格式化Cookie
  const formattedCookie = formatCookie(apiAuthForm.value.cookie)
  if (formattedCookie !== apiAuthForm.value.cookie) {
    apiAuthForm.value.cookie = formattedCookie
    ElMessage.info('已自动格式化Cookie')
  }

  testing.value = true
  try {
    const response = await cmdbApi.testCookie(apiAuthForm.value.cookie)

    // 检查响应中的 valid 字段
    if (response && response.valid === true) {
      ElMessage.success(response.message || 'Cookie有效，可以正常访问CMDB API')
    } else {
      const errorMsg = response?.message || 'Cookie无效或已过期'
      ElMessage.error(errorMsg)
    }
  } catch (error) {
    ElMessage.error('Cookie无效或已过期: ' + (error.response?.data?.detail || error.message))
  } finally {
    testing.value = false
  }
}

// 格式化Cookie
const formatCookie = (cookie) => {
  const trimmed = cookie.trim()
  
  // 如果只包含BDUSS值（不包含"BDUSS="和";"），自动添加BDUSS=前缀
  if (!trimmed.includes('=') && !trimmed.includes(';')) {
    return `BDUSS=${trimmed}`
  }
  
  // 如果包含BDUSS，直接返回完整Cookie（保留所有字段）
  if (trimmed.includes('BDUSS=')) {
    return trimmed
  }
  
  // 其他情况直接返回
  return trimmed
}

// 验证Cookie格式
const handleValidateCookie = () => {
  const cookie = apiAuthForm.value.cookie.trim()
  
  // 检查是否包含BDUSS
  const hasBDUSS = cookie.includes('BDUSS=')
  // 检查是否包含amisid_https
  const hasAmisId = cookie.includes('amisid_https=')
  
  if (hasBDUSS && hasAmisId) {
    ElMessage.success('✅ Cookie格式正确，包含必需的 BDUSS 和 amisid_https 字段')
  } else if (hasBDUSS && !hasAmisId) {
    ElMessage.warning('⚠️ Cookie缺少 amisid_https 字段，可能无法通过验证')
  } else if (!hasBDUSS && hasAmisId) {
    ElMessage.warning('⚠️ Cookie缺少 BDUSS 字段，无法通过验证')
  } else {
    ElMessage.error('❌ Cookie格式不正确，缺少 BDUSS 和 amisid_https 字段')
  }
}

// 保存Cookie配置
const handleSaveCookie = async () => {
  if (!apiAuthForm.value.cookie) {
    ElMessage.warning('请先输入Cookie')
    return
  }

  saving.value = true
  try {
    const config = {
      api_cookie: apiAuthForm.value.cookie,
      expires_at: apiAuthForm.value.expiresAt,
      azone: manualSyncForm.value.azone,
      per_page: manualSyncForm.value.perPage
    }
    
    await configApi.saveConfig('cmdb', config)
    ElMessage.success('配置保存成功')
    isEditing.value = false
    
    // 更新原始配置
    originalConfig.value = JSON.parse(JSON.stringify({
      apiAuthForm: apiAuthForm.value,
      manualSyncForm: manualSyncForm.value
    }))
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

// 取消编辑
const handleCancelEdit = () => {
  if (originalConfig.value.apiAuthForm) {
    apiAuthForm.value = JSON.parse(JSON.stringify(originalConfig.value.apiAuthForm))
    manualSyncForm.value = JSON.parse(JSON.stringify(originalConfig.value.manualSyncForm))
  }
  isEditing.value = false
}

// 立即同步
const handleSyncNow = async () => {
  syncing.value = true
  try {
    const params = {
      azone: manualSyncForm.value.azone || undefined,
      per_page: manualSyncForm.value.perPage
    }
    
    await cmdbApi.syncFromAPI(params)
    ElMessage.success('同步任务已启动，请稍后查看同步日志')
    
    // 3秒后刷新日志
    setTimeout(() => {
      loadSyncLogs()
    }, 3000)
  } catch (error) {
    // 友好的错误提示
    let errorMessage = '同步失败'
    let suggestions = []
    
    if (error.response?.status === 500) {
      errorMessage = '宿主机MySQL连接失败'
      suggestions = [
        '检查宿主机MySQL服务是否正常运行',
        '验证数据库连接配置是否正确',
        '确认网络连接是否畅通',
        '检查数据库用户权限是否足够'
      ]
    } else if (error.response?.status === 401) {
      errorMessage = 'Cookie认证失败'
      suggestions = [
        '请重新获取有效的Cookie',
        '检查Cookie是否已过期',
        '确认Cookie格式是否正确'
      ]
    } else if (error.response?.status === 404) {
      errorMessage = 'API接口不存在'
      suggestions = [
        '检查AMIS API地址是否正确',
        '确认API版本是否匹配'
      ]
    } else if (error.response?.status === 403) {
      errorMessage = 'API访问权限不足'
      suggestions = [
        '检查Cookie对应的用户权限',
        '确认是否有CMDB数据访问权限'
      ]
    } else if (error.message?.includes('timeout')) {
      errorMessage = '连接超时'
      suggestions = [
        '检查网络连接是否稳定',
        '稍后重试同步操作'
      ]
    } else {
      errorMessage = error.response?.data?.detail || error.message || '未知错误'
    }
    
    // 显示详细的错误信息
    if (suggestions.length > 0) {
      const suggestionText = suggestions.map(s => `• ${s}`).join('\n')
      ElMessage({
        message: `${errorMessage}\n\n建议检查：\n${suggestionText}`,
        type: 'error',
        duration: 8000,
        showClose: true,
        dangerouslyUseHTMLString: false
      })
    } else {
      ElMessage.error(`${errorMessage}`)
    }
  } finally {
    syncing.value = false
  }
}

// 保存自动同步配置
const handleSaveSchedule = async () => {
  savingSchedule.value = true
  try {
    const config = {
      enabled: scheduleForm.value.enabled,
      interval_hours: scheduleForm.value.intervalHours,
      azones: scheduleForm.value.azones
    }
    
    await cmdbApi.updateSyncSchedule(config)
    ElMessage.success(`自动同步已${scheduleForm.value.enabled ? '启用' : '禁用'}`)
    
    // 重新加载配置
    await loadScheduleConfig()
  } catch (error) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    savingSchedule.value = false
  }
}

// 加载同步日志
const loadSyncLogs = async () => {
  loadingLogs.value = true
  try {
    const response = await cmdbApi.getSyncLogs({ limit: 20 })
    syncLogs.value = response.logs || []
  } catch (error) {
    // 加载日志失败，静默处理
  } finally {
    loadingLogs.value = false
  }
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}分${secs}秒`
}

// 获取状态类型
const getStatusType = (status) => {
  const typeMap = {
    success: 'success',
    failed: 'danger',
    running: 'warning'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    success: '成功',
    failed: '失败',
    running: '运行中'
  }
  return textMap[status] || status
}

onMounted(() => {
  loadConfig()
  loadSyncLogs()
})
</script>

<style scoped>
.cmdb-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 配置头部 */
.config-header {
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--bg-elevated);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
}

.config-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2) 0;
  line-height: 1;
}

.config-title .el-icon {
  font-size: 28px;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.config-description {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  margin: 0;
  line-height: 1.6;
  opacity: 0.75;
}

/* 标签页样式增强 */
.config-tabs {
  flex: 1;
}

.config-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--spacing-6);
  padding: 0 var(--spacing-2);
}

.config-tabs :deep(.el-tabs__nav-wrap) {
  padding: var(--spacing-1);
  background: var(--bg-elevated);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
}

.config-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.config-tabs :deep(.el-tabs__nav) {
  border: none;
}

.config-tabs :deep(.el-tabs__item) {
  color: var(--text-primary);
  font-weight: 600;
  font-size: var(--font-size-base);
  padding: 0 var(--spacing-6) !important;
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
  border: none;
  opacity: 0.6;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 44px !important;
  line-height: 44px !important;
  vertical-align: middle !important;
}

.config-tabs :deep(.el-tabs__item:hover) {
  opacity: 0.85;
  background: var(--bg-hover);
}

.config-tabs :deep(.el-tabs__item.is-active) {
  color: white;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
  opacity: 1;
}

.config-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

/* 标签页内容 */
.tab-content {
  padding: var(--spacing-6);
  background: var(--bg-elevated);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
}

/* 表单样式增强 */
.config-form {
  max-width: 700px;
}

.config-form :deep(.el-form-item) {
  margin-bottom: var(--spacing-6);
}

.config-form :deep(.el-form-item__label) {
  font-weight: 600;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
  padding-right: var(--spacing-4);
}

.config-form :deep(.el-textarea__inner) {
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

.config-form :deep(.el-textarea__inner:hover) {
  border-color: var(--input-border-hover);
}

.config-form :deep(.el-textarea__inner:focus) {
  border-color: var(--input-border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.config-form :deep(.el-input__wrapper) {
  background: var(--input-bg) !important;
  border: 1px solid var(--input-border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 12px 16px !important;
  min-height: 44px !important;
  box-shadow: none !important;
  transition: var(--transition-all) !important;
}

.config-form :deep(.el-input__wrapper:hover) {
  border-color: var(--input-border-hover) !important;
}

.config-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--input-border-focus) !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

.config-form :deep(.el-input__inner) {
  color: var(--text-primary) !important;
  font-size: var(--font-size-sm) !important;
  line-height: 1.5 !important;
  height: auto !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.config-form :deep(.el-input-number) {
  width: 100%;
}

.config-form :deep(.el-input-number .el-input__wrapper) {
  width: 100% !important;
  padding-left: 40px !important;
  padding-right: 40px !important;
}

.config-form :deep(.el-input-number .el-input__inner) {
  text-align: center !important;
  padding: 0 !important;
}

.config-form :deep(.el-date-editor) {
  width: 100%;
}

.config-form :deep(.el-date-editor .el-input__wrapper) {
  padding-left: 40px !important;
  padding-right: 12px !important;
}

.config-form :deep(.el-date-editor .el-input__inner) {
  padding-left: 40px !important;
  padding-right: 12px !important;
}

.config-form :deep(.el-date-editor .el-input__prefix) {
  left: 12px !important;
}

.config-form :deep(.el-date-editor .el-input__suffix) {
  right: 12px !important;
}

.form-tip {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3) var(--spacing-4);
  background: rgba(59, 130, 246, 0.08);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.8;
}

.form-tip .el-icon {
  font-size: 16px;
  color: var(--color-primary);
  margin-top: 2px;
  flex-shrink: 0;
}

.form-tip strong {
  color: var(--text-primary);
  font-weight: 600;
}

.form-tip a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.form-tip a:hover {
  text-decoration: underline;
}

.form-tip > div > div {
  margin-top: var(--spacing-1);
}

/* 按钮组样式增强 */
.config-form :deep(.el-space) {
  width: 100%;
  flex-wrap: wrap;
}

.config-form :deep(.el-button) {
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: 600;
  border-radius: var(--radius-lg);
  padding: 0 var(--spacing-6);
  transition: var(--transition-all);
}

.config-form :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

.config-form :deep(.el-button:active) {
  transform: translateY(0);
}

.config-form :deep(.el-button .el-icon) {
  font-size: 18px;
}

/* 日志表格样式增强 */
.logs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-spotlight);
  --el-table-row-hover-bg-color: var(--bg-hover);
  --el-table-border-color: var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.logs-table :deep(th.el-table__cell) {
  background-color: var(--bg-spotlight);
  color: var(--text-primary);
  font-weight: 700;
  font-size: var(--font-size-sm);
  padding: var(--spacing-4) var(--spacing-3);
  border-bottom: 2px solid var(--border-color);
}

.logs-table :deep(td.el-table__cell) {
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  padding: var(--spacing-3);
}

.logs-table :deep(.el-table__body tr:hover > td) {
  background-color: var(--bg-hover) !important;
}

.logs-table :deep(.el-tag) {
  font-weight: 600;
  border-radius: var(--radius-md);
  padding: var(--spacing-1) var(--spacing-2);
}

.stat-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  flex-wrap: wrap;
}

.stat-label {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}

.stat-value {
  color: var(--text-primary);
  font-weight: 700;
  font-size: var(--font-size-sm);
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--spacing-4) 0 0 0;
}

.table-footer .el-button {
  height: 36px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.table-footer .el-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* 响应式 */
@media (max-width: 768px) {
  .config-header {
    padding: var(--spacing-3) var(--spacing-4);
  }
  
  .config-title {
    font-size: var(--font-size-xl);
  }
  
  .config-description {
    font-size: var(--font-size-sm);
  }
  
  .tab-content {
    padding: var(--spacing-4);
  }
  
  .config-form {
    max-width: 100%;
  }

  .config-form :deep(.el-form-item__label) {
    width: 100px !important;
    font-size: var(--font-size-sm);
  }
  
  .config-form :deep(.el-button) {
    height: 40px;
    font-size: var(--font-size-sm);
    padding: 0 var(--spacing-4);
  }
  
  .config-tabs :deep(.el-tabs__item) {
    padding: var(--spacing-2) var(--spacing-4);
    font-size: var(--font-size-sm);
  }
  
  .logs-table :deep(th.el-table__cell),
  .logs-table :deep(td.el-table__cell) {
    padding: var(--spacing-2);
    font-size: var(--font-size-xs);
  }
}
</style>
