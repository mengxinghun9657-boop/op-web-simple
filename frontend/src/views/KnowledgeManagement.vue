<template>
  <div class="knowledge-management-page">
    <!-- 密码验证对话框 -->
    <div v-if="!isAuthenticated" class="auth-overlay">
      <div class="auth-dialog">
        <h2>🔐 知识库管理验证</h2>
        <p class="auth-hint">请输入管理员密码以继续</p>
        <input
          v-model="password"
          type="password"
          placeholder="请输入密码"
          @keydown.enter="verifyPassword"
          :disabled="isVerifying"
        />
        <div class="auth-actions">
          <button class="btn-primary" @click="verifyPassword" :disabled="!password || isVerifying">
            {{ isVerifying ? '验证中...' : '验证' }}
          </button>
        </div>
        <p v-if="authError" class="auth-error">{{ authError }}</p>
      </div>
    </div>

    <!-- 主内容区 -->
    <div v-else class="main-content">
      <div class="page-header">
        <h1>📚 知识库管理</h1>
        <div class="header-actions">
          <button class="btn-primary" @click="showCreateDialog">
            ➕ 新建知识条目
          </button>
          <button class="btn-secondary" @click="logout">
            🚪 退出
          </button>
        </div>
      </div>

      <!-- 搜索和过滤 -->
      <div class="filter-section">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索知识条目..."
          class="search-input"
        />
        <select v-model="filterCategory" class="filter-select">
          <option value="">全部分类</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
        <select v-model="filterSource" class="filter-select">
          <option value="">全部来源</option>
          <option value="manual">手动创建</option>
          <option value="auto">自动生成</option>
        </select>
      </div>

      <!-- 知识条目列表 -->
      <div class="entries-list">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="entries.length === 0" class="empty-state">
          <p>暂无知识条目</p>
        </div>
        <div v-else>
          <div v-for="entry in entries" :key="entry.id" class="entry-card">
            <div class="entry-header">
              <h3>{{ entry.title }}</h3>
              <div class="entry-badges">
                <span class="badge" :class="`priority-${entry.priority}`">
                  {{ getPriorityLabel(entry.priority) }}
                </span>
                <span class="badge source-badge">
                  {{ entry.source === 'manual' ? '手动' : '自动' }}
                </span>
              </div>
            </div>
            <div class="entry-content">
              {{ truncateContent(entry.content) }}
            </div>
            <div class="entry-meta">
              <span>分类：{{ entry.category || '无' }}</span>
              <span>标签：{{ entry.tags?.join(', ') || '无' }}</span>
              <span>创建：{{ formatDate(entry.created_at) }}</span>
            </div>
            <div class="entry-actions">
              <button class="btn-small" @click="viewEntry(entry)">查看</button>
              <button class="btn-small" @click="editEntry(entry)">编辑</button>
              <button class="btn-small btn-danger" @click="deleteEntry(entry)">删除</button>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="pagination">
          <button @click="prevPage" :disabled="currentPage === 1">上一页</button>
          <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
          <button @click="nextPage" :disabled="currentPage === totalPages">下一页</button>
        </div>
      </div>

      <!-- 创建/编辑对话框 -->
      <div v-if="showDialog" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog">
          <h2>{{ isEditing ? '编辑知识条目' : '新建知识条目' }}</h2>
          <form @submit.prevent="saveEntry">
            <div class="form-group">
              <label>标题 *</label>
              <input v-model="formData.title" type="text" required />
            </div>
            <div class="form-group">
              <label>内容 *</label>
              <textarea v-model="formData.content" rows="8" required></textarea>
            </div>
            <div class="form-group">
              <label>分类</label>
              <input v-model="formData.category" type="text" />
            </div>
            <div class="form-group">
              <label>标签（逗号分隔）</label>
              <input v-model="tagsInput" type="text" placeholder="例如：MySQL,故障处理" />
            </div>
            <div class="form-group">
              <label>优先级</label>
              <select v-model="formData.priority">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </div>
            <div class="dialog-actions">
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button type="button" class="btn-secondary" @click="closeDialog">取消</button>
            </div>
          </form>
        </div>
      </div>

      <!-- 查看详情对话框 -->
      <div v-if="viewingEntry" class="dialog-overlay" @click.self="viewingEntry = null">
        <div class="dialog dialog-large">
          <h2>{{ viewingEntry.title }}</h2>
          <div class="entry-detail">
            <div class="detail-section">
              <h4>内容</h4>
              <p class="content-text">{{ viewingEntry.content }}</p>
            </div>
            <div class="detail-section">
              <h4>元数据</h4>
              <p><strong>分类：</strong>{{ viewingEntry.category || '无' }}</p>
              <p><strong>标签：</strong>{{ viewingEntry.tags?.join(', ') || '无' }}</p>
              <p><strong>优先级：</strong>{{ getPriorityLabel(viewingEntry.priority) }}</p>
              <p><strong>来源：</strong>{{ viewingEntry.source === 'manual' ? '手动创建' : '自动生成' }}</p>
              <p><strong>创建时间：</strong>{{ formatDate(viewingEntry.created_at) }}</p>
              <p><strong>更新时间：</strong>{{ formatDate(viewingEntry.updated_at) }}</p>
            </div>
          </div>
          <div class="dialog-actions">
            <button class="btn-secondary" @click="viewingEntry = null">关闭</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { 
  verifyPassword as verifyPasswordAPI,
  logout as logoutAPI,
  getKnowledgeEntries,
  createKnowledgeEntry,
  updateKnowledgeEntry,
  deleteKnowledgeEntry,
  getCategories
} from '@/api/knowledge';

