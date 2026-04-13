#!/bin/bash
# 离线部署打包脚本（修复版 v6）
# 修复内容：
# 1. 修复变量转义问题（使用双反斜杠）
# 2. 优化 MySQL 就绪等待时间（10秒 → 30秒）
# 3. 保留完整的 MySQL 检查逻辑和诊断信息

set -e

echo "╔══════════════════════════════════════════╗"
echo "║     集群管理平台 - 离线部署打包          ║"
echo "╚══════════════════════════════════════════╝"

# 检查镜像是否存在
echo ""
echo "� 检查 Docker 镜像..."
if ! docker image inspect op-web-backend:latest > /dev/null 2>&1; then
    echo "❌ 未找到 op-web-backend:latest 镜像"
    echo "请先运行: docker compose -f docker-compose.prod.yml build"
    exit 1
fi

if ! docker image inspect op-web-frontend:latest > /dev/null 2>&1; then
    echo "❌ 未找到 op-web-frontend:latest 镜像"
    echo "请先运行: docker compose -f docker-compose.prod.yml build"
    exit 1
fi

echo "✓ 镜像检查通过"

# 创建临时目录
PACK_DIR="offline-deploy"
rm -rf $PACK_DIR
mkdir -p $PACK_DIR
mkdir -p $PACK_DIR/backend-config

echo ""
echo "📦 1. 导出 Docker 镜像..."

# 从 docker-compose.prod.yml 动态提取镜像名
echo "🔍 从 docker-compose.prod.yml 提取镜像列表..."
IMAGES=$(docker compose -f docker-compose.prod.yml config | grep 'image:' | awk '{print $2}' | sort -u)

if [ -z "$IMAGES" ]; then
    echo "❌ 无法从 docker-compose.prod.yml 提取镜像列表"
    exit 1
fi

echo "📋 将导出以下镜像:"
echo "$IMAGES" | sed 's/^/  - /'

# 导出镜像
docker save -o $PACK_DIR/images.tar $IMAGES

echo "✓ 镜像导出完成"

echo ""
echo "📄 2. 复制部署文件..."

# 复制 docker-compose 文件（离线版，改名为 prod.yml 以便内网使用）
cp docker-compose.offline.yml $PACK_DIR/docker-compose.prod.yml

# 复制 .env 文件
if [ -f ".env" ]; then
    cp .env $PACK_DIR/.env
    echo "✓ 已复制 .env 文件"
else
    echo "⚠️  未找到 .env 文件，请手动创建"
fi

# 复制 mysql-init.sql（优先使用 backend/config，确保最新）
if [ -f "backend/config/mysql-init.sql" ]; then
    cp backend/config/mysql-init.sql $PACK_DIR/backend-config/
    echo "✓ 已复制 mysql-init.sql"
    
    # 验证文件包含 chat_history 表
    if grep -q "chat_history" $PACK_DIR/backend-config/mysql-init.sql; then
        echo "✓ 验证: chat_history 表已包含"
    else
        echo "⚠️  警告: chat_history 表未找到，请确保 backend/config/mysql-init.sql 已更新"
    fi
elif [ -f "deploy/config/mysql-init.sql" ]; then
    cp deploy/config/mysql-init.sql $PACK_DIR/backend-config/
    echo "✓ 已复制 mysql-init.sql (from deploy)"
else
    echo "❌ 错误: 未找到 mysql-init.sql"
    echo "请确保 backend/config/mysql-init.sql 存在"
    rm -rf $PACK_DIR
    exit 1
fi

# 复制CMDB完整表结构SQL
if [ -f "backend/config/mysql-init-cmdb-full.sql" ]; then
    cp backend/config/mysql-init-cmdb-full.sql $PACK_DIR/backend-config/
    echo "✓ 已复制 mysql-init-cmdb-full.sql (CMDB完整表结构)"
else
    echo "⚠️  警告: 未找到 mysql-init-cmdb-full.sql，CMDB功能可能无法正常使用"
fi

