"""
故障手册匹配服务
"""
import logging
import re
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.alert import FaultManual

logger = logging.getLogger(__name__)


class ManualMatchService:
    """手册匹配服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def _extract_base_alert_type(alert_type: str) -> str:
        """
        从告警类型中提取基础告警类型（去掉XID部分）
        
        例如：
        - "EccError_RemappedPending_Xid[48]" → "EccError_RemappedPending"
        - "EccError_RemappedPending_Xid[48,63,94,154]" → "EccError_RemappedPending"
        - "EccError_RemappedPending" → "EccError_RemappedPending"
        
        Args:
            alert_type: 告警类型字符串
            
        Returns:
            基础告警类型（不包含XID）
        """
        # 移除 _Xid[...] 部分
        base_type = re.sub(r'_Xid\[[^\]]+\]$', '', alert_type)
        return base_type
    
    def match(self, alert_type: str, component: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        匹配故障手册
        
        支持包含XID的告警类型，自动提取基础告警类型进行匹配
        支持多个XID的匹配（如 Xid[48,63,94,154]）
        支持复合告警类型的部分匹配（如 DriverError_EccError_GSPError → DriverError）
        
        Args:
            alert_type: 告警类型（支持带XID的格式，如 EccError_RemappedPending_Xid[48] 或 Xid[48,63,94,154]）
            component: 组件类型(可选)
            
        Returns:
            匹配结果字典,未匹配返回None
            如果有多个XID，返回所有匹配的手册信息（合并）
        """
        # 提取基础告警类型（去掉XID）
        base_alert_type = self._extract_base_alert_type(alert_type)
        
        # 1. 精确匹配: category + alert_type
        if component:
            manual = self._exact_match(component, base_alert_type)
            if manual:
                logger.info(f"精确匹配成功: {component} - {base_alert_type}")
                return self._format_result(manual)
        
        # 2. 模糊匹配: 仅 alert_type
        manual = self._fuzzy_match(base_alert_type)
        if manual:
            logger.info(f"模糊匹配成功: {base_alert_type}")
            return self._format_result(manual)
        
        # 3. 部分匹配: 拆分复合告警类型（如 DriverError_EccError_GSPError → DriverError, EccError, GSPError）
        if '_' in base_alert_type:
            parts = base_alert_type.split('_')
            logger.info(f"尝试部分匹配: 拆分为 {parts}")
            
            # 尝试匹配每个部分（从最长到最短）
            for part in sorted(parts, key=len, reverse=True):
                if len(part) >= 3:  # 忽略太短的部分
                    manual = self._fuzzy_match(part)
                    if manual:
                        logger.info(f"部分匹配成功: {part} (原始类型={alert_type})")
                        return self._format_result(manual)
        
        # 4. XID匹配: 如果告警类型包含Xid[xxx]，尝试匹配xidxxx
        # 支持多个XID（如 Xid[48,63,94,154]）
        xid_match = re.search(r'Xid\[([^\]]+)\]', alert_type)
        if xid_match:
            xid_str = xid_match.group(1)
            # 提取所有XID编号（支持逗号分隔）
            xid_numbers = [x.strip() for x in xid_str.split(',')]
            
            logger.info(f"尝试XID匹配: 提取XID={xid_numbers}, 原始类型={alert_type}")
            
            # 尝试匹配所有XID
            matched_manuals = []
            for xid_number in xid_numbers:
                xid_type = f"xid{xid_number}"
                manual = self._fuzzy_match(xid_type)
                if manual:
                    logger.info(f"XID匹配成功: {xid_type}")
                    matched_manuals.append((xid_number, manual))
                else:
                    logger.warning(f"XID匹配失败: 手册中未找到 {xid_type}")
            
            # 如果有匹配的手册，合并返回
            if matched_manuals:
                return self._format_multi_xid_result(matched_manuals, alert_type)
        
        logger.warning(f"未匹配到手册: {alert_type}")
        return None
    
    def _exact_match(self, category: str, alert_type: str) -> Optional[FaultManual]:
        """精确匹配"""
        return self.db.query(FaultManual).filter(
            FaultManual.category == category,
            FaultManual.alert_type == alert_type
        ).first()
    
    def _fuzzy_match(self, alert_type: str) -> Optional[FaultManual]:
        """模糊匹配"""
        logger.debug(f"模糊匹配查询: alert_type={alert_type}")
        result = self.db.query(FaultManual).filter(
            FaultManual.alert_type == alert_type
        ).first()
        if result:
            logger.debug(f"模糊匹配成功: 找到记录 {result.alert_type}")
        else:
            logger.debug(f"模糊匹配失败: 未找到 {alert_type}")
        return result
    
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
        """
        格式化多个XID的匹配结果（合并）
        
        Args:
            matched_manuals: [(xid_number, manual), ...] 列表
            alert_type: 原始告警类型
            
        Returns:
            合并后的匹配结果
        """
        # 合并所有手册信息
        name_parts = []
        solution_parts = []
        danger_levels = []
        
        for xid_number, manual in matched_manuals:
            name_parts.append(f"XID{xid_number}: {manual.name_zh}")
            solution_parts.append(f"**XID{xid_number}**: {manual.recovery_plan}")
            danger_levels.append(manual.danger_level)
        
        # 选择最高危险等级
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