export default {
  name: 'KnowledgeManagement',
  setup() {
    // 认证状态
    const isAuthenticated = ref(false);
    const password = ref('');
    const isVerifying = ref(false);
    const authError = ref('');
    const sessionToken = ref('');

    // 列表状态
    const entries = ref([]);
    const loading = ref(false);
    const currentPage = ref(1);
    const pageSize = ref(20);
    const totalEntries = ref(0);
    const categories = ref([]);

    // 过滤状态
    const searchQuery = ref('');
    const filterCategory = ref('');
    const filterSource = ref('');

    // 对话框状态
    const showDialog = ref(false);
    const isEditing = ref(false);
    const formData = ref({
      title: '',
      content: '',
      category: '',
      tags: [],
      priority: 'medium'
    });
    const tagsInput = ref('');
    const saving = ref(false);
    const viewingEntry = ref(null);

    const totalPages = computed(() => Math.ceil(totalEntries.value / pageSize.value));

    // 密码验证
    const verifyPassword = async () => {
      if (!password.value) return;

      isVerifying.value = true;
      authError.value = '';

      try {
        const response = await verifyPasswordAPI({
          password: password.value
        });

        // 添加调试日志
        console.log('🔍 知识库认证响应:', response);
        console.log('🔍 response.success:', response.success);
        console.log('🔍 response.data:', response.data);
        console.log('🔍 response.data?.token:', response.data?.token);

        if (response.success && response.data && response.data.token) {
          sessionToken.value = response.data.token;
          isAuthenticated.value = true;
          loadEntries();
          loadCategories();
        } else {
          authError.value = response.message || response.error || '密码验证失败';
        }
      } catch (error) {
        console.error('❌ 知识库认证错误:', error);
        console.error('❌ error.response:', error.response);
        console.error('❌ error.response?.data:', error.response?.data);
        authError.value = error.response?.data?.error || error.response?.data?.message || error.message || '密码验证失败';
      } finally {
        isVerifying.value = false;
      }
    };

    // 退出登录
    const logout = async () => {
      try {
        await logoutAPI(sessionToken.value);
      } catch (error) {
        console.error('Logout error:', error);
      }

      isAuthenticated.value = false;
      sessionToken.value = '';
      password.value = '';
      entries.value = [];
    };

    // 处理 401 错误（令牌过期）
    const handleTokenExpired = () => {
      isAuthenticated.value = false;
      sessionToken.value = '';
      password.value = '';
      entries.value = [];
      authError.value = '会话已过期，请重新登录';
    };

    // 加载知识条目列表
    const loadEntries = async () => {
      loading.value = true;

      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        };

        if (filterCategory.value) params.category = filterCategory.value;
        if (filterSource.value) params.source = filterSource.value;

        const response = await getKnowledgeEntries(params, sessionToken.value);

        if (response) {
          // API直接返回KnowledgeEntryListResponse格式
          entries.value = response.entries || [];
          totalEntries.value = response.total || 0;
        }
      } catch (error) {
        console.error('Load entries error:', error);
        if (error.response?.status === 403) {
          isAuthenticated.value = false;
        }
      } finally {
        loading.value = false;
      }
    };

    // 加载分类列表
    const loadCategories = async () => {
      try {
        const response = await getCategories(sessionToken.value);
        if (response && response.categories) {
          categories.value = response.categories || [];
        }
      } catch (error) {
        console.error('Load categories error:', error);
      }
    };

    // 显示创建对话框
    const showCreateDialog = () => {
      isEditing.value = false;
      formData.value = {
        title: '',
        content: '',
        category: '',
        tags: [],
        priority: 'medium'
      };
      tagsInput.value = '';
      showDialog.value = true;
    };

    // 编辑条目
    const editEntry = (entry) => {
      isEditing.value = true;
      formData.value = {
        id: entry.id,
        title: entry.title,
        content: entry.content,
        category: entry.category || '',
        tags: entry.tags || [],
        priority: entry.priority
      };
      tagsInput.value = entry.tags?.join(', ') || '';
      showDialog.value = true;
    };

    // 查看条目
    const viewEntry = (entry) => {
      viewingEntry.value = entry;
    };

    // 保存条目
    const saveEntry = async () => {
      saving.value = true;

      try {
        const data = {
          ...formData.value,
          tags: tagsInput.value.split(',').map(t => t.trim()).filter(t => t)
        };

        let response;
        if (isEditing.value) {
          response = await updateKnowledgeEntry(data.id, data, sessionToken.value);
          alert('✅ 知识条目已更新');
        } else {
          response = await createKnowledgeEntry(data, sessionToken.value);
          alert('✅ 知识条目已保存');
        }

        closeDialog();
        loadEntries();
      } catch (error) {
        console.error('Save entry error:', error);
        
        // 处理 401 错误（令牌过期）
        if (error.response?.status === 401) {
          handleTokenExpired();
          return;
        }
        
        alert(error.message || '保存失败');
      } finally {
        saving.value = false;
      }
    };

    // 删除条目
    const deleteEntry = async (entry) => {
      if (!confirm(`确定要删除"${entry.title}"吗？`)) return;

      try {
        await deleteKnowledgeEntry(entry.id, sessionToken.value);
        alert('✅ 知识条目已删除');
        loadEntries();
      } catch (error) {
        console.error('Delete entry error:', error);
        
        // 处理 401 错误（令牌过期）
        if (error.response?.status === 401) {
          handleTokenExpired();
          return;
        }
        
        alert(error.message || '删除失败');
      }
    };

    // 关闭对话框
    const closeDialog = () => {
      showDialog.value = false;
      formData.value = {
        title: '',
        content: '',
        category: '',
        tags: [],
        priority: 'medium'
      };
      tagsInput.value = '';
    };

    // 分页
    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        loadEntries();
      }
    };

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
        loadEntries();
      }
    };

    // 工具函数
    const truncateContent = (content) => {
      return content.length > 150 ? content.substring(0, 150) + '...' : content;
    };

    const getPriorityLabel = (priority) => {
      const labels = { low: '低', medium: '中', high: '高' };
      return labels[priority] || priority;
    };

    const formatDate = (dateStr) => {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN');
    };

    // 监听过滤条件变化
    watch([filterCategory, filterSource], () => {
      currentPage.value = 1;
      loadEntries();
    });

    return {
      isAuthenticated,
      password,
      isVerifying,
      authError,
      verifyPassword,
      logout,
      handleTokenExpired,
      entries,
      loading,
      currentPage,
      totalPages,
      categories,
      searchQuery,
      filterCategory,
      filterSource,
      showDialog,
      isEditing,
      formData,
      tagsInput,
      saving,
      viewingEntry,
      showCreateDialog,
      editEntry,
      viewEntry,
      saveEntry,
      deleteEntry,
      closeDialog,
      prevPage,
      nextPage,
      truncateContent,
      getPriorityLabel,
      formatDate
    };
  }
};
</script>

