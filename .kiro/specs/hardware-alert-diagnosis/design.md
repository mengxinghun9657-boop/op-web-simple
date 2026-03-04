# 硬件告警智能诊断系统 - 设计文档

## 1. 系统架构

### 1.1 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Webhook配置  │  │  告警列表    │  │  统计报表    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP API
┌─────────────────────────────────────────────────────────────┐
│                      API 层 (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Webhook API  │  │  告警 API    │  │  统计 API    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      服务层 (Services)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 文件监控服务 │  │ 告警解析服务 │  │ 手册匹配服务 │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 诊断API服务  │  │  AI解读服务  │  │ Webhook服务  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据层 (MySQL + Redis)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 告警记录表   │  │ 诊断结果表   │  │ Webhook配置  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈
- **后端**: Python 3.8+, FastAPI, SQLAlchemy, Celery
- **前端**: Vue 3, Element Plus, Axios
- **数据库**: MySQL 8.0, Redis
- **部署**: Docker, Docker Compose
- **监控**: Watchdog (文件监控)

---

## 2. 数据库设计

### 2.1 设计原则

**灵活性优先**：
- 字段长度留足余量（2-3倍预估值），避免频繁修改表结构
- 使用JSON字段存储可变数据，支持动态扩展
- 提取关键字段到独立列，支持高效查询和统计

**向后兼容**：
- 只增不减：只能新增字段，不能删除或重命名
- 新增字段必须有默认值或允许NULL
- 字段变更需要提供数据迁移脚本

**性能优化**：
- 合理使用单列索引和复合索引
- 支持时间趋势分析（时间+维度复合索引）
- 统计字段独立存储，避免JSON查询

### 2.2 告警记录表 (alert_records)
```sql
CREATE TABLE alert_records (
    -- 基础信息
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    alert_type VARCHAR(200) NOT NULL COMMENT '告警类型（预留足够长度）',
    
    -- 位置信息（用于分组统计）
    ip VARCHAR(100) COMMENT '节点IP地址',
    cluster_id VARCHAR(200) COMMENT '集群ID（CCE集群专用）',
    instance_id VARCHAR(200) COMMENT '实例ID（物理机专用）',
    hostname VARCHAR(200) COMMENT '主机名/节点名',
    
    -- 告警属性（用于筛选和统计）
    component VARCHAR(100) COMMENT '组件类型(GPU/Memory/CPU/Motherboard等)',
    severity VARCHAR(50) NOT NULL COMMENT '严重程度(critical/warning/info等)',
    
    -- 时间信息（用于时间趋势分析）
    timestamp DATETIME NOT NULL COMMENT '告警发生时间',
    
    -- 文件信息
    file_path VARCHAR(1000) COMMENT '源文件路径（预留足够长度）',
    
    -- 原始数据（完整保存，支持未来重新解析）
    raw_data JSON COMMENT '告警原始数据（完整JSON）',
    
    -- 处理状态
    status VARCHAR(50) DEFAULT 'pending' COMMENT '处理状态(pending/processing/diagnosed/notified/failed)',
    
    -- 是否CCE集群（用于区分处理流程）
    is_cce_cluster BOOLEAN DEFAULT FALSE COMMENT '是否CCE集群告警',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 单列索引
    INDEX idx_alert_type (alert_type),
    INDEX idx_ip (ip),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_component (component),
    INDEX idx_severity (severity),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status),
    INDEX idx_is_cce_cluster (is_cce_cluster),
    INDEX idx_created_at (created_at),
    
    -- 复合索引（用于常见查询场景）
    INDEX idx_timestamp_severity (timestamp, severity),
    INDEX idx_cluster_timestamp (cluster_id, timestamp),
    INDEX idx_component_timestamp (component, timestamp),
    INDEX idx_status_timestamp (status, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警记录表';
```

**设计说明**：
- `cluster_id`: 新增字段，从文件名提取，用于CCE集群筛选和统计
- `hostname`: 新增字段，保存主机名/节点名
- `is_cce_cluster`: 新增字段，区分CCE集群和物理机，用于差异化处理
- `raw_data`: JSON字段保存完整原始数据，支持未来新增字段无需修改表结构
- 复合索引：支持时间趋势分析（按时间+维度查询）

### 2.3 诊断结果表 (diagnosis_results)
```sql
CREATE TABLE diagnosis_results (
    -- 基础信息
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    alert_id BIGINT NOT NULL COMMENT '关联告警ID（一对一）',
    
    -- 诊断来源
    source VARCHAR(50) NOT NULL COMMENT '诊断来源(manual/api/manual+api)',
    
    -- ========== 手册匹配结果 ==========
    manual_matched BOOLEAN DEFAULT FALSE COMMENT '是否匹配到手册',
    manual_name_zh VARCHAR(500) COMMENT '故障中文名称（预留足够长度）',
    manual_solution TEXT COMMENT '手册解决方案（完整文本）',
    manual_impact TEXT COMMENT '影响描述',
    manual_recovery TEXT COMMENT '恢复方案',
    danger_level VARCHAR(50) COMMENT '危害等级（严重/中等/轻微）',
    customer_aware BOOLEAN COMMENT '是否客户有感',
    
    -- ========== API诊断结果（仅CCE集群） ==========
    api_task_id VARCHAR(200) COMMENT 'API任务ID',
    api_status VARCHAR(50) COMMENT 'API任务状态(normal/abnormal/failed)',
    
    -- API诊断统计字段（用于快速查询）
    api_items_count INT DEFAULT 0 COMMENT '诊断项总数',
    api_error_count INT DEFAULT 0 COMMENT '错误项数量',
    api_warning_count INT DEFAULT 0 COMMENT '警告项数量',
    api_abnormal_count INT DEFAULT 0 COMMENT '异常项数量',
    
    -- API诊断完整报告（JSON格式，包含所有诊断项）
    api_diagnosis JSON COMMENT 'API诊断完整报告（包含raw_report）',
    
    -- ========== AI解读结果 ==========
    -- AI解读完整内容（Markdown格式）
    ai_interpretation TEXT COMMENT 'AI解读完整内容（Markdown）',
    
    -- AI解读提取字段（用于快速展示）
    ai_category VARCHAR(100) COMMENT 'AI问题分类',
    ai_root_cause TEXT COMMENT '根本原因分析',
    ai_impact TEXT COMMENT '影响评估',
    ai_solution TEXT COMMENT '修复建议',
    
    -- ========== 通知状态 ==========
    notified BOOLEAN DEFAULT FALSE COMMENT '是否已发送通知',
    notified_at DATETIME COMMENT '通知发送时间',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键和索引
    FOREIGN KEY (alert_id) REFERENCES alert_records(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_alert_id (alert_id),
    INDEX idx_source (source),
    INDEX idx_danger_level (danger_level),
    INDEX idx_api_status (api_status),
    INDEX idx_manual_matched (manual_matched)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断结果表';
```

**设计说明**：
- `api_items_count`, `api_error_count`, `api_warning_count`, `api_abnormal_count`: 新增统计字段，支持列表页快速查询
- `api_diagnosis`: JSON字段保存完整诊断报告（包含所有73个诊断项），支持详情页展示
- `notified`, `notified_at`: 新增通知状态字段
- 统计字段独立存储，避免每次都解析JSON

### 2.4 监控路径配置表 (monitor_paths)
```sql
CREATE TABLE monitor_paths (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    path VARCHAR(1000) NOT NULL COMMENT '监控路径（绝对路径）',
    description VARCHAR(500) COMMENT '路径描述',
    enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    priority INT DEFAULT 50 COMMENT '优先级（1-100，数值越大优先级越高）',
    file_pattern VARCHAR(200) DEFAULT '*.txt' COMMENT '文件匹配模式',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_path (path),
    INDEX idx_enabled_priority (enabled, priority DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='监控路径配置表';
```

**设计说明**：
- `path`: 监控的目录路径，唯一约束，防止重复配置
- `priority`: 优先级，用于多路径时的处理顺序
- `file_pattern`: 文件匹配模式，支持通配符（如 `*.txt`, `alert_*.log`）
- `enabled`: 启用/禁用开关，禁用后不监控该路径
- 复合索引 `idx_enabled_priority`: 优化查询启用的路径并按优先级排序

### 2.5 Webhook配置表 (webhook_configs)
```sql
CREATE TABLE webhook_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    name VARCHAR(200) NOT NULL COMMENT '配置名称',
    type VARCHAR(50) NOT NULL COMMENT 'Webhook类型(feishu/ruliu)',
    url VARCHAR(1000) NOT NULL COMMENT 'Webhook URL（预留足够长度）',
    access_token VARCHAR(500) COMMENT '访问令牌',
    secret VARCHAR(500) COMMENT '签名密钥',
    enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    
    -- 触发条件（JSON格式，支持复杂过滤规则）
    severity_filter VARCHAR(200) COMMENT '严重程度过滤(critical,warning)',
    component_filter VARCHAR(500) COMMENT '组件过滤(GPU,Memory)',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_type_enabled (type, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Webhook配置表';
```

### 2.6 故障手册表 (fault_manual)
```sql
CREATE TABLE fault_manual (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    category VARCHAR(100) NOT NULL COMMENT '类别(GPU/CPU/Memory等)',
    alert_type VARCHAR(200) NOT NULL COMMENT '告警类型',
    has_level VARCHAR(50) COMMENT 'HAS级别',
    name_zh VARCHAR(500) COMMENT '中文名称',
    impact TEXT COMMENT '影响描述',
    recovery_plan TEXT COMMENT '恢复方案',
    danger_level VARCHAR(50) COMMENT '危害等级',
    customer_aware BOOLEAN COMMENT '是否客户有感',
    manual_check TEXT COMMENT '手动判断方法',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_category_type (category, alert_type),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='故障手册表';
```

### 2.7 数据库迁移策略

**迁移脚本位置**: `backend/alembic/versions/`

**迁移命令**:
```bash
# 生成迁移脚本
alembic revision -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

**字段扩展示例**:
```python
# 新增字段（向后兼容）
op.add_column('alert_records', 
    sa.Column('region', sa.String(100), nullable=True, comment='区域'))

# 扩大字段长度
op.alter_column('alert_records', 'alert_type',
    existing_type=sa.String(200),
    type_=sa.String(500))
```

**详细的Schema演进指南请参考本文档附录B**。

---

## 3. 核心服务设计

### 3.1 文件监控服务 (FileWatcherService)

**职责**: 监控告警文件目录,检测文件变化

**实现方案**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List
from app.models.alert import MonitorPath

class AlertFileHandler(FileSystemEventHandler):
    def __init__(self, db_session):
        self.db = db_session
        self.observers = {}  # 存储每个路径的Observer
    
    def start_monitoring(self):
        """启动监控（从数据库加载配置）"""
        # 1. 从数据库获取启用的监控路径
        paths = self.db.query(MonitorPath).filter(
            MonitorPath.enabled == True
        ).order_by(MonitorPath.priority.desc()).all()
        
        # 2. 为每个路径创建Observer
        for path_config in paths:
            self.add_watch_path(path_config)
    
    def add_watch_path(self, path_config: MonitorPath):
        """添加监控路径"""
        observer = Observer()
        handler = PathSpecificHandler(
            path_config=path_config,
            processor=self.process_file
        )
        observer.schedule(handler, path_config.path, recursive=False)
        observer.start()
        
        self.observers[path_config.id] = observer
        logger.info(f"开始监控路径: {path_config.path} (优先级: {path_config.priority})")
    
    def remove_watch_path(self, path_id: int):
        """移除监控路径"""
        if path_id in self.observers:
            self.observers[path_id].stop()
            self.observers[path_id].join()
            del self.observers[path_id]
            logger.info(f"停止监控路径ID: {path_id}")
    
    def reload_paths(self):
        """重新加载监控路径（配置变更时调用）"""
        # 1. 停止所有现有监控
        for observer in self.observers.values():
            observer.stop()
            observer.join()
        self.observers.clear()
        
        # 2. 重新启动监控
        self.start_monitoring()
    
    def process_file(self, file_path: str, path_config: MonitorPath):
        """处理文件"""
        # 1. 验证文件格式（根据file_pattern）
        if not self.match_pattern(file_path, path_config.file_pattern):
            return
        
        # 2. 发送到消息队列
        from tasks import process_alert_file
        process_alert_file.delay(file_path)
        
        logger.info(f"文件已加入处理队列: {file_path}")
    
    def match_pattern(self, file_path: str, pattern: str) -> bool:
        """匹配文件模式"""
        import fnmatch
        from pathlib import Path
        filename = Path(file_path).name
        return fnmatch.fnmatch(filename, pattern)


class PathSpecificHandler(FileSystemEventHandler):
    """特定路径的事件处理器"""
    def __init__(self, path_config: MonitorPath, processor):
        self.path_config = path_config
        self.processor = processor
    
    def on_created(self, event):
        """新文件创建时触发"""
        if not event.is_directory:
            self.processor(event.src_path, self.path_config)
    
    def on_modified(self, event):
        """文件修改时触发"""
        if not event.is_directory:
            self.processor(event.src_path, self.path_config)
```

**配置动态更新**:
```python
# API调用后触发重新加载
@router.post("/monitor-paths")
async def create_monitor_path(path: MonitorPathCreate, db: Session = Depends(get_db)):
    # 1. 创建配置
    new_path = MonitorPath(**path.dict())
    db.add(new_path)
    db.commit()
    
    # 2. 通知文件监控服务重新加载
    from app.services.file_watcher import file_watcher_service
    file_watcher_service.reload_paths()
    
    return APIResponse(
        success=True,
        data=new_path.to_dict(),
        message="监控路径创建成功"
    )
```

**配置**:
- 监控路径: 从数据库动态加载
- 文件过滤: 根据 `file_pattern` 配置
- 轮询间隔: 10 秒
- 支持热重载: 配置变更后自动重新加载

---

### 3.2 告警解析服务 (AlertParserService)

**职责**: 解析告警文件,提取结构化数据

**解析流程**:
```python
def parse_alert_file(file_path: str) -> List[AlertRecord]:
    """解析告警文件"""
    # 1. 读取文件内容
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 2. 执行Python代码获取列表
    alert_list = eval(content)  # 安全性考虑:使用ast.literal_eval
    
    # 3. 提取字段
    records = []
    for alert in alert_list:
        record = {
            'alert_type': extract_alert_type(alert),
            'ip': extract_ip(alert),
            'instance_id': extract_instance_id(alert),
            'component': extract_component(alert),
            'severity': extract_severity(alert),
            'timestamp': extract_timestamp(alert),
            'raw_data': alert
        }
        records.append(record)
    
    return records
```

**字段提取规则**:
- `alert_type`: 从 `项目` 或 `中文` 字段提取
- `severity`: 从 `HAS级别` 字段提取
- `component`: 从 `类别` 字段提取
- `ip`: 从原始数据中查找 IP 模式
- `timestamp`: 从文件名或数据中提取

---

### 3.3 手册匹配服务 (ManualMatchService)

**职责**: 根据告警类型匹配故障手册

**匹配逻辑**:
```python
def match_manual(alert_type: str, component: str) -> Optional[ManualRecord]:
    """匹配故障手册"""
    # 1. 精确匹配: category + alert_type
    manual = db.query(FaultManual).filter(
        FaultManual.category == component,
        FaultManual.alert_type == alert_type
    ).first()
    
    if manual:
        return manual
    
    # 2. 模糊匹配: alert_type
    manual = db.query(FaultManual).filter(
        FaultManual.alert_type == alert_type
    ).first()
    
    return manual
```

**返回数据**:
```python
{
    "matched": True,
    "name_zh": "GPU掉卡",
    "solution": "换卡",
    "impact": "从PCIe总线掉卡，lspci看不到卡",
    "recovery": "换卡",
    "danger_level": "P0",
    "customer_aware": True
}
```

---

### 3.4 诊断API服务 (DiagnosisAPIService)

**职责**: 调用百度云CCE诊断接口

**调用流程**:
```python
async def diagnose_node(ip: str, cluster_id: str) -> dict:
    """诊断节点"""
    # 1. 创建诊断任务
    task_response = await create_diagnosis_task(
        cluster_id=cluster_id,
        type="node",
        target={"nodeName": ip}
    )
    task_id = task_response['taskId']
    
    # 2. 轮询任务状态
    max_retries = 60  # 5分钟超时
    for i in range(max_retries):
        status = await get_diagnosis_status(cluster_id, task_id)
        if status['result'] == 'succeeded':
            break
        await asyncio.sleep(5)
    
    # 3. 获取诊断报告
    report = await get_diagnosis_report(cluster_id, task_id)
    
    # 4. 提取异常项
    abnormal_items = extract_abnormal_items(report)
    
    return {
        'task_id': task_id,
        'status': status['result'],
        'abnormal_items': abnormal_items,
        'full_report': report
    }
```

**API配置**:
- Base URL: `https://cce.bj.baidubce.com`
- 认证: BCE Auth v1
- 超时: 5 分钟

---

### 3.5 AI解读服务 (AIInterpretationService)

**职责**: 调用AI接口解读诊断结果

**Prompt设计**:
```python
def build_prompt(alert: dict, diagnosis: dict) -> str:
    """构建AI提示词"""
    prompt = f"""
请分析以下硬件告警信息并提供专业的诊断建议:

## 告警基本信息
- 告警类型: {alert['alert_type']}
- 组件: {alert['component']}
- 严重程度: {alert['severity']}
- 实例IP: {alert['ip']}
- 发生时间: {alert['timestamp']}

## 手册匹配结果
{format_manual_result(diagnosis.get('manual'))}

## 诊断API结果
{format_api_result(diagnosis.get('api'))}

请提供以下内容:
1. **故障根本原因**: 分析导致此故障的根本原因
2. **影响评估**: 评估对业务的影响程度和范围
3. **修复建议**: 提供详细的修复步骤和预防措施
4. **故障分类**: 将故障归类(硬件故障/配置问题/环境问题/其他)

请用专业但易懂的语言回答,重点突出可操作性。
"""
    return prompt
```

**调用示例**:
```python
async def interpret_diagnosis(alert: dict, diagnosis: dict) -> dict:
    """AI解读"""
    prompt = build_prompt(alert, diagnosis)
    
    response = await call_ai_api(
        prompt=prompt,
        temperature=0.3,  # 降低随机性
        max_tokens=1000
    )
    
    # 解析AI响应
    interpretation = parse_ai_response(response)
    
    return {
        'interpretation': interpretation['full_text'],
        'root_cause': interpretation['root_cause'],
        'impact': interpretation['impact'],
        'solution': interpretation['solution'],
        'category': interpretation['category']
    }
```

---

### 3.6 Webhook通知服务 (WebhookNotificationService)

**职责**: 发送告警通知到飞书/如流

**通知模板**:
```python
def build_feishu_card(alert: dict, diagnosis: dict) -> dict:
    """构建飞书卡片"""
    severity_color = {
        'FAIL': 'red',
        'ERROR': 'orange',
        'WARN': 'yellow'
    }
    
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": f"🚨 {alert['component']}硬件告警",
                    "tag": "plain_text"
                },
                "template": severity_color.get(alert['severity'], 'blue')
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"""**告警类型**: {alert['alert_type']}
**实例IP**: {alert['ip']}
**严重程度**: {alert['severity']}
**发生时间**: {alert['timestamp']}
**解决方案**: {diagnosis.get('solution', '请查看详情')}""",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "查看详情",
                                "tag": "plain_text"
                            },
                            "url": f"http://10.175.96.168/alerts/{alert['id']}",
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }
    return card
```

**发送逻辑**:
```python
async def send_notification(alert: dict, diagnosis: dict):
    """发送通知"""
    # 1. 获取启用的Webhook配置
    webhooks = get_enabled_webhooks(
        severity=alert['severity'],
        component=alert['component']
    )
    
    # 2. 并发发送
    tasks = []
    for webhook in webhooks:
        if webhook['type'] == 'feishu':
            card = build_feishu_card(alert, diagnosis)
            task = send_feishu_webhook(webhook['url'], card)
        elif webhook['type'] == 'ruliu':
            card = build_ruliu_card(alert, diagnosis)
            task = send_ruliu_webhook(webhook['url'], card)
        tasks.append(task)
    
    # 3. 等待所有发送完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. 记录发送结果
    log_notification_results(alert['id'], results)
```

---

## 4. API 接口设计

### 4.1 API 响应格式规范

**所有API遵循统一响应格式**（详见 `.kiro/steering/api-response-format.md`）：
```json
{
  "success": boolean,
  "data": object | array | null,
  "message": string,
  "error": string | null
}
```

**分页接口统一格式**：
```json
{
  "success": true,
  "data": {
    "list": [],           // 数据列表
    "total": 100,         // 总数
    "page": 1,            // 当前页
    "page_size": 20       // 每页数量
  }
}
```

### 4.2 告警管理 API

#### 4.2.1 获取告警列表（支持筛选、分页、排序）
```
GET /api/v1/alerts

Query参数:
- page: int = 1                    // 页码，默认1
- page_size: int = 20              // 每页数量，默认20，最大100
- alert_type: str (可选)           // 告警类型
- severity: str (可选)             // 严重程度（critical/warning/info）
- component: str (可选)            // 组件类型（GPU/Memory/CPU）
- status: str (可选)               // 处理状态
- start_time: datetime (可选)      // 开始时间（ISO格式）
- end_time: datetime (可选)        // 结束时间（ISO格式）

响应:
{
    "success": true,
    "data": {
        "list": [
            {
                "id": 1,
                "alert_type": "BWDrop",
                "ip": "10.90.1.50",
                "component": "GPU",
                "severity": "critical",
                "timestamp": "2026-02-10T10:30:00Z",
                "status": "diagnosed",
                "has_diagnosis": true
            }
        ],
        "total": 100,
        "page": 1,
        "page_size": 20
    },
    "message": "获取成功"
}
```

**实际实现说明**:
- 实际API路径：`/alerts`（在router中注册为`/api/v1/alerts`）
- 已实现的筛选参数：`alert_type`, `severity`, `component`, `status`, `start_time`, `end_time`
- 排序：固定按 `timestamp DESC` 排序
- 响应字段简化：只返回核心字段和 `has_diagnosis` 标识

**SQL查询示例**:
```sql
SELECT 
    a.id, a.alert_type, a.ip, a.cluster_id, a.hostname,
    a.component, a.severity, a.timestamp, a.status, a.is_cce_cluster,
    a.created_at,
    CASE WHEN d.id IS NOT NULL THEN TRUE ELSE FALSE END as has_diagnosis,
    d.danger_level, d.manual_matched, 
    d.api_error_count, d.api_warning_count
FROM alert_records a
LEFT JOIN diagnosis_results d ON a.id = d.alert_id
WHERE a.timestamp BETWEEN :start_time AND :end_time
  AND (:severity IS NULL OR a.severity = :severity)
  AND (:component IS NULL OR a.component = :component)
  AND (:cluster_id IS NULL OR a.cluster_id = :cluster_id)
ORDER BY a.timestamp DESC
LIMIT :limit OFFSET :offset;
```

#### 4.2.2 获取告警详情
```
GET /api/v1/alerts/{alert_id}

响应:
{
    "success": true,
    "data": {
        "alert": {
            "id": 1,
            "alert_type": "BWDrop",
            "ip": "10.90.1.50",
            "cluster_id": "cce-xrg955qz",
            "hostname": "cce-xrg955qz-ktg4ihz6",
            "instance_id": null,
            "component": "GPU",
            "severity": "critical",
            "timestamp": "2026-02-10T10:30:00Z",
            "file_path": "/data/alerts/xxx.txt",
            "status": "diagnosed",
            "is_cce_cluster": true,
            "raw_data": {
                // 完整的原始告警数据
            },
            "created_at": "2026-02-10T10:31:00Z",
            "updated_at": "2026-02-10T10:35:00Z"
        },
        "diagnosis": {
            "id": 1,
            "source": "manual+api",
            
            // 手册匹配结果
            "manual_matched": true,
            "manual_name_zh": "GPU带宽下降",
            "manual_solution": "检查GPU硬件状态，必要时更换GPU",
            "manual_impact": "可能导致计算任务性能下降",
            "manual_recovery": "重启节点或更换GPU",
            "danger_level": "严重",
            "customer_aware": true,
            
            // API诊断结果统计
            "api_task_id": "cce-xrg955qz-20260210-xxx",
            "api_status": "abnormal",
            "api_items_count": 73,
            "api_error_count": 3,
            "api_warning_count": 5,
            "api_abnormal_count": 2,
            
            // API诊断详细项（包含所有73个诊断项）
            "api_diagnosis": {
                "task_id": "cce-xrg955qz-20260210-xxx",
                "task_result": "abnormal",
                "all_items": [...],  // 所有诊断项
                "error_items": [...],
                "warning_items": [...],
                "raw_report": {...}  // 完整原始报告
            },
            
            // AI解读结果
            "ai_interpretation": "# 问题诊断\n\n...",  // Markdown格式
            "ai_category": "硬件故障",
            "ai_root_cause": "GPU硬件故障导致带宽下降",
            "ai_impact": "计算任务失败，影响业务",
            "ai_solution": "立即更换GPU硬件",
            
            // 通知状态
            "notified": true,
            "notified_at": "2026-02-10T10:36:00Z",
            
            "created_at": "2026-02-10T10:32:00Z",
            "updated_at": "2026-02-10T10:35:00Z"
        }
    },
    "message": "获取成功"
}
```

#### 4.2.3 手动触发诊断
```
POST /api/v1/alerts/{alert_id}/diagnose

请求体:
{
    "force": false  // 是否强制重新诊断
}

响应:
{
    "success": true,
    "data": {
        "task_id": "xxx",
        "status": "processing"
    },
    "message": "诊断任务已创建"
}
```

---

### 4.3 统计分析 API

#### 4.3.1 告警趋势统计
```
GET /api/v1/alerts/statistics/trend

Query参数:
- start_time: str                  // 开始时间
- end_time: str                    // 结束时间
- group_by: str = "day"            // 分组方式（day/hour/week/month）
- cluster_id: str (可选)           // 按集群筛选
- component: str (可选)            // 按组件筛选

响应:
{
    "success": true,
    "data": {
        "trend": [
            {
                "date": "2026-02-01",
                "total": 15,
                "critical": 5,
                "warning": 8,
                "info": 2
            },
            {
                "date": "2026-02-02",
                "total": 20,
                "critical": 8,
                "warning": 10,
                "info": 2
            }
        ],
        "summary": {
            "total_alerts": 150,
            "avg_per_day": 15,
            "peak_date": "2026-02-05",
            "peak_count": 30
        }
    },
    "message": "获取成功"
}
```

**SQL查询示例**:
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total,
    SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
    SUM(CASE WHEN severity='warning' THEN 1 ELSE 0 END) as warning,
    SUM(CASE WHEN severity='info' THEN 1 ELSE 0 END) as info
FROM alert_records
WHERE timestamp BETWEEN :start_time AND :end_time
  AND (:cluster_id IS NULL OR cluster_id = :cluster_id)
  AND (:component IS NULL OR component = :component)
GROUP BY DATE(timestamp)
ORDER BY date;
```

#### 4.3.2 告警类型分布
```
GET /api/v1/alerts/statistics/distribution

Query参数:
- start_time: str
- end_time: str
- dimension: str = "alert_type"    // 维度（alert_type/component/severity/cluster）

响应:
{
    "success": true,
    "data": {
        "distribution": [
            {"name": "BWDrop", "count": 45, "percentage": 30.0},
            {"name": "LaneDrop", "count": 30, "percentage": 20.0},
            {"name": "EccLimitExceeded", "count": 25, "percentage": 16.7}
        ],
        "total": 150
    },
    "message": "获取成功"
}
```

#### 4.3.3 集群/节点告警排行
```
GET /api/v1/alerts/statistics/top-nodes

Query参数:
- start_time: str
- end_time: str
- limit: int = 10
- order_by: str = "total"          // 排序字段（total/critical）

响应:
{
    "success": true,
    "data": {
        "top_nodes": [
            {
                "cluster_id": "cce-xrg955qz",
                "ip": "10.90.1.50",
                "hostname": "cce-xrg955qz-ktg4ihz6",
                "total_alerts": 25,
                "critical_count": 10,
                "warning_count": 12,
                "info_count": 3,
                "last_alert_time": "2026-02-10T10:30:00Z"
            }
        ]
    },
    "message": "获取成功"
}
```

---

### 4.4 告警日志路径配置 API

#### 4.4.1 获取监控路径列表

```
GET /api/v1/monitor-paths

响应:
{
    "success": true,
    "data": {
        "list": [
            {
                "id": 1,
                "path": "/data/HAS_file/changan/",
                "description": "长安项目告警日志",
                "enabled": true,
                "priority": 100,
                "file_pattern": "*.txt",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-02-10T10:00:00Z"
            },
            {
                "id": 2,
                "path": "/data/HAS_file/backup/",
                "description": "备份告警日志",
                "enabled": false,
                "priority": 50,
                "file_pattern": "*.log",
                "created_at": "2026-01-15T00:00:00Z",
                "updated_at": "2026-02-10T10:00:00Z"
            }
        ],
        "total": 2,
        "page": 1,
        "page_size": 20
    },
    "message": "获取成功"
}
```

#### 4.4.2 创建监控路径

```
POST /api/v1/monitor-paths

请求体:
{
    "path": "/data/HAS_file/new_project/",
    "description": "新项目告警日志",
    "enabled": true,
    "priority": 80,
    "file_pattern": "*.txt"
}

响应:
{
    "success": true,
    "data": {
        "id": 3,
        "path": "/data/HAS_file/new_project/",
        "description": "新项目告警日志",
        "enabled": true,
        "priority": 80,
        "file_pattern": "*.txt",
        "created_at": "2026-02-10T10:30:00Z",
        "updated_at": "2026-02-10T10:30:00Z"
    },
    "message": "监控路径创建成功"
}
```

#### 4.4.3 更新监控路径

```
PUT /api/v1/monitor-paths/{path_id}

请求体:
{
    "description": "更新后的描述",
    "enabled": false,
    "priority": 60,
    "file_pattern": "*.log"
}

响应:
{
    "success": true,
    "data": {
        "id": 3,
        "path": "/data/HAS_file/new_project/",
        "description": "更新后的描述",
        "enabled": false,
        "priority": 60,
        "file_pattern": "*.log",
        "created_at": "2026-02-10T10:30:00Z",
        "updated_at": "2026-02-10T11:00:00Z"
    },
    "message": "监控路径更新成功"
}
```

#### 4.4.4 删除监控路径

```
DELETE /api/v1/monitor-paths/{path_id}

响应:
{
    "success": true,
    "data": null,
    "message": "监控路径删除成功"
}
```

#### 4.4.5 测试监控路径

```
POST /api/v1/monitor-paths/{path_id}/test

响应:
{
    "success": true,
    "data": {
        "path_exists": true,
        "readable": true,
        "writable": false,
        "file_count": 15,
        "sample_files": [
            "alert_20260210_001.txt",
            "alert_20260210_002.txt",
            "alert_20260210_003.txt"
        ]
    },
    "message": "路径测试成功"
}
```

#### 4.4.6 批量启用/禁用监控路径

```
POST /api/v1/monitor-paths/batch-update

请求体:
{
    "path_ids": [1, 2, 3],
    "enabled": true
}

响应:
{
    "success": true,
    "data": {
        "updated_count": 3,
        "failed_ids": []
    },
    "message": "批量更新成功"
}
```

---

### 4.5 Webhook管理 API

#### 4.5.1 获取Webhook列表
```
GET /api/v1/webhooks

响应:
{
    "success": true,
    "data": {
        "list": [
            {
                "id": 1,
                "name": "飞书告警通知",
                "type": "feishu",
                "url": "https://...",
                "enabled": true,
                "severity_filter": "critical,warning",
                "created_at": "2026-01-01T00:00:00Z"
            }
        ]
    },
    "message": "获取成功"
}
```

#### 4.5.2 创建Webhook
```
POST /api/v1/webhooks

请求体:
{
    "name": "飞书告警通知",
    "type": "feishu",
    "url": "https://...",
    "access_token": "xxx",
    "severity_filter": "critical,warning",
    "component_filter": "GPU,Memory"
}

响应:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "飞书告警通知"
    },
    "message": "Webhook创建成功"
}
```

#### 4.5.3 测试Webhook
```
POST /api/v1/webhooks/{webhook_id}/test

