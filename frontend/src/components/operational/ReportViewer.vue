<template>
  <div class="w-full h-full bg-white rounded-lg overflow-hidden relative group">
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-gray-50 z-10">
      <el-icon class="is-loading text-primary" :size="30"><Loading /></el-icon>
    </div>
    
    <iframe 
      :src="src" 
      class="w-full h-full border-none"
      @load="loading = false"
    ></iframe>
    
    <div class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
      <el-button type="primary" circle icon="FullScreen" @click="openNewTab" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ src: String })
const loading = ref(true)

const openNewTab = () => {
  if(props.src) window.open(props.src, '_blank')
}
</script>