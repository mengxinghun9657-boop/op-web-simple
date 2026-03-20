# 集群管理平台 v3.0.0

> 基于 FastAPI + Vue3 的集群监控管理平台，集成硬件告警诊断、CMDB资源管理、监控分析和AI智能助手

***

## 📌 项目简介

本系统是一个综合性的集群监控管理平台，提供以下核心功能：

| 功能模块         | 说明                                 |
| ------------ | ---------------------------------- |
| 🔐 用户权限管理    | 基于角色的访问控制（RBAC），支持超级管理员/管理员/普通用户   |
| 🚨 硬件告警诊断    | 自动接收、解析、诊断硬件告警，支持AI解读和Webhook通知    |
| 📦 CMDB资源管理  | 服务器和实例资源管理，支持Excel导入和API自动同步       |
| 📊 监控分析      | PFS监控、Prometheus集群监控、BCC/BOS/EIP监控 |
| 📈 运营数据分析    | 支持Excel上传和iCafe API查询，生成运营分析报告     |
| 💾 资源分析      | 集群资源使用率分析，生成分析报告                   |
| 🤖 AI智能助手    | 智能对话分析，支持自然语言查询数据库                 |
| 🌐 Webhook通知 | 支持飞书和如流告警通知                        |
| 📋 任务管理      | 统一管理所有分析任务                         |
| 🔍 审计日志      | 完整的操作记录追踪                          |

***

## 🏗️ 技术栈

| 层级       | 技术                                            |
| -------- | --------------------------------------------- |
| **后端**   | FastAPI 0.104 / SQLAlchemy 2.0 / Pydantic 2.0 |
| **前端**   | Vue 3 / Element Plus / TailwindCSS            |
| **数据库**  | MySQL 8.0                                     |
| **缓存**   | Redis 7                                       |
| **存储**   | MinIO                                         |
| **AI**   | 百度 ERNIE 4.5                                |
| **部署**   | Docker + Docker Compose + Nginx               |

***

## 🚀 快速开始

### 环境要求

| 依赖             | 版本要求   |
| -------------- | ------ |
| Docker         | 20.10+ |
| Docker Compose | 2.0+   |
| 内存             | 8GB+   |
| 磁盘             | 20GB+  |

### 方式一：完整项目部署（推荐）

在项目根目录执行：

```bash
# 1. 配置环境变量
vi .env

# 2. 执行部署
chmod +x deploy.sh
./deploy.sh
```

### 方式二：内网离线部署

**步骤 1：在外网服务器打包**

```bash
chmod +x pack-offline.sh
./pack-offline.sh
```

**步骤 2：传输到内网服务器**

```bash
scp offline-deploy.tar.gz user@内网服务器IP:/path/to/destination/
```

**步骤 3：在内网服务器部署**

```bash
tar -xzvf offline-deploy.tar.gz
cd offline-deploy
vi .env  # 修改 CORS_ORIGINS
chmod +x start.sh
./start.sh
```

**访问系统**

```bash
# 前端界面
http://服务器IP:8089

# 默认账号
admin / admin123
```

***

## 🔌 API 接口

### 认证接口

| 方法   | 路径                     | 说明       |
| ---- | ---------------------- | -------- |
| POST | `/api/v1/auth/login`   | 用户登录     |
| POST | `/api/v1/auth/refresh` | 刷新 Token |

### 用户管理

| 方法     | 路径                   | 说明        |
| ------ | -------------------- | --------- |
| GET    | `/api/v1/users/me`   | 获取当前用户    |
| GET    | `/api/v1/users`      | 用户列表（管理员） |
| POST   | `/api/v1/users`      | 创建用户      |
| PUT    | `/api/v1/users/{id}` | 更新用户      |
| DELETE | `/api/v1/users/{id}` | 删除用户      |
| GET    | `/api/v1/audit-logs` | 审计日志      |

### 硬件告警

| 方法     | 路径                                      | 说明          |
| ------ | --------------------------------------- | ----------- |
| GET    | `/api/v1/alerts`                        | 告警列表        |
| GET    | `/api/v1/alerts/{id}`                   | 告警详情        |
| POST   | `/api/v1/alerts/{id}/diagnose`          | 触发诊断        |
| PUT    | `/api/v1/alerts/{id}/status`            | 更新状态        |
| POST   | `/api/v1/alerts/{id}/create-icafe-card` | 创建iCafe卡片   |
| GET    | `/api/v1/webhooks`                      | Webhook配置列表 |
| POST   | `/api/v1/webhooks`                      | 创建Webhook配置 |
| PUT    | `/api/v1/webhooks/{id}`                 | 更新Webhook配置 |
| DELETE | `/api/v1/webhooks/{id}`                 | 删除Webhook配置 |

### CMDB管理

| 方法   | 路径                                 | 说明        |
| ---- | ---------------------------------- | --------- |
| GET  | `/api/v1/cmdb/servers`             | 服务器列表     |
| GET  | `/api/v1/cmdb/servers/{hostname}`  | 服务器详情     |
| GET  | `/api/v1/cmdb/instances`           | 实例列表      |
| POST | `/api/v1/cmdb/import`              | 导入Excel数据 |
| POST | `/api/v1/cmdb/sync`                | API同步     |
| GET  | `/api/v1/cmdb/bce/config`          | 获取BCE配置   |
| POST | `/api/v1/cmdb/bce/config`          | 更新BCE配置   |
| POST | `/api/v1/cmdb/bce/sync`            | 同步BCE数据   |
| POST | `/api/v1/cmdb/bce/test-connection` | 测试BCE连接   |

