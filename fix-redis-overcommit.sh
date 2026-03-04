#!/bin/bash

# 修复Redis内存过量分配警告

echo "🔧 修复Redis内存过量分配设置..."

# 1. 临时生效（立即生效，重启后失效）
echo "📝 设置临时配置..."
sudo sysctl vm.overcommit_memory=1

# 2. 永久生效（写入配置文件，重启后仍然有效）
echo "📝 设置永久配置..."
if grep -q "vm.overcommit_memory" /etc/sysctl.conf; then
    echo "⚠️  配置已存在，更新中..."
    sudo sed -i 's/^vm.overcommit_memory.*/vm.overcommit_memory = 1/' /etc/sysctl.conf
else
    echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
fi

# 3. 重新加载配置
echo "🔄 重新加载系统配置..."
sudo sysctl -p

# 4. 验证配置
echo "✅ 验证配置..."
current_value=$(sysctl vm.overcommit_memory | awk '{print $3}')
if [ "$current_value" = "1" ]; then
    echo "✅ 配置成功！vm.overcommit_memory = $current_value"
else
    echo "❌ 配置失败！当前值: $current_value"
    exit 1
fi

# 5. 重启Redis容器以清除警告
echo "🔄 重启Redis容器..."
docker compose -f docker-compose.prod.yml restart redis

# 6. 等待Redis启动
echo "⏳ 等待Redis启动..."
sleep 5

# 7. 检查Redis日志
echo "📋 检查Redis日志（最近20行）..."
docker compose -f docker-compose.prod.yml logs --tail=20 redis

echo ""
echo "✅ 修复完成！"
echo ""
echo "💡 说明："
echo "  - vm.overcommit_memory = 1 表示允许内存过量分配"
echo "  - 这是Redis官方推荐的配置"
echo "  - 配置已永久保存到 /etc/sysctl.conf"
echo "  - 系统重启后仍然有效"
