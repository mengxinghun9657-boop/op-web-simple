#!/bin/bash
# 飞书告警机器人一键部署脚本
# 复用如流的环境变量配置

set -e

echo "========================================"
echo "飞书告警机器人部署脚本"
echo "========================================"

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 配置目录
INSTALL_DIR="/opt/feishu-alert-bot"
LOG_DIR="/var/log/feishu-alert-bot"
SERVICE_NAME="feishu-alert-bot"

echo ""
echo "步骤1: 创建目录..."
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR

echo ""
echo "步骤2: 检查如流环境变量..."

# 尝试从如流服务读取环境变量
if [ -f /opt/ruliu-callback/.env ]; then
    echo "发现如流环境变量文件，复用MySQL配置..."
    source /opt/ruliu-callback/.env
elif [ -f /etc/systemd/system/ruliu-callback.service ]; then
    echo "发现如流systemd服务，尝试提取环境变量..."
    # 从service文件提取环境变量
    MYSQL_HOST=$(grep MYSQL_HOST /etc/systemd/system/ruliu-callback.service | cut -d= -f2 || echo "localhost")
    MYSQL_PORT=$(grep MYSQL_PORT /etc/systemd/system/ruliu-callback.service | cut -d= -f2 || echo "3306")
    MYSQL_USER=$(grep MYSQL_USER /etc/systemd/system/ruliu-callback.service | cut -d= -f2 || echo "root")
    MYSQL_PASSWORD=$(grep MYSQL_PASSWORD /etc/systemd/system/ruliu-callback.service | cut -d= -f2 || echo "")
    MYSQL_DATABASE=$(grep MYSQL_DATABASE /etc/systemd/system/ruliu-callback.service | cut -d= -f2 || echo "cluster_manager")
else
    echo "未找到如流配置，使用默认MySQL配置..."
    MYSQL_HOST="localhost"
    MYSQL_PORT="3306"
    MYSQL_USER="root"
    MYSQL_PASSWORD=""
    MYSQL_DATABASE="cluster_manager"
fi

echo ""
echo "步骤3: 创建环境变量文件..."

cat > $INSTALL_DIR/.env << EOF
# ========================================
# 飞书告警机器人环境变量
# 复用如流的MySQL配置
# ========================================

# 飞书应用配置（必填）
# 从飞书开放平台获取: https://open.feishu.cn/app/
APP_ID=cli_a9563738edbe9bce
APP_SECRET=YKScjtqsyoQSnGh0evS3IcSzJquTP0fs
BASE_DOMAIN=https://open.feishu.cn

# MySQL配置（复用如流配置）
MYSQL_HOST=${MYSQL_HOST:-localhost}
MYSQL_PORT=${MYSQL_PORT:-3306}
MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
MYSQL_DATABASE=${MYSQL_DATABASE:-cluster_manager}
EOF

echo "环境变量文件已创建: $INSTALL_DIR/.env"
echo ""
echo "当前MySQL配置:"
echo "  Host: ${MYSQL_HOST:-localhost}"
echo "  Port: ${MYSQL_PORT:-3306}"
echo "  User: ${MYSQL_USER:-root}"
echo "  Database: ${MYSQL_DATABASE:-cluster_manager}"

echo ""
echo "步骤4: 复制机器人代码..."

# 检查代码文件是否存在
if [ -f "alert_bot.py" ]; then
    cp alert_bot.py $INSTALL_DIR/
    echo "✓ 已复制 alert_bot.py"
else
    echo "✗ 未找到 alert_bot.py，请确保在当前目录"
    exit 1
fi

echo ""
echo "步骤5: 安装Python依赖..."
pip3 install -q lark-oapi pymysql 2>/dev/null || pip install -q lark-oapi pymysql

echo ""
echo "步骤6: 创建systemd服务..."

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Feishu Alert Bot
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=/usr/bin/python3 $INSTALL_DIR/alert_bot.py
Restart=always
RestartSec=10
KillMode=process
StandardOutput=append:$LOG_DIR/bot.log
StandardError=append:$LOG_DIR/bot.error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ 已创建服务: $SERVICE_NAME"

echo ""
echo "步骤7: 设置权限..."
chmod 644 /etc/systemd/system/$SERVICE_NAME.service
chmod 600 $INSTALL_DIR/.env
chmod 755 $INSTALL_DIR/alert_bot.py

echo ""
echo "步骤8: 重载systemd..."
systemctl daemon-reload

echo ""
echo "========================================"
echo "部署完成!"
echo "========================================"
echo ""
echo "启动命令:"
echo "  sudo systemctl start $SERVICE_NAME"
echo ""
echo "查看状态:"
echo "  sudo systemctl status $SERVICE_NAME"
echo ""
echo "查看日志:"
echo "  tail -f $LOG_DIR/bot.log"
echo ""
echo "设置开机自启:"
echo "  sudo systemctl enable $SERVICE_NAME"
echo ""
echo "注意:"
echo "1. 请确认 $INSTALL_DIR/.env 中的飞书配置正确"
echo "2. 在飞书开放平台发布应用"
echo "3. 将机器人添加到飞书群"
echo ""