### 监控分析

| 方法   | 路径                                   | 说明             |
| ---- | ------------------------------------ | -------------- |
| POST | `/api/v1/pfs/query`                  | PFS指标查询        |
| POST | `/api/v1/pfs/export`                 | PFS数据导出        |
| POST | `/api/v1/prometheus/cluster/metrics` | Prometheus集群指标 |
| POST | `/api/v1/monitoring/bcc/analyze`     | BCC监控分析        |
| POST | `/api/v1/monitoring/bos/analyze`     | BOS存储分析        |
| POST | `/api/v1/eip/analyze`                | EIP分析          |

### 运营分析

| 方法   | 路径                                       | 说明      |
| ---- | ---------------------------------------- | ------- |
| POST | `/api/v1/operational/analyze`            | 运营分析    |
| POST | `/api/v1/operational/analyze-api`        | API查询分析 |
| GET  | `/api/v1/operational/result/{task_id}`   | 获取分析结果  |
| GET  | `/api/v1/operational/download/{task_id}` | 下载报告    |

### AI对话助手

| 方法     | 路径                   | 说明      |
| ------ | -------------------- | ------- |
| POST   | `/api/v1/ai/chat`    | AI对话    |
| GET    | `/api/v1/ai/history` | 获取对话历史  |
| DELETE | `/api/v1/ai/history` | 清空对话历史  |
| GET    | `/api/v1/ai/tables`  | 获取可查询的表 |

完整 API 文档: `http://服务器IP:8089/docs`

***

## 🐳 常用 Docker 命令

### 容器管理

```bash
# 查看所有运行中的容器
docker ps
# 查看所有容器（包括已停止）
docker ps -a
# 进入后端容器
docker exec -it cluster-backend bash
# 进入MySQL容器
docker exec -it cluster-mysql bash
# 进入MySQL数据库
docker exec -it cluster-mysql mysql -uroot -p123456
# 查看容器日志
docker logs -f cluster-backend
# 重启容器
docker restart cluster-backend
docker restart cluster-mysql
```

### 数据库操作

```bash
# 检查CMDB表字段数量
docker exec -it cluster-mysql mysql -uroot -p123456 -e "
USE cluster_management;
SELECT COUNT(*) as field_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'cluster_management' AND TABLE_NAME = 'iaas_servers';
"

# 执行SQL文件
docker exec -it cluster-mysql mysql -uroot -p123456 < /path/to/script.sql
```

### 服务管理

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps
# 查看服务日志
docker compose -f docker-compose.prod.yml logs -f backend
# 重新启动所有服务
docker compose -f docker-compose.prod.yml up -d
# 停止所有服务
docker compose -f docker-compose.prod.yml down
# 停止所有服务并删除数据卷
docker compose -f docker-compose.prod.yml down -v
# 删除悬空镜像
docker image prune -a -f
# 删除构建缓存
docker builder prune --all --force

#常用命令
unzip /op-web-simple.zip && rm -rf /op-web-simple.zip /__MACOSX && cd /op-web-simple && vim .env
```

### 文件操作

```bash
# 从容器复制文件到本地
docker cp cluster-backend:/app/logs/app.log ./app.log
# 从本地复制文件到容器
docker cp ./config.json cluster-backend:/app/config.json
```

***

## 🛠️ 维护工具脚本

系统提供了一系列实用工具脚本，位于 `backend/scripts/` 目录。

### 故障手册导入

```bash
docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/import_fault_manual.py"
```

### 重新匹配故障手册

```bash
docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/rematch_fault_manual.py"
```

### 数据库诊断
```bash
# 检查数据库连接
docker exec -it cluster-backend python3 -c "from app.core.database import engine; print('Database connected')"
```

***

## 📁 目录结构

```
op-web-simple/
├── backend/                    # 后端
│   ├── app/
│   │   ├── api/v1/            # API 路由
│   │   ├── core/              # 核心组件
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── alert/         # 硬件告警服务
│   │   │   ├── ai/            # AI服务
│   │   │   └── icafe/         # iCafe服务
│   │   └── utils/             # 工具函数
│   ├── config/                # 配置文件
│   ├── scripts/               # 维护工具脚本
│   └── main.py                # 应用入口
├── frontend/                   # 前端
│   ├── src/
│   │   ├── api/               # API接口
│   │   ├── views/             # 页面
│   │   ├── components/        # 组件
│   │   ├── stores/            # 状态管理
│   │   └── router/            # 路由配置
├── docker-compose.prod.yml    # 生产环境编排
├── deploy.sh                  # 部署脚本
├── pack-offline.sh            # 离线打包脚本
└── README.md
```

***

## 📞 访问地址

| 服务     | 地址                       |
| ------ | ------------------------ |
| 前端界面   | <http://服务器IP:8089>      |
| API 文档 | <http://服务器IP:8089/docs> |

***

## 📄 许可证

本项目仅供内部使用。

***

**开始使用集群管理平台！** 🚀
