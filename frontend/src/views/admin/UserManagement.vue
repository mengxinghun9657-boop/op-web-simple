<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><User /></el-icon>
          </div>
          用户管理
        </div>
        <div class="page-subtitle">管理系统用户和权限设置</div>
      </div>
    </div>

    <!-- 筛选和操作区域 -->
    <div class="content-card">
      <div class="content-card-body">
        <div class="filter-actions">
          <div class="filter-inputs">
            <el-input v-model="searchQuery" placeholder="搜索用户名/邮箱..." prefix-icon="Search" clearable style="width: 240px" />
            <el-select v-model="roleFilter" placeholder="角色筛选" clearable style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="管理员" value="admin" />
              <el-option label="分析师" value="analyst" />
              <el-option label="只读用户" value="viewer" />
            </el-select>
          </div>
          <div class="filter-buttons">
            <el-button type="primary" @click="handleCreate">
              <el-icon><Plus /></el-icon>
              新建用户
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 用户列表 -->
    <!-- 用户列表 -->
    <div class="content-card">
      <div class="content-card-body">
        <el-table :data="filteredUsers" v-loading="loading" class="google-table">
          <el-table-column prop="username" label="用户名" width="150">
            <template #default="{ row }">
              <div class="user-cell">
                <el-avatar :size="24" class="user-avatar">{{ row.username.charAt(0).toUpperCase() }}</el-avatar>
                {{ row.username }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="180" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="getRoleTag(row.role)">{{ formatRole(row.role) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_active"
                @change="handleStatusChange(row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="last_login" label="最后登录" width="180" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
                <el-button size="small" type="warning" @click="handleResetPwd(row)">重置密码</el-button>
                <el-popconfirm title="确认删除该用户?" @confirm="handleDelete(row)">
                  <template #reference>
                    <el-button size="small" type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="table-footer">
          <el-pagination
            background
            layout="total, prev, pager, next, sizes"
            :total="totalUsers"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            class="google-pagination"
          />
        </div>
      </div>
    </div>

    <!-- 用户表单对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" class="google-dialog" append-to-body>
      <el-form :model="form" label-width="80px" class="google-form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" teleported popper-class="dialog-select-popper">
            <el-option label="管理员 (Admin)" value="admin" />
            <el-option label="分析师 (Analyst)" value="analyst" />
            <el-option label="只读用户 (Viewer)" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" v-if="!isEdit">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetPwdVisible" title="重置密码" width="400px" class="google-dialog">
      <el-form :model="resetForm" label-width="80px" class="google-form">
        <el-form-item label="用户名">
          <el-input v-model="resetForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetForm.new_password" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search, User } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

// 数据状态
const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const roleFilter = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = ref({})
const currentPage = ref(1)
const pageSize = ref(10)

// 重置密码相关
const resetPwdVisible = ref(false)
const resetForm = ref({
  user_id: null,
  username: '',
  new_password: ''
})

// 获取用户列表
const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/v1/users', {
      params: {
        skip: 0,
        limit: 1000 // 获取所有用户用于前端筛选
      }
    })
    
    // 修复：正确解析响应格式 {success, data: {list, total, page, page_size}, message}
    if (response.success && response.data && response.data.list) {
      users.value = response.data.list
    } else {
      users.value = []
      ElMessage.warning('用户列表数据格式异常')
    }
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// 过滤后的用户列表
const filteredUsers = computed(() => {
  let result = users.value.filter(u => {
    const matchQuery = !searchQuery.value || 
      u.username.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
      (u.email && u.email.toLowerCase().includes(searchQuery.value.toLowerCase()))
    const matchRole = !roleFilter.value || u.role === roleFilter.value
    return matchQuery && matchRole
  })
  
  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return result.slice(start, end)
})

// 总数（用于分页）
const totalUsers = computed(() => {
  return users.value.filter(u => {
    const matchQuery = !searchQuery.value || 
      u.username.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
      (u.email && u.email.toLowerCase().includes(searchQuery.value.toLowerCase()))
    const matchRole = !roleFilter.value || u.role === roleFilter.value
    return matchQuery && matchRole
  }).length
})

const dialogTitle = computed(() => isEdit.value ? '编辑用户' : '新建用户')

const getRoleTag = (role) => {
  const map = { super_admin: 'danger', admin: 'warning', analyst: 'primary', viewer: 'info' }
  return map[role] || 'info'
}

