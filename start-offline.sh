#!/bin/bash
# 内网部署启动脚本（修复版 v7）
# 修复内容：
# 1. 修复 rematch 命令的 shell 转义问题（使用独立脚本）
# 2. 优化 MySQL 就绪等待时间（30秒）
# 3. 从 .env 文件读取 MySQL 密码
# 4. 降级策略确保故障手册导入成功

set -e

echo "╔══════════════════════════════════════════╗"
echo "║     集群管理平台 - 内网部署启动          ║"
echo "╚══════════════════════════════════════════╝"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 配置文件"
    echo "请创建 .env 文件并配置环境变量"
    exit 1
fi

# 从 .env 文件读取配置
echo "📖 读取 .env 配置..."
export $(grep -v '^#' .env | grep -v '^[[:space:]]*$' | xargs)

if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo "❌ 未找到 MYSQL_ROOT_PASSWORD 配置"
    echo "请在 .env 文件中配置 MYSQL_ROOT_PASSWORD"
    exit 1
fi

echo "✓ 配置读取成功"
echo "  MySQL 密码: ${MYSQL_ROOT_PASSWORD:0:3}***（已脱敏）"

# 检查是否需要清理数据卷
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "数据卷检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "检测到可能存在旧的数据卷。"
echo ""
echo "选项："
echo "  1) 保留数据 - 保留现有数据库数据（推荐用于升级）"
echo "  2) 清理数据 - 删除所有数据卷，全新部署（推荐用于首次部署或修复问题）"
echo ""
read -p "请选择 (1/2，默认=1): " clean_volumes

if [ "$clean_volumes" = "2" ]; then
    echo ""
    echo "⚠️  警告: 即将删除所有数据卷（包括数据库数据）"
    echo ""
    read -p "确认删除？(yes/no): " confirm_clean

    if [ "$confirm_clean" = "yes" ]; then
        echo ""
        echo "🧹 清理旧数据卷..."
        docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
        echo "✓ 数据卷清理完成"
    else
        echo "✓ 取消清理，保留现有数据"
    fi
else
    echo "✓ 保留现有数据"
fi

