# 如流机器人 AI Agent 改造方案

> 文档版本：v2（结合现有代码实际情况更新）

---

## 零、现状梳理

### 当前部署架构
```
宿主机 8120 端口（Flask）
├── ruliu_callback.py      # 消息接收、签名验证、规则路由
├── webhook_sender.py      # 独立进程，每5秒轮询结果文件，调如流API发消息
└── 直连宿主机 MySQL:3307  # cluster_management 库
```

### 关键约束
1. **内网服务器**，无法直接访问 Anthropic Claude、OpenAI 等外部 API
2. 可用 LLM：项目已接入的 `http://llms-se.baidu-int.com:8200`（OpenAI 兼容接口，含 ERNIE 系列 + DeepSeek + Qwen3 共 12 个模型，有自动 failover 机制）
3. 宿主机已部署 BGE-base-zh-v1.5 embedding 模型，端口 **8001**（FastAPI，已在运行）

---

## 一、如流 Channel 与多用户区分

### 消息接收机制（现有）
如流通过**企业级 Webhook 回调**把消息推送给服务器：
```
如流群消息 → 加密推送 → POST /ruliu/callback（Flask）
```

消息结构（AES ECB 解密后）：
```json
{
  "eventtype": "MESSAGE_RECEIVE",
  "groupid": 12345678,          // 群ID（整数），即 channel 标识
  "message": {
    "header": {
      "fromuserid": "user123"   // 发消息的用户ID，即 from_user
    },
    "body": [
      { "type": "TEXT", "content": "查 10.90.0.189" },
      { "type": "AT", ... }     // @机器人，解析时直接跳过
    ]
  }
}
```

### 多人对话如何区分用户
- **`groupid`**：标识是哪个群（channel），用作 session_id 前缀
- **`fromuserid`**：标识是哪个用户，用于：
  - 写操作归因（"谁处理了这条告警"）
  - 按用户隔离上下文（可选，见下）

### Session 隔离策略（两种选择）

| 策略 | session_id 构成 | 适用场景 |
|------|----------------|---------|
| **群级会话**（推荐） | `group:{groupid}` | 群内所有人共享对话上下文，适合运维群 |
| 用户级会话 | `user:{fromuserid}` | 每个人独立上下文，适合私聊或敏感查询 |

推荐群级会话：运维群里的对话通常是协作的，共享上下文更合理（"上面那条告警帮我关掉" → 所有人都知道在说哪条）。

---

## 二、复用现有 AI API（ERNIE Client）

### 现有机制可直接复用
`backend/app/services/ai/ernie_client.py` 已经实现了：
- **12 个模型自动 failover**（429/额度超限自动切换）
- **tenacity 重试**（超时/网络错误指数退避）
- **全局单例**（模型切换状态跨请求保持）

**问题**：ruliu_callback 是宿主机进程，backend 是 Docker 容器，无法直接 import。

### 复用方案
**方案 A：HTTP 调用（推荐）**
ruliu_callback 通过 `POST /api/v1/ai/chat` 端点调用，已有现成实现：
```python
# tool_executor.py 中
def _call_llm(self, messages: list, system_prompt: str) -> str:
    payload = {
        "messages": messages,
        "context_data": None,
        "temperature": 0.3,
        "max_tokens": 2048
    }
    resp = self.session.post(f"{API_BASE}/api/v1/ai/chat", json=payload)
    return resp.json()["content"]
```
优点：failover、重试、模型切换全部由容器内处理，宿主机无感知。

**方案 B：在宿主机复制一份 ernie_client.py**
直接复制 `ernie_client.py` 到 `callback_bot_systemd/`，宿主机独立维护。
缺点：两份代码需要同步维护。

---

## 三、BGE Embedding + RAG 记忆系统

### 服务信息（已确认）
- **地址**：`http://localhost:8001`
- **模型**：`bge-base-zh-v1.5`，向量维度 **768**
- **接口**：
  ```
  POST /embed
  Body:  {"texts": ["文本1", "文本2"], "normalize": true}
  返回:  {"success": true, "data": {"embeddings": [[...], [...]], "dimension": 768}}

  GET /health   → 健康检查
  GET /stats    → 请求统计
  ```

### RAG 的作用场景
1. **告警历史知识库**：把历史告警 + 处理方案向量化，新告警来了检索相似案例给出处理建议
2. **运维手册检索**：把排查文档向量化，回答"XXX 错误怎么处理"类问题
3. **长期记忆补充**：把重要对话摘要存入向量库，弥补 context 被截断的问题

### rag_retriever.py 完整实现

