<template>
  <div class="query-builder">
    <el-form label-width="100px" class="builder-form">
      <!-- 时间范围 -->
      <DateRangePicker v-model="localIql" @update:modelValue="handleIqlUpdate" />
      
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="负责人">
            <el-select
              v-model="conditions.responsiblePeople"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入负责人（回车添加）"
              @change="handleConditionChange"
            >
              <el-option
                v-for="person in cachedPeople"
                :key="person"
                :label="person"
                :value="person"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label="流程状态">
            <el-select
              v-model="conditions.status"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入状态（回车添加）"
              @change="handleConditionChange"
            >
              <el-option
                v-for="status in commonStatuses"
                :key="status"
                :label="status"
                :value="status"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="类型">
            <el-select
              v-model="conditions.type"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入类型（回车添加）"
              @change="handleConditionChange"
            >
              <el-option
                v-for="type in commonTypes"
                :key="type"
                :label="type"
                :value="type"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label="标签">
            <el-select
              v-model="conditions.labels"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入标签（回车添加）"
              @change="handleConditionChange"
            >
              <el-option
                v-for="label in commonLabels"
                :key="label"
                :label="label"
                :value="label"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="所属计划">
            <el-select
              v-model="conditions.plan"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入计划（回车添加）"
              @change="handleConditionChange"
            >
              <el-option
                v-for="plan in cachedPlans"
                :key="plan"
                :label="plan"
                :value="plan"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="12">
          <el-form-item label=" ">
            <el-button @click="clearConditions">清空所有条件</el-button>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { generateFieldCondition } from '@/utils/iqlGenerator'
import DateRangePicker from './DateRangePicker.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

// 时间条件（由 DateRangePicker 维护，单独存储）
const timeIql = ref('')

// 给 DateRangePicker 的 v-model：始终只传时间部分，避免字段条件污染
const localIql = ref('')

// 查询条件
const conditions = ref({
  responsiblePeople: [],
  status: [],
  type: [],
  labels: [],
  plan: []
})

// localStorage 缓存键名
const STORAGE_KEYS = {
  responsiblePeople: 'query_builder_responsible_people',
  plans: 'query_builder_plans'
}

const MAX_CACHE_ITEMS = 5

// 缓存的用户输入历史
const cachedPeople = ref([])
const cachedPlans = ref([])

// 固定选项（不需要缓存）
const commonStatuses = ref(['新建', '开发中', '待开发', '进行中', '已完成', '已关闭'])
const commonTypes = ref(['Bug', 'Epic', 'Story', 'Task'])
const commonLabels = ref(['紧急', '重要', '优化', '新功能'])

/**
 * 从 localStorage 加载缓存
 */
const loadCache = () => {
  try {
    const peopleCache = localStorage.getItem(STORAGE_KEYS.responsiblePeople)
    if (peopleCache) {
      cachedPeople.value = JSON.parse(peopleCache)
    }
    
    const plansCache = localStorage.getItem(STORAGE_KEYS.plans)
    if (plansCache) {
      cachedPlans.value = JSON.parse(plansCache)
    }
  } catch (error) {
    console.warn('加载查询构建器缓存失败:', error)
  }
}

/**
 * 保存缓存到 localStorage
 */
const saveCache = (key, values) => {
  try {
    localStorage.setItem(key, JSON.stringify(values))
  } catch (error) {
    console.warn('保存查询构建器缓存失败:', error)
  }
}

/**
 * 添加新值到缓存（去重、限制数量）
 */
const addToCache = (cacheRef, storageKey, newValue) => {
  if (!newValue || typeof newValue !== 'string') return
  
  // 去重：移除已存在的
  const filtered = cacheRef.value.filter(item => item !== newValue)
  
  // 添加到开头
  filtered.unshift(newValue)
  
  // 限制最大数量
  if (filtered.length > MAX_CACHE_ITEMS) {
    filtered.splice(MAX_CACHE_ITEMS)
  }
  
  cacheRef.value = filtered
  saveCache(storageKey, filtered)
}

/**
 * 监听负责人变化，缓存新输入
 */