响应:
{
    "success": true,
    "data": {
        "status": "success",
        "response_time": 123
    },
    "message": "Webhook测试成功"
}
```

---

### 4.6 筛选选项API

```
GET /api/v1/alerts/filter-options

响应:
{
    "success": true,
    "data": {
        "alert_types": ["BWDrop", "LaneDrop", "EccLimitExceeded"],
        "components": ["GPU", "Memory", "CPU", "Motherboard"],
        "clusters": ["cce-xrg955qz", "cce-abc123"],
        "severity_levels": ["critical", "warning", "info"],
        "statuses": ["pending", "processing", "diagnosed", "notified", "failed"]
    },
    "message": "获取成功"
}
```

---

### 4.7 完整API设计文档

详细的API设计文档（包含SQL查询示例、性能优化建议、错误处理等）请参考本文档附录A。

---

## 5. 异步任务设计

### 5.1 Celery任务

**任务类型**:
1. `process_alert_file`: 处理告警文件
2. `diagnose_alert`: 诊断告警
3. `send_webhook_notification`: 发送Webhook通知
4. `cleanup_old_alerts`: 清理旧告警数据

**任务配置**:
```python
# celery_config.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/1'

task_routes = {
    'tasks.process_alert_file': {'queue': 'high_priority'},
    'tasks.diagnose_alert': {'queue': 'normal'},
    'tasks.send_webhook_notification': {'queue': 'high_priority'},
    'tasks.cleanup_old_alerts': {'queue': 'low_priority'}
}