```python
"""
RAG 检索器
BGE Embedding (localhost:8001) + ChromaDB 本地向量库
"""
import os
import json
import requests
import chromadb
import pymysql
from datetime import datetime

BGE_URL = os.getenv("BGE_EMBEDDING_URL", "http://localhost:8001/embed")
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "/data/ruliu_callback/chroma_db")


class RAGRetriever:
    def __init__(self):
        self.chroma = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.chroma.get_or_create_collection(
            name="alerts_kb",
            metadata={"hnsw:space": "cosine"}
        )

    # ---------- Embedding ----------

    def embed(self, texts: list) -> list:
        """调用 BGE 服务批量向量化"""
        resp = requests.post(BGE_URL, json={"texts": texts, "normalize": True}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Embedding 失败: {data.get('error')}")
        return data["data"]["embeddings"]

    # ---------- 知识库构建（一次性/定期运行）----------

    def build_from_alerts(self, mysql_config: dict):
        """从已解决的告警记录构建知识库"""
        conn = pymysql.connect(**mysql_config, cursorclass=pymysql.cursors.DictCursor)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, alert_type, component, hostname, ip, message,
                           resolution_notes, resolved_at
                    FROM alerts
                    WHERE status = 'resolved'
                      AND resolution_notes IS NOT NULL
                      AND resolution_notes != ''
                    ORDER BY resolved_at DESC
                    LIMIT 2000
                """)
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            return 0

        # 批量处理（每批 16 条）
        batch_size = 16
        added = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            docs, ids, metas = [], [], []
            for r in batch:
                doc = (
                    f"告警类型:{r['alert_type']} "
                    f"组件:{r['component']} "
                    f"主机:{r['hostname']}({r['ip']}) "
                    f"告警内容:{r['message']} "
                    f"处理方案:{r['resolution_notes']}"
                )
                docs.append(doc)
                ids.append(f"alert_{r['id']}")
                metas.append({
                    "alert_type": r["alert_type"] or "",
                    "component": r["component"] or "",
                    "source": "alert_history"
                })

            embeddings = self.embed(docs)
            # upsert 避免重复
            self.collection.upsert(documents=docs, embeddings=embeddings,
                                   ids=ids, metadatas=metas)
            added += len(batch)

        return added

    def add_document(self, doc_id: str, content: str, metadata: dict = None):
        """手动添加单条文档（如运维手册片段）"""
        embedding = self.embed([content])[0]
        self.collection.upsert(
            documents=[content],
            embeddings=[embedding],
            ids=[doc_id],
            metadatas=[metadata or {}]
        )

    # ---------- 检索 ----------

    def search(self, query: str, top_k: int = 3, min_score: float = 0.6) -> str:
        """
        检索相关文档，返回格式化字符串注入 prompt。
        min_score: cosine 相似度阈值（0~1，越高越严格）
        """
        if self.collection.count() == 0:
            return ""

        qvec = self.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[qvec],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # distances 是 cosine distance（0=完全相同，2=完全相反），转换为相似度
        filtered = [
            doc for doc, dist in zip(docs, distances)
            if (1 - dist / 2) >= min_score
        ]

        if not filtered:
            return ""

        return "\n---\n".join(filtered)

    def stats(self) -> dict:
        return {
            "total_documents": self.collection.count(),
            "chroma_path": CHROMA_PATH,
            "bge_url": BGE_URL
        }
```

### 知识库构建脚本（一次性运行）

```bash
# 在宿主机上执行
cd /data/ruliu_callback
python3 - <<'EOF'
import sys
sys.path.insert(0, '.')
from agent.rag_retriever import RAGRetriever

retriever = RAGRetriever()
mysql_config = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "root",
    "password": "你的密码",
    "database": "cluster_management",
    "charset": "utf8mb4"
}
n = retriever.build_from_alerts(mysql_config)
print(f"已导入 {n} 条告警记录")
print(retriever.stats())
EOF
```

### 在 agent_core.py 中集成 RAG

```python
from .rag_retriever import RAGRetriever

class AgentCore:
    def __init__(self):
        ...
        self.rag = RAGRetriever()

    def run(self, user_message: str, session_id: str, from_user: str = "") -> str:
        # 1. RAG 检索
        rag_context = self.rag.search(user_message, top_k=3, min_score=0.65)

        # 2. 构造 system prompt，有上下文时注入
        system = SYSTEM_PROMPT.format(current_time=...)
        if rag_context:
            system += f"\n\n## 相关历史案例（供参考）\n{rag_context}"

        # 3. 其余 Tool Call 逻辑不变...
```

### 依赖安装

```bash
# 宿主机
pip install chromadb pymysql requests
# chromadb 会自动拉取 sqlite3 依赖，无需额外服务
```

---

## 四、混合路由策略（规则 + LLM）

你的思路是对的：**优先走规则，无法识别才走 LLM**。这样：
- 高频、格式固定的命令响应更快、更稳定
- LLM 资源只用在需要理解的场景
- 内网 API 限额压力小

### 路由决策流程

```python
def process_message(message_data):
    text = extract_text(message_data)
    group_id = message_data.get('groupid')
    from_user = message_data.get('message', {}).get('header', {}).get('fromuserid', '')

    # === 第一层：精确命令匹配（毫秒级响应）===
    cmd, args = parse_command(text)   # 现有函数保持不变
    if cmd and cmd != 'unknown':
        return dispatch_command(cmd, args, from_user)

    # === 第二层：RAG 增强的 LLM 路由 ===
    session_id = f"group:{group_id}"
    return agent_core.run(text, session_id=session_id, from_user=from_user)
```

### 规则路由保留的命令（parse_command 现有逻辑）

| 触发模式 | 命令 | 示例 |
|---------|------|------|
| IP 正则 | `query_ip` | `10.90.0.189` |
| 主机名正则 | `query_host` | `cdhmlcc001` |
| SN 正则 | `query_sn` | `SN-XXXXX` |
| 创建卡片关键词 | `create_card` | `创建卡片 P1 GPU ...` |
| `告警` / `alert` | `recent_alerts` | `最近告警` |
| `帮助` / `help` | `help` | `/help` |

### LLM 路由处理的场景（规则无法匹配）

| 用户输入 | LLM 调用的工具 |
|---------|--------------|
| "帮我看看最近 GPU 集群有没有问题" | `get_cluster_metrics` + `get_active_alerts` |
| "Pending PVC 有 195 个，帮我分析一下哪个集群最严重" | `get_pending_pvcs` + LLM 分析 |
| "10.90.0.189 的那个告警处理掉" | `get_active_alerts(ip=...)` → 确认 → `update_alert_status` |
| "最近一周哪类告警最多" | `get_alert_statistics(stat_type=distribution)` |
| "apiserver-alerts 里有没有严重的" | `get_apiserver_alerts(severity=critical)` |

---

## 五、完整实现结构

### 文件结构

```
callback_bot_systemd/
├── ruliu_callback.py          # 原有 Flask，修改 process_message 加混合路由
├── webhook_sender.py          # 不动
├── agent/
│   ├── __init__.py
│   ├── agent_core.py          # 混合路由控制器 + LLM Tool Call 循环
│   ├── tool_executor.py       # Tool → HTTP API 调用
│   ├── tools_schema.py        # Tool JSON Schema 定义
│   ├── session_store.py       # 对话历史（Redis 优先，降级内存）
│   └── rag_retriever.py       # BGE embedding + ChromaDB 检索（可选，后期加）
└── requirements_agent.txt     # httpx, chromadb（如需 RAG）
```

