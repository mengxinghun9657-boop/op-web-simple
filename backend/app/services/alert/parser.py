"""
告警文件解析服务 - 优化版
支持多错误类型合并解析，支持新旧两种文件格式
"""
import ast
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParsedAlert:
    """解析后的告警数据结构"""
    # 基础信息（从文件名提取，所有错误类型共享）
    ip: str
    cluster_id: Optional[str]
    is_cce_cluster: bool
    file_path: str
    
    # 错误类型列表（一个文件可能包含多种错误）
    error_types: List[Dict[str, Any]] = field(default_factory=list)
    
    # 原始数据（用于调试）
    raw_data: List[Dict] = field(default_factory=list)
    
    def add_error_type(self, error_info: Dict[str, Any]):
        """添加错误类型"""
        self.error_types.append(error_info)
    
    def get_all_alert_types(self) -> List[str]:
        """获取所有告警类型列表"""
        return [e['alert_type'] for e in self.error_types]
    
    def get_primary_alert_type(self) -> str:
        """获取主告警类型（第一个）"""
        if self.error_types:
            return self.error_types[0]['alert_type']
        return 'Unknown'
    
    def get_severity(self) -> str:
        """获取最高严重程度"""
        severity_priority = {'FAIL': 4, 'ERROR': 3, 'WARN': 2, 'GOOD': 1}
        max_severity = 'GOOD'
        max_priority = 0
        
        for error in self.error_types:
            sev = error.get('severity', 'ERROR')
            priority = severity_priority.get(sev, 0)
            if priority > max_priority:
                max_priority = priority
                max_severity = sev
        
        return max_severity
    
    def get_earliest_timestamp(self) -> datetime:
        """获取最早的时间戳"""
        timestamps = [e['timestamp'] for e in self.error_types if 'timestamp' in e]
        return min(timestamps) if timestamps else datetime.now()


