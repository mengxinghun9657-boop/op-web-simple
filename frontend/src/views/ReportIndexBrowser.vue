<template>
  <div class="report-browser-page">
    <div class="page-header">
      <h1>📄 报告索引浏览</h1>
      <p class="subtitle">浏览和查看历史分析报告</p>
    </div>

    <div class="browser-container">
      <!-- 过滤器区域 -->
      <div class="filter-section">
        <div class="filter-group">
          <label>报告类型</label>
          <select v-model="filters.reportType" @change="loadReports">
            <option value="">全部类型</option>
            <option value="resource_analysis">资源分析</option>
            <option value="bcc_monitoring">BCC 监控</option>
            <option value="bos_monitoring">BOS 监控</option>
            <option value="operational_analysis">运营分析</option>
          </select>
        </div>

        <div class="filter-group">
          <label>时间范围</label>
          <div class="date-range">
            <input
              v-model="filters.startDate"
              type="date"
              @change="loadReports"
            />
            <span>至</span>
            <input
              v-model="filters.endDate"
              type="date"
              @change="loadReports"
            />
          </div>
        </div>

        <div class="filter-group">
          <label>向量化状态</label>
          <select v-model="filters.vectorized" @change="loadReports">
            <option value="">全部</option>
            <option value="true">已向量化</option>
            <option value="false">未向量化</option>
          </select>
        </div>

        <button class="btn-secondary" @click="resetFilters">
          🔄 重置筛选
        </button>
      </div>

      <!-- 统计信息 -->
      <div v-if="stats" class="stats-section">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总报告数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.vectorized }}</div>
          <div class="stat-label">已向量化</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">待向量化</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.rate }}</div>
          <div class="stat-label">向量化率</div>
        </div>
      </div>

      <!-- 报告列表 -->
      <div class="reports-section">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="reports.length === 0" class="empty-state">
          <p>📭 暂无报告</p>
          <p class="hint">尝试调整筛选条件</p>
        </div>

        <div v-else class="reports-grid">
          <div
            v-for="report in reports"
            :key="report.task_id"
            class="report-card"
            :class="{ 'vectorized': report.vectorized }"
          >
            <div class="report-header">
              <div class="report-type-badge" :class="`type-${report.report_type}`">
                {{ getReportTypeLabel(report.report_type) }}
              </div>
              <div class="report-status">
                <span v-if="report.vectorized" class="status-badge vectorized">
                  ✓ 已向量化
                </span>
                <span v-else class="status-badge pending">
                  ⏳ 待向量化
                </span>
              </div>
            </div>

            <div class="report-content">
              <h3 class="report-title">{{ report.task_id }}</h3>
              <p class="report-summary">{{ report.summary }}</p>
              <div class="report-meta">
                <span class="meta-item">
                  📅 {{ formatDate(report.generated_at) }}
                </span>
                <span class="meta-item">
                  📁 {{ report.file_path.split('/').pop() }}
                </span>
              </div>
            </div>

            <div class="report-actions">
              <button
                class="btn-small btn-primary"
                @click="previewReport(report)"
              >
                👁️ 预览
              </button>
              <button
                class="btn-small btn-secondary"
                @click="downloadReport(report)"
              >
                ⬇️ 下载
              </button>
              <button
                v-if="!report.vectorized && isSuperAdmin"
                class="btn-small btn-accent"
                @click="vectorizeReport(report)"
                :disabled="vectorizing[report.task_id]"
              >
                {{ vectorizing[report.task_id] ? '处理中...' : '🔄 向量化' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="btn-page"
            @click="prevPage"
            :disabled="currentPage === 1"
          >
            ← 上一页
          </button>
          <span class="page-info">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <button
            class="btn-page"
            @click="nextPage"
            :disabled="currentPage === totalPages"
          >
            下一页 →
          </button>
        </div>
      </div>

      <!-- 预览对话框 -->
      <div v-if="previewingReport" class="dialog-overlay" @click.self="closePreview">
        <div class="dialog dialog-large">
          <div class="dialog-header">
            <h2>📄 报告预览</h2>
            <button class="btn-close" @click="closePreview">✕</button>
          </div>

          <div class="dialog-content">
            <div class="preview-meta">
              <div class="meta-row">
                <strong>任务ID：</strong>{{ previewingReport.task_id }}
              </div>
              <div class="meta-row">
                <strong>类型：</strong>{{ getReportTypeLabel(previewingReport.report_type) }}
              </div>
              <div class="meta-row">
                <strong>生成时间：</strong>{{ formatDateTime(previewingReport.generated_at) }}
              </div>
              <div class="meta-row">
                <strong>文件路径：</strong>{{ previewingReport.file_path }}
              </div>
            </div>

            <div class="preview-summary">
              <h4>摘要</h4>
              <p>{{ previewingReport.summary }}</p>
            </div>

            <div v-if="previewContent" class="preview-content">
              <h4>内容预览</h4>
              <div v-html="previewContent" class="content-html"></div>
            </div>
            <div v-else-if="loadingPreview" class="loading-preview">
              <div class="spinner"></div>
              <p>加载预览中...</p>
            </div>
          </div>

          <div class="dialog-actions">
            <button class="btn-primary" @click="downloadReport(previewingReport)">
              ⬇️ 下载完整报告
            </button>
            <button class="btn-secondary" @click="closePreview">
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import axios from '@/utils/axios';

export default {
  name: 'ReportIndexBrowser',
  setup() {
    // 状态
    const reports = ref([]);
    const loading = ref(false);
    const currentPage = ref(1);
    const pageSize = ref(12);
    const totalReports = ref(0);
    const stats = ref(null);
    const vectorizing = ref({});

    // 过滤器
    const filters = ref({
      reportType: '',
      startDate: '',
      endDate: '',
      vectorized: ''
    });

    // 预览
    const previewingReport = ref(null);
    const previewContent = ref('');
    const loadingPreview = ref(false);

    // 用户信息
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const isSuperAdmin = computed(() => user.role === 'super_admin');

    // 计算属性
    const totalPages = computed(() => {
      return Math.ceil(totalReports.value / pageSize.value);
    });

    // 加载报告列表
    const loadReports = async () => {
      loading.value = true;
      try {
        const params = {
          limit: pageSize.value,
          offset: (currentPage.value - 1) * pageSize.value
        };

        if (filters.value.reportType) {
          params.report_type = filters.value.reportType;
        }
        if (filters.value.startDate) {
          params.start_date = filters.value.startDate + 'T00:00:00Z';
        }
        if (filters.value.endDate) {
          params.end_date = filters.value.endDate + 'T23:59:59Z';
        }

        const response = await axios.get('/api/v1/ai/report-index', { params });
        reports.value = response.reports || [];
        totalReports.value = response.total || 0;

        // 如果有过滤条件，应用客户端过滤
        if (filters.value.vectorized !== '') {
          const vectorizedFilter = filters.value.vectorized === 'true';
          reports.value = reports.value.filter(r => r.vectorized === vectorizedFilter);
        }
      } catch (error) {
        console.error('加载报告列表失败:', error);
      } finally {
        loading.value = false;
      }
    };

    // 加载统计信息
    const loadStats = async () => {
      try {
        const response = await axios.get('/api/v1/ai/vectorization-status');
        stats.value = {
          total: response.total_reports || 0,
          vectorized: response.vectorized_reports || 0,
          pending: response.pending_reports || 0,
          rate: response.vectorization_rate || '0%'
        };
      } catch (error) {
        console.error('加载统计信息失败:', error);
      }
    };

    // 重置筛选
    const resetFilters = () => {
      filters.value = {
        reportType: '',
        startDate: '',
        endDate: '',
        vectorized: ''
      };
      currentPage.value = 1;
      loadReports();
    };

    // 分页
    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        loadReports();
      }
    };

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
        loadReports();
      }
    };

    // 预览报告
    const previewReport = async (report) => {
      previewingReport.value = report;
      previewContent.value = '';
      loadingPreview.value = true;

      try {
        // 这里应该调用后端API获取报告内容
        // 暂时使用模拟数据
        await new Promise(resolve => setTimeout(resolve, 500));
        previewContent.value = `<p>报告内容预览...</p><p>完整内容请下载查看。</p>`;
      } catch (error) {
        console.error('加载预览失败:', error);
        previewContent.value = '<p class="error">加载预览失败</p>';
      } finally {
        loadingPreview.value = false;
      }
    };

    // 关闭预览
    const closePreview = () => {
      previewingReport.value = null;
      previewContent.value = '';
    };

    // 下载报告
    const downloadReport = (report) => {
      // 构建下载URL
      const downloadUrl = `/api/v1/files/download?path=${encodeURIComponent(report.file_path)}`;
      window.open(downloadUrl, '_blank');
    };

    // 向量化报告
    const vectorizeReport = async (report) => {
      if (!isSuperAdmin.value) {
        alert('仅超级管理员可以执行此操作');
        return;
      }

      vectorizing.value[report.task_id] = true;

      try {
        await axios.post('/api/v1/ai/vectorize-report', {
          task_id: report.task_id,
          report_type: report.report_type,
          file_path: report.file_path,
          generated_at: report.generated_at
        });

        alert('报告向量化成功');
        report.vectorized = true;
        loadStats();
      } catch (error) {
        console.error('向量化失败:', error);
        alert('向量化失败: ' + (error.response?.data?.detail || error.message));
      } finally {
        vectorizing.value[report.task_id] = false;
      }
    };

    // 格式化函数
    const getReportTypeLabel = (type) => {
      const labels = {
        resource_analysis: '资源分析',
        bcc_monitoring: 'BCC 监控',
        bos_monitoring: 'BOS 监控',
        operational_analysis: '运营分析'
      };
      return labels[type] || type;
    };

    const formatDate = (dateStr) => {
      const date = new Date(dateStr);
      return date.toLocaleDateString('zh-CN');
    };

    const formatDateTime = (dateStr) => {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN');
    };

    // 初始化
    onMounted(() => {
      loadReports();
      loadStats();
    });

    return {
      reports,
      loading,
      currentPage,
      totalPages,
      stats,
      filters,
      vectorizing,
      previewingReport,
      previewContent,
      loadingPreview,
      isSuperAdmin,
      loadReports,
      resetFilters,
      prevPage,
      nextPage,
      previewReport,
      closePreview,
      downloadReport,
      vectorizeReport,
      getReportTypeLabel,
      formatDate,
      formatDateTime
    };
  }
};
</script>

