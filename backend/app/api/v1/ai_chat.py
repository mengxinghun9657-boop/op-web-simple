#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 对话 API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import List, Optional, Dict, Any
import httpx
import json
import os

from app.core.logger import logger
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.chat import ChatHistory
from app.services.ai.ernie_client import ERNIEClient

router = APIRouter()

# 初始化 ERNIE 客户端（使用统一配置）
ernie_client = ERNIEClient()


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: user, assistant, system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage] = Field(..., description="消息历史")
    context_data: Optional[Dict[str, Any]] = Field(None, description="上下文数据")
    temperature: float = Field(0.6, ge=0, le=1, description="温度参数")
    max_tokens: int = Field(1000, ge=1, le=4000, description="最大token数")


class DataQueryRequest(BaseModel):
    """数据查询请求（简化版）"""
    table: str = Field(..., description="表名")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件（可选）")
    limit: int = Field(20, ge=1, le=50, description="返回数量建议（实际会根据表大小智能调整）")
    columns: Optional[List[str]] = Field(None, description="指定返回的列（可选，默认返回所有列）")


@router.post("/chat", summary="AI 对话")
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    与 AI 对话
    - 支持上下文数据注入
    - 调用百度 ERNIE API
    - 保存对话历史
    """
    try:
        # 构建系统提示词
        system_prompt = build_system_prompt(request.context_data)
        
        # 准备消息列表
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # 添加用户消息历史
        for msg in request.messages:
            api_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 调用 ERNIE API（使用统一的 ERNIEClient）
        response = await ernie_client.chat(
            messages=api_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 保存对话历史
        # 保存用户最后一条消息
        if request.messages and request.messages[-1].role == "user":
            user_msg = ChatHistory(
                user_id=current_user.id,
                role="user",
                content=request.messages[-1].content,
                context_data=json.dumps(request.context_data, ensure_ascii=False) if request.context_data else None
            )
            db.add(user_msg)
        
        # 保存 AI 回复
        assistant_msg = ChatHistory(
            user_id=current_user.id,
            role="assistant",
            content=response,  # ERNIEClient.chat() 直接返回文本
            context_data=None
        )
        db.add(assistant_msg)
        db.commit()
        
        return {
            "success": True,
            "data": {
                "message": response,  # 直接使用返回的文本
                "usage": {}  # ERNIEClient 内部已处理
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"AI 对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI 对话失败: {str(e)}")


@router.get("/history", summary="获取对话历史")
async def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的对话历史"""
    try:
        history = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id
        ).order_by(
            ChatHistory.created_at.desc()
        ).limit(limit).all()
        
        # 反转顺序，使最早的消息在前
        history.reverse()
        
        return {
            "success": True,
            "data": [msg.to_dict() for msg in history]
        }
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history", summary="清空对话历史")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空用户的对话历史"""
    try:
        db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id
        ).delete()
        db.commit()
        
        return {
            "success": True,
            "message": "对话历史已清空"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"清空对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-data", summary="查询数据库数据")
