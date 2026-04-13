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
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 5 }"
                placeholder="搜索主机名/SN/IP/UUID，支持多条（换行或英文逗号分隔）"
                @keydown.enter.exact.prevent="handleSearch"
              />
              <div v-if="searchKeywordCount > 1" class="search-hint">
                {{ searchKeywordCount }} 个关键词
              </div>
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
            <!-- BCE 同步按钮（仅管理员可见） -->
            <el-button
              v-if="isAdmin"
              type="success"
              @click="router.push({ name: 'SystemConfig', query: { section: 'bce_sync' } })"
            >
              <el-icon><Refresh /></el-icon>
              BCE 同步
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
    <el-drawer v-model="drawerVisible" :title="currentServer?.bns_hostname" size="56%" class="google-drawer">
      <template v-if="currentServer">
        <el-tabs class="drawer-tabs">
          <!-- Tab 1: 基本信息 -->
          <el-tab-pane label="基本信息">
            <div class="drawer-kv-grid">
              <div class="kv-item">
                <span class="kv-label">主机名</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.bns_hostname, '主机名')">{{ currentServer.bns_hostname }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">SN</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_sn, 'SN')">{{ currentServer.rms_sn || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">品牌</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_manufacturer, '品牌')">{{ currentServer.rms_manufacturer || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">节点类型</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.nova_host_node_type, '节点类型')">{{ currentServer.nova_host_node_type || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">服务器类型</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_type, '服务器类型')">{{ currentServer.rms_type || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">服务器型号</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_model, '服务器型号')">{{ currentServer.rms_model || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">套餐号</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_suit, '套餐号')">{{ currentServer.rms_suit || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item">
                <span class="kv-label">产品线</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_product, '产品线')">{{ currentServer.rms_product || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item kv-item-full">
                <span class="kv-label">CPU 配置</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_cpu, 'CPU配置')">{{ currentServer.rms_cpu || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item kv-item-full">
                <span class="kv-label">内存配置</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_memory, '内存配置')">{{ currentServer.rms_memory || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item kv-item-full">
                <span class="kv-label">磁盘配置</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.rms_ssd, '磁盘配置')">{{ currentServer.rms_ssd || '-' }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item kv-item-full" v-if="currentServer.nova_host_blacklisted_reason">
                <span class="kv-label kv-label-warn">加黑原因</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.nova_host_blacklisted_reason, '加黑原因')">{{ currentServer.nova_host_blacklisted_reason }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
              <div class="kv-item kv-item-full" v-if="currentServer.nova_host_blacklisted_description">
                <span class="kv-label kv-label-warn">加黑说明</span>
                <span class="kv-value kv-copyable" @click="copyToClipboard(currentServer.nova_host_blacklisted_description, '加黑说明')">{{ currentServer.nova_host_blacklisted_description }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab 2: 资源使用 -->
          <el-tab-pane label="资源使用">
            <!-- 虚拟化资源（有 nova 数据时显示进度卡片） -->
            <template v-if="currentServer.nova_host_vcpus_total">
              <div class="drawer-resource-grid" style="margin-bottom: 16px;">
                <div class="resource-card">
                  <div class="resource-card-header">
                    <span class="resource-card-title">vCPU</span>
                    <span class="resource-card-value">{{ currentServer.nova_host_vcpus_used }} / {{ currentServer.nova_host_vcpus_total }}</span>
                  </div>
                  <div class="progress-track">
                    <div class="progress-bar" :style="{ width: Math.min(Math.round(currentServer.nova_host_vcpus_used / currentServer.nova_host_vcpus_total * 100), 100) + '%', background: getProgressColor(Math.min(Math.round(currentServer.nova_host_vcpus_used / currentServer.nova_host_vcpus_total * 100), 100)) }"></div>
                  </div>
                  <div class="resource-card-sub">空闲 {{ currentServer.nova_host_vcpus_free }} 核 · 物理 {{ currentServer.nova_host_physical_cpus }} 核</div>
                </div>
                <div class="resource-card" v-if="currentServer.nova_host_physical_memory_mb_total">
                  <div class="resource-card-header">
                    <span class="resource-card-title">内存</span>
                    <span class="resource-card-value">{{ formatMemory(currentServer.nova_host_physical_memory_mb_total - currentServer.nova_host_physical_memory_mb_free) }} / {{ formatMemory(currentServer.nova_host_physical_memory_mb_total) }}</span>
                  </div>
                  <div class="progress-track">
                    <div class="progress-bar" :style="{ width: Math.min(Math.round((currentServer.nova_host_physical_memory_mb_total - currentServer.nova_host_physical_memory_mb_free) / currentServer.nova_host_physical_memory_mb_total * 100), 100) + '%', background: getProgressColor(Math.min(Math.round((currentServer.nova_host_physical_memory_mb_total - currentServer.nova_host_physical_memory_mb_free) / currentServer.nova_host_physical_memory_mb_total * 100), 100)) }"></div>
                  </div>
                  <div class="resource-card-sub">空闲 {{ formatMemory(currentServer.nova_host_physical_memory_mb_free) }}</div>
                </div>
                <div class="resource-card" v-if="currentServer.nova_host_running_vms != null">
                  <div class="resource-card-header">
                    <span class="resource-card-title">运行实例</span>
                    <span class="resource-card-value">{{ currentServer.nova_host_running_vms }} 个</span>
                  </div>
                </div>
                <div class="resource-card" v-if="currentServer.nova_host_physical_disk_gb_free">
                  <div class="resource-card-header">
                    <span class="resource-card-title">磁盘剩余</span>
                    <span class="resource-card-value">{{ currentServer.nova_host_physical_disk_gb_free }} GB</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- 其他有值的资源字段（KV 形式，动态展示） -->
            <div class="drawer-kv-grid">
              <template v-for="item in resourceKVItems" :key="item.key">
                <div class="kv-item" :class="item.full ? 'kv-item-full' : ''">
                  <span class="kv-label">{{ item.label }}</span>
                  <span class="kv-value kv-copyable" @click="copyToClipboard(String(item.value), item.label)">{{ item.value }}<el-icon class="kv-copy-icon"><DocumentCopy /></el-icon></span>
                </div>
              </template>
              <div v-if="!resourceKVItems.length && !currentServer.nova_host_vcpus_total" class="kv-item kv-item-full" style="color: var(--text-tertiary); font-size: 13px;">
                暂无资源数据
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab 3: 实例列表 -->
          <el-tab-pane :label="`实例 (${serverInstances.length})`">
            <div class="table-wrapper" v-if="serverInstances.length">
              <div class="native-table-scroll">
                <table class="native-drawer-table">
                  <thead>
                    <tr>
                      <th v-for="col in instanceColumns" :key="col.key" :style="{ minWidth: col.width + 'px' }">{{ col.label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in serverInstances" :key="row.nova_vm_instance_uuid">
                      <td v-for="col in instanceColumns" :key="col.key">
                        <template v-if="col.key === 'nova_vm_instance_uuid' || col.key === 'nova_vm_fixed_ips'">
                          <div class="copyable-cell" @click.stop>
                            <span class="bce-cell-text">{{ row[col.key] }}</span>
                            <el-icon class="copy-icon" @click="copyToClipboard(row[col.key], col.label)"><DocumentCopy /></el-icon>
                          </div>
                        </template>
                        <template v-else-if="col.key === 'nova_vm_memory_mb'">
                          <span class="bce-cell-text">{{ formatMemory(row[col.key]) }}</span>
                        </template>
                        <template v-else-if="col.key === 'nova_vm_vm_state'">
                          <span class="glass-tag" :class="row[col.key] === 'active' ? 'glass-tag-success' : 'glass-tag-primary'">{{ row[col.key] }}</span>
                        </template>
                        <template v-else>
                          <span v-if="row[col.key] != null && row[col.key] !== ''" class="bce-cell-text">{{ row[col.key] }}</span>
                          <span v-else style="color: var(--text-tertiary, #9ca3af);">-</span>
                        </template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else class="drawer-bce-placeholder" style="color: var(--text-tertiary, #9ca3af);">暂无实例数据</div>
          </el-tab-pane>

          <!-- Tab 4: BCE 关联 -->
          <el-tab-pane label="BCE 关联" @click.native="!bceContextLoaded && loadBceContext(currentServer.bns_hostname)">
            <div v-if="!bceContextLoaded && !bceContextLoading" class="drawer-bce-placeholder">
              <el-button type="primary" plain @click="loadBceContext(currentServer.bns_hostname)">加载 BCE 关联数据</el-button>
              <div class="bce-empty-tip" style="margin-top: 8px;">查询该服务器在 BCC/CCE 中的关联记录</div>
            </div>
            <div v-else-if="bceContextLoading" class="drawer-bce-placeholder">
              <el-icon class="is-loading"><Refresh /></el-icon>
              <span style="margin-left: 8px; color: var(--text-secondary);">加载中...</span>
            </div>
            <template v-else>
              <!-- BCC 实例 -->
              <div class="drawer-sub-section">
                <div class="drawer-sub-title">BCC 实例 <span class="drawer-sub-count">{{ bceContext.bcc_instances?.length || 0 }}</span></div>
                <div class="table-wrapper" v-if="bceContext.bcc_instances?.length">
                  <div class="native-table-scroll">
                    <table class="native-drawer-table">
                      <thead>
                        <tr>
                          <th v-for="col in bccColumns" :key="col" :style="{ minWidth: bceColWidth(col) + 'px' }">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, rowIndex) in bceContext.bcc_instances" :key="`bcc-${rowIndex}`">
                          <td v-for="col in bccColumns" :key="`${rowIndex}-${col}`" :style="{ minWidth: bceColWidth(col) + 'px' }">
                            <div v-if="row[col] && row[col] !== 'None'" class="copyable-cell" @click.stop>
                              <span class="bce-cell-text">{{ row[col] }}</span>
                              <el-icon class="copy-icon" @click="copyToClipboard(row[col], col)"><DocumentCopy /></el-icon>
                            </div>
                            <span v-else style="color: var(--text-tertiary, #9ca3af);">-</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div v-else class="bce-empty-tip">无 BCC 关联记录</div>
              </div>

              <!-- CCE 节点 -->
              <div class="drawer-sub-section">
                <div class="drawer-sub-title">CCE 节点 <span class="drawer-sub-count">{{ bceContext.cce_nodes?.length || 0 }}</span></div>
                <div class="table-wrapper" v-if="bceContext.cce_nodes?.length">
                  <div class="native-table-scroll">
                    <table class="native-drawer-table">
                      <thead>
                        <tr>
                          <th v-for="col in cceColumns" :key="col" :style="{ minWidth: bceColWidth(col) + 'px' }">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, rowIndex) in bceContext.cce_nodes" :key="`cce-${rowIndex}`">
                          <td v-for="col in cceColumns" :key="`${rowIndex}-${col}`" :style="{ minWidth: bceColWidth(col) + 'px' }">
                            <div v-if="row[col] && row[col] !== 'None'" class="copyable-cell" @click.stop>
                              <span class="bce-cell-text">{{ row[col] }}</span>
                              <el-icon class="copy-icon" @click="copyToClipboard(row[col], col)"><DocumentCopy /></el-icon>
                            </div>
                            <span v-else style="color: var(--text-tertiary, #9ca3af);">-</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div v-else class="bce-empty-tip">无 CCE 关联记录</div>
              </div>
            </template>
          </el-tab-pane>
        </el-tabs>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { Monitor, Cpu, Odometer, Coin, Search, Upload, Refresh, Delete, Grid, DocumentCopy, Setting, Tools, FolderOpened, ArrowDown, Connection } from '@element-plus/icons-vue'
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

// 当前有效关键词数量（用于提示）
const searchKeywordCount = computed(() => {
  if (!searchText.value.trim()) return 0
  return searchText.value.split(/[\n,]/).filter(k => k.trim()).length
})
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

// BCE 关联信息（按需加载，随抽屉打开重置）
const bceContext = ref({ bcc_instances: [], cce_nodes: [], ip_list: [] })
const bceContextLoading = ref(false)
const bceContextLoaded = ref(false)

// 资源使用 Tab - 进度条颜色阶梯（数组格式，兼容 el-progress）
const progressColorStops = [  { color: '#67c23a', percentage: 70 },
  { color: '#e6a23c', percentage: 90 },
  { color: '#f56c6c', percentage: 100 },
]

// 资源使用 Tab - 动态 KV 字段（过滤掉 null/0/空，展示有意义的字段）
const resourceKVItems = computed(() => {
  if (!currentServer.value) return []
  const s = currentServer.value
  const candidates = [
    { key: 'nova_host_azone', label: '可用区', value: s.nova_host_azone },
    { key: 'nova_host_cluster', label: '集群', value: s.nova_host_cluster },
    { key: 'nova_host_node_type', label: '节点类型', value: s.nova_host_node_type },
    { key: 'nova_host_node_state', label: '节点状态', value: s.nova_host_node_state },
    { key: 'nova_host_model', label: '主机型号', value: s.nova_host_model },
    { key: 'nova_host_machine_suit', label: '机器套件', value: s.nova_host_machine_suit },
    { key: 'nova_host_physical_cpus', label: '物理CPU核数', value: s.nova_host_physical_cpus },
    { key: 'nova_host_vcpus_total', label: 'vCPU总数', value: s.nova_host_vcpus_total },
    { key: 'nova_host_vcpus_used', label: 'vCPU已用', value: s.nova_host_vcpus_used },
    { key: 'nova_host_vcpus_free', label: 'vCPU空闲', value: s.nova_host_vcpus_free },
    { key: 'nova_host_running_vms', label: '运行实例', value: s.nova_host_running_vms != null ? `${s.nova_host_running_vms} 个` : null },
    { key: 'nova_host_physical_disk_gb_free', label: '磁盘剩余', value: s.nova_host_physical_disk_gb_free ? `${s.nova_host_physical_disk_gb_free} GB` : null },
    { key: 'nova_host_net_bandwidth', label: '网络带宽', value: s.nova_host_net_bandwidth },
    { key: 'rms_idc', label: '数据中心', value: s.rms_idc },
    { key: 'rms_rack_info', label: '机架位置', value: s.rms_rack_info },
    { key: 'rms_ip_in1', label: '内网IP1', value: s.rms_ip_in1 },
    { key: 'rms_ip_in2', label: '内网IP2', value: s.rms_ip_in2 },
    { key: 'rms_ilo_ip', label: '带外IP', value: s.rms_ilo_ip },
    { key: 'rms_kernel', label: '内核版本', value: s.rms_kernel },
    { key: 'nova_host_blacklisted_reason', label: '加黑原因', value: s.nova_host_blacklisted_reason },
  ]
  return candidates.filter(item => item.value !== null && item.value !== undefined && item.value !== '' && item.value !== 0)
})

// BCE Tab - 动态列（从数据第一行取所有 key，过滤内部字段）
const BCE_SKIP_COLS = new Set(['id', 'insert_time'])

// 实例 Tab - 固定列定义（顺序 + 宽度 + 友好标签）
const instanceColumns = [
  { key: 'nova_vm_instance_uuid', label: 'UUID', width: 240, minWidth: 200 },
  { key: 'nova_vm_fixed_ips',     label: 'IP',   width: 130, minWidth: 120 },
  { key: 'nova_vm_vm_state',      label: '状态',  width: 80, minWidth: 70  },
  { key: 'nova_vm_vcpus',         label: 'vCPU', width: 60, minWidth: 60  },
  { key: 'nova_vm_memory_mb',     label: '内存',  width: 90, minWidth: 80  },
  { key: 'nova_vm_root_gb',       label: '系统盘(G)', width: 90, minWidth: 80 },
  { key: 'nova_vm_ephemeral_gb',  label: '临时盘(G)', width: 90, minWidth: 80 },
  { key: 'nova_vm_metadata_source', label: '来源', width: 90, minWidth: 80 },
  { key: 'nova_vm_display_name',  label: '显示名', width: 150, minWidth: 120 },
  { key: 'nova_vm_azone',         label: '可用区', width: 100, minWidth: 90 },
  { key: 'nova_vm_cluster',       label: '集群',  width: 120, minWidth: 100 },
  { key: 'nova_vm_power_state',   label: '电源',  width: 70, minWidth: 70  },
  { key: 'nova_vm_task_state',    label: '任务',  width: 80, minWidth: 70  },
  { key: 'nova_vm_created_at',    label: '创建时间', width: 160, minWidth: 140 },
]
const bccColumns = computed(() => {
  const rows = bceContext.value?.bcc_instances
  if (!rows?.length) return []
  return Object.keys(rows[0]).filter(k => !BCE_SKIP_COLS.has(k))
})
const cceColumns = computed(() => {
  const rows = bceContext.value?.cce_nodes
  if (!rows?.length) return []
  return Object.keys(rows[0]).filter(k => !BCE_SKIP_COLS.has(k))
})
// 根据列名自动推断合适的最小宽度
const bceColWidth = (col) => {
  if (['id', 'bcc_id', '实例名称_id', 'cluster_id'].includes(col)) return 140
  if (['名称', '节点名称', '实例规格', '配置_类型', '操作系统名称'].includes(col)) return 160
  if (['描述', '标签', 'ipv6地址'].includes(col)) return 200
  if (['主ipv4私网地址', '主ipv4公网地址', 'ip地址', 'ip??'].includes(col)) return 130
  if (['collect_date', '创建时间', '到期时间'].includes(col)) return 110
  return 100
}

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

const loadBceContext = async (hostname) => {
  bceContextLoading.value = true
  try {
    const res = await cmdbApi.getServerBceContext(hostname)
    bceContext.value = res
    bceContextLoaded.value = true
  } catch (e) {
    ElMessage.error('BCE 关联查询失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    bceContextLoading.value = false
  }
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
    currentServer.value = response.server
    serverInstances.value = response.instances
    // 重置 BCE 关联状态（新抽屉按需加载）
    bceContext.value = { bcc_instances: [], cce_nodes: [], ip_list: [] }
    bceContextLoaded.value = false
    bceContextLoading.value = false
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

/* 单元格容器需要撑满列宽，否则 el-progress 宽度为 0 */
.cell-wrapper {
  width: 100%;
  min-width: 0;
}

/* 主列表表格样式优化 */
.google-table {
  width: 100%;
}

.google-table :deep(.el-table__header th) {
  background: var(--bg-secondary, #f9fafb);
  font-weight: 600;
  white-space: normal;
  line-height: 1.3;
  padding: 8px 4px;
}

.google-table :deep(.el-table__header .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.3;
}

.google-table :deep(.el-table__body td) {
  padding: 8px 4px;
}

.google-table :deep(.el-table .cell) {
  padding: 0 4px;
  line-height: 1.5;
}

/* 详情页描述列表内容不换行（加黑说明等长文本除外） */
.modern-descriptions :deep(.el-descriptions__content) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 搜索框宽度 */
.search-box {
  position: relative;
}

.search-box :deep(.el-textarea) {
  width: 350px;
}

.search-box :deep(.el-textarea__inner) {
  resize: none;
  font-size: var(--text-sm);
  line-height: 1.5;
}

.search-hint {
  position: absolute;
  bottom: -18px;
  left: 4px;
  font-size: 11px;
  color: var(--primary);
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
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding-right: 8px;
}

.copyable-cell .cell-text,
.copyable-cell .bce-cell-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.copyable-cell .copy-icon {
  opacity: 0 !important;
  transition: opacity 0.2s ease;
  cursor: pointer;
  color: var(--color-primary);
  font-size: 14px;
  flex-shrink: 0;
  margin-right: 4px;
}

.copyable-cell:hover .copy-icon {
  opacity: 1 !important;
}

.copyable-cell .copy-icon:hover {
  color: var(--color-primary-hover);
  transform: scale(1.1);
}

@media (max-width: 768px) {
  .search-box :deep(.el-textarea) {
    width: 100%;
  }
}

.bce-empty-tip {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.bce-cell-text {
  font-size: 12px;
  white-space: nowrap;
}

/* 抽屉 Tab 样式 */
.drawer-tabs {
  height: 100%;
}
.drawer-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
.drawer-tabs :deep(.el-tabs__content) {
  overflow-y: auto;
  max-height: calc(100vh - 120px);
}

/* 基本信息 KV 网格 */
.drawer-kv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  background: var(--border-primary, #e5e7eb);
  border: 1px solid var(--border-primary, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
}
.kv-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-primary, #fff);
}
.kv-item-full {
  grid-column: 1 / -1;
}
.kv-label {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-tertiary, #9ca3af);
  min-width: 72px;
}
.kv-label-warn {
  color: #e6a23c;
}
.kv-value {
  font-size: 13px;
  color: var(--text-primary, #111827);
  word-break: break-all;
}
.kv-value.copyable {
  cursor: pointer;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
}
.kv-value.copyable:hover {
  color: var(--primary, #3b82f6);
}

/* 可复制值样式 */
.kv-value.kv-copyable {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.kv-value.kv-copyable .kv-copy-icon {
  opacity: 0;
  transition: opacity 0.2s ease;
  color: var(--primary, #3b82f6);
  font-size: 14px;
  flex-shrink: 0;
}

.kv-value.kv-copyable:hover .kv-copy-icon {
  opacity: 1;
}

.kv-value.kv-copyable:hover {
  color: var(--primary, #3b82f6);
}

/* 资源使用卡片 */
.drawer-resource-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.resource-card {
  padding: 16px;
  border: 1px solid var(--border-primary, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-primary, #fff);
}
.resource-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.resource-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
}
.resource-card-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #111827);
  font-family: var(--font-mono, monospace);
}
.resource-card-sub {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-tertiary, #9ca3af);
}

/* 进度条样式 - 资源使用卡片 */
.progress-track {
  width: 100%;
  height: 4px;
  background: var(--border-primary, #e5e7eb);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 8px;
}

.progress-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease, background 0.3s ease;
  min-width: 2px;
}

/* BCE 关联 Tab 内部分节 */
.drawer-sub-section {
  margin-bottom: 20px;
}
.drawer-sub-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.drawer-sub-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 5px;
  background: var(--bg-secondary, #f3f4f6);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary, #9ca3af);
}
.drawer-bce-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

/* 表格包装器 - 修复内容超出和框线对齐问题 */
.table-wrapper {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border-primary, #e5e7eb);
  overflow: hidden;
}

.native-table-scroll {
  width: 100%;
  max-height: 280px;
  overflow: auto;
}

.native-drawer-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: var(--bg-primary);
}

.native-drawer-table th,
.native-drawer-table td {
  border-right: 1px solid var(--border-primary, #e5e7eb);
  border-bottom: 1px solid var(--border-primary, #e5e7eb);
  padding: 8px 10px;
  box-sizing: border-box;
  vertical-align: top;
}

.native-drawer-table th {
  background: var(--bg-secondary, #f9fafb);
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
}

.native-drawer-table th:last-child,
.native-drawer-table td:last-child {
  border-right: none;
}

.native-drawer-table tbody tr:last-child td {
  border-bottom: none;
}

.native-drawer-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
}

</style>
