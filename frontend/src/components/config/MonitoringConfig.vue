<template>
  <div class="monitoring-config">

    <!-- 集群ID配置（资源分析 / bottom / APIServer告警共用） -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-primary">
            <el-icon :size="16"><Cpu /></el-icon>
          </div>
          集群ID配置
        </div>
      </div>
      <div class="bento-card-body">
        <div class="config-section">
          <label class="config-label">
            <el-icon><List /></el-icon>
            集群ID列表（每行一个）
          </label>
          <el-input
            v-model="clusterConfig.text"
            type="textarea"
            :rows="8"
            placeholder="请输入集群ID，每行一个&#10;例如：&#10;cce-3nusu9su&#10;cce-9m1ht29q"
            :disabled="!isAdmin"
          />
          <p class="config-hint">当前配置: {{ clusterConfig.ids.length }} 个集群ID（资源分析、bottom卡时、APIServer告警共用）</p>
        </div>
        <div class="action-row">
          <el-button
            type="success"
            @click="syncClusterIds"
            :loading="syncing.cluster"
            :disabled="!isAdmin"
          >
            <el-icon><Refresh /></el-icon>
            从 CCE API 同步
          </el-button>
          <el-button
            type="primary"
            @click="saveClusterConfig"
            :loading="saving.cluster"
            :disabled="!isAdmin"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- EIP监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-success">
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
        </div>
        <div class="action-row">
          <el-button
            type="success"
            @click="syncEipIds"
            :loading="syncing.eip"
            :disabled="!isAdmin"
          >
            <el-icon><Refresh /></el-icon>
            从 BCE API 同步
          </el-button>
          <el-button
            type="primary"
            @click="saveEipConfig"
            :loading="saving.eip"
            :disabled="!isAdmin"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- BCC监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-warning">
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
        </div>
        <div class="action-row">
          <el-button
            type="success"
            @click="syncBccIds"
            :loading="syncing.bcc"
            :disabled="!isAdmin"
          >
            <el-icon><Refresh /></el-icon>
            从 BCE API 同步
          </el-button>
          <el-button
            type="primary"
            @click="saveBccConfig"
            :loading="saving.bcc"
            :disabled="!isAdmin"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- BOS监控配置 -->
    <div class="bento-card">
      <div class="bento-card-header">
        <div class="bento-card-title">
          <div class="bento-card-title-icon icon-bg-primary">
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
        </div>
        <div class="action-row">
          <el-button
            type="success"
            @click="syncBosNames"
            :loading="syncing.bos"
            :disabled="!isAdmin"
          >
            <el-icon><Refresh /></el-icon>
            从 BCE API 同步
          </el-button>
          <el-button
            type="primary"
            @click="saveBosConfig"
            :loading="saving.bos"
            :disabled="!isAdmin"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Monitor, Coin, List, Check, Cpu, Refresh } from '@element-plus/icons-vue'
import * as configApi from '@/api/config'
import { getCCEClusterIds, getBCCInstanceIds, getEIPInstanceIds, getBOSBucketNames } from '@/api/cmdb'

const user = computed(() => JSON.parse(localStorage.getItem('user') || '{}'))
const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value.role))

// 配置数据
const clusterConfig = ref({ text: '', ids: [] })
const eipConfig = ref({ text: '', ids: [] })
const bccConfig = ref({ text: '', ids: [] })
const bosConfig = ref({ text: '', ids: [] })

// 保存 / 同步状态
const saving = ref({ cluster: false, eip: false, bcc: false, bos: false })
const syncing = ref({ cluster: false, eip: false, bcc: false, bos: false })

// 文本 → ID 数组
const parseIds = (text) =>
  text.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'))

watch(() => clusterConfig.value.text, t => { clusterConfig.value.ids = parseIds(t) })
watch(() => eipConfig.value.text,     t => { eipConfig.value.ids     = parseIds(t) })
watch(() => bccConfig.value.text,     t => { bccConfig.value.ids     = parseIds(t) })
watch(() => bosConfig.value.text,     t => { bosConfig.value.ids     = parseIds(t) })

// 加载配置
const loadConfig = async () => {
  try {
    // 集群ID 从 prometheus_runtime 加载
    const r1 = await configApi.loadConfig('prometheus_runtime')
    const c1 = r1.data?.config || r1.config || {}
    if (c1.cluster_ids) {
      clusterConfig.value.text = Array.isArray(c1.cluster_ids)
        ? c1.cluster_ids.join('\n')
        : String(c1.cluster_ids).replace(/,/g, '\n')
    }
  } catch { /* silent */ }

  try {
    // EIP / BCC / BOS 从 monitoring 加载
    const r2 = await configApi.loadConfig('monitoring')
    const c2 = r2.data?.config || r2.config || {}
    if (c2.eip_instance_ids)  eipConfig.value.text  = Array.isArray(c2.eip_instance_ids)  ? c2.eip_instance_ids.join('\n')  : String(c2.eip_instance_ids).replace(/,/g, '\n')
    if (c2.bcc_instance_ids)  bccConfig.value.text  = Array.isArray(c2.bcc_instance_ids)  ? c2.bcc_instance_ids.join('\n')  : String(c2.bcc_instance_ids).replace(/,/g, '\n')
    if (c2.bos_bucket_names)  bosConfig.value.text  = Array.isArray(c2.bos_bucket_names)  ? c2.bos_bucket_names.join('\n')  : String(c2.bos_bucket_names).replace(/,/g, '\n')
  } catch { /* silent */ }
}