async def query_database(
    request: DataQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询数据库数据供 AI 分析
    - 支持所有表查询
    - 智能数据采样和摘要生成
    - 自动精简数据避免超过上下文限制
    - 生成向量化的表结构描述
    """
    try:
        # 获取所有表的映射
        from app.models.base import Base
        table_models = {mapper.class_.__tablename__: mapper.class_ 
                       for mapper in Base.registry.mappers}
        
        # 检查表是否存在
        if request.table not in table_models:
            raise HTTPException(
                status_code=400, 
                detail=f"表 '{request.table}' 不存在。可用表: {', '.join(table_models.keys())}"
            )
        
        model = table_models[request.table]
        query = db.query(model)
        
        # 应用过滤条件
        if request.filters:
            query = apply_filters(query, model, request.filters)
        
        # 获取总数
        total = query.count()
        
        # 智能限制返回数量
        # 根据表大小自动调整：小表返回更多，大表返回更少
        if total <= 20:
            actual_limit = total  # 小表全部返回
        elif total <= 100:
            actual_limit = min(20, request.limit)  # 中等表返回20条
        else:
            actual_limit = min(10, request.limit)  # 大表只返回10条示例
        
        # 智能采样：如果数据量大，使用随机采样而不是简单截断
        if total > actual_limit * 2:
            # 使用随机采样
            from sqlalchemy import func
            results = query.order_by(func.random()).limit(actual_limit).all()
            logger.info(f"表 {request.table}: 使用随机采样，返回 {actual_limit}/{total} 条")
        else:
            # 数据量不大，按顺序返回
            results = query.limit(actual_limit).all()
            logger.info(f"表 {request.table}: 按顺序返回 {actual_limit}/{total} 条")
        
        # 转换为字典
        data = []
        for row in results:
            row_dict = row_to_dict(row, request.columns)
            data.append(row_dict)
        
        # 生成表结构描述（向量化的精简 prompt）
        table_schema = generate_table_schema_prompt(model, request.table)
        
        # 生成数据摘要（用于 AI 上下文）
        data_summary = generate_data_summary(request.table, data, total, actual_limit)
        
        # 组合成完整的 AI prompt
        ai_prompt = f"""{table_schema}

{data_summary}

请基于以上表结构和数据摘要进行分析。如果需要更详细的数据，请告诉我需要查询哪些具体条件。"""
        
        return {
            "success": True,
            "data": {
                "table": request.table,
                "count": len(data),
                "total": total,
                "rows": data,
                "summary": ai_prompt,  # 完整的 AI prompt
                "truncated": total > actual_limit,
                "sampled": total > actual_limit * 2  # 标记是否使用了随机采样
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询数据失败: {str(e)}")

@router.get("/tables", summary="获取所有可查询的表")
async def get_available_tables(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有可查询的数据库表"""
    try:
        logger.info(f"用户 {current_user.username} (ID: {current_user.id}) 正在获取表列表")
        from app.models.base import Base  # 修改：使用正确的 Base
        
        tables = []
        for mapper in Base.registry.mappers:
            table_name = mapper.class_.__tablename__
            table_doc = mapper.class_.__doc__ or table_name
            
            # 获取列信息
            columns = []
            for column in inspect(mapper.class_).columns:
                # 安全地获取类型字符串
                try:
                    type_str = str(column.type)
                except Exception as e:
                    logger.warning(f"无法转换列类型: {table_name}.{column.name}, 错误: {e}")
                    type_str = column.type.__class__.__name__
                
                columns.append({
                    "name": column.name,
                    "type": type_str,
                    "nullable": column.nullable,
                    "primary_key": column.primary_key
                })
            
            tables.append({
                "table_name": table_name,  # 修改：使用table_name而不是name
                "comment": table_doc.strip(),  # 修改：使用comment而不是description
                "table_comment": table_doc.strip(),  # 添加：兼容字段
                "name": table_name,  # 保留：向后兼容
                "description": table_doc.strip(),  # 保留：向后兼容
                "columns": columns
            })
        
        logger.info(f"成功返回 {len(tables)} 个表的信息")
        return {
            "success": True,
            "data": sorted(tables, key=lambda x: x["table_name"])
        }
        
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables-debug", summary="[调试] 获取表列表（无需认证）")
async def get_available_tables_debug(db: Session = Depends(get_db)):
    """
    调试用接口 - 无需认证
    用于排查是否是认证问题还是数据问题
    生产环境部署后应删除此接口
    """
    try:
        logger.warning("⚠️ 调试接口被调用: /tables-debug (无认证)")
        from app.models.base import Base  # 修改：使用正确的 Base
        
        tables = []
        for mapper in Base.registry.mappers:
            table_name = mapper.class_.__tablename__
            table_doc = mapper.class_.__doc__ or table_name
            
            # 获取列信息
            columns = []
            for column in inspect(mapper.class_).columns:
                # 安全地获取类型字符串
                try:
                    type_str = str(column.type)
                except Exception as e:
                    logger.warning(f"[调试] 无法转换列类型: {table_name}.{column.name}, 错误: {e}")
                    type_str = column.type.__class__.__name__
                
                columns.append({
                    "name": column.name,
                    "type": type_str,
                    "nullable": column.nullable,
                    "primary_key": column.primary_key
                })
            
            # 查询表中的数据量
            try:
                model = mapper.class_
                count = db.query(model).count()
            except:
                count = -1  # 查询失败
            
            tables.append({
                "name": table_name,
                "description": table_doc.strip(),
                "columns": columns,
                "row_count": count  # 添加数据量信息
            })
        
        logger.info(f"[调试] 返回 {len(tables)} 个表的信息")
        return {
            "success": True,
            "data": sorted(tables, key=lambda x: x["name"]),
            "warning": "这是调试接口，生产环境应删除"
        }
        
    except Exception as e:
        logger.error(f"[调试] 获取表列表失败: {e}")
        import traceback
        return {
            "success": False,
            "detail": str(e),
            "traceback": traceback.format_exc()
        }


# ==================== 辅助函数 ====================

def build_system_prompt(context_data: Optional[Dict[str, Any]]) -> str:
    """构建系统提示词"""
    base_prompt = """你是一个资深的运维数据分析助手。

你的职责：
1. 分析任务执行情况和趋势
2. 查询和解读系统资源使用数据
3. 分析监控数据，发现异常
4. 提供专业的运维建议和优化方案
5. 解答用户关于系统运维的问题

回答要求：
- 使用简洁、专业的语言
- 提供具体的数据支持
- 给出可操作的建议
- 必要时使用表格或列表展示数据
- 如果数据不足，明确说明需要哪些额外信息"""
    
    if context_data:
        # 使用摘要而不是完整数据，避免超过上下文限制
        if 'summary' in context_data:
            base_prompt += f"\n\n当前数据摘要：\n{context_data['summary']}"
        else:
            # 兼容旧格式
            base_prompt += f"\n\n当前数据上下文：\n```json\n{format_context_data(context_data)}\n```"
    
    return base_prompt


def format_context_data(data: Dict[str, Any]) -> str:
    """格式化上下文数据（限制大小）"""
    # 限制 JSON 字符串长度，避免超过上下文
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    max_length = 2000  # 最多2000字符
    
    if len(json_str) > max_length:
        json_str = json_str[:max_length] + "\n... (数据已截断)"
    
    return json_str


def generate_table_schema_prompt(model, table_name: str) -> str:
    """
    生成表结构的向量化描述（精简 prompt）
    用于帮助 AI 理解表结构，而不需要传递完整的列信息
    """
    mapper = inspect(model)
    
    # 基本信息
    prompt_lines = [
        f"## 数据表: {table_name}",
        f"表说明: {model.__doc__.strip() if model.__doc__ else '无说明'}",
        ""
    ]
    
    # 字段分类
    key_fields = []      # 主键和唯一键
    id_fields = []       # ID 类字段
    name_fields = []     # 名称类字段
    status_fields = []   # 状态类字段
    time_fields = []     # 时间类字段
    numeric_fields = []  # 数值类字段
    text_fields = []     # 文本类字段
    other_fields = []    # 其他字段
    
    for column in mapper.columns:
        col_name = column.name
        col_type = str(column.type)
        
        # 构建字段描述
        field_desc = f"{col_name} ({col_type})"
        
        # 分类
        if column.primary_key:
            key_fields.append(field_desc + " [主键]")
        elif 'id' in col_name.lower() and col_name != 'id':
            id_fields.append(field_desc)
        elif 'name' in col_name.lower() or 'title' in col_name.lower():
            name_fields.append(field_desc)
        elif 'status' in col_name.lower() or 'state' in col_name.lower():
            status_fields.append(field_desc)
        elif 'time' in col_name.lower() or 'date' in col_name.lower() or 'at' in col_name.lower():
            time_fields.append(field_desc)
        elif 'INT' in col_type.upper() or 'FLOAT' in col_type.upper() or 'DECIMAL' in col_type.upper():
            numeric_fields.append(field_desc)
        elif 'TEXT' in col_type.upper() or 'VARCHAR' in col_type.upper():
            text_fields.append(field_desc)
        else:
            other_fields.append(field_desc)
    
    # 按分类输出
    if key_fields:
        prompt_lines.append(f"**主键字段**: {', '.join(key_fields)}")
    if id_fields:
        prompt_lines.append(f"**关联ID**: {', '.join(id_fields)}")
    if name_fields:
        prompt_lines.append(f"**名称字段**: {', '.join(name_fields)}")
    if status_fields:
        prompt_lines.append(f"**状态字段**: {', '.join(status_fields)}")
    if time_fields:
        prompt_lines.append(f"**时间字段**: {', '.join(time_fields)}")
    if numeric_fields:
        prompt_lines.append(f"**数值字段**: {', '.join(numeric_fields)}")
    if text_fields:
        prompt_lines.append(f"**文本字段**: {', '.join(text_fields)}")
    if other_fields:
        prompt_lines.append(f"**其他字段**: {', '.join(other_fields)}")
    
    return "\n".join(prompt_lines)


def generate_data_summary(table: str, data: List[Dict], total: int, limit: int) -> str:
    """
    生成数据摘要，用于 AI 上下文
    避免将完整数据传递给 AI，减少 token 消耗
    """
    if not data:
        return f"\n## 查询结果\n表 '{table}' 查询结果为空。"
    
    # 基本统计
    summary_lines = [
        "\n## 查询结果",
        f"- 返回记录数: {len(data)} 条",
        f"- 总记录数: {total} 条"
    ]
    
    if total > limit:
        summary_lines.append(f"- ⚠️ 数据已采样，仅显示 {limit} 条代表性数据")
    
    # 数值字段统计
    fields = list(data[0].keys()) if data else []
    numeric_stats = {}
    
    for field in fields:
        values = [row.get(field) for row in data if row.get(field) is not None]
        if values and all(isinstance(v, (int, float)) for v in values):
            numeric_stats[field] = {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'count': len(values)
            }
    
    if numeric_stats:
        summary_lines.append("\n### 数值字段统计")
        for field, stats in numeric_stats.items():
            summary_lines.append(
                f"- **{field}**: 最小={stats['min']}, 最大={stats['max']}, "
                f"平均={stats['avg']:.2f}, 有效值={stats['count']}"
            )
    
    # 分类字段分布（取前5个最常见的值）
    categorical_stats = {}
    for field in fields:
        # 跳过明显的ID字段和时间字段
        if 'id' in field.lower() or 'time' in field.lower() or 'date' in field.lower() or 'at' in field.lower():
            continue
            
        values = [str(row.get(field)) for row in data if row.get(field) is not None]
        unique_count = len(set(values))
        
        # 如果唯一值数量少于总数的80%，认为是分类字段
        if values and unique_count < len(values) * 0.8 and unique_count <= 20:
            from collections import Counter
            counter = Counter(values)
            categorical_stats[field] = counter.most_common(5)
    
    if categorical_stats:
        summary_lines.append("\n### 分类字段分布")
        for field, distribution in categorical_stats.items():
            dist_str = ", ".join([f"{val}({count})" for val, count in distribution])
            summary_lines.append(f"- **{field}**: {dist_str}")
    
    # 示例数据（仅显示前3条，且只显示关键字段）
    summary_lines.append("\n### 示例数据（前3条）")
    for i, row in enumerate(data[:3], 1):
        # 优先显示关键字段
        priority_keys = ['id', 'name', 'title', 'username', 'status', 'type', 'created_at', 'updated_at']
        key_fields = {}
        
        # 先添加优先字段
        for key in priority_keys:
            if key in row:
                key_fields[key] = row[key]
        
        # 如果优先字段不足5个，补充其他字段
        if len(key_fields) < 5:
            for key, value in row.items():
                if key not in key_fields and len(key_fields) < 5:
                    key_fields[key] = value
        
        # 格式化输出
        field_strs = [f"{k}={v}" for k, v in key_fields.items()]
        summary_lines.append(f"{i}. {', '.join(field_strs)}")
    
    if len(data) > 3:
        summary_lines.append(f"... 还有 {len(data) - 3} 条记录")
    
    return "\n".join(summary_lines)


def apply_filters(query, model, filters: Dict[str, Any]):
    """应用过滤条件"""
    for field, value in filters.items():
        if hasattr(model, field):
            column = getattr(model, field)
            
            # 支持不同的过滤操作
            if isinstance(value, dict):
                # 复杂过滤: {"op": ">=", "value": 10}
                op = value.get("op", "=")
                val = value.get("value")
                
                if op == "=":
                    query = query.filter(column == val)
                elif op == "!=":
                    query = query.filter(column != val)
                elif op == ">":
                    query = query.filter(column > val)
                elif op == ">=":
                    query = query.filter(column >= val)
                elif op == "<":
                    query = query.filter(column < val)
                elif op == "<=":
                    query = query.filter(column <= val)
                elif op == "like":
                    query = query.filter(column.like(f"%{val}%"))
                elif op == "in":
                    query = query.filter(column.in_(val))
            else:
                # 简单过滤: {"field": "value"}
                query = query.filter(column == value)
    
    return query


def row_to_dict(row, columns: Optional[List[str]] = None) -> dict:
    """将 SQLAlchemy 对象转换为字典"""
    result = {}
    
    # 获取所有列
    mapper = inspect(row.__class__)
    
    for column in mapper.columns:
        col_name = column.name
        
        # 如果指定了列，只返回指定的列
        if columns and col_name not in columns:
            continue
        
        value = getattr(row, col_name)
        
        # 处理特殊类型
        if value is None:
            result[col_name] = None
        elif hasattr(value, 'isoformat'):
            # datetime 对象
            result[col_name] = value.isoformat()
        elif hasattr(value, 'value') and not isinstance(value, str):
            # Enum 对象（确保不是字符串）
            result[col_name] = value.value
        else:
            result[col_name] = value
    
    return result
