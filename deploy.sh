#!/bin/bash

##############################################################################
# 生产环境部署脚本 - 一键部署
# 使用方法：./deploy.sh [--clean]
# 参数说明：
#   --clean  完全清理模式（删除镜像、卷、缓存）
##############################################################################

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 解析参数
CLEAN_MODE=false
if [ "$1" = "--clean" ]; then
    CLEAN_MODE=true
fi

echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════╗
║     集群管理平台 - 生产环境部署器        ║
╚══════════════════════════════════════════╝
EOF
echo -e "${NC}"

# 检查配置文件
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ 未找到 .env 配置文件${NC}"
    echo ""
    echo "请先创建配置文件:"
    echo "  1. cp deploy/.env.example .env"
    echo "  2. vi .env  # 编辑配置，修改所有密码和密钥"
    echo ""
    exit 1
fi

# 安全检查
echo -e "${YELLOW}⚠️  生产环境部署前检查...${NC}"
echo ""

# 加载环境变量
source .env 2>/dev/null || true

# 检查必要配置
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo -e "${RED}✗ MYSQL_ROOT_PASSWORD 未配置${NC}"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-secret-key-change-me" ]; then
    echo -e "${RED}✗ 请修改 .env 中的 SECRET_KEY${NC}"
    echo "  生成方法: openssl rand -hex 32"
    exit 1
fi

echo -e "${GREEN}✓ 配置检查通过${NC}"
echo ""
echo "当前配置："
echo "  MySQL用户: ${MYSQL_USER:-cluster_user}"
echo "  MinIO用户: ${MINIO_ROOT_USER:-admin}"
echo "  CORS: ${CORS_ORIGINS:-http://localhost:8089}"
echo ""

# 询问确认
if [ "$CLEAN_MODE" = true ]; then
    echo -e "${RED}⚠️  完全清理模式已启用！${NC}"
    echo ""
    echo -e "${YELLOW}即将执行以下操作：${NC}"
    echo "  1. 停止并删除所有容器"
    echo "  2. 删除所有相关镜像"
    echo "  3. 删除所有数据卷（⚠️ 数据将丢失）"
    echo "  4. 清理 Docker 构建缓存"
    echo "  5. 重新构建并启动服务"
    echo ""
    echo -e "${RED}警告：此操作将删除所有数据，包括数据库、文件存储等！${NC}"
    echo ""
    read -p "确认继续完全清理部署? (输入 'yes' 确认): " confirm
else
    echo -e "${YELLOW}即将部署到生产环境，这将：${NC}"
    echo "  1. 停止当前运行的容器"
    echo "  2. 删除旧的镜像"
    echo "  3. 清理构建缓存"
    echo "  4. 重新构建所有镜像"
    echo "  5. 启动生产环境"
    echo ""
    echo -e "${YELLOW}注意：数据卷将被保留${NC}"
    echo ""
    read -p "确认继续? (yes/no): " confirm
fi

if [ "$confirm" != "yes" ]; then
    echo "取消部署"
    exit 0
fi

echo ""
echo "🚀 开始部署..."
echo ""

# 停止当前运行的容器
echo "📦 停止当前容器..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

if [ "$CLEAN_MODE" = true ]; then
    # 完全清理模式
    echo ""
    echo "🗑️  删除数据卷..."
    docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true
    
    echo ""
    echo "🗑️  删除相关镜像（包括中间层）..."
    # 先用 compose 删除
    docker compose -f docker-compose.prod.yml down --rmi all 2>/dev/null || true
    # 再手动删除可能残留的镜像
    docker images | grep -E "op-web-backend|op-web-frontend|cluster-backend|cluster-frontend" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    # 清理所有悬空镜像
    echo ""
    echo "🗑️  清理悬空镜像..."
    docker image prune -a -f 2>/dev/null || true
    
    echo ""
    echo "🗑️  清理构建缓存（完全清理）..."
    # 使用 --all --force 清理所有构建缓存，不仅仅是悬空的
    docker builder prune --all --force 2>/dev/null || true
    
    echo ""
    echo "🗑️  清理未使用的网络..."
    docker network prune -f 2>/dev/null || true
else
    # 标准清理模式（保留数据卷）
    echo ""
    echo "🗑️  删除旧镜像..."
    docker compose -f docker-compose.prod.yml down --rmi all 2>/dev/null || true
    # 手动删除可能残留的镜像
    docker images | grep -E "op-web-backend|op-web-frontend|cluster-backend|cluster-frontend" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    echo ""
    echo "🗑️  清理构建缓存..."
    docker builder prune --all --force 2>/dev/null || true
