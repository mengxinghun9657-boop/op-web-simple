#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
知识库管理 API 接口

提供知识库条目的 CRUD 操作接口：
- POST /api/v1/knowledge/entries - 创建知识条目
- GET /api/v1/knowledge/entries - 列表查询
- GET /api/v1/knowledge/entries/{id} - 详情查询
- PUT /api/v1/knowledge/entries/{id} - 更新条目
- DELETE /api/v1/knowledge/entries/{id} - 删除条目
- GET /api/v1/knowledge/search - 搜索接口
- POST /api/v1/knowledge/import - 批量导入

所有接口验证超级管理员权限和会话令牌。

Requirements: 17.1, 18.1, 18.5, 18.7, 19.1, 20.1, 23.1, 23.2
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import csv
import io

from app.core.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.services.ai.knowledge_manager import get_knowledge_manager, KnowledgeManager
from app.core.knowledge_auth_middleware import require_knowledge_session
from app.core.logger import logger


router = APIRouter()


# Request/Response Models
class KnowledgeEntryCreate(BaseModel):
    """创建知识条目请求"""
    title: str = Field(..., description="标题", min_length=1, max_length=500)
    content: str = Field(..., description="内容", min_length=1, max_length=10000)
    category: Optional[str] = Field(None, description="分类", max_length=100)
    tags: Optional[List[str]] = Field(None, description="标签列表")
    priority: Optional[str] = Field("medium", description="优先级", pattern="^(low|medium|high)$")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据（详情层数据）")


class KnowledgeEntryUpdate(BaseModel):
    """更新知识条目请求"""
    title: Optional[str] = Field(None, description="标题", min_length=1, max_length=500)
    content: Optional[str] = Field(None, description="内容", min_length=1, max_length=10000)
    category: Optional[str] = Field(None, description="分类", max_length=100)
    tags: Optional[List[str]] = Field(None, description="标签列表")
    priority: Optional[str] = Field(None, description="优先级", pattern="^(low|medium|high)$")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据（详情层数据）")


class KnowledgeEntryResponse(BaseModel):
    """知识条目响应"""
    id: int = Field(..., description="条目ID")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    priority: str = Field(..., description="优先级")
    source: str = Field(..., description="来源类型（manual/auto）")
    source_type: Optional[str] = Field(None, description="报告类型（auto时有效）")
    source_id: Optional[str] = Field(None, description="任务ID（auto时有效）")
    author: str = Field(..., description="创建者")
    updated_by: Optional[str] = Field(None, description="最后更新者")
    auto_generated: bool = Field(..., description="是否自动生成")
    manually_edited: bool = Field(..., description="是否被手动编辑")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    similarity: Optional[float] = Field(None, description="相似度（搜索时有效）")