---

## 六、agent_core.py（内网版实现）

```python
"""
Agent 核心 - 内网版
LLM 使用项目内部 ERNIE API（通过 /api/v1/ai/chat 端点）
工具调用通过 /api/v1/* 内部接口
"""
import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Any

from .session_store import SessionStore
from .tool_executor import ToolExecutor
from .tools_schema import TOOLS

MAX_TOOL_ROUNDS = 5
API_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")
INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

SYSTEM_PROMPT = """你是一个智能运维助手，服务于长安汽车 LCC 集群运维团队。

你可以：
1. 查询服务器、CCE节点资产信息（支持 IP、主机名、SN、实例ID）
2. 查看硬件告警（GPU故障、磁盘故障等）和 APIServer 告警
3. 查询 CCE 集群监控指标、Pending PVC 状态
4. 更新告警处理状态（需先确认）
5. 创建 iCafe 运维事件卡片

规则：
- 回答使用 Markdown 格式，保持简洁
- 涉及写操作前，先向用户确认
- 数据为空时明确告知"未找到相关记录"
- 不捏造数据，只基于工具返回的真实数据回答

当前时间：{current_time}"""


class AgentCore:
    def __init__(self):
        self.session_store = SessionStore()
        self.tool_executor = ToolExecutor()
        self.api_session = requests.Session()
        self.api_session.headers.update({
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "Content-Type": "application/json"
        })

    def run(self, user_message: str, session_id: str, from_user: str = "") -> str:
        """混合路由主入口"""
        messages = self.session_store.get(session_id)
        messages.append({"role": "user", "content": user_message})

        for round_num in range(MAX_TOOL_ROUNDS):
            # 构造 system prompt + 工具描述（ERNIE 兼容格式）
            system = SYSTEM_PROMPT.format(
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            tools_desc = self._format_tools_for_ernie(TOOLS)

            # 调用内网 LLM（通过项目 API 端点）
            response = self._call_llm(messages, system, tools_desc)

            # 解析响应：是否有 tool_call
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                # 没有工具调用，直接返回文本
                final_text = response.get("content", "")
                messages.append({"role": "assistant", "content": final_text})
                self.session_store.save(session_id, messages)
                return final_text

            # 执行工具
            messages.append({"role": "assistant", "content": response.get("content", ""),
                             "tool_calls": tool_calls})
            for tc in tool_calls:
                result = self.tool_executor.execute(
                    tool_name=tc["function"]["name"],
                    tool_input=json.loads(tc["function"]["arguments"]),
                    from_user=from_user
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False)
                })

        self.session_store.save(session_id, messages)
        return "⚠️ 查询超时，请重新描述您的问题"

    def _call_llm(self, messages: list, system: str, tools_desc: str) -> dict:
        """调用内网 ERNIE API（通过项目 /api/v1/ai/chat 端点）"""
        # 把 system + tools 描述合并到消息中（ERNIE 兼容方式）
        full_messages = [{"role": "system", "content": system + "\n\n" + tools_desc}] + messages
        payload = {
            "messages": full_messages,
            "temperature": 0.2,
            "max_tokens": 2048
        }
        resp = self.api_session.post(f"{API_BASE}/api/v1/ai/chat", json=payload, timeout=60)
        return resp.json()

    def _format_tools_for_ernie(self, tools: list) -> str:
        """把 Tool schema 格式化成 ERNIE 能理解的文本描述注入到 Prompt"""
        lines = ["## 可用工具\n你可以通过在回复中输出以下 JSON 格式调用工具：\n",
                 "```json\n{\"tool_call\": {\"name\": \"工具名\", \"arguments\": {...}}}\n```\n",
                 "### 工具列表\n"]
        for t in tools:
            lines.append(f"**{t['name']}**: {t['description']}")
            props = t.get("input_schema", {}).get("properties", {})
            for pname, pdef in props.items():
                required = "必填" if pname in t.get("input_schema", {}).get("required", []) else "可选"
                lines.append(f"  - `{pname}` ({required}): {pdef.get('description', '')}")
            lines.append("")
        return "\n".join(lines)

    def _extract_tool_calls(self, response: dict) -> list:
        """从 ERNIE 响应中提取 tool_call（解析 JSON 格式）"""
        content = response.get("content", "")
        if not content or "tool_call" not in content:
            return []
        try:
            # 找到 JSON 块
            import re
            match = re.search(r'\{.*"tool_call".*\}', content, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group())
            tc = data.get("tool_call", {})
            return [{
                "id": f"tc_{datetime.now().timestamp()}",
                "function": {
                    "name": tc.get("name"),
                    "arguments": json.dumps(tc.get("arguments", {}))
                }
            }]
        except Exception:
            return []
```

> **注意**：ERNIE 对 Function Calling 的原生支持程度不如 Claude/GPT-4，这里用 **Prompt 注入工具描述 + 解析输出 JSON** 的方式模拟 tool_call，是内网 LLM 的常见兼容方案。如果 ERNIE-4.5 已支持原生 tool_call，可以直接用原生格式。

---

## 七、RAG 集成（后期扩展）

BGE-1.5B 服务端口确认后，在 `agent_core.py` 的 `run()` 中加一步 RAG 检索：

```python
def run(self, user_message: str, session_id: str, from_user: str = "") -> str:
    # 在调用 LLM 前，先检索相关上下文
    rag_context = self.rag_retriever.search(user_message, top_k=3)

    system = SYSTEM_PROMPT.format(current_time=...)
    if rag_context:
        system += f"\n\n## 相关历史案例\n{rag_context}"

    # 其余逻辑不变...