class AlertParserService:
    """告警解析服务 - 优化版"""
    
    # 已知的所有字段映射（固化）
    FIELD_MAPPINGS = {
        # 基础字段
        'alert_type': ['reason', '项目', '中文', 'alert_type', 'type', 'name', 'key_name'],
        'severity': ['case_type', 'HAS级别', 'severity', 'level', 'priority'],
        'component': ['device_type', 'case_dev', '类别', 'component', 'category', 'device'],
        'timestamp': ['error_time', 'case_start_time', 'timestamp', 'time', 'created_at', 'create_time'],
        'ip': ['ip', 'IP', 'host', 'node'],
        'hostname': ['hostname', 'case_dev_name', 'host'],
        'instance_id': ['instance_id', 'instanceId', 'id', 'uuid', 'case_key'],
        'device': ['device', 'devslot', 'device_id', 'device_slot'],
        'position': ['position', 'device_slot'],
        'hostsn': ['hostsn', 'host_sn', 'server_sn'],
        'part_model': ['part_model', 'partModel', 'gpu_model', 'device_model'],
        'part_sn': ['part_sn', 'partSn', 'device_sn', 'gpu_sn'],
        'recommend_op_type': ['recommend_op_type', 'recommendOpType', 'op_type'],
        'source': ['source', 'alarm_source'],
        'zone_info': ['zone_info', 'zone', 'region'],
        'warehouse': ['warehouse', 'idc', 'datacenter'],
        
        # 新格式专用字段
        'case_info': ['case_info'],
        'create_time': ['create_time', 'created_at'],
        'update_time': ['update_time', 'updated_at'],
        'handler': ['handler', 'handle_type', 'handler_type'],
        'racksn': ['racksn', 'rack_sn'],
    }
    
    @staticmethod
    def extract_node_info_from_filename(file_path: str) -> Optional[Dict[str, str]]:
        """
        从文件名提取节点信息（支持新旧格式）
        
        支持格式：
        - 旧格式: 长安-cce-uk1zi507-05tberpr-10.90.1.4.txt
        - 旧格式: 长安-FAIL-cce-uk1zi507-05tberpr-10.90.1.4.txt
        - 新格式: Error_长安-cdhmlcc001-bbc-cdonlinea-com-1566995.cdhmlcc001-10.90.128.114.txt
        
        Returns:
            {'cluster_id': 'cce-uk1zi507', 'ip': '10.90.1.4', 'is_cce': True}
        """
        filename = Path(file_path).name
        
        # 移除 Error_ 前缀（新格式）
        clean_name = re.sub(r'^Error_', '', filename)
        
        # 移除 FAIL 前缀（旧格式）
        clean_name = re.sub(r'-FAIL-', '-', clean_name)
        
        # 提取IP（最可靠）
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        ip_match = re.search(ip_pattern, clean_name)
        ip = ip_match.group(1) if ip_match else None
        
        # 提取集群ID（改进正则）
        # 匹配 cce-[8位随机字符] 格式，排除 ig/ld 等前缀
        cluster_id = None
        is_cce = False
        node_type = 'unknown'
        
        # 先尝试匹配标准CCE格式（8位字符）
        cce_pattern = r'cce-([a-z0-9]{8})'
        match = re.search(cce_pattern, clean_name)
        if match:
            cluster_id = f"cce-{match.group(1)}"
            is_cce = True
            node_type = 'cce'
            logger.debug(f"从文件名提取CCE集群ID: {cluster_id}")
        else:
            # 检查是否是BCC实例 (格式: cdhmlcc001-bcc-cdonlinea-com-<instance_id>.cdhmlcc001)
            bcc_pattern = r'cdhmlcc001-bcc-cdonlinea-com-(\d+)\.cdhmlcc001'
            bcc_match = re.search(bcc_pattern, clean_name)
            if bcc_match:
                instance_id = bcc_match.group(1)
                cluster_id = f"bcc-{instance_id}"
                node_type = 'bcc'
                logger.debug(f"从文件名提取BCC实例ID: {cluster_id}")
            # 检查是否是物理机 (格式: instance-<id>-<number>)
            elif 'instance-' in clean_name:
                instance_pattern = r'instance-([a-z0-9]+)-(\d+)'
                instance_match = re.search(instance_pattern, clean_name)
                if instance_match:
                    cluster_id = f"instance-{instance_match.group(1)}-{instance_match.group(2)}"
                    node_type = 'physical'
                    logger.debug(f"从文件名提取物理机ID: {cluster_id}")
                else:
                    cluster_id = 'physical'
                    node_type = 'physical'
                    logger.debug(f"判定为物理机: {filename}")
            else:
                logger.warning(f"无法识别的节点类型: {filename}")
        
        return {
            'cluster_id': cluster_id,
            'ip': ip,
            'is_cce': is_cce
        }
    
    @staticmethod
    def _get_field_value(data: Dict, field_name: str) -> Any:
        """
        根据字段名获取值（支持字段映射）
        
        Args:
            data: 原始数据字典
            field_name: 目标字段名
            
        Returns:
            字段值或None
        """
        if field_name not in AlertParserService.FIELD_MAPPINGS:
            return data.get(field_name)
        
        # 尝试所有可能的字段名
        for possible_name in AlertParserService.FIELD_MAPPINGS[field_name]:
            if possible_name in data and data[possible_name] is not None:
                return data[possible_name]
        
        return None
    
    @staticmethod
    def parse_file(file_path: str) -> Optional[ParsedAlert]:
        """
        解析告警文件（支持新旧格式）
        
        新格式: JSON 格式，包含 data 数组
        旧格式: Python 列表格式，直接是数组
        
        一个文件 = 一个节点的一条告警记录
        该记录可能包含多种错误类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            ParsedAlert 对象或 None
        """
        try:
            # 1. 从文件名提取节点信息
            node_info = AlertParserService.extract_node_info_from_filename(file_path)
            if not node_info or not node_info['ip']:
                logger.error(f"无法从文件名提取节点信息: {file_path}")
                return None
            
            # 2. 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                logger.error(f"文件为空: {file_path}")
                return None
            
            # 3. 判断文件格式并解析
            # 新格式1: 以 【Error接口数据】开头，包含 JSON 对象
            # 新格式2: 文件名以 Error_ 开头，纯 JSON 数组
            # 旧格式: Python 列表格式
            filename = Path(file_path).name
            if '【Error接口数据】' in content:
                logger.info(f"检测到新格式文件(带标记): {file_path}")
                parsed_data = AlertParserService._parse_new_format_with_header(content, file_path)
            elif filename.startswith('Error_'):
                logger.info(f"检测到新格式文件(纯JSON): {file_path}")
                parsed_data = AlertParserService._parse_new_format_pure_json(content, file_path)
            else:
                logger.info(f"检测到旧格式文件: {file_path}")
                parsed_data = AlertParserService._parse_old_format(content, file_path)
            
            if not parsed_data:
                return None
            
            # 4. 创建告警对象
            alert = ParsedAlert(
                ip=node_info['ip'],
                cluster_id=node_info['cluster_id'],
                is_cce_cluster=node_info['is_cce'],
                file_path=file_path,
                raw_data=parsed_data.get('raw_data', [])
            )
            
            # 5. 提取所有错误类型
            for error_data in parsed_data.get('errors', []):
                error_info = AlertParserService._parse_error_type(error_data)
                if error_info:
                    alert.add_error_type(error_info)
            
            if not alert.error_types:
                logger.error(f"文件解析后无有效错误类型: {file_path}")
                return None
            
            logger.info(f"文件解析完成: {file_path}, 共 {len(alert.error_types)} 种错误类型")
            return alert
            
        except Exception as e:
            logger.error(f"解析文件失败: {file_path}, 错误: {e}")
            return None
    
    @staticmethod
    def _parse_new_format_with_header(content: str, file_path: str) -> Optional[Dict]:
        """
        解析新格式文件（带【Error接口数据】标记的JSON格式）
        
        格式示例:
        【Error接口数据】
        {
          "data": [
            {
              "detail": [...],
              "hostsn": "xxx",
              "num": 1
            }
          ],
          "num": 1,
          "status": 200
        }
        """
        try:
            # 提取 JSON 部分（去掉开头的标记）
            json_start = content.find('{')
            if json_start == -1:
                logger.error(f"新格式文件未找到JSON内容: {file_path}")
                return None
            
            json_content = content[json_start:]
            data = json.loads(json_content)
            
            if 'data' not in data or not isinstance(data['data'], list):
                logger.error(f"新格式文件缺少data字段: {file_path}")
                return None
            
            errors = []
            raw_data = []
            
            for item in data['data']:
                if 'detail' in item and isinstance(item['detail'], list):
                    for detail in item['detail']:
                        errors.append(detail)
                        raw_data.append(detail)
            
            return {'errors': errors, 'raw_data': raw_data}
            
        except json.JSONDecodeError as e:
            logger.error(f"新格式文件JSON解析失败: {file_path}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"解析新格式文件失败: {file_path}, 错误: {e}")
            return None
    
    @staticmethod
    def _parse_new_format_pure_json(content: str, file_path: str) -> Optional[Dict]:
        """
        解析新格式文件（纯JSON数组格式，文件名以Error_开头）
        
        格式示例:
        [
          {
            "detail": [
              {"case_info": "ERROR#gpu1-DriverError", ...},
              {"case_info": "ERROR#gpu2-DriverError", ...}
            ],
            "hostsn": "xxx",
            "num": 8
          }
        ]
        """
        try:
            # 直接解析 JSON 数组
            data = json.loads(content)
            
            if not isinstance(data, list):
                logger.error(f"纯JSON格式文件不是数组: {file_path}")
                return None
            
            errors = []
            raw_data = []
            
            for item in data:
                if isinstance(item, dict) and 'detail' in item and isinstance(item['detail'], list):
                    for detail in item['detail']:
                        errors.append(detail)
                        raw_data.append(detail)
            
            return {'errors': errors, 'raw_data': raw_data}
            
        except json.JSONDecodeError as e:
            logger.error(f"纯JSON格式文件解析失败: {file_path}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"解析纯JSON格式文件失败: {file_path}, 错误: {e}")
            return None
    
    @staticmethod
    def _parse_old_format(content: str, file_path: str) -> Optional[Dict]:
        """
        解析旧格式文件（Python列表格式）
        
        格式示例:
        [{'detail': [...], 'hostsn': 'xxx', 'num': 1}]
        """
        try:
            lines = content.strip().split('\n')
            errors = []
            raw_data = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # 旧格式使用 ast.literal_eval 解析
                    line_data = ast.literal_eval(line)
                    
                    if not isinstance(line_data, list):
                        logger.warning(f"第 {line_num} 行不是列表: {file_path}")
                        continue
                    
                    for item in line_data:
                        if isinstance(item, dict):
                            # 检查是否为嵌套格式（包含detail数组）
                            if 'detail' in item and isinstance(item['detail'], list):
                                for detail_item in item['detail']:
                                    errors.append(detail_item)
                                    raw_data.append(detail_item)
                            else:
                                errors.append(item)
                                raw_data.append(item)
                                    
                except Exception as e:
                    logger.warning(f"解析第 {line_num} 行失败: {file_path}, 错误: {e}")
                    continue
            
            return {'errors': errors, 'raw_data': raw_data}
            
        except Exception as e:
            logger.error(f"解析旧格式文件失败: {file_path}, 错误: {e}")
            return None
    
    @staticmethod
    def _parse_error_type(data: Dict) -> Optional[Dict[str, Any]]:
        """
        解析单个错误类型
        
        Args:
            data: 原始数据
            
        Returns:
            错误类型信息字典
        """
        try:
            # 提取告警类型
            alert_type = AlertParserService._extract_alert_type(data)
            if not alert_type:
                logger.warning(f"无法提取告警类型: {data}")
                return None
            
            # 提取其他字段
            severity = AlertParserService._extract_severity(data)
            component = AlertParserService._extract_component(data)
            timestamp = AlertParserService._extract_timestamp(data)
            device = AlertParserService._get_field_value(data, 'device')
            position = AlertParserService._get_field_value(data, 'position')
            hostsn = AlertParserService._get_field_value(data, 'hostsn')
            part_model = AlertParserService._get_field_value(data, 'part_model')
            part_sn = AlertParserService._get_field_value(data, 'part_sn')
            recommend_op = AlertParserService._get_field_value(data, 'recommend_op_type')
            source = AlertParserService._get_field_value(data, 'source')
            zone_info = AlertParserService._get_field_value(data, 'zone_info')
            warehouse = AlertParserService._get_field_value(data, 'warehouse')
            
            # 提取XID列表
            xid_list = AlertParserService._extract_xid_list(alert_type)
            
            return {
                'alert_type': alert_type,
                'severity': severity,
                'component': component,
                'timestamp': timestamp,
                'device': device,
                'position': position,
                'hostsn': hostsn,
                'part_model': part_model,
                'part_sn': part_sn,
                'recommend_op_type': recommend_op,
                'source': source,
                'zone_info': zone_info,
                'warehouse': warehouse,
                'xid_list': xid_list,
                'raw_data': data
            }
            
        except Exception as e:
            logger.warning(f"解析错误类型失败: {e}")
            return None
    
    @staticmethod
    def _extract_alert_type(data: Dict) -> Optional[str]:
        """提取告警类型"""
        raw_type = AlertParserService._get_field_value(data, 'alert_type')
        if not raw_type:
            return None
        
        return AlertParserService._normalize_alert_type(str(raw_type))
    
    @staticmethod
    def _normalize_alert_type(raw_type: str) -> str:
        """标准化告警类型"""
        # 优先提取XID
        xid_match = re.search(r'Xid\[(\d+)\]', raw_type)
        if xid_match:
            return f"xid{xid_match.group(1)}"
        
        # 处理复合类型
        if '_' in raw_type:
            parts = raw_type.split('_')
            meaningful_parts = [p for p in parts if len(p) >= 3 and not p.startswith('Xid')]
            if meaningful_parts:
                return meaningful_parts[0]
        
        return raw_type
    
    @staticmethod
    def _extract_xid_list(alert_type: str) -> Optional[List[int]]:
        """提取XID列表"""
        match = re.search(r'Xid\[([^\]]+)\]', alert_type)
        if not match:
            return None
        xid_str = match.group(1)
        try:
            return [int(x.strip()) for x in xid_str.split(',')]
        except ValueError:
            return None
    
    @staticmethod
    def _extract_severity(data: Dict) -> str:
        """提取严重程度"""
        # 新格式：从 case_info 提取
        case_info = AlertParserService._get_field_value(data, 'case_info')
        if case_info:
            case_info_str = str(case_info).upper()
            if case_info_str.startswith('FAIL'):
                return 'FAIL'
            elif case_info_str.startswith('ERROR'):
                return 'ERROR'
            elif case_info_str.startswith('WARN'):
                return 'WARN'
        
        # 旧格式：从 case_type 提取
        case_type = AlertParserService._get_field_value(data, 'severity')
        if case_type:
            level = str(case_type).strip().upper()
            if level in ['FAIL', 'ERROR', 'WARN', 'GOOD']:
                return level
        
        return 'ERROR'
    
    @staticmethod
    def _extract_component(data: Dict) -> Optional[str]:
        """提取组件类型"""
        return AlertParserService._get_field_value(data, 'component')
    
    @staticmethod
    def _extract_timestamp(data: Dict) -> datetime:
        """提取时间戳"""
        # 新格式：error_time（字符串）
        error_time = AlertParserService._get_field_value(data, 'timestamp')
        if error_time:
            try:
                return datetime.strptime(str(error_time), '%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 旧格式：case_start_time（Unix时间戳）
        case_start_time = data.get('case_start_time')
        if case_start_time:
            try:
                return datetime.fromtimestamp(int(case_start_time))
            except:
                pass
        
        # 默认当前时间
        return datetime.now()
    
    @staticmethod
    def convert_to_alert_records(parsed_alert: ParsedAlert) -> List[Dict[str, Any]]:
        """
        将解析后的告警转换为数据库记录格式
        
        策略：
        - 一个文件生成一条主告警记录
        - 包含所有错误类型的信息
        
        Args:
            parsed_alert: 解析后的告警对象
            
        Returns:
            告警记录列表（通常只有一条）
        """
        if not parsed_alert or not parsed_alert.error_types:
            return []
        
        # 构建主告警记录
        primary_error = parsed_alert.error_types[0]
        
        record = {
            'alert_type': primary_error['alert_type'],
            'ip': parsed_alert.ip,
            'cluster_id': parsed_alert.cluster_id,
            'is_cce_cluster': parsed_alert.is_cce_cluster,
            'instance_id': None,
            'hostname': None,
            'component': primary_error['component'],
            'severity': parsed_alert.get_severity(),
            'timestamp': parsed_alert.get_earliest_timestamp(),
            'file_path': parsed_alert.file_path,
            'raw_data': {
                'error_types': parsed_alert.error_types,
                'all_alert_types': parsed_alert.get_all_alert_types()
            },
            'status': 'pending'
        }
        
        # 尝试从第一个错误提取instance_id和hostname
        if parsed_alert.error_types:
            first_error = parsed_alert.error_types[0]
            raw_data = first_error.get('raw_data', {})
            
            if 'case_key' in raw_data:
                record['instance_id'] = raw_data['case_key']
            
            hostname = AlertParserService._get_field_value(raw_data, 'hostname')
            if hostname:
                record['hostname'] = hostname
        
        return [record]