class KnowledgeEntryListResponse(BaseModel):
    """知识条目列表响应"""
    entries: List[KnowledgeEntryResponse] = Field(..., description="条目列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class KnowledgeSearchResponse(BaseModel):
    """知识搜索响应"""
    results: List[KnowledgeEntryResponse] = Field(..., description="搜索结果")
    query: str = Field(..., description="查询文本")
    total: int = Field(..., description="结果数量")


class ImportResponse(BaseModel):
    """批量导入响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    imported_count: int = Field(..., description="成功导入数量")
    failed_count: int = Field(..., description="失败数量")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误详情")



@router.post(
    "/entries",
    response_model=KnowledgeEntryResponse,
    summary="创建知识条目",
    description="""
    创建新的知识条目。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    - 必填字段：title（标题）、content（内容）
    - 内容长度不超过 10000 字符
    
    **自动处理**：
    - 自动向量化内容并存储到向量数据库
    - 自动创建不存在的标签
    - 记录审计日志
    
    **Requirements**: 17.1, 17.7, 17.8, 17.9, 17.10, 17.11
    """
)
async def create_entry(
    request: Request,
    entry_data: KnowledgeEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)  # 验证会话令牌
):
    """
    创建知识条目
    
    验证流程：
    1. 验证用户角色（超级管理员）
    2. 验证会话令牌（通过 require_knowledge_session 中间件）
    3. 验证必填字段和内容长度
    4. 创建知识条目并向量化
    5. 记录审计日志
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            logger.warning(
                f"⚠️ 非超级管理员尝试创建知识条目: "
                f"user_id={current_user.id}, role={current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以创建知识条目"
            )
        
        # 2. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 3. 获取请求元数据
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # 4. 创建知识条目
        result = await knowledge_manager.create_entry(
            entry_data=entry_data.dict(exclude_none=True),
            user_id=str(current_user.id),
            username=current_user.username,
            session_id=None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 5. 获取完整的条目信息
        entry = await knowledge_manager.get_entry_by_id(result["id"])
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建成功但无法获取条目信息"
            )
        
        logger.info(
            f"✅ 知识条目创建成功: "
            f"entry_id={result['id']}, user={current_user.username}"
        )
        
        return KnowledgeEntryResponse(**entry)
    
    except ValueError as e:
        logger.error(f"❌ 知识条目验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 创建知识条目接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识条目失败: {str(e)}"
        )



@router.get(
    "/entries",
    response_model=KnowledgeEntryListResponse,
    summary="列出知识条目",
    description="""
    列出知识条目（分页）。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **支持的过滤条件**：
    - category: 分类过滤
    - tags: 标签过滤（逗号分隔）
    - author: 作者过滤
    - source: 来源过滤（manual/auto）
    
    **支持的排序字段**：
    - created_at: 创建时间（默认）
    - updated_at: 更新时间
    - priority: 优先级
    
    **Requirements**: 18.1, 18.2, 18.3, 18.4
    """
)
async def list_entries(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    tags: Optional[str] = None,  # 逗号分隔的标签列表
    author: Optional[str] = None,
    source: Optional[str] = None,
    order_by: str = "created_at",
    order_direction: str = "DESC",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    列出知识条目（分页）
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以访问知识库"
            )
        
        # 2. 解析标签
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 3. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 4. 列出条目
        result = await knowledge_manager.list_entries(
            page=page,
            page_size=page_size,
            category=category,
            tags=tags_list,
            author=author,
            source=source,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # 5. 转换为响应模型
        entries = [KnowledgeEntryResponse(**entry) for entry in result["entries"]]
        
        logger.info(
            f"✅ 列出知识条目: total={result['total']}, page={page}, "
            f"user={current_user.username}"
        )
        
        return KnowledgeEntryListResponse(
            entries=entries,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 列出知识条目接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出知识条目失败: {str(e)}"
        )



@router.get(
    "/entries/{entry_id}",
    response_model=KnowledgeEntryResponse,
    summary="获取知识条目详情",
    description="""
    根据ID获取知识条目详情。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **返回**：
    - 成功：返回完整的条目信息
    - 失败：返回 404 错误（条目不存在或已删除）
    
    **Requirements**: 18.5
    """
)
async def get_entry(
    request: Request,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    获取知识条目详情
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以访问知识库"
            )
        
        # 2. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 3. 获取条目
        entry = await knowledge_manager.get_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识条目不存在: entry_id={entry_id}"
            )
        
        logger.info(
            f"✅ 获取知识条目详情: entry_id={entry_id}, user={current_user.username}"
        )
        
        return KnowledgeEntryResponse(**entry)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 获取知识条目详情接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识条目详情失败: {str(e)}"
        )



@router.put(
    "/entries/{entry_id}",
    response_model=KnowledgeEntryResponse,
    summary="更新知识条目",
    description="""
    更新知识条目。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **支持部分更新（PATCH）**：
    - 仅更新提交的字段
    - 未提交的字段保持不变
    
    **自动处理**：
    - 如果内容被更新，自动重新生成向量
    - 如果是自动生成的条目，标记为手动编辑
    - 更新标签使用次数
    - 记录审计日志
    
    **Requirements**: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.8, 19.9, 19.10
    """
)
async def update_entry(
    request: Request,
    entry_id: int,
    updates: KnowledgeEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    更新知识条目
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以更新知识条目"
            )
        
        # 2. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 3. 获取请求元数据
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # 4. 更新条目
        success = await knowledge_manager.update_entry(
            entry_id=entry_id,
            updates=updates.dict(exclude_none=True),
            user_id=str(current_user.id),
            username=current_user.username,
            session_id=None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新失败"
            )
        
        # 5. 获取更新后的条目
        entry = await knowledge_manager.get_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新成功但无法获取条目信息"
            )
        
        logger.info(
            f"✅ 知识条目更新成功: entry_id={entry_id}, user={current_user.username}"
        )
        
        return KnowledgeEntryResponse(**entry)
    
    except ValueError as e:
        logger.error(f"❌ 知识条目更新验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 更新知识条目接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识条目失败: {str(e)}"
        )



