#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 对话历史模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base  # 使用 models.base 而不是 core.database


class ChatHistory(Base):
    """AI 对话历史"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant" or "system"
    content = Column(Text, nullable=False)
    context_data = Column(Text, nullable=True)  # JSON 格式的上下文数据
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    # 关系
    user = relationship("User", back_populates="chat_history")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