const formatRole = (role) => {
  const map = { super_admin: '超级管理员', admin: '管理员', analyst: '分析师', viewer: '只读用户' }
  return map[role] || role
}

const handleCreate = () => {
  isEdit.value = false
  form.value = { role: 'viewer', is_active: true, username: '', email: '', password: '' }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const saveUser = async () => {
  try {
    if (isEdit.value) {
      // 更新用户
      await axios.put(`/api/v1/users/${form.value.id}`, {
        email: form.value.email,
        role: form.value.role,
        is_active: form.value.is_active
      })
      ElMessage.success('用户更新成功')
    } else {
      // 创建新用户
      if (!form.value.username || !form.value.password) {
        ElMessage.warning('请填写用户名和密码')
        return
      }
      
      // 前端密码验证
      if (form.value.password.length < 6) {
        ElMessage.warning('密码长度至少6位')
        return
      }
      if (form.value.username.length < 3) {
        ElMessage.warning('用户名长度至少3位')
        return
      }
      
      await axios.post('/api/v1/users', {
        username: form.value.username,
        email: form.value.email || null,  // 不填则为null，而不是生成虚假邮箱
        password: form.value.password,
        role: form.value.role,
        full_name: form.value.username
      })
      ElMessage.success('用户创建成功')
    }
    
    dialogVisible.value = false
    await fetchUsers() // 刷新列表
  } catch (error) {
    // 422错误通常是验证失败
    if (error.response?.status === 422) {
      const detail = error.response?.data?.detail
      if (Array.isArray(detail)) {
        // Pydantic验证错误
        const errors = detail.map(e => {
          const field = e.loc[e.loc.length - 1]
          const fieldMap = {
            'password': '密码',
            'username': '用户名',
            'email': '邮箱'
          }
          return `${fieldMap[field] || field}: ${e.msg}`
        }).join('; ')
        ElMessage.error(`输入验证失败: ${errors}`)
      } else {
        ElMessage.error(`验证失败: ${detail}`)
      }
    } else {
      const msg = error.response?.data?.detail || error.message
      ElMessage.error(`操作失败: ${msg}`)
    }
  }
}

const handleStatusChange = async (row) => {
  try {
    await axios.put(`/api/v1/users/${row.id}`, {
      is_active: row.is_active
    })
    ElMessage.success(`用户 ${row.username} 状态已更新为 ${row.is_active ? '启用' : '禁用'}`)
  } catch (error) {
    row.is_active = !row.is_active // 回滚
    ElMessage.error('状态更新失败')
  }
}

const handleResetPwd = (row) => {
  resetForm.value = {
    user_id: row.id,
    username: row.username,
    new_password: ''
  }
  resetPwdVisible.value = true
}

const confirmResetPwd = async () => {
  if (!resetForm.value.new_password || resetForm.value.new_password.length < 6) {
    ElMessage.warning('请输入至少6位密码')
    return
  }
  
  try {
    await axios.post(`/api/v1/users/${resetForm.value.user_id}/reset-password`, {
      new_password: resetForm.value.new_password
    })
    ElMessage.success(`用户 ${resetForm.value.username} 密码重置成功`)
    resetPwdVisible.value = false
  } catch (error) {
    const msg = error.response?.data?.detail || error.message
    ElMessage.error(`重置密码失败: ${msg}`)
  }
}

const handleDelete = async (row) => {
  try {
    await axios.delete(`/api/v1/users/${row.id}`)
    ElMessage.success('用户已删除')
    await fetchUsers() // 刷新列表
  } catch (error) {
    const msg = error.response?.data?.detail || error.message
    ElMessage.error(`删除失败: ${msg}`)
  }
}

// 组件挂载时获取用户列表
onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.filter-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.filter-inputs {
  display: flex;
  gap: var(--space-3);
}

.filter-buttons {
  display: flex;
  gap: var(--space-2);
}

.user-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.user-avatar {
  background: var(--primary);
  color: white;
}

.action-buttons {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.action-buttons .el-button {
  padding: 6px 12px !important;
  font-size: var(--text-xs) !important;
}

@media (max-width: 768px) {
  .filter-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-inputs {
    flex-direction: column;
  }

  .filter-inputs .el-input,
  .filter-inputs .el-select {
    width: 100% !important;
  }
}
</style>
