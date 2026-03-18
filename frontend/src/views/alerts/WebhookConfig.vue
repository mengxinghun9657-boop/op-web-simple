<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Connection /></el-icon>
          </div>
          Webhook配置管理
        </div>
        <div class="page-subtitle">配置告警通知的Webhook地址</div>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-extra">
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加Webhook
          </el-button>
        </div>
      </div>
      <div class="content-card-body">

      <el-table v-loading="loading" :data="webhookList" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'feishu' ? 'primary' : 'success'">
              {{ row.type === 'feishu' ? '飞书' : '如流' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="severity_filter" label="严重程度过滤" width="150" />
        <el-table-column prop="keywords" label="关键词" width="120" />
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggleEnable(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleTest(row.id)"
              style="margin-right: 8px;"
            >
              测试
            </el-button>
            <el-button 
              type="primary" 
              size="small" 
              @click="handleEdit(row)"
              style="margin-right: 8px;"
            >
              编辑
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
      append-to-body
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-radio-group v-model="formData.type">
            <el-radio label="feishu">飞书</el-radio>
            <el-radio label="ruliu">如流</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Webhook URL" prop="url">
          <el-input v-model="formData.url" type="textarea" :rows="3" placeholder="请输入Webhook URL" />
        </el-form-item>
        <el-form-item label="访问令牌" prop="access_token">
          <el-input v-model="formData.access_token" placeholder="可选" />
        </el-form-item>
        <el-form-item v-if="formData.type === 'feishu'" label="签名密钥" prop="secret">
          <el-input v-model="formData.secret" type="password" placeholder="飞书签名密钥（可选）" show-password />
        </el-form-item>
        <el-form-item v-if="formData.type === 'ruliu'" label="群组ID" prop="group_id">
          <el-input v-model="formData.group_id" placeholder="如流群组ID（必填）" />
          <div class="form-tip">💡 如流机器人需要配置群组ID，可在如流群组设置中查看</div>
        </el-form-item>
        <el-form-item label="严重程度过滤">
          <el-checkbox-group v-model="severityFilters">
            <el-checkbox label="critical">Critical</el-checkbox>
            <el-checkbox label="warning">Warning</el-checkbox>
            <el-checkbox label="info">Info</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="组件过滤">
          <el-input v-model="formData.component_filter" placeholder="如: GPU,Memory (逗号分隔)" />
        </el-form-item>
        <el-form-item label="关键词" prop="keywords">
          <el-input v-model="formData.keywords" placeholder="飞书机器人关键词(如: 告警)" />
          <div class="form-tip">💡 仅飞书自定义机器人需要配置关键词。消息中必须包含该关键词才能发送成功。如流无此限制。</div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection } from '@element-plus/icons-vue'
import { getWebhooks, createWebhook, updateWebhook, deleteWebhook, testWebhook } from '@/api/webhooks'

const loading = ref(false)
const webhookList = ref([])
const dialogVisible = ref(false)
const dialogTitle = computed(() => formData.id ? '编辑Webhook' : '添加Webhook')
const submitting = ref(false)
const formRef = ref(null)

const formData = reactive({
  id: null,
  name: '',
  type: 'feishu',
  url: '',
  access_token: '',
  secret: '',
  group_id: '',
  severity_filter: '',
  component_filter: '',
  keywords: '',
  enabled: true
})

const severityFilters = ref([])

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  url: [{ required: true, message: '请输入Webhook URL', trigger: 'blur' }]
}

const fetchWebhooks = async () => {
  loading.value = true
  try {
    const response = await getWebhooks()
    if (response.success) {
      webhookList.value = response.data.list || []
    }
  } catch (error) {
    console.error('获取Webhook列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  Object.assign(formData, {
    id: null,
    name: '',
    type: 'feishu',
    url: '',
    access_token: '',
    secret: '',
    group_id: '',
    severity_filter: '',
    component_filter: '',
    keywords: '',
    enabled: true
  })
  severityFilters.value = []
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(formData, { ...row })
  severityFilters.value = row.severity_filter ? row.severity_filter.split(',') : []
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  formData.severity_filter = severityFilters.value.join(',')
  
  submitting.value = true
  try {
    const response = formData.id
      ? await updateWebhook(formData.id, formData)
      : await createWebhook(formData)
    
    if (response.success) {
      ElMessage.success(formData.id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchWebhooks()
    }
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    submitting.value = false
  }
}

const handleToggleEnable = async (row) => {
  try {
    const response = await updateWebhook(row.id, { enabled: row.enabled })
    if (response.success) {
      ElMessage.success('状态更新成功')
    }
  } catch (error) {
    row.enabled = !row.enabled
    console.error('更新状态失败:', error)
  }
}

const handleTest = async (id) => {
  try {
    const response = await testWebhook(id)
    if (response.success) {
      ElMessage.success('测试成功')
    }
  } catch (error) {
    console.error('测试失败:', error)
  }
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除此Webhook吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const response = await deleteWebhook(id)
    if (response.success) {
      ElMessage.success('删除成功')
      fetchWebhooks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

onMounted(() => {
  fetchWebhooks()
})
</script>

<style scoped>
.form-tip {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

/* 修复表单项间距，避免重叠 */
:deep(.el-form-item) {
  margin-bottom: var(--space-5);
}

:deep(.el-form-item__label) {
  line-height: 32px;
  padding-bottom: var(--space-2);
}

:deep(.el-form-item__content) {
  line-height: 32px;
}

/* 确保输入框有足够的边距 */
:deep(.el-input),
:deep(.el-textarea),
:deep(.el-select) {
  width: 100%;
}

/* 修复checkbox-group间距 */
:deep(.el-checkbox-group) {
  line-height: 32px;
}

:deep(.el-checkbox) {
  margin-right: var(--space-5);
  margin-bottom: var(--space-2);
}

/* 修复radio-group间距 */
:deep(.el-radio-group) {
  line-height: 32px;
}

:deep(.el-radio) {
  margin-right: var(--space-5);
}
</style>
