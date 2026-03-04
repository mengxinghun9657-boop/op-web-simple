#!/bin/bash

# 后端启动脚本

echo "🚀 启动集群管理平台后端服务..."

# 切换到backend目录
cd "$(dirname "$0")"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查是否有虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📚 安装依赖..."
pip install -r requirements.txt

# 创建必要的目录
mkdir -p uploads results logs

# 启动服务
echo "✅ 启动FastAPI服务..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
