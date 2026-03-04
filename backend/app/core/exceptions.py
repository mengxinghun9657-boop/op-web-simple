#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理中间件

实现统一的错误响应格式和用户友好的错误提示。

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import traceback
import time
import uuid
from typing import Dict, Any

from app.core.custom_exceptions import AIQueryException


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理中间件
    
    功能：
    1. 捕获所有未处理的异常
    2. 返回统一的错误响应格式
    3. 记录详细的错误日志（用于调试）
    4. 对用户隐藏技术细节（安全性）
    
    Validates: Requirements 10.1, 10.2
    """
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            return await call_next(request)
        
        except HTTPException:
            # FastAPI 的 HTTPException 直接抛出，由专门的处理器处理
            raise
        
        except AIQueryException as e:
            # 自定义异常：返回用户友好的错误消息
            logger.warning(
                f"AI Query Exception: {request.method} {request.url.path} - "
                f"{e.error_code}: {e.message}",
                extra={"request_id": request_id}
            )
            
            return _create_error_response(
                status_code=e.http_status,
                error_dict=e.to_dict(),
                request_id=request_id,
                debug=getattr(request.app.state, 'debug', False)
            )
        
        except Exception as e:
            # 未预期的异常：记录详细日志，返回通用错误消息
            logger.error(
                f"Unhandled Exception: {request.method} {request.url.path} - {str(e)}",
                extra={"request_id": request_id}
            )
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            return _create_error_response(
                status_code=500,
                error_dict={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "服务器内部错误，请稍后重试",
                    "details": {"error": str(e)} if getattr(request.app.state, 'debug', False) else {}
                },
                request_id=request_id,
                debug=getattr(request.app.state, 'debug', False)
            )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 异常处理器
    
    处理 FastAPI 的 HTTPException，返回统一格式。
    
    Validates: Requirements 10.1
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # 如果 detail 是字典，直接使用
    if isinstance(exc.detail, dict):
        error_dict = exc.detail
    else:
        error_dict = {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail)
        }
    
    return _create_error_response(
        status_code=exc.status_code,
        error_dict=error_dict,
        request_id=request_id,
        debug=getattr(request.app.state, 'debug', False)
    )


async def validation_exception_handler(request: Request, exc):
    """
    请求验证异常处理器
    
    处理 Pydantic 的验证错误，返回友好的错误消息。
    
    Validates: Requirements 10.1, 10.2
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # 提取验证错误信息
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({
            "field": field,
            "message": message,
            "type": error["type"]
        })
    
    error_dict = {
        "code": "VALIDATION_ERROR",
        "message": "请求参数验证失败",
        "details": {"errors": errors}
    }
    
    return _create_error_response(
        status_code=422,
        error_dict=error_dict,
        request_id=request_id,
        debug=getattr(request.app.state, 'debug', False)
    )


def _create_error_response(
    status_code: int,
    error_dict: Dict[str, Any],
    request_id: str,
    debug: bool = False
) -> JSONResponse:
    """
    创建统一的错误响应
    
    响应格式：
    {
        "status": "error",
        "error": {
            "code": "ERROR_CODE",
            "message": "用户友好的错误描述",
            "details": {...},  # 可选
            "suggestion": "操作建议"  # 可选
        },
        "timestamp": "2026-01-23T10:00:00Z",
        "request_id": "uuid"
    }
    
    Validates: Requirements 10.1, 10.2
    """
    response_content = {
        "status": "error",
        "error": error_dict,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": request_id
    }
    
    # 在调试模式下，可以包含更多技术细节
    if not debug and "details" in error_dict:
        # 生产环境：移除技术细节（Validates: Requirements 10.2）
        if "error_detail" in error_dict["details"]:
            del error_dict["details"]["error_detail"]
        if "error" in error_dict["details"]:
            del error_dict["details"]["error"]
    
    return JSONResponse(
        status_code=status_code,
        content=response_content
    )
