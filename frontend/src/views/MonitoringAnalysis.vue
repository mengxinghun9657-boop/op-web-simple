<script setup>
import { useRouter } from 'vue-router'
import { Monitor, Connection, Coin, ArrowRight } from '@element-plus/icons-vue'
import { Card } from '@/components/common'

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
  }
]

const navigateTo = (path) => router.push(path)
</script>

<template>
  <div class="monitoring-analysis-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-icon">
        <el-icon :size="24"><Monitor /></el-icon>
      </div>
      <div class="page-header-content">
        <h2 class="page-title">监控数据分析中心</h2>
        <p class="page-subtitle">EIP带宽 · BOS存储 · BCC实例监控</p>
      </div>
    </div>

    <!-- 监控模块卡片 -->
    <div class="monitoring-modules">
      <Card
        v-for="mod in modules"
        :key="mod.path"
        :title="mod.title"
        :icon="mod.icon"
        class="module-card animate-slide-in-up"
        @click="navigateTo(mod.path)"
      >
        <template #header>
          <el-icon class="arrow-icon">
            <ArrowRight />
          </el-icon>
        </template>
        <p class="module-desc">{{ mod.desc }}</p>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.monitoring-analysis-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
  animation: slideInUp var(--duration-slow) var(--ease-out);
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-secondary-500));
  border-radius: var(--radius-lg);
  color: white;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0;
}

.monitoring-modules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-6);
}

.module-card {
  cursor: pointer;
  transition: all var(--transition-normal);
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.arrow-icon {
  color: var(--text-tertiary);
  transition: all var(--transition-fast);
}

.module-card:hover .arrow-icon {
  color: var(--color-primary);
  transform: translateX(4px);
}

.module-desc {
  font-size: var(--font-size-sm);
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