task_time_limit = 600  # 10分钟超时
```

---

## 6. 前端设计

### 6.1 页面结构
```
/alerts                 # 告警列表页
/alerts/:id             # 告警详情页
/webhooks               # Webhook配置页
/monitor-paths          # 告警日志路径配置页
/statistics             # 统计报表页
```

### 6.2 核心组件

#### AlertList.vue
- 表格展示告警列表
- 支持筛选、搜索、分页
- 快速操作: 查看详情、重新诊断

#### AlertDetail.vue
- 告警基本信息
- 诊断结果展示
- AI解读内容
- 操作历史时间线

#### MonitorPathConfig.vue
- 监控路径列表（表格展示）
- 添加/编辑/删除监控路径
- 启用/禁用开关
- 优先级设置（拖拽排序）
- 测试路径连接
- 批量操作（批量启用/禁用）

**功能详情**：
```vue
<template>
  <div class="monitor-path-config">
    <!-- 操作栏 -->
    <el-row :gutter="20" class="toolbar">
      <el-col :span="12">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加监控路径
        </el-button>
        <el-button @click="handleBatchEnable">批量启用</el-button>
        <el-button @click="handleBatchDisable">批量禁用</el-button>
      </el-col>
      <el-col :span="12" class="text-right">
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </el-col>
    </el-row>

    <!-- 监控路径表格 -->
    <el-table
      :data="pathList"
      @selection-change="handleSelectionChange"
      row-key="id"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="path" label="监控路径" min-width="200" />
      <el-table-column prop="description" label="描述" min-width="150" />
      <el-table-column prop="file_pattern" label="文件模式" width="120" />
      <el-table-column prop="priority" label="优先级" width="100" sortable />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.enabled"
            @change="handleToggleEnable(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleTest(row)">
            测试
          </el-button>
          <el-button link type="primary" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button link type="danger" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="监控路径" prop="path">
          <el-input v-model="formData.path" placeholder="/data/HAS_file/project/" />
          <div class="form-tip">请输入绝对路径，如：/data/HAS_file/changan/</div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" placeholder="项目告警日志" />
        </el-form-item>
        <el-form-item label="文件模式" prop="file_pattern">
          <el-input v-model="formData.file_pattern" placeholder="*.txt" />
          <div class="form-tip">支持通配符，如：*.txt, alert_*.log</div>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-slider v-model="formData.priority" :min="1" :max="100" show-input />
          <div class="form-tip">数值越大优先级越高（1-100）</div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