# 复制CMDB Schema修复脚本（如果存在）
if [ -f "backend/fix_cmdb_schema.py" ]; then
    cp backend/fix_cmdb_schema.py $PACK_DIR/
    echo "✓ 已复制 fix_cmdb_schema.py (CMDB Schema修复脚本)"
fi

# 复制实例配置文件
if [ -f "backend/config/default_instance_ids.json" ]; then
    cp backend/config/default_instance_ids.json $PACK_DIR/backend-config/
    echo "✓ 已复制 default_instance_ids.json"
else
    echo "⚠️  警告: 未找到 default_instance_ids.json，实例配置初始化将跳过"
fi

# 复制 Prometheus 配置文件
if [ -f "backend/config/prometheus_config.json" ]; then
    cp backend/config/prometheus_config.json $PACK_DIR/backend-config/
    echo "✓ 已复制 prometheus_config.json (Prometheus Cookie 配置)"
else
    echo "⚠️  警告: 未找到 prometheus_config.json，Prometheus 查询将使用空 Cookie"
fi

# 复制系统配置初始化脚本
if [ -f "backend/init_system_configs.py" ]; then
    cp backend/init_system_configs.py $PACK_DIR/
    echo "✓ 已复制 init_system_configs.py"
else
    echo "⚠️  警告: 未找到 init_system_configs.py，系统配置初始化将跳过"
fi

