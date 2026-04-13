#!/bin/bash
# 如流回调服务安装脚本

set -e

echo "========================================"
echo "如流回调服务安装脚本"
echo "========================================"

# 检查root权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用root权限运行此脚本"
    exit 1
fi

# 安装目录
INSTALL_DIR="/data/ruliu_callback"
LOG_DIR="/var/log/ruliu-callback"

echo ""
echo "1. 创建安装目录..."
mkdir -p $INSTALL_DIR
mkdir -p $LOG_DIR

echo ""
echo "2. 安装系统依赖..."
apt-get update || true  # 忽略仓库错误
apt-get install -y python3 python3-venv python3-pip || {
    echo "警告: 部分依赖安装失败，尝试继续..."
}

echo ""
echo "3. 创建Python虚拟环境..."
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate

echo ""
echo "4. 安装Python依赖..."
pip install --upgrade pip
pip install flask pymysql pycryptodome requests cryptography

echo ""
echo "5. 复制服务文件..."
# 假设当前目录是项目目录
cp ruliu_callback.py $INSTALL_DIR/
cp webhook_sender.py $INSTALL_DIR/
cp ruliu-callback.service /etc/systemd/system/
cp webhook-sender.service /etc/systemd/system/

echo ""
echo "6. 设置权限..."
chmod +x $INSTALL_DIR/ruliu_callback.py
chmod +x $INSTALL_DIR/webhook_sender.py
chown -R root:root $INSTALL_DIR
chown -R root:root $LOG_DIR

echo ""
echo "7. 重新加载systemd..."
systemctl daemon-reload

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "请按以下步骤配置服务:"
echo ""
echo "===== 回调服务配置 ====="
echo "1. 编辑回调服务配置:"
echo "   vim /etc/systemd/system/ruliu-callback.service"
echo ""
echo "2. 修改回调服务环境变量:"
echo "   - RULIU_TOKEN: T2yJvnNier"
echo "   - RULIU_ENCODING_AES_KEY: VrBuaSxT9P5Z6bfdHneKv0"
echo "   - MYSQL_PASSWORD: Zhang~~1"
echo "   - RULIU_PORT: 8120"
echo ""
echo "===== Webhook发送服务配置（可选） ====="
echo "3. 编辑Webhook服务配置:"
echo "   vim /etc/systemd/system/webhook-sender.service"
echo ""
echo "4. 修改Webhook环境变量（用于发送回复消息）:"
echo "   - WEBHOOK_URL: http://apiin.im.baidu.com/api/v1/robot/msg/groupmsgsend"
echo "   - WEBHOOK_ACCESS_TOKEN: 你的Webhook Token"
echo ""
echo "===== 启动服务 ====="
echo "5. 启动回调服务:"
echo "   systemctl start ruliu-callback"
echo "   systemctl enable ruliu-callback"
echo ""
echo "6. 启动Webhook发送服务（可选）:"
echo "   systemctl start webhook-sender"
echo "   systemctl enable webhook-sender"
echo ""
echo "===== 查看状态 ====="
echo "7. 查看服务状态:"
echo "   systemctl status ruliu-callback"
echo "   systemctl status webhook-sender"
echo ""
echo "8. 查看日志:"
echo "   journalctl -u ruliu-callback -f"
echo "   journalctl -u webhook-sender -f"
echo ""
echo "回调地址: http://your-server-ip:8120/ruliu/callback"
echo ""
