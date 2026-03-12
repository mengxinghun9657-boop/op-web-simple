# 集群管理平台 - 前端 Dockerfile（多阶段构建）

# 构建阶段 - 使用华为云镜像源
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18-alpine AS builder

WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 配置 npm 使用淘宝镜像源（解决外网网络问题）
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖
# 使用 npm install 代替 npm ci，更宽容的依赖安装方式
RUN npm install --production=false

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# 生产阶段 - 使用华为云 Nginx 镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:1.25-alpine

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
