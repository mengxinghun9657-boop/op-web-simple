<template>
  <div class="pfs-config">
    <div class="config-header">
      <h2 class="config-title">
        <el-icon><Folder /></el-icon>
        PFS 监控配置
      </h2>
      <p class="config-description">配置 PFS（并行文件系统）监控的 Prometheus 连接信息和查询参数。</p>
    </div>

    <el-form :model="configForm" label-width="140px" class="config-form">
      <!-- Grafana URL -->
      <el-form-item label="Grafana URL">
        <el-input
          v-model="configForm.grafana_url"
          placeholder="https://cprom.cd.baidubce.com/select/prometheus"
          :disabled="!isEditing"
        />
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          Prometheus API 的基础 URL
        </div>
      </el-form-item>

      <!-- Token -->
      <el-form-item label="认证 Token">
        <el-input
          v-model="configForm.token"
          type="textarea"
          :rows="4"
          placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
          :disabled="!isEditing"
          show-password
        />
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          用于 Prometheus API 认证的 JWT Token
        </div>
      </el-form-item>

      <!-- Instance ID -->
      <el-form-item label="Instance ID">
        <el-input
          v-model="configForm.instance_id"
          placeholder="cprom-pmdfwwqqln0w7"
          :disabled="!isEditing"
        />
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          Prometheus 实例 ID（用于请求头）
        </div>
      </el-form-item>

      <!-- PFS Instance IDs -->
      <el-form-item label="PFS 集群 ID">
        <el-select
          v-model="configForm.pfs_instance_ids"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="请输入或选择 PFS 集群 ID（支持多个）"
          :disabled="!isEditing"
          style="width: 100%;"
        >
          <el-option
            v-for="id in commonPfsIds"
            :key="id"
            :label="id"
            :value="id"
          />
        </el-select>
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          要监控的 PFS 集群 ID（支持多个，如 pfs-mTYGr6, pfs-abc123）
        </div>
      </el-form-item>

      <!-- Region -->
      <el-form-item label="区域">
        <el-select
          v-model="configForm.region"
          placeholder="请选择区域"
          :disabled="!isEditing"
          style="width: 100%;"
        >
          <el-option label="成都（cd）" value="cd" />
          <el-option label="北京（bj）" value="bj" />
          <el-option label="广州（gz）" value="gz" />
        </el-select>
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          PFS 实例所在区域
        </div>
      </el-form-item>

      <!-- Instance Type -->
      <el-form-item label="实例类型">
        <el-input
          v-model="configForm.instance_type"
          placeholder="plusl2"
          :disabled="!isEditing"
        />
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          PFS 实例类型（如 plusl2）
        </div>
      </el-form-item>

      <!-- Step -->
      <el-form-item label="查询步长">
        <el-select
          v-model="configForm.step"
          placeholder="请选择步长"
          :disabled="!isEditing"
          style="width: 100%;"
        >
          <el-option label="1 分钟" value="1m" />
          <el-option label="5 分钟" value="5m" />
          <el-option label="15 分钟" value="15m" />
          <el-option label="1 小时" value="1h" />
        </el-select>
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          Prometheus 查询的时间步长（默认 5m）
        </div>
      </el-form-item>

      <!-- Default Client -->
      <el-form-item label="默认客户端过滤">
        <el-input
          v-model="configForm.default_client"
          placeholder=".*"
          :disabled="!isEditing"
        />
        <div class="form-tip">
          <el-icon><InfoFilled /></el-icon>
          默认的客户端过滤规则（.* 表示所有客户端）
        </div>
      </el-form-item>

      <!-- 操作按钮 -->
      <el-form-item>
        <el-space>
          <el-button
            type="primary"
            :loading="testing"
            :disabled="!configForm.grafana_url || !configForm.token || testing"
            @click="handleTestConnection"
          >
            <el-icon><CircleCheck /></el-icon>
            测试连接
          </el-button>
          <el-button
            type="success"
            :loading="saving"
            :disabled="!isEditing"
            @click="handleSaveConfig"
          >
            <el-icon><Select /></el-icon>
            保存配置
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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Folder,
  InfoFilled,
  CircleCheck,
  Select,
  Edit,
  Close
} from '@element-plus/icons-vue'
import * as configApi from '@/api/config'
import * as pfsApi from '@/api/pfs'

// 配置表单
const configForm = ref({
  grafana_url: 'https://cprom.cd.baidubce.com/select/prometheus',
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lc3BhY2UiOiJjcHJvbS1wbWRmd3dxcWxuMHc3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0OTAxMzI4NzY4LCJpc3MiOiJjcHJvbSJ9.xMrMQgaV1Hb0WwF04sTFFTaMWyfqoutB4670dTpIIHA',
  instance_id: 'cprom-pmdfwwqqln0w7',
  pfs_instance_ids: ['pfs-mTYGr6'],  // 改为数组
  region: 'cd',
  instance_type: 'plusl2',
  step: '5m',
  default_client: '.*'
})