```

`rag_retriever.py` 核心：
```python
class RAGRetriever:
    BGE_URL = os.getenv("BGE_EMBEDDING_URL", "http://localhost:9000/embed")

    def embed(self, text: str) -> list:
        resp = requests.post(self.BGE_URL, json={"text": text}, timeout=5)
        return resp.json()["embedding"]

    def search(self, query: str, top_k: int = 3) -> str:
        qvec = self.embed(query)
        results = self.collection.query(query_embeddings=[qvec], n_results=top_k)
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""
```

---

## 八、改造影响评估

| 现有功能 | 改造后 | 影响 |
|---------|--------|------|
| 正则命令（IP查询/告警查询/创建卡片） | **完全保留**，走第一层规则路由 | ✅ 无影响 |
| 帮助命令 `/help` | 保留，但可让 LLM 动态回答 | ✅ 无影响 |
| webhook_sender.py 发消息 | 不动 | ✅ 无影响 |
| AES 签名验证 | 不动 | ✅ 无影响 |
| 飞书 callback | 不动 | ✅ 无影响 |
| **新增**：自然语言查询 | 走 LLM Agent | 新增能力 |
| **新增**：多步推理 | 走 LLM Agent | 新增能力 |
| **新增**：上下文记忆 | SessionStore（Redis） | 新增能力 |

**改造核心只改一处**：`process_message` 函数末尾加 `else` 分支走 Agent，现有逻辑完整保留。


## 一、背景与目标

### 当前问题
`ruliu_callback.py` 是基于**正则规则路由**的机器人：
```
用户输入 → parse_command()（正则匹配） → 固定函数调用 → 模板化输出
```
缺陷：
- 命令必须严格匹配格式，自然语言无法识别
- 新增能力需要手动写正则 + 函数，维护成本高
- 无法处理多步查询（"帮我查 10.90.0.189 的信息，如果有告警就创建 iCafe 卡片"）
- 无上下文记忆，每次对话相互独立

### 改造目标
```
用户自然语言 → LLM（意图理解 + 参数提取） → Tool Call → 项目 API → LLM 汇总回答
```
- 支持自然语言交互，无需记命令格式
- 多步 / 多 Tool 组合调用
- 保留上下文，支持追问
- 工具集可扩展，新增功能只需注册新 Tool

---

## 二、整体架构

```
如流群消息
    │
    ▼
ruliu_callback.py（Flask，宿主机 8120 端口）
    │  接收回调、签名验证、AES 解密
    ▼
AgentCore.run(user_message, session_id)
    │
    ├─ 1. 加载对话历史（Redis / 内存）
    ├─ 2. 调用 LLM（带 tools schema）
    ├─ 3. LLM 返回 tool_calls
    │       │
    │       ▼
    │   ToolExecutor.execute(tool_name, args)
    │       │  HTTP 调用项目内部 API（localhost:8000）
    │       │  或直连 MySQL 查询
    │       ▼
    │   返回 tool_result
    ├─ 4. 把 tool_result 追加到 messages 继续对话
    ├─ 5. LLM 生成最终回答（Markdown 格式）
    ▼
