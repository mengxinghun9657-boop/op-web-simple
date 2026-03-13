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

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用清华源加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

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
CMD ["sh", "-c", "gunicorn main:app -w ${WORKERS:-4} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 300 --graceful-timeout 120 --access-logfile - --error-logfile -"]
