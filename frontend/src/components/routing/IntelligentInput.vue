<template>
  <div class="intelligent-input">
    <!-- 模式切换 -->
    <div class="mode-switch mb-4">
      <el-radio-group v-model="currentMode" @change="handleModeChange">
        <el-radio-button label="natural">自然语言</el-radio-button>
        <el-radio-button label="regex">正则表达式</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 自然语言输入模式 -->
    <div v-if="currentMode === 'natural'" class="natural-mode">
      <el-input
        v-model="naturalLanguageInput"
        type="textarea"
        :rows="3"
        placeholder="请用自然语言描述匹配规则，例如：查询包含IP地址的内容"
        @input="handleNaturalLanguageInput"
      />
      
      <div class="mt-2 flex justify-between items-center">
        <el-button 
          type="primary" 
          :loading="converting"
          :disabled="!naturalLanguageInput.trim()"
          @click="handleConvert"
        >
          <i class="el-icon-magic-stick mr-1"></i>
          转换为正则表达式
        </el-button>
        
        <span v-if="convertResult" class="text-sm text-gray-500">
          置信度: {{ (convertResult.confidence * 100).toFixed(0) }}%
        </span>
      </div>

      <!-- 转换结果 -->
      <div v-if="convertResult" class="convert-result mt-4 p-4 bg-gray-50 rounded">
        <div class="mb-2">
          <span class="font-medium">生成的正则表达式：</span>
          <el-input 
            v-model="convertResult.regex" 
            readonly
            class="mt-1"
          >
            <template #append>
              <el-button @click="copyToClipboard(convertResult.regex)">
                <i class="el-icon-document-copy"></i>
              </el-button>
            </template>
          </el-input>
        </div>
        
        <div class="mb-2">
          <span class="font-medium">解释：</span>
          <p class="text-sm text-gray-600 mt-1">{{ convertResult.explanation }}</p>
        </div>
        
        <div>
          <span class="font-medium">匹配示例：</span>
          <ul class="text-sm text-gray-600 mt-1 list-disc list-inside">
            <li v-for="(example, index) in convertResult.examples" :key="index">
              {{ example }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 正则表达式输入模式 -->
    <div v-else class="regex-mode">
      <el-input
        v-model="regexInput"
        type="textarea"
        :rows="3"
        placeholder="请输入正则表达式，例如：\b(?:\d{1,3}\.){3}\d{1,3}\b"
        @input="handleRegexInput"
      />
      
      <div class="mt-2 text-sm text-gray-500">
        <i class="el-icon-info"></i>
        提示：输入正则表达式后会自动进行语法验证
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { convertNaturalLanguage } from '@/api/routing-assistant'
import { debounceCancelable } from '@/utils/debounce'

export default {
  name: 'IntelligentInput',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    mode: {
      type: String,
      default: 'natural',
      validator: (value) => ['natural', 'regex'].includes(value)
    },
    intentType: {
      type: String,
      required: true
    }
  },
  emits: ['update:modelValue', 'update:mode', 'convert', 'validate'],
  setup(props, { emit }) {
    const currentMode = ref(props.mode)
    const naturalLanguageInput = ref('')
    const regexInput = ref(props.modelValue)
    const converting = ref(false)
    const convertResult = ref(null)
    
    // 使用可取消的防抖函数进行验证（500ms）
    const debouncedValidate = debounceCancelable((value) => {
      if (value.trim()) {
        emit('validate', value)
      }
    }, 500)

    // 监听外部值变化
    watch(() => props.modelValue, (newValue) => {
      if (currentMode.value === 'regex') {
        regexInput.value = newValue
      }
    })

    // 模式切换
    const handleModeChange = (mode) => {
      emit('update:mode', mode)
      
      // 切换到正则模式时，如果有转换结果，使用转换的正则
      if (mode === 'regex' && convertResult.value) {
        regexInput.value = convertResult.value.regex
        emit('update:modelValue', convertResult.value.regex)
      }
    }

    // 自然语言输入
    const handleNaturalLanguageInput = () => {
      // 清除之前的转换结果
      convertResult.value = null
    }

    // 转换自然语言
    const handleConvert = async () => {
      if (!naturalLanguageInput.value.trim()) {
        ElMessage.warning('请输入自然语言描述')
        return
      }

      converting.value = true
      
      try {
        const response = await convertNaturalLanguage(
          naturalLanguageInput.value,
          props.intentType
        )
        
        if (response.success) {
          convertResult.value = response.data
          emit('convert', response.data)
          ElMessage.success('转换成功')
        } else {
          ElMessage.error(response.message || '转换失败')
        }
      } catch (error) {
        console.error('转换失败:', error)
        ElMessage.error('转换失败，请稍后重试')
      } finally {
        converting.value = false
      }
    }

    // 正则表达式输入（带防抖）
    const handleRegexInput = () => {
      emit('update:modelValue', regexInput.value)
      debouncedValidate(regexInput.value)
    }

    // 复制到剪贴板
    const copyToClipboard = (text) => {
      navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('已复制到剪贴板')
      }).catch(() => {
        ElMessage.error('复制失败')
      })
    }

    // 清理
    onUnmounted(() => {
      debouncedValidate.cancel()
    })

    return {
      currentMode,
      naturalLanguageInput,
      regexInput,
      converting,
      convertResult,
      handleModeChange,
      handleNaturalLanguageInput,
      handleConvert,
      handleRegexInput,
      copyToClipboard
    }
  }
}
</script>

<style scoped>
.intelligent-input {
  width: 100%;
}

.mode-switch {
  display: flex;
  justify-content: flex-start;
}

.convert-result {
  border: 1px solid #e5e7eb;
}
</style>