发送如流群消息（调用如流 API）
```

---

## 三、LLM 选型

| 方案 | 模型 | 特点 | 推荐度 |
|------|------|------|--------|
| **方案 A（推荐）** | Claude claude-sonnet-4-6 | Tool Use 能力强，中文好，支持多步推理 | ★★★★★ |
| 方案 B | 文心一言 ERNIE-4.0 | 项目已接入，无需新申请 API Key | ★★★★☆ |
| 方案 C | OpenAI GPT-4o | Function Calling 成熟 | ★★★★☆ |

项目已有 `POST /api/v1/ai/chat` 端点（ERNIE），可直接复用。但建议使用 **Anthropic Claude** 作为 Agent 核心，因为 Tool Use 的稳定性和多步推理能力更强。

---

## 四、Tool 设计（完整清单）

每个 Tool 对应项目中一个或多个 API 端点，LLM 通过 JSON Schema 理解参数含义。

### 4.1 CMDB 查询类

#### `query_asset`
查询服务器/实例/CCE节点信息，支持 IP、主机名、SN、实例ID、集群ID 等多种关键词。

```json
{
  "name": "query_asset",
  "description": "查询服务器、虚拟机实例、CCE节点的详细信息。支持 IP地址、主机名、SN序列号、BCC实例ID(i-xxx)、实例名称、CCE集群ID(cce-xxx)、CCE节点名称等多种查询方式。",
  "input_schema": {
    "type": "object",
    "properties": {
      "keyword": {
        "type": "string",
        "description": "查询关键词，如 IP地址 10.90.0.189、主机名 cdhmlcc001、SN序列号、实例ID i-xxx、集群ID cce-xxx"
      }
    },
    "required": ["keyword"]
  }
}
```

**调用链**：
```
→ GET /api/v1/cmdb/search?keyword={keyword}
→ 或 GET /api/v1/cmdb/servers/{hostname}
→ 或 GET /api/v1/cmdb/cce/cluster/{cluster_id}/instances
```

---

#### `get_cce_cluster_info`
查询 CCE 集群基础信息（K8S版本、节点数、网络模式等）。

```json
{
  "name": "get_cce_cluster_info",
  "description": "查询 CCE 集群的基础信息，包括 K8S 版本、Master 类型、网络模式、节点数量、集群状态等。cluster_id 为空时返回所有集群列表。",
  "input_schema": {
    "type": "object",
    "properties": {
      "cluster_id": {
        "type": "string",
        "description": "集群ID，格式为 cce-xxxxxxxx，可选，不传则返回所有集群"
      }
    }
  }
}
```

**调用链**：
```
→ GET /api/v1/cmdb/cce/clusters            （全部）
→ GET /api/v1/cmdb/cce/cluster/{cluster_id} （单个）
```

---

### 4.2 告警查询类

#### `get_active_alerts`
获取当前未完成的硬件告警列表。

```json
{
  "name": "get_active_alerts",
  "description": "获取当前未完成（处理中）的硬件告警列表。可按 IP、集群ID、告警类型、严重程度过滤。",
  "input_schema": {
    "type": "object",
    "properties": {
      "ip": { "type": "string", "description": "按 IP 地址过滤，可选" },
      "cluster_id": { "type": "string", "description": "按集群ID过滤，如 cce-xxx，可选" },
      "alert_type": { "type": "string", "description": "告警类型，如 GPU故障、磁盘故障，可选" },
      "severity": { "type": "string", "enum": ["critical", "warning", "info"], "description": "严重程度，可选" },
      "status": { "type": "string", "default": "processing", "description": "状态，默认 processing（处理中）" }
    }
  }
}
```

**调用链**：
```
→ GET /api/v1/alerts?status=processing&ip={ip}&cluster_id={cluster_id}&...
```

---

#### `get_alert_detail`
获取单条告警的详细信息和诊断结果。

```json
{
  "name": "get_alert_detail",
  "description": "获取某条告警的详细信息，包括告警内容、诊断结果、处理历史等。",
  "input_schema": {
    "type": "object",
    "properties": {
      "alert_id": { "type": "integer", "description": "告警ID" }
    },
    "required": ["alert_id"]
  }
}
```

**调用链**：
```
→ GET /api/v1/alerts/{alert_id}
```

---

#### `get_alert_statistics`
获取告警统计信息（趋势、分布、Top节点）。

```json
{
  "name": "get_alert_statistics",
  "description": "获取告警统计数据：趋势图（按天/周/月）、类型分布、告警最多的节点排行。",
  "input_schema": {
    "type": "object",
    "properties": {
      "stat_type": {
        "type": "string",
        "enum": ["trend", "distribution", "top_nodes"],
        "description": "统计类型：trend=趋势，distribution=分布，top_nodes=节点排行"
      },
      "start_time": { "type": "string", "description": "开始时间，ISO 格式，可选" },
      "end_time": { "type": "string", "description": "结束时间，ISO 格式，可选" },
      "dimension": { "type": "string", "description": "distribution 时的维度：alert_type/component/severity/cluster" }
    },
    "required": ["stat_type"]
  }
}
```

**调用链**：
```
→ GET /api/v1/alerts/statistics/trend
→ GET /api/v1/alerts/statistics/distribution?dimension={dimension}
→ GET /api/v1/alerts/statistics/top-nodes
```

---

### 4.3 告警处理类（写操作，需用户确认）

#### `update_alert_status`
更新告警处理状态。

```json
{
  "name": "update_alert_status",
  "description": "更新告警的处理状态。status 可选：processing（处理中）、resolved（已处理）、closed（已关闭）。",
  "input_schema": {
    "type": "object",
    "properties": {
      "alert_id": { "type": "integer", "description": "告警ID" },
      "status": {
        "type": "string",
        "enum": ["processing", "resolved", "closed"],
        "description": "目标状态"
      },
      "resolution_notes": { "type": "string", "description": "处理说明，可选" }
    },
    "required": ["alert_id", "status"]
  }
}
```

**调用链**：
```
→ PUT /api/v1/alerts/{alert_id}/status
  Body: { status, resolution_notes, resolved_by: <当前用户> }
```

---

### 4.4 iCafe 工单类

#### `create_icafe_card`
为告警创建 iCafe 运维事件卡片。

```json
{
  "name": "create_icafe_card",
  "description": "为指定告警创建 iCafe 运维事件卡片（长安LCC项目）。也可以直接提供标题和内容手动创建。",
  "input_schema": {
    "type": "object",
    "properties": {
      "alert_id": { "type": "integer", "description": "关联的告警ID，与 alert_id 二选一" },
      "level": { "type": "string", "description": "卡片级别，如 P0、P1、C0，仅手动创建时需要" },
      "module": { "type": "string", "description": "模块，如 GPU、BCC、存储，仅手动创建时需要" },
      "title": { "type": "string", "description": "卡片标题，仅手动创建时需要" },
      "content": { "type": "string", "description": "问题描述内容，仅手动创建时需要" }
    }
  }
}
```

**调用链**：
```
→ POST /api/v1/alerts/{alert_id}/create-icafe-card   （关联告警）
→ 或通过 ruliu_callback 中现有的 create_icafe_card() 函数（手动）
```

---

### 4.5 CCE 集群监控类

#### `get_cluster_metrics`
查询 CCE 集群实时监控指标。

```json
{
  "name": "get_cluster_metrics",
  "description": "查询指定 CCE 集群的实时监控指标，包括节点数、Pod状态、CPU/内存使用率、Pending PVC 数等。",
  "input_schema": {
    "type": "object",
    "properties": {
      "cluster_id": { "type": "string", "description": "集群ID，格式 cce-xxxxxxxx" }
    },
    "required": ["cluster_id"]
  }
}
```

**调用链**：
```
→ GET /api/v1/cce-monitoring/query?cluster_id={cluster_id}
```

---

#### `get_pending_pvcs`
查询 Pending 状态的 PVC 列表。

```json
{
  "name": "get_pending_pvcs",
  "description": "查询全部集群或指定集群中处于 Pending（未绑定）状态的 PVC 列表，返回命名空间、PVC名称、存储类、容量等信息。",
  "input_schema": {
    "type": "object",
    "properties": {
      "cluster_id": { "type": "string", "description": "集群ID，可选，不传则查全部集群" }
    }
  }
}
```

**调用链**：
```
→ GET /api/v1/cce-monitoring/pending-pvcs?cluster_id={cluster_id}
```

---

### 4.6 APIServer 告警类

#### `get_apiserver_alerts`
查询 APIServer 错误率告警。

```json
{
  "name": "get_apiserver_alerts",
  "description": "查询 Kubernetes APIServer 的错误率告警记录，可按集群、严重程度、状态过滤。",
  "input_schema": {
    "type": "object",
    "properties": {
      "cluster_id": { "type": "string", "description": "集群ID，可选" },
      "severity": { "type": "string", "description": "严重程度，可选" },
      "status": { "type": "string", "description": "状态，可选" },
      "page_size": { "type": "integer", "default": 20 }
    }
  }
}
```

**调用链**：
```
→ GET /api/v1/apiserver-alerts?cluster_id=...&severity=...
```

---

### 4.7 通用 Prometheus 查询类

#### `query_prometheus`
执行自定义 PromQL 查询（高级用法）。

```json
{
  "name": "query_prometheus",
  "description": "执行自定义 PromQL 查询，用于查询 Prometheus 中的任意指标。适合高级运维查询。",
  "input_schema": {
    "type": "object",
    "properties": {
      "promql": { "type": "string", "description": "PromQL 查询语句" },
      "cluster_id": { "type": "string", "description": "集群ID，用于自动注入 clusterID 过滤条件，可选" }
    },
    "required": ["promql"]
  }
}
```

**调用链**：
```
→ 直接调用 Prometheus API（复用 CCEMonitoringService._query_instant()）
```

---

## 五、核心实现：AgentCore

### 5.1 文件结构

```
callback_bot_systemd/
├── ruliu_callback.py          # 原有 Flask 回调（保留，修改 process_message）
├── agent_core.py              # 新增：Agent 核心逻辑
├── tool_executor.py           # 新增：Tool 执行器（HTTP 调用项目 API）
├── tools_schema.py            # 新增：所有 Tool 的 JSON Schema 定义
└── session_store.py           # 新增：对话历史管理
```

---

### 5.2 agent_core.py 实现

```python
"""
Agent 核心：LLM + Tool Call 循环
"""
import json
import anthropic
from typing import List, Dict, Any
from session_store import SessionStore
from tool_executor import ToolExecutor
from tools_schema import TOOLS