<style scoped>
.knowledge-management-page {
  min-height: 100vh;
  background: #f5f5f5;
}

/* 认证对话框 */
.auth-overlay {
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

.auth-dialog {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.auth-dialog h2 {
  margin-bottom: 0.5rem;
  text-align: center;
}

.auth-hint {
  text-align: center;
  color: #666;
  margin-bottom: 1.5rem;
}

.auth-dialog input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.auth-actions {
  display: flex;
  justify-content: center;
}

.auth-error {
  color: #f44336;
  text-align: center;
  margin-top: 1rem;
}

/* 主内容区 */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

/* 过滤区 */
.filter-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.search-input, .filter-select {
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
}

.search-input {
  flex: 1;
}

/* 条目列表 */
.entries-list {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading, .empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.entry-card {
  padding: 1.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 1rem;
  transition: box-shadow 0.3s;
}

.entry-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.entry-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.entry-badges {
  display: flex;
  gap: 0.5rem;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.priority-low { background: #e8f5e9; color: #2e7d32; }
.priority-medium { background: #fff3e0; color: #f57c00; }
.priority-high { background: #ffebee; color: #c62828; }
.source-badge { background: #e3f2fd; color: #1976d2; }

.entry-content {
  color: #666;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.entry-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.9rem;
  color: #999;
  margin-bottom: 1rem;
}

.entry-actions {
  display: flex;
  gap: 0.5rem;
}

/* 按钮 */
.btn-primary, .btn-secondary, .btn-small, .btn-danger {
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

.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-small {
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  background: #f5f5f5;
  color: #333;
}

.btn-small:hover {
  background: #e0e0e0;
}

.btn-danger {
  background: #ffebee;
  color: #c62828;
}

.btn-danger:hover {
  background: #ffcdd2;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

.pagination button:hover:not(:disabled) {
  background: #f5f5f5;
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
  padding: 2rem;
  border-radius: 12px;
  width: 600px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.dialog-large {
  width: 800px;
}

.dialog h2 {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
}

.form-group textarea {
  resize: vertical;
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

/* 详情视图 */
.entry-detail {
  margin: 1.5rem 0;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h4 {
  margin-bottom: 1rem;
  color: #333;
}

.content-text {
  line-height: 1.8;
  color: #444;
  white-space: pre-wrap;
}

.detail-section p {
  margin-bottom: 0.5rem;
  color: #666;
}
</style>
