#!/usr/bin/env python3
"""
飞书告警查询机器人 - 使用卡片 JSON 2.0 格式 + 分段发送
"""
import os
import json
import re
import pymysql
from datetime import datetime
from typing import List, Tuple

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTrigger, P2CardActionTriggerResponse

# ==================== 配置 ====================
os.environ.setdefault("APP_ID", "cli_a9563738edbe9bce")
os.environ.setdefault("APP_SECRET", "YKScjtqsyoQSnGh0evS3IcSzJquTP0fs")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3307")
os.environ.setdefault("MYSQL_USER", "root")
os.environ.setdefault("MYSQL_PASSWORD", "Zhang~~1")
os.environ.setdefault("MYSQL_DATABASE", "cluster_management")

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3307')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'Zhang~~1'),
    'database': os.getenv('MYSQL_DATABASE', 'cluster_management'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ==================== 数据库 ====================
class Database:
    def __init__(self):
        self.connection = None
    
    def connect(self) -> bool:
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def query(self, sql: str, params: tuple = ()) -> list:
        if not self.connection and not self.connect():
            return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"查询失败: {e}")
            return []
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

# ==================== 命令解析 ====================
def parse_command(text: str) -> Tuple[str, list]:
    """解析用户命令，返回 (command, args)"""
    text = re.sub(r'^@.*?\s+', '', text.strip())
    parts = text.split()
    
    if not parts:
        return 'help', []
    
    first = parts[0]
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    # IP 开头的命令
    if re.match(ip_pattern, first):
        if len(parts) >= 2:
            cmd = parts[1].lower()
            if cmd in ['告警', '告警列表', 'alerts']:
                return 'ip_alerts', [first, 'today']
            elif cmd in ['历史告警', 'history']:
                return 'ip_alerts', [first, 'all']
        return 'query', [first]
    
    # 普通命令
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    cmd_map = {
        '告警': 'alerts', '告警列表': 'alerts', 'alerts': 'alerts', 'alert': 'alerts',
        '帮助': 'help', 'help': 'help', '?': 'help',
        '查询': 'query', 'query': 'query',
    }
    return cmd_map.get(cmd, cmd), args

# ==================== 数据查询 ====================
def get_recent_alerts_data(db: Database) -> list:
    sql = """
        SELECT id, alert_type, component, severity, ip, cluster_id, status, created_at
        FROM alert_records WHERE status NOT IN ('resolved', 'closed')
        ORDER BY created_at DESC LIMIT 100
    """
    return db.query(sql)

def get_ip_alerts_data(db: Database, keyword: str, scope: str = 'today') -> list:
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    if re.match(ip_pattern, keyword):
        where_clause, params = "ar.ip = %s", [keyword]
    else:
        # 通过主机名/SN查找IP
        sql_cmdb = """SELECT rms_ip_in1, rms_ip_in2, rms_ip_out
                      FROM iaas_servers WHERE bns_hostname = %s OR rms_sn = %s LIMIT 1"""
        server = db.query(sql_cmdb, (keyword, keyword))
        if server:
            ips = [ip for ip in server[0].values() if ip]
            if ips:
                where_clause = f"ar.ip IN ({','.join(['%s']*len(ips))})"
                params = ips
            else:
                return []
        else:
            where_clause, params = "ar.ip LIKE %s OR ar.cluster_id LIKE %s", [f"%{keyword}%", f"%{keyword}%"]
    
    if scope == 'today':
        where_clause += " AND DATE(ar.created_at) = %s"
        params.append(datetime.now().strftime('%Y-%m-%d'))
    
    sql = f"""SELECT ar.id, ar.alert_type, ar.created_at, ar.status, ar.severity, ar.component, ar.ip, ar.cluster_id
              FROM alert_records ar WHERE {where_clause} ORDER BY ar.created_at DESC LIMIT 100"""
    return db.query(sql, tuple(params))

