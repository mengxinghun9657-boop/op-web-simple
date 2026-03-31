<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Document /></el-icon>
          </div>
          告警详情
        </div>
      </div>
      <div class="page-actions">
        <el-button @click="handleBack">
          <el-icon><ArrowLeft /></el-icon>返回
        </el-button>
      </div>
    </div>

    <div v-loading="loading">
      <template v-if="!loading && alertData">
        <!-- 基本信息卡片 -->
        <div class="content-card">
          <div class="content-card-header">
            <div class="content-card-title">基本信息</div>
            <div class="content-card-extra">
              <el-button
                type="warning"
                size="small"
                @click="handleDiagnose"
                :loading="diagnosing"
              >
                <el-icon><Refresh /></el-icon>
                重新诊断
              </el-button>
            </div>
          </div>
          <div class="content-card-body">

          <el-descriptions :column="2" border>
            <el-descriptions-item label="告警ID">
              {{ alertData.alert.id }}
            </el-descriptions-item>
            <el-descriptions-item label="告警类型" :span="1">
              <div class="alert-types-container">
                <template v-if="alertData.diagnosis && alertData.diagnosis.fault_items && alertData.diagnosis.fault_items.length > 0">
                  <el-tag
                    v-for="(fault, index) in getUniqueFaultTypes(alertData.diagnosis.fault_items)"
                    :key="index"
                    :type="getFaultTagType(fault.severity)"
                    size="small"
                    class="alert-type-tag"
                  >
                    {{ fault.device ? fault.device + '-' : '' }}{{ fault.alert_type }}
                  </el-tag>
                </template>
                <template v-else-if="parsedAlertTypes.length > 0">
                  <el-tag
                    v-for="(fault, index) in parsedAlertTypes"
                    :key="index"
                    :type="getFaultTagType(fault.severity)"
                    size="small"
                    class="alert-type-tag"
                  >
                    {{ fault.device ? fault.device + '-' : '' }}{{ fault.alert_type }}
                  </el-tag>
                </template>
                <template v-else>
                  {{ alertData.alert.alert_type }}
                </template>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="组件类型">
              <el-tag :type="getComponentTagType(alertData.alert.component)">
                {{ alertData.alert.component }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="严重程度">
              <el-tag :type="getSeverityTagType(alertData.alert.severity)">
                {{ alertData.alert.severity }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="节点IP">
              {{ alertData.alert.ip || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="主机名">
              {{ alertData.alert.hostname || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="集群ID">
              {{ alertData.alert.cluster_id || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="实例ID">
              {{ alertData.alert.instance_id || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="发生时间">
              {{ formatDateTime(alertData.alert.timestamp) }}
            </el-descriptions-item>
            <el-descriptions-item label="处理状态">
              <el-tag :type="getStatusTagType(alertData.alert.status)">
                {{ statusLabels[alertData.alert.status] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="处理人" v-if="alertData.alert.resolved_by">
              {{ alertData.alert.resolved_by }}
            </el-descriptions-item>
            <el-descriptions-item label="处理时间" v-if="alertData.alert.resolved_at">
              {{ formatDateTime(alertData.alert.resolved_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="文件路径" :span="2">
              <span class="file-path">{{ alertData.alert.file_path || '-' }}</span>
            </el-descriptions-item>

            <!-- 原始数据展开 - 新格式告警详情 -->
            <el-descriptions-item label="原始数据" :span="2">
              <el-collapse v-if="hasRawDataDetails" v-model="rawDataCollapse">
                <el-collapse-item title="查看详细硬件信息" name="rawData">
                  <el-descriptions :column="2" border size="small">
                    <!-- 设备信息 -->
                    <el-descriptions-item label="设备ID" v-if="getRawDataField('device_id')">
                      {{ getRawDataField('device_id') }}
                    </el-descriptions-item>
                    <el-descriptions-item label="设备槽位" v-if="getRawDataField('device_slot') && getRawDataField('device_slot') !== 'None'">
                      {{ getRawDataField('device_slot') }}
                    </el-descriptions-item>
                    <el-descriptions-item label="设备类型" v-if="getRawDataField('device_type')">
                      <el-tag size="small">{{ getRawDataField('device_type') }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="设备SN" v-if="getRawDataField('device_sn')">
                      {{ getRawDataField('device_sn') }}
                    </el-descriptions-item>

                    <!-- 主机信息 -->
                    <el-descriptions-item label="主机SN" v-if="getRawDataField('hostsn')">
                      {{ getRawDataField('hostsn') }}
                    </el-descriptions-item>
                    <el-descriptions-item label="机架SN" v-if="getRawDataField('racksn') && getRawDataField('racksn') !== 'None'">
                      {{ getRawDataField('racksn') }}
                    </el-descriptions-item>

                    <!-- 部件信息 -->
                    <el-descriptions-item label="部件型号" v-if="getRawDataField('part_model')">
                      {{ getRawDataField('part_model') }}
                    </el-descriptions-item>
                    <el-descriptions-item label="部件SN" v-if="getRawDataField('part_sn')">
                      {{ getRawDataField('part_sn') }}
                    </el-descriptions-item>

                    <!-- 告警信息 -->
                    <el-descriptions-item label="告警来源" v-if="getRawDataField('source')">
                      <el-tag type="info" size="small">{{ getRawDataField('source') }}</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="处理类型" v-if="getRawDataField('handler')">
                      <el-tag type="warning" size="small">{{ getRawDataField('handler') }}</el-tag>
                    </el-descriptions-item>

                    <!-- case_info 原始信息 -->
                    <el-descriptions-item label="原始case_info" :span="2" v-if="getRawDataField('case_info')">
                      <code class="case-info-code">{{ getRawDataField('case_info') }}</code>
                    </el-descriptions-item>
                  </el-descriptions>

                  <!-- 多错误类型展示 -->
                  <div v-if="hasMultipleErrorTypes" class="error-types-section">
                    <div class="section-title">所有错误类型 ({{ getErrorTypesCount }}个)</div>
                    <el-table :data="getAllErrorTypes" size="small" border>
                      <el-table-column prop="device" label="设备" width="100" />
                      <el-table-column prop="alert_type" label="告警类型" width="150" />
                      <el-table-column prop="severity" label="级别" width="80">
                        <template #default="{ row }">
                          <el-tag :type="getSeverityTagType(row.severity)" size="small">{{ row.severity }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="component" label="组件" width="100" />
                      <el-table-column prop="part_sn" label="部件SN" min-width="150" show-overflow-tooltip />
                    </el-table>
                  </div>
                </el-collapse-item>
              </el-collapse>
              <span v-else class="no-data">-</span>
            </el-descriptions-item>

            <!-- 处理备注 - 可编辑 -->
            <el-descriptions-item label="处理备注" :span="2">
              <div class="editable-field">
                <div v-if="!editingNotes" class="resolution-notes" @click="startEditNotes">
                  {{ alertData.alert.resolution_notes || '点击添加备注...' }}
                  <el-icon class="edit-icon"><Edit /></el-icon>
                </div>
                <div v-else class="edit-form">
                  <el-input
                    v-model="editingNotesValue"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入处理备注"
                  />
                  <div class="edit-actions">
                    <el-button type="primary" size="small" @click="saveNotes" :loading="savingNotes">保存</el-button>
                    <el-button size="small" @click="cancelEditNotes">取消</el-button>
                  </div>
                </div>
              </div>
            </el-descriptions-item>
            <!-- 处理结果 - 仅已处理状态显示，可编辑 -->
            <el-descriptions-item 
              v-if="alertData.alert.status === 'resolved' || alertData.alert.resolution_result" 
              label="处理结果" 
              :span="2"
            >
              <div class="editable-field">
                <div v-if="!editingResult" class="resolution-result" @click="startEditResult">
                  {{ alertData.alert.resolution_result || '点击添加处理结果...' }}
                  <el-icon class="edit-icon"><Edit /></el-icon>
                </div>
                <div v-else class="edit-form">
                  <el-input
                    v-model="editingResultValue"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入处理结果（如：更换GPU后告警消除）"
                  />
                  <div class="edit-actions">
                    <el-button type="primary" size="small" @click="saveResult" :loading="savingResult">保存</el-button>
                    <el-button size="small" @click="cancelEditResult">取消</el-button>
                  </div>
                </div>
              </div>
            </el-descriptions-item>
          </el-descriptions>
          </div>
        </div>

        <!-- 诊断结果 -->
        <template v-if="alertData.diagnosis">
          <!-- 手册匹配结果 -->
          <div class="content-card">
            <div class="content-card-header">
              <div class="content-card-title">
                <el-icon :color="alertData.diagnosis?.manual_matched ? '#67C23A' : '#909399'">
                  <CircleCheck v-if="alertData.diagnosis?.manual_matched" />
                  <Document v-else />
                </el-icon>
                手册匹配结果
                <el-tag v-if="alertData.diagnosis?.manual_matched" type="success" size="small" style="margin-left: 8px;">
                  已匹配
                </el-tag>
                <el-tag v-else type="info" size="small" style="margin-left: 8px;">
                  未匹配
                </el-tag>
              </div>
            </div>
            <div class="content-card-body">
              <!-- 多故障类型表格展示 -->
              <template v-if="alertData.diagnosis?.fault_items && alertData.diagnosis.fault_items.length > 0">
                <div class="native-table-wrapper">
                  <table class="native-detail-table">
                    <colgroup>
                      <col style="width: 140px">
                      <col style="width: 190px">
                      <col style="width: 110px">
                      <col style="width: 110px">
                      <col style="width: 260px">
                      <col style="width: 320px">
                      <col style="width: 260px">
                    </colgroup>
                    <thead>
                      <tr>
                        <th>所属设备</th>
                        <th>故障名称</th>
                        <th>危害等级</th>
                        <th>客户有感</th>
                        <th>影响描述</th>
                        <th>建议解决方案</th>
                        <th>手动判断方法</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, index) in alertData.diagnosis.fault_items" :key="`${row.device}-${row.alert_type}-${index}`">
                        <td>
                          <div class="device-info">
                            <div class="device-name">{{ row.device || '-' }}</div>
                            <div class="device-model" v-if="row.part_model">{{ row.part_model }}</div>
                          </div>
                        </td>
                        <td>
                          <el-tag :type="getFaultTagType(row.severity)" size="small">
                            {{ row.alert_type }}
                          </el-tag>
                          <div class="fault-name">{{ row.fault_name }}</div>
                        </td>
                        <td class="cell-center">
                          <el-tag :type="getDangerLevelTagType(row.danger_level)" size="small">
                            {{ row.danger_level || 'P2' }}
                          </el-tag>
                        </td>
                        <td class="cell-center">
                          <el-tag :type="row.customer_aware ? 'danger' : 'success'" size="small">
                            {{ row.customer_aware ? '是' : '否' }}
                          </el-tag>
                        </td>
                        <td class="cell-wrap">{{ row.impact_description || '-' }}</td>
                        <td class="cell-wrap">{{ row.solution || '-' }}</td>
                        <td>
                          <div class="copyable-cell" @click.stop>
                            <code class="manual-check-code">{{ row.manual_check || '-' }}</code>
                            <el-icon
                              v-if="row.manual_check"
                              class="copy-icon"
                              @click="copyToClipboard(row.manual_check, '手动判断方法')"
                            >
                              <DocumentCopy />
                            </el-icon>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
              <!-- 单故障类型兼容旧数据 -->
              <template v-else-if="alertData.diagnosis?.manual_matched">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="故障名称">
                    {{ alertData.diagnosis.manual_name_zh }}
                  </el-descriptions-item>
                  <el-descriptions-item label="危害等级">
                    <el-tag :type="getDangerLevelTagType(alertData.diagnosis.danger_level)">
                      {{ alertData.diagnosis.danger_level }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="客户有感">
                    <el-tag :type="alertData.diagnosis.customer_aware ? 'danger' : 'success'">
                      {{ alertData.diagnosis.customer_aware ? '是' : '否' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="影响描述">
                    <div class="text-content">{{ alertData.diagnosis.manual_impact || '-' }}</div>
                  </el-descriptions-item>
                  <el-descriptions-item label="建议解决方案">
                    <div class="text-content">{{ alertData.diagnosis.suggested_solution || alertData.diagnosis.manual_solution || '-' }}</div>
                  </el-descriptions-item>
                </el-descriptions>
              </template>
              <!-- 未匹配到手册 -->
              <template v-else>
                <el-empty description="暂无匹配结果" />
              </template>
            </div>
          </div>

          <!-- API诊断结果 -->
          <div v-if="alertData.diagnosis.api_task_id || alertData.diagnosis.api_diagnosis" class="content-card">
            <div class="content-card-header">
              <div class="content-card-title">
                <el-icon color="#409EFF"><Document /></el-icon>
                API诊断结果
              </div>
              <div class="content-card-extra">
                <el-tag :type="getApiStatusTagType(alertData.diagnosis.api_status)">
                  {{ getApiStatusText(alertData.diagnosis.api_status) }}
                </el-tag>
              </div>
            </div>
            <div class="content-card-body">
            <!-- 诊断中状态 -->
            <div v-if="alertData.diagnosis.api_status === 'processing'" class="diagnosis-processing">
              <el-skeleton :rows="3" animated />
              <div class="processing-text">
                <el-icon class="is-loading"><Loading /></el-icon>
                诊断任务进行中，请稍后刷新查看结果...
              </div>
            </div>

            <!-- 诊断失败状态 -->
            <div v-else-if="alertData.diagnosis.api_status === 'failed' && alertData.diagnosis.api_diagnosis?.error" class="diagnosis-error">
              <el-alert
                :title="'诊断失败: ' + alertData.diagnosis.api_diagnosis.error"
                type="error"
                :closable="false"
                show-icon
              />
            </div>

            <!-- 诊断完成状态 -->
            <template v-else-if="alertData.diagnosis.api_diagnosis">
              <div class="api-diagnosis-summary">
                <el-statistic title="诊断项总数" :value="alertData.diagnosis.api_items_count" />
                <el-statistic title="错误项" :value="alertData.diagnosis.api_error_count">
                  <template #suffix>
                    <el-icon color="#F56C6C"><CircleClose /></el-icon>
                  </template>
                </el-statistic>
                <el-statistic title="警告项" :value="alertData.diagnosis.api_warning_count">
                  <template #suffix>
                    <el-icon color="#E6A23C"><Warning /></el-icon>
                  </template>
                </el-statistic>
                <el-statistic title="异常项" :value="alertData.diagnosis.api_abnormal_count">
                  <template #suffix>
                    <el-icon color="#F56C6C"><WarningFilled /></el-icon>
                  </template>
                </el-statistic>
              </div>

              <el-divider />

              <el-collapse v-model="activeCollapse">
                <el-collapse-item
                  v-if="alertData.diagnosis.api_diagnosis.error_items?.length"
                  title="错误项"
                  name="errors"
                >
                  <el-table :data="alertData.diagnosis.api_diagnosis.error_items" stripe>
                    <el-table-column prop="item_name_zh" label="诊断项" min-width="200" />
                    <el-table-column prop="result" label="结果" width="100">
                      <template #default="{ row }">
                        <el-tag type="danger" size="small">{{ row.result }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="exact_message" label="详情" min-width="300" show-overflow-tooltip />
                  </el-table>
                </el-collapse-item>

                <el-collapse-item
                  v-if="alertData.diagnosis.api_diagnosis.warning_items?.length"
                  title="警告项"
                  name="warnings"
                >
                  <el-table :data="alertData.diagnosis.api_diagnosis.warning_items" stripe>
                    <el-table-column prop="item_name_zh" label="诊断项" min-width="200" />
                    <el-table-column prop="result" label="结果" width="100">
                      <template #default="{ row }">
                        <el-tag type="warning" size="small">{{ row.result }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="exact_message" label="详情" min-width="300" show-overflow-tooltip />
                  </el-table>
                </el-collapse-item>
              </el-collapse>
            </template>
            </div>
          </div>

          <!-- AI解读结果 -->
          <div v-if="alertData.diagnosis.ai_interpretation" class="content-card">
            <div class="content-card-header">
              <div class="content-card-title">
                <el-icon color="#9333EA"><MagicStick /></el-icon>
                AI智能解读
              </div>
            </div>
            <div class="content-card-body">
              <div class="ai-interpretation">
                <div v-html="renderMarkdown(alertData.diagnosis.ai_interpretation)"></div>
              </div>
            </div>
          </div>
        </template>

        <!-- 无诊断结果提示 -->
        <el-empty v-else description="暂无诊断结果" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  CircleCheck,
  CircleClose,
  Document,
  Warning,
  WarningFilled,
  MagicStick,
  ArrowLeft,
  Loading,
  Edit,
  DocumentCopy
} from '@element-plus/icons-vue'
import { getAlertDetail, diagnoseAlert, updateAlertStatus } from '@/api/alerts'
import { marked } from 'marked'

const route = useRoute()
const router = useRouter()

const statusLabels = {
  processing: '处理中',
  resolved: '已处理',
  closed: '已关闭'
}

const loading = ref(false)
const diagnosing = ref(false)
const alertData = ref(null)
const activeCollapse = ref(['errors', 'warnings'])

// 编辑状态
const editingNotes = ref(false)
const editingNotesValue = ref('')
const savingNotes = ref(false)
const editingResult = ref(false)
const editingResultValue = ref('')
const savingResult = ref(false)

// 原始数据展开状态
const rawDataCollapse = ref([])

// ========== 新格式告警原始数据解析 ==========

const normalizeRawValue = (value) => {
  if (value === undefined || value === null) return null
  if (typeof value === 'string' && (!value.trim() || value.trim() === 'None' || value.trim() === 'null')) {
    return null
  }
  return value
}

// 获取原始数据中的字段
const getRawDataField = (fieldName) => {
  if (!alertData.value?.alert?.raw_data) return null

  const rawData = alertData.value.alert.raw_data

  // 优先从 error_types[0].raw_data 获取（新格式）
  if (rawData.error_types && Array.isArray(rawData.error_types) && rawData.error_types.length > 0) {
    const firstError = rawData.error_types[0]
    if (firstError.raw_data && firstError.raw_data[fieldName] !== undefined) {
      return normalizeRawValue(firstError.raw_data[fieldName])
    }
    if (firstError[fieldName] !== undefined) {
      return normalizeRawValue(firstError[fieldName])
    }
  }

  // 从 raw_data 直接获取（旧格式兼容）
  if (rawData[fieldName] !== undefined) {
    return normalizeRawValue(rawData[fieldName])
  }

  return null
}

// 是否有原始数据详情
const hasRawDataDetails = computed(() => {
  if (!alertData.value?.alert?.raw_data) return false
  const rawData = alertData.value.alert.raw_data

  // 检查是否有新格式的 error_types
  if (rawData.error_types && Array.isArray(rawData.error_types) && rawData.error_types.length > 0) {
    return true
  }

  // 检查是否有旧格式的关键字段
  const keyFields = ['device_id', 'device_type', 'hostsn', 'case_info', 'source', 'handler']
  return keyFields.some(field => rawData[field] !== undefined)
})

// 是否有多个错误类型
const hasMultipleErrorTypes = computed(() => {
  if (!alertData.value?.alert?.raw_data?.error_types) return false
  return alertData.value.alert.raw_data.error_types.length > 1
})

// 获取错误类型数量
const getErrorTypesCount = computed(() => {
  if (!alertData.value?.alert?.raw_data?.error_types) return 0
  return alertData.value.alert.raw_data.error_types.length
})

// 获取所有错误类型（用于表格展示）
const getAllErrorTypes = computed(() => {
  if (!alertData.value?.alert?.raw_data?.error_types) return []

  return alertData.value.alert.raw_data.error_types.map(error => ({
    device: error.device || error.raw_data?.device_id || '-',
    alert_type: error.alert_type || '-',
    severity: error.severity || 'ERROR',
    component: error.component || error.raw_data?.device_type || '-',
    part_sn: error.part_sn || error.raw_data?.device_sn || '-',
    position: error.position || error.raw_data?.device_slot || '-'
  }))
})

const parsedAlertTypes = computed(() => {
  const errorTypes = alertData.value?.alert?.raw_data?.error_types
  if (!Array.isArray(errorTypes)) return []

  const seen = new Set()
  return errorTypes
    .map(error => ({
      device: error.device || error.raw_data?.device_id || '',
      alert_type: error.alert_type || '',
      severity: error.severity || 'ERROR'
    }))
    .filter(item => {
      if (!item.alert_type) return false
      const key = `${item.device}-${item.alert_type}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
})

// 获取告警详情
const fetchAlertDetail = async () => {
  // 检查ID是否存在
  const alertId = route.params.id
  if (!alertId || alertId === 'undefined') {
    console.warn('告警ID不存在或无效')
    return
  }

  loading.value = true
  try {
    const response = await getAlertDetail(alertId)
    if (response.success) {
      alertData.value = response.data
    }
  } catch (error) {
    ElMessage.error('获取告警详情失败')
  } finally {
    loading.value = false
  }
}


// 重新诊断
const handleDiagnose = async () => {
  // 检查ID是否存在
  const alertId = route.params.id
  if (!alertId || alertId === 'undefined') {
    ElMessage.error('告警ID不存在或无效')
    return
  }

  diagnosing.value = true
  try {
    const response = await diagnoseAlert(alertId, true)  // 传递布尔值而不是对象
    // 检查响应是否成功
    if (response && response.success) {
      ElMessage.success(response.message || '诊断任务已创建,正在处理中...')
      // 开始轮询检查诊断状态
      startDiagnosisPolling()
    } else {
      // 后端返回success:false，但可能基础流程已完成
      const message = response?.message || '诊断处理完成'
      ElMessage.success(message)
      // 仍然开始轮询检查状态
      startDiagnosisPolling()
    }

  } catch (error) {
    // 检查是否是axios拦截器抛出的错误（基础流程可能已完成）
    if (error.message && (
      error.message.includes('重新诊断') ||
      error.message.includes('诊断') ||
      error.message.includes('已存在诊断结果')
    )) {
      // 这种情况下，基础流程可能已经完成，显示成功信息并轮询
      ElMessage.success('诊断处理已完成，正在检查结果...')
      startDiagnosisPolling()
    } else {
      // 真正的网络错误或其他异常
      ElMessage.error('诊断请求失败，请重试')
    }
  } finally {
    diagnosing.value = false
  }
}

// 轮询检查诊断状态
const startDiagnosisPolling = () => {
  let pollCount = 0
  const maxPolls = 20 // 最多轮询20次 (约2分钟)
  
  const pollInterval = setInterval(async () => {
    try {
      await fetchAlertDetail()
      pollCount++
      
      // 检查诊断是否完成 (可以根据诊断状态判断)
      if (alertData.value?.diagnosis?.api_status === 'success' || 
          alertData.value?.diagnosis?.api_status === 'failed' ||
          pollCount >= maxPolls) {
        clearInterval(pollInterval)
        if (pollCount < maxPolls) {
          ElMessage.success('诊断已完成')
        }
      }
    } catch (error) {
      clearInterval(pollInterval)
    }
  }, 6000) // 每6秒轮询一次
}

// 返回
const handleBack = () => {
  router.back()
}

// 渲染Markdown
const renderMarkdown = (content) => {
  return marked(content || '')
}

// 标签类型辅助函数
const getComponentTagType = (component) => {
  const typeMap = {
    GPU: 'danger',
    Memory: 'warning',
    CPU: 'success',
    Motherboard: 'info'
  }
  return typeMap[component] || ''
}

const getSeverityTagType = (severity) => {
  const typeMap = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[severity] || ''
}

const getStatusTagType = (status) => {
  const typeMap = {
    processing: 'warning',
    resolved: 'success',
    closed: 'info'
  }
  return typeMap[status] || ''
}

const getDangerLevelTagType = (level) => {
  if (!level) return ''
  if (level.includes('严重') || level.includes('P0')) return 'danger'
  if (level.includes('中等') || level.includes('P1')) return 'warning'
  return 'info'
}

const getApiStatusTagType = (status) => {
  const typeMap = {
    normal: 'success',
    abnormal: 'danger',
    failed: 'danger',
    processing: 'warning',
    timeout: 'info'
  }
  return typeMap[status] || 'info'
}

const getApiStatusText = (status) => {
  const textMap = {
    normal: '正常',
    abnormal: '异常',
    failed: '失败',
    processing: '诊断中',
    timeout: '超时',
    unknown: '未知'
  }
  return textMap[status] || status
}

// 获取唯一的故障类型列表（去重）
const getUniqueFaultTypes = (faultItems) => {
  if (!faultItems || !Array.isArray(faultItems)) return []
  
  const seen = new Set()
  return faultItems.filter(item => {
    const key = `${item.device || ''}-${item.alert_type}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

// 获取故障标签类型
const getFaultTagType = (severity) => {
  const typeMap = {
    'FAIL': 'danger',
    'ERROR': 'warning',
    'WARN': 'info',
    'GOOD': 'success'
  }
  return typeMap[severity] || ''
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const copyToClipboard = async (text, label = '内容') => {
  if (!text) {
    ElMessage.warning('内容为空，无法复制')
    return
  }

  try {
    await navigator.clipboard.writeText(String(text))
    ElMessage.success(`${label}已复制到剪贴板`)
  } catch (err) {
    const textarea = document.createElement('textarea')
    textarea.value = String(text)
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success(`${label}已复制到剪贴板`)
    } catch (e) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}

// ========== 处理备注编辑 ==========
const startEditNotes = () => {
  editingNotesValue.value = alertData.value.alert.resolution_notes || ''
  editingNotes.value = true
}

const cancelEditNotes = () => {
  editingNotes.value = false
  editingNotesValue.value = ''
}

const saveNotes = async () => {
  savingNotes.value = true
  try {
    const response = await updateAlertStatus(alertData.value.alert.id, {
      resolution_notes: editingNotesValue.value
    })
    if (response.success) {
      ElMessage.success('备注更新成功')
      alertData.value.alert.resolution_notes = editingNotesValue.value
      editingNotes.value = false
    } else {
      ElMessage.error(response.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    savingNotes.value = false
  }
}

// ========== 处理结果编辑 ==========
const startEditResult = () => {
  editingResultValue.value = alertData.value.alert.resolution_result || ''
  editingResult.value = true
}

const cancelEditResult = () => {
  editingResult.value = false
  editingResultValue.value = ''
}

const saveResult = async () => {
  savingResult.value = true
  try {
    const response = await updateAlertStatus(alertData.value.alert.id, {
      resolution_result: editingResultValue.value
    })
    if (response.success) {
      ElMessage.success('处理结果更新成功')
      alertData.value.alert.resolution_result = editingResultValue.value
      editingResult.value = false
    } else {
      ElMessage.error(response.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    savingResult.value = false
  }
}

onMounted(() => {
  fetchAlertDetail()
})
</script>

<style scoped>
.text-content {
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.api-diagnosis-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

.ai-interpretation {
  padding: var(--space-4);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-lg);
  line-height: 1.8;
}

.ai-interpretation :deep(h1),
.ai-interpretation :deep(h2),
.ai-interpretation :deep(h3) {
  margin-top: var(--space-4);
  margin-bottom: var(--space-3);
  color: var(--text-primary);
}

.ai-interpretation :deep(p) {
  margin-bottom: var(--space-3);
  color: var(--text-secondary);
}

.ai-interpretation :deep(ul),
.ai-interpretation :deep(ol) {
  margin-left: var(--space-6);
  margin-bottom: var(--space-3);
}

.ai-interpretation :deep(code) {
  background-color: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.ai-interpretation :deep(pre) {
  background-color: var(--text-primary);
  color: white;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  overflow-x: auto;
  margin-bottom: var(--space-3);
}

.ai-interpretation :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

.resolution-notes {
  padding: var(--space-3);
  background-color: rgba(26, 115, 232, 0.1);
  border-left: 4px solid var(--primary);
  border-radius: var(--radius-md);
  line-height: 1.6;
  color: var(--primary);
  white-space: pre-wrap;
  cursor: pointer;
  position: relative;
}

.resolution-notes:hover {
  background-color: rgba(26, 115, 232, 0.15);
}

.resolution-result {
  padding: var(--space-3);
  background-color: rgba(103, 194, 58, 0.1);
  border-left: 4px solid var(--success);
  border-radius: var(--radius-md);
  line-height: 1.6;
  color: var(--success);
  white-space: pre-wrap;
  cursor: pointer;
  position: relative;
}

.resolution-result:hover {
  background-color: rgba(103, 194, 58, 0.15);
}

.editable-field {
  position: relative;
}

.edit-icon {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.resolution-notes:hover .edit-icon,
.resolution-result:hover .edit-icon {
  opacity: 1;
}

.edit-form {
  padding: var(--space-3);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.edit-actions {
  margin-top: var(--space-3);
  display: flex;
  gap: var(--space-2);
}

.diagnosis-processing {
  padding: var(--space-5);
  text-align: center;
}

.diagnosis-processing .processing-text {
  margin-top: var(--space-4);
  color: var(--text-secondary);
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.diagnosis-error {
  padding: var(--space-4);
}

/* 告警类型标签容器 */
.alert-types-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  max-width: 100%;
}

.alert-type-tag {
  margin: 0;
  font-size: 12px;
}

/* 手册匹配表格样式 */
.device-info {
  line-height: 1.4;
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
}

.device-model {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.fault-name {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-primary);
}

.manual-check-code {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  background-color: var(--bg-secondary);
  padding: 2px 4px;
  border-radius: 3px;
  color: var(--text-secondary);
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copyable-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  width: 100%;
}

.copy-icon {
  opacity: 0;
  cursor: pointer;
  color: var(--color-primary, #409eff);
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.copyable-cell:hover .copy-icon {
  opacity: 1;
}

.native-table-wrapper {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.native-detail-table {
  width: 100%;
  min-width: 1390px;
  border-collapse: collapse;
  table-layout: fixed;
  background: var(--bg-primary);
}

.native-detail-table th,
.native-detail-table td {
  border-right: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  padding: 12px 14px;
  vertical-align: top;
  box-sizing: border-box;
}

.native-detail-table th:last-child,
.native-detail-table td:last-child {
  border-right: none;
}

.native-detail-table tbody tr:last-child td {
  border-bottom: none;
}

.native-detail-table th {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.native-detail-table td {
  color: var(--text-primary);
  line-height: 1.7;
}

.cell-center {
  text-align: center;
  vertical-align: middle !important;
}

.cell-wrap {
  white-space: normal;
  word-break: break-word;
}

/* 原始数据展开样式 */
.case-info-code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background-color: var(--bg-tertiary);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  display: block;
  word-break: break-all;
  line-height: 1.5;
}

.error-types-section {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.error-types-section .section-title {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-3);
  font-size: 14px;
}

.no-data {
  color: var(--text-tertiary);
}
</style>
