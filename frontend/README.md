# 集群管理平台前端

## 技术栈

- Vue 3 (Composition API)
- Vite 5
- Element Plus
- Pinia
- Vue Router
- Axios
- ECharts 5

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 访问

- 开发环境: http://localhost:3000
- 后端API: http://127.0.0.1:8000
- API文档: http://127.0.0.1:8000/docs

## 目录结构

```
frontend/
├── src/
│   ├── main.js              # 入口文件
│   ├── App.vue              # 根组件
│   ├── views/               # 页面组件
│   ├── components/          # 可复用组件
│   ├── router/              # 路由配置
│   ├── stores/              # Pinia状态管理
│   ├── api/                 # API调用
│   ├── assets/              # 静态资源
│   └── utils/               # 工具函数
├── public/                  # 公共资源
├── index.html               # HTML模板
├── vite.config.js           # Vite配置
└── package.json             # 依赖配置
```

## 注意事项

- 确保后端服务器运行在 http://127.0.0.1:8000
- 使用 Element Plus 组件库
- 遵循 Vue 3 Composition API
- 使用 ECharts 进行数据可视化
