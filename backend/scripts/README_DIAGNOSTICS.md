# 诊断脚本说明

本目录包含集群管理平台的**后端诊断和测试脚本**。

> **注意**：项目根目录还有一个 `scripts/` 目录，用于存放部署和配置脚本（如 `configure-host-mysql.sh`）。
> 本目录 `backend/scripts/` 专门存放需要访问后端代码的诊断脚本。

## 📋 脚本列表

### 1. 交互式诊断工具

**diagnose.py** - 主诊断工具（推荐使用）
- 提供交互式菜单，统一调用所有诊断脚本
- 彩色输出，易于阅读
- 支持单独运行或批量运行所有诊断

**使用方法**：
```bash
# 在容器内执行
docker exec -it cluster-backend python3 /app/backend/scripts/diagnose.py

# 或在宿主机执行（需要设置PYTHONPATH）
cd /root/cluster-management
export PYTHONPATH=/root/cluster-management/backend:$PYTHONPATH
python3 backend/scripts/diagnose.py
```

---

### 2. 独立诊断脚本

#### check_severity.py
**功能**：检查告警记录的severity字段

**检查内容**：
- 数据库中severity字段的实际值分布
- 统计API期望的severity值映射
- 显示示例告警记录

**使用场景**：
- 验证severity字段是否正确存储
- 排查告警统计无数据问题

**执行方式**：
```bash
docker exec cluster-backend python3 /app/backend/scripts/check_severity.py
```

---

#### check_timestamp.py
**功能**：检查告警记录的时间戳问题

**检查内容**：
- 数据库中timestamp字段的时区信息
- 模拟前端查询，验证时区转换
- 分析时间范围不匹配的原因

**使用场景**：
- 验证时区转换是否正确
- 排查告警统计时间范围问题

**执行方式**：
```bash
docker exec cluster-backend python3 /app/backend/scripts/check_timestamp.py
```

---

#### test_diagnosis_parse.py
**功能**：测试诊断报告解析逻辑

**检查内容**：
- 验证composedResult字段解析
- 测试grade字段映射
- 检查错误项/警告项分类

**使用场景**：
- 验证诊断解析逻辑是否正确
- 排查诊断结果显示异常问题

**执行方式**：
```bash
docker exec cluster-backend python3 /app/backend/scripts/test_diagnosis_parse.py
```

---

#### verify_fix.py
**功能**：验证修复效果（综合测试）

**检查内容**：
- 运行所有诊断检查
- 验证修复后的功能
- 生成综合测试报告

**使用场景**：
- 部署后验证修复效果
- 回归测试

**执行方式**：
```bash
docker exec cluster-backend python3 /app/scripts/verify_fix.py
```

---

### 3. 配置脚本

#### configure-host-mysql.sh
**功能**：配置宿主机MySQL连接

**使用场景**：
- 初始化部署时配置MySQL
- 修改MySQL连接参数

---

## 🚀 快速开始

### 方式1：使用交互式诊断工具（推荐）

```bash
# 进入容器
docker exec -it cluster-backend bash

# 运行诊断工具
python3 /app/scripts/diagnose.py

# 根据菜单选择要执行的诊断
```

### 方式2：直接运行单个脚本

```bash
# 检查severity字段
docker exec cluster-backend python3 /app/scripts/check_severity.py

# 检查时间戳问题
docker exec cluster-backend python3 /app/scripts/check_timestamp.py

# 测试诊断解析
docker exec cluster-backend python3 /app/scripts/test_diagnosis_parse.py

# 验证修复效果
docker exec cluster-backend python3 /app/scripts/verify_fix.py
```

---

## 📝 常见问题

### Q: 脚本执行失败，提示ModuleNotFoundError？
A: 确保在容器内执行，或者在宿主机上设置正确的PYTHONPATH：
```bash
export PYTHONPATH=/root/cluster-management/backend:$PYTHONPATH
python3 scripts/check_severity.py
```

### Q: 如何查看脚本的详细输出？
A: 脚本会自动输出详细信息，如果需要保存日志：
```bash
docker exec cluster-backend python3 /app/scripts/diagnose.py 2>&1 | tee diagnose.log
```

### Q: 诊断工具显示颜色异常？
A: 某些终端不支持ANSI颜色，可以禁用颜色输出或使用支持颜色的终端（如iTerm2、Windows Terminal）

---

## 🔧 开发说明

### 添加新的诊断脚本

1. 在`scripts/`目录下创建新脚本
2. 遵循现有脚本的格式和命名规范
3. 在`diagnose.py`中添加菜单项
4. 更新本README文档

### 脚本规范

- 使用Python 3.7+
- 添加详细的文档字符串
- 使用`sys.path.insert(0, ...)`添加backend路径
- 输出清晰的诊断信息
- 返回明确的退出码（0=成功，非0=失败）

---

## 📞 支持

如有问题，请查看：
- 项目主README: `/root/cluster-management/README.md`
- 功能逻辑文档: `.kiro/steering/功能逻辑.md`
- 项目状态: `.kiro/steering/PROJECT_STATUS.md`
