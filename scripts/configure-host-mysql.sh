#!/bin/bash

# 宿主机 MySQL 全文索引配置脚本（简化版）
# 用途：直接在宿主机上运行，配置 MySQL 全文索引参数
# 使用：将此脚本上传到宿主机，然后执行 bash configure-host-mysql-simple.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置参数
MYSQL_PORT="${MYSQL_PORT_2:-8306}"
MYSQL_USER="${MYSQL_USER_2:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD_2:-Xx36829wdt!}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}宿主机 MySQL 全文索引配置工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 检查 MySQL 是否运行
echo -e "${BLUE}[1/6] 检查 MySQL 服务状态...${NC}"
if systemctl is-active --quiet mysqld; then
    echo -e "${GREEN}✓ MySQL 服务正在运行${NC}"
elif systemctl is-active --quiet mysql; then
    echo -e "${GREEN}✓ MySQL 服务正在运行${NC}"
else
    echo -e "${RED}✗ MySQL 服务未运行${NC}"
    exit 1
fi

# 2. 查找 MySQL 配置文件
echo -e "${BLUE}[2/6] 查找 MySQL 配置文件...${NC}"
MYSQL_CONFIG=""
for config_path in /etc/my.cnf /etc/mysql/my.cnf /etc/mysql/mysql.conf.d/mysqld.cnf; do
    if [ -f "$config_path" ]; then
        MYSQL_CONFIG="$config_path"
        echo -e "${GREEN}✓ 找到配置文件：${MYSQL_CONFIG}${NC}"
        break
    fi
done

if [ -z "$MYSQL_CONFIG" ]; then
    echo -e "${RED}✗ 未找到 MySQL 配置文件${NC}"
    exit 1
fi

# 3. 检查配置是否已存在
echo -e "${BLUE}[3/6] 检查现有配置...${NC}"
if grep -q "ngram_token_size" "$MYSQL_CONFIG"; then
    echo -e "${YELLOW}⚠ 配置已存在，检查是否需要更新${NC}"
    
    # 检查配置值是否正确
    CURRENT_NGRAM=$(grep "ngram_token_size" "$MYSQL_CONFIG" | grep -oP '\d+' | head -1)
    CURRENT_FTMIN=$(grep "ft_min_word_len" "$MYSQL_CONFIG" | grep -oP '\d+' | head -1)
    
    if [ "$CURRENT_NGRAM" == "1" ] && [ "$CURRENT_FTMIN" == "1" ]; then
        echo -e "${GREEN}✓ 配置已正确，无需修改${NC}"
        
        # 验证运行时配置
        echo -e "${BLUE}[4/6] 验证运行时配置...${NC}"
        RUNTIME_NGRAM=$(mysql -h localhost -P ${MYSQL_PORT} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW VARIABLES LIKE 'ngram_token_size';" 2>/dev/null | grep ngram_token_size | awk '{print $2}')
        
        if [ "$RUNTIME_NGRAM" == "1" ]; then
            echo -e "${GREEN}✓ 运行时配置正确${NC}"
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}✓ 配置已完成，无需操作${NC}"
            echo -e "${GREEN}========================================${NC}"
            exit 0
        else
            echo -e "${YELLOW}⚠ 运行时配置不正确，需要重启 MySQL${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 配置值不正确，需要更新${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 配置不存在，需要添加${NC}"
fi

# 4. 备份配置文件
echo -e "${BLUE}[4/6] 备份配置文件...${NC}"
BACKUP_FILE="${MYSQL_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$MYSQL_CONFIG" "$BACKUP_FILE"
echo -e "${GREEN}✓ 备份文件：${BACKUP_FILE}${NC}"

# 5. 添加或更新配置
echo -e "${BLUE}[5/6] 更新配置文件...${NC}"

# 检查是否有 [mysqld] 段
if ! grep -q "^\[mysqld\]" "$MYSQL_CONFIG"; then
    echo -e "${YELLOW}⚠ 配置文件中没有 [mysqld] 段，添加中...${NC}"
    echo "" >> "$MYSQL_CONFIG"
    echo "[mysqld]" >> "$MYSQL_CONFIG"
fi

