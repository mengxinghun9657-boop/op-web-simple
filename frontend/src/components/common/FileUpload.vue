<template>
  <div class="file-upload-wrapper">
    <input 
      type="file" 
      ref="inputRef" 
      class="hidden" 
      :accept="accept" 
      @change="handleChange" 
    />
    
    <!-- 文件选择区域 -->
    <div v-if="!selectedFile" class="upload-area" @click="$refs.inputRef.click()">
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <p class="upload-text">点击选择文件或拖拽文件到此处</p>
      <p class="upload-hint">支持 {{ accept }} 格式，最大 {{ Math.round(maxSize / 1024 / 1024) }}MB</p>
    </div>
    
    <!-- 已选择文件显示 -->
    <div v-else class="file-selected">
      <div class="file-info">
        <el-icon class="file-icon"><Document /></el-icon>
        <div class="file-details">
          <p class="file-name">{{ selectedFile.name }}</p>
          <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
        </div>
      </div>
      <el-button 
        type="danger" 
        size="small" 
        :icon="Delete" 
        circle 
        @click="clearFile"
      />
    </div>
    
    <!-- 重新选择按钮 -->
    <el-button 
      v-if="selectedFile"
      type="primary" 
      plain
      size="small"
      @click="$refs.inputRef.click()"
      style="margin-top: 10px;"
    >
      <el-icon><RefreshRight /></el-icon>
      重新选择
    </el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, Delete, RefreshRight } from '@element-plus/icons-vue'

const props = defineProps({
  accept: {
    type: String,
    default: '.xlsx,.xls'
  },
  buttonText: {
    type: String,
    default: '选择文件'
  },
  buttonType: {
    type: String,
    default: 'primary'
  },
  maxSize: {
    type: Number,
    default: 50 * 1024 * 1024 // 50MB
  }
})

const emit = defineEmits(['file-selected'])
const inputRef = ref(null)
const selectedFile = ref(null)

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const validate = (file) => {
  // 根据accept提取扩展名
  const extensions = props.accept.split(',').map(ext => ext.trim().replace('.', ''))
  const fileExt = file.name.split('.').pop().toLowerCase()
  
  if (!extensions.includes(fileExt)) {
    const acceptStr = extensions.join(', ')
    ElMessage.error(`仅支持 ${acceptStr} 格式的文件`)
    return false
  }
  
  if (file.size > props.maxSize) {
    ElMessage.error(`文件大小不能超过 ${Math.round(props.maxSize / 1024 / 1024)}MB`)
    return false
  }
  
  return true
}

const handleFile = (file) => {
  if (file && validate(file)) {
    selectedFile.value = file
    emit('file-selected', file)
    ElMessage.success(`已选择文件: ${file.name}`)
  }
}

const handleChange = (e) => {
  if (e.target.files && e.target.files[0]) {
    handleFile(e.target.files[0])
  }
}

const clearFile = () => {
  selectedFile.value = null
  inputRef.value.value = ''
  emit('file-selected', null)
  ElMessage.info('已清除文件')
}
</script>

<style scoped>
.file-upload-wrapper {
  width: 100%;
}

.hidden {
  display: none;
}

.upload-area {
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--el-fill-color-blank);
}

.upload-area:hover {
  border-color: var(--el-color-primary);
  background: var(--el-fill-color-light);
}

.upload-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 16px;
}

.upload-text {
  font-size: var(--text-lg);
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.upload-hint {
  font-size: var(--text-base);
  color: var(--el-text-color-secondary);
}

.file-selected {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.file-icon {
  font-size: 32px;
  color: var(--el-color-primary);
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--el-text-color-primary);
  margin: 0 0 4px 0;
  word-break: break-all;
}

.file-size {
  font-size: var(--text-sm);
  color: var(--el-text-color-secondary);
  margin: 0;
}
</style>