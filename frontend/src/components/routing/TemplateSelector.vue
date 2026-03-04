<template>
  <div class="template-selector">
    <!-- 搜索和过滤 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索模板..."
        clearable
        @input="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select
        v-model="selectedCategory"
        placeholder="选择分类"
        clearable
        @change="handleCategoryChange"
        style="width: 200px; margin-left: 10px;"
      >
        <el-option label="全部分类" value="" />
        <el-option label="IP查询" value="ip_query" />
        <el-option label="实例ID查询" value="instance_query" />
        <el-option label="统计查询" value="statistics_query" />
        <el-option label="报告查询" value="report_query" />
        <el-option label="知识查询" value="knowledge_query" />
        <el-option label="其他" value="other" />
      </el-select>
    </div>

    <!-- 模板列表 -->
    <div class="template-list" v-loading="loading">
      <el-empty v-if="filteredTemplates.length === 0" description="暂无模板" />
      
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        class="template-item"
        :class="{ 'selected': selectedTemplate?.id === template.id }"
        @click="selectTemplate(template)"
      >
        <div class="template-header">
          <span class="template-name">{{ template.name }}</span>
          <el-tag :type="getCategoryType(template.category)" size="small">
            {{ getCategoryLabel(template.category) }}
          </el-tag>
        </div>
        
        <div class="template-description">
          {{ template.description }}
        </div>
        
        <div class="template-footer">
          <el-tag size="small" effect="plain">
            {{ getIntentTypeLabel(template.intent_type) }}
          </el-tag>
          <span class="template-priority">优先级: {{ template.priority }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button @click="handlePreview" :disabled="!selectedTemplate">
        预览模板
      </el-button>
      <el-button type="primary" @click="handleApply" :disabled="!selectedTemplate">
        应用模板
      </el-button>
      <el-button @click="handleSaveCustom">
        保存为自定义模板
      </el-button>
    </div>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="模板预览"
      width="600px"
    >
      <div v-if="selectedTemplate" class="template-preview">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="模板名称">
            {{ selectedTemplate.name }}
          </el-descriptions-item>
          <el-descriptions-item label="分类">
            {{ getCategoryLabel(selectedTemplate.category) }}
          </el-descriptions-item>
          <el-descriptions-item label="描述">
            {{ selectedTemplate.description }}
          </el-descriptions-item>
          <el-descriptions-item label="匹配模式">
            <code>{{ selectedTemplate.pattern }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="意图类型">
            {{ getIntentTypeLabel(selectedTemplate.intent_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            {{ selectedTemplate.priority }}
          </el-descriptions-item>
          <el-descriptions-item label="推荐表" v-if="selectedTemplate.metadata?.recommended_tables">
            {{ selectedTemplate.metadata.recommended_tables.join(', ') }}
          </el-descriptions-item>
          <el-descriptions-item label="关键词" v-if="selectedTemplate.metadata?.keywords">
            {{ selectedTemplate.metadata.keywords.join(', ') }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleApplyFromPreview">
          应用此模板
        </el-button>
      </template>
    </el-dialog>

    <!-- 保存自定义模板对话框 -->
    <el-dialog
      v-model="saveDialogVisible"
      title="保存为自定义模板"
      width="500px"
    >
      <el-form :model="customTemplate" label-width="100px">
        <el-form-item label="模板名称" required>
          <el-input v-model="customTemplate.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="customTemplate.category" placeholder="选择分类">
            <el-option label="IP查询" value="ip_query" />
            <el-option label="实例ID查询" value="instance_query" />
            <el-option label="统计查询" value="statistics_query" />
            <el-option label="报告查询" value="report_query" />
            <el-option label="知识查询" value="knowledge_query" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="customTemplate.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfirm">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getTemplates } from '@/api/routing-assistant'

const props = defineProps({
  currentRule: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['apply-template', 'save-custom'])

// 数据
const templates = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const selectedCategory = ref('')
const selectedTemplate = ref(null)
const previewDialogVisible = ref(false)
const saveDialogVisible = ref(false)
const customTemplate = ref({
  name: '',
  category: '',
  description: ''
})

// 计算属性
const filteredTemplates = computed(() => {
  let result = templates.value

  // 分类过滤
  if (selectedCategory.value) {
    result = result.filter(t => t.category === selectedCategory.value)
  }

  // 关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(keyword) ||
      t.description.toLowerCase().includes(keyword) ||
      t.pattern.toLowerCase().includes(keyword)
    )
  }

  return result
})

// 方法
const loadTemplates = async () => {
  loading.value = true
  try {
    const response = await getTemplates()
    if (response.success) {
      templates.value = response.data || []
    } else {
      ElMessage.error(response.message || '加载模板失败')
    }
  } catch (error) {
    console.error('加载模板失败:', error)
    ElMessage.error('加载模板失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  // 搜索已通过 computed 实现
}

const handleCategoryChange = () => {
  // 过滤已通过 computed 实现
}

const selectTemplate = (template) => {
  selectedTemplate.value = template
}

const handlePreview = () => {
  if (!selectedTemplate.value) {
    ElMessage.warning('请先选择一个模板')
    return
  }
  previewDialogVisible.value = true
}

const handleApply = () => {
  if (!selectedTemplate.value) {
    ElMessage.warning('请先选择一个模板')
    return
  }
  
  emit('apply-template', selectedTemplate.value)
  ElMessage.success('模板已应用')
}

const handleApplyFromPreview = () => {
  handleApply()
  previewDialogVisible.value = false
}

const handleSaveCustom = () => {
  if (!props.currentRule.pattern) {
    ElMessage.warning('请先创建规则内容')
    return
  }
  
  customTemplate.value = {
    name: '',
    category: props.currentRule.intent_type || '',
    description: ''
  }
  saveDialogVisible.value = true
}

const handleSaveConfirm = () => {
  if (!customTemplate.value.name) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (!customTemplate.value.category) {
    ElMessage.warning('请选择分类')
    return
  }
  
  const templateData = {
    ...customTemplate.value,
    pattern: props.currentRule.pattern,
    intent_type: props.currentRule.intent_type,
    priority: props.currentRule.priority || 50,
    metadata: {
      recommended_tables: props.currentRule.recommended_tables || [],
      keywords: props.currentRule.keywords || []
    }
  }
  
  emit('save-custom', templateData)
  saveDialogVisible.value = false
  ElMessage.success('自定义模板已保存')
}

const getCategoryType = (category) => {
  const typeMap = {
    ip_query: 'primary',
    instance_query: 'success',
    statistics_query: 'warning',
    report_query: 'danger',
    knowledge_query: 'info',
    other: ''
  }
  return typeMap[category] || ''
}

const getCategoryLabel = (category) => {
  const labelMap = {
    ip_query: 'IP查询',
    instance_query: '实例ID查询',
    statistics_query: '统计查询',
    report_query: '报告查询',
    knowledge_query: '知识查询',
    other: '其他'
  }
  return labelMap[category] || category
}

const getIntentTypeLabel = (intentType) => {
  const labelMap = {
    sql: 'SQL查询',
    rag_knowledge: '知识库检索',
    rag_report: '报告检索',
    chat: '普通对话'
  }
  return labelMap[intentType] || intentType
}

// 生命周期
onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.template-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.search-bar {
  display: flex;
  margin-bottom: 16px;
}

.template-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
  max-height: 400px;
}

.template-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.template-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.template-item.selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.template-name {
  font-weight: 600;
  font-size: 14px;
}

.template-description {
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
  line-height: 1.5;
}

.template-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-priority {
  font-size: 12px;
  color: #909399;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.template-preview code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}
</style>
