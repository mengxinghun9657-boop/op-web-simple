# 集群管理平台 v5.0.0

> 基于 FastAPI + Vue3 的集群监控运维平台，集成硬件告警诊断、CMDB资源管理、GPU 集群监控、CCE 集群监控、APIServer 监控告警、资源分析和 AI 智能助手

---

## 📌 项目简介

| 功能模块 | 说明 |
|---------|------|
| 🔐 用户权限管理 | JWT 认证，RBAC 角色控制（super_admin / admin / analyst / viewer），审计日志 |
| 🚨 硬件告警管理 | 接收 HAS Webhook / 文件监控，故障手册匹配，CCE 诊断，AI 解读，飞书/如流通知 |
| 📦 CMDB 资源管理 | 服务器/实例资源管理，支持 Excel 导入和 AMIS/BCE API 自动同步 |
| 🖥️ APIServer 监控 | Prometheus 查询 APIServer 请求率/错误率/延迟，扫描异常记录，iCafe 建卡 |
| 🖥️ CCE 集群监控 | 实时查询 Prometheus，展示节点/Pod/资源使用率/APIServer 健康，支持趋势图 |
| 🎮 GPU 集群监控 | HAS 巡检采集，Grafana 仪表盘嵌入，bottom 卡时统计与分析报告 |
| 📊 监控分析 | PFS 监控、BCC/BOS/EIP 监控分析 |
| 💾 资源分析 | 集群资源使用率分析，生成分析报告 |
| 📈 运营数据分析 | Excel 上传或 iCafe API 查询，生成运营分析报告 |
| 🤖 AI 智能助手 | ERNIE 对话，自然语言查询数据库 |
| 📋 任务管理 | 统一管理所有异步任务（Redis 队列 + Worker） |
| 🔍 审计日志 | 记录用户登录、创建、修改、删除等操作 |

---

## 🏗️ 技术栈

| 层级 | 技术 |
|-----|------|
| **后端 API** | FastAPI 0.104 / SQLAlchemy 2.0 / Pydantic 2.0 |
| **后端 Worker** | Python 独立进程，通过 Redis 队列消费任务 |
| **前端** | Vue 3 / Element Plus / ECharts |
| **数据库** | MySQL 8.0 |
| **缓存 / 队列** | Redis 7 |
| **对象存储** | MinIO |
| **AI** | 百度 ERNIE 4.5 |
| **部署** | Docker + Docker Compose + Nginx |

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本要求 |
|-----|---------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| 内存 | 8GB+ |
| 磁盘 | 20GB+ |

### 方式一：外网部署

#### 1. 配置环境变量

```bash
cp .env.example .env
vi .env
```

**关键配置项**：

| 配置项 | 说明 |
|-------|------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码（请修改） |
| `MYSQL_PASSWORD` | MySQL 应用密码（请修改） |
| `REDIS_PASSWORD` | Redis 密码（请修改） |
| `MINIO_ROOT_PASSWORD` | MinIO 密码（请修改） |
| `SECRET_KEY` | JWT 密钥（从环境变量读取，必须设置） |
| `CORS_ORIGINS` | 跨域允许地址，**必须改为实际服务器 IP** |
| `WORKERS` | 后端 Worker 数量（外网建议 2，内网建议 4） |

```bash
# 必须修改
CORS_ORIGINS=http://YOUR_SERVER_IP:8089
```

#### 2. 执行部署

```bash
chmod +x deploy.sh
./deploy.sh
```

### 方式二：内网离线部署

```bash
# 外网打包
chmod +x pack-offline.sh
./pack-offline.sh

# 传输到内网
scp offline-deploy.tar.gz user@内网IP:/path/

# 内网部署
tar -xzvf offline-deploy.tar.gz
cd offline-deploy
vi .env  # 修改 CORS_ORIGINS
chmod +x start.sh
./start.sh
```

**访问地址**：`http://服务器IP:8089`，默认账号：`admin / admin123`

---

## 🏛️ 服务架构

系统拆分为两个后端服务：