<style scoped>
.report-browser-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
}

.browser-container {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 过滤器 */
.filter-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #555;
}

.filter-group select,
.filter-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

/* 报告网格 */
.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.report-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.3s;
  background: white;
}

.report-card:hover {
  border-color: #4CAF50;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.report-card.vectorized {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.report-type-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
}

.type-resource_analysis {
  background: #e3f2fd;
  color: #1976d2;
}

.type-bcc_monitoring {
  background: #fff3e0;
  color: #f57c00;
}

.type-bos_monitoring {
  background: #f3e5f5;
  color: #7b1fa2;
}

.type-operational_analysis {
  background: #e0f2f1;
  color: #00796b;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
}

.status-badge.vectorized {
  background: #c8e6c9;
  color: #2e7d32;
}

.status-badge.pending {
  background: #fff9c4;
  color: #f57f17;
}

.report-content {
  margin-bottom: 1rem;
}

.report-title {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: #333;
}

.report-summary {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

.report-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: #888;
}

.report-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-small {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-small.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-small.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-small.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-small.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-small.btn-accent {
  background: #2196F3;
  color: white;
}

.btn-small.btn-accent:hover:not(:disabled) {
  background: #1976D2;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载和空状态 */
.loading, .empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 1rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state .hint {
  font-size: 0.9rem;
  color: #999;
  margin-top: 0.5rem;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-page {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-page:hover:not(:disabled) {
  background: #4CAF50;
  color: white;
  border-color: #4CAF50;
}

.btn-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: #666;
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog-large {
  max-width: 900px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
}

.btn-close:hover {
  color: #333;
}

.dialog-content {
  margin-bottom: 1.5rem;
}

.preview-meta {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.meta-row {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.preview-summary {
  margin-bottom: 1rem;
}

.preview-summary h4 {
  margin-bottom: 0.5rem;
}

.preview-content {
  border-top: 1px solid #e0e0e0;
  padding-top: 1rem;
}

.content-html {
  max-height: 400px;
  overflow-y: auto;
  padding: 1rem;
  background: #fafafa;
  border-radius: 4px;
}

.loading-preview {
  text-align: center;
  padding: 2rem;
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-primary, .btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}
</style>