// 常用的 PFS 集群 ID（可以预设一些）
const commonPfsIds = ref([
  'pfs-mTYGr6',
  'pfs-abc123',
  'pfs-test01'
])

// 加载状态
const testing = ref(false)
const saving = ref(false)
const isEditing = ref(false)

// 原始配置（用于取消编辑）
const originalConfig = ref({})

// 加载 PFS 配置
const loadConfig = async () => {
  try {
    const response = await configApi.loadConfig('pfs')
    console.log('PFS 配置响应:', response)
    
    // 统一响应格式处理：response.data.config
    const config = response.data?.config || response.config || {}
    
    if (config && Object.keys(config).length > 0) {
      // 向后兼容：如果是单个ID，转换为数组
      let pfsIds = config.pfs_instance_ids || []
      if (!pfsIds.length && config.pfs_instance_id) {
        pfsIds = [config.pfs_instance_id]
      }
      
      configForm.value = {
        grafana_url: config.grafana_url || configForm.value.grafana_url,
        token: config.token || configForm.value.token,  // 保留默认值
        instance_id: config.instance_id || configForm.value.instance_id,
        pfs_instance_ids: pfsIds.length ? pfsIds : configForm.value.pfs_instance_ids,
        region: config.region || configForm.value.region,
        instance_type: config.instance_type || configForm.value.instance_type,
        step: config.step || configForm.value.step,
        default_client: config.default_client || configForm.value.default_client
      }
      
      // 保存原始配置
      originalConfig.value = JSON.parse(JSON.stringify(configForm.value))
      
      console.log('✅ PFS 配置加载成功:', configForm.value)
    } else {
      console.log('⚠️  未找到 PFS 配置，使用默认值')
      // 保存默认配置
      originalConfig.value = JSON.parse(JSON.stringify(configForm.value))
    }
  } catch (error) {
    console.error('加载 PFS 配置失败:', error)
    ElMessage.warning('加载配置失败，使用默认配置')
    // 保存默认配置
    originalConfig.value = JSON.parse(JSON.stringify(configForm.value))
  }
}

// 测试连接
const handleTestConnection = async () => {
  if (!configForm.value.grafana_url || !configForm.value.token) {
    ElMessage.warning('请先填写 Grafana URL 和 Token')
    return
  }

  testing.value = true
  try {
    // 先保存配置到数据库（测试连接需要从数据库读取配置）
    const configData = {
      grafana_url: configForm.value.grafana_url,
      token: configForm.value.token,
      instance_id: configForm.value.instance_id,
      pfs_instance_ids: configForm.value.pfs_instance_ids,
      region: configForm.value.region,
      instance_type: configForm.value.instance_type,
      step: configForm.value.step,
      default_client: configForm.value.default_client
    }

    await configApi.saveConfig('pfs', configData)
    
    // 调用测试连接 API
    const response = await pfsApi.testConnection()

    if (response.success) {
      ElMessage.success(response.message || '连接测试成功！')
      console.log('连接详情:', response.data)
    } else {
      ElMessage.error(response.error || '连接测试失败')
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    ElMessage.error('连接测试失败：' + (error.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

// 保存配置
const handleSaveConfig = async () => {
  saving.value = true
  try {
    const configData = {
      grafana_url: configForm.value.grafana_url,
      token: configForm.value.token,
      instance_id: configForm.value.instance_id,
      pfs_instance_ids: configForm.value.pfs_instance_ids,
      region: configForm.value.region,
      instance_type: configForm.value.instance_type,
      step: configForm.value.step,
      default_client: configForm.value.default_client
    }

    await configApi.saveConfig('pfs', configData)
    
    // 更新原始配置
    originalConfig.value = JSON.parse(JSON.stringify(configForm.value))
    isEditing.value = false
    
    ElMessage.success('PFS 配置保存成功！')
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败：' + error.message)
  } finally {
    saving.value = false
  }
}

// 取消编辑
const handleCancelEdit = () => {
  configForm.value = JSON.parse(JSON.stringify(originalConfig.value))
  isEditing.value = false
  ElMessage.info('已取消编辑')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.pfs-config {
  padding: var(--spacing-6);
}

.config-header {
  margin-bottom: var(--spacing-6);
}

.config-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2) 0;
}

.config-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

.config-form {
  max-width: 800px;
}

.form-tip {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  margin-top: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.form-tip .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--color-info);
}

.form-tip div {
  flex: 1;
}

.form-tip a {
  color: var(--color-primary);
  text-decoration: none;
}

.form-tip a:hover {
  text-decoration: underline;
}
</style>