```
┌─────────────────────────────────────────────────────────┐
│                    frontend (Nginx)                     │
│             Vue 3 + Element Plus + ECharts              │
└─────────────────────────────────────────────────────────┘
                          │ Axios
                          ▼
┌─────────────────────────────────────────────────────────┐
│               backend-api (FastAPI)                     │
│  处理 HTTP 请求，耗时任务入队后立即返回 task_id          │
│  ENABLE_SCHEDULER=false  ENABLE_FILE_WATCHER=false      │
└─────────────────────────────────────────────────────────┘
            │ Redis queue:xxx 入队
            ▼
┌─────────────────────────────────────────────────────────┐
│              backend-worker (Python)                    │
│  消费 Redis 队列，执行耗时分析任务，结果写 DB / MinIO   │
│  ENABLE_SCHEDULER=true  ENABLE_FILE_WATCHER=true        │
└─────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┼──────────────┐
            ▼             ▼              ▼
         MySQL          Redis          MinIO
        业务数据         队列/缓存      报告文件
```

**Worker 任务队列**：

| 队列名 | 功能 |
|-------|------|
| `resource_analysis` | 资源分析 |
| `gpu_bottom_analysis` | GPU bottom 卡时分析 |
| `apiserver_alert_analysis` | APIServer 告警扫描 |
| `pfs_export` | PFS 数据导出 |
| `gpu_has_inspection_collect` | GPU HAS 巡检采集 |
| `prometheus_batch_collect` | 批量集群指标采集 |
| `operational_excel_analysis` | 运营 Excel 分析 |
| `operational_api_analysis` | 运营 API 查询分析 |

---

## 🔌 API 接口

### 认证

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |

### 用户管理

| 方法 | 路径 | 权限 | 说明 |
|-----|------|------|------|
| GET | `/api/v1/users/me` | 需登录 | 当前用户信息 |
| GET | `/api/v1/users` | admin+ | 用户列表（`page` / `page_size`） |
| POST | `/api/v1/users` | admin+ | 创建用户 |
| PUT | `/api/v1/users/{id}` | admin+ | 更新用户（admin 不可改 super_admin） |
| DELETE | `/api/v1/users/{id}` | super_admin | 删除用户（不可删自己） |
| POST | `/api/v1/users/{id}/reset-password` | admin+ | 重置密码（admin 不可改 super_admin） |
| GET | `/api/v1/audit-logs` | admin+ | 审计日志（`page` / `page_size`） |

### 硬件告警

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/alerts` | 告警列表 |
| GET | `/api/v1/alerts/{id}` | 告警详情 |
| POST | `/api/v1/alerts/{id}/diagnose` | 触发诊断 |
| PUT | `/api/v1/alerts/{id}/status` | 更新状态 |
| PUT | `/api/v1/alerts/batch/status` | 批量更新状态 |
| POST | `/api/v1/alerts/{id}/create-icafe-card` | 创建 iCafe 卡片 |

### APIServer 监控告警

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/v1/apiserver-alerts/analyze` | 触发扫描任务 |
| GET | `/api/v1/apiserver-alerts` | 告警列表 |
| GET | `/api/v1/apiserver-alerts/{id}` | 告警详情 |
| PUT | `/api/v1/apiserver-alerts/{id}/status` | 更新状态 |
| PUT | `/api/v1/apiserver-alerts/batch/status` | 批量更新状态 |
| POST | `/api/v1/apiserver-alerts/{id}/create-icafe-card` | 创建 iCafe 卡片 |

### CCE 集群监控

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/cce-monitoring/config` | 获取配置 |
| GET | `/api/v1/cce-monitoring/clusters` | 集群列表 |
| GET | `/api/v1/cce-monitoring/query` | 查询即时指标 |
| GET | `/api/v1/cce-monitoring/query-charts` | 查询趋势图数据 |
| GET | `/api/v1/cce-monitoring/query-all` | 查询全部集群 |

### GPU 集群监控

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/gpu-monitoring/has-inspection` | 获取 HAS 巡检数据 |
| POST | `/api/v1/gpu-monitoring/has-inspection/collect` | 触发巡检采集任务 |
| POST | `/api/v1/gpu-monitoring/bottom-card-time/query` | 即时查询 bottom 卡时 |
| POST | `/api/v1/gpu-monitoring/bottom-card-time/analyze` | 生成 bottom 卡时分析报告 |

