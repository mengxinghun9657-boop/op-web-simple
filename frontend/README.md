# 集群管理平台前端

基于 Vue 3 + Element Plus 的现代化管理平台，采用 Google Material Design 设计系统。

## 技术栈

- Vue 3 (Composition API)
- Vite 5
- Element Plus
- Pinia (状态管理)
- Vue Router 4
- Axios (HTTP客户端)
- ECharts 5 (数据可视化)
- **Google Material Design** (设计系统)

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
```

## 访问地址

- 开发环境: http://localhost:3000
- 后端API: http://127.0.0.1:8000
- API文档: http://127.0.0.1:8000/docs

## 目录结构

```
frontend/
├── src/
│   ├── main.js              # 应用入口
│   ├── App.vue              # 根组件
│   ├── views/               # 页面组件（22个）
│   │   ├── Dashboard.vue
│   │   ├── alerts/          # 硬件告警模块
│   │   ├── admin/           # 系统管理模块
│   │   └── monitoring/      # 监控分析模块
│   ├── components/          # 可复用组件
│   │   ├── common/          # 通用组件
│   │   ├── cmdb/            # CMDB组件
│   │   └── pfs/             # PFS监控组件
│   ├── router/              # 路由配置
│   ├── stores/              # Pinia状态管理
│   ├── api/                 # API调用封装
│   ├── assets/              # 静态资源
│   │   └── styles/          # 样式文件
│   │       ├── google-blue-theme.css      # 主题变量
│   │       ├── google-components.css      # 组件样式
│   │       └── google-pages.css           # 页面样式
│   └── utils/               # 工具函数
├── public/                  # 公共资源
├── .archived_docs/          # 已归档的临时文档
├── index.html               # HTML模板
├── vite.config.js           # Vite配置
└── package.json             # 项目依赖

```

## 核心功能模块

### 1. 🚨 硬件告警诊断系统
- 告警列表与详情查看
- 自动诊断与AI解读
- Webhook通知管理
- 统计分析

### 2. 📊 监控分析
- BCC实例监控
- BOS存储分析
- EIP流量分析
- PFS文件系统监控

### 3. 📦 CMDB资源管理
- 服务器资源管理
- 实例信息查询
- 自动同步与更新

### 4. 📈 运营分析
- 趋势预测与报告生成
- 人效分析
- iCafe集成

### 5. ⚙️ 系统配置
- 模块配置管理
- 用户权限管理
- 审计日志查看

## 设计系统

本项目采用 **Google Material Design** 统一设计系统：

### 色彩规范
- 主色: `#1a73e8` (Google Blue)
- 成功: `#1e8e3e` (Google Green)
- 警告: `#f9ab00` (Google Yellow)
- 错误: `#d93025` (Google Red)

### 间距系统（8px网格）
- `--space-2` = 8px（小间距）
- `--space-4` = 16px（标准间距）
- `--space-6` = 24px（大间距）
- `--space-8` = 32px（超大间距）

### 圆角规范
- 按钮: `--radius-md` = 8px
- 卡片: `--radius-xl` = 16px
- 对话框: `--radius-2xl` = 20px

### 统一组件类名
- `page-container` - 页面容器
- `page-header` - 页面头部
- `content-card` - 内容卡片
- `google-table` - 统一表格样式
- `google-dialog` - 统一对话框样式
- `google-pagination` - 统一分页样式

详细设计规范请参考 `.archived_docs/DESIGN_SYSTEM.md`（已归档）

## 开发规范

### 页面结构模板

```vue
<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <div class="page-title">
          <div class="page-title-icon">
            <el-icon><IconComponent /></el-icon>
          </div>
          页面标题
        </div>
        <div class="page-subtitle">页面说明</div>
      </div>
      <div class="page-actions">
        <el-button type="primary">操作按钮</el-button>
      </div>
    </div>

    <!-- 内容卡片 -->
    <div class="content-card">
      <div class="content-card-header">
        <div class="content-card-title">
          <el-icon><Icon /></el-icon>
          卡片标题
        </div>
      </div>
      <div class="content-card-body">
        <!-- 内容区域 -->
      </div>
    </div>
  </div>
</template>
```

### CSS变量使用

```css
/* ✅ 正确 - 使用统一变量 */
.my-component {
  padding: var(--space-4);
  font-size: var(--text-base);
  color: var(--primary);
  border-radius: var(--radius-md);
}

/* ❌ 错误 - 旧命名方式 */
.my-component {
  padding: var(--spacing-4);
  font-size: var(--font-size-base);
  color: var(--color-primary);
}
```

## 项目状态

- ✅ 基础设施：100% 完成
- ✅ 高优先级页面：100% 完成（3/3）
- 🟡 中优先级页面：37.5% 完成（3/8）
- 🔴 低优先级页面：0% 完成（0/11）
- **总体进度**：**38.5%** (10/26)

最后更新：2026-03-16

## 相关文档

- **功能逻辑文档**: `../.kiro/steering/功能逻辑.md`
- **后端README**: `../backend/README.md`
- **部署文档**: `../deploy.sh`
- **归档文档**: `.archived_docs/README.md`

## 许可证

内部项目


## 注意事项

- 确保后端服务器运行在 http://127.0.0.1:8000
- 使用 Element Plus 组件库
- 遵循 Vue 3 Composition API
- 使用 ECharts 进行数据可视化