MAX_TOOL_ROUNDS = 5  # 最多连续调用 Tool 次数，防止死循环

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """你是一个智能运维助手，服务于长安汽车 LCC 集群运维团队。

你可以：
1. 查询服务器、虚拟机、CCE节点的资产信息（通过IP、主机名、SN、实例ID等）
2. 查看和管理硬件告警（GPU故障、磁盘故障等）
3. 查询 CCE 集群状态和监控指标（节点数、Pod状态、Pending PVC等）
4. 查询 APIServer 告警记录
5. 创建 iCafe 运维事件卡片

规则：
- 回答使用 Markdown 格式，表格对齐整齐
- 涉及写操作（更新状态、创建卡片）时，先确认再执行
- 查询到数据为空时，明确告知"未找到相关记录"
- 不要捏造数据，只基于工具返回的真实数据回答
- 时间相关查询默认使用最近7天范围

当前时间：{current_time}
"""

class AgentCore:
    def __init__(self):
        self.session_store = SessionStore()
        self.tool_executor = ToolExecutor()

    def run(self, user_message: str, session_id: str, from_user: str = "") -> str:
        """
        Agent 主循环：接收用户消息，返回最终回复文本
        """
        # 1. 加载历史对话
        messages = self.session_store.get(session_id)
        messages.append({"role": "user", "content": user_message})

        # 2. Tool Call 循环
        for round_num in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT.format(
                    current_time=datetime.now().strftime("%Y-%m-%d %H:%M")
                ),
                tools=TOOLS,
                messages=messages,
            )

            # 没有 tool_use，直接返回文本答案
            if response.stop_reason == "end_turn":
                final_text = self._extract_text(response)
                messages.append({"role": "assistant", "content": response.content})
                self.session_store.save(session_id, messages)
                return final_text

            # 有 tool_use，执行工具
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                # 收集所有 tool_use block 并并行执行
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self.tool_executor.execute(
                            tool_name=block.name,
                            tool_input=block.input,
                            from_user=from_user
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

        # 超过最大轮次
        self.session_store.save(session_id, messages)
        return "⚠️ 查询超时，请重新描述您的问题"

    def _extract_text(self, response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
```

---

### 5.3 tool_executor.py 实现

```python
"""
Tool 执行器：把 LLM 的 tool_call 翻译成实际的 HTTP API 调用
"""
import requests
import os
from typing import Any, Dict

# 项目内部 API 基础 URL（localhost，无需鉴权走内部 token）
API_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")
INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")  # 服务间调用专用 Token

class ToolExecutor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "Content-Type": "application/json"
        })

    def execute(self, tool_name: str, tool_input: Dict, from_user: str = "") -> Any:
        """分发 tool_call 到对应处理函数"""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            return {"error": f"未知工具: {tool_name}"}
        try:
            return handler(**tool_input, from_user=from_user)
        except Exception as e:
            return {"error": str(e)}

    def _tool_query_asset(self, keyword: str, **kwargs) -> Dict:
        resp = self.session.get(f"{API_BASE}/api/v1/cmdb/search", params={"keyword": keyword})
        return resp.json()

    def _tool_get_cce_cluster_info(self, cluster_id: str = None, **kwargs) -> Dict:
        if cluster_id:
            resp = self.session.get(f"{API_BASE}/api/v1/cmdb/cce/cluster/{cluster_id}")
        else:
            resp = self.session.get(f"{API_BASE}/api/v1/cmdb/cce/clusters")
        return resp.json()

    def _tool_get_active_alerts(self, ip: str = None, cluster_id: str = None,
                                 alert_type: str = None, severity: str = None,
                                 status: str = "processing", **kwargs) -> Dict:
        params = {"status": status, "page_size": 50}
        if ip: params["ip"] = ip
        if cluster_id: params["cluster_id"] = cluster_id
        if alert_type: params["alert_type"] = alert_type
        if severity: params["severity"] = severity
        resp = self.session.get(f"{API_BASE}/api/v1/alerts", params=params)
        return resp.json()

    def _tool_get_alert_detail(self, alert_id: int, **kwargs) -> Dict:
        resp = self.session.get(f"{API_BASE}/api/v1/alerts/{alert_id}")
        return resp.json()

    def _tool_get_alert_statistics(self, stat_type: str, start_time: str = None,
                                    end_time: str = None, dimension: str = None, **kwargs) -> Dict:
        params = {}
        if start_time: params["start_time"] = start_time
        if end_time: params["end_time"] = end_time
        if dimension: params["dimension"] = dimension
        url_map = {
            "trend": "/api/v1/alerts/statistics/trend",
            "distribution": "/api/v1/alerts/statistics/distribution",
            "top_nodes": "/api/v1/alerts/statistics/top-nodes"
        }
        resp = self.session.get(f"{API_BASE}{url_map[stat_type]}", params=params)
        return resp.json()

    def _tool_update_alert_status(self, alert_id: int, status: str,
                                   resolution_notes: str = "", from_user: str = "", **kwargs) -> Dict:
        payload = {
            "status": status,
            "resolved_by": from_user,
            "resolution_notes": resolution_notes
        }
        resp = self.session.put(f"{API_BASE}/api/v1/alerts/{alert_id}/status", json=payload)
        return resp.json()

    def _tool_create_icafe_card(self, alert_id: int = None, level: str = None,
                                 module: str = None, title: str = None,
                                 content: str = None, from_user: str = "", **kwargs) -> Dict:
        if alert_id:
            resp = self.session.post(
                f"{API_BASE}/api/v1/alerts/{alert_id}/create-icafe-card",
                json={"card_type": "standard"}
            )
            return resp.json()
        else:
            # 直接调用现有 create_icafe_card 函数
            from ruliu_callback import create_icafe_card
            result = create_icafe_card(level, module, title, content, from_user)
            return {"message": result}

    def _tool_get_cluster_metrics(self, cluster_id: str, **kwargs) -> Dict:
        resp = self.session.get(
            f"{API_BASE}/api/v1/cce-monitoring/query",
            params={"cluster_id": cluster_id}
        )
        return resp.json()

    def _tool_get_pending_pvcs(self, cluster_id: str = None, **kwargs) -> Dict:
        params = {}
        if cluster_id: params["cluster_id"] = cluster_id
        resp = self.session.get(f"{API_BASE}/api/v1/cce-monitoring/pending-pvcs", params=params)
        return resp.json()

    def _tool_get_apiserver_alerts(self, cluster_id: str = None, severity: str = None,
                                    status: str = None, page_size: int = 20, **kwargs) -> Dict:
        params = {"page_size": page_size}
        if cluster_id: params["cluster_id"] = cluster_id
        if severity: params["severity"] = severity
        if status: params["status"] = status
        resp = self.session.get(f"{API_BASE}/api/v1/apiserver-alerts", params=params)
        return resp.json()

    def _tool_query_prometheus(self, promql: str, cluster_id: str = None, **kwargs) -> Dict:
        # 如果指定了 cluster_id，自动注入过滤条件
        if cluster_id and "clusterID" not in promql:
            promql = promql.rstrip("}") + f',clusterID="{cluster_id}"}}'
        # 直接调用 Prometheus API（复用配置）
        import pymysql
        # 从数据库读取 Prometheus 配置
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "cluster_manager"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT config_value FROM system_config WHERE module='prometheus_runtime' AND config_key='main'"
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            return {"error": "Prometheus 未配置"}

        config = json.loads(row["config_value"])
        headers = {
            "Authorization": config["token"],
            "InstanceId": config["instance_id"]
        }
        resp = requests.get(
            f"{config['grafana_url'].rstrip('/')}/api/v1/query",
            headers=headers,
            params={"query": promql},
            timeout=20, verify=False
        )
        return resp.json().get("data", {})