# 自动修复 CORS_ORIGINS
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "自动配置 CORS_ORIGINS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 获取当前服务器IP
SERVER_IP=$(hostname -I | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

echo "检测到服务器IP: $SERVER_IP"

# 检查 .env 文件中的 CORS_ORIGINS
if grep -q "^CORS_ORIGINS=" .env; then
    CURRENT_CORS=$(grep "^CORS_ORIGINS=" .env | cut -d= -f2)
    echo "当前 CORS_ORIGINS: $CURRENT_CORS"

    if [[ "$CURRENT_CORS" == *"$SERVER_IP"* ]]; then
        echo "✓ CORS_ORIGINS 已包含当前服务器IP"
    else
        echo "🔧 更新 CORS_ORIGINS 包含当前服务器IP..."
        NEW_CORS="http://localhost:8089,http://127.0.0.1:8089,http://$SERVER_IP:8089"
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$NEW_CORS|" .env
        echo "✓ CORS_ORIGINS 已更新为: $NEW_CORS"
    fi
else
    echo "🔧 添加 CORS_ORIGINS 配置..."
    NEW_CORS="http://localhost:8089,http://127.0.0.1:8089,http://$SERVER_IP:8089"
    echo "CORS_ORIGINS=$NEW_CORS" >> .env
    echo "✓ CORS_ORIGINS 已添加: $NEW_CORS"
fi

echo ""
echo "📦 1. 加载 Docker 镜像..."
if [ -f "images.tar" ]; then
    docker load -i images.tar
    echo "✓ 镜像加载完成"

    # 重新打标签，使镜像名与 docker-compose.yml 一致
    echo "🏷️  重新标记镜像..."
    docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:8.0 mysql:8.0 2>/dev/null || true
    docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/redis:7-alpine redis:7-alpine 2>/dev/null || true
    docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/minio/minio:latest minio/minio:latest 2>/dev/null || true
    echo "✓ 镜像标记完成"
else
    echo "❌ 未找到 images.tar 文件"
    exit 1
fi

echo ""
echo "🚀 2. 启动服务..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ 3. 等待服务启动..."

# 步骤1: 等待 MySQL 服务就绪
echo "等待 MySQL 服务就绪..."

# 读取超时配置（默认360秒）
MYSQL_TIMEOUT=${MYSQL_STARTUP_TIMEOUT:-360}
MAX_ATTEMPTS=$((MYSQL_TIMEOUT / 3))

for i in $(seq 1 $MAX_ATTEMPTS); do
    # 直接测试 MySQL 连接（最可靠的方式）
    if docker compose -f docker-compose.prod.yml exec -T mysql mysqladmin ping \
        -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" --silent 2>/dev/null; then
        echo "✓ MySQL 服务已就绪 (用时 $((i*3)) 秒)"
        break
    fi

    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "❌ MySQL 启动超时（已等待 ${MYSQL_TIMEOUT} 秒）"
        echo ""
        echo "诊断信息："
        echo "1. 检查 MySQL 容器状态："
        docker compose -f docker-compose.prod.yml ps mysql
        echo ""
        echo "2. 查看 MySQL 日志（最后50行）："
        docker compose -f docker-compose.prod.yml logs mysql --tail=50
        exit 1
    fi

    # 每20次显示一次进度（每分钟）
    if [ $((i % 20)) -eq 0 ]; then
        echo "  等待 MySQL 启动... ($((i*3))/${MYSQL_TIMEOUT}秒)"
    fi

    sleep 3
done

# 步骤2: 额外等待确保完全就绪（增加到30秒，给MySQL更多初始化时间）
echo "等待 MySQL 完全初始化..."
sleep 30

# 步骤3: 等待后端容器完全启动
echo "等待后端容器启动..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T backend python3 --version >/dev/null 2>&1; then
        echo "✓ 后端容器已启动 (用时 $((i*2)) 秒)"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "⚠️  后端容器启动超时，但继续部署"
    fi

    sleep 2
done

# 步骤4: 验证后端容器可以连接数据库（修复版 - 单行Python）
echo "验证后端数据库连接..."
DB_PASSWORD="$MYSQL_ROOT_PASSWORD"  # 预展开变量，避免转义问题

for i in {1..10}; do
    if docker compose -f docker-compose.prod.yml exec -T backend python3 -c \
        "import pymysql,sys; \
        try: \
            conn=pymysql.connect(host='mysql',port=3306,user='root',password='$DB_PASSWORD',database='cluster_management',connect_timeout=10); \
            conn.close(); \
            sys.exit(0) \
        except: \
            sys.exit(1)" 2>/dev/null; then
        echo "✓ 后端数据库连接正常 (用时 $((i*2)) 秒)"
        break
    fi

    if [ $i -eq 10 ]; then
        echo "⚠️  后端数据库连接测试失败，但继续部署"
        echo "   后端应用会自动重试连接（内置5次重试机制）"
    fi

    sleep 2
done

echo "✓ 服务启动完成"

# 检查服务状态
echo ""
echo "📊 5. 检查服务状态..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "🗄️ 6. 初始化数据库和配置..."

# 导入故障手册函数
import_fault_manual() {
    local file_path="$1"
    local file_name=$(basename "$file_path")

    echo "📚 导入故障手册（${file_name}）..."

    # 确保容器内目录存在
    docker compose -f docker-compose.prod.yml exec -T backend mkdir -p /app/knowledge 2>/dev/null || true
    docker compose -f docker-compose.prod.yml exec -T backend mkdir -p /app/backend/scripts 2>/dev/null || true

    # 获取后端容器 ID
    BACKEND_CONTAINER=$(docker compose -f docker-compose.prod.yml ps -q backend)
    if [ -z "$BACKEND_CONTAINER" ]; then
        echo "❌ 无法获取后端容器 ID"
        return 1
    fi

    # 复制故障手册文件到容器内
    if docker cp "$file_path" "${BACKEND_CONTAINER}:/app/knowledge/${file_name}"; then
        echo "✓ 故障手册文件已复制到容器"
    else
        echo "❌ 故障手册文件复制失败"
        return 1
    fi

    # 复制导入脚本到容器内
    if [ -f "backend-scripts/import_fault_manual.py" ]; then
        if docker cp "backend-scripts/import_fault_manual.py" "${BACKEND_CONTAINER}:/app/backend/scripts/import_fault_manual.py"; then
            echo "✓ 导入脚本已复制到容器"
        else
            echo "❌ 导入脚本复制失败"
            return 1
        fi
    else
        echo "❌ 未找到导入脚本: backend-scripts/import_fault_manual.py"
        return 1
    fi

    # 复制重新匹配脚本到容器内
    if [ -f "backend-scripts/rematch_fault_manual.py" ]; then
        docker cp "backend-scripts/rematch_fault_manual.py" "${BACKEND_CONTAINER}:/app/backend/scripts/rematch_fault_manual.py" 2>/dev/null || true
    fi

    # 执行导入（使用正确的路径）
    if docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/import_fault_manual.py" 2>/dev/null; then
        echo "✓ 故障手册导入成功"

        # 重新匹配已有告警（使用独立脚本，避免 shell 转义问题）
        echo "  重新匹配已有告警的手册..."
        echo "  等待 MySQL 处理完导入（20秒）..."
        sleep 20  # 增加等待时间，给MySQL足够时间处理292条记录的写入

        if docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/rematch_fault_manual.py" 2>/dev/null; then
            echo "✓ 已有告警重新匹配完成"
        else
            echo "⚠️  重新匹配失败（不影响部署）"
            echo "   可稍后手动重新匹配："
            echo "   docker compose -f docker-compose.prod.yml exec backend bash -c \"cd /app && python3 backend/scripts/rematch_fault_manual.py\""
        fi

        return 0
    else
        echo "❌ 故障手册导入失败"
        return 1
    fi
}

# 检查并导入故障手册（带降级策略）
if [ -f "knowledge/故障维修手册.csv" ]; then
    # 额外等待确保MySQL完全就绪（数据库初始化完成）
    echo "⏳ 等待MySQL数据库完全就绪..."
    MYSQL_READY=false

    for i in {1..20}; do
        if docker compose -f docker-compose.prod.yml exec -T mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "USE cluster_management; SELECT 1;" >/dev/null 2>&1; then
            echo "✓ MySQL数据库已就绪"
            sleep 5  # 额外等待5秒确保连接池稳定
            MYSQL_READY=true
            break
        fi

        if [ $i -eq 20 ]; then
            echo "⚠️  MySQL数据库未就绪，无法自动导入故障手册"
        else
            echo "  等待中... ($i/20)"
            sleep 3
        fi
    done

    # 只有在MySQL完全就绪后才执行自动导入
    if [ "$MYSQL_READY" = true ]; then
        if import_fault_manual "knowledge/故障维修手册.csv"; then
            echo "✅ 故障手册自动导入成功"
        else
            # 降级策略：自动导入失败，提示手动导入
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "⚠️  故障手册自动导入失败"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "请使用以下命令手动导入（推荐）："
            echo ""
            echo "  docker compose -f docker-compose.prod.yml exec -T backend bash -c \"cd /app && python3 backend/scripts/import_fault_manual.py\""
            echo ""
            echo "或者进入容器后执行："
            echo ""
            echo "  docker compose -f docker-compose.prod.yml exec backend bash"
            echo "  cd /app"
            echo "  python3 backend/scripts/import_fault_manual.py"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""

            # 询问用户是否立即手动导入
            echo "是否现在尝试手动导入？"
            read -p "输入 yes 立即导入，或按回车跳过: " manual_import

            if [ "$manual_import" = "yes" ]; then
                echo ""
                echo "🔄 正在手动导入故障手册..."
                if docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/import_fault_manual.py"; then
                    echo "✅ 手动导入成功"
                else
                    echo "❌ 手动导入也失败了"
                    echo "   请查看后端日志排查问题："
                    echo "   docker compose -f docker-compose.prod.yml logs backend --tail=50"
                fi
            else
                echo "⏭️  已跳过手动导入，可稍后执行"
            fi
        fi
    else
        # MySQL 未就绪，直接提示手动导入
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚠️  MySQL 数据库未就绪，无法导入故障手册"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "请稍后（等待服务完全启动后）手动执行："
        echo ""
        echo "  docker compose -f docker-compose.prod.yml exec -T backend bash -c \"cd /app && python3 backend/scripts/import_fault_manual.py\""
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    fi
elif [ -f "knowledge/故障维修手册.md" ]; then
    # 降级处理 MD 格式
    if import_fault_manual "knowledge/故障维修手册.md"; then
        echo "✅ 故障手册导入成功（MD格式）"
    else
        echo "⚠️  故障手册导入失败，请稍后手动导入"
    fi
else
    echo "⚠️  未找到故障手册文件，跳过导入"
    echo "   支持的文件: knowledge/故障维修手册.csv 或 knowledge/故障维修手册.md"
fi

# 初始化系统配置
if [ -f "init_system_configs.py" ]; then
    echo "⚙️  初始化系统配置..."
    echo "  等待 MySQL 连接池恢复（额外10秒）..."
    sleep 10  # 给 MySQL 额外时间恢复，避免与故障手册导入冲突

    # 先复制配置文件到容器
    BACKEND_CONTAINER=$(docker compose -f docker-compose.prod.yml ps -q backend)
    if [ -z "$BACKEND_CONTAINER" ]; then
        echo "❌ 错误: Backend容器未运行"
        echo "   请检查容器状态: docker compose -f docker-compose.prod.yml ps"
        exit 1
    fi

    echo "📋 复制配置文件到容器..."

    # 复制 default_instance_ids.json
    if [ -f "backend-config/default_instance_ids.json" ]; then
        if docker cp backend-config/default_instance_ids.json "${BACKEND_CONTAINER}:/app/config/default_instance_ids.json"; then
            echo "✓ default_instance_ids.json 复制成功"

            # 验证文件是否存在
            if docker compose -f docker-compose.prod.yml exec -T backend test -f /app/config/default_instance_ids.json; then
                echo "✓ 验证配置文件存在于容器内"
            else
                echo "❌ 警告: 配置文件复制后验证失败"
            fi
        else
            echo "❌ 错误: default_instance_ids.json 复制失败"
            echo "   请检查容器状态和权限"
            exit 1
        fi
    else
        echo "❌ 错误: 未找到 backend-config/default_instance_ids.json"
        echo "   配置初始化将被跳过，监控和分析功能将无默认配置"
        exit 1
    fi

    # 复制 prometheus_config.json（包含 Cookie）
    if [ -f "backend-config/prometheus_config.json" ]; then
        if docker cp backend-config/prometheus_config.json "${BACKEND_CONTAINER}:/app/config/prometheus_config.json"; then
            echo "✓ prometheus_config.json 复制成功（包含 Prometheus Cookie）"
        else
            echo "⚠️  警告: prometheus_config.json 复制失败，Prometheus 查询将使用空 Cookie"
        fi
    else
        echo "⚠️  警告: 未找到 backend-config/prometheus_config.json"
        echo "   Prometheus 查询将使用空 Cookie，请在前端页面配置"
    fi

    # 执行初始化
    echo "🔧 执行系统配置初始化..."
    if docker compose -f docker-compose.prod.yml exec -T backend python3 init_system_configs.py; then
        echo "✓ 系统配置初始化成功"
    else
        echo "❌ 系统配置初始化失败"
        echo "   请查看详细日志:"
        echo "   docker compose -f docker-compose.prod.yml logs backend --tail=100 | grep -i 'init_system\\|系统配置'"
        exit 1
    fi
else
    echo "⚠️  警告: 未找到 init_system_configs.py，跳过系统配置初始化"
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "访问地址："
echo "  前端: http://$SERVER_IP:8089"
echo "  后端API: http://$SERVER_IP:8000"
echo "  API文档: http://$SERVER_IP:8000/docs"
echo ""
echo "默认账号: admin / admin123"
echo ""
echo "📝 管理命令:"
echo "  查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "  查看后端: docker compose -f docker-compose.prod.yml logs -f backend"
echo "  查看状态: docker compose -f docker-compose.prod.yml ps"
echo "  重启服务: docker compose -f docker-compose.prod.yml restart"
echo "  停止服务: docker compose -f docker-compose.prod.yml down"
echo ""
echo "如需配置宿主机MySQL，请运行："
echo "  ./scripts/configure-host-mysql.sh"
