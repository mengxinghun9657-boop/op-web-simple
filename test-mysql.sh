#!/bin/bash
# MySQL 连接测试脚本
# 用于诊断内网部署时的 MySQL 连接问题

MYSQL_PASSWORD="Zhang~~1"

echo "╔══════════════════════════════════════════╗"
echo "║     MySQL 连接诊断测试                    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "=== 测试 1: MySQL Healthcheck（容器内部）==="
if docker compose -f docker-compose.prod.yml exec mysql mysqladmin ping -h localhost -u root -p"$MYSQL_PASSWORD" --silent 2>/dev/null; then
    echo "✓ MySQL Healthcheck 通过"
else
    echo "✗ MySQL Healthcheck 失败"
fi

echo ""
echo "=== 测试 2: 后端到 MySQL 的网络连接 ==="
if docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import pymysql
import sys
try:
    conn = pymysql.connect(
        host='mysql',
        port=3306,
        user='root',
        password='$MYSQL_PASSWORD',
        database='cluster_management',
        connect_timeout=10
    )
    conn.close()
    print('✓ 连接成功')
    sys.exit(0)
except Exception as e:
    print(f'✗ 连接失败: {e}')
    sys.exit(1)
" 2>&1; then
    echo "✓ 后端可以连接 MySQL"
else
    echo "✗ 后端无法连接 MySQL（Connection refused）"
fi

echo ""
echo "=== 测试 3: MySQL 初始化状态 ==="
TABLE_COUNT=$(docker compose -f docker-compose.prod.yml exec -T mysql mysql -u root -p"$MYSQL_PASSWORD" cluster_management -se "
SELECT COUNT(*) 
FROM information_schema.tables 
WHERE table_schema = 'cluster_management';
" 2>/dev/null)

if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✓ MySQL 已初始化（表数量: $TABLE_COUNT）"
else
    echo "✗ MySQL 还在初始化中（表数量: ${TABLE_COUNT:-0}）"
fi

echo ""
echo "=== 测试 4: 检查关键表是否存在 ==="
docker compose -f docker-compose.prod.yml exec -T mysql mysql -u root -p"$MYSQL_PASSWORD" cluster_management -se "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'cluster_management' 
ORDER BY table_name 
LIMIT 10;
" 2>/dev/null

echo ""
echo "=== 测试 5: MySQL 进程状态 ==="
docker compose -f docker-compose.prod.yml exec mysql sh -c "ps aux | grep mysqld | grep -v grep"

echo ""
echo "=== 测试 6: MySQL 网络监听状态 ==="
docker compose -f docker-compose.prod.yml exec mysql sh -c "netstat -tlnp 2>/dev/null | grep 3306 || ss -tlnp | grep 3306"

echo ""
echo "=== 测试 7: 容器网络连通性 ==="
echo "后端容器 IP:"
docker compose -f docker-compose.prod.yml exec backend hostname -i
echo "MySQL 容器 IP:"
docker compose -f docker-compose.prod.yml exec mysql hostname -i
echo "后端 ping MySQL:"
docker compose -f docker-compose.prod.yml exec backend ping -c 2 mysql 2>&1 | grep "packets transmitted"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     测试完成                              ║"
echo "╚══════════════════════════════════════════╝"