```

---

### 5.4 session_store.py 实现

```python
"""
对话历史管理：支持 Redis（生产）或内存（开发）
每个 session 保留最近 20 轮对话，防止 context 过长
"""
import json
import os
from typing import List, Dict
from datetime import timedelta

MAX_HISTORY_ROUNDS = 20  # 最多保留轮数
SESSION_TTL = 3600       # 会话超时 1 小时

class SessionStore:
    def __init__(self):
        self._use_redis = False
        self._memory = {}
        try:
            import redis
            self._redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
                decode_responses=True
            )
            self._redis.ping()
            self._use_redis = True
        except Exception:
            pass  # 降级到内存存储

    def get(self, session_id: str) -> List[Dict]:
        key = f"agent:session:{session_id}"
        if self._use_redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else []
        return self._memory.get(key, [])

    def save(self, session_id: str, messages: List[Dict]):
        # 只保留最近 MAX_HISTORY_ROUNDS 轮（1轮 = user + assistant 2条）
        if len(messages) > MAX_HISTORY_ROUNDS * 2:
            messages = messages[-(MAX_HISTORY_ROUNDS * 2):]
        key = f"agent:session:{session_id}"
        if self._use_redis:
            self._redis.setex(key, SESSION_TTL, json.dumps(messages, ensure_ascii=False))
        else:
            self._memory[key] = messages

    def clear(self, session_id: str):
        key = f"agent:session:{session_id}"
        if self._use_redis:
            self._redis.delete(key)
        else:
            self._memory.pop(key, None)
```

---

### 5.5 修改 ruliu_callback.py（接入 AgentCore）

只需修改 `process_message` 函数，其他保持不变：

```python
# 在文件顶部添加
from agent_core import AgentCore

_agent = AgentCore()

