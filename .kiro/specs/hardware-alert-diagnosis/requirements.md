# 硬件告警智能诊断系统 - 需求文档

## 1. 项目概述

### 1.1 背景
- 厂内机器 `/data/HAS_file/changan/` 目录每天定期更新硬件告警文件
- 告警数据包含 GPU、主板、内存、硬盘等硬件故障信息
- 现有故障维修手册包含详细的故障类型和解决方案
- 需要自动化处理告警数据,提供智能诊断和解决方案

### 1.2 目标
构建一个自动化的硬件告警诊断系统,实现:
1. 自动监控和解析告警文件
2. 智能匹配故障维修手册
3. 调用诊断 API 获取深度诊断结果
4. AI 解读诊断结果并分类
5. 通过 Webhook 推送告警通知
6. 提供前端界面展示历史告警记录

### 1.3 开发方式
- 在本地独立文件夹进行开发和测试
- 测试完成后与当前 MCP 项目合并部署
- 使用 Spec 驱动开发流程

---

## 2. 用户故事

### 2.1 系统管理员
**作为** 系统管理员  
**我想要** 系统自动监控告警文件并解析  
**以便** 及时发现硬件故障,无需手动检查文件

### 2.2 运维工程师
**作为** 运维工程师  
**我想要** 查看告警的智能诊断结果和解决方案  
**以便** 快速定位问题并采取修复措施

### 2.3 技术负责人
**作为** 技术负责人  
**我想要** 查看告警统计和分类报告  
**以便** 了解硬件故障趋势,优化资源配置

### 2.4 客户团队
**作为** 客户团队成员  
**我想要** 通过飞书/如流接收告警通知  
**以便** 第一时间了解硬件故障情况

---

## 3. 功能需求

### 3.1 文件监控服务
**优先级**: P0 (核心功能)

**需求描述**:
- 监控 `/data/HAS_file/changan/` 目录的文件变化
- 检测新增或更新的告警文件
- 触发告警解析流程

**验收标准**:
1. 系统能够实时检测目录中的文件变化
2. 新文件出现后 30 秒内触发解析
3. 支持批量处理历史文件
4. 文件解析失败时记录错误日志

---

### 3.2 告警解析服务
**优先级**: P0 (核心功能)

**需求描述**:
- 解析告警文件中的 Python 列表数据
- 提取关键信息:告警类型、IP、实例ID、时间戳、严重程度等
- 数据验证和清洗

**验收标准**:
1. 正确解析所有告警文件格式
2. 提取的字段完整且准确
3. 处理异常数据时不中断流程
4. 解析性能: 单个文件 < 1 秒

**数据结构示例**:
```python
{
    "alert_type": "BWDrop",  # 告警类型
    "ip": "10.175.96.168",   # 实例IP
    "instance_id": "xxx",     # 实例ID
    "timestamp": "2026-01-26 10:30:00",
    "severity": "FAIL",       # 严重程度
    "component": "GPU",       # 组件类型
    "raw_data": {...}         # 原始数据
}
```

---

### 3.3 故障手册匹配服务
**优先级**: P0 (核心功能)

**需求描述**:
- 根据告警类型匹配故障维修手册
- 返回对应的解决方案、危害等级、恢复方案等
- 区分"手册内"和"手册外"告警

**验收标准**:
1. 准确匹配手册中的故障类型
2. 返回完整的故障信息(中文名称、危害等级、恢复方案等)
3. 未匹配到时标记为"手册外"
4. 匹配准确率 > 95%

**匹配逻辑**:
- 优先匹配: `告警类型` (如 BWDrop, LaneDrop)
- 次要匹配: `组件类型` + `HAS级别`
- 返回字段: 中文名称、危害等级、恢复方案、是否客户有感

---

### 3.4 诊断 API 调用服务
**优先级**: P1 (重要功能)

**需求描述**:
- 对于"手册外"告警,调用百度云 CCE 诊断接口
- 根据 IP/实例ID 发起诊断任务
- 轮询获取诊断结果
- 解析诊断报告中的异常内容