```

#### WebhookConfig.vue
- Webhook列表
- 添加/编辑/删除Webhook
- 测试Webhook连接

#### StatisticsChart.vue
- 告警趋势图(折线图)
- 告警分布图(饼图)
- 组件故障统计(柱状图)

---

## 7. 部署方案

### 7.1 Docker Compose配置
```yaml
version: '3.8'

services:
  alert-api:
    build: ./backend
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=mysql://user:pass@db:3306/alerts
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - /data/HAS_file/changan:/data/alerts:ro
    depends_on:
      - db
      - redis

  alert-worker:
    build: ./backend
    command: celery -A tasks worker -l info
    environment:
      - DATABASE_URL=mysql://user:pass@db:3306/alerts
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - /data/HAS_file/changan:/data/alerts:ro
    depends_on:
      - db
      - redis

  alert-frontend:
    build: ./frontend
    ports:
      - "8080:80"
    depends_on:
      - alert-api

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=alerts
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
```

---

## 8. 监控与日志

### 8.1 日志规范
```python
import logging

logger = logging.getLogger(__name__)

# 日志级别
# DEBUG: 详细调试信息
# INFO: 正常流程信息
# WARNING: 警告信息
# ERROR: 错误信息
# CRITICAL: 严重错误

# 日志格式
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
```

### 8.2 监控指标
- 文件处理速度: 文件/秒
- API调用成功率: %
- Webhook发送成功率: %
- 数据库查询响应时间: ms
- 告警处理延迟: 秒

---

## 9. 安全设计

### 9.1 数据安全
- 敏感信息加密存储(access_token, secret)
- 数据库连接使用SSL
- API调用使用HTTPS

### 9.2 访问控制
- API接口鉴权(JWT Token)
- 前端路由守卫
- 操作日志记录

---

## 10. 性能优化

### 10.1 数据库优化
- 合理使用索引
- 分页查询
- 定期清理旧数据(保留90天)

### 10.2 缓存策略
- Redis缓存手册数据
- Redis缓存统计结果(5分钟过期)

### 10.3 异步处理
- 文件解析异步化
- 诊断API调用异步化
- Webhook发送异步化


---

# 附录

## 附录A: 完整API设计文档

### A.1 告警列表API详细设计

**SQL查询优化示例**:
```sql
-- 使用复合索引优化查询
SELECT 
    a.id, a.alert_type, a.ip, a.cluster_id, a.hostname,
    a.component, a.severity, a.timestamp, a.status, a.is_cce_cluster,
    a.created_at,
    CASE WHEN d.id IS NOT NULL THEN TRUE ELSE FALSE END as has_diagnosis,
    d.danger_level, d.manual_matched, 
    d.api_error_count, d.api_warning_count
