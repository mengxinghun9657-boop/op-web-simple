<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Grid /></el-icon>
          </div>
          CMDB 资源管理
        </div>
        <div class="page-subtitle">集中管理物理服务器和虚拟实例资源配置信息</div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">物理服务器</div>
          <div class="stat-card-icon primary">
            <el-icon><Monitor /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ stats.total_servers || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">虚拟实例</div>
          <div class="stat-card-icon success">
            <el-icon><Cpu /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ stats.total_instances || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">vCPU总数</div>
          <div class="stat-card-icon info">
            <el-icon><Odometer /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ stats.resource_summary?.vcpus_total || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-header">
          <div class="stat-card-label">内存总量</div>
          <div class="stat-card-icon warning">
            <el-icon><Coin /></el-icon>
          </div>
        </div>
        <div class="stat-card-value">{{ stats.resource_summary?.memory_total_gb || 0 }} GB</div>
      </div>
    </div>

    <!-- 配置提示卡片 -->
    <div class="content-card" style="background: linear-gradient(135deg, rgba(26, 115, 232, 0.05), rgba(26, 115, 232, 0.02)); border: 1px solid rgba(26, 115, 232, 0.2);">
      <div class="content-card-body" style="display: flex; align-items: flex-start; gap: var(--space-4);">
        <el-icon style="font-size: 32px; color: var(--primary); flex-shrink: 0; margin-top: 4px;"><Tools /></el-icon>
        <div style="flex: 1;">
          <h4 style="font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); margin: 0 0 var(--space-2);">CMDB 配置管理</h4>
          <p style="font-size: var(--text-sm); color: var(--text-secondary); margin: 0 0 var(--space-3); line-height: 1.6;">
            CMDB 的 Cookie 配置、数据同步、定时同步等功能已统一到系统配置页面。
          </p>
          <el-button type="primary" @click="handleGoToConfig">
            <el-icon><Tools /></el-icon>
            前往系统配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="content-card">
      <div class="content-card-body"  style="padding: var(--space-4);"