**验收标准**:
1. 成功创建诊断任务并获取 taskId
2. 轮询诊断状态直到完成(超时时间 5 分钟)
3. 正确解析诊断报告中的异常项
4. API 调用失败时记录错误并重试(最多 3 次)

**API 调用流程**:
```
1. POST /v2/cluster/{clusterId}/diagnosis
   - 参数: type=node, target={nodeName: IP}
   - 返回: taskId

2. GET /v2/cluster/{clusterId}/diagnoses?type=node
   - 轮询任务状态
   - 等待 result=succeeded

3. GET /v2/cluster/{clusterId}/diagnosis/{taskId}/report
   - 获取详细诊断报告
   - 提取 reportItems 中 result=false 的项
```

---

### 3.5 AI 解读服务
**优先级**: P1 (重要功能)

**需求描述**:
- 调用厂内 AI 接口解读诊断结果
- 输入: 手册匹配结果 或 诊断 API 结果
- 输出: 故障原因分析、影响评估、修复建议

**验收标准**:
1. AI 解读结果清晰易懂
2. 包含故障原因、影响范围、修复步骤
3. 解读时间 < 10 秒
4. 支持批量解读

**AI Prompt 模板**:
```
请分析以下硬件告警信息:
- 告警类型: {alert_type}
- 组件: {component}
- 严重程度: {severity}
- 手册解决方案: {manual_solution}
- 诊断结果: {diagnosis_result}

请提供:
1. 故障根本原因
2. 对业务的影响
3. 详细修复步骤
4. 预防措施
```

---

### 3.6 数据持久化
**优先级**: P0 (核心功能)

**需求描述**:
- 保存所有告警记录到数据库
- 保存诊断结果和 AI 解读
- 支持历史查询和统计

**验收标准**:
1. 所有告警数据完整保存
2. 支持按时间、类型、严重程度查询
3. 数据保留期 >= 90 天
4. 数据库性能: 查询响应 < 500ms

**数据库表结构**:
```sql
-- 告警记录表
CREATE TABLE alert_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    alert_type VARCHAR(100),
    ip VARCHAR(50),
    instance_id VARCHAR(100),
    component VARCHAR(50),
    severity VARCHAR(20),
    timestamp DATETIME,
    raw_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 诊断结果表
CREATE TABLE diagnosis_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    alert_id BIGINT,
    source VARCHAR(20),  -- 'manual' or 'api'
    manual_solution TEXT,
    api_diagnosis JSON,
    ai_interpretation TEXT,
    category VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alert_records(id)
);
```

---

### 3.7 Webhook 通知服务
**优先级**: P1 (重要功能)

**需求描述**:
- 支持飞书和如流 Webhook 配置
- 告警发生时自动推送通知
- 支持自定义通知模板和触发条件

**验收标准**:
1. 支持配置多个 Webhook 地址
2. 通知发送成功率 > 99%
3. 支持按严重程度过滤(只推送 FAIL 级别)
4. 通知内容包含: 告警类型、IP、时间、解决方案链接

**通知模板**:
```json
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "content": "🚨 硬件告警通知",
                "tag": "plain_text"
            }
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": "**告警类型**: GPU掉卡\n**实例IP**: 10.175.96.168\n**严重程度**: FAIL\n**发生时间**: 2026-01-26 10:30:00",
                    "tag": "lark_md"
                }
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
                        "url": "http://10.175.96.168/alerts/{alert_id}"
                    }
                ]
            }
        ]
    }
}
```

---

### 3.8 前端展示界面
**优先级**: P2 (次要功能)

**需求描述**:
- Webhook 配置管理页面
- 历史告警记录列表
- 告警详情页面(包含诊断结果和 AI 解读)
- 统计报表(按类型、时间、归属分类)

**验收标准**:
1. 支持分页查询(每页 20 条)
2. 支持多条件筛选(时间范围、类型、严重程度)
3. 支持导出 Excel 报表
4. 页面加载时间 < 2 秒

**页面功能**:
- **Webhook 配置页**: 添加/编辑/删除 Webhook,测试连接
- **告警列表页**: 表格展示,支持搜索和筛选
- **告警详情页**: 完整信息展示,包含时间线
- **统计报表页**: 图表展示(饼图、柱状图、趋势图)

---

## 4. 非功能需求