fi

# 显示清理后的磁盘空间
echo ""
echo "💾 当前 Docker 磁盘使用情况:"
docker system df

# 构建镜像
echo ""
echo "🔨 构建 Docker 镜像..."
docker compose -f docker-compose.prod.yml build --no-cache

# 验证构建的镜像
echo ""
echo "🔍 验证构建的镜像..."
echo "检查本地源文件..."
if grep -q "is_cce = alert.is_cce_cluster" backend/app/services/alert/alert_processor.py; then
    echo -e "${GREEN}✓ 本地源文件正确${NC}"
else
    echo -e "${RED}✗ 本地源文件错误！${NC}"
    echo "请检查 backend/app/services/alert/alert_processor.py 文件"
    exit 1
fi

# 验证构建的镜像内容
echo ""
echo "� 验证构建的镜像内容..."
docker run --rm op-web-backend:latest python3 -c "
import sys
with open('/app/app/services/alert/alert_processor.py', 'r') as f:
    content = f.read()
    if 'is_cce = alert.is_cce_cluster' in content:
        print('✅ 镜像中的代码正确')
        sys.exit(0)
    else:
        print('❌ 镜像中的代码错误！')
        print('显示错误的代码行：')
        for i, line in enumerate(content.split('\n'), 1):
            if 'is_cce' in line and '=' in line and 'alert' in line:
                print(f'  Line {i}: {line.strip()}')
        sys.exit(1)
" || {
    echo ""
    echo -e "${RED}✗ 镜像验证失败！${NC}"
    echo ""
    echo "可能原因："
    echo "  1. Docker构建上下文问题"
    echo "  2. .dockerignore 排除了文件"
    echo "  3. 文件系统缓存问题"
    echo ""
    echo "建议操作："
    echo "  1. 检查 backend/.dockerignore 文件"
    echo "  2. 手动检查: docker run --rm op-web-backend:latest cat /app/app/services/alert/alert_processor.py | grep 'is_cce ='"
    echo "  3. 尝试清理系统缓存: sync && echo 3 > /proc/sys/vm/drop_caches"
    echo ""
    exit 1
}

# 启动服务
echo ""
echo "🚀 启动生产环境..."
docker compose -f docker-compose.prod.yml up -d

# 等待 MySQL 完全启动
echo ""
echo "⏳ 等待 MySQL 服务启动..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T mysql mysqladmin ping -h localhost -u root -p'Zhang~~1' --silent 2>/dev/null; then
        echo "✓ MySQL服务已启动"
        break
    fi
    echo "  等待中... ($i/30)"
    sleep 2
done

# 检查 MySQL 是否成功启动
if ! docker compose -f docker-compose.prod.yml exec -T mysql mysqladmin ping -h localhost -u root -p'Zhang~~1' --silent 2>/dev/null; then
    echo "❌ MySQL 启动超时"
    exit 1
fi

# 额外等待，确保 MySQL 完全就绪
echo "  等待 MySQL 完全就绪..."
sleep 5

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
docker compose -f docker-compose.prod.yml ps

# 检查服务健康状态
echo ""
echo "🏥 检查服务健康状态..."
sleep 5
BACKEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' cluster-backend 2>/dev/null || echo "unknown")
MYSQL_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' cluster-mysql 2>/dev/null || echo "unknown")
REDIS_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' cluster-redis 2>/dev/null || echo "unknown")

echo "  Backend: $BACKEND_HEALTH"
echo "  MySQL: $MYSQL_HEALTH"
echo "  Redis: $REDIS_HEALTH"

# 最终验证：检查运行中容器的代码
echo ""
echo "🔍 最终验证：检查运行中容器的代码..."
sleep 10  # 等待容器完全启动
docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import sys
with open('/app/app/services/alert/alert_processor.py', 'r') as f:
    content = f.read()
    if 'is_cce = alert.is_cce_cluster' in content:
        print('✅ 运行中容器的代码正确')
        sys.exit(0)
    else:
        print('❌ 运行中容器的代码错误！')
        print('显示错误的代码行：')
        for i, line in enumerate(content.split('\n'), 1):
            if 'is_cce' in line and '=' in line and 'alert' in line:
                print(f'  Line {i}: {line.strip()}')
        sys.exit(1)
