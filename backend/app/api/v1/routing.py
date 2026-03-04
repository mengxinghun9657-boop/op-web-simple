#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由规则管理 API

实现需求：
- Requirements 2.2: 创建路由规则
- Requirements 2.5: 查询、更新、删除路由规则
- Requirements 9.1-9.5: 测试路由规则
- Requirements 10.1-10.4: 导入导出路由规则
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai.routing_rule_manager import RoutingRuleManager
from app.services.ai.routing_logger import RoutingLogger
from app.services.ai.intent_router import get_intent_router
from app.core.logger import logger


router = APIRouter()


# ==================== Pydantic 模型 ====================

class RoutingRuleCreate(BaseModel):
    """创建路由规则请求"""
    pattern: str = Field(..., description="查询模式")
    intent_type: str = Field(..., description="意图类型")
    priority: int = Field(50, description="优先级（0-100）")
    description: Optional[str] = Field(None, description="规则描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据（推荐的表、数据库等）")


class RoutingRuleUpdate(BaseModel):
    """更新路由规则请求"""
    pattern: Optional[str] = Field(None, description="查询模式")
    intent_type: Optional[str] = Field(None, description="意图类型")
    priority: Optional[int] = Field(None, description="优先级（0-100）")
    description: Optional[str] = Field(None, description="规则描述")
    is_active: Optional[bool] = Field(None, description="是否启用")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RoutingRuleResponse(BaseModel):
    """路由规则响应"""
    id: int
    pattern: str
    intent_type: str
    priority: int
    description: Optional[str]
    is_active: bool
    metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class RoutingTestRequest(BaseModel):
    """测试路由规则请求"""
    queries: List[str] = Field(..., description="测试查询列表")


class RoutingTestResult(BaseModel):
    """测试路由结果"""
    query: str
    with_rules: Dict[str, Any]
    without_rules: Dict[str, Any]


class RoutingStatisticsRequest(BaseModel):
    """路由统计查询请求"""
    start_date: Optional[str] = Field(None, description="开始日期（ISO格式）")
    end_date: Optional[str] = Field(None, description="结束日期（ISO格式）")
    intent_type: Optional[str] = Field(None, description="意图类型过滤")
    routing_method: Optional[str] = Field(None, description="路由方法过滤")


class RoutingRuleImport(BaseModel):
    """导入路由规则请求"""
    pattern: str = Field(..., description="查询模式")
    intent_type: str = Field(..., description="意图类型")
    priority: int = Field(50, description="优先级（0-100）")
    description: Optional[str] = Field(None, description="规则描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    is_active: bool = Field(True, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建者")


class RoutingRulesImportRequest(BaseModel):
    """批量导入路由规则请求"""
    rules: List[RoutingRuleImport] = Field(..., description="规则列表")
    conflict_strategy: str = Field("skip", description="冲突策略：skip（跳过）或 overwrite（覆盖）")


# ==================== 智能辅助 Pydantic 模型 ====================

class NLConvertRequest(BaseModel):
    """自然语言转换请求"""
    natural_language: str = Field(..., description="自然语言描述")
    intent_type: str = Field(..., description="意图类型")


class RegexValidateRequest(BaseModel):
    """正则表达式验证请求"""
    regex: str = Field(..., description="正则表达式")
    intent_type: str = Field(..., description="意图类型")
    exclude_rule_id: Optional[int] = Field(None, description="排除的规则ID（编辑时使用）")


class TestMatchRequest(BaseModel):
    """测试匹配请求"""
    regex: str = Field(..., description="正则表达式")
    test_queries: List[str] = Field(..., description="测试查询列表")


class ExtractKeywordsRequest(BaseModel):
    """关键词提取请求"""
    pattern: str = Field(..., description="匹配模式")
    pattern_type: str = Field(..., description="模式类型：natural_language 或 regex")


class GenerateDescriptionRequest(BaseModel):
    """生成描述请求"""
    pattern: str = Field(..., description="匹配模式")
    intent_type: str = Field(..., description="意图类型")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")


class SuggestPriorityRequest(BaseModel):
    """优先级建议请求"""
    pattern: str = Field(..., description="匹配模式")
    intent_type: str = Field(..., description="意图类型")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")


class PredictImpactRequest(BaseModel):
    """影响预测请求"""
    pattern: str = Field(..., description="匹配模式")
    intent_type: str = Field(..., description="意图类型")


class SaveDraftRequest(BaseModel):
    """保存草稿请求"""
    draft_data: Dict[str, Any] = Field(..., description="草稿数据")


# ==================== 反馈和建议 Pydantic 模型 ====================

class RoutingFeedbackCreate(BaseModel):
    """提交反馈请求"""
    routing_log_id: int = Field(..., description="路由日志ID")
    correct_intent: str = Field(..., description="正确的意图类型")
    comment: Optional[str] = Field(None, description="反馈备注")