### 4.1 性能要求
- 文件解析: 单个文件 < 1 秒
- 手册匹配: < 100ms
- API 调用: 完整诊断流程 < 5 分钟
- AI 解读: < 10 秒
- 数据库查询: < 500ms
- 前端页面加载: < 2 秒

### 4.2 可靠性要求
- 系统可用性: >= 99.9%
- 文件监控服务自动重启
- API 调用失败自动重试(最多 3 次)
- 数据库连接池管理
- 异常情况记录详细日志

### 4.3 安全要求
- API 调用使用 HTTPS
- 敏感信息(access_token)加密存储
- 数据库访问权限控制
- 前端接口鉴权

### 4.4 可维护性要求
- 代码遵循项目规范(见 `.kiro/steering/rules.md`)
- 统一 API 响应格式(见 `.kiro/steering/api-response-format.md`)
- 完善的错误日志和监控
- 配置文件化管理

---

## 5. 技术约束

### 5.1 开发环境
- Python 3.8+
- FastAPI 框架
- MySQL 8.0+
- Vue 3 + Element Plus (前端)

### 5.2 部署环境
- 服务器: 10.175.96.168
- Docker 容器化部署
- 与现有 MCP 项目共享数据库

### 5.3 外部依赖
- 百度云 CCE 诊断 API
- 厂内 AI 接口
- 飞书/如流 Webhook API

---

## 6. 验收标准总结

### 6.1 核心功能验收
- [ ] 文件监控服务正常运行,能检测文件变化
- [ ] 告警解析准确率 100%
- [ ] 手册匹配准确率 > 95%
- [ ] 诊断 API 调用成功率 > 90%
- [ ] AI 解读结果清晰可用
- [ ] 数据完整保存到数据库
- [ ] Webhook 通知发送成功

### 6.2 性能验收
- [ ] 单个告警处理时间 < 30 秒(不含诊断 API)
- [ ] 数据库查询响应 < 500ms
- [ ] 前端页面加载 < 2 秒

### 6.3 可靠性验收
- [ ] 系统连续运行 7 天无崩溃
- [ ] 异常情况有完整日志记录
- [ ] API 调用失败能自动重试

---

## 7. 里程碑

### 阶段 1: 核心功能开发 (预计 5 天)
- 文件监控服务
- 告警解析服务
- 手册匹配服务
- 数据持久化

### 阶段 2: 扩展功能开发 (预计 3 天)
- 诊断 API 调用服务
- AI 解读服务
- Webhook 通知服务

### 阶段 3: 前端开发 (预计 3 天)
- Webhook 配置页面
- 告警列表和详情页面
- 统计报表页面

### 阶段 4: 测试与部署 (预计 2 天)
- 单元测试
- 集成测试
- 部署到生产环境
- 与 MCP 项目合并

---

## 8. 风险与挑战

### 8.1 技术风险
- **诊断 API 稳定性**: 百度云 API 可能超时或失败
  - **缓解措施**: 实现重试机制,记录失败日志

- **AI 接口响应时间**: AI 解读可能较慢
  - **缓解措施**: 异步处理,先保存基础信息

### 8.2 业务风险
- **告警文件格式变化**: 文件格式可能更新
  - **缓解措施**: 灵活的解析逻辑,版本兼容

- **手册更新**: 故障维修手册可能更新
  - **缓解措施**: 手册数据库化,支持在线更新

---

## 9. 附录

### 9.1 告警类型列表(部分)
- GPU: Missing, BWDrop, LaneDrop, EccLimitExceeded, xid48, xid79
- 主板: BusUncorrectableerror, BusFatalError, Predictivefailure
- 内存: UncorrectableECC, DIMMUE, DimmAssetMissing
- 硬盘: SMARTFail, HardwareError, Missing, NotReady
- 网卡: NetLinkDown, NicSpeedLow, NICCRC

### 9.2 参考文档
- 故障维修手册: `mcp/knowledge/故障维修手册.md`
- 诊断接口文档: `mcp/knowledge/故障诊断接口.md`
- 项目规范: `mcp/.kiro/steering/rules.md`
- API 规范: `mcp/.kiro/steering/api-response-format.md`
