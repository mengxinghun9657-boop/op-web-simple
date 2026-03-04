#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
模板管理服务

实现需求：
- Requirements 8.1-8.7: 规则模板管理
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.rule_template import RuleTemplate

logger = logging.getLogger(__name__)


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_templates(self, category: Optional[str] = None) -> List[Dict]:
        """
        获取模板列表
        
        Args:
            category: 模板分类（可选）
            
        Returns:
            List[Dict]: 模板列表
        """
        query = self.db.query(RuleTemplate)
        
        if category:
            query = query.filter(RuleTemplate.category == category)
        
        templates = query.order_by(RuleTemplate.priority.desc()).all()
        
        return [template.to_dict() for template in templates]
    
    def get_template(self, template_id: int) -> Optional[Dict]:
        """获取单个模板"""
        template = self.db.query(RuleTemplate).filter(
            RuleTemplate.id == template_id
        ).first()
        
        return template.to_dict() if template else None
    
    def create_template(self, template_data: Dict) -> Dict:
        """创建自定义模板"""
        template = RuleTemplate(
            name=template_data["name"],
            category=template_data.get("category", "自定义"),
            description=template_data.get("description"),
            pattern=template_data["pattern"],
            intent_type=template_data["intent_type"],
            priority=template_data.get("priority", 50),
            rule_metadata=template_data.get("metadata"),
            is_system=False,
            created_by=template_data.get("created_by", "user")
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template.to_dict()
    
    def delete_template(self, template_id: int) -> bool:
        """删除模板（仅非系统模板）"""
        template = self.db.query(RuleTemplate).filter(
            RuleTemplate.id == template_id,
            RuleTemplate.is_system == False
        ).first()
        
        if not template:
            return False
        
        self.db.delete(template)
        self.db.commit()
        
        return True
    
    def export_templates(self, template_ids: List[int]) -> List[Dict]:
        """导出模板"""
        templates = self.db.query(RuleTemplate).filter(
            RuleTemplate.id.in_(template_ids)
        ).all()
        
        return [template.to_dict() for template in templates]
    
    def import_templates(self, templates_data: List[Dict]) -> Dict:
        """导入模板"""
        imported_count = 0
        skipped_count = 0
        
        for template_data in templates_data:
            # 检查是否已存在
            existing = self.db.query(RuleTemplate).filter(
                RuleTemplate.name == template_data["name"]
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # 创建新模板
            template = RuleTemplate(
                name=template_data["name"],
                category=template_data.get("category", "导入"),
                description=template_data.get("description"),
                pattern=template_data["pattern"],
                intent_type=template_data["intent_type"],
                priority=template_data.get("priority", 50),
                rule_metadata=template_data.get("metadata"),
                is_system=False,
                created_by="import"
            )
            
            self.db.add(template)
            imported_count += 1
        
        self.db.commit()
        
        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count
        }