// ——— 同步函数 ———

const syncClusterIds = async () => {
  syncing.value.cluster = true
  try {
    const res = await getCCEClusterIds()
    const ids = res.data?.cluster_ids || res.cluster_ids || []
    if (!ids.length) { ElMessage.warning('CCE API 未返回集群ID，请确认 AK/SK 已配置'); return }
    clusterConfig.value.text = ids.join('\n')
    ElMessage.success(`已同步 ${ids.length} 个集群ID，请点击保存`)
  } catch (e) {
    ElMessage.error('CCE API 同步失败：' + (e.response?.data?.detail || e.message))
  } finally { syncing.value.cluster = false }
}

const syncEipIds = async () => {
  syncing.value.eip = true
  try {
    const res = await getEIPInstanceIds()
    const ids = res.data?.instance_ids || res.instance_ids || []
    if (!ids.length) { ElMessage.warning('EIP API 未返回实例，请确认 AK/SK 已配置'); return }
    eipConfig.value.text = ids.join('\n')
    ElMessage.success(`已同步 ${ids.length} 个EIP ID，请点击保存`)
  } catch (e) {
    ElMessage.error('EIP API 同步失败：' + (e.response?.data?.detail || e.message))
  } finally { syncing.value.eip = false }
}

const syncBccIds = async () => {
  syncing.value.bcc = true
  try {
    const res = await getBCCInstanceIds()
    const ids = res.data?.instance_ids || res.instance_ids || []
    if (!ids.length) { ElMessage.warning('BCC API 未返回实例，请确认 AK/SK 已配置'); return }
    bccConfig.value.text = ids.join('\n')
    ElMessage.success(`已同步 ${ids.length} 个BCC实例ID，请点击保存`)
  } catch (e) {
    ElMessage.error('BCC API 同步失败：' + (e.response?.data?.detail || e.message))
  } finally { syncing.value.bcc = false }
}

const syncBosNames = async () => {
  syncing.value.bos = true
  try {
    const res = await getBOSBucketNames()
    const names = res.data?.bucket_names || res.bucket_names || []
    if (!names.length) { ElMessage.warning('BOS API 未返回 Bucket，请确认 AK/SK 已配置'); return }
    bosConfig.value.text = names.join('\n')
    ElMessage.success(`已同步 ${names.length} 个 Bucket 名称，请点击保存`)
  } catch (e) {
    ElMessage.error('BOS API 同步失败：' + (e.response?.data?.detail || e.message))
  } finally { syncing.value.bos = false }
}

// ——— 保存函数 ———

const saveClusterConfig = async () => {
  if (!isAdmin.value) return ElMessage.warning('仅管理员可以修改配置')
  if (!clusterConfig.value.ids.length) return ElMessage.warning('请至少输入一个集群ID')
  saving.value.cluster = true
  try {
    const r = await configApi.loadConfig('prometheus_runtime')
    const existing = r.data?.config || r.config || {}
    await configApi.saveConfig('prometheus_runtime', {
      ...existing,
      cluster_ids: clusterConfig.value.ids.join(',')
    })
    ElMessage.success(`集群ID配置保存成功（${clusterConfig.value.ids.length} 个）`)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value.cluster = false }
}

const saveEipConfig = async () => {
  if (!isAdmin.value) return ElMessage.warning('仅管理员可以修改配置')
  saving.value.eip = true
  try {
    const r = await configApi.loadConfig('monitoring')
    const existing = r.data?.config || r.config || {}
    await configApi.saveConfig('monitoring', { ...existing, eip_instance_ids: eipConfig.value.ids.join(',') })
    ElMessage.success(`EIP配置保存成功（${eipConfig.value.ids.length} 个）`)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value.eip = false }
}

const saveBccConfig = async () => {
  if (!isAdmin.value) return ElMessage.warning('仅管理员可以修改配置')
  saving.value.bcc = true
  try {
    const r = await configApi.loadConfig('monitoring')
    const existing = r.data?.config || r.config || {}
    await configApi.saveConfig('monitoring', { ...existing, bcc_instance_ids: bccConfig.value.ids.join(',') })
    ElMessage.success(`BCC配置保存成功（${bccConfig.value.ids.length} 个）`)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value.bcc = false }
}

const saveBosConfig = async () => {
  if (!isAdmin.value) return ElMessage.warning('仅管理员可以修改配置')
  saving.value.bos = true
  try {
    const r = await configApi.loadConfig('monitoring')
    const existing = r.data?.config || r.config || {}
    await configApi.saveConfig('monitoring', { ...existing, bos_bucket_names: bosConfig.value.ids.join(',') })
    ElMessage.success(`BOS配置保存成功（${bosConfig.value.ids.length} 个）`)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value.bos = false }
}

onMounted(loadConfig)
</script>

<style scoped>
.monitoring-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: var(--spacing-6);
}

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
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
}

.config-label .el-icon {
  font-size: var(--text-xl);
  color: var(--color-primary);
}

.config-hint {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-top: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.action-row {
  display: flex;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
}

.action-row .el-button {
  flex: 1;
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.action-row .el-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg);
}

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

.config-section :deep(.el-textarea__inner:focus) {
  border-color: var(--input-border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

@media (max-width: 1200px) {
  .monitoring-config { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .monitoring-config { gap: var(--spacing-4); }
}
</style>
