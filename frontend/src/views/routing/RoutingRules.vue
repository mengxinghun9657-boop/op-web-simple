<template>
  <div class="routing-rules-page">
    <div class="page-header">
      <h1>路由规则管理</h1>
      <p class="subtitle">管理意图路由规则，优化查询路由准确率</p>
    </div>

    <div class="content-container">
      <!-- 操作栏 -->
      <div class="action-bar">
        <div class="filters">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索规则模式..."
            clearable
            class="filter-input"
            @keyup.enter="loadRules"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select
            v-model="filters.intentType"
            placeholder="筛选意图类型"
            clearable
            class="filter-select"
            @change="loadRules"
          >
            <el-option label="SQL查询" value="sql" />
            <el-option label="报告查询" value="rag_report" />
            <el-option label="知识查询" value="rag_knowledge" />
            <el-option label="对话" value="chat" />
          </el-select>

          <el-select
            v-model="filters.isActive"
            placeholder="筛选状态"
            clearable
            class="filter-select-small"
            @change="loadRules"
          >
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </div>

        <div class="actions">
          <el-button type="primary" @click="showCreateDialog" class="action-btn">
            <el-icon><Plus /></el-icon>
            <span class="btn-text">创建规则</span>
          </el-button>
          <el-button type="success" @click="handleGenerateSuggestions" :loading="generating" class="action-btn">
            <el-icon><MagicStick /></el-icon>
            <span class="btn-text">生成建议</span>
          </el-button>
          <el-button @click="showTestDialog" class="action-btn">
            <el-icon><Operation /></el-icon>
            <span class="btn-text">测试规则</span>
          </el-button>
          <el-button @click="handleExport" class="action-btn">
            <el-icon><Download /></el-icon>
            <span class="btn-text">导出</span>
          </el-button>
          <el-button @click="showImportDialog" class="action-btn">
            <el-icon><Upload /></el-icon>
            <span class="btn-text">导入</span>
          </el-button>
          <el-button @click="loadRules" class="action-btn">
            <el-icon><Refresh /></el-icon>
            <span class="btn-text md:hidden">刷新</span>
          </el-button>
        </div>
      </div>

      <!-- 规则列表 -->
      <div class="table-container">
        <el-table
          v-loading="loading"
          :data="rules"
          class="rules-table"
        >
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="pattern" label="匹配模式" min-width="200">
          <template #default="{ row }">
            <div class="pattern-cell">
              <el-tag size="small" :type="getIntentTagType(row.intent_type)">
                {{ getIntentLabel(row.intent_type) }}
              </el-tag>
              <span class="pattern-text">{{ row.pattern }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="priority" label="优先级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="handleToggleActive(row)"
            />
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadRules"
          @current-change="loadRules"
        />
      </div>
    </div>

    <!-- 创建/编辑规则对话框 -->
    <el-dialog
      v-model="ruleDialogVisible"
      :title="isEditMode ? '编辑规则' : '创建规则'"
      width="1200px"
      :close-on-click-modal="false"
      :aria-modal="true"
      :aria-labelledby="isEditMode ? 'edit-rule-dialog-title' : 'create-rule-dialog-title'"
      role="dialog"
      @close="handleDialogClose"
    >
      <!-- 教程按钮 -->
      <div v-if="!isEditMode" class="tutorial-trigger">
        <el-button
          size="small"
          type="info"
          @click="restartTutorial"
          title="查看教程 (F1)"
          aria-label="查看交互式教程"
        >
          <el-icon><QuestionFilled /></el-icon>
          查看教程
        </el-button>
      </div>

      <!-- 键盘快捷键提示 -->
      <div class="keyboard-shortcuts-hint" role="status" aria-live="polite">
        <el-text size="small" type="info">
          快捷键: Ctrl+1-6 切换标签 | Ctrl+Enter 保存 | Esc 关闭
        </el-text>
      </div>

      <!-- 交互式教程 -->
      <InteractiveTutorial
        v-if="showTutorial"
        :visible="showTutorial"
        @complete="handleTutorialComplete"
        @skip="handleTutorialSkip"
      />

      <!-- 模板选择器 -->
      <div v-if="!isEditMode && showTemplateSelector" class="template-section">
        <TemplateSelector
          :current-rule="ruleForm"
          @apply-template="handleApplyTemplate"
          @save-custom="handleSaveCustomTemplate"
        />
        <el-divider />
      </div>

      <!-- 切换模板选择器按钮 -->
      <div v-if="!isEditMode" class="template-toggle">
        <el-button
          size="small"
          @click="showTemplateSelector = !showTemplateSelector"
          :aria-expanded="showTemplateSelector"
          aria-controls="template-selector-section"
          aria-label="切换模板选择器显示"
        >
          <el-icon><Collection /></el-icon>
          {{ showTemplateSelector ? '隐藏模板' : '显示模板' }}
        </el-button>
      </div>

      <!-- 标签页 -->
      <el-tabs 
        v-model="activeTab" 
        class="rule-tabs"
        role="tablist"
        aria-label="规则创建步骤"
      >
        <!-- 基本信息标签页 -->
        <el-tab-pane 
          label="基本信息" 
          name="basic"
          role="tabpanel"
          aria-labelledby="tab-basic"
        >
          <el-form
            ref="ruleFormRef"
            :model="ruleForm"
            :rules="ruleFormRules"
            label-width="100px"
          >
            <!-- 智能输入组件 -->
            <el-form-item label="匹配模式" prop="pattern">
              <IntelligentInput
                v-model:pattern="ruleForm.pattern"
                v-model:mode="inputMode"
                :intent-type="ruleForm.intent_type"
                @converted="handleConverted"
                @validated="handleValidated"
              />
            </el-form-item>

        <el-form-item label="意图类型" prop="intent_type">
          <el-select 
            v-model="ruleForm.intent_type" 
            placeholder="选择意图类型" 
            style="width: 100%"
            aria-label="选择路由意图类型"
            aria-describedby="intent-type-help"
          >
            <el-option label="SQL查询" value="sql">
              <div class="option-with-desc">
                <span>SQL查询</span>
                <span class="option-desc">数据库查询、统计信息</span>
              </div>
            </el-option>
            <el-option label="报告查询" value="rag_report">
              <div class="option-with-desc">
                <span>报告查询</span>
                <span class="option-desc">查找历史报告</span>
              </div>
            </el-option>
            <el-option label="知识查询" value="rag_knowledge">
              <div class="option-with-desc">
                <span>知识查询</span>
                <span class="option-desc">操作指南、概念说明</span>
              </div>
            </el-option>
            <el-option label="对话" value="chat">
              <div class="option-with-desc">
                <span>对话</span>
                <span class="option-desc">问候、闲聊</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-input-number
            v-model="ruleForm.priority"
            :min="1"
            :max="100"
            style="width: 100%"
            aria-label="设置规则优先级"
            aria-describedby="priority-help priority-example"
          />
          <div id="priority-help" class="field-help">
            <el-icon class="help-icon"><QuestionFilled /></el-icon>
            <span>范围 1-100，数值越大优先级越高</span>
          </div>
          <div id="priority-example" class="field-example">
            建议：强制规则 90-100，业务规则 50-89，通用规则 1-49
          </div>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="ruleForm.description"
            type="textarea"
            :rows="3"
            placeholder="规则描述（可选）"
            aria-label="输入规则描述"
          />
        </el-form-item>

        <el-form-item label="元数据" prop="metadata">
          <!-- 简化模式：表选择器 -->
          <div class="metadata-editor">
            <el-radio-group v-model="metadataMode" class="metadata-mode-selector">
              <el-radio-button label="simple">简化模式</el-radio-button>
              <el-radio-button label="advanced">高级模式</el-radio-button>
            </el-radio-group>

            <!-- 简化模式：表选择器 -->
            <div v-if="metadataMode === 'simple'" class="simple-metadata">
              <div class="metadata-field">
                <label>推荐表（可选）</label>
                <el-select
                  v-model="simpleMetadata.tableHints"
                  multiple
                  filterable
                  placeholder="选择推荐的数据库表"
                  style="width: 100%"
                  @focus="loadAvailableTables"
                >
                  <el-option
                    v-for="table in availableTables"
                    :key="table.name"
                    :label="`${table.name} - ${table.comment || '无描述'}`"
                    :value="table.name"
                  >
                    <div class="table-option">
                      <span class="table-name">{{ table.name }}</span>
                      <span class="table-comment">{{ table.comment || '无描述' }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div class="field-help">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  <span>为SQL查询推荐优先使用的表</span>
                </div>
              </div>

              <div class="metadata-field">
                <label>关键词（可选）</label>
                <el-select
                  v-model="simpleMetadata.keywords"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="输入关键词，按回车添加"
                  style="width: 100%"
                >
                </el-select>
                <div class="field-help">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  <span>辅助匹配的关键词列表</span>
                </div>
              </div>
            </div>

            <!-- 高级模式：JSON编辑器 -->
            <div v-else class="advanced-metadata">
              <el-input
                v-model="metadataText"
                type="textarea"
                :rows="6"
                placeholder='JSON格式的元数据（可选）'
              />
              <div class="field-help">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
                <span>JSON 格式的额外配置信息</span>
              </div>
              <div class="field-example">
                示例：<code>{"table_hints": ["iaas_servers"], "keywords": ["物理机", "虚拟机"]}</code>
              </div>
              <div v-if="metadataError" class="form-error">{{ metadataError }}</div>
            </div>
          </div>
        </el-form-item>
      </el-form>
        </el-tab-pane>

        <!-- 验证标签页 -->
        <el-tab-pane 
          label="验证" 
          name="validation"
          role="tabpanel"
          aria-labelledby="tab-validation"
        >
          <ValidationPanel
            v-if="validationResult"
            :validation-result="validationResult"
            aria-label="规则验证结果"
          />
          <el-empty 
            v-else 
            description="请先在基本信息中输入匹配模式"
            role="status"
          />
        </el-tab-pane>

        <!-- 测试标签页 -->
        <el-tab-pane 
          label="测试" 
          name="test"
          role="tabpanel"
          aria-labelledby="tab-test"
        >
          <TestMatchPanel
            v-if="ruleForm.pattern"
            :pattern="ruleForm.pattern"
            aria-label="规则匹配测试"
          />
          <el-empty 
            v-else 
            description="请先在基本信息中输入匹配模式"
            role="status"
          />
        </el-tab-pane>

        <!-- 智能辅助标签页 -->
        <el-tab-pane 
          label="智能辅助" 
          name="assistant"
          role="tabpanel"
          aria-labelledby="tab-assistant"
        >
          <AssistantPanel
            v-if="ruleForm.pattern && ruleForm.intent_type"
            :pattern="ruleForm.pattern"
            :intent-type="ruleForm.intent_type"
            :current-description="ruleForm.description"
            :current-keywords="simpleMetadata.keywords"
            :current-tables="simpleMetadata.tableHints"
            :current-priority="ruleForm.priority"
            @update:description="ruleForm.description = $event"
            @update:keywords="simpleMetadata.keywords = $event"
            @update:tables="simpleMetadata.tableHints = $event"
            @update:priority="ruleForm.priority = $event"
            aria-label="智能辅助工具"
          />
          <el-empty 
            v-else 
            description="请先在基本信息中输入匹配模式和意图类型"
            role="status"
          />
        </el-tab-pane>

        <!-- 可视化标签页 -->
        <el-tab-pane 
          label="可视化" 
          name="visualizer"
          role="tabpanel"
          aria-labelledby="tab-visualizer"
        >
          <RegexVisualizer
            v-if="ruleForm.pattern && inputMode === 'regex'"
            :pattern="ruleForm.pattern"
            aria-label="正则表达式可视化"
          />
          <el-empty 
            v-else 
            description="仅支持正则表达式模式的可视化"
            role="status"
          />
        </el-tab-pane>

        <!-- 预览标签页 -->
        <el-tab-pane 
          label="预览" 
          name="preview"
          role="tabpanel"
          aria-labelledby="tab-preview"
        >
          <RulePreview
            :rule-data="{
              pattern: ruleForm.pattern,
              intent_type: ruleForm.intent_type,
              priority: ruleForm.priority,
              description: ruleForm.description,
              metadata: ruleForm.metadata,
              mode: inputMode,
              conversion_result: conversionResult,
              validation_result: validationResult
            }"
            @back-to-edit="activeTab = 'basic'"
            aria-label="规则预览"
          />
        </el-tab-pane>
      </el-tabs>

      <!-- 草稿管理 -->
      <DraftManager
        v-if="!isEditMode"
        :current-data="{
          pattern: ruleForm.pattern,
          intent_type: ruleForm.intent_type,
          priority: ruleForm.priority,
          description: ruleForm.description,
          metadata: ruleForm.metadata,
          mode: inputMode
        }"
        @restore="handleRestoreDraft"
      />

      <template #footer>
        <el-button 
          @click="ruleDialogVisible = false"
          aria-label="取消并关闭对话框"
        >
          取消
        </el-button>
        <el-button 
          type="primary" 
          :loading="saving" 
          @click="handleSaveRule"
          :aria-busy="saving"
          aria-label="保存规则"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试规则对话框 -->
    <el-dialog
      v-model="testDialogVisible"
      title="测试路由规则"
      width="900px"
      :close-on-click-modal="false"
    >
      <div class="test-section">
        <el-input
          v-model="testQueries"
          type="textarea"
          :rows="6"
          placeholder="输入测试查询，每行一个"
        />
        <el-button
          type="primary"
          :loading="testing"
          @click="handleTest"
          style="margin-top: 12px"
        >
          开始测试
        </el-button>

        <div v-if="testResults" class="test-results" style="margin-top: 20px">
          <h3>测试结果</h3>
          <div
            v-for="(result, index) in testResults"
            :key="index"
            class="test-result-item"
          >
            <div class="query-text">{{ result.query }}</div>
            <div class="result-comparison">
              <div class="result-column">
                <div class="column-label">无规则</div>
                <el-tag>{{ result.without_rule.intent }}</el-tag>
                <span>{{ (result.without_rule.confidence * 100).toFixed(1) }}%</span>
              </div>
              <el-icon class="arrow"><Right /></el-icon>
              <div class="result-column">
                <div class="column-label">有规则</div>
                <el-tag type="success">{{ result.with_rule.intent }}</el-tag>
                <span>{{ (result.with_rule.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入路由规则"
      width="500px"
    >
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".json"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">只支持 JSON 格式文件</div>
        </template>
      </el-upload>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Operation, Download, Upload, Refresh, Right, UploadFilled, QuestionFilled, MagicStick, Collection
} from '@element-plus/icons-vue'
import {
  getRoutingRules,
  createRoutingRule,
  updateRoutingRule,
  deleteRoutingRule,
  testRoutingRules,
  exportRoutingRules,
  importRoutingRules,
  generateRuleSuggestions
} from '@/api/routing'
import IntelligentInput from '@/components/routing/IntelligentInput.vue'
import ValidationPanel from '@/components/routing/ValidationPanel.vue'
import TestMatchPanel from '@/components/routing/TestMatchPanel.vue'
import AssistantPanel from '@/components/routing/AssistantPanel.vue'
import TemplateSelector from '@/components/routing/TemplateSelector.vue'
import RegexVisualizer from '@/components/routing/RegexVisualizer.vue'
import RulePreview from '@/components/routing/RulePreview.vue'
import ContextHelp from '@/components/routing/ContextHelp.vue'
import DraftManager from '@/components/routing/DraftManager.vue'
import InteractiveTutorial from '@/components/routing/InteractiveTutorial.vue'

// 状态
const loading = ref(false)
const rules = ref([])
const ruleDialogVisible = ref(false)
const testDialogVisible = ref(false)
const importDialogVisible = ref(false)
const isEditMode = ref(false)
const saving = ref(false)
const testing = ref(false)
const importing = ref(false)
const generating = ref(false)

// 教程相关
const showTutorial = ref(false)
const TUTORIAL_COMPLETED_KEY = 'routing_rule_tutorial_completed'

// 标签页和模板
const activeTab = ref('basic')
const showTemplateSelector = ref(false)

// 智能输入模式
const inputMode = ref('natural') // 'natural' 或 'regex'

// 验证和转换结果
const validationResult = ref(null)
const conversionResult = ref(null)

// 键盘导航
const handleKeyDown = (event) => {
  // Escape键关闭对话框
  if (event.key === 'Escape' && ruleDialogVisible.value) {
    event.preventDefault()
    handleDialogClose()
    return
  }
  
  // Ctrl/Cmd + Enter 保存
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && ruleDialogVisible.value) {
    event.preventDefault()
    handleSaveRule()
    return
  }
  
  // Ctrl/Cmd + 数字键切换标签页
  if ((event.ctrlKey || event.metaKey) && event.key >= '1' && event.key <= '6') {
    event.preventDefault()
    const tabs = ['basic', 'validation', 'test', 'assistant', 'visualizer', 'preview']
    const index = parseInt(event.key) - 1
    if (index < tabs.length) {
      activeTab.value = tabs[index]
    }
    return
  }
}

// 筛选
const filters = reactive({
  keyword: '',
  intentType: '',
  isActive: null
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 规则表单
const ruleFormRef = ref(null)
const ruleForm = reactive({
  id: null,
  pattern: '',
  intent_type: '',
  priority: 50,
  description: '',
  metadata: null
})

const metadataText = ref('')
const metadataError = ref('')

// 元数据编辑模式
const metadataMode = ref('simple') // 'simple' 或 'advanced'
const availableTables = ref([])
const simpleMetadata = reactive({
  tableHints: [],
  keywords: []
})

const ruleFormRules = {
  pattern: [{ required: true, message: '请输入匹配模式', trigger: 'blur' }],
  intent_type: [{ required: true, message: '请选择意图类型', trigger: 'change' }],
  priority: [
    { required: true, message: '请输入优先级', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '优先级范围：1-100', trigger: 'blur' }
  ]
}

// 测试
const testQueries = ref('')
const testResults = ref(null)

// 导入
const importFile = ref(null)

// 监听元数据文本变化（高级模式）
watch(metadataText, (newVal) => {
  if (metadataMode.value !== 'advanced') return
  
  if (!newVal.trim()) {
    metadataError.value = ''
    ruleForm.metadata = null
    return
  }

  try {
    ruleForm.metadata = JSON.parse(newVal)
    metadataError.value = ''
  } catch (error) {
    metadataError.value = 'JSON 格式错误'
  }
})

// 监听简化模式的元数据变化
watch(() => [simpleMetadata.tableHints, simpleMetadata.keywords], () => {
  if (metadataMode.value !== 'simple') return
  
  const metadata = {}
  if (simpleMetadata.tableHints.length > 0) {
    metadata.table_hints = simpleMetadata.tableHints
  }
  if (simpleMetadata.keywords.length > 0) {
    metadata.keywords = simpleMetadata.keywords
  }
  
  ruleForm.metadata = Object.keys(metadata).length > 0 ? metadata : null
  metadataText.value = ruleForm.metadata ? JSON.stringify(ruleForm.metadata, null, 2) : ''
}, { deep: true })

// 加载可用表列表
const loadAvailableTables = async () => {
  if (availableTables.value.length > 0) return // 已加载
  
  try {
    const response = await fetch('/api/v1/ai/tables', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    const data = await response.json()
    
    if (data.success && data.data) {
      availableTables.value = data.data.map(table => ({
        name: table.table_name,
        comment: table.comment || table.table_comment || ''
      }))
    }
  } catch (error) {
    console.error('加载表列表失败:', error)
  }
}

// 加载规则列表
const loadRules = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: filters.keyword || undefined,
      intent_type: filters.intentType || undefined,
      is_active: filters.isActive !== null ? filters.isActive : undefined
    }

    const response = await getRoutingRules(params)

    if (response.success) {
      rules.value = response.data.list
      pagination.total = response.data.total
    } else {
      ElMessage.error(response.message || '加载失败')
    }
  } catch (error) {
    console.error('加载规则列表失败:', error)
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  isEditMode.value = false
  resetRuleForm()
  ruleDialogVisible.value = true
  
  // 检查是否首次使用
  checkFirstTimeUse()
}

// 检查首次使用
const checkFirstTimeUse = () => {
  const completed = localStorage.getItem(TUTORIAL_COMPLETED_KEY)
  if (!completed) {
    // 延迟显示教程，让对话框先完全打开
    setTimeout(() => {
      showTutorial.value = true
    }, 500)
  }
}

// 重新查看教程
const restartTutorial = () => {
  showTutorial.value = true
}

// 教程完成处理
const handleTutorialComplete = () => {
  localStorage.setItem(TUTORIAL_COMPLETED_KEY, 'true')
  showTutorial.value = false
  ElMessage.success('教程已完成！现在可以开始创建规则了')
}

// 跳过教程
const handleTutorialSkip = () => {
  showTutorial.value = false
}

// 显示编辑对话框
const showEditDialog = (rule) => {
  isEditMode.value = true
  ruleForm.id = rule.id
  ruleForm.pattern = rule.pattern
  ruleForm.intent_type = rule.intent_type
  ruleForm.priority = rule.priority
  ruleForm.description = rule.description || ''
  ruleForm.metadata = rule.metadata
  metadataText.value = rule.metadata ? JSON.stringify(rule.metadata, null, 2) : ''
  
  // 解析元数据到简化模式
  if (rule.metadata) {
    simpleMetadata.tableHints = rule.metadata.table_hints || []
    simpleMetadata.keywords = rule.metadata.keywords || []
    // 如果元数据只包含 table_hints 和 keywords，使用简化模式
    const keys = Object.keys(rule.metadata)
    const isSimple = keys.every(k => ['table_hints', 'keywords'].includes(k))
    metadataMode.value = isSimple ? 'simple' : 'advanced'
  } else {
    metadataMode.value = 'simple'
    simpleMetadata.tableHints = []
    simpleMetadata.keywords = []
  }
  
  ruleDialogVisible.value = true
}

// 重置表单
const resetRuleForm = () => {
  ruleForm.id = null
  ruleForm.pattern = ''
  ruleForm.intent_type = ''
  ruleForm.priority = 50
  ruleForm.description = ''
  ruleForm.metadata = null
  metadataText.value = ''
  metadataError.value = ''
  metadataMode.value = 'simple'
  simpleMetadata.tableHints = []
  simpleMetadata.keywords = []
  activeTab.value = 'basic'
  inputMode.value = 'natural'
  validationResult.value = null
  conversionResult.value = null
  ruleFormRef.value?.clearValidate()
}

// 处理转换结果
const handleConverted = (result) => {
  conversionResult.value = result
  if (result.regex) {
    ruleForm.pattern = result.regex
  }
}

// 处理验证结果
const handleValidated = (result) => {
  validationResult.value = result
}

// 应用模板
const handleApplyTemplate = (template) => {
  ruleForm.pattern = template.pattern
  ruleForm.intent_type = template.intent_type
  ruleForm.priority = template.priority
  ruleForm.description = template.description || ''
  
  if (template.metadata) {
    ruleForm.metadata = template.metadata
    metadataText.value = JSON.stringify(template.metadata, null, 2)
    
    // 解析到简化模式
    simpleMetadata.tableHints = template.metadata.table_hints || []
    simpleMetadata.keywords = template.metadata.keywords || []
  }
  
  ElMessage.success('模板已应用')
}

// 保存自定义模板
const handleSaveCustomTemplate = async (templateData) => {
  // TODO: 调用API保存自定义模板
  ElMessage.success('自定义模板已保存')
}

// 对话框关闭处理
const handleDialogClose = () => {
  // 如果有未保存的内容，提示用户
  if (ruleForm.pattern || ruleForm.description) {
    ElMessageBox.confirm(
      '有未保存的内容，确认关闭？',
      '提示',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      ruleDialogVisible.value = false
      showTutorial.value = false
    }).catch(() => {
      // 用户取消关闭
    })
  } else {
    ruleDialogVisible.value = false
    showTutorial.value = false
  }
}

// 快速填充示例
const fillExample = (type) => {
  const examples = {
    ip: {
      pattern: '/\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/',
      intent_type: 'sql',
      priority: 95,
      description: 'IP 地址查询规则 - 自动识别 IP 地址并路由到 SQL 查询',
      metadata: {
        table_hints: ['iaas_servers', 'iaas_instances', 'mydb.bce_cce_nodes'],
        keywords: ['IP', '地址', '集群', '节点']
      }
    },
    instance: {
      pattern: '/i-[a-zA-Z0-9]{8,}/',
      intent_type: 'sql',
      priority: 90,
      description: '实例 ID 查询规则 - 自动识别实例 ID 并路由到 SQL 查询',
      metadata: {
        table_hints: ['iaas_instances', 'mydb.bce_bcc_instances'],
        keywords: ['实例', 'instance']
      }
    },
    stats: {
      pattern: '统计,汇总,总数,数量,分布',
      intent_type: 'sql',
      priority: 60,
      description: '统计查询规则 - 识别统计类查询并路由到 SQL 查询',
      metadata: {
        query_type: 'aggregation',
        keywords: ['统计', '汇总', '总数', '数量']
      }
    },
    report: {
      pattern: '报告,报表,分析结果,监控结果',
      intent_type: 'rag_report',
      priority: 70,
      description: '报告检索规则 - 识别报告查询并路由到报告检索',
      metadata: {
        report_types: ['operational', 'resource', 'monitoring'],
        keywords: ['报告', '报表', '分析']
      }
    }
  }

  const example = examples[type]
  if (example) {
    ruleForm.pattern = example.pattern
    ruleForm.intent_type = example.intent_type
    ruleForm.priority = example.priority
    ruleForm.description = example.description
    ruleForm.metadata = example.metadata
    metadataText.value = JSON.stringify(example.metadata, null, 2)
    ElMessage.success('已填充示例数据')
  }
}

// 保存规则
const handleSaveRule = async () => {
  console.log('🔍 handleSaveRule 开始执行')
  console.log('🔍 metadataError:', metadataError.value)
  console.log('🔍 ruleForm:', JSON.stringify(ruleForm, null, 2))
  
  if (metadataError.value) {
    ElMessage.warning('请修正元数据格式错误')
    return
  }

  try {
    console.log('🔍 开始表单验证...')
    await ruleFormRef.value.validate()
    console.log('✅ 表单验证通过')
  } catch (error) {
    console.error('❌ 表单验证失败:', error)
    ElMessage.error('请检查表单填写是否完整')
    return
  }

  saving.value = true
  try {
    const data = {
      pattern: ruleForm.pattern,
      intent_type: ruleForm.intent_type,
      priority: ruleForm.priority,
      description: ruleForm.description || undefined,
      metadata: ruleForm.metadata
    }

    console.log('🔍 准备发送请求:', JSON.stringify(data, null, 2))
    console.log('🔍 isEditMode:', isEditMode.value)

    const response = isEditMode.value
      ? await updateRoutingRule(ruleForm.id, data)
      : await createRoutingRule(data)

    console.log('🔍 收到响应:', response)

    if (response.success) {
      ElMessage.success(isEditMode.value ? '更新成功' : '创建成功')
      ruleDialogVisible.value = false
      loadRules()
    } else {
      console.error('❌ 保存失败:', response.message)
      ElMessage.error(response.message || '保存失败')
    }
  } catch (error) {
    console.error('❌ 保存规则失败:', error)
    console.error('❌ error.response:', error.response)
    console.error('❌ error.response?.data:', error.response?.data)
    ElMessage.error(error.response?.data?.message || error.message || '保存失败')
  } finally {
    saving.value = false
    console.log('🔍 handleSaveRule 执行完成')
  }
}

// 切换启用状态
const handleToggleActive = async (rule) => {
  try {
    const response = await updateRoutingRule(rule.id, {
      is_active: rule.is_active
    })

    if (response.success) {
      ElMessage.success(rule.is_active ? '已启用' : '已禁用')
    } else {
      rule.is_active = !rule.is_active
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    rule.is_active = !rule.is_active
    console.error('切换状态失败:', error)
    ElMessage.error('操作失败')
  }
}

// 删除规则
const handleDelete = async (rule) => {
  try {
    await ElMessageBox.confirm(
      `确认删除规则"${rule.pattern}"？删除后将从向量索引中移除。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await deleteRoutingRule(rule.id)

    if (response.success) {
      ElMessage.success('删除成功')
      loadRules()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除规则失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 显示测试对话框
const showTestDialog = () => {
  testQueries.value = ''
  testResults.value = null
  testDialogVisible.value = true
}

// 测试规则
const handleTest = async () => {
  const queries = testQueries.value
    .split('\n')
    .map(q => q.trim())
    .filter(q => q.length > 0)

  if (queries.length === 0) {
    ElMessage.warning('请输入至少一个测试查询')
    return
  }

  testing.value = true
  try {
    const response = await testRoutingRules({ queries })

    if (response.success) {
      testResults.value = response.data.results
      ElMessage.success('测试完成')
    } else {
      ElMessage.error(response.message || '测试失败')
    }
  } catch (error) {
    console.error('测试失败:', error)
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

// 导出规则
const handleExport = async () => {
  try {
    const response = await exportRoutingRules()
    
    // 创建下载链接
    const blob = new Blob([JSON.stringify(response.data, null, 2)], {
      type: 'application/json'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `routing_rules_${new Date().getTime()}.json`
    link.click()
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 显示导入对话框
const showImportDialog = () => {
  importFile.value = null
  importDialogVisible.value = true
}

// 文件变化
const handleFileChange = (file) => {
  importFile.value = file.raw
}

// 导入规则
const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  importing.value = true
  try {
    const response = await importRoutingRules(importFile.value)

    if (response.success) {
      ElMessage.success(
        `导入完成：成功 ${response.data.imported_count} 条，跳过 ${response.data.skipped_count} 条`
      )
      importDialogVisible.value = false
      loadRules()
    } else {
      ElMessage.error(response.message || '导入失败')
    }
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

// 生成规则建议
const handleGenerateSuggestions = async () => {
  try {
    await ElMessageBox.confirm(
      '将基于用户反馈数据自动生成规则建议。对于错误次数 >= 3 次的查询模式，系统会生成规则建议供审核。',
      '生成规则建议',
      {
        confirmButtonText: '开始生成',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    generating.value = true
    try {
      const response = await generateRuleSuggestions({ min_support_count: 3 })

      if (response.success) {
        const count = response.data.generated_count
        if (count > 0) {
          ElMessageBox.confirm(
            `成功生成 ${count} 个规则建议。是否前往规则建议审核页面查看？`,
            '生成成功',
            {
              confirmButtonText: '前往审核',
              cancelButtonText: '稍后查看',
              type: 'success'
            }
          ).then(() => {
            // 跳转到规则建议审核页面
            window.location.href = '/#/routing/suggestions/review'
          }).catch(() => {
            // 用户选择稍后查看
          })
        } else {
          ElMessage.info('当前没有符合条件的反馈数据，无法生成规则建议')
        }
      } else {
        ElMessage.error(response.message || '生成失败')
      }
    } catch (error) {
      console.error('生成规则建议失败:', error)
      ElMessage.error(error.response?.data?.message || error.message || '生成失败')
    } finally {
      generating.value = false
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('生成规则建议失败:', error)
    }
  }
}

// 工具函数
const getIntentLabel = (intent) => {
  const labels = {
    sql: 'SQL查询',
    rag_report: '报告查询',
    rag_knowledge: '知识查询',
    chat: '对话'
  }
  return labels[intent] || intent
}

const getIntentTagType = (intent) => {
  const types = {
    sql: 'success',
    rag_report: 'warning',
    rag_knowledge: 'info',
    chat: ''
  }
  return types[intent] || ''
}

const getPriorityType = (priority) => {
  if (priority >= 80) return 'danger'
  if (priority >= 50) return 'warning'
  return 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 恢复草稿
const handleRestoreDraft = (draftData) => {
  ruleForm.pattern = draftData.pattern || ''
  ruleForm.intent_type = draftData.intent_type || ''
  ruleForm.priority = draftData.priority || 50
  ruleForm.description = draftData.description || ''
  ruleForm.metadata = draftData.metadata || null
  inputMode.value = draftData.mode || 'natural'
  
  if (draftData.metadata) {
    metadataText.value = JSON.stringify(draftData.metadata, null, 2)
    simpleMetadata.tableHints = draftData.metadata.table_hints || []
    simpleMetadata.keywords = draftData.metadata.keywords || []
  }
  
  ElMessage.success('草稿已恢复')
}

// 初始化
onMounted(() => {
  loadRules()
  
  // 添加全局键盘事件监听
  window.addEventListener('keydown', handleKeyDown)
})

// 清理
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.routing-rules-page {
  padding: 16px;
  min-height: 100vh;
}

@media (min-width: 768px) {
  .routing-rules-page {
    padding: 20px;
  }
}

@media (min-width: 1024px) {
  .routing-rules-page {
    padding: 24px;
  }
}

.page-header {
  margin-bottom: 20px;
}

@media (min-width: 768px) {
  .page-header {
    margin-bottom: 24px;
  }
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

@media (min-width: 768px) {
  .page-header h1 {
    font-size: 24px;
  }
}

.subtitle {
  color: #606266; /* 提高对比度，原来是 #475569 */
  font-size: 13px;
}

@media (min-width: 768px) {
  .subtitle {
    font-size: 14px;
  }
}

.content-container {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

@media (min-width: 768px) {
  .content-container {
    padding: 20px;
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding: 24px;
  }
}

.action-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

@media (min-width: 768px) {
  .action-bar {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

@media (min-width: 640px) {
  .filters {
    flex-direction: row;
    flex-wrap: wrap;
  }
}

@media (min-width: 768px) {
  .filters {
    width: auto;
  }
}

.filter-input {
  width: 100%;
}

@media (min-width: 640px) {
  .filter-input {
    width: 240px;
  }
}

@media (min-width: 1024px) {
  .filter-input {
    width: 300px;
  }
}

.filter-select {
  width: 100%;
}

@media (min-width: 640px) {
  .filter-select {
    width: 160px;
  }
}

@media (min-width: 1024px) {
  .filter-select {
    width: 180px;
  }
}

.filter-select-small {
  width: 100%;
}

@media (min-width: 640px) {
  .filter-select-small {
    width: 130px;
  }
}

@media (min-width: 1024px) {
  .filter-select-small {
    width: 150px;
  }
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (min-width: 768px) {
  .actions {
    gap: 12px;
  }
}

.action-btn {
  min-height: 44px;
  flex: 1;
  min-width: 0;
}

@media (min-width: 640px) {
  .action-btn {
    flex: 0 1 auto;
  }
}

.btn-text {
  margin-left: 4px;
}

@media (max-width: 639px) {
  .btn-text {
    display: none;
  }
  
  .action-btn :deep(.el-icon) {
    margin-right: 0;
  }
}

.table-container {
  overflow-x: auto;
  margin-bottom: 16px;
  -webkit-overflow-scrolling: touch;
}

@media (min-width: 768px) {
  .table-container {
    margin-bottom: 20px;
  }
}

.rules-table {
  min-width: 800px;
}

.pattern-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pattern-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pagination {
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  font-size: 12px;
  color: #606266; /* 提高对比度 */
  margin-top: 4px;
}

.form-error {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
  font-weight: 500; /* 增加字重以提高可读性 */
}

/* 快速填充区域 */
.quick-fill-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.quick-fill-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 字段帮助提示 */
.field-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266; /* 提高对比度，原来是 #909399 */
  margin-top: 4px;
}

.help-icon {
  color: #409eff;
  font-size: 14px;
}

.field-example {
  font-size: 12px;
  color: #303133; /* 提高对比度，原来是 #606266 */
  margin-top: 4px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid #409eff; /* 添加视觉提示 */
}

.field-example code {
  padding: 2px 6px;
  background: #e4e7ed;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: #303133; /* 提高对比度 */
}

/* 选项描述 */
.option-with-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.option-desc {
  font-size: 12px;
  color: #606266; /* 提高对比度，原来是 #909399 */
}

.test-section {
  padding: 12px;
}

.test-results {
  margin-top: 20px;
}

.test-result-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.query-text {
  font-weight: 500;
  margin-bottom: 8px;
}

.result-comparison {
  display: flex;
  align-items: center;
  gap: 16px;
}

.result-column {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-label {
  font-size: 12px;
  color: #606266; /* 提高对比度 */
  font-weight: 500; /* 增加字重 */
}

.arrow {
  font-size: 20px;
  color: #409eff;
}

/* 元数据编辑器 */
.metadata-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metadata-mode-selector {
  margin-bottom: 8px;
}

.simple-metadata {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metadata-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metadata-field label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.table-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.table-name {
  font-weight: 500;
  color: #303133;
}

.table-comment {
  font-size: 12px;
  color: #606266; /* 提高对比度 */
  margin-left: 8px;
}

.advanced-metadata {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 教程触发按钮 */
.tutorial-trigger {
  position: absolute;
  top: 16px;
  right: 60px;
  z-index: 10;
}

/* 键盘快捷键提示 */
.keyboard-shortcuts-hint {
  position: absolute;
  bottom: 16px;
  left: 24px;
  z-index: 10;
  opacity: 0.7;
}

.keyboard-shortcuts-hint:hover {
  opacity: 1;
}

/* 可访问性：状态指示器（不仅依赖颜色） */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.status-indicator::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
}

/* 错误状态 */
.status-error {
  color: #f56c6c;
}

.status-error::before {
  background-color: #f56c6c;
}

/* 警告状态 */
.status-warning {
  color: #e6a23c;
}

.status-warning::before {
  background-color: #e6a23c;
}

/* 成功状态 */
.status-success {
  color: #67c23a;
}

.status-success::before {
  background-color: #67c23a;
}

/* 信息状态 */
.status-info {
  color: #409eff;
}

.status-info::before {
  background-color: #409eff;
}

/* 模板部分 */
.template-section {
  margin-bottom: 20px;
}

.template-toggle {
  margin-bottom: 16px;
}

/* 标签页 */
.rule-tabs {
  margin-top: 16px;
}
</style>
