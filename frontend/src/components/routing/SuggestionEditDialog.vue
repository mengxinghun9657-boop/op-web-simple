<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="编辑规则建议"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      v-loading="loading"
    >
      <el-form-item label="查询模式" prop="pattern">
        <el-input
          v-model="form.pattern"
          placeholder="请输入查询模式"
          :rows="2"
          type="textarea"
        />
      </el-form-item>

      <el-form-item label="意图类型" prop="intent_type">
        <el-select v-model="form.intent_type" placeholder="请选择意图类型" style="width: 100%">
          <el-option label="SQL查询" value="sql" />
          <el-option label="报告查询" value="rag_report" />
          <el-option label="知识查询" value="rag_knowledge" />
          <el-option label="对话" value="chat" />
        </el-select>
      </el-form-item>

      <el-form-item label="优先级" prop="priority">
        <el-input-number
          v-model="form.priority"
          :min="1"
          :max="100"
          placeholder="1-100"
          style="width: 100%"
        />
        <div class="form-tip">优先级越高，规则匹配优先级越高（1-100）</div>
      </el-form-item>

      <el-form-item label="元数据" prop="metadata">
        <el-input
          v-model="metadataText"
          type="textarea"
          :rows="8"
          placeholder='请输入JSON格式的元数据，例如：
{
  "recommended_tables": ["iaas_servers"],
  "recommended_database": "cmdb"
}'
          @blur="validateMetadata"
        />
        <div class="form-tip">
          元数据用于优化SQL生成，支持推荐表、数据库等配置
        </div>
        <el-alert
          v-if="metadataError"
          :title="metadataError"
          type="error"
          :closable="false"
          style="margin-top: 8px"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue'
import { updateSuggestion } from '@/api/routing'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  suggestion: Object
})

const emit = defineEmits(['update:modelValue', 'success'])

const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const metadataText = ref('')
const metadataError = ref('')

const form = reactive({
  pattern: '',
  intent_type: '',
  priority: 50,
  metadata: null
})

const rules = {
  pattern: [
    { required: true, message: '请输入查询模式', trigger: 'blur' }
  ],
  intent_type: [
    { required: true, message: '请选择意图类型', trigger: 'change' }
  ],
  priority: [
    { required: true, message: '请输入优先级', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '优先级范围为1-100', trigger: 'blur' }
  ]
}

// 验证元数据JSON
const validateMetadata = () => {
  metadataError.value = ''
  
  if (!metadataText.value.trim()) {
    form.metadata = null
    return true
  }
  
  try {
    form.metadata = JSON.parse(metadataText.value)
    return true
  } catch (error) {
    metadataError.value = 'JSON格式错误: ' + error.message
    return false
  }
}

// 初始化表单
const initForm = () => {
  if (!props.suggestion) return
  
  form.pattern = props.suggestion.pattern || ''
  form.intent_type = props.suggestion.suggested_intent || ''
  form.priority = props.suggestion.priority || 50
  
  // 处理metadata
  if (props.suggestion.metadata) {
    if (typeof props.suggestion.metadata === 'string') {
      metadataText.value = props.suggestion.metadata
      try {
        form.metadata = JSON.parse(props.suggestion.metadata)
      } catch {
        form.metadata = null
      }
    } else {
      form.metadata = props.suggestion.metadata
      metadataText.value = JSON.stringify(props.suggestion.metadata, null, 2)
    }
  } else {
    metadataText.value = ''
    form.metadata = null
  }
  
  metadataError.value = ''
}

watch(() => props.modelValue, (visible) => {
  if (visible) {
    nextTick(() => {
      initForm()
      formRef.value?.clearValidate()
    })
  }
})

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  // 验证表单
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  // 验证元数据
  if (!validateMetadata()) return
  
  submitting.value = true
  try {
    const data = {
      pattern: form.pattern,
      intent_type: form.intent_type,
      priority: form.priority,
      metadata: form.metadata
    }
    
    const response = await updateSuggestion(props.suggestion.id, data)
    
    if (response.success) {
      ElMessage.success('更新成功')
      emit('update:modelValue', false)
      emit('success')
    } else {
      ElMessage.error(response.message || '更新失败')
    }
  } catch (error) {
    console.error('更新建议失败:', error)
    ElMessage.error('更新失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}
</style>
