import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    // 代码分割优化
    rollupOptions: {
      output: {
        manualChunks: {
          // Vue 核心
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Element Plus 单独打包
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          // 图表库单独打包
          'echarts': ['echarts'],
          // 工具库
          'utils': ['axios', 'marked', 'nprogress']
        }
      }
    },
    // 压缩优化
    minify: 'esbuild',
    // 关闭 CSS 代码分割（减少请求）
    cssCodeSplit: false,
    // 资源内联阈值
    assetsInlineLimit: 4096,
    // 块大小警告阈值
    chunkSizeWarningLimit: 1000
  },
  // CSS 优化
  css: {
    devSourcemap: false
  },
  // 依赖预构建优化
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'element-plus',
      '@element-plus/icons-vue',
      'axios',
      'echarts'
    ]
  }
})