>
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-4);">
          <div style="display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap;">
            <div class="search-box">
              <el-input
                v-model="searchText"
                placeholder="搜索主机名/SN/IP/UUID（支持跨视图搜索）"
                clearable
                @keyup.enter="handleSearch"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
            </div>
            <el-select v-model="filterManufacturer" placeholder="服务器品牌" clearable @change="handleSearch" style="width: 160px;">
              <el-option v-for="m in filters.manufacturers" :key="m" :label="m" :value="m" />
            </el-select>
            <el-select v-model="filterNodeType" placeholder="节点类型" clearable @change="handleSearch" style="width: 140px;">
              <el-option v-for="n in filters.node_types" :key="n" :label="n" :value="n" />
            </el-select>
            <el-radio-group v-model="viewMode" @change="handleViewChange">
              <el-radio-button value="servers">服务器视图</el-radio-button>
              <el-radio-button value="instances">实例视图</el-radio-button>
            </el-radio-group>
          </div>
          <div style="display: flex; align-items: center; gap: var(--space-2);">
            <!-- 配置管理按钮（仅管理员可见） -->
            <el-button
              v-if="isAdmin"
              @click="handleGoToConfig"
            >
              <el-icon><Tools /></el-icon>
              配置管理
            </el-button>
            <!-- 字段配置按钮 -->
            <el-button @click="fieldConfigVisible = true">
              <el-icon><Setting /></el-icon>
              字段配置
            </el-button>
            <!-- 导入数据按钮 -->
            <div class="import-button-group">
              <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls" class="import-upload">
                <el-button type="primary" class="import-main-btn">
                  <el-icon><Upload /></el-icon>导入数据
                </el-button>
              </el-upload>
              <el-dropdown trigger="click" @command="(cmd) => importMode = cmd" placement="bottom-end">
                <el-button type="primary" class="import-mode-btn">
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="update" :class="{ 'is-active': importMode === 'update' }">
                      <el-icon><Refresh /></el-icon>更新模式（推荐）
                    </el-dropdown-item>
                    <el-dropdown-item command="replace" :class="{ 'is-active': importMode === 'replace' }">
                      <el-icon><Delete /></el-icon>覆盖模式
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <div class="table-header">
        <div class="table-title">{{ viewMode === 'servers' ? '服务器列表' : '实例列表' }}</div>
        <div class="table-toolbar">
          <span class="status-badge primary">共 {{ total }} 条</span>
        </div>
      </div>
      <div class="table-body">
        <!-- 服务器列表 - 动态列 -->
        <el-table
          v-if="viewMode === 'servers'"
          :data="servers"
          v-loading="loading"
          @row-click="showServerDetail"
          @sort-change="handleSortChange"
          class="google-table"
        >
          <el-table-column
            v-for="fieldConfig in currentFieldConfigs"
            :key="fieldConfig.key"
            :prop="fieldConfig.key"
            :label="fieldConfig.label"
            :width="fieldConfig.width"
            :min-width="fieldConfig.minWidth"
            :sortable="fieldConfig.sortable ? 'custom' : false"
            :show-overflow-tooltip="false"
            :align="fieldConfig.align || 'left'"
          >
            <template #default="{ row }">
              <el-tooltip
                :content="getCellTooltipContent(row, fieldConfig)"
                placement="top"
                :disabled="!shouldShowTooltip(row, fieldConfig)"
                :show-after="500"
                :popper-options="{ strategy: 'fixed' }"
              >
                <div class="cell-wrapper">
                  <component
                    :is="getFieldComponent(fieldConfig)"
                    :row="row"
                    :field-config="fieldConfig"
                  />
                </div>
              </el-tooltip>
            </template>
          </el-table-column>
          
          <!-- 空状态插槽 -->
          <template #empty>
            <div class="empty-state">
              <div class="empty-state-icon">
                <el-icon><FolderOpened /></el-icon>
              </div>
              <div class="empty-state-title">暂无服务器数据</div>
              <div class="empty-state-description">请导入 Excel 文件或前往系统配置页面同步数据</div>
              <div style="display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-4);">
                <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls" style="display: flex;">
                  <el-button type="primary">
                    <el-icon><Upload /></el-icon>
                    导入 Excel
                  </el-button>
                </el-upload>
                <el-button type="success" @click="handleGoToConfig">
                  <el-icon><Tools /></el-icon>
                  前往系统配置
                </el-button>
              </div>
            </div>
          </template>
        </el-table>

        <!-- 实例列表 - 动态列 -->
        <el-table v-else :data="instances" v-loading="loading" class="google-table">
          <el-table-column
            v-for="fieldConfig in currentFieldConfigs"
            :key="fieldConfig.key"
            :prop="fieldConfig.key"
            :label="fieldConfig.label"
            :width="fieldConfig.width"
            :min-width="fieldConfig.minWidth"
            :sortable="fieldConfig.sortable ? 'custom' : false"
            :show-overflow-tooltip="false"
            :align="fieldConfig.align || 'left'"
          >
            <template #default="{ row }">
              <el-tooltip
                :content="getCellTooltipContent(row, fieldConfig)"
                placement="top"
                :disabled="!shouldShowTooltip(row, fieldConfig)"
                :show-after="500"
                :popper-options="{ strategy: 'fixed' }"
              >
                <div class="cell-wrapper">
                  <component
                    :is="getFieldComponent(fieldConfig)"
                    :row="row"
                    :field-config="fieldConfig"
                  />
                </div>
              </el-tooltip>
            </template>
          </el-table-column>
          
          <!-- 空状态插槽 -->
          <template #empty>
            <div class="empty-state">
              <div class="empty-state-icon">
                <el-icon><FolderOpened /></el-icon>
              </div>
              <div class="empty-state-title">暂无实例数据</div>
              <div class="empty-state-description">请导入 Excel 文件或前往系统配置页面同步数据</div>
              <div style="display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-4);">
                <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls" style="display: flex;">
                  <el-button type="primary">
                    <el-icon><Upload /></el-icon>
                    导入 Excel
                  </el-button>
                </el-upload>
                <el-button type="success" @click="handleGoToConfig">
                  <el-icon><Tools /></el-icon>
                  前往系统配置
                </el-button>
              </div>
            </div>
          </template>
        </el-table>

        <!-- 分页 -->
        <div class="table-footer">
          <div>共 {{ total }} 条</div>
          <div class="google-pagination">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @change="fetchData"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 服务器详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="currentServer?.bns_hostname" size="60%" class="google-drawer">
      <template v-if="currentServer">
        <el-descriptions :column="2" border class="modern-descriptions">
          <el-descriptions-item label="主机名">{{ currentServer.bns_hostname }}</el-descriptions-item>
          <el-descriptions-item label="SN">{{ currentServer.rms_sn }}</el-descriptions-item>
          <el-descriptions-item label="套餐号">{{ currentServer.rms_suit }}</el-descriptions-item>
          <el-descriptions-item label="服务器类型">{{ currentServer.rms_type }}</el-descriptions-item>
          <el-descriptions-item label="服务器型号">{{ currentServer.rms_model }}</el-descriptions-item>
          <el-descriptions-item label="品牌">{{ currentServer.rms_manufacturer }}</el-descriptions-item>
          <el-descriptions-item label="类别">{{ currentServer.rms_product }}</el-descriptions-item>
          <el-descriptions-item label="节点标识">{{ currentServer.nova_host_node_type }}</el-descriptions-item>
          <el-descriptions-item label="CPU配置" :span="2">{{ currentServer.rms_cpu }}</el-descriptions-item>
          <el-descriptions-item label="内存配置" :span="2">{{ currentServer.rms_memory }}</el-descriptions-item>
          <el-descriptions-item label="磁盘配置" :span="2">{{ currentServer.rms_ssd }}</el-descriptions-item>
          <el-descriptions-item label="物理CPU核数">{{ currentServer.nova_host_physical_cpus }}</el-descriptions-item>
          <el-descriptions-item label="vCPU总数">{{ currentServer.nova_host_vcpus_total }}</el-descriptions-item>
          <el-descriptions-item label="vCPU已用">{{ currentServer.nova_host_vcpus_used }}</el-descriptions-item>
          <el-descriptions-item label="vCPU空闲">{{ currentServer.nova_host_vcpus_free }}</el-descriptions-item>
          <el-descriptions-item label="内存总量">{{ formatMemory(currentServer.nova_host_physical_memory_mb_total) }}</el-descriptions-item>
          <el-descriptions-item label="内存空闲">{{ formatMemory(currentServer.nova_host_physical_memory_mb_free) }}</el-descriptions-item>
          <el-descriptions-item label="磁盘空闲">{{ currentServer.nova_host_physical_disk_gb_free }} GB</el-descriptions-item>
          <el-descriptions-item label="运行实例数">{{ currentServer.nova_host_running_vms }}</el-descriptions-item>
          <el-descriptions-item label="加黑说明" :span="2">{{ currentServer.nova_host_blacklisted_description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="加黑原因" :span="2">{{ currentServer.nova_host_blacklisted_reason || '-' }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="drawer-section">
          <h4 class="section-title">
            <el-icon><Cpu /></el-icon>
            实例列表 ({{ serverInstances.length }})
          </h4>
          <el-table :data="serverInstances" max-height="400" class="modern-table">
            <el-table-column prop="nova_vm_instance_uuid" label="UUID" width="300" :show-overflow-tooltip="false">
              <template #default="{ row }">
                <el-tooltip
                  :content="row.nova_vm_instance_uuid"
                  placement="top"
                  :disabled="!row.nova_vm_instance_uuid"
                  :show-after="500"
                  :popper-options="{ strategy: 'fixed' }"
                >
                  <div class="copyable-cell" @click.stop>
                    <span class="cell-text">{{ row.nova_vm_instance_uuid }}</span>
                    <el-icon class="copy-icon" @click="copyToClipboard(row.nova_vm_instance_uuid, 'UUID')">
                      <DocumentCopy />
                    </el-icon>
                  </div>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="nova_vm_fixed_ips" label="IP" width="140">
              <template #default="{ row }">
                <div class="copyable-cell" @click.stop>
                  <span class="cell-text">{{ row.nova_vm_fixed_ips }}</span>
                  <el-icon class="copy-icon" @click="copyToClipboard(row.nova_vm_fixed_ips, 'IP')">
                    <DocumentCopy />
                  </el-icon>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="nova_vm_metadata_source" label="类型" width="100" />
            <el-table-column prop="nova_vm_vcpus" label="vCPU" width="70" align="center" />
            <el-table-column label="内存" width="80" align="center">
              <template #default="{ row }">{{ formatMemory(row.nova_vm_memory_mb) }}</template>
            </el-table-column>
            <el-table-column prop="nova_vm_root_gb" label="磁盘(GB)" width="80" align="center" />
            <el-table-column prop="nova_vm_vm_state" label="状态" width="80">
              <template #default="{ row }">
                <span class="glass-tag" :class="row.nova_vm_vm_state === 'active' ? 'glass-tag-success' : 'glass-tag-primary'">
                  {{ row.nova_vm_vm_state }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-drawer>

    <!-- 字段配置对话框 -->
    <FieldConfigDialog
      v-model="fieldConfigVisible"
      :view-mode="viewMode"
      :visible-fields="currentVisibleFields"
      :field-order="currentFieldOrder"
      @confirm="handleFieldConfigConfirm"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { Monitor, Cpu, Odometer, Coin, Search, Upload, Refresh, Delete, Grid, DocumentCopy, Setting, Tools, FolderOpened, ArrowDown } from '@element-plus/icons-vue'
import FieldConfigDialog from '@/components/cmdb/FieldConfigDialog.vue'
import { getAllFields, getDefaultVisibleFields } from '@/config/cmdbFields'
import { useUserStore } from '@/stores/user'
import * as cmdbApi from '@/api/cmdb'

// 导入字段渲染组件
import CopyableCell from '@/components/cmdb/cells/CopyableCell.vue'
import ResourceCell from '@/components/cmdb/cells/ResourceCell.vue'
import StatusCell from '@/components/cmdb/cells/StatusCell.vue'
import DefaultCell from '@/components/cmdb/cells/DefaultCell.vue'
import DateTimeCell from '@/components/cmdb/cells/DateTimeCell.vue'
import BooleanCell from '@/components/cmdb/cells/BooleanCell.vue'
import MemoryCell from '@/components/cmdb/cells/MemoryCell.vue'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const viewMode = ref('servers')
const searchText = ref('')
const filterManufacturer = ref('')
const filterNodeType = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const sortBy = ref('')
const sortOrder = ref('desc')

const stats = ref({})

// 是否为管理员
const isAdmin = computed(() => {
  const role = userStore.userRole
  return role === 'super_admin' || role === 'admin'
})
const filters = ref({ manufacturers: [], node_types: [] })
const servers = ref([])
const instances = ref([])

const drawerVisible = ref(false)
const currentServer = ref(null)
const serverInstances = ref([])
const importMode = ref('update')

// 字段配置相关
const fieldConfigVisible = ref(false)
const visibleServerFields = ref([])
const visibleInstanceFields = ref([])
const serverFieldOrder = ref([])
const instanceFieldOrder = ref([])

// 当前视图的可见字段
const currentVisibleFields = computed(() => {
  return viewMode.value === 'servers' ? visibleServerFields.value : visibleInstanceFields.value
})

// 当前视图的字段顺序
const currentFieldOrder = computed(() => {
  return viewMode.value === 'servers' ? serverFieldOrder.value : instanceFieldOrder.value
})

// 当前视图的字段配置（按顺序，只包含可见字段）
const currentFieldConfigs = computed(() => {
  const allFields = getAllFields(viewMode.value)
  
  // 如果没有可见字段配置,使用默认可见字段(修复no data问题)
  const visibleFields = currentVisibleFields.value.length > 0 
    ? currentVisibleFields.value 
    : getDefaultVisibleFields(viewMode.value)
  
  const orderedFields = currentFieldOrder.value.length > 0
    ? currentFieldOrder.value.map(key => allFields.find(f => f.key === key)).filter(Boolean)
    : allFields
  
  return orderedFields.filter(f => visibleFields.includes(f.key))
})

const formatMemory = (mb) => {
  if (!mb) return '0'
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`
}

const getProgressColor = (percent) => {
  if (percent >= 90) return 'var(--color-error)'
  if (percent >= 70) return 'var(--color-warning)'
  return 'var(--color-success)'
}

const fetchStats = async () => {
  try {
    stats.value = await cmdbApi.getStats()
  } catch (e) { console.error(e) }
}

const fetchFilters = async () => {
  try {
    filters.value = await cmdbApi.getFilters()
  } catch (e) { console.error(e) }
}

const fetchData = async () => {
  loading.value = true
  try {
    if (viewMode.value === 'servers') {
      const response = await cmdbApi.getServers({
        page: page.value,
        page_size: pageSize.value,
        search: searchText.value || undefined,
        manufacturer: filterManufacturer.value || undefined,
        node_type: filterNodeType.value || undefined,
        sort_by: sortBy.value || undefined,
        sort_order: sortBy.value ? sortOrder.value : undefined
      })
      // axios拦截器已经返回了response.data，所以response就是{data, total}
      servers.value = response.data
      total.value = response.total
    } else {
      const response = await cmdbApi.getInstances({
        page: page.value,
        page_size: pageSize.value,
        search: searchText.value || undefined
      })
      // axios拦截器已经返回了response.data，所以response就是{data, total}
      instances.value = response.data
      total.value = response.total
    }
  } catch (e) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleSortChange = ({ prop, order }) => {
  // 映射前端列属性到后端排序字段
  const sortFieldMap = {
    'nova_host_vcpus_used': 'vcpus_used',
    'memory_used': 'memory_used',
    'nova_host_running_vms': 'running_vms',
    'nova_host_physical_disk_gb_free': 'disk_free'
  }
  
  if (order) {
    sortBy.value = sortFieldMap[prop] || prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortBy.value = ''
    sortOrder.value = 'desc'
  }
  page.value = 1
  fetchData()
}

const handleSearch = () => {
  page.value = 1
  fetchData()
}

const handleViewChange = () => {
  page.value = 1
  fetchData()
}

// 跳转到系统配置页面
const handleGoToConfig = () => {
  router.push({ name: 'SystemConfig', query: { section: 'cmdb' } })
}

const handleImport = async (file) => {
  // 显示导入提示
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '正在导入数据，请稍候...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    const response = await cmdbApi.importData(formData, importMode.value)
    // axios拦截器已经返回了response.data
    
    ElMessage.success({
      message: `导入成功: 服务器(新增${response.servers?.added || 0}/更新${response.servers?.updated || 0}), 实例(新增${response.instances?.added || 0}/更新${response.instances?.updated || 0})`,
      duration: 5000,
      showClose: true
    })
    
    fetchStats()
    fetchFilters()
    fetchData()
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingInstance.close()
  }
  return false
}

const showServerDetail = async (row) => {
  try {
    const response = await cmdbApi.getServerDetail(row.bns_hostname)
    // axios拦截器已经返回了response.data，所以response就是{server, instances}
    currentServer.value = response.server
    serverInstances.value = response.instances
    drawerVisible.value = true
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

const copyToClipboard = async (text, label) => {
  if (!text) {
    ElMessage.warning('内容为空，无法复制')
    return
  }
  
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${label}已复制到剪贴板`)
  } catch (err) {
    // 降级方案：使用传统方法
    const textarea = document.createElement('textarea')
    textarea.value = text
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

// 从localStorage加载配置
const loadFieldConfig = () => {
  try {
    const savedConfig = localStorage.getItem('cmdb_field_config')
    if (savedConfig) {
      const config = JSON.parse(savedConfig)
      visibleServerFields.value = config.visibleServerFields || getDefaultVisibleFields('servers')
      visibleInstanceFields.value = config.visibleInstanceFields || getDefaultVisibleFields('instances')
      serverFieldOrder.value = config.serverFieldOrder || []
      instanceFieldOrder.value = config.instanceFieldOrder || []
    } else {
      visibleServerFields.value = getDefaultVisibleFields('servers')
      visibleInstanceFields.value = getDefaultVisibleFields('instances')
    }
  } catch (e) {
    console.error('加载字段配置失败:', e)
    visibleServerFields.value = getDefaultVisibleFields('servers')
    visibleInstanceFields.value = getDefaultVisibleFields('instances')
  }
}

// 保存配置到localStorage
const saveFieldConfig = () => {
  try {
    const config = {
      visibleServerFields: visibleServerFields.value,
      visibleInstanceFields: visibleInstanceFields.value,
      serverFieldOrder: serverFieldOrder.value,
      instanceFieldOrder: instanceFieldOrder.value
    }
    localStorage.setItem('cmdb_field_config', JSON.stringify(config))
  } catch (e) {
    console.error('保存字段配置失败:', e)
  }
}

// 处理字段配置确认
const handleFieldConfigConfirm = ({ visibleFields, fieldOrder }) => {
  if (viewMode.value === 'servers') {
    visibleServerFields.value = visibleFields
    serverFieldOrder.value = fieldOrder
  } else {
    visibleInstanceFields.value = visibleFields
    instanceFieldOrder.value = fieldOrder
  }
  saveFieldConfig()
  
  // 刷新数据以应用新的列配置
  nextTick(() => {
    fetchData()
  })
  
  ElMessage.success('字段配置已保存并应用')
}

// 获取字段渲染组件
const getFieldComponent = (fieldConfig) => {
  if (fieldConfig.type === 'resource') return ResourceCell
  if (fieldConfig.type === 'status') return StatusCell
  if (fieldConfig.copyable) return CopyableCell
  if (fieldConfig.type === 'datetime') return DateTimeCell
  if (fieldConfig.type === 'boolean') return BooleanCell
  if (fieldConfig.type === 'memory') return MemoryCell
  return DefaultCell
}

// 获取单元格 tooltip 内容
const getCellTooltipContent = (row, fieldConfig) => {
  const value = row[fieldConfig.key]
  
  // 处理空值
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  
  // 处理对象和数组
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  
  return String(value)
}

// 判断是否应该显示 tooltip
const shouldShowTooltip = (row, fieldConfig) => {
  const value = row[fieldConfig.key]
  
  // 空值不显示 tooltip
  if (value === null || value === undefined || value === '') {
    return false
  }
  
  // 资源类型和状态类型不显示 tooltip (它们有自己的可视化)
  if (fieldConfig.type === 'resource' || fieldConfig.type === 'status') {
    return false
  }
  
  // 布尔类型不显示 tooltip
  if (fieldConfig.type === 'boolean') {
    return false
  }
  
  // 对于文本类型,只有内容较长时才显示 tooltip
  const strValue = String(value)
  return strValue.length > 20
}

onMounted(() => {
  loadFieldConfig()  // 加载字段配置
  fetchStats()
  fetchFilters()
  fetchData()
})
</script>

<style scoped>
/* 所有样式已由 google-pages.css 统一提供 */
/* 只保留页面特定的特殊样式 */

/* 搜索框宽度 */
.search-box :deep(.el-input) {
  width: 350px;
}

/* 导入按钮组 */
.import-button-group {
  display: inline-flex;
  align-items: stretch;
}

.import-upload {
  display: flex;
}

.import-upload :deep(.el-upload) {
  display: flex;
}

.import-main-btn {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-right-color: rgba(255,255,255,0.3) !important;
}

.import-mode-btn {
  border-top-left-radius: 0 !important;
  border-bottom-left-radius: 0 !important;
  padding: 0 10px;
  border-left: none !important;
}

/* 可复制单元格样式 */
.copyable-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.copyable-cell .cell-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copyable-cell .copy-icon {
  opacity: 0;
  transition: opacity var(--duration-normal);
  cursor: pointer;
  color: var(--primary);
  font-size: 14px;
  flex-shrink: 0;
}

.copyable-cell:hover .copy-icon {
  opacity: 1;
}

.copyable-cell .copy-icon:hover {
  color: var(--primary-hover);
  transform: scale(1.1);
}

@media (max-width: 768px) {
  .search-box :deep(.el-input) {
    width: 100%;
  }
}
</style>