watch(() => conditions.value.responsiblePeople, (newValues, oldValues) => {
  if (!oldValues) return
  
  // 找出新添加的值
  const added = newValues.filter(v => !oldValues.includes(v))
  added.forEach(value => {
    addToCache(cachedPeople, STORAGE_KEYS.responsiblePeople, value)
  })
}, { deep: true })

/**
 * 监听所属计划变化，缓存新输入
 */
watch(() => conditions.value.plan, (newValues, oldValues) => {
  if (!oldValues) return
  
  // 找出新添加的值
  const added = newValues.filter(v => !oldValues.includes(v))
  added.forEach(value => {
    addToCache(cachedPlans, STORAGE_KEYS.plans, value)
  })
}, { deep: true })

// 生成字段条件的IQL
const generateFieldsIql = () => {
  const parts = []

  if (conditions.value.responsiblePeople.length > 0) {
    parts.push(generateFieldCondition('负责人', conditions.value.responsiblePeople))
  }

  if (conditions.value.status.length > 0) {
    parts.push(generateFieldCondition('流程状态', conditions.value.status))
  }

  if (conditions.value.type.length > 0) {
    parts.push(generateFieldCondition('类型', conditions.value.type))
  }

  if (conditions.value.labels.length > 0) {
    parts.push(generateFieldCondition('测试『Label』标签', conditions.value.labels))
  }

  if (conditions.value.plan.length > 0) {
    parts.push(generateFieldCondition('所属计划', conditions.value.plan))
  }

  return parts.join(' AND ')
}

// 处理条件变化（不 emit，等待"应用"按钮）
const handleConditionChange = () => {
  // 仅做本地状态更新，不 emit
}

// 暴露给父组件调用，手动将当前条件 emit 出去
const applyConditions = () => {
  updateIql()
}

// 更新IQL并 emit
const updateIql = () => {
  const fieldsIql = generateFieldsIql()
  const parts = []
  if (timeIql.value) parts.push(timeIql.value)
  if (fieldsIql) parts.push(fieldsIql)
  const newIql = parts.join(' AND ')
  emit('update:modelValue', newIql)
}

// DateRangePicker 更新时，只保存时间部分
const handleIqlUpdate = (newIql) => {
  // newIql 是 DateRangePicker 基于 localIql（纯时间）合并后的结果
  // 提取时间条件部分
  const timePattern = /(最后修改时间|创建时间|完成时间)\s*[><]=?\s*"[^"]+"/g
  const matches = newIql.match(timePattern)
  timeIql.value = matches ? matches.join(' AND ') : ''
  localIql.value = timeIql.value
}

const clearConditions = () => {
  conditions.value = {
    responsiblePeople: [],
    status: [],
    type: [],
    labels: [],
    plan: []
  }
  // 清空后立即更新IQL（只保留时间条件）
  updateIql()
}

// 监听外部变化（如 IQLEditor 手动编辑、历史记录加载）
// 只提取时间条件部分同步给 DateRangePicker，字段条件由 conditions 管理
watch(() => props.modelValue, (newVal) => {
  const timePattern = /(最后修改时间|创建时间|完成时间)\s*[><]=?\s*"[^"]+"/g
  const matches = (newVal || '').match(timePattern)
  const extractedTime = matches ? matches.join(' AND ') : ''
  if (extractedTime !== timeIql.value) {
    timeIql.value = extractedTime
    localIql.value = extractedTime
  }
})

// 初始化时加载缓存
onMounted(() => {
  loadCache()
})

defineExpose({ applyConditions })
</script>

<style scoped>
.query-builder {
  width: 100%;
}

.builder-form {
  margin-bottom: 0;
}

.builder-form :deep(.el-select) {
  width: 100%;
}

.builder-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.builder-form :deep(.el-select__wrapper) {
  transition: all var(--transition-fast);
}

.builder-form :deep(.el-select__wrapper:hover) {
  border-color: var(--color-primary-400);
}

.builder-form :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

@media (max-width: 768px) {
  .builder-form :deep(.el-row) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  
  .builder-form :deep(.el-col) {
    padding-left: 0 !important;
    padding-right: 0 !important;
    width: 100%;
  }
}
</style>