# 删除旧的全文索引配置（如果存在）
grep -v "Fulltext index config" "$MYSQL_CONFIG" > "${MYSQL_CONFIG}.tmp" || cp "$MYSQL_CONFIG" "${MYSQL_CONFIG}.tmp"
grep -v "^ngram_token_size" "${MYSQL_CONFIG}.tmp" > "${MYSQL_CONFIG}.tmp2" || cp "${MYSQL_CONFIG}.tmp" "${MYSQL_CONFIG}.tmp2"
grep -v "^ft_min_word_len" "${MYSQL_CONFIG}.tmp2" > "${MYSQL_CONFIG}.tmp3" || cp "${MYSQL_CONFIG}.tmp2" "${MYSQL_CONFIG}.tmp3"
grep -v "^innodb_ft_enable_stopword" "${MYSQL_CONFIG}.tmp3" > "$MYSQL_CONFIG" || cp "${MYSQL_CONFIG}.tmp3" "$MYSQL_CONFIG"
rm -f "${MYSQL_CONFIG}.tmp" "${MYSQL_CONFIG}.tmp2" "${MYSQL_CONFIG}.tmp3"

# 在 [mysqld] 段后添加新配置
python3 -c "
import sys
config_file = '$MYSQL_CONFIG'
with open(config_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

output = []
for line in lines:
    output.append(line)
    if line.strip() == '[mysqld]':
        output.append('\n')
        output.append('# Fulltext index config - added by configure-host-mysql.sh\n')
        output.append('ngram_token_size = 1\n')
        output.append('ft_min_word_len = 1\n')
        output.append('innodb_ft_enable_stopword = 0\n')

with open(config_file, 'w', encoding='utf-8') as f:
    f.writelines(output)
"

echo -e "${GREEN}✓ 配置文件已更新${NC}"

# 6. 重启 MySQL 服务
echo -e "${BLUE}[6/6] 重启 MySQL 服务...${NC}"
echo -e "${YELLOW}⚠ 即将重启 MySQL，可能会短暂中断服务（约10-30秒）${NC}"
echo -n "是否继续？[y/N] "
read -r CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}⚠ 已取消重启${NC}"
    echo -e "${YELLOW}⚠ 配置已更新，但需要手动重启 MySQL 才能生效${NC}"
    echo ""
    echo "手动重启命令："
    echo "  systemctl restart mysqld"
    echo ""
    echo "回滚命令（如果需要）："
    echo "  cp ${BACKUP_FILE} ${MYSQL_CONFIG}"
    echo "  systemctl restart mysqld"
    exit 0
fi

# 重启 MySQL
if systemctl restart mysqld 2>/dev/null; then
    echo -e "${GREEN}✓ MySQL 服务已重启（mysqld）${NC}"
elif systemctl restart mysql 2>/dev/null; then
    echo -e "${GREEN}✓ MySQL 服务已重启（mysql）${NC}"
else
    echo -e "${RED}✗ MySQL 重启失败${NC}"
    echo -e "${YELLOW}⚠ 正在回滚配置...${NC}"
    cp "$BACKUP_FILE" "$MYSQL_CONFIG"
    echo -e "${GREEN}✓ 配置已回滚${NC}"
    exit 1
fi

# 等待 MySQL 启动
echo -e "${BLUE}等待 MySQL 启动...${NC}"
sleep 5

# 验证配置
echo -e "${BLUE}验证配置...${NC}"
RUNTIME_NGRAM=$(mysql -h localhost -P ${MYSQL_PORT} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW VARIABLES LIKE 'ngram_token_size';" 2>/dev/null | grep ngram_token_size | awk '{print $2}')
RUNTIME_FTMIN=$(mysql -h localhost -P ${MYSQL_PORT} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW VARIABLES LIKE 'ft_min_word_len';" 2>/dev/null | grep ft_min_word_len | awk '{print $2}')
RUNTIME_STOPWORD=$(mysql -h localhost -P ${MYSQL_PORT} -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW VARIABLES LIKE 'innodb_ft_enable_stopword';" 2>/dev/null | grep innodb_ft_enable_stopword | awk '{print $2}')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 配置完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "配置验证："
echo "  ngram_token_size: ${RUNTIME_NGRAM} (期望: 1)"
echo "  ft_min_word_len: ${RUNTIME_FTMIN} (期望: 1)"
echo "  innodb_ft_enable_stopword: ${RUNTIME_STOPWORD} (期望: OFF)"
echo ""
echo "备份文件："
echo "  ${BACKUP_FILE}"
echo ""