# ==================== 状态图标映射 ====================
STATUS_ICONS = {
    '运行中': '🟢', '可用': '🟢', 'Active': '🟢', 'active': '🟢', 'Running': '🟢', 'running': '🟢',
    '已停止': '⛔', '停止': '⛔', '不可用': '⛔', 'Inactive': '⛔', 'Stopped': '⛔', 'stopped': '⛔',
    '创建中': '⏳', '启动中': '⏳', '删除中': '⏳', 'Starting': '⏳', 'Stopping': '⏳',
    '维修中': '🔧', '维护中': '🔧', 'processing': '🔧',
    'pending': '⏳', 'resolved': '✅', 'closed': '⛔'
}

SEVERITY_ICONS = {
    'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢', 'warning': '🟠'
}

def get_status_icon(status):
    return STATUS_ICONS.get(status, '⚪') if status else '⚪'

def get_severity_icon(severity):
    return SEVERITY_ICONS.get(severity, '🟡')

# ==================== 查询服务器信息（卡片格式）====================
def query_server_info(db: Database, keyword: str) -> dict:
    """查询服务器信息（CMDB + BCE）- 返回飞书卡片格式"""
    elements = []
    found_any = False
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    # 1. 查询虚拟机实例表 - 按IP获取物理机信息
    if re.match(ip_pattern, keyword):
        sql_instance = """
            SELECT bns_hostname, nova_vm_instance_name, nova_vm_fixed_ips, nova_vm_cluster
            FROM iaas_instances WHERE nova_vm_fixed_ips LIKE %s LIMIT 5
        """
        instances = db.query(sql_instance, (f'%{keyword}%',))
        
        if instances:
            found_any = True
            for inst in instances:
                physical_hostname = inst['bns_hostname']
                
                # 虚拟机信息 - 使用表格（对象数组格式）
                elements.extend([
                    {"tag": "markdown", "content": "**📋 虚拟机信息**"},
                    {
                        "tag": "table",
                        "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                        "columns": [
                            {"name": "field", "display_name": "字段", "width": "30%", "data_type": "text"},
                            {"name": "value", "display_name": "值", "width": "70%", "data_type": "text"}
                        ],
                        "rows": [
                            {"field": "实例名称", "value": inst['nova_vm_instance_name'] or 'N/A'},
                            {"field": "所属集群", "value": inst['nova_vm_cluster'] or 'N/A'}
                        ]
                    }
                ])
                
                # 物理机信息
                if physical_hostname:
                    sql_server = """
                        SELECT bns_hostname, rms_sn, rms_manufacturer, rms_model,
                               rms_status, nova_host_cluster,
                               nova_host_blacklisted_reason, nova_host_blacklisted_description
                        FROM iaas_servers WHERE bns_hostname = %s LIMIT 1
                    """
                    servers = db.query(sql_server, (physical_hostname,))
                    if servers:
                        srv = servers[0]
                        rows = [
                            {"field": "物理机名称", "value": srv['bns_hostname'] or 'N/A'},
                            {"field": "SN", "value": srv['rms_sn'] or 'N/A'},
                            {"field": "所属集群", "value": srv['nova_host_cluster'] or 'N/A'}
                        ]
                        if srv['nova_host_blacklisted_reason']:
                            rows.append({"field": "⚠️ 加黑原因", "value": srv['nova_host_blacklisted_reason']})
                        if srv['nova_host_blacklisted_description']:
                            desc = srv['nova_host_blacklisted_description'][:100] + "..."
                            rows.append({"field": "⚠️ 加黑说明", "value": desc})
                        
                        elements.extend([
                            {"tag": "markdown", "content": "**📋 物理机信息**"},
                            {
                                "tag": "table",
                                "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                                "columns": [
                                    {"name": "field", "display_name": "字段", "width": "30%", "data_type": "text"},
                                    {"name": "value", "display_name": "值", "width": "70%", "data_type": "text"}
                                ],
                                "rows": rows
                            }
                        ])
        
        # BCC实例信息
        try:
            sql_bcc = """SELECT bcc_id, 名称, 状态, `内网ip` FROM bce_bcc_instances WHERE `内网ip` = %s LIMIT 3"""
            bcc_list = db.query(sql_bcc, (keyword,))
            if bcc_list:
                found_any = True
                rows = []
                for bcc in bcc_list:
                    status_icon = get_status_icon(bcc['状态'])
                    rows.append({
                        "name": bcc['名称'],
                        "id": bcc['bcc_id'],
                        "status": f"{status_icon} {bcc['状态']}",
                        "ip": bcc['内网ip'] or 'N/A'
                    })
                elements.extend([
                    {"tag": "markdown", "content": "**🖥️ BCC实例信息**"},
                    {
                        "tag": "table",
                        "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                        "columns": [
                            {"name": "name", "display_name": "名称", "width": "25%", "data_type": "text"},
                            {"name": "id", "display_name": "ID", "width": "25%", "data_type": "text"},
                            {"name": "status", "display_name": "状态", "width": "25%", "data_type": "text"},
                            {"name": "ip", "display_name": "IP", "width": "25%", "data_type": "text"}
                        ],
                        "rows": rows
                    }
                ])
        except Exception as e:
            pass
        
        # CCE节点信息
        try:
            sql_cce = """SELECT cluster_id, `节点名称`, `状态`, `内网ip` FROM bce_cce_nodes WHERE `内网ip` = %s LIMIT 3"""
            cce_nodes = db.query(sql_cce, (keyword,))
            if cce_nodes:
                found_any = True
                rows = []
                for node in cce_nodes:
                    status_icon = get_status_icon(node['状态'])
                    rows.append({
                        "name": node['节点名称'],
                        "cluster": node['cluster_id'],
                        "status": f"{status_icon} {node['状态']}"
                    })
                elements.extend([
                    {"tag": "markdown", "content": "**☸️ CCE节点信息**"},
                    {
                        "tag": "table",
                        "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                        "columns": [
                            {"name": "name", "display_name": "节点名称", "width": "35%", "data_type": "text"},
                            {"name": "cluster", "display_name": "集群", "width": "35%", "data_type": "text"},
                            {"name": "status", "display_name": "状态", "width": "30%", "data_type": "text"}
                        ],
                        "rows": rows
                    }
                ])
        except Exception as e:
            pass
    
    # 2. 查询CMDB - 按主机名
    sql = """SELECT bns_hostname, rms_sn, rms_manufacturer, rms_model,
               rms_status, nova_host_cluster FROM iaas_servers WHERE bns_hostname = %s LIMIT 5"""
    servers = db.query(sql, (keyword,))
    if servers:
        found_any = True
        rows = []
        for srv in servers:
            status_icon = get_status_icon(srv['rms_status'])
            rows.append({
                "hostname": srv['bns_hostname'] or 'N/A',
                "sn": srv['rms_sn'] or 'N/A',
                "status": f"{status_icon} {srv['rms_status'] or 'N/A'}",
                "cluster": srv['nova_host_cluster'] or 'N/A'
            })
        elements.extend([
            {"tag": "markdown", "content": "**📋 物理机信息 (按主机名)**"},
            {
                "tag": "table",
                "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                "columns": [
                    {"name": "hostname", "display_name": "主机名", "width": "30%", "data_type": "text"},
                    {"name": "sn", "display_name": "SN", "width": "25%", "data_type": "text"},
                    {"name": "status", "display_name": "状态", "width": "20%", "data_type": "text"},
                    {"name": "cluster", "display_name": "集群", "width": "25%", "data_type": "text"}
                ],
                "rows": rows
            }
        ])
    
    # 3. 查询CMDB - 按SN
    sql = """SELECT bns_hostname, rms_sn, rms_manufacturer, rms_model,
               rms_status, nova_host_cluster FROM iaas_servers WHERE rms_sn = %s LIMIT 5"""
    servers = db.query(sql, (keyword,))
    if servers:
        found_any = True
        rows = []
        for srv in servers:
            status_icon = get_status_icon(srv['rms_status'])
            rows.append({
                "hostname": srv['bns_hostname'] or 'N/A',
                "sn": srv['rms_sn'] or 'N/A',
                "status": f"{status_icon} {srv['rms_status'] or 'N/A'}",
                "cluster": srv['nova_host_cluster'] or 'N/A'
            })
        elements.extend([
            {"tag": "markdown", "content": "**📋 物理机信息 (按SN)**"},
            {
                "tag": "table",
                "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
                "columns": [
                    {"name": "hostname", "display_name": "主机名", "width": "30%", "data_type": "text"},
                    {"name": "sn", "display_name": "SN", "width": "25%", "data_type": "text"},
                    {"name": "status", "display_name": "状态", "width": "20%", "data_type": "text"},
                    {"name": "cluster", "display_name": "集群", "width": "25%", "data_type": "text"}
                ],
                "rows": rows
            }
        ])
    
    if not found_any:
        return {
            "schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": f"{keyword} 查询结果"}, "template": "red"},
            "body": {"direction": "vertical", "elements": [{"tag": "markdown", "content": f"❌ 未找到 {keyword} 关联的任何信息\n\n支持的查询类型：IP地址、主机名、SN、集群ID(cce-xxxxx)、节点名称"}]}
        }
    
    return {
        "schema": "2.0",
        "header": {"title": {"tag": "plain_text", "content": f"{keyword} 关联信息查询结果"}, "template": "blue"},
        "body": {"direction": "vertical", "padding": "12px", "elements": elements}
    }