@router.delete(
    "/entries/{entry_id}",
    summary="删除知识条目",
    description="""
    软删除知识条目。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **软删除机制**：
    - MySQL 中标记 deleted_at 字段
    - 向量存储中标记 is_deleted=true
    - 后续的向量检索不会返回该条目
    - 定时任务会物理清理软删除超过 30 天的条目
    
    **自动处理**：
    - 更新标签使用次数
    - 记录审计日志
    
    **Requirements**: 20.1, 20.2, 20.3, 20.4, 20.5, 20.8
    """
)
async def delete_entry(
    request: Request,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    删除知识条目（软删除）
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以删除知识条目"
            )
        
        # 2. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 3. 获取请求元数据
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # 4. 删除条目
        success = await knowledge_manager.soft_delete_entry(
            entry_id=entry_id,
            user_id=str(current_user.id),
            username=current_user.username,
            session_id=None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="删除失败"
            )
        
        logger.info(
            f"✅ 知识条目删除成功: entry_id={entry_id}, user={current_user.username}"
        )
        
        return {
            "success": True,
            "message": f"知识条目已删除: entry_id={entry_id}",
            "entry_id": entry_id
        }
    
    except ValueError as e:
        logger.error(f"❌ 知识条目删除验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 删除知识条目接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识条目失败: {str(e)}"
        )



@router.get(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="搜索知识条目",
    description="""
    使用向量检索搜索知识条目。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **搜索方式**：
    - 使用向量化模型将查询文本转换为向量
    - 在向量数据库中检索最相关的条目
    - 按相似度降序排序
    - 自动过滤已删除的条目
    
    **参数**：
    - query: 查询文本（必填）
    - top_k: 返回结果数量（默认3，最大10）
    - similarity_threshold: 相似度阈值（默认0.6）
    - category: 分类过滤（可选）
    
    **Requirements**: 18.7, 22.1, 22.2, 22.3, 22.4
    """
)
async def search_entries(
    request: Request,
    query: str,
    top_k: int = 3,
    similarity_threshold: float = 0.6,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    搜索知识条目（向量检索）
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以搜索知识库"
            )
        
        # 2. 验证参数
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="查询文本不能为空"
            )
        
        if top_k < 1 or top_k > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="top_k 必须在 1-10 之间"
            )
        
        if similarity_threshold < 0 or similarity_threshold > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="similarity_threshold 必须在 0-1 之间"
            )
        
        # 3. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 4. 搜索条目
        results = await knowledge_manager.search_entries(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            category=category
        )
        
        # 5. 转换为响应模型
        entries = [KnowledgeEntryResponse(**entry) for entry in results]
        
        logger.info(
            f"✅ 搜索知识条目: query={query[:50]}..., found={len(results)}, "
            f"user={current_user.username}"
        )
        
        return KnowledgeSearchResponse(
            results=entries,
            query=query,
            total=len(results)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 搜索知识条目接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索知识条目失败: {str(e)}"
        )



@router.get(
    "/categories",
    summary="获取分类列表",
    description="""
    获取所有知识库分类列表。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **返回**：
    - 分类列表（去重）
    - 按使用频率降序排序
    
    **Requirements**: 18.1, 18.2
    """
)
async def get_categories(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    获取分类列表
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以访问知识库"
            )
        
        # 2. 查询所有分类（去重）
        sql_stmt = text("""
            SELECT DISTINCT category
            FROM knowledge_entries
            WHERE deleted_at IS NULL AND category IS NOT NULL AND category != ''
            ORDER BY category ASC
        """)
        
        result = db.execute(sql_stmt)
        rows = result.fetchall()
        
        categories = [row[0] for row in rows if row[0]]
        
        logger.info(
            f"✅ 获取分类列表: total={len(categories)}, user={current_user.username}"
        )
        
        return {
            "success": True,
            "categories": categories,
            "total": len(categories)
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 获取分类列表接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类列表失败: {str(e)}"
        )