FROM alert_records a
LEFT JOIN diagnosis_results d ON a.id = d.alert_id
WHERE a.timestamp BETWEEN :start_time AND :end_time
  AND (:severity IS NULL OR a.severity = :severity)
  AND (:component IS NULL OR a.component = :component)
  AND (:cluster_id IS NULL OR a.cluster_id = :cluster_id)
ORDER BY a.timestamp DESC
LIMIT :limit OFFSET :offset;
```

### A.2 统计分析API详细设计

**告警趋势统计SQL**:
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total,
    SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical,
    SUM(CASE WHEN severity='warning' THEN 1 ELSE 0 END) as warning,
    SUM(CASE WHEN severity='info' THEN 1 ELSE 0 END) as info
FROM alert_records
WHERE timestamp BETWEEN :start_time AND :end_time
  AND (:cluster_id IS NULL OR cluster_id = :cluster_id)
  AND (:component IS NULL OR component = :component)
GROUP BY DATE(timestamp)
ORDER BY date;
```

**告警类型分布SQL**:
```sql
SELECT 
    alert_type as name,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM alert_records 
                               WHERE timestamp BETWEEN :start_time AND :end_time), 2) as percentage
FROM alert_records
WHERE timestamp BETWEEN :start_time AND :end_time
GROUP BY alert_type
ORDER BY count DESC;
```