### CMDB 管理

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/cmdb/servers` | 服务器列表 |
| GET | `/api/v1/cmdb/servers/{hostname}` | 服务器详情 |
| GET | `/api/v1/cmdb/instances` | 实例列表 |
| POST | `/api/v1/cmdb/import` | 导入 Excel |
| POST | `/api/v1/cmdb/sync` | AMIS API 同步 |
| POST | `/api/v1/cmdb/bce/sync` | BCE 数据同步 |

### 监控分析

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/v1/pfs/query` | PFS 指标查询 |
| POST | `/api/v1/pfs/export` | PFS 数据导出（异步） |
| POST | `/api/v1/prometheus/cluster/metrics` | Prometheus 集群指标 |
| POST | `/api/v1/monitoring/bcc/analyze` | BCC 监控分析 |
| POST | `/api/v1/monitoring/bos/analyze` | BOS 存储分析 |
| POST | `/api/v1/eip/analyze` | EIP 分析 |

### 资源分析

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/v1/resource/analyze` | 提交资源分析任务（异步） |
| GET | `/api/v1/resource/tasks` | 任务列表 |

### 运营分析

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/v1/operational/analyze` | Excel 数据分析（异步） |
| POST | `/api/v1/operational/analyze-api` | API 查询分析（异步） |

完整 API 文档：`http://服务器IP:8089/docs`

---

## 🐳 常用 Docker 命令

```bash
# 查看容器
docker ps
docker ps -a

# 进入容器
docker exec -it cluster-backend-api bash
docker exec -it cluster-backend-worker bash
docker exec -it cluster-mysql bash

# 查看日志
docker logs -f cluster-backend-api
docker logs -f cluster-backend-worker

# 重启
docker restart cluster-backend-api
docker restart cluster-backend-worker

# 服务管理
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml down -v
# 清理镜像
docker image prune -a -f
docker builder prune --all --force


# 常用部署命令
unzip /op-web-simple.zip && rm -rf /op-web-simple.zip /__MACOSX && cd /op-web-simple && vim .env


---

## 📁 目录结构

```
op-web-simple/
├── backend/
│   ├── app/
│   │   ├── api/v1/             # API 路由
│   │   │   ├── users.py        # 用户认证与管理
│   │   │   ├── endpoints/alerts.py  # 硬件告警
│   │   │   ├── apiserver_alerts.py  # APIServer 告警
│   │   │   ├── cce_monitoring.py    # CCE 集群监控
│   │   │   ├── gpu_monitoring.py    # GPU 集群监控
│   │   │   ├── cmdb.py         # CMDB 资源管理
│   │   │   ├── pfs.py          # PFS 监控
│   │   │   ├── prometheus.py   # Prometheus 集群监控
│   │   │   ├── resource.py     # 资源分析
│   │   │   ├── operational.py  # 运营分析
│   │   │   ├── monitoring.py   # BCC/BOS 监控
│   │   │   ├── eip.py          # EIP 分析
│   │   │   ├── ai_chat.py      # AI 对话
│   │   │   └── config.py       # 系统配置
│   │   ├── core/               # 核心组件（config/security/deps/redis）
│   │   ├── models/             # 数据模型
│   │   ├── schemas/            # Pydantic 模型
│   │   └── services/           # 业务逻辑
│   │       ├── alert/          # 硬件告警服务
│   │       ├── apiserver_alert_service.py
│   │       ├── cce_monitoring_service.py
│   │       ├── gpu_monitoring_service.py
│   │       ├── task_queue_service.py  # Redis 队列服务
│   │       ├── icafe/          # iCafe 服务
│   │       └── ai/             # AI 服务
│   ├── worker.py               # Worker 主入口
│   └── main.py                 # API 应用入口
├── frontend/
│   └── src/
│       ├── api/                # API 接口封装
│       ├── views/
│       │   ├── alerts/         # 硬件告警页面
│       │   ├── apiserver/      # APIServer 监控页面
│       │   ├── cce-monitoring/ # CCE 集群监控页面
│       │   ├── gpu-monitoring/ # GPU 集群监控页面
│       │   ├── admin/          # 用户管理、审计日志
│       │   └── monitoring/     # PFS/BCC/BOS 监控
│       ├── components/config/  # 配置组件
│       └── router/             # 路由配置
├── docker-compose.prod.yml     # 外网部署
├── docker-compose.offline.yml  # 内网离线部署
├── deploy.sh                   # 外网部署脚本
└── pack-offline.sh             # 离线打包脚本
```

---

## 📞 访问地址

| 服务 | 地址 |
|-----|------|
| 前端界面 | http://服务器IP:8089 |
| API 文档 | http://服务器IP:8089/docs |

---

## 📄 许可证

本项目仅供内部使用。