def process_message(message_data: Dict[str, Any]) -> str:
    """处理用户消息 - 改为调用 AgentCore"""
    try:
        # 提取消息内容（逻辑不变）
        body = message_data.get('message', {}).get('body', [])
        text_parts = []
        for item in body:
            item_type = item.get('type', '')
            if item_type == 'TEXT':
                text_parts.append(item.get('content', ''))
            elif item_type == 'LINK':
                text_parts.append(item.get('label', '') or item.get('content', ''))
            elif item_type == 'AT':
                continue
        text = ' '.join(text_parts).strip()

        # 提取用户 & 群信息（用于会话隔离和写操作归因）
        header = message_data.get('message', {}).get('header', {})
        from_user = header.get('fromuserid', '')
        group_id = message_data.get('groupid', '')

        # 清理 @机器人 前缀（逻辑不变）
        import re
        text = re.sub(r'^@[^\s]+(?:\s+[^\s]+)?\s*', '', text).strip()

        if not text:
            return get_help()

        # ⭐ 核心：调用 AgentCore（session_id 用群ID隔离上下文）
        session_id = f"group:{group_id}"
        return _agent.run(text, session_id=session_id, from_user=from_user)

    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        return "❌ 处理消息时出错，请稍后重试"
```

---

## 六、意图识别与路由决策

LLM 的路由决策完全由 Prompt + Tool Schema 驱动，**不需要写额外的意图分类代码**。以下是几个典型案例：

### 案例1：简单查询

```
用户: "查一下 10.90.0.189 是什么机器"

LLM 决策:
  → tool_use: query_asset(keyword="10.90.0.189")
  → 返回: { BCC实例信息, CCE节点信息, 物理机信息 }

LLM 回复:
  "10.90.0.189 是一台 BCC 虚拟机实例，名称为 L20-dev，
   归属集群 cce-xrg955qz，当前状态：运行中 🟢..."
```

### 案例2：多步查询

```
用户: "帮我看看 cce-3nusu9su 集群最近有没有问题"

LLM 决策:
  → tool_use: get_cluster_metrics(cluster_id="cce-3nusu9su")
  → tool_use: get_active_alerts(cluster_id="cce-3nusu9su")
  → tool_use: get_pending_pvcs(cluster_id="cce-3nusu9su")

LLM 回复:
  "cce-3nusu9su 集群当前状态：
   节点总数 142，Ready 142，Pod 运行正常...
   ⚠️ 发现 30 个 Pending PVC，建议检查存储配置
   告警：当前有 3 条处理中告警..."
```

### 案例3：确认后写操作

```
用户: "把告警 #123 标记为已处理，原因是硬件已更换"

LLM 决策（第一轮）:
  → 回复: "确认要将告警 #123 状态改为「已处理」，
            备注「硬件已更换」吗？（回复「确认」执行）"

用户: "确认"

LLM 决策（第二轮）:
  → tool_use: update_alert_status(alert_id=123, status="resolved", resolution_notes="硬件已更换")
  → 回复: "✅ 告警 #123 已更新为「已处理」"
```

### 案例4：追问（上下文记忆）

```
用户: "查一下 Pending PVC 有哪些"
LLM:  "全集群共 195 个 Pending PVC，最多的是 cce-xrg955qz（148个）..."

用户: "xrg955qz 这个集群的节点状态怎么样"
LLM 决策:
  → 根据上下文知道 cluster_id = "cce-xrg955qz"
  → tool_use: get_cluster_metrics(cluster_id="cce-xrg955qz")
```

---

## 七、内部 API 鉴权方案

Agent 调用项目 API 需要 Token，有两种方案：

### 方案 A（推荐）：专用服务账号
1. 在项目中创建一个 role=`service` 的内部账号（用户名 `ruliu-agent`）
2. 登录获取 JWT Token，写入 `.env` 文件
3. ToolExecutor 使用该 Token 调用 API
4. 优点：走正常鉴权流程，权限可控，审计日志可见

```bash
# .env 新增
INTERNAL_API_TOKEN=<通过 /api/v1/auth/login 获取的 JWT>
INTERNAL_API_BASE=http://localhost:8000
```

### 方案 B：直连 MySQL（现有方式）
保持现有 `Database` 类，对需要的数据直接 SQL 查询，不走 HTTP。
- 优点：无鉴权复杂度，延迟低
- 缺点：绕过业务逻辑，耦合数据库结构

**推荐方案 A**，保持架构清晰，后续迁移 / 权限变更更容易。

---

## 八、环境依赖

在宿主机 `ruliu_callback` 环境中新增：

```bash
pip install anthropic>=0.34.0
pip install redis>=5.0.0  # 如果没有的话
```

`.env` 新增：
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxx
INTERNAL_API_BASE=http://localhost:8000
INTERNAL_API_TOKEN=<服务账号 JWT>
```

---

## 九、渐进式迁移策略

不需要一次性全部替换，可以分阶段：

### Phase 1：并行运行（安全）
在 `process_message` 中根据环境变量开关决定走规则路由还是 Agent：

```python
USE_AGENT = os.getenv("USE_AGENT", "false").lower() == "true"

def process_message(message_data):
    if USE_AGENT:
        return _agent.run(...)
    else:
        return _legacy_process(message_data)  # 原有逻辑重命名
```

### Phase 2：灰度（按命令类型）
只有规则路由无法匹配的命令才走 Agent，匹配到的走原有逻辑。

### Phase 3：全量切换
所有消息都走 Agent，删除 `parse_command` 等遗留代码。

---

## 十、扩展方向

一旦 Agent 框架建立，后续扩展只需：

1. **新增 Tool**：在 `tools_schema.py` 增加 JSON Schema，在 `ToolExecutor` 增加 `_tool_xxx` 方法
2. **PFS 查询**：`query_pfs_metrics(level, region, instance_id, metrics, time_range)` → `POST /api/v1/pfs/query`
3. **GPU 卡时分析**：`analyze_gpu_bottom(cluster_ids, start_time, end_time)` → `POST /api/v1/gpu-monitoring/bottom-card-time/analyze`
4. **自动巡检报告**：定时触发 `get_cluster_metrics` 对所有集群扫描，发现异常主动推送群消息
5. **多模态**：如流支持图片回调时，可以让 LLM 分析截图中的错误信息
