<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon"><el-icon><Warning /></el-icon></div>
          APIServer 告警列表
        </div>
        <div class="page-subtitle">查看已生成的 APIServer 指标告警，并进行状态管理处理</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="runAnalyze" :loading="analyzing">
          <el-icon><Refresh /></el-icon>
          立即检测
        </el-button>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header"><div class="content-card-title">筛选条件</div></div>
      <div class="content-card-body">
        <el-form :inline="true">
          <el-form-item label="集群ID"><el-input v-model="filters.cluster_id" clearable placeholder="请输入集群ID" /></el-form-item>
          <el-form-item label="严重程度">
            <el-select v-model="filters.severity" clearable style="width: 140px">
              <el-option label="critical" value="critical" />
              <el-option label="warning" value="warning" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" clearable style="width: 140px">
              <el-option label="处理中" value="processing" />
              <el-option label="已处理" value="resolved" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
          <el-form-item><el-button @click="fetchList">查询</el-button></el-form-item>
        </el-form>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">告警列表</div>
        <div class="content-card-extra">
          <el-tag type="info" style="margin-right: 8px">共 {{ total }} 条</el-tag>
          <el-button
            v-if="selectedAlerts.length > 0"
            type="warning"
            size="small"
            @click="openBatchStatusDialog"
          >
            批量修改状态（{{ selectedAlerts.length }}）
          </el-button>
        </div>
      </div>
      <div class="content-card-body">
        <el-table
          :data="rows"
          v-loading="loading"
          class="google-table"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="cluster_id" label="集群ID" min-width="180" />
          <el-table-column prop="metric_label" label="指标" min-width="180" />
          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="当前值" width="140">
            <template #default="{ row }">{{ row.current_value }} {{ row.unit || '' }}</template>
          </el-table-column>
          <el-table-column prop="description" label="影响描述" min-width="220" show-overflow-tooltip />
          <el-table-column label="iCafe" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.icafe_card_id" type="success" size="small">已建卡</el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="action-grid">
                <div class="action-row action-row-primary">
                  <button class="action-btn btn-primary" @click.stop="showDetail(row)">详情</button>
                  <button class="action-btn btn-primary" @click.stop="openResolveDialog(row)">修改状态</button>
                  <button class="action-btn btn-primary" @click.stop="openIcafeDialog(row)">建卡</button>
                </div>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-footer">
          <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" @current-change="fetchList" @size-change="fetchList" layout="total, sizes, prev, pager, next, jumper" />
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="APIServer 告警详情" width="800px" append-to-body>
      <el-descriptions :column="2" border v-if="current">
        <el-descriptions-item label="集群ID">{{ current.cluster_id }}</el-descriptions-item>
        <el-descriptions-item label="指标">{{ current.metric_label }}</el-descriptions-item>
        <el-descriptions-item label="严重程度">{{ current.severity }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(current.status)">{{ statusLabel(current.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="当前值">{{ current.current_value }} {{ current.unit || '' }}</el-descriptions-item>
        <el-descriptions-item label="阈值">W={{ current.warning_threshold }} / C={{ current.critical_threshold }}</el-descriptions-item>
        <el-descriptions-item label="影响描述" :span="2">{{ current.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="建议动作" :span="2">{{ current.suggestion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="PromQL" :span="2"><code class="code-block">{{ current.promql }}</code></el-descriptions-item>
        <el-descriptions-item label="处理人">{{ current.resolved_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处理结果">{{ current.resolution_result || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处理备注" :span="2">{{ current.resolution_notes || '-' }}</el-descriptions-item>
        <el-descriptions-item label="iCafe 卡片">
          <span v-if="current.icafe_card_id">{{ current.icafe_card_id }}</span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="恢复时间">{{ current.resolved_at || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button v-if="current && !current.icafe_card_id" type="primary" @click="openIcafeDialog(current); detailVisible = false">创建 iCafe 卡片</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 处理/状态弹窗 -->
    <el-dialog v-model="resolveVisible" title="修改告警状态" width="500px" append-to-body class="google-dialog">
      <el-form :model="resolveForm" label-position="top" class="google-form">
        <el-form-item label="当前状态">
          <el-tag :type="statusTagType(resolveForm.currentStatus)">{{ statusLabel(resolveForm.currentStatus) }}</el-tag>
        </el-form-item>
        <el-form-item label="新状态" required>
          <el-select v-model="resolveForm.status" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="处理中" value="processing" />
            <el-option label="已处理" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理结果">
          <el-select v-model="resolveForm.resolution_result" clearable placeholder="请选择处理结果" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="已修复" value="fixed" />
            <el-option label="误报" value="false_alarm" />
            <el-option label="已知问题" value="known_issue" />
            <el-option label="待观察" value="monitoring" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理备注">
          <el-input v-model="resolveForm.resolution_notes" type="textarea" :rows="4" placeholder="请输入处理备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveVisible = false">取消</el-button>
        <el-button type="primary" :loading="resolveLoading" @click="submitResolve">确认</el-button>
      </template>
    </el-dialog>

    <!-- 批量修改状态弹窗 -->
    <el-dialog v-model="batchStatusVisible" title="批量修改告警状态" width="440px" append-to-body class="google-dialog">
      <el-form :model="batchStatusForm" label-position="top" class="google-form">
        <el-form-item label="已选择告警数量">
          <el-tag type="info">{{ selectedAlerts.length }} 条</el-tag>
        </el-form-item>
        <el-form-item label="新状态" required>
          <el-select v-model="batchStatusForm.status" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="处理中" value="processing" />
            <el-option label="已处理" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchStatusVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchStatusLoading" @click="submitBatchStatus">确认</el-button>
      </template>
    </el-dialog>

    <!-- 创建 iCafe 卡片弹窗 -->
    <el-dialog v-model="icafeVisible" title="创建 iCafe 卡片" width="700px" append-to-body class="google-dialog" :close-on-click-modal="false">
      <el-form :model="icafeForm" label-position="top" class="google-form" :rules="icafeFormRules" ref="icafeFormRef">
        <!-- 告警信息展示 -->
        <el-form-item label="告警信息">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="集群ID">{{ icafeForm.clusterID }}</el-descriptions-item>
            <el-descriptions-item label="严重程度">{{ icafeForm.severity }}</el-descriptions-item>
            <el-descriptions-item label="指标">{{ icafeForm.metricLabel }}</el-descriptions-item>
          </el-descriptions>
        </el-form-item>

        <!-- 自动生成的卡片标题 -->
        <el-form-item label="卡片标题">
          <el-input v-model="icafeForm.generatedTitle" readonly />
        </el-form-item>

        <!-- 卡片类型选择 -->
        <el-form-item label="卡片类型" required>
          <el-radio-group v-model="icafeForm.card_type">
            <el-radio label="Bug">Bug（故障）</el-radio>
            <el-radio label="Task">Task（任务）</el-radio>
          </el-radio-group>
          <div class="form-tip">
            <span v-if="icafeForm.card_type === 'Bug'">用于跟踪 APIServer 故障和问题修复</span>
            <span v-else>用于 APIServer 运维任务和工作项</span>
          </div>
        </el-form-item>

        <!-- Task类型特有字段 -->
        <template v-if="icafeForm.card_type === 'Task'">
          <el-form-item label="方向大类" required>
            <el-select v-model="icafeForm.direction" placeholder="请选择方向大类" style="width: 100%" teleported popper-class="dialog-select-popper">
              <el-option label="硬件" value="硬件" />
              <el-option label="计算" value="计算" />
              <el-option label="虚拟网络" value="虚拟网络" />
              <el-option label="存储" value="存储" />
              <el-option label="数据库" value="数据库" />
              <el-option label="K8S" value="K8S" />
            </el-select>
          </el-form-item>
          <el-form-item label="汇总分类" required>
            <el-select v-model="icafeForm.category" placeholder="请选择汇总分类" style="width: 100%" teleported popper-class="dialog-select-popper">
              <el-option label="运维事件" value="运维事件" />
              <el-option label="产品咨询" value="产品咨询" />
              <el-option label="内部事务" value="内部事务" />
              <el-option label="运营对接" value="运营对接" />
              <el-option label="产品需求" value="产品需求" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 手动填写字段 -->
        <el-form-item label="负责人" prop="responsible_person" required>
          <el-input v-model="icafeForm.responsible_person" placeholder="请输入负责人姓名" maxlength="50" />
        </el-form-item>

        <el-form-item label="细分分类" prop="subcategory" required>
          <el-input v-model="icafeForm.subcategory" placeholder="例如：BCC,GPU" maxlength="100" />
          <div class="form-tip">多个分类用逗号分隔，例如：BCC,GPU</div>
        </el-form-item>

        <el-form-item label="工时" prop="work_hours" required>
          <el-input-number
            v-model="icafeForm.work_hours"
            :min="0.1"
            :max="999"
            :step="0.1"
            :precision="1"
            placeholder="请输入预估工时"
            style="width: 200px"
          />
          <span style="margin-left: 8px; color: var(--text-tertiary);">小时</span>
        </el-form-item>

        <!-- 下拉选择字段 -->
        <el-form-item label="所属计划" prop="plan" required>
          <el-select v-model="icafeForm.plan" placeholder="请选择所属计划" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="2026/2026Q1" value="2026/2026Q1" />
            <el-option label="2026/2026Q2" value="2026/2026Q2" />
            <el-option label="2026/2026Q3" value="2026/2026Q3" />
            <el-option label="2026/2026Q4" value="2026/2026Q4" />
          </el-select>
        </el-form-item>

        <!-- 固定字段展示 -->
        <el-form-item label="固定字段">
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="有感事件">否</el-descriptions-item>
            <el-descriptions-item label="TAM负责人">陈少禄</el-descriptions-item>
            <el-descriptions-item label="汇总分类">运维事件</el-descriptions-item>
          </el-descriptions>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="icafeVisible = false">取消</el-button>
          <el-button type="primary" :loading="icafeLoading" @click="submitIcafe">创建卡片</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Warning } from '@element-plus/icons-vue'
import {
  analyzeAPIServerAlerts,
  batchUpdateAPIServerAlertStatus,
  createAPIServerIcafeCard,
  getAPIServerAlertDetail,
  getAPIServerAlerts,
  updateAPIServerAlertStatus,
} from '@/api/apiserverAlerts'
import { pollTaskStatus } from '@/utils/taskPoller'

const loading = ref(false)
const analyzing = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const current = ref(null)
const filters = reactive({ cluster_id: '', severity: '', status: '' })
const selectedAlerts = ref([])

// 处理弹窗
const resolveVisible = ref(false)
const resolveLoading = ref(false)
const resolveTarget = ref(null)
const resolveForm = reactive({ currentStatus: '', status: 'processing', resolution_notes: '', resolution_result: '' })

// 批量状态弹窗
const batchStatusVisible = ref(false)
const batchStatusLoading = ref(false)
const batchStatusForm = reactive({ status: 'processing' })

// iCafe 弹窗
const icafeVisible = ref(false)
const icafeLoading = ref(false)
const icafeTarget = ref(null)
const icafeFormRef = ref(null)
const icafeForm = reactive({
  card_type: 'Bug',
  clusterID: '',
  severity: '',
  metricLabel: '',
  generatedTitle: '',
  direction: '',
  category: '',
  responsible_person: '',
  subcategory: '',
  work_hours: 1.0,
  plan: '2026/2026Q1',
})

const icafeFormRules = {
  responsible_person: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  subcategory: [{ required: true, message: '请输入细分分类', trigger: 'blur' }],
  work_hours: [{ required: true, message: '请输入工时', trigger: 'change' }],
  plan: [{ required: true, message: '请选择所属计划', trigger: 'change' }],
}

const statusLabel = (status) => {
  const map = { processing: '处理中', resolved: '已处理', closed: '已关闭' }
  return map[status] || status
}

const statusTagType = (status) => {
  if (status === 'resolved') return 'success'
  if (status === 'processing') return 'warning'
  if (status === 'closed') return 'info'
  return 'danger'
}

const handleSelectionChange = (rows) => {
  selectedAlerts.value = rows
}

const fetchList = async () => {
  loading.value = true
  try {
    const response = await getAPIServerAlerts({ page: page.value, page_size: pageSize.value, ...filters })
    rows.value = response.data?.list || []
    total.value = response.data?.total || 0
  } catch {
    ElMessage.error('获取 APIServer 告警失败')
  } finally {
    loading.value = false
  }
}

const runAnalyze = async () => {
  analyzing.value = true
  try {
    const response = await analyzeAPIServerAlerts()
    if (!response.success) throw new Error(response.error || response.message)
    const taskId = response.data.task_id
    ElMessage.success('检测任务已创建')
    pollTaskStatus(taskId, () => {}, async () => {
      analyzing.value = false
      ElMessage.success('APIServer 告警检测完成')
      await fetchList()
    }, (error) => {
      analyzing.value = false
      ElMessage.error(error || '检测失败')
    })
  } catch (error) {
    analyzing.value = false
    ElMessage.error(error.message || '创建检测任务失败')
  }
}

const showDetail = async (row) => {
  const response = await getAPIServerAlertDetail(row.id)
  if (response.success) {
    current.value = response.data
    detailVisible.value = true
  }
}

const openResolveDialog = (row) => {
  resolveTarget.value = row
  resolveForm.currentStatus = row.status
  resolveForm.status = 'processing'
  resolveForm.resolution_notes = ''
  resolveForm.resolution_result = ''
  resolveVisible.value = true
}

const submitResolve = async () => {
  resolveLoading.value = true
  try {
    const payload = {
      status: resolveForm.status,
      resolution_notes: resolveForm.resolution_notes || undefined,
      resolution_result: resolveForm.resolution_result || undefined,
    }
    const response = await updateAPIServerAlertStatus(resolveTarget.value.id, payload)
    if (response.success) {
      ElMessage.success('处理成功')
      resolveVisible.value = false
      fetchList()
    } else {
      ElMessage.error(response.error || '处理失败')
    }
  } catch {
    ElMessage.error('处理失败')
  } finally {
    resolveLoading.value = false
  }
}

const openBatchStatusDialog = () => {
  batchStatusForm.status = 'processing'
  batchStatusVisible.value = true
}

const submitBatchStatus = async () => {
  batchStatusLoading.value = true
  try {
    const alertIds = selectedAlerts.value.map(r => r.id)
    const response = await batchUpdateAPIServerAlertStatus({ alert_ids: alertIds, status: batchStatusForm.status })
    if (response.success) {
      ElMessage.success(response.message || '批量更新成功')
      batchStatusVisible.value = false
      selectedAlerts.value = []
      fetchList()
    } else {
      ElMessage.error(response.error || '批量更新失败')
    }
  } catch {
    ElMessage.error('批量更新失败')
  } finally {
    batchStatusLoading.value = false
  }
}

const openIcafeDialog = (row) => {
  icafeTarget.value = row
  icafeForm.card_type = 'Bug'
  icafeForm.clusterID = row.cluster_id || ''
  icafeForm.severity = row.severity || ''
  icafeForm.metricLabel = row.metric_label || ''
  icafeForm.generatedTitle = `[APIServer] ${row.severity?.toUpperCase() || ''} - ${row.cluster_id || ''} - ${row.metric_label || ''}`
  icafeForm.direction = ''
  icafeForm.category = ''
  icafeForm.responsible_person = ''
  icafeForm.subcategory = ''
  icafeForm.work_hours = 1.0
  icafeForm.plan = '2026/2026Q1'
  icafeVisible.value = true
}

const submitIcafe = async () => {
  if (!icafeFormRef.value) return
  try {
    await icafeFormRef.value.validate()
  } catch {
    return
  }
  icafeLoading.value = true
  try {
    const payload = {
      card_type: icafeForm.card_type,
      responsible_person: icafeForm.responsible_person,
      subcategory: icafeForm.subcategory,
      work_hours: icafeForm.work_hours,
      plan: icafeForm.plan,
    }
    if (icafeForm.card_type === 'Task') {
      payload.direction = icafeForm.direction
      payload.category = icafeForm.category
    }
    const response = await createAPIServerIcafeCard(icafeTarget.value.id, payload)
    if (response.success) {
      ElMessage.success('iCafe 卡片创建成功')
      icafeVisible.value = false
      fetchList()
    } else {
      ElMessage.error(response.error || 'iCafe 卡片创建失败')
    }
  } catch {
    ElMessage.error('iCafe 卡片创建失败')
  } finally {
    icafeLoading.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.code-block { white-space: pre-wrap; word-break: break-word; display:block; }
.text-muted { color: var(--text-tertiary); font-size: var(--text-sm); }
.form-tip { font-size: var(--text-sm); color: var(--text-tertiary); margin-top: 4px; }

.action-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.action-row {
  display: flex;
  gap: 4px;
}
.action-btn {
  flex: 1;
  padding: 3px 0;
  border: none;
  border-radius: 4px;
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
}
.action-btn:hover { opacity: 0.8; }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary { background: var(--color-primary-50); color: var(--color-primary-600); }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-secondary); }
</style>
