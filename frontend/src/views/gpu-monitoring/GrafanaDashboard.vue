<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          Grafana监控仪表盘
        </div>
        <div class="page-subtitle">直接接入现有 GPU 集群 Grafana 仪表盘，支持页面内预览与新标签打开</div>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">访问方式</div>
      </div>
      <div class="content-card-body action-body">
        <div class="action-card">
          <div class="action-title">打开链接地址</div>
          <div class="action-desc">使用 Grafana 原始地址在新标签页打开，适合需要完整原生功能时使用。</div>
          <el-button class="action-button" @click="openGrafanaUrl" :disabled="!grafanaUrl">
            <el-icon><TopRight /></el-icon>
            打开链接地址
          </el-button>
        </div>
        <div class="action-card">
          <div class="action-title">打开 Grafana</div>
          <div class="action-desc">使用项目内代理地址打开，可与当前系统页面内嵌展示保持一致。</div>
          <el-button type="primary" class="action-button" @click="openGrafana" :disabled="!grafanaProxyUrl">
            <el-icon><Monitor /></el-icon>
            打开 Grafana
          </el-button>
        </div>
      </div>
    </div>

    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">仪表盘预览</div>
        <div class="content-card-extra">
          <el-tag type="info">若被 Grafana 安全策略拦截，请使用“打开 Grafana”按钮</el-tag>
        </div>
      </div>
      <div class="content-card-body dashboard-body">
        <iframe v-if="grafanaProxyUrl" :src="grafanaProxyUrl" class="grafana-frame" frameborder="0" />
        <el-empty v-else description="暂无可预览的仪表盘地址" :image-size="140" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor, TopRight } from '@element-plus/icons-vue'
import { getGrafanaInfo } from '@/api/gpuMonitoring'

const grafanaUrl = ref('')
const grafanaProxyUrl = ref('')

const fetchGrafanaInfo = async () => {
  try {
    const response = await getGrafanaInfo()
    if (!response.success) {
      throw new Error(response.error || response.message || '获取失败')
    }
    grafanaUrl.value = response.data.url || ''
    grafanaProxyUrl.value = response.data.proxy_url || ''
  } catch (error) {
    ElMessage.error(error.message || '获取 Grafana 地址失败')
  }
}

const openGrafana = () => {
  if (grafanaProxyUrl.value) {
    window.open(grafanaProxyUrl.value, '_blank', 'noopener,noreferrer')
  }
}

const openGrafanaUrl = () => {
  if (grafanaUrl.value) {
    window.open(grafanaUrl.value, '_blank', 'noopener,noreferrer')
  }
}

onMounted(fetchGrafanaInfo)
</script>

<style scoped>
.dashboard-body {
  padding: 0;
}

.action-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.action-card {
  padding: var(--space-4);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
}

.action-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.action-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.7;
}

.action-button {
  margin-top: auto;
}

.grafana-frame {
  width: 100%;
  min-height: 760px;
  border: none;
  background: #fff;
}

@media (max-width: 900px) {
  .action-body {
    grid-template-columns: 1fr;
  }
}
</style>