class RuleSuggestionUpdate(BaseModel):
    """更新规则建议请求"""
    pattern: Optional[str] = Field(None, description="查询模式")
    intent_type: Optional[str] = Field(None, description="意图类型")
    priority: Optional[int] = Field(None, description="优先级")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RuleSuggestionApprove(BaseModel):
    """采纳规则建议请求"""
    final_pattern: Optional[str] = Field(None, description="最终的模式")
    final_intent: Optional[str] = Field(None, description="最终的意图类型")
    final_priority: Optional[int] = Field(None, description="最终的优先级")
    final_metadata: Optional[Dict[str, Any]] = Field(None, description="最终的元数据")


class RuleSuggestionReject(BaseModel):
    """拒绝规则建议请求"""
    reason: Optional[str] = Field(None, description="拒绝原因")


class RuleSuggestionBatchApprove(BaseModel):
    """批量采纳规则建议请求"""
    suggestion_ids: List[int] = Field(..., description="建议ID列表")


class RuleSuggestionTest(BaseModel):
    """测试规则建议请求"""
    test_queries: List[str] = Field(..., description="测试查询列表")


# ==================== API 端点 ====================

@router.post("/rules", response_model=Dict[str, Any])
async def create_routing_rule(
    rule: RoutingRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建路由规则
    
    Validates: Requirements 2.2, 2.7
    """
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 创建规则
        created_rule = await rule_manager.create_rule(
            pattern=rule.pattern,
            intent_type=rule.intent_type,
            priority=rule.priority,
            description=rule.description,
            metadata=rule.metadata
        )
        
        logger.info(f"✅ 用户 {current_user.username} 创建路由规则: id={created_rule.id}")
        
        return {
            "success": True,
            "data": {
                "id": created_rule.id,
                "pattern": created_rule.pattern,
                "intent_type": created_rule.intent_type,
                "priority": created_rule.priority,
                "description": created_rule.description,
                "is_active": created_rule.is_active,
                "metadata": created_rule.rule_metadata,
                "created_at": created_rule.created_at.isoformat(),
                "updated_at": created_rule.updated_at.isoformat()
            },
            "message": "路由规则创建成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 创建路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=Dict[str, Any])
async def list_routing_rules(
    page: int = 1,
    page_size: int = 20,
    intent_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询路由规则列表
    
    Validates: Requirements 2.5
    """
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 查询规则
        result = await rule_manager.list_rules(
            page=page,
            page_size=page_size,
            intent_type=intent_type,
            is_active=is_active
        )
        
        return {
            "success": True,
            "data": result,
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 查询路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=Dict[str, Any])
async def get_routing_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取单个路由规则
    
    Validates: Requirements 2.5
    """
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 获取规则
        rule = await rule_manager.get_rule(rule_id)
        
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        return {
            "success": True,
            "data": rule,
            "message": "查询成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=Dict[str, Any])
async def update_routing_rule(
    rule_id: int,
    rule: RoutingRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新路由规则
    
    Validates: Requirements 2.5
    """
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 检查规则是否存在
        existing_rule = await rule_manager.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 更新规则
        updated_rule = await rule_manager.update_rule(
            rule_id=rule_id,
            pattern=rule.pattern,
            intent_type=rule.intent_type,
            priority=rule.priority,
            description=rule.description,
            is_active=rule.is_active,
            metadata=rule.metadata
        )
        
        if not updated_rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        logger.info(f"✅ 用户 {current_user.username} 更新路由规则: id={rule_id}")
        
        return {
            "success": True,
            "data": {
                "id": updated_rule.id,
                "pattern": updated_rule.pattern,
                "intent_type": updated_rule.intent_type,
                "priority": updated_rule.priority,
                "description": updated_rule.description,
                "is_active": updated_rule.is_active,
                "metadata": updated_rule.rule_metadata,
                "created_at": updated_rule.created_at.isoformat(),
                "updated_at": updated_rule.updated_at.isoformat()
            },
            "message": "路由规则更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}", response_model=Dict[str, Any])
async def delete_routing_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除路由规则
    
    Validates: Requirements 2.5
    """
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 检查规则是否存在
        existing_rule = await rule_manager.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        # 删除规则
        success = await rule_manager.delete_rule(rule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="规则不存在")
        
        logger.info(f"✅ 用户 {current_user.username} 删除路由规则: id={rule_id}")
        
        return {
            "success": True,
            "data": None,
            "message": "路由规则删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_routing_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    intent_type: Optional[str] = None,
    routing_method: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取路由统计信息
    
    Validates: Requirements 5.2, 5.3, 5.4
    """
    try:
        # 创建 RoutingLogger
        routing_logger = RoutingLogger(db=db)
        
        # 解析日期
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # 获取统计信息
        statistics = await routing_logger.get_statistics(
            start_date=start_dt,
            end_date=end_dt,
            intent_type=intent_type,
            routing_method=routing_method
        )
        
        return {
            "success": True,
            "data": statistics,
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取路由统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/low-confidence", response_model=Dict[str, Any])
async def get_low_confidence_logs(
    threshold: float = 0.7,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取低置信度的路由记录
    
    Validates: Requirements 5.3
    """
    try:
        # 创建 RoutingLogger
        routing_logger = RoutingLogger(db=db)
        
        # 获取低置信度记录
        result = await routing_logger.get_low_confidence_logs(
            threshold=threshold,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        return {
            "success": True,
            "data": {
                "list": result["logs"],
                "total": result["total"],
                "page": page,
                "page_size": page_size,
                "threshold": threshold
            },
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取低置信度记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=Dict[str, Any])
async def test_routing_rules(
    request: RoutingTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试路由规则效果
    
    支持批量测试查询，返回有无规则的对比结果。
    
    Validates: Requirements 9.1-9.5
    """
    try:
        from app.services.ai.intent_router import IntentRouter
        from app.services.ai.ernie_client import ERNIEClient
        from app.services.ai.embedding_model import EmbeddingModel
        
        # 创建 IntentRouter 实例（带规则）
        rule_manager = RoutingRuleManager(db=db)
        ernie_client = ERNIEClient()
        embedding_model = EmbeddingModel()
        
        router_with_rules = IntentRouter(
            ernie_client=ernie_client,
            embedding_model=embedding_model,
            routing_rule_manager=rule_manager
        )
        
        # 创建 IntentRouter 实例（不带规则）
        router_without_rules = IntentRouter(
            ernie_client=ernie_client,
            embedding_model=embedding_model,
            routing_rule_manager=None  # 不使用规则
        )
        
        # 测试每个查询
        results = []
        
        for query in request.queries:
            logger.info(f"🧪 测试查询: {query}")
            
            # 有规则的路由结果
            try:
                intent_with, conf_with, handlers_with, metadata_with, rule_id, similarity, method_with = await router_with_rules.route(query)
                with_rules_result = {
                    "intent": intent_with,
                    "confidence": round(conf_with, 4),
                    "handlers": handlers_with,
                    "metadata": metadata_with,
                    "matched_rule_id": rule_id,
                    "similarity_score": round(similarity, 4) if similarity else None,
                    "routing_method": method_with
                }
            except Exception as e:
                logger.error(f"❌ 有规则路由失败: {e}")
                with_rules_result = {
                    "error": str(e)
                }
            
            # 无规则的路由结果
            try:
                intent_without, conf_without, handlers_without, _, _, _, method_without = await router_without_rules.route(query)
                without_rules_result = {
                    "intent": intent_without,
                    "confidence": round(conf_without, 4),
                    "handlers": handlers_without,
                    "routing_method": method_without
                }
            except Exception as e:
                logger.error(f"❌ 无规则路由失败: {e}")
                without_rules_result = {
                    "error": str(e)
                }
            
            # 对比结果
            comparison = {
                "query": query,
                "with_rules": with_rules_result,
                "without_rules": without_rules_result,
                "is_different": (
                    with_rules_result.get("intent") != without_rules_result.get("intent")
                    if "error" not in with_rules_result and "error" not in without_rules_result
                    else None
                )
            }
            
            results.append(comparison)
        
        logger.info(f"✅ 测试完成，共 {len(results)} 个查询")
        
        return {
            "success": True,
            "data": {
                "results": results,
                "total": len(results)
            },
            "message": "测试完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 测试路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/export", response_model=Dict[str, Any])
async def export_routing_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出所有路由规则为 JSON 格式
    
    导出内容包括：
    - 版本信息
    - 导出时间
    - 所有规则（包含 metadata）
    
    Validates: Requirements 10.1
    """
    try:
        from datetime import datetime
        from app.models.routing_rule import RoutingRule
        from sqlalchemy import select
        
        # 查询所有规则（包括未启用的）
        stmt = select(RoutingRule).order_by(
            RoutingRule.priority.desc(),
            RoutingRule.created_at.desc()
        )
        
        result = await db.execute(stmt)
        rules = result.scalars().all()
        
        # 转换为导出格式
        exported_rules = []
        for rule in rules:
            exported_rules.append({
                "pattern": rule.pattern,
                "intent_type": rule.intent_type,
                "priority": rule.priority,
                "description": rule.description,
                "metadata": rule.rule_metadata,  # 包含 metadata
                "is_active": rule.is_active,
                "created_by": rule.created_by
            })
        
        logger.info(f"✅ 导出路由规则: 共 {len(exported_rules)} 条规则")
        
        return {
            "success": True,
            "data": {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "exported_by": current_user.username,
                "total_count": len(exported_rules),
                "rules": exported_rules
            },
            "message": "导出成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 导出路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/import", response_model=Dict[str, Any])
async def import_routing_rules(
    request: RoutingRulesImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导入路由规则
    
    支持批量导入规则，可选择冲突策略：
    - skip: 跳过已存在的规则（相同 pattern）
    - overwrite: 覆盖已存在的规则
    
    Validates: Requirements 10.2, 10.3, 10.4
    """
    try:
        # 验证冲突策略
        if request.conflict_strategy not in ["skip", "overwrite"]:
            raise HTTPException(
                status_code=400,
                detail="conflict_strategy 必须是 'skip' 或 'overwrite'"
            )
        
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 统计信息
        imported_count = 0
        skipped_count = 0
        failed_count = 0
        failed_rules = []
        
        # 逐个处理规则
        for idx, rule_data in enumerate(request.rules):
            try:
                # 验证必需字段
                if not rule_data.pattern or not rule_data.intent_type:
                    logger.warning(f"⚠️ 规则 {idx + 1} 缺少必需字段: pattern 或 intent_type")
                    failed_count += 1
                    failed_rules.append({
                        "index": idx + 1,
                        "pattern": rule_data.pattern,
                        "error": "缺少必需字段: pattern 或 intent_type"
                    })
                    continue
                
                # 检查是否已存在相同 pattern 的规则
                from app.models.routing_rule import RoutingRule
                from sqlalchemy import select
                
                stmt = select(RoutingRule).filter(
                    RoutingRule.pattern == rule_data.pattern
                )
                result = await db.execute(stmt)
                existing_rule = result.scalar_one_or_none()
                
                if existing_rule:
                    if request.conflict_strategy == "skip":
                        # 跳过该规则
                        logger.info(f"⏭️ 跳过已存在的规则: pattern={rule_data.pattern}")
                        skipped_count += 1
                        continue
                    elif request.conflict_strategy == "overwrite":
                        # 覆盖该规则
                        logger.info(f"🔄 覆盖已存在的规则: id={existing_rule.id}, pattern={rule_data.pattern}")
                        await rule_manager.update_rule(
                            rule_id=existing_rule.id,
                            pattern=rule_data.pattern,
                            intent_type=rule_data.intent_type,
                            priority=rule_data.priority,
                            description=rule_data.description,
                            metadata=rule_data.metadata,
                            is_active=rule_data.is_active
                        )
                        imported_count += 1
                        continue
                
                # 创建新规则
                await rule_manager.create_rule(
                    pattern=rule_data.pattern,
                    intent_type=rule_data.intent_type,
                    priority=rule_data.priority,
                    description=rule_data.description,
                    metadata=rule_data.metadata,
                    created_by=rule_data.created_by or current_user.username
                )
                
                imported_count += 1
                logger.info(f"✅ 导入规则 {idx + 1}: pattern={rule_data.pattern}")
                
            except Exception as e:
                logger.error(f"❌ 导入规则 {idx + 1} 失败: {e}")
                failed_count += 1
                failed_rules.append({
                    "index": idx + 1,
                    "pattern": rule_data.pattern,
                    "error": str(e)
                })
        
        # 返回导入统计
        result_data = {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "total_count": len(request.rules)
        }
        
        # 如果有失败的规则，添加详情
        if failed_rules:
            result_data["failed_rules"] = failed_rules
        
        logger.info(
            f"✅ 导入完成: 成功={imported_count}, 跳过={skipped_count}, 失败={failed_count}"
        )
        
        return {
            "success": True,
            "data": result_data,
            "message": f"导入完成: 成功 {imported_count} 条, 跳过 {skipped_count} 条, 失败 {failed_count} 条"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 导入路由规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=Dict[str, Any])
async def convert_natural_language(
    request: NLConvertRequest,
    db: Session = Depends(get_db)
    # 移除认证要求，允许匿名访问
):
    """
    自然语言转换为正则表达式
    
    Validates: Requirements 2.1, 2.2, 2.3
    """
    try:
        from app.services.routing.nl_converter import NLConverter
        
        # 创建转换服务
        converter = NLConverter()
        
        # 执行转换
        result = await converter.convert(
            natural_language=request.natural_language,
            intent_type=request.intent_type
        )
        
        logger.info(f"✅ 自然语言转换成功: {request.natural_language[:50]}...")
        
        return {
            "success": True,
            "data": result,
            "message": "转换成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 自然语言转换失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "ERNIE_API_ERROR",
            "message": f"转换失败: {str(e)}"
        }


@router.post("/validate", response_model=Dict[str, Any])
async def validate_regex(
    request: RegexValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    验证正则表达式
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
    """
    try:
        from app.services.routing.regex_validator import RegexValidator
        from app.services.routing.conflict_detector import ConflictDetector
        
        # 创建验证服务
        validator = RegexValidator()
        conflict_detector = ConflictDetector(db=db)
        
        # 验证语法
        validation_result = validator.validate(request.regex)
        
        # 检测冲突
        conflicts = await conflict_detector.detect_conflicts(
            pattern=request.regex,
            intent_type=request.intent_type,
            exclude_rule_id=request.exclude_rule_id
        )
        
        # 计算复杂度
        complexity_score = validator.calculate_complexity(request.regex)
        
        result = {
            "is_valid": validation_result["is_valid"],
            "syntax_errors": validation_result["errors"],
            "conflicts": conflicts,
            "complexity_score": complexity_score
        }
        
        logger.info(f"✅ 正则验证完成: valid={result['is_valid']}, conflicts={len(conflicts)}")
        
        return {
            "success": True,
            "data": result,
            "message": "验证完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 正则验证失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "VALIDATION_TIMEOUT",
            "message": f"验证失败: {str(e)}"
        }


@router.post("/test-match", response_model=Dict[str, Any])
async def test_match(
    request: TestMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试正则表达式匹配
    
    Validates: Requirements 4.2, 4.3, 4.5, 4.6
    """
    try:
        from app.services.routing.match_tester import MatchTester
        
        if not request.test_queries:
            return {
                "success": False,
                "data": None,
                "error": "EMPTY_TEST_QUERIES",
                "message": "测试查询列表不能为空"
            }
        
        # 创建测试服务
        tester = MatchTester()
        
        # 执行测试
        result = tester.test_batch(
            regex=request.regex,
            queries=request.test_queries
        )
        
        logger.info(f"✅ 测试匹配完成: match_rate={result['match_rate']}")
        
        return {
            "success": True,
            "data": result,
            "message": "测试完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 测试匹配失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"测试失败: {str(e)}"
        }


@router.post("/extract-keywords", response_model=Dict[str, Any])
async def extract_keywords(
    request: ExtractKeywordsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    提取关键词
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4
    """
    try:
        from app.services.routing.intelligent_assistant import IntelligentAssistant
        
        # 创建智能辅助服务
        assistant = IntelligentAssistant(db=db)
        
        # 提取关键词
        keywords = await assistant.extract_keywords(
            pattern=request.pattern,
            pattern_type=request.pattern_type
        )
        
        logger.info(f"✅ 关键词提取完成: {len(keywords)} 个关键词")
        
        return {
            "success": True,
            "data": {"keywords": keywords},
            "message": "提取成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 关键词提取失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"提取失败: {str(e)}"
        }


@router.get("/recommend-tables", response_model=Dict[str, Any])
async def recommend_tables(
    keywords: str,
    intent_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    推荐相关表
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.6
    """
    try:
        from app.services.routing.intelligent_assistant import IntelligentAssistant
        
        # 解析关键词
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # 创建智能辅助服务
        assistant = IntelligentAssistant(db=db)
        
        # 推荐表
        tables = await assistant.recommend_tables(
            keywords=keyword_list,
            intent_type=intent_type
        )
        
        logger.info(f"✅ 表推荐完成: {len(tables)} 个表")
        
        return {
            "success": True,
            "data": {"tables": tables},
            "message": "推荐成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 表推荐失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "TABLE_RECOMMENDATION_ERROR",
            "message": f"推荐失败: {str(e)}"
        }


@router.get("/templates", response_model=Dict[str, Any])
async def get_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取规则模板列表
    
    Validates: Requirements 8.1, 8.2, 8.4
    """
    try:
        from app.services.routing.template_manager import TemplateManager
        
        # 创建模板管理服务
        template_manager = TemplateManager(db=db)
        
        # 获取模板
        templates = await template_manager.get_templates(category=category)
        
        logger.info(f"✅ 获取模板完成: {len(templates)} 个模板")
        
        return {
            "success": True,
            "data": {"templates": templates},
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取模板失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "TEMPLATE_LOAD_ERROR",
            "message": f"获取失败: {str(e)}"
        }


@router.post("/generate-description", response_model=Dict[str, Any])
async def generate_description(
    request: GenerateDescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成规则描述
    
    Validates: Requirements 5.1, 5.2, 5.5
    """
    try:
        from app.services.routing.intelligent_assistant import IntelligentAssistant
        
        # 创建智能辅助服务
        assistant = IntelligentAssistant(db=db)
        
        # 生成描述
        description = await assistant.generate_description(
            pattern=request.pattern,
            intent_type=request.intent_type,
            keywords=request.keywords or []
        )
        
        logger.info(f"✅ 描述生成完成")
        
        return {
            "success": True,
            "data": description,
            "message": "生成成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 描述生成失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"生成失败: {str(e)}"
        }


@router.post("/suggest-priority", response_model=Dict[str, Any])
async def suggest_priority(
    request: SuggestPriorityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    建议优先级
    
    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.7
    """
    try:
        from app.services.routing.intelligent_assistant import IntelligentAssistant
        
        # 创建智能辅助服务
        assistant = IntelligentAssistant(db=db)
        
        # 建议优先级
        priority_suggestion = await assistant.suggest_priority(
            pattern=request.pattern,
            intent_type=request.intent_type,
            keywords=request.keywords or []
        )
        
        logger.info(f"✅ 优先级建议完成: {priority_suggestion['suggested_priority']}")
        
        return {
            "success": True,
            "data": priority_suggestion,
            "message": "建议成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 优先级建议失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"建议失败: {str(e)}"
        }


@router.post("/predict-impact", response_model=Dict[str, Any])
async def predict_impact(
    request: PredictImpactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预测规则影响
    
    Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
    """
    try:
        from app.services.routing.impact_predictor import ImpactPredictor
        
        # 创建影响预测服务
        predictor = ImpactPredictor(db=db)
        
        # 预测影响
        impact = await predictor.predict_impact(
            pattern=request.pattern,
            intent_type=request.intent_type
        )
        
        logger.info(f"✅ 影响预测完成: affected={impact['affected_query_count']}")
        
        return {
            "success": True,
            "data": impact,
            "message": "预测完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 影响预测失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "HISTORY_QUERY_ERROR",
            "message": f"预测失败: {str(e)}"
        }


@router.post("/drafts", response_model=Dict[str, Any])
async def save_draft(
    request: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    保存草稿
    
    Validates: Requirements 18.1, 18.2
    """
    try:
        from app.services.routing.draft_manager import DraftManager
        
        # 创建草稿管理服务
        draft_manager = DraftManager(db=db)
        
        # 保存草稿
        draft = await draft_manager.save_draft(
            user_id=current_user.username,
            draft_data=request.draft_data
        )
        
        logger.info(f"✅ 草稿保存成功: draft_id={draft['id']}")
        
        return {
            "success": True,
            "data": draft,
            "message": "草稿保存成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 草稿保存失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "DRAFT_SAVE_ERROR",
            "message": f"保存失败: {str(e)}"
        }


@router.get("/drafts", response_model=Dict[str, Any])
async def get_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取草稿列表
    
    Validates: Requirements 18.5, 18.6
    """
    try:
        from app.services.routing.draft_manager import DraftManager
        
        # 创建草稿管理服务
        draft_manager = DraftManager(db=db)
        
        # 获取草稿列表
        drafts = await draft_manager.get_drafts(user_id=current_user.username)
        
        logger.info(f"✅ 获取草稿列表成功: {len(drafts)} 个草稿")
        
        return {
            "success": True,
            "data": {"drafts": drafts},
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取草稿列表失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "DRAFT_LOAD_ERROR",
            "message": f"查询失败: {str(e)}"
        }


@router.get("/drafts/{draft_id}", response_model=Dict[str, Any])
async def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取草稿详情
    
    Validates: Requirements 18.4
    """
    try:
        from app.services.routing.draft_manager import DraftManager
        
        # 创建草稿管理服务
        draft_manager = DraftManager(db=db)
        
        # 获取草稿
        draft = await draft_manager.get_draft(
            draft_id=draft_id,
            user_id=current_user.username
        )
        
        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")
        
        logger.info(f"✅ 获取草稿详情成功: draft_id={draft_id}")
        
        return {
            "success": True,
            "data": draft,
            "message": "查询成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取草稿详情失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "DRAFT_LOAD_ERROR",
            "message": f"查询失败: {str(e)}"
        }


@router.delete("/drafts/{draft_id}", response_model=Dict[str, Any])
async def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除草稿
    
    Validates: Requirements 18.7
    """
    try:
        from app.services.routing.draft_manager import DraftManager
        
        # 创建草稿管理服务
        draft_manager = DraftManager(db=db)
        
        # 删除草稿
        success = await draft_manager.delete_draft(
            draft_id=draft_id,
            user_id=current_user.username
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="草稿不存在")
        
        logger.info(f"✅ 删除草稿成功: draft_id={draft_id}")
        
        return {
            "success": True,
            "data": None,
            "message": "删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除草稿失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": "DRAFT_DELETE_ERROR",
            "message": f"删除失败: {str(e)}"
        }


@router.post("/feedback", response_model=Dict[str, Any])
async def submit_routing_feedback(
    request: RoutingFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    提交路由错误反馈
    
    Validates: Requirements 6.3
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 提交反馈
        feedback = feedback_manager.submit_feedback(
            routing_log_id=request.routing_log_id,
            correct_intent=request.correct_intent,
            user_id=current_user.username,
            comment=request.comment
        )
        
        logger.info(
            f"✅ 用户 {current_user.username} 提交反馈: "
            f"log_id={request.routing_log_id}"
        )
        
        return {
            "success": True,
            "data": {
                "id": feedback.id,
                "routing_log_id": feedback.routing_log_id,
                "correct_intent": feedback.correct_intent,
                "user_id": feedback.user_id,
                "comment": feedback.comment,
                "created_at": feedback.created_at.isoformat()
            },
            "message": "反馈提交成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback", response_model=Dict[str, Any])
async def list_routing_feedback(
    page: int = 1,
    page_size: int = 20,
    correct_intent: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询反馈列表
    
    Validates: Requirements 6.5
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 查询反馈
        result = await feedback_manager.list_feedback(
            page=page,
            page_size=page_size,
            correct_intent=correct_intent
        )
        
        return {
            "success": True,
            "data": result,
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 查询反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions", response_model=Dict[str, Any])
async def list_rule_suggestions(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    intent_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询规则建议列表
    
    Validates: Requirements 7.4
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 查询建议
        result = await feedback_manager.list_suggestions(
            page=page,
            page_size=page_size,
            status=status,
            intent_type=intent_type
        )
        
        return {
            "success": True,
            "data": result,
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 查询规则建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/pending", response_model=Dict[str, Any])
async def get_pending_suggestions(
    page: int = 1,
    page_size: int = 20,
    intent_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取待审核的规则建议列表
    
    Validates: Requirements 14.1
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 查询待审核建议
        result = await feedback_manager.list_suggestions(
            page=page,
            page_size=page_size,
            status="pending",
            intent_type=intent_type
        )
        
        return {
            "success": True,
            "data": result,
            "message": "查询成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取待审核建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{suggestion_id}", response_model=Dict[str, Any])
async def get_suggestion_detail(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取规则建议详情
    
    Validates: Requirements 14.2
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 获取建议详情
        suggestion = await feedback_manager.get_suggestion(suggestion_id)
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="规则建议不存在")
        
        return {
            "success": True,
            "data": suggestion,
            "message": "查询成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取建议详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/suggestions/{suggestion_id}", response_model=Dict[str, Any])
async def update_suggestion(
    suggestion_id: int,
    request: RuleSuggestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新规则建议（审核时编辑）
    
    Validates: Requirements 14.3
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 更新建议
        success = await feedback_manager.update_suggestion(
            suggestion_id=suggestion_id,
            pattern=request.pattern,
            intent_type=request.intent_type,
            priority=request.priority,
            metadata=request.metadata
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="规则建议不存在")
        
        # 获取更新后的建议
        suggestion = await feedback_manager.get_suggestion(suggestion_id)
        
        logger.info(f"✅ 用户 {current_user.username} 更新建议: id={suggestion_id}")
        
        return {
            "success": True,
            "data": suggestion,
            "message": "更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/{suggestion_id}/approve", response_model=Dict[str, Any])
async def approve_suggestion(
    suggestion_id: int,
    request: RuleSuggestionApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    采纳规则建议（创建正式规则）
    
    Validates: Requirements 14.4, 14.8
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 采纳建议
        rule_id = await feedback_manager.adopt_suggestion(
            suggestion_id=suggestion_id,
            adopted_by=current_user.username,
            final_pattern=request.final_pattern,
            final_intent=request.final_intent,
            final_priority=request.final_priority,
            final_metadata=request.final_metadata
        )
        
        logger.info(
            f"✅ 用户 {current_user.username} 采纳建议: "
            f"suggestion_id={suggestion_id}, rule_id={rule_id}"
        )
        
        return {
            "success": True,
            "data": {
                "suggestion_id": suggestion_id,
                "created_rule_id": rule_id,
                "status": "adopted",
                "adopted_by": current_user.username,
                "adopted_at": datetime.now().isoformat()
            },
            "message": "规则已采纳并创建"
        }
        
    except Exception as e:
        logger.error(f"❌ 采纳建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/{suggestion_id}/reject", response_model=Dict[str, Any])
async def reject_suggestion(
    suggestion_id: int,
    request: RuleSuggestionReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    拒绝规则建议
    
    Validates: Requirements 14.9
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 拒绝建议
        success = await feedback_manager.reject_suggestion(
            suggestion_id=suggestion_id,
            rejected_by=current_user.username,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="规则建议不存在")
        
        logger.info(
            f"✅ 用户 {current_user.username} 拒绝建议: "
            f"suggestion_id={suggestion_id}"
        )
        
        return {
            "success": True,
            "data": {
                "suggestion_id": suggestion_id,
                "status": "rejected",
                "rejected_by": current_user.username,
                "rejected_at": datetime.now().isoformat()
            },
            "message": "规则已拒绝"
        }
        
    except Exception as e:
        logger.error(f"❌ 拒绝建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/batch-approve", response_model=Dict[str, Any])
async def batch_approve_suggestions(
    request: RuleSuggestionBatchApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量采纳规则建议
    
    Validates: Requirements 14.6
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 批量采纳
        result = await feedback_manager.batch_approve(
            suggestion_ids=request.suggestion_ids,
            approved_by=current_user.username
        )
        
        logger.info(
            f"✅ 用户 {current_user.username} 批量采纳建议: "
            f"成功={result['success_count']}, 失败={result['failed_count']}"
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"批量采纳完成: 成功 {result['success_count']} 条, 失败 {result['failed_count']} 条"
        }
        
    except Exception as e:
        logger.error(f"❌ 批量采纳失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/{suggestion_id}/test", response_model=Dict[str, Any])
async def test_suggestion(
    suggestion_id: int,
    request: RuleSuggestionTest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试规则建议效果
    
    支持批量测试查询，返回有无建议的对比结果。
    
    Validates: Requirements 14.10
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        from app.services.ai.intent_router import IntentRouter
        from app.services.ai.ernie_client import ERNIEClient
        from app.services.ai.embedding_model import EmbeddingModel
        
        # 获取建议详情
        feedback_manager = FeedbackManager(db=db)
        suggestion = await feedback_manager.get_suggestion(suggestion_id)
        
        if not suggestion:
            raise HTTPException(status_code=404, detail="规则建议不存在")
        
        # 创建临时规则（不保存到数据库）
        # 这里简化实现：直接使用 IntentRouter 测试
        
        # 创建 IntentRouter 实例（不带建议规则）
        rule_manager = RoutingRuleManager(db=db)
        ernie_client = ERNIEClient()
        embedding_model = EmbeddingModel()
        
        router_without_suggestion = IntentRouter(
            ernie_client=ernie_client,
            embedding_model=embedding_model,
            routing_rule_manager=rule_manager
        )
        
        # 测试每个查询
        results = []
        
        for query in request.test_queries:
            logger.info(f"🧪 测试查询: {query}")
            
            # 无建议的路由结果
            try:
                intent_without, conf_without, handlers_without, _, _, _, method_without = await router_without_suggestion.route(query)
                without_suggestion_result = {
                    "intent": intent_without,
                    "confidence": round(conf_without, 4),
                    "handlers": handlers_without,
                    "routing_method": method_without
                }
            except Exception as e:
                logger.error(f"❌ 无建议路由失败: {e}")
                without_suggestion_result = {
                    "error": str(e)
                }
            
            # 模拟有建议的路由结果
            # 简化：如果查询包含建议的 pattern，则使用建议的 intent
            with_suggestion_result = without_suggestion_result.copy()
            if suggestion["pattern"] in query:
                with_suggestion_result = {
                    "intent": suggestion["suggested_intent"],
                    "confidence": suggestion["confidence"],
                    "handlers": [suggestion["suggested_intent"]],
                    "routing_method": "routing_rule"
                }
            
            # 对比结果
            comparison = {
                "query": query,
                "with_suggestion": with_suggestion_result,
                "without_suggestion": without_suggestion_result,
                "improvement": (
                    with_suggestion_result.get("intent") != without_suggestion_result.get("intent")
                    if "error" not in with_suggestion_result and "error" not in without_suggestion_result
                    else None
                )
            }
            
            results.append(comparison)
        
        logger.info(f"✅ 测试完成，共 {len(results)} 个查询")
        
        return {
            "success": True,
            "data": {
                "results": results,
                "total": len(results)
            },
            "message": "测试完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 测试建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 异常检测 API ====================

@router.post("/suggestions/generate", response_model=Dict[str, Any])
async def generate_rule_suggestions(
    min_support_count: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成规则建议
    
    基于用户反馈数据自动生成规则建议。
    对于错误次数 >= min_support_count 的查询模式，生成规则建议。
    
    Validates: Requirements 7.1, 7.2, 7.3
    """
    try:
        from app.services.ai.feedback_manager import FeedbackManager
        
        # 创建 FeedbackManager
        feedback_manager = FeedbackManager(db=db)
        
        # 生成规则建议
        suggestions = await feedback_manager.generate_rule_suggestions(
            min_support_count=min_support_count
        )
        
        logger.info(
            f"✅ 用户 {current_user.username} 触发生成规则建议: "
            f"生成 {len(suggestions)} 个建议"
        )
        
        return {
            "success": True,
            "data": {
                "generated_count": len(suggestions),
                "min_support_count": min_support_count,
                "suggestions": [
                    {
                        "id": s.id,
                        "pattern": s.pattern,
                        "suggested_intent": s.suggested_intent,
                        "confidence": float(s.confidence),
                        "support_count": s.support_count
                    }
                    for s in suggestions
                ]
            },
            "message": f"成功生成 {len(suggestions)} 个规则建议"
        }
        
    except Exception as e:
        logger.error(f"❌ 生成规则建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies", response_model=Dict[str, Any])
async def get_routing_anomalies(
    limit: int = 10,
    severity: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取路由异常列表
    
    参考: 字节跳动RAG 8.2节 - 异常检测和自动修复
    
    Validates: Requirements 25.5
    """
    try:
        # 获取 IntentRouter 实例
        intent_router = get_intent_router()
        
        # 获取最近的异常
        anomalies = intent_router.get_recent_anomalies(
            limit=limit,
            severity=severity,
            anomaly_type=anomaly_type
        )
        
        # 获取统计数据
        statistics = intent_router.get_anomaly_statistics()
        
        return {
            "success": True,
            "data": {
                "anomalies": anomalies,
                "statistics": statistics
            },
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取路由异常失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies/statistics", response_model=Dict[str, Any])
async def get_anomaly_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取异常检测统计数据
    
    参考: 字节跳动RAG 8.2节 - 异常检测和自动修复
    
    Validates: Requirements 25.5
    """
    try:
        # 获取 IntentRouter 实例
        intent_router = get_intent_router()
        
        # 获取统计数据
        statistics = intent_router.get_anomaly_statistics()
        
        return {
            "success": True,
            "data": statistics,
            "message": "获取成功"
        }
        
    except Exception as e:
        logger.error(f"❌ 获取异常统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/enhanced", response_model=Dict[str, Any])
async def get_enhanced_routing_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取增强的路由统计信息

    包含:
    - 查询预处理监控 (预处理耗时、纠错次数、实体识别成功率)
    - 成本监控 (ERNIE API调用次数、缓存命中率、成本节省金额)
    - 查询改写监控 (查询分解次数、改写成功率、改写后准确率变化)
    - 异常检测监控

    参考: 字节跳动RAG 8.1节和13.3节 - 性能监控

    Validates: Requirements 26
    """
    try:
        # 获取 IntentRouter 实例
        intent_router = get_intent_router()

        # 获取增强的统计数据
        statistics = intent_router.get_enhanced_statistics()

        return {
            "success": True,
            "data": statistics,
            "message": "获取成功"
        }

    except Exception as e:
        logger.error(f"❌ 获取增强统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

