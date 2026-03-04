# 硬件告警智能诊断系统 - 前端设置指南

## 功能概述

硬件告警智能诊断系统前端包含以下功能模块:

1. **告警列表** (`/alerts`) - 查看所有硬件告警,支持筛选和分页
2. **告警详情** (`/alerts/:id`) - 查看告警详细信息和诊断结果
3. **统计分析** (`/alerts/statistics`) - 可视化展示告警趋势和分布
4. **Webhook配置** (`/alerts/webhooks`) - 管理告警通知的Webhook
5. **监控路径配置** (`/alerts/monitor-paths`) - 配置告警文件监控路径

## 安装依赖

### 1. 安装新增的依赖包

```bash
cd frontend
npm install marked@^11.0.0
```

或者重新安装所有依赖:

```bash
cd frontend
npm install
```

### 2. 依赖说明

- `marked` - 用于渲染AI解读结果的Markdown内容
- `echarts` - 用于统计图表展示(已存在)
- `element-plus` - UI组件库(已存在)

## 启动开发服务器

```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173` (或Vite显示的端口)

## 页面路由

| 路由 | 页面 | 权限要求 |
|------|------|---------|
| `/alerts` | 告警列表 | 所有用户 |
| `/alerts/:id` | 告警详情 | 所有用户 |
| `/alerts/statistics` | 统计分析 | 所有用户 |
| `/alerts/webhooks` | Webhook配置 | 管理员 |
| `/alerts/monitor-paths` | 监控路径配置 | 管理员 |

## API端点

所有API遵循统一响应格式:

```json
{
  "success": boolean,
  "data": object | array | null,
  "message": string,
  "error": string | null
}
```

### 告警管理API

- `GET /api/v1/alerts` - 获取告警列表
- `GET /api/v1/alerts/{id}` - 获取告警详情
- `POST /api/v1/alerts/{id}/diagnose` - 手动触发诊断
- `GET /api/v1/alerts/filter-options` - 获取筛选选项

### 统计分析API

- `GET /api/v1/alerts/statistics/trend` - 告警趋势统计
- `GET /api/v1/alerts/statistics/distribution` - 告警类型分布
- `GET /api/v1/alerts/statistics/top-nodes` - 节点告警排行

### Webhook管理API

- `GET /api/v1/webhooks` - 获取Webhook列表
- `POST /api/v1/webhooks` - 创建Webhook
- `PUT /api/v1/webhooks/{id}` - 更新Webhook
- `DELETE /api/v1/webhooks/{id}` - 删除Webhook
- `POST /api/v1/webhooks/{id}/test` - 测试Webhook

### 监控路径配置API

- `GET /api/v1/monitor-paths` - 获取监控路径列表
- `POST /api/v1/monitor-paths` - 创建监控路径
- `PUT /api/v1/monitor-paths/{id}` - 更新监控路径
- `DELETE /api/v1/monitor-paths/{id}` - 删除监控路径
- `POST /api/v1/monitor-paths/{id}/test` - 测试监控路径
- `POST /api/v1/monitor-paths/batch-update` - 批量更新状态

## 文件结构

```
frontend/src/
├── api/
│   ├── alerts.js              # 告警管理API
│   ├── statistics.js          # 统计分析API
│   ├── webhooks.js            # Webhook管理API
│   └── monitor-paths.js       # 监控路径配置API
├── views/alerts/
│   ├── AlertList.vue          # 告警列表页面
│   ├── AlertDetail.vue        # 告警详情页面
│   ├── Statistics.vue         # 统计分析页面
│   ├── WebhookConfig.vue      # Webhook配置页面
│   └── MonitorPathConfig.vue  # 监控路径配置页面
└── router/
    └── index.js               # 路由配置(已添加告警相关路由)
```

## 开发注意事项

### 1. API响应格式

所有API调用都会返回统一格式,前端axios拦截器已配置自动处理:

```javascript
// 成功响应
{
  success: true,
  data: { ... },
  message: "操作成功"
}

// 失败响应
{
  success: false,
  error: "错误信息",
  message: "操作失败"
}
```

### 2. 分页数据格式

列表接口返回的分页数据格式:

```javascript
{
  success: true,
  data: {
    list: [...],      // 数据列表
    total: 100,       // 总数
    page: 1,          // 当前页
    page_size: 20     // 每页数量
  }
}
```

### 3. 字段命名约定

- 后端使用 `snake_case` (如: `alert_type`, `created_at`)
- 前端保持与后端一致,不做转换
- 这样可以避免字段名转换带来的问题

### 4. 错误处理

axios拦截器已配置统一错误处理,会自动显示错误消息:

```javascript
// 不需要手动处理错误提示
try {
  const response = await getAlerts(params)
  if (response.success) {
    // 处理成功逻辑
  }
} catch (error) {
  // 错误已被拦截器处理,这里可以做额外处理
}
```

## 测试建议

### 1. 功能测试

- [ ] 告警列表加载和筛选
- [ ] 告警详情展示(手册、API、AI解读)
- [ ] 统计图表正确渲染
- [ ] Webhook CRUD操作
- [ ] 监控路径CRUD操作
- [ ] 批量操作功能

### 2. 响应式测试

- [ ] 移动端(320px)
- [ ] 平板(768px)
- [ ] 桌面(1024px, 1440px)

### 3. 浏览器兼容性

- [ ] Chrome (推荐)
- [ ] Firefox
- [ ] Safari
- [ ] Edge

## 部署

### 构建生产版本

```bash
cd frontend
npm run build
```

构建产物在 `dist/` 目录

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/frontend/dist;
    index index.html;
    
    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 常见问题

### Q: 图表不显示?

A: 确保已安装echarts依赖,并且容器元素有明确的高度:

```vue
<div ref="chartRef" style="height: 400px"></div>
```

### Q: Markdown渲染不正确?

A: 确保已安装marked依赖:

```bash
npm install marked@^11.0.0
```

### Q: API请求失败?

A: 检查:
1. 后端服务是否启动
2. `.env.development` 中的 `VITE_API_BASE_URL` 配置是否正确
3. 浏览器控制台的网络请求详情

### Q: 路由404?

A: 确保:
1. 路由已在 `router/index.js` 中正确配置
2. 组件文件路径正确
3. 使用了懒加载 `() => import('@/views/...')`

## 后续优化建议

1. **性能优化**
   - 图表数据缓存
   - 虚拟滚动(大数据量列表)
   - 组件懒加载

2. **用户体验**
   - 添加骨架屏
   - 优化加载状态
   - 添加空状态提示

3. **功能增强**
   - 导出报表功能
   - 告警订阅功能
   - 实时推送更新

4. **测试覆盖**
   - 单元测试(Vitest)
   - E2E测试(Playwright)
   - 视觉回归测试

## 联系方式

如有问题,请联系开发团队或查看项目文档。
