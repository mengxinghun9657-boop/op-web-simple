<template>
  <div class="bce-sync-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>BCE 数据同步配置</span>
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存配置
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <!-- 基本配置 Tab -->
        <el-tab-pane label="基本配置" name="basic">
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="120px"
            @submit.prevent="handleSave"
          >
            <el-form-item label="BCE Cookie" prop="bce_cookie" required>
              <el-input
                v-model="form.bce_cookie"
                type="textarea"
                :rows="3"
                placeholder="请输入 BCE Cookie"
                show-password
              />
              <div class="form-tip">
                从百度云控制台获取 Cookie，用于访问 BCC/CCE API
              </div>
            </el-form-item>

            <el-form-item label="区域" prop="region">
              <el-select v-model="form.region" placeholder="选择区域">
                <el-option label="成都" value="cd" />
                <el-option label="北京" value="bj" />
                <el-option label="广州" value="gz" />
                <el-option label="上海" value="sh" />
              </el-select>
              <div class="form-tip">选择 BCE 所在区域</div>
            </el-form-item>

            <el-form-item label="CCE 集群" prop="cluster_ids">
              <el-select
                v-model="form.cluster_ids"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入或选择集群 ID"
                style="width: 100%"
              >
                <el-option
                  v-for="id in defaultClusterIds"
                  :key="id"
                  :label="id"
                  :value="id"
                />
              </el-select>
              <div class="form-tip">选择需要同步的 CCE 集群（可多选）</div>
            </el-form-item>

            <el-form-item label="测试连接">
              <el-button @click="handleTestConnection" :loading="testing">
                测试连接
              </el-button>
              <span v-if="testResult" :class="testResultClass" style="margin-left: 12px;">
                {{ testResult }}
              </span>
            </el-form-item>

            <el-divider />

            <el-form-item>
              <el-button type="primary" @click="handleSync" :loading="syncing" size="large">
                <el-icon><Refresh /></el-icon>
                立即同步
              </el-button>
              <span v-if="syncResult" :class="syncResultClass" style="margin-left: 12px;">
                {{ syncResult }}
              </span>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 自动同步 Tab -->
        <el-tab-pane label="自动同步" name="sync">
          <el-form label-width="120px">
            <el-form-item label="启用自动同步">
              <el-switch v-model="syncConfig.enabled" active-text="启用" inactive-text="禁用" />
              <div class="form-tip">开启后，系统将按设定间隔自动同步 BCE 数据</div>
            </el-form-item>

            <el-form-item label="同步间隔" v-if="syncConfig.enabled">
              <el-input-number
                v-model="syncIntervalHours"
                :min="1"
                :max="24"
                :step="1"
                style="width: 200px"
              />
              <span style="margin-left: 8px;">小时</span>
              <div class="form-tip">
                同步间隔范围 1-24 小时，建议设置为 1 小时
              </div>
            </el-form-item>

            <el-form-item label="同步内容" v-if="syncConfig.enabled">
              <el-checkbox v-model="syncConfig.auto_sync_bcc">BCC 实例</el-checkbox>
              <el-checkbox v-model="syncConfig.auto_sync_cce">CCE 节点</el-checkbox>
              <div class="form-tip">选择需要自动同步的数据类型</div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSaveSyncConfig" :loading="savingSync">
                保存同步配置
              </el-button>
            </el-form-item>

            <el-divider />

            <el-form-item label="上次同步">
              <span v-if="syncConfig.last_sync_time">{{ formatTime(syncConfig.last_sync_time) }}</span>
              <span v-else style="color: #909399;">暂无记录</span>
            </el-form-item>

            <el-form-item label="下次同步">
              <span v-if="syncConfig.next_sync_time">{{ formatTime(syncConfig.next_sync_time) }}</span>
              <span v-else style="color: #909399;">--</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 数据统计 Tab -->
        <el-tab-pane label="数据统计" name="stats">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="BCC 实例数">
              {{ stats.bcc_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="BCC 最新采集">
              {{ stats.bcc_latest_date || '暂无数据' }}
            </el-descriptions-item>
            <el-descriptions-item label="CCE 节点数">
              {{ stats.cce_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="CCE 最新采集">
              {{ stats.cce_latest_date || '暂无数据' }}
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 20px;">
            <el-button type="primary" @click="loadStats" :loading="loadingStats">
              <el-icon><Refresh /></el-icon>
              刷新统计
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 使用说明 -->
      <el-divider content-position="left">使用说明</el-divider>
      <div class="usage-info">
        <el-alert title="配置说明" type="info" :closable="false" show-icon>
          <ul>
            <li>BCE 数据同步用于将百度云 BCC 实例和 CCE 节点数据导入本地数据库</li>
            <li>配置 Cookie 后，系统可通过百度云控制台 API 下载实例数据</li>
            <li>同步后的数据可用于服务器关联查询、资源统计等功能</li>
            <li>建议定期同步以保持数据最新（可配置自动同步）</li>
          </ul>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getBCEConfig,
  updateBCEConfig,
  syncBCE,
  getBCEStats,
  testBCEConnection,
  getBCESyncConfig,
  updateBCESyncConfig
} from '@/api/cmdb'

// 默认集群 ID 列表
const defaultClusterIds = [
  'cce-266b50jq', 'cce-3nusu9su', 'cce-9m1ht29q', 'cce-elwhlymq',
  'cce-48c915gn', 'cce-ld2ckre2', 'cce-216ima4l', 'cce-2ys5dxch',
  'cce-75n0j16r', 'cce-hcbs74xg', 'cce-xrg955qz', 'cce-pog0r4mg',
  'cce-gzk0qlzk', 'cce-p6w3c5z8', 'cce-uk1zi507', 'cce-k5sn275j',
  'cce-4nmy1x1s'
]

// 当前激活的 Tab
const activeTab = ref('basic')

// 表单数据
const form = reactive({
  bce_cookie: '',
  region: 'cd',
  cluster_ids: []
})

// 同步配置
const syncConfig = reactive({
  enabled: false,
  sync_interval: 3600,
  auto_sync_bcc: true,
  auto_sync_cce: true,
  last_sync_time: null,
  next_sync_time: null
})

// 计算属性：同步间隔（小时）
const syncIntervalHours = computed({
  get() {
    return Math.floor(syncConfig.sync_interval / 3600)
  },
  set(val) {
    syncConfig.sync_interval = val * 3600
  }
})

// 统计数据
const stats = reactive({
  bcc_count: 0,
  bcc_latest_date: null,
  cce_count: 0,
  cce_latest_date: null
})

// 状态
const formRef = ref(null)
const saving = ref(false)
const savingSync = ref(false)
const syncing = ref(false)
const loadingStats = ref(false)
const testing = ref(false)
const testResult = ref('')
const testResultClass = ref('')
const syncResult = ref('')
const syncResultClass = ref('')

// 表单验证规则
const rules = {
  bce_cookie: [
    { required: true, message: '请输入 BCE Cookie', trigger: 'blur' }
  ],
  region: [
    { required: true, message: '请选择区域', trigger: 'change' }
  ]
}

// 加载配置
const loadConfig = async () => {
  try {
    const response = await getBCEConfig()
    if (response.cookie_configured) {
      // Cookie 已配置，显示预览
      form.bce_cookie = response.cookie_preview || ''
    }
    form.region = response.region || 'cd'
    form.cluster_ids = response.cluster_ids || []
  } catch (error) {
    console.error('加载 BCE 配置失败:', error)
  }
}

// 加载同步配置
const loadSyncConfig = async () => {
  try {
    const response = await getBCESyncConfig()
    if (response.success && response.data) {
      Object.assign(syncConfig, response.data)
    }
  } catch (error) {
    console.error('加载同步配置失败:', error)
  }
}

// 加载统计数据
const loadStats = async () => {
  try {
    loadingStats.value = true
    const response = await getBCEStats()
    console.log('BCE Stats Response:', response)
    
    // 确保数据正确赋值
    stats.bcc_count = response.bcc_count || 0
    stats.bcc_latest_date = response.bcc_latest_date || null
    stats.cce_count = response.cce_count || 0
    stats.cce_latest_date = response.cce_latest_date || null
    
    console.log('Updated Stats:', stats)
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

// 保存配置
const handleSave = async () => {
  try {
    await formRef.value.validate()

    saving.value = true

    const configData = {
      cookie: form.bce_cookie,
      region: form.region,
      cluster_ids: form.cluster_ids
    }

    await updateBCEConfig(configData)
    ElMessage.success('BCE 配置保存成功')
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存 BCE 配置失败:', error)
      ElMessage.error('保存配置失败')
    }
  } finally {
    saving.value = false
  }
}

// 保存同步配置
const handleSaveSyncConfig = async () => {
  try {
    savingSync.value = true

    const configData = {
      enabled: syncConfig.enabled,
      sync_interval: syncConfig.sync_interval,
      auto_sync_bcc: syncConfig.auto_sync_bcc,
      auto_sync_cce: syncConfig.auto_sync_cce
    }

    const response = await updateBCESyncConfig(configData)
    if (response.success) {
      ElMessage.success('同步配置保存成功')
      // 刷新配置
      await loadSyncConfig()
    } else {
      ElMessage.error(response.message || '保存失败')
    }
  } catch (error) {
    console.error('保存同步配置失败:', error)
    ElMessage.error('保存同步配置失败')
  } finally {
    savingSync.value = false
  }
}

// 测试连接
const handleTestConnection = async () => {
  try {
    await formRef.value.validate()

    testing.value = true
    testResult.value = ''

    // 使用当前表单数据测试连接
    const testConfig = {
      bce_cookie: form.bce_cookie,
      region: form.region
    }

    const response = await testBCEConnection(testConfig)

    if (response.success) {
      testResult.value = '✅ 连接测试成功'
      testResultClass.value = 'test-success'
    } else {
      testResult.value = `❌ 连接测试失败：${response.error || response.message}`
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

// 立即同步
const handleSync = async () => {
  try {
    syncing.value = true
    syncResult.value = ''
    
    const response = await syncBCE('all')
    if (response.success) {
      syncResult.value = '✅ 同步成功'
      syncResultClass.value = 'test-success'
      ElMessage.success('BCE 数据同步成功')
      // 同步完成后刷新统计数据
      await loadStats()
    } else {
      syncResult.value = `❌ 同步失败：${response.message || '未知错误'}`
      syncResultClass.value = 'test-error'
      ElMessage.error(response.message || '同步失败')
    }
  } catch (error) {
    console.error('同步失败:', error)
    syncResult.value = `❌ 同步失败：${error.message || '未知错误'}`
    syncResultClass.value = 'test-error'
    ElMessage.error('同步失败')
  } finally {
    syncing.value = false
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '--'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

// 初始化
onMounted(() => {
  loadConfig()
  loadSyncConfig()
  loadStats()
})
</script>

<style scoped>
.bce-sync-config {
  max-width: 900px;
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