# 复制后端诊断脚本目录
if [ -d "backend/scripts" ]; then
    mkdir -p $PACK_DIR/backend-scripts
    cp backend/scripts/*.py $PACK_DIR/backend-scripts/ 2>/dev/null || true
    if [ -f "backend/scripts/README_DIAGNOSTICS.md" ]; then
        cp backend/scripts/README_DIAGNOSTICS.md $PACK_DIR/backend-scripts/
    fi
    echo "✓ 已复制 backend/scripts/ (诊断工具)"
else
    echo "⚠️  警告: 未找到 backend/scripts 目录，诊断工具将不可用"
fi

# 复制故障手册文件
if [ -d "knowledge" ]; then
    mkdir -p $PACK_DIR/knowledge
    # 优先复制CSV文件（完整版292条）
    if [ -f "knowledge/故障维修手册.csv" ]; then
        cp knowledge/故障维修手册.csv $PACK_DIR/knowledge/
        echo "✓ 已复制 故障维修手册.csv (292条完整记录)"
    else
        echo "⚠️  警告: 未找到 knowledge/故障维修手册.csv"
    fi
    # 同时复制MD文件（降级备份）
    if [ -f "knowledge/故障维修手册.md" ]; then
        cp knowledge/故障维修手册.md $PACK_DIR/knowledge/
        echo "✓ 已复制 故障维修手册.md (降级备份)"
    else
        echo "⚠️  警告: 未找到 knowledge/故障维修手册.md"
    fi
else
    echo "⚠️  警告: 未找到 knowledge 目录，故障手册导入将跳过"
fi

# 复制宿主机MySQL配置脚本
if [ -f "scripts/configure-host-mysql.sh" ]; then
    mkdir -p $PACK_DIR/scripts
    cp scripts/configure-host-mysql.sh $PACK_DIR/scripts/
    chmod +x $PACK_DIR/scripts/configure-host-mysql.sh
    echo "✓ 已复制 configure-host-mysql.sh (宿主机MySQL配置脚本)"
else
    echo "⚠️  警告: 未找到 configure-host-mysql.sh，宿主机MySQL配置功能将不可用"
fi

# 创建启动脚本（修复版 v6 - 修复转义问题和优化等待时间）
cat > $PACK_DIR/start.sh << 'EOFSTART'
#!/bin/bash
# 内网部署启动脚本（修复版 v6）
# 修复内容：
# 1. 修复变量转义问题（使用正确的 bash 语法）
# 2. 优化 MySQL 就绪等待时间（10秒 → 30秒）
# 3. 从 .env 文件读取 MySQL 密码

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
echo "等待后端 API 容器启动..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T backend-api python3 --version >/dev/null 2>&1; then
        echo "✓ 后端 API 容器已启动 (用时 $((i*2)) 秒)"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "⚠️  后端容器启动超时，但继续部署"
    fi
    
    sleep 2
done

# 步骤4: 验证后端容器可以连接数据库（修复版 - 单行Python）
echo "验证后端 API 数据库连接..."
DB_PASSWORD="$MYSQL_ROOT_PASSWORD"  # 预展开变量，避免转义问题

for i in {1..10}; do
    if docker compose -f docker-compose.prod.yml exec -T backend-api python3 -c \
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

# 检查 Worker 是否正常运行
WORKER_STATUS=$(docker inspect --format='{{.State.Status}}' cluster-backend-worker 2>/dev/null || echo "unknown")
if [ "$WORKER_STATUS" != "running" ]; then
    echo ""
    echo "⚠️  警告：Backend Worker 状态异常 ($WORKER_STATUS)"
    echo "   请检查 worker 日志：docker compose -f docker-compose.prod.yml logs backend-worker --tail=50"
fi

echo ""
echo "🗄️ 6. 初始化数据库和配置..."

# 升级模式：补建缺失的新表（保留数据时执行）
if [ "$clean_volumes" != "2" ]; then
    echo ""
    echo "🔧 检查并补建缺失的数据库表（升级模式）..."

    # 用 Python 脚本检查并创建缺失的表，避免 SQL heredoc 转义问题
    docker compose -f docker-compose.prod.yml exec -T backend-api python3 - << 'PYEOF'
import sys
import time
import pymysql
import os

host = os.environ.get("MYSQL_HOST", "mysql")
port = int(os.environ.get("MYSQL_PORT", 3306))
user = os.environ.get("MYSQL_USER", "root")
password = os.environ.get("MYSQL_PASSWORD", os.environ.get("MYSQL_ROOT_PASSWORD", ""))
database = os.environ.get("MYSQL_DATABASE", "cluster_management")

# 等待 MySQL 就绪
conn = None
for attempt in range(10):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password,
                               database=database, connect_timeout=10,
                               charset="utf8mb4")
        break
    except Exception as e:
        if attempt < 9:
            print("  等待 MySQL... (%d/10)" % (attempt + 1))
            time.sleep(3)
        else:
            print("❌ 无法连接 MySQL: %s" % e)
            sys.exit(1)

cursor = conn.cursor()

# 查询当前已有的表
cursor.execute("SHOW TABLES")
existing = {row[0] for row in cursor.fetchall()}
print("当前已有表: %s" % sorted(existing))

# 定义需要补建的表（只在不存在时创建）
tables = {
    "chat_history": """
        CREATE TABLE `chat_history` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NOT NULL COMMENT '用户ID',
            `role` VARCHAR(20) NOT NULL COMMENT 'user/assistant/system',
            `content` TEXT NOT NULL COMMENT '消息内容',
            `context_data` TEXT NULL COMMENT 'JSON格式上下文数据',
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX `idx_chat_history_user_id` (`user_id`),
            INDEX `idx_chat_history_created_at` (`created_at`),
            CONSTRAINT `fk_chat_history_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话历史'
    """,
    "user_notes": """
        CREATE TABLE `user_notes` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT NOT NULL UNIQUE COMMENT '用户ID',
            `content` TEXT DEFAULT '' COMMENT '备忘内容',
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            CONSTRAINT `fk_user_notes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户备忘'
    """,
    "instance_config": """
        CREATE TABLE `instance_config` (
            `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            `config_type` VARCHAR(50) NOT NULL UNIQUE COMMENT '配置类型',
            `instance_ids` TEXT NOT NULL COMMENT '实例ID列表（JSON数组格式）',
            `description` VARCHAR(500) NULL COMMENT '配置说明',
            `created_by` VARCHAR(100) NULL COMMENT '创建者',
            `updated_by` VARCHAR(100) NULL COMMENT '更新者',
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实例配置表'
    """,
}

created = []
skipped = []
failed = []

for table_name, ddl in tables.items():
    if table_name in existing:
        skipped.append(table_name)
        print("  ⏭  %s 已存在，跳过" % table_name)
    else:
        try:
            cursor.execute(ddl.strip())
            conn.commit()
            created.append(table_name)
            print("  ✅ %s 创建成功" % table_name)
        except Exception as e:
            failed.append(table_name)
            print("  ❌ %s 创建失败: %s" % (table_name, e))

cursor.close()
conn.close()

print("")
print("补表完成: 新建 %d 张，跳过 %d 张，失败 %d 张" % (len(created), len(skipped), len(failed)))
if failed:
    sys.exit(1)
PYEOF

    if [ $? -eq 0 ]; then
        echo "✓ 数据库表检查完成"
    else
        echo "⚠️  补表过程中出现错误，请检查日志后继续"
    fi
fi

# 导入故障手册函数
import_fault_manual() {
    local file_path="$1"
    local file_name=$(basename "$file_path")

    echo "📚 导入故障手册（${file_name}）..."
    
    # 确保容器内目录存在
    docker exec cluster-backend-api mkdir -p /app/knowledge /app/backend/scripts 2>/dev/null || true

    # 复制故障手册文件到容器内
    if docker cp "$file_path" "cluster-backend-api:/app/knowledge/${file_name}"; then
        echo "✓ 故障手册文件已复制到容器"
    else
        echo "❌ 故障手册文件复制失败"
        return 1
    fi

    # 复制导入脚本到容器内
    if [ -f "backend-scripts/import_fault_manual.py" ]; then
        if docker cp "backend-scripts/import_fault_manual.py" "cluster-backend-api:/app/backend/scripts/import_fault_manual.py"; then
            echo "✓ 导入脚本已复制到容器"
        else
            echo "❌ 导入脚本复制失败"
            return 1
        fi
    else
        echo "❌ 未找到导入脚本: backend-scripts/import_fault_manual.py"
        return 1
    fi
    
    # 执行导入（使用正确的路径）
    if docker compose -f docker-compose.prod.yml exec -T backend-api bash -c "cd /app && python3 backend/scripts/import_fault_manual.py" 2>/dev/null; then
        echo "✓ 故障手册导入成功"

        # 重新匹配已有告警（带连接重试，避免导入后MySQL短暂不可用）
        echo "  重新匹配已有告警的手册..."
        echo "  等待 MySQL 处理完导入（20秒）..."
        sleep 20  # 增加等待时间，给MySQL足够时间处理292条记录的写入
        docker compose -f docker-compose.prod.yml exec -T backend-api python3 -c '
import sys, time
sys.path.insert(0, "/app")
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 带重试的数据库连接
db = None
for attempt in range(5):
    try:
        from sqlalchemy import text
        from app.core.deps import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        break
    except Exception as e:
        if attempt < 4:
            logger.warning("数据库连接失败（尝试 %d/5）: %s，3秒后重试..." % (attempt+1, e))
            time.sleep(3)
        else:
            logger.error("数据库连接失败（已重试5次）: %s" % e)
            sys.exit(1)

from app.models.alert import AlertRecord, DiagnosisResult
from app.services.alert.manual_matcher import ManualMatchService

try:
    # 查询所有未匹配手册的告警
    unmatched = db.query(DiagnosisResult).filter(
        DiagnosisResult.manual_matched == False
    ).all()

    logger.info("发现 %d 条未匹配手册的告警" % len(unmatched))

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
                diagnosis.manual_name_zh = manual.get("name_zh")
                diagnosis.manual_impact = manual.get("impact")
                diagnosis.manual_recovery = manual.get("recovery")
                diagnosis.manual_solution = manual.get("solution")
                diagnosis.customer_aware = manual.get("customer_aware")
                diagnosis.danger_level = manual.get("danger_level")
                success_count += 1

        db.commit()
        logger.info("✅ 重新匹配完成: %d/%d 条成功" % (success_count, len(unmatched)))
    else:
        logger.info("✅ 所有告警已匹配手册")

except Exception as e:
    logger.error("重新匹配失败: %s" % e)
    db.rollback()
finally:
    if db:
        db.close()
'
        if [ $? -eq 0 ]; then
            echo "✓ 已有告警重新匹配完成"
        else
            echo "⚠️  重新匹配失败（不影响部署）"
            echo "   可稍后手动重新匹配："
            echo "   docker compose -f docker-compose.prod.yml exec backend-api bash -c \"cd /app && python3 backend/scripts/rematch_fault_manual.py\""
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
            echo "  docker compose -f docker-compose.prod.yml exec -T backend-api bash -c \"cd /app && python3 backend/scripts/import_fault_manual.py\""
            echo ""
            echo "或者进入容器后执行："
            echo ""
            echo "  docker compose -f docker-compose.prod.yml exec backend-api bash"
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
                if docker compose -f docker-compose.prod.yml exec -T backend-api bash -c "cd /app && python3 backend/scripts/import_fault_manual.py"; then
                    echo "✅ 手动导入成功"
                else
                    echo "❌ 手动导入也失败了"
                    echo "   请查看后端日志排查问题："
                    echo "   docker compose -f docker-compose.prod.yml logs backend-api --tail=50"
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
        echo "  docker compose -f docker-compose.prod.yml exec -T backend-api bash -c \"cd /app && python3 backend/scripts/import_fault_manual.py\""
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
    echo "📋 复制配置文件到容器..."

    # 复制 default_instance_ids.json
    if [ -f "backend-config/default_instance_ids.json" ]; then
        if docker cp backend-config/default_instance_ids.json "cluster-backend-api:/app/config/default_instance_ids.json"; then
            echo "✓ default_instance_ids.json 复制成功"

            # 验证文件是否存在
            if docker compose -f docker-compose.prod.yml exec -T backend-api test -f /app/config/default_instance_ids.json; then
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
        if docker cp backend-config/prometheus_config.json "cluster-backend-api:/app/config/prometheus_config.json"; then
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
    if docker compose -f docker-compose.prod.yml exec -T backend-api python3 init_system_configs.py; then
        echo "✓ 系统配置初始化成功"
    else
        echo "❌ 系统配置初始化失败"
        echo "   请查看详细日志:"
        echo "   docker compose -f docker-compose.prod.yml logs backend-api --tail=100 | grep -i 'init_system\\|系统配置'"
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
echo "  查看后端API: docker compose -f docker-compose.prod.yml logs -f backend-api"
echo "  查看后端Worker: docker compose -f docker-compose.prod.yml logs -f backend-worker"
echo "  查看状态: docker compose -f docker-compose.prod.yml ps"
echo "  重启服务: docker compose -f docker-compose.prod.yml restart"
echo "  停止服务: docker compose -f docker-compose.prod.yml down"
echo ""
echo "如需配置宿主机MySQL，请运行："
echo "  ./scripts/configure-host-mysql.sh"
EOFSTART

chmod +x $PACK_DIR/start.sh

echo ""
echo "� 3. 打包文件..."
tar -czf offline-deploy.tar.gz $PACK_DIR/

echo ""
echo "🧹 4. 清理临时文件..."
rm -rf $PACK_DIR

echo ""
echo "✅ 离线部署包创建完成！"
echo ""
echo "文件: offline-deploy.tar.gz"
echo "大小: $(du -h offline-deploy.tar.gz | cut -f1)"
echo ""
echo "使用方法："
echo "1. 将 offline-deploy.tar.gz 传输到内网服务器"
echo "2. 解压: tar -xzf offline-deploy.tar.gz"
echo "3. 进入目录: cd offline-deploy"
echo "4. 修改 .env 文件中的配置（如需要）"
echo "5. 运行: ./start.sh"
echo ""
echo "📝 v6 修复说明："
echo "- 修复了变量转义问题（heredoc 使用正确语法）"
echo "- 优化了 MySQL 就绪等待时间（10秒 → 30秒）"
echo "- 保留了完整的 MySQL 检查逻辑和诊断信息"
echo "- 增加了后端容器启动检查"
echo "- 增加了数据库连接验证"
echo ""