" || {
    echo ""
    echo -e "${RED}✗ 运行中容器验证失败！${NC}"
    echo ""
    echo "这是一个严重问题，说明："
    echo "  1. 镜像构建正确，但容器启动时使用了错误的镜像"
    echo "  2. 或者有volume挂载覆盖了代码"
    echo ""
    echo "检查步骤："
    echo "  1. docker compose -f docker-compose.prod.yml config | grep -A 5 backend"
    echo "  2. docker inspect cluster-backend | grep -A 10 Mounts"
    echo ""
}

# 初始化系统配置
echo ""
echo "⚙️  初始化系统配置..."
# 等待后端服务完全启动
sleep 10
docker compose -f docker-compose.prod.yml exec -T backend python3 init_system_configs.py || {
    echo -e "${YELLOW}⚠️  系统配置初始化失败，请手动执行${NC}"
}

# 导入故障手册
echo ""
echo "📚 导入故障手册..."
# 1. 在容器内创建knowledge目录
docker compose -f docker-compose.prod.yml exec -T backend mkdir -p /knowledge 2>/dev/null || true

# 2. 复制故障手册文件到容器（优先CSV）
CSV_FILE="knowledge/故障维修手册.csv"
MD_FILE="knowledge/故障维修手册.md"

if [ -f "$CSV_FILE" ]; then
    echo "  ✅ 发现CSV格式手册，优先使用..."
    docker cp "$CSV_FILE" $(docker compose -f docker-compose.prod.yml ps -q backend):/knowledge/故障维修手册.csv
    echo "  ✓ CSV文件已复制"
elif [ -f "$MD_FILE" ]; then
    echo "  ⚠️  仅发现MD格式手册，使用降级方案..."
    docker cp "$MD_FILE" $(docker compose -f docker-compose.prod.yml ps -q backend):/knowledge/故障维修手册.md
    echo "  ✓ MD文件已复制"
else
    echo -e "${YELLOW}⚠️  未找到故障手册文件${NC}"
    echo "  跳过手册导入"
fi

# 3. 复制导入脚本到容器
if [ -f "backend/scripts/import_fault_manual.py" ]; then
    docker compose -f docker-compose.prod.yml exec -T backend mkdir -p /app/backend/scripts 2>/dev/null || true
    docker cp backend/scripts/import_fault_manual.py $(docker compose -f docker-compose.prod.yml ps -q backend):/app/backend/scripts/
    echo "  ✓ 导入脚本已复制"
    
    # 4. 调用导入脚本（自动优先使用CSV）
    echo "  导入手册数据到数据库..."
    docker compose -f docker-compose.prod.yml exec -T backend bash -c "cd /app && python3 backend/scripts/import_fault_manual.py" && \
    echo -e "${GREEN}✓ 故障手册导入成功${NC}" || \
    echo -e "${YELLOW}⚠️  故障手册导入失败，请手动导入${NC}"
    
    # 5. 重新匹配已有告警（如果手册导入成功）
    if [ $? -eq 0 ]; then
        echo ""
        echo "  重新匹配已有告警的手册..."
        docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import sys
sys.path.insert(0, '/app')
from app.core.deps import SessionLocal
from app.models.alert import AlertRecord, DiagnosisResult
from app.services.alert.manual_matcher import ManualMatchService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    # 查询所有未匹配手册的告警
    unmatched = db.query(DiagnosisResult).filter(
        DiagnosisResult.manual_matched == False
    ).all()
    
    logger.info(f'发现 {len(unmatched)} 条未匹配手册的告警')
    
    if len(unmatched) > 0:
        matcher = ManualMatchService(db)
        success_count = 0
        
        for diagnosis in unmatched:
            alert = db.query(AlertRecord).filter(AlertRecord.id == diagnosis.alert_id).first()
            if not alert:
                continue
            
            # 重新匹配手册
            manual = matcher.match(alert.alert_type, alert.component)
            if manual:
                diagnosis.manual_matched = True
                diagnosis.manual_name_zh = manual.get('name_zh')
                diagnosis.manual_impact = manual.get('impact')
                diagnosis.manual_recovery = manual.get('recovery')
                diagnosis.manual_solution = manual.get('solution')
                diagnosis.customer_aware = manual.get('customer_aware')
                diagnosis.danger_level = manual.get('danger_level')
                success_count += 1
        
        db.commit()
        logger.info(f'✅ 重新匹配完成: {success_count}/{len(unmatched)} 条成功')
    else:
        logger.info('✅ 所有告警已匹配手册')
        
