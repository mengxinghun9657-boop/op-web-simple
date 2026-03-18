<script setup>
import { useRouter } from 'vue-router'
import { Monitor, Connection, Coin, Folder, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()

const modules = [
  {
    title: 'EIP带宽分析',
    desc: '弹性IP入向/出向带宽监控与丢包统计',
    icon: 'Connection',
    path: '/monitoring/eip',
    variant: 'primary'
  },
  {
    title: 'BOS存储分析',
    desc: '对象存储空间使用量、文件数及TOP排名',
    icon: 'Coin',
    path: '/monitoring/bos',
    variant: 'success'
  },
  {
    title: 'BCC实例分析',
    desc: '云服务器CPU、内存使用率深度监控',
    icon: 'Monitor',
    path: '/monitoring/bcc',
    variant: 'info'
  },
  {
    title: 'PFS监控分析',
    desc: '并行文件系统容量、吞吐、QPS、延迟监控',
    icon: 'Folder',
    path: '/monitoring/pfs',
    variant: 'warning'
  }
]

const navigateTo = (path) => router.push(path)
</script>

<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          监控数据分析中心
        </div>
        <div class="page-subtitle">EIP带宽 · BOS存储 · BCC实例 · PFS文件系统监控</div>
      </div>
    </div>

    <!-- 监控模块卡片 -->
    <div class="monitoring-modules">
      <div
        v-for="mod in modules"
        :key="mod.path"
        class="content-card module-card"
        @click="navigateTo(mod.path)"
      >
        <div class="content-card-header">
          <div class="content-card-title">
            <el-icon><component :is="mod.icon" /></el-icon>
            {{ mod.title }}
          </div>
          <div class="content-card-extra">
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>
        <div class="content-card-body">
          <p class="module-desc">{{ mod.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-modules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-6);
}

.module-card {
  cursor: pointer;
  transition: box-shadow var(--duration-normal) var(--ease-standard),
              border-color var(--duration-normal) var(--ease-standard);
}

.module-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}

.arrow-icon {
  color: var(--text-tertiary);
  transition: color var(--duration-fast) var(--ease-standard);
}

.module-card:hover .arrow-icon {
  color: var(--primary);
}

.module-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 768px) {
  .monitoring-modules {
    grid-template-columns: 1fr;
  }
}
</style>
