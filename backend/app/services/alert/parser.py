"""
告警文件解析服务
"""
import ast
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AlertParserService:
    """告警解析服务"""
    
    @staticmethod
    def extract_node_info_from_filename(file_path: str) -> Optional[Dict[str, str]]:
        """
        从文件名提取节点信息（cluster_id + ip）
        
        文件名格式：长安-cce-xrg955qz-ghy9yll6-10.90.0.245.txt
        
        Args:
            file_path: 文件路径
            
        Returns:
            {'cluster_id': 'cce-xrg955qz', 'ip': '10.90.0.245'} 或 None（物理机）
        """
        filename = Path(file_path).name
        
        # 提取cluster_id（CCE集群）
        cce_pattern = r'cce-([a-z0-9]+)'
        match = re.search(cce_pattern, filename)
        cluster_id = f"cce-{match.group(1)}" if match else None
        
        # 提取IP
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        match = re.search(ip_pattern, filename)
        ip = match.group(1) if match else None
        
        if cluster_id and ip:
            logger.debug(f"从文件名提取节点信息: cluster_id={cluster_id}, ip={ip}")
            return {'cluster_id': cluster_id, 'ip': ip}
        elif ip:
            logger.debug(f"从文件名提取物理机IP: ip={ip}")
            return {'cluster_id': None, 'ip': ip}
        else:
            logger.warning(f"无法从文件名提取节点信息: {filename}")
            return None
    
    @staticmethod
    def parse_file(file_path: str) -> List[Dict[str, Any]]:
        """
        解析告警文件
        
        支持两种格式：
        1. 单行格式：[{...}]
        2. 多行格式：
           [{...}]  # 第一行：case信息
           [{...}]  # 第二行：detail信息（可选）
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析后的告警记录列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 解析每一行（每行都是一个独立的JSON数组）
            all_data = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 使用 ast.literal_eval 安全解析 Python 列表
                    line_data = ast.literal_eval(line)
                    
                    if not isinstance(line_data, list):
                        logger.warning(f"第 {line_num} 行不是列表: {file_path}")
                        continue
                    
                    all_data.extend(line_data)
                except Exception as e:
                    logger.warning(f"解析第 {line_num} 行失败: {file_path}, 错误: {e}")
                    continue
            
            if not all_data:
                logger.error(f"文件内容为空或解析失败: {file_path}")
                return []
            
            # 合并多行数据（如果第二行是detail信息）
            alert_list = all_data
            
            # 解析每条告警
            records = []
            for alert_data in alert_list:
                try:
                    # 检查是否为嵌套格式（包含detail数组）
                    if isinstance(alert_data, dict) and 'detail' in alert_data:
                        # 新格式：{'detail': [...], 'hostsn': '...', 'num': 1}
                        detail_list = alert_data.get('detail', [])
                        for detail_item in detail_list:
                            # 合并外层和内层数据
                            merged_data = {**alert_data, **detail_item}
                            parsed_records = AlertParserService._parse_alert(merged_data, file_path)
                            if parsed_records:
                                # _parse_alert 返回列表，需要展平
                                records.extend(parsed_records)
                    else:
                        # 旧格式：直接解析
                        parsed_records = AlertParserService._parse_alert(alert_data, file_path)
                        if parsed_records:
                            # _parse_alert 返回列表，需要展平
                            records.extend(parsed_records)
                except Exception as e:
                    logger.warning(f"解析告警失败: {e}, 数据: {alert_data}")
                    continue
            
            logger.info(f"文件解析完成: {file_path}, 共 {len(records)} 条记录")
            return records
            
        except Exception as e:
            logger.error(f"解析文件失败: {file_path}, 错误: {e}")
            return []
    
    @staticmethod
    def _parse_alert(alert_data: Any, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        解析单条告警数据
        
        支持多xid告警的拆分：
        - 如果告警包含 Xid[48,63,94,154]，则为每个xid创建一条告警
        
        Args:
            alert_data: 原始告警数据
            file_path: 源文件路径
            
        Returns:
            解析后的告警记录列表（支持多xid拆分）
        """
        if not isinstance(alert_data, dict):
            return None
        
        # 提取告警类型
        alert_type = AlertParserService._extract_alert_type(alert_data)
        if not alert_type:
            return None
        
        # 提取xid列表（如果存在）
        xid_list = AlertParserService._extract_xid_list(alert_type)
        
        # 提取集群ID（传入file_path用于从文件名提取）
        cluster_id = AlertParserService._extract_cluster_id(alert_data, file_path)
        
        # 提取IP地址（优先从文件名提取，确保是真实IP而不是hostname）
        ip_address = AlertParserService._extract_ip(alert_data, file_path)
        
        # 验证IP格式（必须是x.x.x.x格式，不能是hostname）
        if ip_address:
            import re
            ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
            if not re.match(ip_pattern, ip_address):
                # 不是有效IP格式，清空
                ip_address = None
        
        # 如果没有有效IP但有hostname，使用hostname作为节点标识（仅用于显示，不用于诊断API）
        if not ip_address and 'hostname' in alert_data and alert_data['hostname']:
            hostname_value = str(alert_data['hostname']).strip()
            # 再次验证：如果hostname恰好是IP格式，则使用
            import re
            ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
            if re.match(ip_pattern, hostname_value):
                ip_address = hostname_value
        
        # 如果没有IP但有case_dev_name，尝试从中提取（CCE集群的备用方案）
        if not ip_address and 'case_dev_name' in alert_data and alert_data['case_dev_name']:
            case_dev_name = str(alert_data['case_dev_name']).strip()
            # 尝试从case_dev_name中提取IP（如果文件名中有IP）
            if file_path:
                filename = Path(file_path).name
                ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
                match = re.search(ip_pattern, filename)
                if match:
                    ip_address = match.group(1)
        
        # 判断是否为CCE集群（必须有cluster_id且以cce-开头）
        is_cce = cluster_id is not None and cluster_id.startswith('cce-')
        
        # 基础记录
        base_record = {
            'alert_type': alert_type,
            'ip': ip_address,
            'instance_id': AlertParserService._extract_instance_id(alert_data),
            'cluster_id': cluster_id,  # CCE集群ID或None（物理机）
            'is_cce_cluster': is_cce,  # 是否为CCE集群
            'component': AlertParserService._extract_component(alert_data),
            'severity': AlertParserService._extract_severity(alert_data),
            'timestamp': AlertParserService._extract_timestamp(alert_data, file_path),
            'file_path': file_path,
            'raw_data': alert_data,
            'status': 'pending'
        }
        
        # 如果有多个xid，为每个xid创建一条告警
        if xid_list and len(xid_list) > 1:
            records = []
            for xid in xid_list:
                record = base_record.copy()
                # 修改alert_type，添加xid标识
                record['alert_type'] = f"{alert_type.split('_Xid')[0]}_Xid[{xid}]"
                record['xid'] = xid  # 添加xid字段用于追踪
                records.append(record)
            return records
        else:
            # 单个xid或无xid，返回单条记录
            return [base_record]
    
    @staticmethod
    def _extract_alert_type(data: Dict) -> Optional[str]:
        """
        提取告警类型（标准化格式）
        
        策略：
        1. 如果包含 Xid[xxx]，提取为 xidxxx
        2. 如果是复合类型（包含_），提取第一个组件
        3. 否则直接使用原始类型
        
        例如：
        - "DriverError_EccError_GSPError_Xid[48]" → "xid48"
        - "RemappedPending_Xid[63]" → "xid63"
        - "DriverError_EccError" → "DriverError"
        - "NetLinkDown" → "NetLinkDown"
        """
        # 新格式：从 'reason' 字段提取
        raw_type = None
        if 'reason' in data and data['reason']:
            raw_type = str(data['reason']).strip()
        # 兼容旧格式：从 '项目' 字段提取
        elif '项目' in data and data['项目']:
            raw_type = str(data['项目']).strip()
        # 其次从 '中文' 字段提取
        elif '中文' in data and data['中文']:
            raw_type = str(data['中文']).strip()
        # 尝试从其他可能的字段提取
        else:
            for key in ['alert_type', 'type', 'name', 'key_name']:
                if key in data and data[key]:
                    raw_type = str(data[key]).strip()
                    break
        
        if not raw_type:
            return None
        
        # 标准化告警类型
        return AlertParserService._normalize_alert_type(raw_type)
    
    @staticmethod
    def _normalize_alert_type(raw_type: str) -> str:
        """
        标准化告警类型
        
        策略：
        1. 如果包含 Xid[xxx]，提取为 xidxxx（优先级最高）
        2. 如果是复合类型（包含_），提取第一个有意义的组件
        3. 否则直接使用原始类型
        
        Args:
            raw_type: 原始告警类型
            
        Returns:
            标准化后的告警类型
        """
        import re
        
        # 1. 优先提取XID（如果存在）
        xid_match = re.search(r'Xid\[(\d+)\]', raw_type)
        if xid_match:
            xid_number = xid_match.group(1)
            return f"xid{xid_number}"
        
        # 2. 处理复合类型（包含_）
        if '_' in raw_type:
            # 拆分组件
            parts = raw_type.split('_')
            
            # 过滤掉太短或无意义的部分
            meaningful_parts = [p for p in parts if len(p) >= 3 and not p.startswith('Xid')]
            
            if meaningful_parts:
                # 使用第一个有意义的组件
                return meaningful_parts[0]
        
        # 3. 直接使用原始类型
        return raw_type
    
    @staticmethod
    def _extract_xid_list(alert_type: str) -> Optional[list]:
        """
        从告警类型中提取xid列表
        
        例如：
        - "EccError_RemappedPending_Xid[48,63,94,154]" -> [48, 63, 94, 154]
        - "BWDrop_Xid[43]" -> [43]
        - "NoXid" -> None
        
        Args:
            alert_type: 告警类型字符串
            
        Returns:
            xid列表或None
        """
        import re
        
        # 匹配 Xid[...] 模式
        match = re.search(r'Xid\[([^\]]+)\]', alert_type)
        if not match:
            return None
        
        # 提取xid值并转换为整数列表
        xid_str = match.group(1)
        try:
            xid_list = [int(x.strip()) for x in xid_str.split(',')]
            return xid_list
        except ValueError:
            return None
    
    @staticmethod
    def _extract_ip(data: Dict, file_path: str = None) -> Optional[str]:
        """提取IP地址"""
        # 1. 尝试从常见字段提取
        for key in ['ip', 'IP', 'host', 'node']:
            if key in data and data[key]:
                value = str(data[key])
                # 验证IP格式
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', value):
                    return value
        
        # 2. 从文件名提取IP（优先级高）
        if file_path:
            filename = Path(file_path).name
            # 匹配IP格式：xxx.xxx.xxx.xxx
            ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
            match = re.search(ip_pattern, filename)
            if match:
                ip = match.group(1)
                logger.debug(f"从文件名提取IP: {ip}")
                return ip
        
        # 3. 尝试从整个数据中查找IP模式
        data_str = str(data)
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        match = re.search(ip_pattern, data_str)
        if match:
            return match.group()
        
        return None
    
    @staticmethod
    def _extract_instance_id(data: Dict) -> Optional[str]:
        """提取实例ID"""
        for key in ['instance_id', 'instanceId', 'id', 'uuid']:
            if key in data and data[key]:
                return str(data[key]).strip()
        return None
    
    @staticmethod
    def _extract_cluster_id(data: Dict, file_path: str = None) -> Optional[str]:
        """
        提取集群ID（仅CCE集群）
        
        优先级：
        1. 从文件名提取（如：长安-cce-uk1zi507-xxx.txt → cce-uk1zi507）
        2. 从 hostname 字段提取（如：cce-uk1zi507-05tberpr → cce-uk1zi507）
        
        Args:
            data: 告警数据
            file_path: 文件路径
            
        Returns:
            集群ID（仅CCE集群），物理机返回 None
        """
        # 1. 从文件名提取（最可靠）
        if file_path:
            filename = Path(file_path).name
            # 匹配 cce-xxxxxxxx 格式
            cce_pattern = r'cce-([a-z0-9]+)'
            match = re.search(cce_pattern, filename)
            if match:
                cluster_id = f"cce-{match.group(1)}"
                logger.debug(f"从文件名提取集群ID: {cluster_id}")
                return cluster_id
        
        # 2. 从 hostname 提取（新格式）
        if 'hostname' in data and data['hostname']:
            hostname = str(data['hostname']).strip()
            parts = hostname.split('-')
            if len(parts) >= 2 and parts[0] == 'cce':
                cluster_id = f"{parts[0]}-{parts[1]}"
                logger.debug(f"从hostname提取集群ID: {cluster_id}")
                return cluster_id
        
        # 3. 从 case_dev_name 提取（旧格式）
        if 'case_dev_name' in data and data['case_dev_name']:
            dev_name = str(data['case_dev_name']).strip()
            parts = dev_name.split('-')
            if len(parts) >= 2 and parts[0] == 'cce':
                cluster_id = f"{parts[0]}-{parts[1]}"
                logger.debug(f"从case_dev_name提取集群ID: {cluster_id}")
                return cluster_id
        
        # 物理机（cdhmlcc001、instance-等）返回 None
        logger.debug(f"未找到CCE集群ID，判定为物理机")
        return None
    
    @staticmethod
    def is_cce_cluster(data: Dict, file_path: str = None) -> bool:
        """
        判断是否为CCE集群节点
        
        Args:
            data: 告警数据
            file_path: 文件路径
            
        Returns:
            是否为CCE集群节点
        """
        cluster_id = AlertParserService._extract_cluster_id(data, file_path)
        return cluster_id is not None and cluster_id.startswith('cce-')
    
    @staticmethod
    def _extract_component(data: Dict) -> Optional[str]:
        """提取组件类型"""
        # 新格式：从 'device_type' 字段提取
        if 'device_type' in data and data['device_type']:
            return str(data['device_type']).strip()
        
        # 旧格式：从 'case_dev' 字段提取
        if 'case_dev' in data and data['case_dev']:
            return str(data['case_dev']).strip()
        
        # 兼容旧格式：从 '类别' 字段提取
        if '类别' in data and data['类别']:
            return str(data['类别']).strip()
        
        for key in ['component', 'category', 'type', 'device']:
            if key in data and data[key]:
                return str(data[key]).strip()
        
        return None
    
    @staticmethod
    def _extract_severity(data: Dict) -> str:
        """提取严重程度"""
        # 新格式：从 case_info 中提取（ERROR#...）
        if 'case_info' in data and data['case_info']:
            case_info = str(data['case_info']).upper()
            if case_info.startswith('ERROR'):
                return 'ERROR'
            elif case_info.startswith('FAIL'):
                return 'FAIL'
            elif case_info.startswith('WARN'):
                return 'WARN'
        
        # 旧格式：从 'case_type' 字段提取
        if 'case_type' in data and data['case_type']:
            level = str(data['case_type']).strip().upper()
            if level in ['FAIL', 'ERROR', 'WARN', 'GOOD']:
                return level
        
        # 兼容旧格式：从 'HAS级别' 字段提取
        if 'HAS级别' in data and data['HAS级别']:
            level = str(data['HAS级别']).strip().upper()
            if level in ['FAIL', 'ERROR', 'WARN', 'GOOD']:
                return level
        
        # 从其他字段提取
        for key in ['severity', 'level', 'priority']:
            if key in data and data[key]:
                level = str(data[key]).strip().upper()
                if level in ['FAIL', 'ERROR', 'WARN', 'GOOD']:
                    return level
        
        # 默认为 ERROR
        return 'ERROR'
    
    @staticmethod
    def _extract_timestamp(data: Dict, file_path: str) -> datetime:
        """提取时间戳"""
        # 新格式：从 'error_time' 字段提取（字符串格式）
        if 'error_time' in data and data['error_time']:
            try:
                # 格式: '2026-02-09 20:08:22'
                return datetime.strptime(str(data['error_time']), '%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 旧格式：从 'case_start_time' 字段提取（Unix时间戳）
        if 'case_start_time' in data and data['case_start_time']:
            try:
                timestamp = int(data['case_start_time'])
                return datetime.fromtimestamp(timestamp)
            except:
                pass
        
        # 尝试从数据中提取
        for key in ['timestamp', 'time', 'created_at', 'date', 'create_time']:
            if key in data and data[key]:
                try:
                    if isinstance(data[key], datetime):
                        return data[key]
                    # 尝试解析字符串
                    time_str = str(data[key])
                    # 尝试多种格式
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(time_str, fmt)
                        except:
                            continue
                except:
                    pass
        
        # 尝试从文件名提取日期
        filename = Path(file_path).stem
        # 匹配 YYYYMMDD 或 YYYY-MM-DD 格式
        date_pattern = r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})'
        match = re.search(date_pattern, filename)
        if match:
            try:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
            except:
                pass
        
        # 默认使用当前时间
        return datetime.now()
    
    @staticmethod
    def validate_record(record: Dict[str, Any]) -> bool:
        """
        验证记录是否有效
        
        Args:
            record: 告警记录
            
        Returns:
            是否有效
        """
        # 必需字段检查
        required_fields = ['alert_type', 'severity', 'timestamp']
        for field in required_fields:
            if field not in record or not record[field]:
                logger.warning(f"记录缺少必需字段: {field}")
                return False
        
        # 严重程度验证
        if record['severity'] not in ['FAIL', 'ERROR', 'WARN', 'GOOD']:
            logger.warning(f"无效的严重程度: {record['severity']}")
            return False
        
        return True
