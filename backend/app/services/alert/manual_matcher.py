"""
故障手册匹配服务 - 优化版
支持多错误类型匹配
"""
import logging
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.alert import FaultManual

logger = logging.getLogger(__name__)


class ManualMatchService:
    """手册匹配服务 - 优化版"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def match_multiple(self, error_types: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        匹配多个错误类型的手册
        
        策略：
        - 每个错误类型单独匹配手册
        - 合并所有匹配结果
        - AI解读时将所有错误类型作为prompt
        
        Args:
            error_types: 错误类型列表
            
        Returns:
            合并后的匹配结果
        """
        if not error_types:
            return {'matched': False}
        
        # 匹配每个错误类型
        all_matches = []
        for error in error_types:
            alert_type = error.get('alert_type')
            component = error.get('component')
            
            if alert_type:
                match_result = self.match(alert_type, component)
                if match_result and match_result.get('matched'):
                    all_matches.append({
                        'error_type': alert_type,
                        'component': component,
                        'match': match_result
                    })
        
        if not all_matches:
            return {'matched': False}
        
        # 合并匹配结果
        return self._merge_match_results(all_matches, error_types)
    
    def match(self, alert_type: str, component: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        匹配单个故障手册
        
        Args:
            alert_type: 告警类型
            component: 组件类型(可选)
            
        Returns:
            匹配结果字典,未匹配返回None
        """
        # 提取基础告警类型（去掉XID）
        base_alert_type = self._extract_base_alert_type(alert_type)
        normalized_component = self._normalize_component(component)
        
        # 1. 精确匹配: category + alert_type
        if normalized_component:
            manual = self._exact_match(normalized_component, base_alert_type)
            if manual:
                logger.info(f"精确匹配成功: {normalized_component} - {base_alert_type}")
                return self._format_result(manual)
        
        # 2. 模糊匹配: 仅 alert_type
        manual = self._fuzzy_match(base_alert_type)
        if manual:
            logger.info(f"模糊匹配成功: {base_alert_type}")
            return self._format_result(manual)
        
        # 3. 部分匹配: 拆分复合告警类型
        if '_' in base_alert_type:
            parts = base_alert_type.split('_')
            logger.info(f"尝试部分匹配: 拆分为 {parts}")
            
            for part in sorted(parts, key=len, reverse=True):
                if len(part) >= 3:
                    manual = self._fuzzy_match(part)
                    if manual:
                        logger.info(f"部分匹配成功: {part} (原始类型={alert_type})")
                        return self._format_result(manual)
        
        # 4. XID匹配
        xid_match = re.search(r'Xid\[([^\]]+)\]', alert_type)
        if xid_match:
            xid_str = xid_match.group(1)
            xid_numbers = [x.strip() for x in xid_str.split(',')]
            
            logger.info(f"尝试XID匹配: 提取XID={xid_numbers}, 原始类型={alert_type}")
            
            matched_manuals = []
            for xid_number in xid_numbers:
                xid_type = f"xid{xid_number}"
                manual = self._fuzzy_match(xid_type)
                if manual:
                    logger.info(f"XID匹配成功: {xid_type}")
                    matched_manuals.append((xid_number, manual))
            
            if matched_manuals:
                return self._format_multi_xid_result(matched_manuals, alert_type)
        
        logger.warning(f"未匹配到手册: {alert_type}")
        return {'matched': False}
    
    def _extract_base_alert_type(self, alert_type: str) -> str:
        """提取基础告警类型（去掉XID）"""
        return re.sub(r'_Xid\[[^\]]+\]$', '', alert_type)

    def _normalize_component(self, component: Optional[str]) -> Optional[str]:
        """标准化组件名，避免 GPU/gpu 这类大小写差异导致匹配失败"""
        if not component:
            return None

        component_str = str(component).strip()
        if not component_str:
            return None

        component_aliases = {
            'gpu': 'GPU',
            'vm_gpu': 'GPU',
            'nic': 'Network',
            'network': 'Network',
            'cpu': 'CPU',
            'memory': 'Memory',
            'disk': 'Disk',
        }

        return component_aliases.get(component_str.lower(), component_str)
    
    def _exact_match(self, category: str, alert_type: str) -> Optional[FaultManual]:
        """精确匹配"""
        normalized_category = category.strip().lower()
        normalized_alert_type = alert_type.strip().lower()

        return self.db.query(FaultManual).filter(
            func.lower(func.trim(FaultManual.category)) == normalized_category,
            func.lower(func.trim(FaultManual.alert_type)) == normalized_alert_type
        ).first()
    
    def _fuzzy_match(self, alert_type: str) -> Optional[FaultManual]:
        """模糊匹配"""
        normalized_alert_type = alert_type.strip().lower()

        manual = self.db.query(FaultManual).filter(
            func.lower(func.trim(FaultManual.alert_type)) == normalized_alert_type
        ).first()
        if manual:
            return manual

        # 兜底：处理手册中存在前后缀或历史脏数据的情况
        return self.db.query(FaultManual).filter(
            func.lower(func.trim(FaultManual.alert_type)).contains(normalized_alert_type)
        ).first()
    
    def _format_result(self, manual: FaultManual) -> Dict[str, Any]:
        """格式化匹配结果"""
        return {
            'matched': True,
            'name_zh': manual.name_zh,
            'solution': manual.recovery_plan,
            'impact': manual.impact,
            'recovery': manual.recovery_plan,
            'danger_level': manual.danger_level,
            'customer_aware': manual.customer_aware,
            'has_level': manual.has_level,
            'manual_check': manual.manual_check
        }
    
    def _format_multi_xid_result(self, matched_manuals: list, alert_type: str) -> Dict[str, Any]:
        """格式化多个XID的匹配结果"""
        name_parts = []
        solution_parts = []
        danger_levels = []
        
        for xid_number, manual in matched_manuals:
            name_parts.append(f"XID{xid_number}: {manual.name_zh}")
            solution_parts.append(f"**XID{xid_number}**: {manual.recovery_plan}")
            danger_levels.append(manual.danger_level)
        
        danger_level_priority = {'CRITICAL': 3, 'WARN': 2, 'INFO': 1}
        max_danger_level = max(danger_levels, key=lambda x: danger_level_priority.get(x, 0))
        
        return {
            'matched': True,
            'name_zh': ' | '.join(name_parts),
            'solution': '\n\n'.join(solution_parts),
            'impact': f"检测到 {len(matched_manuals)} 个XID错误",
            'recovery': '\n\n'.join(solution_parts),
            'danger_level': max_danger_level,
            'customer_aware': any(m.customer_aware for _, m in matched_manuals),
            'has_level': any(m.has_level for _, m in matched_manuals),
            'manual_check': any(m.manual_check for _, m in matched_manuals),
            'xid_count': len(matched_manuals),
            'xid_numbers': [xid for xid, _ in matched_manuals]
        }
    
    def _merge_match_results(self, all_matches: List[Dict], error_types: List[Dict]) -> Dict[str, Any]:
        """
        合并多个匹配结果
        
        Args:
            all_matches: 所有匹配结果
            error_types: 所有错误类型
            
        Returns:
            合并后的结果
        """
        if not all_matches:
            return {'matched': False}
        
        # 收集所有信息
        name_parts = []
        solution_parts = []
        impact_parts = []
        danger_levels = []
        customer_aware = False
        has_level = False
        manual_check = False
        fault_items = []
        seen_fault_keys = set()
        
        for idx, match_info in enumerate(all_matches):
            match = match_info['match']
            error_type = match_info['error_type']
            component = match_info.get('component', '')
            error_data = error_types[idx] if idx < len(error_types) else {}
            raw_data = error_data.get('raw_data', {}) or {}
            device = error_data.get('device') or raw_data.get('device_id') or '-'
            part_model = error_data.get('part_model') or raw_data.get('part_model') or raw_data.get('device_type') or ''
            part_sn = error_data.get('part_sn') or raw_data.get('part_sn') or raw_data.get('device_sn') or ''
            impact_description = match.get('impact', '')
            solution = match.get('solution', '')
            fault_name = match.get('name_zh', '') or error_type

            fault_key = (device, error_type, part_sn)
            if fault_key not in seen_fault_keys:
                seen_fault_keys.add(fault_key)
                fault_items.append({
                    'device': device,
                    'device_slot': error_data.get('position') or raw_data.get('device_slot') or '',
                    'part_model': part_model,
                    'part_sn': part_sn,
                    'fault_name': fault_name,
                    'alert_type': error_type,
                    'severity': error_data.get('severity', 'ERROR'),
                    'danger_level': match.get('danger_level', 'P2'),
                    'customer_aware': match.get('customer_aware', False),
                    'impact_description': impact_description,
                    'solution': solution,
                    'manual_check': match.get('manual_check', ''),
                    'timestamp': error_data.get('timestamp').isoformat() if error_data.get('timestamp') else '',
                    'source': error_data.get('source', '') or raw_data.get('source', '')
                })
            
            concise_name = f"{device}: {fault_name}" if device and device != '-' else fault_name
            name_parts.append(concise_name)
            solution_parts.append(f"{device}: {solution}" if device and device != '-' else solution)
            impact_parts.append(f"{device}: {error_type}，{impact_description}" if device and device != '-' else f"{error_type}: {impact_description}")
            danger_levels.append(match.get('danger_level', 'INFO'))
            customer_aware = customer_aware or match.get('customer_aware', False)
            has_level = has_level or match.get('has_level', False)
            manual_check = manual_check or match.get('manual_check', False)
        
        # 选择最高危险等级
        danger_level_priority = {'CRITICAL': 3, 'WARN': 2, 'INFO': 1}
        max_danger_level = max(danger_levels, key=lambda x: danger_level_priority.get(x, 0))
        
        # 构建AI解读用的完整prompt
        all_error_types_str = '\n'.join([
            f"- {e.get('device') or '-'}: {e.get('alert_type')} ({e.get('component')}, {e.get('severity')})"
            for e in error_types
        ])

        unique_name_parts = list(dict.fromkeys([part for part in name_parts if part]))
        unique_solution_parts = list(dict.fromkeys([part for part in solution_parts if part]))
        unique_impact_parts = list(dict.fromkeys([part for part in impact_parts if part]))
        
        return {
            'matched': True,
            'name_zh': ' | '.join(unique_name_parts),
            'solution': '\n'.join(unique_solution_parts),
            'impact': f"检测到 {len(fault_items)} 个故障项:\n" + '\n'.join(unique_impact_parts),
            'recovery': '\n'.join(unique_solution_parts),
            'danger_level': max_danger_level,
            'customer_aware': customer_aware,
            'has_level': has_level,
            'manual_check': manual_check,
            'error_count': len(error_types),
            'matched_count': len(all_matches),
            'fault_items': fault_items,
            # AI解读用的完整信息
            'ai_prompt': {
                'all_error_types': all_error_types_str,
                'all_solutions': '\n'.join(unique_solution_parts),
                'all_impacts': '\n'.join(unique_impact_parts)
            }
        }