**集群告警排行SQL**:
```sql
SELECT 
    cluster_id,
    ip,
    hostname,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN severity='critical' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN severity='warning' THEN 1 ELSE 0 END) as warning_count,
    SUM(CASE WHEN severity='info' THEN 1 ELSE 0 END) as info_count,
    MAX(timestamp) as last_alert_time
FROM alert_records
WHERE timestamp BETWEEN :start_time AND :end_time
GROUP BY cluster_id, ip, hostname
ORDER BY total_alerts DESC
LIMIT :limit;
```

### A.3 前端图表展示建议

**告警趋势图（折线图）**:
- X轴：时间
- Y轴：告警数量
- 多条线：critical/warning/info
- 支持时间范围切换（1小时/24小时/7天/30天）

**告警类型分布（饼图）**:
- 各告警类型占比
- 点击可跳转到对应告警列表

**组件告警分布（柱状图）**:
- X轴：组件类型
- Y轴：告警数量
- 分组：严重程度

**集群告警热力图**:
- 显示各集群的告警密度
- 颜色深浅表示告警数量

### A.4 性能优化策略

**缓存策略**:
```python
# 统计数据缓存5分钟
@cache(expire=300)
def get_alert_statistics(start_time, end_time):
    pass

# 筛选选项缓存1小时
@cache(expire=3600)
def get_filter_options():
    pass
```

