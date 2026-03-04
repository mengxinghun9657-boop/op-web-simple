#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
草稿管理服务

实现需求：
- Requirements 18.1-18.7: 错误恢复和草稿管理
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.rule_draft import RuleDraft

logger = logging.getLogger(__name__)


class DraftManager:
    """草稿管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_draft(self, user_id: str, draft_data: Dict) -> Dict:
        """
        保存草稿
        
        Args:
            user_id: 用户ID
            draft_data: 草稿数据
            
        Returns:
            Dict: 保存的草稿信息
        """
        # 查找用户的现有草稿
        existing_draft = self.db.query(RuleDraft).filter(
            RuleDraft.user_id == user_id
        ).order_by(RuleDraft.updated_at.desc()).first()
        
        if existing_draft:
            # 更新现有草稿
            existing_draft.draft_data = draft_data
            existing_draft.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing_draft)
            return existing_draft.to_dict()
        else:
            # 创建新草稿
            draft = RuleDraft(
                user_id=user_id,
                draft_data=draft_data
            )
            self.db.add(draft)
            self.db.commit()
            self.db.refresh(draft)
            return draft.to_dict()
    
    def get_drafts(self, user_id: str) -> List[Dict]:
        """获取用户的草稿列表"""
        drafts = self.db.query(RuleDraft).filter(
            RuleDraft.user_id == user_id
        ).order_by(RuleDraft.updated_at.desc()).all()
        
        return [draft.to_dict() for draft in drafts]
    
    def get_draft(self, draft_id: int, user_id: str) -> Optional[Dict]:
        """获取单个草稿"""
        draft = self.db.query(RuleDraft).filter(
            RuleDraft.id == draft_id,
            RuleDraft.user_id == user_id
        ).first()
        
        return draft.to_dict() if draft else None
    
    def delete_draft(self, draft_id: int, user_id: str) -> bool:
        """删除草稿"""
        draft = self.db.query(RuleDraft).filter(
            RuleDraft.id == draft_id,
            RuleDraft.user_id == user_id
        ).first()
        
        if not draft:
            return False
        
        self.db.delete(draft)
        self.db.commit()
        
        return True
    
    def get_latest_draft(self, user_id: str) -> Optional[Dict]:
        """获取最新草稿"""
        draft = self.db.query(RuleDraft).filter(
            RuleDraft.user_id == user_id
        ).order_by(RuleDraft.updated_at.desc()).first()
        
        return draft.to_dict() if draft else None