except Exception as e:
    logger.error(f'重新匹配失败: {e}')
    db.rollback()
finally:
    db.close()
" && echo -e "${GREEN}✓ 已有告警重新匹配完成${NC}" || echo -e "${YELLOW}⚠️  重新匹配失败${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到导入脚本: backend/scripts/import_fault_manual.py${NC}"
    echo "  跳过手册导入"
fi

# 初始化路由规则模板
echo ""
echo "📋 初始化路由规则模板..."
docker compose -f docker-compose.prod.yml exec -T backend python3 scripts/init_rule_templates.py && \
echo -e "${GREEN}✓ 路由规则模板初始化成功${NC}" || \
echo -e "${YELLOW}⚠️  路由规则模板初始化失败或已存在，跳过${NC}"

# 询问是否配置宿主机MySQL
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}宿主机 MySQL 配置（可选）${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "意图路由优化功能需要在宿主机 MySQL 上配置全文索引参数。"
echo ""
echo "配置内容："
echo "  - ngram_token_size = 1  (支持单字搜索)"
echo "  - ft_min_word_len = 1   (最小词长度)"
echo "  - innodb_ft_enable_stopword = 0  (禁用停用词)"
echo ""
echo "安全保证："
echo "  ✓ 自动备份配置文件"
echo "  ✓ 不影响现有数据"
echo "  ✓ 可以随时回滚"
echo "  ✓ 仅修改配置参数，不修改数据"
echo ""
echo "宿主机信息："
echo "  地址: ${MYSQL_HOST_2:-10.175.96.168}"
echo "  端口: ${MYSQL_PORT_2:-8306}"
echo ""
read -p "是否配置宿主机 MySQL？(y/N): " configure_host_mysql

if [ "$configure_host_mysql" = "y" ] || [ "$configure_host_mysql" = "Y" ]; then
    echo ""
    echo "🔧 开始配置宿主机 MySQL..."
    
    # 检查脚本是否存在
    if [ ! -f "scripts/configure-host-mysql.sh" ]; then
        echo -e "${RED}✗ 配置脚本不存在: scripts/configure-host-mysql.sh${NC}"
        echo -e "${YELLOW}⚠️  跳过宿主机配置${NC}"
    else
        chmod +x scripts/configure-host-mysql.sh
        ./scripts/configure-host-mysql.sh --auto || {
            echo -e "${YELLOW}⚠️  宿主机配置失败，请手动配置${NC}"
            echo ""
            echo "手动配置步骤："
            echo "  1. ssh root@${MYSQL_HOST_2:-10.175.96.168}"
            echo "  2. vim /etc/my.cnf"
            echo "  3. 在 [mysqld] 段添加："
            echo "     ngram_token_size = 1"
            echo "     ft_min_word_len = 1"
            echo "     innodb_ft_enable_stopword = 0"
            echo "  4. systemctl restart mysqld"
            echo ""
        }
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  跳过宿主机 MySQL 配置${NC}"
    echo ""
    echo "如需后续配置，请运行："
    echo "  ./scripts/configure-host-mysql.sh --auto"
    echo ""
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ 生产环境部署完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📍 访问地址:"
echo "   前端: http://<服务器IP>:8089"
echo "   API文档: http://<服务器IP>:8000/docs"
echo "   MinIO控制台: http://<服务器IP>:8087"
echo ""
echo "📝 默认账号: admin / admin123"
echo ""
echo "📝 管理命令:"
echo "   查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "   查看后端: docker compose -f docker-compose.prod.yml logs -f backend"
echo "   查看状态: docker compose -f docker-compose.prod.yml ps"
echo "   重启服务: docker compose -f docker-compose.prod.yml restart"
echo "   停止服务: docker compose -f docker-compose.prod.yml down"
echo ""
echo "🧹 清理命令:"
echo "   标准清理: ./deploy.sh"
echo "   完全清理: ./deploy.sh --clean  (⚠️ 会删除所有数据)"
echo ""
echo "📦 打包离线部署:"
echo "   ./pack-offline.sh"
echo ""
echo "🔒 安全提醒:"
echo "   1. 首次登录后立即修改admin密码"
echo "   2. 定期备份MySQL和MinIO数据"
echo "   3. 查看审计日志监控系统访问"
echo ""

if [ "$CLEAN_MODE" = true ]; then
    echo -e "${YELLOW}⚠️  注意：完全清理模式已执行，所有旧数据已删除${NC}"
    echo ""
fi
