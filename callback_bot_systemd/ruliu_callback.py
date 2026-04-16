#!/usr/bin/env python3
"""
如流机器人回调服务
独立于主项目运行，部署在宿主机上
"""
import os
import sys
import json
import time
import hmac
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

import pymysql
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/ruliu-callback/ruliu_callback.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置参数（从环境变量读取）
CONFIG = {
    'token': os.getenv('RULIU_TOKEN', ''),
    'encoding_aes_key': os.getenv('RULIU_ENCODING_AES_KEY', ''),
    'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
    'mysql_port': int(os.getenv('MYSQL_PORT', '3307')),
    'mysql_user': os.getenv('MYSQL_USER', 'root'),
    'mysql_password': os.getenv('MYSQL_PASSWORD', 'Zhang~~1'),
    'mysql_database': os.getenv('MYSQL_DATABASE', 'cluster_management'),
    'ruliu_api_url': os.getenv('RULIU_API_URL', 'http://apiin.im.baidu.com/api/v1/robot/msg/groupmsgsend'),
    'ruliu_access_token': os.getenv('RULIU_ACCESS_TOKEN', ''),
}


class Database:
    """数据库连接类"""
    
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=CONFIG['mysql_host'],
                port=CONFIG['mysql_port'],
                user=CONFIG['mysql_user'],
                password=CONFIG['mysql_password'],
                database=CONFIG['mysql_database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def query(self, sql: str, params: tuple = ()) -> list:
        """执行查询"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询失败: {e}, SQL: {sql}")
            return []
    
    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class AESCipher:
    """AES加解密类"""
    
    def __init__(self, key: str):
        # Base64解码key，补齐到16字节
        key_bytes = base64.b64decode(key + '==')
        self.key = key_bytes[:16]
        
    def decrypt(self, ciphertext: str) -> str:
        """解密消息"""
        try:
            # URL safe base64解码
            ciphertext = ciphertext.replace('-', '+').replace('_', '/')
            ciphertext += '=' * (len(ciphertext) % 4)
            
            # Base64解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # AES解密
            cipher = AES.new(self.key, AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted_data)
            
            # 去除padding
            decrypted = unpad(decrypted, AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise


def verify_signature(signature: str, timestamp: str, rn: str) -> bool:
    """验证签名"""
    try:
        expected = hashlib.md5(f"{rn}{timestamp}{CONFIG['token']}".encode()).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return False


def parse_command(text: str) -> tuple:
    """
    解析用户命令
    支持格式：
    - 告警列表
    - 10.90.0.189 告警列表
    - 10.90.0.189 历史告警列表
    - 集群 cce-xxx
    - 查询 10.90.0.189
    - 查询 SN123456
    """
    import re
    
    # 清理消息：移除 @机器人名称 前缀
    # 匹配 @用户名 或 @机器人名称 格式（支持空格分隔的名称）
    text = re.sub(r'^@[^\s]+(?:\s+[^\s]+)?\s*', '', text.strip())
    text = text.strip()
    
    parts = text.split()
    
    if not parts:
        return 'help', []
    
    # 检查是否是 IP/ID/主机名/SN 开头
    first_part = parts[0]
    
    # IP 正则
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    is_ip = re.match(ip_pattern, first_part)
    
    # 如果第一部分是IP
    if is_ip:
        keyword = first_part
        
        # 如果有后续命令
        if len(parts) >= 2:
            command = parts[1].lower()
            args = parts[2:] if len(parts) > 2 else []
            
            if command in ['告警', '告警列表', 'alerts', 'alert']:
                return 'ip_alerts', [keyword, 'today']
            elif command in ['历史告警', '历史告警列表', 'history']:
                return 'ip_alerts', [keyword, 'all']
            else:
                return 'query', [keyword]
        else:
            # 只有IP，没有后续命令，默认查询信息
            return 'query', [keyword]
    
    # 检查是否是创建iCafe卡片命令
    # 格式: 创建卡片 级别 模块 标题 内容
    # 示例: 创建卡片 P0 GPU 服务异常 详细描述信息
    if len(parts) >= 5 and parts[0].lower() in ['创建卡片', 'icafe', 'card']:
        # 检查第二部分是否是级别（支持 P0-P9, C0-C9 等格式）
        level_pattern = r'^[A-Za-z]\d$'
        if re.match(level_pattern, parts[1]):
            level = parts[1].upper()
            module = parts[2]
            # 标题是第4部分，内容从第5部分开始
            title = parts[3]
            content = ' '.join(parts[4:])
            return 'icafe', [level, module, title, content]
    
    # 普通命令格式
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args


def get_recent_alerts(db: Database) -> str:
    """获取未完成的告警（表格形式）"""
    sql = """
        SELECT id, alert_type, component, severity, ip, cluster_id, status, created_at
        FROM alert_records
        WHERE status NOT IN ('resolved', 'closed')
        ORDER BY created_at DESC
    """
    alerts = db.query(sql)

    if not alerts:
        return "✅ 当前没有未完成的告警"

    lines = [f"##### 未完成告警列表（共 {len(alerts)} 条）", ""]

    # 表格头部: IP | 集群 | 类型 | 组件 | 状态
    lines.append("| IP | 集群 | 类型 | 组件 | 状态 |")
    lines.append("|-----|------|------|------|------|")

    for alert in alerts:
        # 状态显示（前端只有3种：处理中、已处理、已关闭）
        status_map = {
            'processing': '🔧 处理中',
            'resolved': '✅ 已处理',
            'closed': '⛔ 已关闭'
        }
        status_display = status_map.get(alert['status'], alert['status'])

        lines.append(f"| {alert['ip'] or '-'} | {alert['cluster_id'] or '-'} | {alert['alert_type']} | {alert['component'] or '-'} | {status_display} |")

    return "\n".join(lines)


def get_ip_alerts(db: Database, keyword: str, scope: str = 'today') -> str:
    """
    获取指定IP/主机名/SN的告警列表
    
    Args:
        keyword: IP地址、主机名或SN
        scope: 'today' 仅今日, 'all' 所有历史
    
    Returns:
        格式化的告警列表（表格形式）
    """
    from datetime import datetime, timedelta
    
    # 判断keyword类型
    import re
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    is_ip = re.match(ip_pattern, keyword)
    
    # 构建查询条件
    if is_ip:
        # 直接匹配IP
        where_clause = "ar.ip = %s"
        params = [keyword]
        title_keyword = f"IP {keyword}"
    else:
        # 可能是主机名或SN，需要从CMDB关联查询
        # 先查询CMDB获取IP
        sql_cmdb = """
            SELECT rms_ip_in1, rms_ip_in2, rms_ip_out1, rms_ip_out2
            FROM iaas_servers
            WHERE bns_hostname = %s OR rms_sn = %s
            LIMIT 1
        """
        server = db.query(sql_cmdb, (keyword, keyword))
        
        if server:
            srv = server[0]
            # 收集所有可能的IP
            ips = [ip for ip in [srv['rms_ip_in1'], srv['rms_ip_in2'], srv['rms_ip_out1'], srv['rms_ip_out2']] if ip]
            if ips:
                placeholders = ','.join(['%s'] * len(ips))
                where_clause = f"ar.ip IN ({placeholders})"
                params = ips
                title_keyword = f"主机 {keyword}"
            else:
                return f"❌ 未找到 {keyword} 关联的IP地址"
        else:
            # 尝试直接匹配告警中的IP字段（可能是主机名存储在IP字段）
            where_clause = "ar.ip LIKE %s OR ar.cluster_id LIKE %s"
            params = [f"%{keyword}%", f"%{keyword}%"]
            title_keyword = f"关键词 {keyword}"
    
    # 时间过滤
    if scope == 'today':
        today = datetime.now().strftime('%Y-%m-%d')
        where_clause += " AND DATE(ar.created_at) = %s"
        params.append(today)
        time_desc = "今日"
    else:
        time_desc = "历史"
    
    # 查询告警
    sql = f"""
        SELECT 
            ar.id,
            ar.alert_type,
            ar.created_at,
            ar.status,
            ar.severity,
            ar.component,
            ar.cluster_id,
            ar.ip
        FROM alert_records ar
        WHERE {where_clause}
        ORDER BY ar.created_at DESC
        LIMIT 20
    """
    
    alerts = db.query(sql, tuple(params))
    
    if not alerts:
        return f"📭 {title_keyword} 暂无{time_desc}告警记录"
    
    # 构建表格形式的消息
    lines = [f"##### {title_keyword} 的{time_desc}告警列表", ""]
    lines.append("| IP | 集群 | 类型 | 组件 | 状态 |")
    lines.append("|-----|------|------|------|------|")

    for alert in alerts:
        # 状态显示（前端只有3种：处理中、已处理、已关闭）
        status_map = {
            'processing': '🔧 处理中',
            'resolved': '✅ 已处理',
            'closed': '⛔ 已关闭'
        }
        status_display = status_map.get(alert['status'], alert['status'])

        lines.append(f"| {alert['ip'] or '-'} | {alert['cluster_id'] or '-'} | {alert['alert_type']} | {alert['component'] or '-'} | {status_display} |")

    lines.append("")
    lines.append(f"📊 共 {len(alerts)} 条记录")
    
    return "\n".join(lines)


# 状态图标映射
STATUS_ICONS = {
    '运行中': '🟢', '可用': '🟢', 'Active': '🟢', 'active': '🟢', 'Running': '🟢', 'running': '🟢',
    '已停止': '⛔', '停止': '⛔', '不可用': '⛔', 'Inactive': '⛔', 'Stopped': '⛔', 'stopped': '⛔',
    '创建中': '⏳', '启动中': '⏳', '删除中': '⏳', 'Starting': '⏳', 'Stopping': '⏳',
    '维修中': '🔧', '维护中': '🔧', 'processing': '🔧',
    'pending': '⏳', 'resolved': '✅', 'closed': '⛔'
}

def get_status_icon(status):
    return STATUS_ICONS.get(status, '⚪') if status else '⚪'

def query_server_info(db: Database, keyword: str) -> str:
    """
    查询服务器信息（CMDB + BCE）- Markdown表格格式
    支持IP、主机名、SN、实例ID、集群ID等
    """
    import re
    
    lines = [f"##### {keyword} 关联信息查询结果", ""]
    found_any = False
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    
    # 1. 查询虚拟机实例表 - 按IP获取物理机信息
    if re.match(ip_pattern, keyword):
        logger.info(f"正在查询CMDB，IP: {keyword}")
        
        sql_instance = """
            SELECT bns_hostname, nova_vm_instance_name, nova_vm_fixed_ips, nova_vm_cluster
            FROM iaas_instances WHERE nova_vm_fixed_ips LIKE %s LIMIT 5
        """
        instances = db.query(sql_instance, (f'%{keyword}%',))
        logger.info(f"虚拟机实例查询结果: {len(instances)} 条记录")
        
        if instances:
            found_any = True
            for inst in instances:
                physical_hostname = inst['bns_hostname']
                
                # 虚拟机信息 - Markdown表格
                lines.append("**📋 虚拟机信息**")
                lines.append("")
                lines.append("| 字段 | 值 |")
                lines.append("|------|-----|")
                lines.append(f"| 实例名称 | {inst['nova_vm_instance_name'] or 'N/A'} |")
                lines.append(f"| 所属集群 | {inst['nova_vm_cluster'] or 'N/A'} |")
                lines.append("")
                
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
                        lines.append("**📋 物理机信息**")
                        lines.append("")
                        lines.append("| 字段 | 值 |")
                        lines.append("|------|-----|")
                        lines.append(f"| 物理机名称 | {srv['bns_hostname'] or 'N/A'} |")
                        lines.append(f"| SN | {srv['rms_sn'] or 'N/A'} |")
                        lines.append(f"| 所属集群 | {srv['nova_host_cluster'] or 'N/A'} |")
                        if srv['nova_host_blacklisted_reason']:
                            lines.append(f"| ⚠️ 加黑原因 | {srv['nova_host_blacklisted_reason']} |")
                        if srv['nova_host_blacklisted_description']:
                            desc = srv['nova_host_blacklisted_description'][:100] + "..."
                            lines.append(f"| ⚠️ 加黑说明 | {desc} |")
                        lines.append("")
        
        # 查询BCC实例信息
        try:
            sql_bcc = """SELECT bcc_id, 名称, 状态, `内网ip` FROM bce_bcc_instances WHERE `内网ip` = %s LIMIT 3"""
            bcc_list = db.query(sql_bcc, (keyword,))
            if bcc_list:
                found_any = True
                lines.append("**🖥️ BCC实例信息**")
                lines.append("")
                lines.append("| 名称 | ID | 状态 | IP |")
                lines.append("|------|-----|------|-----|")
                for bcc in bcc_list:
                    status_icon = get_status_icon(bcc['状态'])
                    lines.append(f"| {bcc['名称']} | {bcc['bcc_id']} | {status_icon} {bcc['状态']} | {bcc['内网ip'] or 'N/A'} |")
                lines.append("")
        except Exception as e:
            logger.warning(f"BCC查询失败: {e}")
        
        # 查询CCE节点信息
        try:
            sql_cce = """SELECT cluster_id, `节点名称`, `状态`, `内网ip` FROM bce_cce_nodes WHERE `内网ip` = %s LIMIT 3"""
            logger.info(f"正在查询CCE，IP: {keyword}")
            cce_nodes = db.query(sql_cce, (keyword,))
            logger.info(f"CCE查询结果: {len(cce_nodes)} 条记录")
            if cce_nodes:
                found_any = True
                lines.append("**☸️ CCE节点信息**")
                lines.append("")
                lines.append("| 节点名称 | 集群 | 状态 |")
                lines.append("|----------|------|------|")
                for node in cce_nodes:
                    status_icon = get_status_icon(node['状态'])
                    lines.append(f"| {node['节点名称']} | {node['cluster_id']} | {status_icon} {node['状态']} |")
                lines.append("")
        except Exception as e:
            logger.warning(f"CCE查询失败: {e}")
    
    # 2. 查询CMDB - 按主机名
    sql = """SELECT bns_hostname, rms_sn, rms_manufacturer, rms_model,
               rms_status, nova_host_cluster FROM iaas_servers WHERE bns_hostname = %s LIMIT 5"""
    servers = db.query(sql, (keyword,))
    if servers:
        found_any = True
        lines.append("**📋 物理机信息 (按主机名)**")
        lines.append("")
        lines.append("| 主机名 | SN | 状态 | 集群 |")
        lines.append("|--------|-----|------|------|")
        for srv in servers:
            status_icon = get_status_icon(srv['rms_status'])
            lines.append(f"| {srv['bns_hostname'] or 'N/A'} | {srv['rms_sn'] or 'N/A'} | {status_icon} {srv['rms_status'] or 'N/A'} | {srv['nova_host_cluster'] or 'N/A'} |")
        lines.append("")
    
    # 3. 查询CMDB - 按SN
    sql = """SELECT bns_hostname, rms_sn, rms_manufacturer, rms_model,
               rms_status, nova_host_cluster FROM iaas_servers WHERE rms_sn = %s LIMIT 5"""
    servers = db.query(sql, (keyword,))
    if servers:
        found_any = True
        lines.append("**📋 物理机信息 (按SN)**")
        lines.append("")
        lines.append("| 主机名 | SN | 状态 | 集群 |")
        lines.append("|--------|-----|------|------|")
        for srv in servers:
            status_icon = get_status_icon(srv['rms_status'])
            lines.append(f"| {srv['bns_hostname'] or 'N/A'} | {srv['rms_sn'] or 'N/A'} | {status_icon} {srv['rms_status'] or 'N/A'} | {srv['nova_host_cluster'] or 'N/A'} |")
        lines.append("")
    
    # 4. 查询BCE BCC - 按实例ID
    try:
        sql = """SELECT bcc_id, 名称, 状态, `内网ip` FROM bce_bcc_instances WHERE bcc_id = %s LIMIT 3"""
        bcc_list = db.query(sql, (keyword,))
        if bcc_list:
            found_any = True
            lines.append("**🖥️ BCC实例信息 (按实例ID)**")
            lines.append("")
            lines.append("| 名称 | ID | 状态 | IP |")
            lines.append("|------|-----|------|-----|")
            for bcc in bcc_list:
                status_icon = get_status_icon(bcc['状态'])
                lines.append(f"| {bcc['名称']} | {bcc['bcc_id']} | {status_icon} {bcc['状态']} | {bcc['内网ip'] or 'N/A'} |")
            lines.append("")
    except Exception as e:
        logger.warning(f"BCC实例ID查询失败: {e}")
    
    # 5. 查询BCE BCC - 按实例名称
    try:
        sql = """SELECT bcc_id, 名称, 状态, `内网ip` FROM bce_bcc_instances WHERE 名称 = %s LIMIT 3"""
        bcc_list = db.query(sql, (keyword,))
        if bcc_list:
            found_any = True
            lines.append("**🖥️ BCC实例信息 (按实例名称)**")
            lines.append("")
            lines.append("| 名称 | ID | 状态 | IP |")
            lines.append("|------|-----|------|-----|")
            for bcc in bcc_list:
                status_icon = get_status_icon(bcc['状态'])
                lines.append(f"| {bcc['名称']} | {bcc['bcc_id']} | {status_icon} {bcc['状态']} | {bcc['内网ip'] or 'N/A'} |")
            lines.append("")
    except Exception as e:
        logger.warning(f"BCC实例名称查询失败: {e}")
    
    # 6. 查询BCE CCE - 按集群ID
    if keyword.startswith('cce-'):
        try:
            sql = """SELECT cluster_id, `节点名称`, `状态`, `内网ip` FROM bce_cce_nodes WHERE cluster_id = %s LIMIT 10"""
            nodes = db.query(sql, (keyword,))
            if nodes:
                found_any = True
                lines.append(f"**☸️ CCE集群节点 (集群ID: {keyword})**")
                lines.append("")
                lines.append("| 节点名称 | IP | 状态 |")
                lines.append("|----------|-----|------|")
                for node in nodes:
                    status_icon = get_status_icon(node['状态'])
                    lines.append(f"| {node['节点名称']} | {node['内网ip']} | {status_icon} {node['状态']} |")
                lines.append("")
        except Exception as e:
            logger.warning(f"CCE集群查询失败: {e}")

    # 7. 查询BCE CCE - 按节点名称
    try:
        sql = """SELECT cluster_id, `节点名称`, `状态`, `内网ip` FROM bce_cce_nodes WHERE `节点名称` = %s LIMIT 3"""
        nodes = db.query(sql, (keyword,))
        if nodes:
            found_any = True
            lines.append("**☸️ CCE节点信息 (按节点名称)**")
            lines.append("")
            lines.append("| 节点名称 | 集群 | IP | 状态 |")
            lines.append("|----------|------|-----|------|")
            for node in nodes:
                status_icon = get_status_icon(node['状态'])
                lines.append(f"| {node['节点名称']} | {node['cluster_id']} | {node['内网ip']} | {status_icon} {node['状态']} |")
            lines.append("")
    except Exception as e:
        logger.warning(f"CCE节点查询失败: {e}")
    
    # 8. 查询告警记录 - 按IP（放在最后）
    if re.match(ip_pattern, keyword):
        sql = """SELECT alert_type, severity, status, created_at FROM alert_records WHERE ip = %s ORDER BY created_at DESC LIMIT 3"""
        alerts = db.query(sql, (keyword,))
        if alerts:
            found_any = True
            lines.append("**⚠️ 最近告警**")
            lines.append("")
            lines.append("| 告警类型 | 级别 | 状态 | 时间 |")
            lines.append("|----------|------|------|------|")
            for alert in alerts:
                status_icon = "🔴" if alert['status'] == 'active' else "🟢"
                sev_icon = "🔴" if alert['severity'] == 'critical' else "🟠" if alert['severity'] == 'warning' else "⚪"
                time_str = alert['created_at'].strftime('%m-%d %H:%M') if alert['created_at'] else 'N/A'
                status_text = alert['status'] or '未知'
                lines.append(f"| {alert['alert_type']} | {sev_icon} | {status_icon} {status_text} | {time_str} |")
            lines.append("")
    
    if not found_any:
        return f"❌ 未找到 {keyword} 关联的任何信息\n\n支持的查询类型：IP地址、主机名、SN、实例ID(i-xxxxx)、实例名称、集群ID(cce-xxxxx)、节点名称"
    
    return "\n".join(lines)


def _format_server_info(srv: dict) -> list:
    """格式化服务器信息为文本行列表"""
    lines = []
    lines.append(f"  **主机名**: {srv['bns_hostname'] or 'N/A'}")
    lines.append(f"  **SN**: {srv['rms_sn'] or 'N/A'}")
    lines.append(f"  **厂商/型号**: {srv['rms_manufacturer'] or 'N/A'} / {srv['rms_model'] or 'N/A'}")
    
    ips = [ip for ip in [srv['rms_ip_in1'], srv['rms_ip_in2'], srv['rms_ip_out1'], srv['rms_ip_out2']] if ip]
    lines.append(f"  **IP地址**: {', '.join(ips) if ips else 'N/A'}")
    lines.append(f"  **状态**: {srv['rms_status'] or 'N/A'}")
    lines.append(f"  **集群**: {srv['nova_host_cluster'] or 'N/A'}")
    lines.append("")
    return lines


def create_icafe_card(level: str, module: str, title: str, content: str, from_user: str = '') -> str:
    """
    创建iCafe卡片

    卡片名称：【长安LCC】【级别】【模块】标题
    固定参数：
    - 方向大类：计算
    - 细分分类：BCC
    - 汇总分类：运维事件
    - TAM负责人：陈少禄
    - 占用工时：2
    """
    try:
        import requests

        # iCafe配置
        icafe_config = {
            'api_url': 'http://icafeapi.baidu-int.com/api/v2',
            'space_id': 'HMLCC',
            'username': 'chenshaolu',
            'password': 'VVVCRG5Ah9xqYHoWMl38PmcvL59p6jk6rZi'
        }

        # 构建卡片标题（标题不包含内容）
        card_title = f"【长安LCC】【{level}】【{module}】{title}"

        # 构建卡片内容（HTML格式）
        card_detail = f"""<h3>【环境】</h3>
<p>客户：长安汽车<br>
region：CD</p>

<h3>【现象】</h3>
<p>{content}</p>

<h3>【排查过程】</h3>
<p></p>

<h3>【结论】</h3>
<p></p>

<h3>【创建人】</h3>
<p>{from_user}</p>
"""

        # 构建请求数据（参考项目中的格式）
        url = f"{icafe_config['api_url']}/space/{icafe_config['space_id']}/issue/new"

        payload = {
            "username": icafe_config['username'],
            "password": icafe_config['password'],
            "issues": [{
                "title": card_title,
                "detail": card_detail,
                "type": "Task",
                "fields": {
                    "方向大类": "计算",
                    "细分分类": "BCC",
                    "汇总分类": "运维事件",
                    "TAM负责人": "陈少禄",
                    "占用工时": "2"
                },
                "creator": from_user or icafe_config['username'],
                "comment": ""
            }]
        }

        headers = {"Content-Type": "application/json"}

        logger.info(f"正在创建iCafe卡片: {card_title}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        result = response.json()

        if result.get("status") == 200:
            logger.info(f"✅ iCafe卡片创建成功: {card_title}")
            # 获取卡片链接
            issues_data = result.get('issues', [])
            if issues_data and len(issues_data) > 0:
                # API直接返回url字段
                card_url = issues_data[0].get('url', '')
                if card_url:
                    return f"✅ iCafe卡片创建成功！\n\n**卡片标题**: {card_title}\n**卡片链接**: {card_url}\n\n请补充【排查过程】和【结论】部分"
            return f"✅ iCafe卡片创建成功！\n\n**卡片标题**: {card_title}\n\n请补充【排查过程】和【结论】部分"
        else:
            error_msg = result.get('message', '未知错误')
            logger.error(f"❌ iCafe卡片创建失败: {error_msg}")
            return f"❌ iCafe卡片创建失败: {error_msg}"

    except Exception as e:
        logger.error(f"创建iCafe卡片异常: {e}", exc_info=True)
        return f"❌ 创建iCafe卡片失败: {str(e)}"


def get_help() -> str:
    """获取帮助信息"""
    return """##### 🤖 硬件告警助手帮助

**📋 指令列表**:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1️⃣ 告警列表** - 查询所有未完成的告警
格式：`告警列表`
示例：`@机器人 告警列表`

返回：表格形式显示所有处理中的告警
• 显示字段：IP | 集群 | 类型 | 组件 | 状态
• 状态说明：🔧 处理中 / ✅ 已处理 / ⛔ 已关闭

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**2️⃣ IP + 告警列表** - 查询指定IP的今日告警
格式：`<IP> 告警列表`
示例：`@机器人 10.90.0.189 告警列表`

返回：该IP今日的告警记录（表格形式）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**3️⃣ IP + 历史告警列表** - 查询指定IP的所有历史告警
格式：`<IP> 历史告警列表`
示例：`@机器人 10.90.0.189 历史告警列表`

返回：该IP的所有历史告警记录（包含已处理/已关闭）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**4️⃣ 信息查询** - 查询服务器/实例/节点详细信息
格式：`<查询内容>`
示例：`@机器人 10.90.0.189`

支持的查询类型：
| 类型 | 示例 | 返回信息 |
|------|------|---------|
| IP地址 | 10.90.0.189 | 虚拟机信息 + 物理机信息 + BCC实例 + 告警记录 |
| SN序列号 | 21D109579 | 物理机信息（加黑原因/说明） |
| 主机名 | cdhmlcc001... | 物理机信息 |
| 实例ID | i-Qdox90Xf | BCC实例信息 |
| 实例名称 | L20-dev | BCC实例信息 |
| 集群ID | cce-xrg955qz | CCE集群所有节点 |
| 节点名称 | cce-node-01 | CCE节点信息 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**5️⃣ 创建iCafe卡片** - 快速创建长安LCC运维事件卡片
格式：`创建卡片 <级别> <模块> <标题> <内容>`
示例：`@机器人 创建卡片 P0 GPU 服务异常 GPU驱动报错导致服务无法启动`

别名：`icafe`、`card` 也可以替代 `创建卡片`

固定参数：
• 方向大类：计算
• 细分分类：BCC
• 汇总分类：运维事件
• 占用工时：2
• 卡片类型：Task

卡片内容模板：
```
【环境】
客户：长安汽车
region：CD

【现象】
<用户输入的内容>

【排查过程】
（待补充）

【结论】
（待补充）
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**6️⃣ 帮助** - 显示此帮助信息
格式：`帮助`
示例：`@机器人 帮助`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 使用提示**:
• 所有命令不区分大小写
• 必须先@机器人，再输入指令
• IP地址格式：10.90.0.189（IPv4）
• 表格显示时，如流会自动渲染为美观的表格样式"""


def process_message(message_data: Dict[str, Any]) -> str:
    """处理用户消息"""
    try:
        # 提取消息内容
        body = message_data.get('message', {}).get('body', [])
        text_parts = []
        
        logger.info(f"消息体: {body}")
        
        # 过滤掉 @AT 类型的元素，保留 TEXT 和 LINK 类型
        for item in body:
            item_type = item.get('type', '')
            if item_type == 'TEXT':
                text_parts.append(item.get('content', ''))
            elif item_type == 'LINK':
                # 保留链接内容（如IP地址被识别为链接）
                text_parts.append(item.get('label', '') or item.get('content', ''))
            elif item_type == 'AT':
                # 跳过@机器人的部分
                logger.info(f"跳过AT: {item}")
                continue
        
        text = ' '.join(text_parts).strip()
        logger.info(f"收到消息(原始): '{text}'")
        
        # 解析命令
        command, args = parse_command(text)
        logger.info(f"解析命令: {command}, 参数: {args}")
        
        # 连接数据库
        db = Database()
        if not db.connect():
            return "❌ 数据库连接失败，请稍后重试"
        
        try:
            # 执行命令
            if command == 'ip_alerts' and len(args) >= 2:
                # IP + 告警列表 / 历史告警列表
                keyword, scope = args[0], args[1]
                return get_ip_alerts(db, keyword, scope)
            
            elif command == 'query' and len(args) >= 1:
                # 信息查询（IP/SN/主机名）
                return query_server_info(db, args[0])
            
            elif command in ['告警', '告警列表', 'alerts', 'alert']:
                return get_recent_alerts(db)
            
            elif command == 'icafe' and len(args) >= 4:
                # 创建iCafe卡片
                level, module, title, content = args[0], args[1], args[2], args[3]
                from_user = message_data.get('message', {}).get('header', {}).get('fromuserid', '')
                return create_icafe_card(level, module, title, content, from_user)
            
            elif command in ['帮助', 'help', '?']:
                return get_help()
            
            else:
                return f"❓ 未知命令: {command}\n\n{get_help()}"
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        return "❌ 处理消息时出错，请稍后重试"


def save_result_to_file(group_id: str, from_user: str, reply_content: str, platform: str = 'ruliu'):
    """
    保存处理结果到文件
    
    Args:
        group_id: 群ID
        from_user: 用户ID
        reply_content: 回复内容
        platform: 平台类型 ('ruliu' 或 'feishu')
    """
    result_data = {
        'platform': platform,
        'group_id': group_id,
        'from_user': from_user,
        'content': reply_content,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    # 保存到结果目录
    result_file = f"/var/log/ruliu-callback/results/{int(time.time() * 1000)}.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"处理结果已保存: {result_file}, platform={platform}")
    logger.info(f"回复内容: {reply_content[:100]}...")


@app.route('/ruliu/callback', methods=['GET', 'POST'])
def ruliu_callback():
    """如流回调接口"""
    try:
        # 获取URL参数（GET请求）
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        rn = request.args.get('rn', '')
        echostr = request.args.get('echostr', '')
        
        # 如果URL参数为空，尝试从POST表单数据获取
        if not signature and request.method == 'POST':
            signature = request.form.get('signature', '')
            timestamp = request.form.get('timestamp', '')
            rn = request.form.get('rn', '')
            echostr = request.form.get('echostr', '')
        
        logger.info(f"收到如流回调请求: signature={signature[:10] if signature else 'empty'}..., timestamp={timestamp}, rn={rn}")
        
        # 验证签名
        if not verify_signature(signature, timestamp, rn):
            logger.warning("如流签名验证失败")
            return 'signature check fail', 403
        
        # 如果是配置验证请求（有echostr）
        if echostr:
            logger.info(f"配置验证请求，返回 echostr: {echostr[:20]}...")
            return echostr
        
        # 处理加密消息
        if request.data:
            encrypted_data = request.data.decode('utf-8')
            logger.info(f"收到加密消息: {encrypted_data[:100]}...")
            
            # 解密消息
            cipher = AESCipher(CONFIG['encoding_aes_key'])
            decrypted = cipher.decrypt(encrypted_data)
            logger.info(f"解密后消息: {decrypted[:200]}...")
            
            # 解析JSON
            message_data = json.loads(decrypted)
            
            # 只处理消息接收事件
            event_type = message_data.get('eventtype', '')
            if event_type == 'MESSAGE_RECEIVE':
                # 提取群ID和消息信息
                group_id = message_data.get('groupid')
                from_user = message_data.get('message', {}).get('header', {}).get('fromuserid')
                
                # 处理消息
                reply_content = process_message(message_data)
                
                # 保存结果到文件
                save_result_to_file(group_id, from_user, reply_content, platform='ruliu')
                
                # 返回成功响应
                return jsonify({'code': 200, 'msg': 'ok'})
            
            return jsonify({'code': 200, 'msg': 'ok'})
        
        return jsonify({'code': 200, 'msg': 'ok'})
    
    except Exception as e:
        logger.error(f"如流回调处理失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': 'internal error'}), 500


@app.route('/feishu/callback', methods=['POST'])
def feishu_callback():
    """
    飞书回调接口
    复用项目中飞书Webhook的处理逻辑
    """
    try:
        logger.info(f"收到飞书回调请求")
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            logger.warning("飞书回调数据为空")
            return jsonify({'code': 400, 'msg': 'bad request'}), 400
        
        # 处理飞书挑战验证（首次配置时需要）
        challenge = data.get('challenge')
        if challenge:
            logger.info(f"飞书挑战验证: {challenge}")
            return jsonify({'challenge': challenge})
        
        # 获取事件类型
        header = data.get('header', {})
        event_type = header.get('event_type', '')
        
        logger.info(f"飞书事件类型: {event_type}")
        
        # 处理消息事件
        if event_type == 'im.message.receive_v1':
            event = data.get('event', {})
            message = event.get('message', {})
            sender = event.get('sender', {})
            
            # 提取消息信息
            chat_id = message.get('chat_id')  # 飞书群ID
            user_id = sender.get('sender_id', {}).get('user_id')  # 用户ID
            msg_type = message.get('message_type')
            content = json.loads(message.get('content', '{}'))
            
            logger.info(f"飞书消息: chat_id={chat_id}, user_id={user_id}, msg_type={msg_type}")
            
            # 提取文本内容
            text = content.get('text', '')
            if not text:
                logger.warning("飞书消息内容为空")
                return jsonify({'code': 200, 'msg': 'ok'})
            
            # 清理@机器人的前缀
            import re
            text = re.sub(r'^@.*?\s+', '', text.strip())
            
            # 构建如流格式的消息数据，复用现有的process_message
            message_data = {
                'message': {
                    'body': [
                        {'type': 'TEXT', 'content': text}
                    ],
                    'header': {
                        'fromuserid': user_id
                    }
                }
            }
            
            # 处理消息（复用现有逻辑）
            reply_content = process_message(message_data)
            
            # 保存结果到文件（platform=feishu）
            save_result_to_file(chat_id, user_id, reply_content, platform='feishu')
            
            return jsonify({'code': 200, 'msg': 'ok'})
        
        return jsonify({'code': 200, 'msg': 'ok'})
    
    except Exception as e:
        logger.error(f"飞书回调处理失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': 'internal error'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    # 检查配置（如流配置是可选的，如果要用如流才需要）
    has_ruliu_config = CONFIG['token'] and CONFIG['encoding_aes_key']
    has_feishu_config = os.getenv('FEISHU_WEBHOOK_URL', '')
    
    if not has_ruliu_config and not has_feishu_config:
        logger.warning("警告: 如流和飞书配置都未完整配置")
        logger.warning("如流需要: RULIU_TOKEN, RULIU_ENCODING_AES_KEY")
        logger.warning("飞书需要: FEISHU_WEBHOOK_URL")
    
    # 从环境变量读取端口，默认8120
    port = int(os.getenv('RULIU_PORT', '8120'))
    
    logger.info("=" * 60)
    logger.info("回调服务启动 (支持如流/飞书)")
    logger.info("=" * 60)
    logger.info(f"监听端口: {port}")
    logger.info(f"如流回调: {'已配置' if has_ruliu_config else '未配置'} (/ruliu/callback)")
    logger.info(f"飞书回调: {'已配置' if has_feishu_config else '未配置'} (/feishu/callback)")
    logger.info("=" * 60)
    
    # 启动Flask服务
    app.run(host='0.0.0.0', port=port, debug=False)