def get_help() -> str:
    return """🤖 **硬件告警助手**

📋 **指令列表**:
1️⃣ `告警列表` - 查询未完成告警
2️⃣ `<IP> 告警列表` - 查询IP今日告警
3️⃣ `<IP> 历史告警` - 查询IP所有告警  
4️⃣ `<IP/主机名/SN>` - 查询服务器信息
5️⃣ `帮助` - 显示帮助

💡 告警较多时会分段显示"""


# ==================== 卡片构建（告警列表）====================
def build_alert_cards(alerts: list, title: str, page_size: int = 8) -> list:
    """构建告警卡片列表（JSON 2.0 格式，表格展示）"""
    
    if not alerts:
        return [{
            "schema": "2.0",
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "green"},
            "body": {"direction": "vertical", "elements": [{"tag": "markdown", "content": "✅ 当前没有告警记录"}]}
        }]
    
    total = len(alerts)
    total_pages = (total + page_size - 1) // page_size
    cards = []
    
    for page in range(1, total_pages + 1):
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        
        elements = []
        if page == 1:
            elements.append({"tag": "markdown", "content": f"**共 {total} 条告警**"})
        
        # 构建表格数据 - 对象数组格式
        rows = []
        for alert in alerts[start:end]:
            severity = get_severity_icon(alert.get('severity', 'medium'))
            status = get_status_icon(alert.get('status', 'pending'))
            status_text = alert.get('status', 'pending')
            if status_text == 'processing':
                status_text = '处理中'
            elif status_text == 'pending':
                status_text = '待处理'
            elif status_text == 'resolved':
                status_text = '已处理'
            elif status_text == 'closed':
                status_text = '已关闭'
            
            ip = alert.get('ip') or '-'
            alert_type = alert.get('alert_type', 'Unknown')[:25]
            component = alert.get('component', '-')[:15]
            cluster = alert.get('cluster_id', '-')[:20]
            
            created = alert.get('created_at')
            if isinstance(created, str):
                time_str = created[5:16]
            elif created:
                time_str = created.strftime('%m-%d %H:%M')
            else:
                time_str = '-'
            
            rows.append({
                "type": f"{severity} {alert_type}",
                "ip": ip,
                "cluster": cluster,
                "component": component,
                "status": f"{status} {status_text}",
                "time": time_str
            })
        
        elements.append({
            "tag": "table",
            "page_size": page_size,
            "header_style": {"text_align": "left", "background_style": "grey", "bold": True},
            "columns": [
                {"name": "type", "display_name": "告警类型", "width": "28%", "data_type": "text"},
                {"name": "ip", "display_name": "IP", "width": "15%", "data_type": "text"},
                {"name": "cluster", "display_name": "集群", "width": "20%", "data_type": "text"},
                {"name": "component", "display_name": "组件", "width": "12%", "data_type": "text"},
                {"name": "status", "display_name": "状态", "width": "15%", "data_type": "text"},
                {"name": "time", "display_name": "时间", "width": "10%", "data_type": "text"}
            ],
            "rows": rows
        })
        
        if total_pages > 1:
            elements.append({"tag": "markdown", "content": f"📄 **第 {page}/{total_pages} 页**", "text_align": "center"})
        
        template = "red" if total > 10 else "orange" if total > 5 else "green"
        
        card = {
            "schema": "2.0",
            "config": {"update_multi": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"{title} (第{page}页)" if total_pages > 1 else title},
                "template": template if page == 1 else "blue"
            },
            "body": {
                "direction": "vertical",
                "padding": "12px",
                "elements": elements
            }
        }
        cards.append(card)
    
    return cards