**分页限制**:
```python
# 限制最大分页数量
MAX_PAGE_SIZE = 100
page_size = min(page_size, MAX_PAGE_SIZE)
```

### A.5 错误处理规范

**参数错误**:
```json
{
  "success": false,
  "error": "参数错误：page_size不能超过100",
  "message": "请求失败"
}
```

**数据不存在**:
```json
{
  "success": false,
  "error": "告警记录不存在",
  "message": "获取失败"
}
```

**服务器错误**:
```json
{
  "success": false,
  "error": "数据库查询失败",
  "message": "服务器内部错误"
}
```

---

## 附录B: 数据库Schema演进指南

### B.1 字段扩展场景

**场景1：新增告警字段**

问题：告警文件新增了`region`字段（区域信息）

解决方案：
```python
# 方案A：直接存入raw_data（推荐）
# 无需修改表结构，数据自动保存在raw_data JSON字段

# 方案B：如果需要按region统计，提取到独立列
# 1. 创建迁移脚本
op.add_column('alert_records', 
    sa.Column('region', sa.String(100), nullable=True, comment='区域'))

# 2. 数据迁移（从raw_data提取）
op.execute("""
    UPDATE alert_records 
    SET region = JSON_EXTRACT(raw_data, '$.region')
    WHERE raw_data IS NOT NULL
""")

# 3. 创建索引
op.create_index('idx_region', 'alert_records', ['region'])
```