@router.post(
    "/import",
    response_model=ImportResponse,
    summary="批量导入知识条目",
    description="""
    批量导入知识条目。
    
    **要求**：
    - 用户必须是超级管理员（SUPER_ADMIN）
    - 必须通过知识库管理密码验证（会话令牌有效）
    
    **支持的文件格式**：
    - JSON: 包含条目数组的 JSON 文件
    - CSV: 包含 title, content, category, tags 列的 CSV 文件
    
    **JSON 格式示例**：
    ```json
    [
        {
            "title": "MySQL 主从同步延迟处理方案",
            "content": "当发现 MySQL 主从同步延迟超过 10 秒时...",
            "category": "故障处理",
            "tags": ["MySQL", "主从同步"],
            "priority": "high"
        }
    ]
    ```
    
    **CSV 格式示例**：
    ```csv
    title,content,category,tags,priority
    "MySQL 主从同步延迟处理方案","当发现 MySQL 主从同步延迟超过 10 秒时...","故障处理","MySQL,主从同步","high"
    ```
    
    **限制**：
    - 单次导入最多 1000 条
    - 单个条目导入失败不影响其他条目
    
    **Requirements**: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7, 23.8, 23.9
    """
)
async def import_entries(
    request: Request,
    file: UploadFile = File(..., description="导入文件（JSON 或 CSV）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_knowledge_session)
):
    """
    批量导入知识条目
    """
    try:
        # 1. 验证用户角色
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可以批量导入知识条目"
            )
        
        # 2. 读取文件内容
        content = await file.read()
        
        # 3. 解析文件
        entries_to_import = []
        errors = []
        
        if file.filename.endswith('.json'):
            # JSON 格式
            try:
                data = json.loads(content.decode('utf-8'))
                if not isinstance(data, list):
                    raise ValueError("JSON 文件必须包含条目数组")
                entries_to_import = data
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"JSON 解析失败: {str(e)}"
                )
        
        elif file.filename.endswith('.csv'):
            # CSV 格式
            try:
                csv_content = content.decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                
                for row in csv_reader:
                    # 解析标签（逗号分隔）
                    tags = []
                    if row.get('tags'):
                        tags = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                    
                    entries_to_import.append({
                        'title': row.get('title'),
                        'content': row.get('content'),
                        'category': row.get('category'),
                        'tags': tags if tags else None,
                        'priority': row.get('priority', 'medium')
                    })
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"CSV 解析失败: {str(e)}"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的文件格式，仅支持 JSON 和 CSV"
            )
        
        # 4. 验证数量限制
        if len(entries_to_import) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"单次导入最多 1000 条，当前: {len(entries_to_import)}"
            )
        
        if len(entries_to_import) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件中没有有效的条目"
            )
        
        # 5. 获取知识库管理器
        knowledge_manager = get_knowledge_manager(db)
        
        # 6. 获取请求元数据
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # 7. 逐个导入条目
        imported_count = 0
        failed_count = 0
        
        for index, entry_data in enumerate(entries_to_import):
            try:
                # 验证必填字段
                if not entry_data.get('title') or not entry_data.get('content'):
                    errors.append({
                        "index": index + 1,
                        "title": entry_data.get('title', '未知'),
                        "error": "缺少必填字段（title 或 content）"
                    })
                    failed_count += 1
                    continue
                
                # 创建条目
                await knowledge_manager.create_entry(
                    entry_data=entry_data,
                    user_id=str(current_user.id),
                    username=current_user.username,
                    session_id=None,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                imported_count += 1
                logger.info(f"✅ 导入条目 {index + 1}/{len(entries_to_import)}: {entry_data.get('title', '')[:50]}...")
            
            except Exception as e:
                errors.append({
                    "index": index + 1,
                    "title": entry_data.get('title', '未知'),
                    "error": str(e)
                })
                failed_count += 1
                logger.error(f"❌ 导入条目 {index + 1} 失败: {e}")
                # 继续处理其他条目
                continue
        
        logger.info(
            f"✅ 批量导入完成: imported={imported_count}, failed={failed_count}, "
            f"user={current_user.username}"
        )
        
        return ImportResponse(
            success=True,
            message=f"导入完成: 成功 {imported_count} 条，失败 {failed_count} 条",
            imported_count=imported_count,
            failed_count=failed_count,
            errors=errors
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 批量导入接口异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导入失败: {str(e)}"
        )
