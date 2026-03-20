<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Bell /></el-icon>
          </div>
          硬件告警管理
        </div>
        <div class="page-subtitle">实时监控硬件告警,快速定位和诊断问题</div>
      </div>
    </div>

    <!-- 筛选器 -->
    <div class="filter-section">
      <el-form :model="filters" class="filter-row">
        <div class="filter-item">
          <span class="filter-item-label">告警类型</span>
          <el-select
            v-model="filters.alert_type"
            placeholder="全部"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="type in filterOptions.alert_types"
              :key="type"
              :label="type"
              :value="type"
            />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-item-label">严重程度</span>
          <el-select
            v-model="filters.severity"
            placeholder="全部"
            clearable
            style="width: 100%"
          >
            <el-option label="Critical" value="critical" />
            <el-option label="Warning" value="warning" />
            <el-option label="Info" value="info" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-item-label">组件类型</span>
          <el-select
            v-model="filters.component"
            placeholder="全部"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="comp in filterOptions.components"
              :key="comp"
              :label="comp"
              :value="comp"
            />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-item-label">处理状态</span>
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="stat in filterOptions.statuses"
              :key="stat"
              :label="statusLabels[stat]"
              :value="stat"
            />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-item-label">告警来源</span>
          <el-select
            v-model="filters.source"
            placeholder="全部"
            clearable
            style="width: 100%"
          >
            <el-option label="HAS告警" value="file" />
            <el-option label="手动录入" value="manual" />
          </el-select>
        </div>

        <div class="filter-item">
          <span class="filter-item-label">节点IP</span>
          <el-input
            v-model="filters.ip"
            placeholder="输入IP模糊搜索"
            clearable
            style="width: 100%"
          />
        </div>

        <div class="filter-item">
          <span class="filter-item-label">集群ID</span>
          <el-input
            v-model="filters.cluster_id"
            placeholder="输入集群ID模糊搜索"
            clearable
            style="width: 100%"
          />
        </div>

        <div class="filter-item" style="min-width: 360px;">
          <span class="filter-item-label">时间范围</span>
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 100%"
            @change="handleDateRangeChange"
          />
        </div>

        <div class="filter-actions">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </div>
      </el-form>
    </div>

    <!-- 告警列表 -->
    <div class="table-container">
      <!-- 表头 -->
      <div class="table-header">
        <div class="table-title">告警列表</div>
        <div class="table-toolbar">
          <el-button
            type="primary"
            :icon="Plus"
            @click="handleCreateAlert"
          >
            手动添加告警
          </el-button>
          <el-button
            type="warning"
            :icon="Notification"
            @click="handleBatchResendNotifications"
            :loading="batchResending"
          >
            批量补发通知（全部）
          </el-button>
          <el-button
            type="primary"
            :icon="Notification"
            @click="handleSelectedResendNotifications"
            :disabled="selectedAlerts.length === 0"
            :loading="batchResending"
          >
            补发选中通知（{{ selectedAlerts.length }}）
          </el-button>
          <el-button
            type="success"
            :icon="Edit"
            @click="handleDetectAndCorrectClusterIds"
            :loading="batchCorrecting"
          >
            检测并修正cluster_id
          </el-button>
          <el-tooltip
            content="从宿主机数据库查询正确的cluster_id，修正容器内数据库的告警记录"
            placement="top"
          >
            <el-icon style="margin-left: 8px; cursor: help; color: var(--text-tertiary);">
              <QuestionFilled />
            </el-icon>
          </el-tooltip>
        </div>
      </div>

      <!-- 表格主体 -->
      <div class="table-body">
        <!-- 首次加载：显示骨架屏 -->
        <el-skeleton
          v-if="loading && !alertList.length"
          :rows="10"
          animated
        />

        <!-- 数据加载完成：显示表格 -->
        <el-table
          v-else-if="alertList.length > 0"
          v-loading="loading"
          :data="alertList"
          @row-click="handleRowClick"
          @selection-change="handleSelectionChange"
          @sort-change="handleSortChange"
          class="google-table"
          aria-label="硬件告警列表"
        >
          <el-table-column type="selection" width="55" />

          <el-table-column prop="id" label="ID" width="80" sortable="custom" />

          <el-table-column prop="alert_type" label="告警类型" min-width="180" sortable="custom" />

          <el-table-column prop="component" label="组件" width="120" sortable="custom">
            <template #default="{ row }">
              <span :class="`status-badge ${getComponentBadgeClass(row.component)}`">
                {{ row.component }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="severity" label="严重程度" width="120" sortable="custom">
            <template #default="{ row }">
              <span
                :class="`status-badge ${getSeverityBadgeClass(row.severity)}`"
                :aria-label="`严重程度：${getSeverityLabel(row.severity)}`"
              >
                <span :class="`status-dot ${getSeverityBadgeClass(row.severity)}`"></span>
                {{ getSeverityLabel(row.severity) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="ip" label="节点IP" width="140" sortable="custom" />

          <el-table-column prop="cluster_id" label="集群ID" width="150" show-overflow-tooltip sortable="custom" />

          <el-table-column prop="timestamp" label="发生时间" width="180" sortable="custom">
            <template #default="{ row }">
              {{ formatDateTime(row.timestamp) }}
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="120" sortable="custom">
            <template #default="{ row }">
              <span
                :class="`status-badge ${getStatusBadgeClass(row.status)}`"
              >
                <span :class="`status-dot ${getStatusBadgeClass(row.status)}`"></span>
                {{ statusLabels[row.status] }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="source" label="来源" width="100" sortable="custom">
            <template #default="{ row }">
              <span :class="`status-badge ${getSourceBadgeClass(row.source)}`">
                {{ getSourceLabel(row.source) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="诊断" width="80" align="center">
            <template #default="{ row }">
              <el-icon
                v-if="row.has_diagnosis"
                :size="18"
                aria-label="已诊断"
                style="color: var(--color-success);"
              >
                <CircleCheck />
              </el-icon>
              <el-icon
                v-else
                :size="18"
                aria-label="未诊断"
                style="color: var(--text-disabled);"
              >
                <CircleClose />
              </el-icon>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="action-grid">
                <div class="action-row action-row-primary">
                  <button class="action-btn btn-primary" @click.stop="handleViewDetail(row.id)">查看详情</button>
                  <button class="action-btn btn-primary" @click.stop="handleChangeStatus(row)">修改状态</button>
                  <button class="action-btn btn-primary" @click.stop="handleEditAlert(row)">编辑字段</button>
                </div>
                <div class="action-row action-row-secondary">
                  <button class="action-btn btn-secondary" @click.stop="handleAddNote(row)">添加备注</button>
                  <button class="action-btn btn-secondary" @click.stop="handleDiagnose(row.id)" :disabled="diagnosingIds.includes(row.id)">{{ diagnosingIds.includes(row.id) ? '诊断中' : '重新诊断' }}</button>
                  <button class="action-btn btn-secondary" @click.stop="handleCreateICafeCard(row)">创建卡片</button>
                </div>
              </div>
            </template>
          </el-table-column>
        </el-table>

      <!-- 空状态 -->
      <el-empty
        v-else-if="!loading && !alertList.length"
        :image-size="200"
      >
        <template #description>
          <p class="empty-title">暂无告警数据</p>
          <p class="empty-subtitle">
            {{ hasFilters ? '尝试调整筛选条件' : '系统运行正常，暂无硬件告警' }}
          </p>
        </template>

        <template #default>
          <el-button
            v-if="hasFilters"
            type="primary"
            @click="handleReset"
          >
            <el-icon><Refresh /></el-icon>
            清除筛选
          </el-button>
          <el-button
            v-else
            @click="fetchAlerts"
          >
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
        </template>
      </el-empty>
      </div>

      <!-- 分页 -->
      <div v-if="alertList.length > 0" class="table-footer">
        <div>共 {{ pagination.total }} 条</div>
        <div class="google-pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- 编辑告警字段对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑告警字段"
      width="600px"
      :close-on-click-modal="false"
      class="google-dialog"
      append-to-body
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-position="top"
        class="google-form"
        @submit.prevent="handleEditSubmit"
      >
        <el-form-item label="告警ID">
          <el-input v-model="editForm.alertId" readonly />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="告警类型" prop="alertType">
              <el-select
                v-model="editForm.alertType"
                placeholder="请选择告警类型"
                filterable
                allow-create
                default-first-option
                style="width: 100%"
                teleported
                popper-class="dialog-select-popper"
              >
                <el-option
                  v-for="type in alertTypeEnums"
                  :key="type"
                  :label="type"
                  :value="type"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="严重程度" prop="severity">
              <el-select v-model="editForm.severity" placeholder="请选择严重程度" style="width: 100%" teleported popper-class="dialog-select-popper">
                <el-option label="严重 (Critical)" value="critical" />
                <el-option label="警告 (Warning)" value="warning" />
                <el-option label="信息 (Info)" value="info" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="组件类型" prop="component">
              <el-select v-model="editForm.component" placeholder="请选择组件类型" style="width: 100%" teleported popper-class="dialog-select-popper">
                <el-option
                  v-for="comp in componentEnums"
                  :key="comp"
                  :label="comp"
                  :value="comp"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="节点IP" prop="ip">
              <el-input
                v-model="editForm.ip"
                placeholder="例如: 192.168.1.1"
                maxlength="100"
                show-word-limit
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="集群ID" prop="clusterId">
              <el-input
                v-model="editForm.clusterId"
                placeholder="例如: cce-xxx 或 bcc-xxx"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主机名" prop="hostname">
              <el-input
                v-model="editForm.hostname"
                placeholder="请输入主机名"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="实例ID" prop="instanceId">
          <el-input
            v-model="editForm.instanceId"
            placeholder="请输入实例ID"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleEditCancel">取消</el-button>
          <el-button type="primary" @click="handleEditSubmit">
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 状态编辑对话框 -->
    <el-dialog
      v-model="statusDialogVisible"
      title="修改告警状态"
      width="500px"
      :close-on-click-modal="false"
      class="google-dialog"
      append-to-body
    >
      <el-form
        ref="statusFormRef"
        :model="statusForm"
        label-position="top"
        class="google-form"
        @submit.prevent="handleStatusSubmit"
      >
        <el-form-item label="告警类型">
          <el-input v-model="statusForm.alertType" readonly />
        </el-form-item>

        <el-form-item label="当前状态">
          <span :class="`status-badge ${getStatusBadgeClass(statusForm.currentStatus)}`">
            <span :class="`status-dot ${getStatusBadgeClass(statusForm.currentStatus)}`"></span>
            {{ statusLabels[statusForm.currentStatus] }}
          </span>
        </el-form-item>

        <el-form-item label="新状态" required>
          <el-select v-model="statusForm.newStatus" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已诊断" value="diagnosed" />
            <el-option label="已通知" value="notified" />
            <el-option label="已处理" value="resolved" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="handleStatusCancel">取消</el-button>
        <el-button type="primary" @click="handleStatusSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 备注编辑对话框 -->
    <el-dialog
      v-model="noteDialogVisible"
      title="添加告警备注"
      width="600px"
      :close-on-click-modal="false"
      class="google-dialog"
      append-to-body
    >
      <el-form
        ref="noteFormRef"
        :model="noteForm"
        label-position="top"
        class="google-form"
        @submit.prevent="handleNoteSubmit"
      >
        <el-form-item label="告警类型">
          <el-input v-model="noteForm.alertType" readonly />
        </el-form-item>

        <el-form-item label="备注内容" required>
          <el-input
            v-model="noteForm.notes"
            type="textarea"
            :rows="6"
            placeholder="请输入备注内容，如：问题描述、处理过程、解决方案等"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="handleNoteCancel">取消</el-button>
        <el-button type="primary" @click="handleNoteSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- iCafe 卡片创建对话框 -->
    <el-dialog
      v-model="icafeDialogVisible"
      title="创建 iCafe 卡片"
      width="700px"
      :close-on-click-modal="false"
      class="google-dialog"
      append-to-body
    >
      <el-form
        ref="icafeFormRef"
        :model="icafeForm"
        label-position="top"
        class="google-form"
        label-width="120px"
        :rules="icafeFormRules"
        @submit.prevent="handleICafeSubmit"
      >
        <!-- 告警信息展示 -->
        <el-form-item label="告警信息">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="告警类型">{{ icafeForm.alertType }}</el-descriptions-item>
            <el-descriptions-item label="节点IP">{{ icafeForm.nodeIP }}</el-descriptions-item>
            <el-descriptions-item label="组件">{{ icafeForm.component }}</el-descriptions-item>
            <el-descriptions-item label="严重程度">{{ icafeForm.severity }}</el-descriptions-item>
            <el-descriptions-item label="集群ID" v-if="icafeForm.clusterID">{{ icafeForm.clusterID }}</el-descriptions-item>
          </el-descriptions>
        </el-form-item>

        <!-- 自动生成的卡片标题 -->
        <el-form-item label="卡片标题">
          <el-input v-model="icafeForm.generatedTitle" readonly />
        </el-form-item>

        <!-- 手动填写字段 -->
        <el-form-item label="负责人" prop="responsiblePerson" required>
          <el-input
            v-model="icafeForm.responsiblePerson"
            placeholder="请输入负责人姓名"
            maxlength="50"
          />
        </el-form-item>

        <el-form-item label="细分分类" prop="subcategory" required>
          <el-input
            v-model="icafeForm.subcategory"
            placeholder="例如：BCC,GPU"
            maxlength="100"
          />
          <div class="form-tip">多个分类用逗号分隔，例如：BCC,GPU</div>
        </el-form-item>

        <el-form-item label="工时" prop="workHours" required>
          <el-input-number
            v-model="icafeForm.workHours"
            :min="0.1"
            :max="999"
            :step="0.1"
            :precision="1"
            placeholder="请输入预估工时"
            style="width: 200px"
          />
          <span style="margin-left: 8px; color: #909399;">小时</span>
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
          <el-button @click="handleICafeCancel">取消</el-button>
          <el-button
            type="primary"
            @click="handleICafeSubmit"
            :loading="icafeCreating"
          >
            创建卡片
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建告警对话框 -->
    <el-dialog
      v-model="createAlertDialogVisible"
      title="手动添加告警"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createAlertFormRef"
        :model="createAlertForm"
        :rules="createAlertRules"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="告警类型" prop="alert_type">
              <el-select
                v-model="createAlertForm.alert_type"
                placeholder="请选择告警类型"
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option
                  v-for="type in alertTypeEnums"
                  :key="type"
                  :label="type"
                  :value="type"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="严重程度" prop="severity">
              <el-select v-model="createAlertForm.severity" placeholder="请选择" style="width: 100%">
                <el-option label="严重 (Critical)" value="critical" />
                <el-option label="警告 (Warning)" value="warning" />
                <el-option label="信息 (Info)" value="info" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="组件类型" prop="component">
              <el-select
                v-model="createAlertForm.component"
                placeholder="请选择组件类型"
                clearable
                style="width: 100%"
              >
                <el-option
                  v-for="comp in componentEnums"
                  :key="comp"
                  :label="comp"
                  :value="comp"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="告警时间" prop="timestamp">
              <el-date-picker
                v-model="createAlertForm.timestamp"
                type="datetime"
                placeholder="选择告警时间"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="节点IP" prop="ip">
              <el-input
                v-model="createAlertForm.ip"
                placeholder="例如: 192.168.1.1"
                maxlength="100"
                show-word-limit
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="集群ID" prop="cluster_id">
              <el-input
                v-model="createAlertForm.cluster_id"
                placeholder="例如: cce-xxx 或 bcc-xxx"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="实例ID" prop="instance_id">
              <el-input
                v-model="createAlertForm.instance_id"
                placeholder="请输入实例ID"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主机名" prop="hostname">
              <el-input
                v-model="createAlertForm.hostname"
                placeholder="请输入主机名"
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="CCE集群">
          <el-switch
            v-model="createAlertForm.is_cce_cluster"
            active-text="是"
            inactive-text="否"
          />
          <el-text type="info" size="small" style="margin-left: 10px">
            自动判断：集群ID以 cce- 开头则为CCE集群
          </el-text>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleCreateAlertCancel">取消</el-button>
          <el-button
            type="primary"
            @click="handleCreateAlertSubmit"
            :loading="createAlertLoading"
          >
            创建告警
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, CircleCheck, CircleClose, Notification, QuestionFilled, Edit, EditPen, Bell, Plus } from '@element-plus/icons-vue'
import { getAlerts, getFilterOptions, diagnoseAlert, batchResendNotifications, updateAlertStatus, createICafeCard, detectIncorrectAlerts, correctClusterIds, testHostConnection, updateAlertFields, createAlert, getComponentEnums, getAlertTypeEnums } from '@/api/alerts'

const router = useRouter()

// 状态标签映射
const statusLabels = {
  pending: '待处理',
  processing: '处理中',
  diagnosed: '已诊断',
  notified: '已通知',
  failed: '失败',
  resolved: '已处理'
}

// Google Blue 样式映射函数
const getSeverityBadgeClass = (severity) => {
  const classes = {
    critical: 'error',
    warning: 'warning',
    info: 'info'
  }
  return classes[severity] || 'primary'
}

const getComponentBadgeClass = (component) => {
  // 组件类型默认用primary风格
  return 'primary'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    resolved: 'success',
    notified: 'info',
    diagnosed: 'primary',
    processing: 'warning',
    pending: 'warning',
    failed: 'error'
  }
  return classes[status] || 'primary'
}

const getSourceBadgeClass = (source) => {
  const classes = {
    file: 'info',      // HAS告警 - 蓝色
    manual: 'warning'  // 手动录入 - 橙色
  }
  return classes[source] || 'primary'
}

const getSourceLabel = (source) => {
  const labels = {
    file: 'HAS告警',
    manual: '手动录入'
  }
  return labels[source] || source || '未知'
}

// 数据
const loading = ref(false)
const alertList = ref([])
const filterOptions = reactive({
  alert_types: [],
  components: [],
  clusters: [],
  severity_levels: [],
  statuses: []
})

// 筛选条件
const filters = reactive({
  alert_type: '',
  severity: '',
  component: '',
  status: '',
  ip: '',           // 节点IP搜索
  cluster_id: '',   // 集群ID搜索
  source: '',       // 告警来源筛选
  start_time: '',
  end_time: '',
  sort_by: 'timestamp',  // 默认按时间排序
  sort_order: 'desc'      // 默认降序
})

const dateRange = ref([])

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 正在诊断的告警ID列表
const diagnosingIds = ref([])

// 批量补发通知状态
const batchResending = ref(false)

// 批量修正cluster_id状态
const batchCorrecting = ref(false)

// 表格选择
const selectedAlerts = ref([])  // 选中的告警列表

// 编辑告警字段对话框
const editDialogVisible = ref(false)
const editForm = reactive({
  alertId: null,
  alertType: '',
  component: '',
  severity: '',
  ip: '',
  clusterId: '',
  hostname: '',
  instanceId: ''
})

// 编辑表单验证规则
const editFormRules = {
  alertType: [
    { required: true, message: '请选择告警类型', trigger: 'change' },
    { max: 200, message: '告警类型不能超过200个字符', trigger: 'blur' }
  ],
  component: [
    { required: true, message: '请选择组件类型', trigger: 'change' }
  ],
  severity: [
    { required: true, message: '请选择严重程度', trigger: 'change' }
  ],
  // 选填字段的校验（防止超出数据库限制）
  ip: [
    { max: 100, message: 'IP地址不能超过100个字符', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback() // 空值不校验格式
          return
        }
        // 支持IPv4和IPv6以及主机名
        const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$|^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$/
        if (!ipPattern.test(value)) {
          callback(new Error('请输入有效的IP地址或主机名'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  clusterId: [
    { max: 200, message: '集群ID不能超过200个字符', trigger: 'blur' }
  ],
  hostname: [
    { max: 200, message: '主机名不能超过200个字符', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9\-_\.]+$/,
      message: '主机名只能包含字母、数字、横线、下划线和点号',
      trigger: 'blur'
    }
  ],
  instanceId: [
    { max: 200, message: '实例ID不能超过200个字符', trigger: 'blur' }
  ]
}

// 状态编辑对话框
const statusDialogVisible = ref(false)
const statusForm = reactive({
  alertId: null,
  alertType: '',
  currentStatus: '',
  newStatus: ''
})

// 备注编辑对话框
const noteDialogVisible = ref(false)
const noteForm = reactive({
  alertId: null,
  alertType: '',
  notes: ''
})

// iCafe 卡片创建对话框
const icafeDialogVisible = ref(false)
const icafeCreating = ref(false)
const icafeForm = reactive({
  alertId: null,
  alertType: '',
  nodeIP: '',
  component: '',
  severity: '',
  clusterID: '',
  generatedTitle: '',
  responsiblePerson: '',
  subcategory: '',
  workHours: 1,
  plan: ''
})

// iCafe 表单验证规则
const icafeFormRules = {
  responsiblePerson: [
    { required: true, message: '请输入负责人', trigger: 'blur' }
  ],
  subcategory: [
    { required: true, message: '请输入细分分类', trigger: 'blur' }
  ],
  workHours: [
    { required: true, message: '请输入工时', trigger: 'blur' },
    { type: 'number', min: 0.1, message: '工时必须大于0', trigger: 'blur' }
  ],
  plan: [
    { required: true, message: '请选择所属计划', trigger: 'change' }
  ]
}

const statusFormRef = ref(null)
const noteFormRef = ref(null)
const editFormRef = ref(null)
const icafeFormRef = ref(null)
const createAlertFormRef = ref(null)

// 创建告警对话框
const createAlertDialogVisible = ref(false)
const createAlertLoading = ref(false)
const componentEnums = ref([])
const alertTypeEnums = ref([])
const createAlertForm = reactive({
  alert_type: '',
  severity: 'warning',
  component: '',
  ip: '',
  cluster_id: '',
  instance_id: '',
  hostname: '',
  timestamp: new Date(),
  is_cce_cluster: false
})

// 创建告警表单验证规则
const createAlertRules = {
  alert_type: [
    { required: true, message: '请选择告警类型', trigger: 'change' },
    { max: 200, message: '告警类型不能超过200个字符', trigger: 'blur' }
  ],
  severity: [
    { required: true, message: '请选择严重程度', trigger: 'change' }
  ],
  timestamp: [
    { required: true, message: '请选择告警时间', trigger: 'change' }
  ],
  // 选填字段的校验（防止超出数据库限制）
  ip: [
    { max: 100, message: 'IP地址不能超过100个字符', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) {
          callback() // 空值不校验格式
          return
        }
        // 支持IPv4和IPv6以及主机名
        const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]+$|^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$/
        if (!ipPattern.test(value)) {
          callback(new Error('请输入有效的IP地址或主机名'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  cluster_id: [
    { max: 200, message: '集群ID不能超过200个字符', trigger: 'blur' }
  ],
  instance_id: [
    { max: 200, message: '实例ID不能超过200个字符', trigger: 'blur' }
  ],
  hostname: [
    { max: 200, message: '主机名不能超过200个字符', trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9\-_\.]+$/, 
      message: '主机名只能包含字母、数字、横线、下划线和点号', 
      trigger: 'blur' 
    }
  ],
  component: [
    { max: 100, message: '组件类型不能超过100个字符', trigger: 'blur' }
  ]
}

// 检查是否有筛选条件
const hasFilters = computed(() => {
  return !!(
    filters.alert_type ||
    filters.severity ||
    filters.component ||
    filters.status ||
    filters.ip ||
    filters.cluster_id ||
    filters.source ||
    filters.start_time ||
    filters.end_time
  )
})

// 获取严重程度标签文本
const getSeverityLabel = (severity) => {
  const labels = {
    critical: '严重',
    warning: '警告',
    info: '信息'
  }
  return labels[severity] || severity
}

// 获取筛选选项
const fetchFilterOptions = async () => {
  try {
    const response = await getFilterOptions()
    if (response.success) {
      Object.assign(filterOptions, response.data)
    }
  } catch (error) {
    // Silent error handling
  }
}

// 获取告警列表
const fetchAlerts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...filters
    }
    
    const response = await getAlerts(params)
    if (response.success) {
      alertList.value = response.data.list
      pagination.total = response.data.total
    }
  } catch (error) {
    // Silent error handling
  } finally {
    loading.value = false
  }
}

// 处理时间范围变化
const handleDateRangeChange = (value) => {
  if (value && value.length === 2) {
    filters.start_time = value[0].toISOString()
    filters.end_time = value[1].toISOString()
  } else {
    filters.start_time = ''
    filters.end_time = ''
  }
}

// 查询
const handleSearch = () => {
  pagination.page = 1
  fetchAlerts()
}

// 重置
const handleReset = () => {
  Object.assign(filters, {
    alert_type: '',
    severity: '',
    component: '',
    status: '',
    ip: '',
    cluster_id: '',
    source: '',
    start_time: '',
    end_time: ''
  })
  dateRange.value = []
  pagination.page = 1
  fetchAlerts()
}

// 分页变化
const handleSizeChange = () => {
  pagination.page = 1
  fetchAlerts()
}

const handlePageChange = () => {
  fetchAlerts()
}

// 查看详情
const handleViewDetail = (id) => {
  router.push(`/alerts/${id}`)
}

// 行点击
const handleRowClick = (row) => {
  handleViewDetail(row.id)
}

// 重新诊断
const handleDiagnose = async (id) => {
  diagnosingIds.value.push(id)
  try {
    const response = await diagnoseAlert(id, true)  // 传递布尔值而不是对象
    
    // 检查响应是否成功
    if (response && response.success) {
      ElMessage.success(response.message || '诊断任务已创建')
      // 3秒后刷新列表
      setTimeout(() => {
        fetchAlerts()
      }, 3000)
    } else {
      // 后端返回success:false，但可能基础流程已完成
      const message = response?.message || '诊断处理完成'
      ElMessage.success(message)
      // 仍然刷新列表
      setTimeout(() => {
        fetchAlerts()
      }, 3000)
    }
    
  } catch (error) {
    // 检查是否是axios拦截器抛出的错误（基础流程可能已完成）
    if (error.message && (
      error.message.includes('重新诊断') || 
      error.message.includes('诊断') ||
      error.message.includes('已存在诊断结果')
    )) {
      // 这种情况下，基础流程可能已经完成，显示成功信息并刷新
      ElMessage.success('诊断处理已完成，请查看结果')
      setTimeout(() => {
        fetchAlerts()
      }, 3000)
    } else {
      // 真正的网络错误或其他异常
      ElMessage.error('诊断请求失败，请重试')
    }
  } finally {
    diagnosingIds.value = diagnosingIds.value.filter(item => item !== id)
  }
}

// 批量补发通知（全部未通知的告警）
const handleBatchResendNotifications = async () => {
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      '此操作将为所有未发送通知的告警补发webhook通知。是否继续？',
      '批量补发通知',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    batchResending.value = true
    const response = await batchResendNotifications()
    
    if (response.success) {
      const { total, success, failed } = response.data
      if (success > 0) {
        ElMessage.success(`批量补发完成：成功 ${success} 个，失败 ${failed} 个，共 ${total} 个`)
      } else if (total === 0) {
        ElMessage.info('没有需要补发的告警通知')
      } else {
        ElMessage.warning(`批量补发失败：失败 ${failed} 个，共 ${total} 个`)
      }
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量补发通知失败')
    }
  } finally {
    batchResending.value = false
  }
}

// 补发选中告警的通知
const handleSelectedResendNotifications = async () => {
  if (selectedAlerts.value.length === 0) {
    ElMessage.warning('请先选择要补发通知的告警')
    return
  }
  
  try {
    // 确认对话框
    await ElMessageBox.confirm(
      `此操作将为选中的 ${selectedAlerts.value.length} 个告警补发webhook通知。是否继续？`,
      '补发选中通知',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    batchResending.value = true
    const alertIds = selectedAlerts.value.map(alert => alert.id)
    const response = await batchResendNotifications(alertIds)
    
    if (response.success) {
      const { total, success, failed } = response.data
      if (success > 0) {
        ElMessage.success(`补发完成：成功 ${success} 个，失败 ${failed} 个，共 ${total} 个`)
      } else if (total === 0) {
        ElMessage.info('选中的告警中没有需要补发的通知')
      } else {
        ElMessage.warning(`补发失败：失败 ${failed} 个，共 ${total} 个`)
      }
      // 清空选择
      selectedAlerts.value = []
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('补发选中通知失败')
    }
  } finally {
    batchResending.value = false
  }
}

// 检测并修正cluster_id
const handleDetectAndCorrectClusterIds = async () => {
  try {
    batchCorrecting.value = true
    
    // 先测试宿主机数据库连接
    ElMessage.info('正在测试宿主机数据库连接...')
    const testResponse = await testHostConnection()
    
    if (!testResponse.success) {
      // 显示友好的错误提示
      const suggestions = testResponse.data?.suggestions || []
      const suggestionText = suggestions.length > 0 ? 
        `\n\n建议检查：\n${suggestions.map(s => `• ${s}`).join('\n')}` : ''
      
      await ElMessageBox.alert(
        `宿主机数据库连接失败：${testResponse.error}${suggestionText}`,
        '连接测试失败',
        {
          confirmButtonText: '确定',
          type: 'error'
        }
      )
      return
    }
    
    ElMessage.success('宿主机数据库连接正常')
    
    // 检测需要修正的记录
    ElMessage.info('正在检测需要修正的记录...')
    const detectResponse = await detectIncorrectAlerts()
    
    if (!detectResponse.success) {
      ElMessage.error(`检测失败：${detectResponse.error}`)
      return
    }
    
    const { total, records } = detectResponse.data
    
    if (total === 0) {
      ElMessage.success('所有告警记录的cluster_id都是正确的，无需修正')
      return
    }
    
    // 显示检测结果并确认修正
    const recordsText = records.slice(0, 5).map(r => 
      `ID:${r.id} IP:${r.ip} ${r.current_cluster_id} → ${r.correct_cluster_id}`
    ).join('\n')
    
    const moreText = total > 5 ? `\n... 还有 ${total - 5} 条记录` : ''
    
    await ElMessageBox.confirm(
      `检测到 ${total} 条记录需要修正cluster_id：\n\n${recordsText}${moreText}\n\n是否继续修正？`,
      '检测结果',
      {
        confirmButtonText: '修正',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'detect-result-dialog'
      }
    )
    
    // 执行修正
    ElMessage.info('正在修正cluster_id...')
    const correctResponse = await correctClusterIds()
    
    if (correctResponse.success) {
      const { corrected, skipped, failed } = correctResponse.data
      if (corrected > 0) {
        ElMessage.success(`修正完成：成功 ${corrected} 个，跳过 ${skipped} 个，失败 ${failed} 个`)
        // 刷新列表
        fetchAlerts()
      } else {
        ElMessage.info('没有记录需要修正')
      }
    } else {
      ElMessage.error(`修正失败：${correctResponse.error}`)
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败，请检查宿主机数据库连接')
    }
  } finally {
    batchCorrecting.value = false
  }
}

// 处理表格选择变化
const handleSelectionChange = (selection) => {
  selectedAlerts.value = selection
}

// 处理表格排序变化
const handleSortChange = ({ prop, order }) => {
  if (!prop || !order) {
    // 清除排序，恢复默认
    filters.sort_by = 'timestamp'
    filters.sort_order = 'desc'
  } else {
    filters.sort_by = prop
    filters.sort_order = order === 'ascending' ? 'asc' : 'desc'
  }
  // 重新查询
  pagination.page = 1
  fetchAlerts()
}

// 获取组件标签类型
const getComponentTagType = (component) => {
  const typeMap = {
    GPU: 'danger',
    Memory: 'warning',
    CPU: 'success',
    Motherboard: 'info'
  }
  return typeMap[component] || ''
}

// 获取严重程度标签类型
const getSeverityTagType = (severity) => {
  const typeMap = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[severity] || ''
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    pending: 'info',
    processing: 'warning',
    diagnosed: 'success',
    notified: 'success',
    failed: 'danger',
    resolved: 'success'
  }
  return typeMap[status] || ''
}

// 编辑告警字段
const handleEditAlert = async (alert) => {
  // 获取组件枚举值
  try {
    const response = await getComponentEnums()
    if (response.success) {
      componentEnums.value = response.data.components
    }
  } catch (error) {
    // 使用默认值
    componentEnums.value = ['GPU', 'Memory', 'CPU', 'Motherboard', 'Disk', 'Network', 'Power', 'Temperature']
  }

  // 获取告警类型枚举值
  try {
    const response = await getAlertTypeEnums()
    if (response.success) {
      alertTypeEnums.value = response.data.alert_types
    }
  } catch (error) {
    // 使用默认值
    alertTypeEnums.value = [
      'GPU故障', 'GPU温度异常', 'GPU显存不足',
      '内存故障', '内存不足', 'CPU故障', 'CPU温度过高',
      '磁盘故障', '磁盘空间不足', '网络故障',
      '电源故障', '主板故障', '风扇故障', '硬件故障', '系统告警'
    ]
  }

  editForm.alertId = alert.id
  editForm.alertType = alert.alert_type
  editForm.component = alert.component
  editForm.severity = alert.severity
  editForm.ip = alert.ip
  editForm.clusterId = alert.cluster_id || ''
  editForm.hostname = alert.hostname || ''
  editForm.instanceId = alert.instance_id || ''
  editDialogVisible.value = true
}

// 提交编辑
const handleEditSubmit = async () => {
  try {
    // 表单验证
    await editFormRef.value.validate()
    
    const updateData = {
      alert_type: editForm.alertType.trim(),
      component: editForm.component,
      severity: editForm.severity,
      ip: editForm.ip.trim(),
      cluster_id: editForm.clusterId ? editForm.clusterId.trim() : null,
      hostname: editForm.hostname ? editForm.hostname.trim() : null,
      instance_id: editForm.instanceId ? editForm.instanceId.trim() : null
    }
    
    const response = await updateAlertFields(editForm.alertId, updateData)
    
    if (response.success) {
      const updatedFields = response.data.updated_fields
      if (updatedFields && updatedFields.length > 0) {
        ElMessage.success(`字段更新成功：${updatedFields.join(', ')}`)
      } else {
        ElMessage.info('没有字段需要更新')
      }
      editDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    if (error !== 'validation failed') {
      const errorMsg = error.response?.data?.error || error.message || '更新失败'
      ElMessage.error(`更新告警字段失败：${errorMsg}`)
    }
  }
}

// 取消编辑
const handleEditCancel = () => {
  editDialogVisible.value = false
  editForm.alertId = null
  editForm.alertType = ''
  editForm.component = ''
  editForm.severity = ''
  editForm.ip = ''
  editForm.clusterId = ''
  editForm.hostname = ''
  editForm.instanceId = ''
}

// 修改状态
const handleChangeStatus = (alert) => {
  statusForm.alertId = alert.id
  statusForm.alertType = alert.alert_type
  statusForm.currentStatus = alert.status
  statusForm.newStatus = alert.status === 'resolved' ? 'pending' : 'resolved'
  statusDialogVisible.value = true
}

// 添加备注
const handleAddNote = (alert) => {
  noteForm.alertId = alert.id
  noteForm.alertType = alert.alert_type
  noteForm.notes = ''
  noteDialogVisible.value = true
}

// 提交状态更新
const handleStatusSubmit = async () => {
  try {
    const response = await updateAlertStatus(statusForm.alertId, {
      status: statusForm.newStatus
    })
    
    if (response.success) {
      ElMessage.success('告警状态更新成功')
      statusDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    ElMessage.error('更新告警状态失败')
  }
}

// 提交备注
const handleNoteSubmit = async () => {
  try {
    const response = await updateAlertStatus(noteForm.alertId, {
      resolution_notes: noteForm.notes
    })
    
    if (response.success) {
      ElMessage.success('备注添加成功')
      noteDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    }
  } catch (error) {
    ElMessage.error('添加备注失败')
  }
}

// 取消状态编辑
const handleStatusCancel = () => {
  statusDialogVisible.value = false
  statusForm.alertId = null
  statusForm.alertType = ''
  statusForm.currentStatus = ''
  statusForm.newStatus = ''
}

// 取消备注编辑
const handleNoteCancel = () => {
  noteDialogVisible.value = false
  noteForm.alertId = null
  noteForm.alertType = ''
  noteForm.notes = ''
}

// 生成卡片标题
const generateCardTitle = (alert) => {
  const prefix = '【长安LCC】【C3】【硬件维修】'
  if (alert.cluster_id && alert.cluster_id.trim()) {
    return `${prefix} ${alert.cluster_id}集群${alert.ip}节点${alert.alert_type}`
  } else {
    return `${prefix} ${alert.ip}节点${alert.alert_type}`
  }
}

// 创建 iCafe 卡片
const handleCreateICafeCard = (alert) => {
  icafeForm.alertId = alert.id
  icafeForm.alertType = alert.alert_type
  icafeForm.nodeIP = alert.ip
  icafeForm.component = alert.component
  icafeForm.severity = getSeverityLabel(alert.severity)
  icafeForm.clusterID = alert.cluster_id || ''
  icafeForm.generatedTitle = generateCardTitle(alert)
  
  // 重置表单字段
  icafeForm.responsiblePerson = ''
  icafeForm.subcategory = ''
  icafeForm.workHours = 1
  icafeForm.plan = ''
  
  icafeDialogVisible.value = true
}

// 提交 iCafe 卡片创建
const handleICafeSubmit = async () => {
  try {
    // 表单验证
    await icafeFormRef.value.validate()
    
    icafeCreating.value = true
    
    const cardData = {
      responsible_person: icafeForm.responsiblePerson,
      subcategory: icafeForm.subcategory,
      work_hours: icafeForm.workHours,
      plan: icafeForm.plan
    }
    
    const response = await createICafeCard(icafeForm.alertId, cardData)
    
    if (response.success) {
      ElMessage.success('iCafe 卡片创建成功')
      icafeDialogVisible.value = false
      // 可以选择刷新列表或显示卡片链接
    }
  } catch (error) {
    if (error !== 'validation failed') {
      ElMessage.error('创建 iCafe 卡片失败')
    }
  } finally {
    icafeCreating.value = false
  }
}

// 取消 iCafe 卡片创建
const handleICafeCancel = () => {
  icafeDialogVisible.value = false
  icafeForm.alertId = null
  icafeForm.alertType = ''
  icafeForm.nodeIP = ''
  icafeForm.component = ''
  icafeForm.severity = ''
  icafeForm.clusterID = ''
  icafeForm.generatedTitle = ''
  icafeForm.responsiblePerson = ''
  icafeForm.subcategory = ''
  icafeForm.workHours = 1
  icafeForm.plan = ''
}

// 打开创建告警对话框
const handleCreateAlert = async () => {
  // 获取组件枚举值
  try {
    const response = await getComponentEnums()
    if (response.success) {
      componentEnums.value = response.data.components
    }
  } catch (error) {
    // 使用默认值
    componentEnums.value = ['GPU', 'Memory', 'CPU', 'Motherboard', 'Disk', 'Network', 'Power', 'Temperature']
  }

  // 获取告警类型枚举值
  try {
    const response = await getAlertTypeEnums()
    if (response.success) {
      alertTypeEnums.value = response.data.alert_types
    }
  } catch (error) {
    // 使用默认值
    alertTypeEnums.value = [
      'GPU故障', 'GPU温度异常', 'GPU显存不足',
      '内存故障', '内存不足', 'CPU故障', 'CPU温度过高',
      '磁盘故障', '磁盘空间不足', '网络故障',
      '电源故障', '主板故障', '风扇故障', '硬件故障', '系统告警'
    ]
  }

  // 重置表单，时间默认为当前
  createAlertForm.alert_type = ''
  createAlertForm.severity = 'warning'
  createAlertForm.component = ''
  createAlertForm.ip = ''
  createAlertForm.cluster_id = ''
  createAlertForm.instance_id = ''
  createAlertForm.hostname = ''
  createAlertForm.timestamp = new Date()
  createAlertForm.is_cce_cluster = false

  createAlertDialogVisible.value = true
}

// 提交创建告警
const handleCreateAlertSubmit = async () => {
  if (!createAlertFormRef.value) return

  try {
    await createAlertFormRef.value.validate()
    createAlertLoading.value = true

    const data = {
      alert_type: createAlertForm.alert_type,
      severity: createAlertForm.severity,
      component: createAlertForm.component || null,
      ip: createAlertForm.ip || null,
      cluster_id: createAlertForm.cluster_id || null,
      instance_id: createAlertForm.instance_id || null,
      hostname: createAlertForm.hostname || null,
      timestamp: createAlertForm.timestamp.toISOString(),
      is_cce_cluster: createAlertForm.is_cce_cluster || (createAlertForm.cluster_id && createAlertForm.cluster_id.startsWith('cce-'))
    }

    const response = await createAlert(data)
    if (response.success) {
      ElMessage.success('告警创建成功，诊断任务已自动触发')
      createAlertDialogVisible.value = false
      // 刷新列表
      fetchAlerts()
    } else {
      ElMessage.error(response.message || '创建失败')
    }
  } catch (error) {
    if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error('创建失败：' + (error.message || '未知错误'))
    }
  } finally {
    createAlertLoading.value = false
  }
}

// 取消创建告警
const handleCreateAlertCancel = () => {
  createAlertDialogVisible.value = false
  createAlertFormRef.value?.resetFields()
}

// 格式化日期时间
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

// 初始化
onMounted(() => {
  fetchFilterOptions()
  fetchAlerts()
})
</script>

<style scoped>
/* 所有样式已由 google-pages.css 统一提供 */
/* 只保留页面特定的额外样式 */
</style>