# ==================== 消息处理 ====================
processed_messages = set()

def do_p2_im_message_receive_v1(data) -> None:
    """处理消息"""
    if data.event.message.message_type != "text":
        reply_text(data, "请发送文本消息")
        return
    
    # 去重
    msg_id = data.event.message.message_id
    if msg_id in processed_messages:
        return
    processed_messages.add(msg_id)
    if len(processed_messages) > 1000:
        processed_messages.clear()
    
    text = json.loads(data.event.message.content).get("text", "")
    print(f"收到: {text}")

    command, args = parse_command(text)
    
    db = Database()
    if not db.connect():
        reply_text(data, "❌ 数据库连接失败")
        return
    
    try:
        if command == 'ip_alerts' and len(args) >= 2:
            keyword, scope = args[0], args[1]
            alerts = get_ip_alerts_data(db, keyword, scope)
            title = f"{keyword} 的{'今日' if scope == 'today' else '历史'}告警"
            cards = build_alert_cards(alerts, title, page_size=8)
            for card in cards:
                reply_card(data, card)
        
        elif command == 'query' and args:
            card_data = query_server_info(db, args[0])
            reply_card(data, card_data)
        
        elif command == 'alerts':
            alerts = get_recent_alerts_data(db)
            title = "未完成告警列表"
            cards = build_alert_cards(alerts, title, page_size=8)
            for card in cards:
                reply_card(data, card)
        
        elif command == 'help':
            reply_text(data, get_help())
        
        else:
            reply_text(data, f"❓ 未知命令\n\n{get_help()}")
    
    finally:
        db.close()


