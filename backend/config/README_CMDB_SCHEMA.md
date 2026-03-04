# CMDB数据库Schema说明

## 问题说明

CMDB功能使用了完整的175字段数据模型，但 `mysql-init.sql` 中的表定义是简化版本（只有20多个字段）。

这会导致：
- 使用 `--clean` 模式部署时，数据库表结构不完整
- 访问CMDB页面时出现 `Unknown column 'iaas_servers.bns_id'` 错误

## 解决方案

### 方案1：使用修复脚本（推荐）

在服务器上执行：

```bash
# 进入后端容器
docker exec -it cluster-backend bash

# 运行修复脚本
python3 fix_cmdb_schema.py

# 按提示输入 'yes' 确认修复
```

### 方案2：手动执行SQL

```bash
# 进入MySQL容器
docker exec -it cluster-mysql mysql -uroot -p123456

# 在MySQL中执行
USE cluster_db;
SOURCE /docker-entrypoint-initdb.d/mysql-init-cmdb-full.sql;
EXIT;

# 重启后端服务
docker restart cluster-backend
```

### 方案3：完全重新部署

```bash
# 停止所有服务
docker-compose -f docker-compose.prod.yml down -v

# 重新部署
./deploy.sh --clean
```

## 验证修复

```bash
# 检查表结构
docker exec -it cluster-mysql mysql -uroot -p123456 -e "
USE cluster_db;
SELECT COUNT(*) as field_count FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'cluster_db' AND TABLE_NAME = 'iaas_servers';
"
```

应该显示约145个字段（完整版）。

## 内网部署注意事项

内网部署时，确保：

1. **使用完整的SQL文件**：
   ```bash
   # 在打包时包含完整的SQL文件
   cp backend/config/mysql-init-cmdb-full.sql offline-deploy/backend/config/
   ```

2. **在docker-compose.offline.yml中挂载**：
   ```yaml
   mysql:
     volumes:
       - ./backend/config/mysql-init.sql:/docker-entrypoint-initdb.d/01-init.sql
       - ./backend/config/mysql-init-cmdb.sql:/docker-entrypoint-initdb.d/02-cmdb.sql
       - ./backend/config/mysql-init-cmdb-full.sql:/docker-entrypoint-initdb.d/03-cmdb-full.sql
       - ./backend/config/mysql-init-ai-query.sql:/docker-entrypoint-initdb.d/04-ai-query.sql
       - ./backend/config/mysql-init-instance-config.sql:/docker-entrypoint-initdb.d/05-instance-config.sql
   ```

3. **首次部署后运行修复脚本**：
   ```bash
   docker exec -it cluster-backend python3 fix_cmdb_schema.py
   ```

## 为什么会出现这个问题？

1. **历史原因**：最初的CMDB表定义是简化版，后来扩展到175个字段
2. **SQL文件未同步**：`mysql-init.sql` 没有更新为完整版本
3. **SQLAlchemy自动创建**：代码依赖SQLAlchemy自动创建表，但如果MySQL数据持久化，旧表结构会保留

## 长期解决方案

已创建以下文件确保schema一致性：

- `mysql-init-cmdb-full.sql`: 完整的CMDB表结构（175字段）
- `fix_cmdb_schema.py`: 自动修复脚本
- 更新部署脚本，确保使用完整SQL

## 相关文件

- `backend/app/models/iaas.py` - 数据模型定义（175字段）
- `backend/config/mysql-init-cmdb-full.sql` - 完整表结构SQL
- `backend/fix_cmdb_schema.py` - Schema修复脚本