**场景2：字段长度不够**

问题：`alert_type`字段长度从200不够用

解决方案：
```python
# 创建迁移脚本
op.alter_column('alert_records', 'alert_type',
    existing_type=sa.String(200),
    type_=sa.String(500),  # 扩大长度
    existing_nullable=False)
```

**场景3：新增统计维度**

问题：需要按"故障根因"统计

解决方案：
```python
# 1. 新增字段
op.add_column('diagnosis_results',
    sa.Column('root_cause_category', sa.String(100), 
              nullable=True, comment='根因分类'))

# 2. 数据回填（从AI解读中提取）
# 可以写一个脚本重新分析历史数据

# 3. 创建索引
op.create_index('idx_root_cause', 'diagnosis_results', ['root_cause_category'])
```

### B.2 数据迁移最佳实践

**创建迁移脚本**:
```bash
# 生成迁移脚本
cd backend
alembic revision -m "add_region_field"
```

**编写迁移逻辑**:
```python
def upgrade():
    # 1. 新增字段
    op.add_column('alert_records', 
        sa.Column('region', sa.String(100), nullable=True))
    
    # 2. 数据迁移
    connection = op.get_bind()
    connection.execute("""
        UPDATE alert_records 
        SET region = JSON_EXTRACT(raw_data, '$.region')
        WHERE raw_data IS NOT NULL
    """)
    
    # 3. 创建索引
    op.create_index('idx_region', 'alert_records', ['region'])

def downgrade():
    # 回滚操作
    op.drop_index('idx_region', 'alert_records')
    op.drop_column('alert_records', 'region')
```

**执行迁移**:
```bash
# 测试环境先验证
alembic upgrade head

# 生产环境执行
# 1. 备份数据库
mysqldump -u root -p mcp_db > backup_$(date +%Y%m%d).sql

# 2. 执行迁移
alembic upgrade head

# 3. 验证数据
python3 -c "from app.models.alert import AlertRecord; print('OK')"
```

### B.3 性能优化建议

**索引策略**:

单列索引（用于单一条件查询）：
```python
Index('idx_timestamp', 'timestamp')
Index('idx_severity', 'severity')
```

复合索引（用于组合条件查询）：
```python
Index('idx_timestamp_severity', 'timestamp', 'severity')
Index('idx_cluster_timestamp', 'cluster_id', 'timestamp')
```

**JSON字段查询优化**:
```sql
-- 提取JSON字段
SELECT JSON_EXTRACT(raw_data, '$.hostname') as hostname
FROM alert_records;

-- JSON字段条件查询
SELECT * FROM alert_records
WHERE JSON_EXTRACT(raw_data, '$.region') = 'cn-north';

-- 创建虚拟列索引（MySQL 5.7.8+）
ALTER TABLE alert_records 
ADD COLUMN region_virtual VARCHAR(100) 
AS (JSON_UNQUOTE(JSON_EXTRACT(raw_data, '$.region'))) VIRTUAL;

CREATE INDEX idx_region_virtual ON alert_records(region_virtual);
```

**分区策略（大数据量场景）**:
```sql
ALTER TABLE alert_records
PARTITION BY RANGE (TO_DAYS(timestamp)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

### B.4 常见问题

**Q1: 如何处理字段类型变更？**

A: 尽量避免类型变更。如果必须变更：
1. 新增一个字段（新类型）
2. 数据迁移到新字段
3. 旧字段标记为废弃（不删除）
4. 前端逐步切换到新字段

**Q2: JSON字段查询性能差怎么办？**

A: 
1. 提取高频查询字段到独立列
2. 使用虚拟列+索引
3. 使用缓存（Redis）

**Q3: 如何回滚数据库变更？**

A:
```bash
# 查看当前版本
alembic current

# 回滚到上一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>
```

**Q4: 生产环境迁移注意事项？**

A:
1. **必须先备份数据库**
2. **在测试环境完整验证**
3. **选择低峰期执行**
4. **准备回滚方案**
5. **监控迁移过程**

### B.5 总结

**核心原则**：
1. ✅ 关键字段提取到独立列（支持高效查询）
2. ✅ 完整数据保存在JSON字段（支持灵活扩展）
3. ✅ 字段长度留足余量（避免频繁修改）
4. ✅ 只增不减（保持向后兼容）
5. ✅ 数据迁移脚本化（可重复执行）

这样的设计可以在不频繁修改表结构的情况下，支持业务的快速迭代！