def do_p2_card_action_trigger_v1(data: P2CardActionTrigger) -> P2CardActionTriggerResponse:
    """处理卡片按钮点击 - 长连接模式下卡片回调不支持，返回空响应"""
    return P2CardActionTriggerResponse({})


def reply_text(data, content: str) -> None:
    """发送文本消息"""
    msg = json.dumps({"text": content})
    if data.event.message.chat_type == "p2p":
        req = (CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(data.event.message.chat_id)
                .msg_type("text")
                .content(msg)
                .build())
            .build())
        client.im.v1.message.create(req)
    else:
        req = (ReplyMessageRequest.builder()
            .message_id(data.event.message.message_id)
            .request_body(ReplyMessageRequestBody.builder()
                .content(msg)
                .msg_type("text")
                .build())
            .build())
        client.im.v1.message.reply(req)


def reply_card(data, card_data: dict) -> None:
    """发送卡片消息"""
    msg = json.dumps(card_data)
    print(f"发送卡片: {msg[:200]}...")
    
    if data.event.message.chat_type == "p2p":
        req = (CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(data.event.message.chat_id)
                .msg_type("interactive")
                .content(msg)
                .build())
            .build())
        client.im.v1.message.create(req)
    else:
        req = (ReplyMessageRequest.builder()
            .message_id(data.event.message.message_id)
            .request_body(ReplyMessageRequestBody.builder()
                .content(msg)
                .msg_type("interactive")
                .build())
            .build())
        client.im.v1.message.reply(req)


# ==================== 启动 ====================
if not os.getenv('HTTP_PROXY'):
    os.environ['HTTP_PROXY'] = 'http://agent.baidu.com:8891'
    os.environ['HTTPS_PROXY'] = 'http://agent.baidu.com:8891'

event_handler = (lark.EventDispatcherHandler.builder(lark.APP_ID, lark.APP_SECRET)
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .register_p2_card_action_trigger(do_p2_card_action_trigger_v1)
    .build())

client = lark.Client.builder().app_id(lark.APP_ID).app_secret(lark.APP_SECRET).build()
wsClient = lark.ws.Client(lark.APP_ID, lark.APP_SECRET, event_handler=event_handler, log_level=lark.LogLevel.DEBUG)


def main():
    print("=" * 50)
    print("飞书告警机器人启动")
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("=" * 50)
    wsClient.start()


if __name__ == "__main__":
    main()
