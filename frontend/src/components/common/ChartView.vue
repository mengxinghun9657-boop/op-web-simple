<template>
  <div ref="chartDom" :style="{ width: '100%', height: height }"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  options: Object,
  height: { type: String, default: '400px' }
})

const chartDom = ref(null)
let chartInstance = null

const init = () => {
  if(chartDom.value) {
    chartInstance = echarts.init(chartDom.value)
    if(props.options) chartInstance.setOption(props.options)
  }
}

watch(() => props.options, (newVal) => {
  chartInstance?.setOption(newVal)
}, { deep: true })

onMounted(() => {
  init()
  window.addEventListener('resize', () => chartInstance?.resize())
})

onUnmounted(() => {
  window.removeEventListener('resize', () => chartInstance?.resize())
  chartInstance?.dispose()
})
</script>