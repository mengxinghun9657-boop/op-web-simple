# 集群管理平台 - 后端 Dockerfile
# 使用华为云 Python 3.10 镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖（使用阿里云源加速）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 先安装基础工具和 Docker CLI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 添加 Docker 源（使用华为云镜像）并安装 Docker CLI
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.huaweicloud.com/docker-ce/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（优先清华源，失败时回退官方 PyPI）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    || pip install --no-cache-dir -r requirements.txt -i https://pypi.org/simple

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads results logs data/reports config

# 暴露端口
EXPOSE 8000

# 健康检查（由docker-compose管理，这里注释掉）
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# 启动命令（使用 gunicorn 生产环境）
# 根据环境调整 worker 数量：
# - 内网环境（192GB RAM）：4 workers，充分利用资源
# - 外网环境（8GB RAM）：2 workers，避免资源不足
# 使用环境变量 WORKERS 控制，默认 4
# timeout 设置为 600 秒（10 分钟），适应 lifespan 启动时间（文件监控等待 360 秒 + AI 初始化等）
CMD ["sh", "-c", "gunicorn main:app -w ${WORKERS:-4} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 600 --graceful-timeout 120 --access-logfile - --error-logfile -"]
