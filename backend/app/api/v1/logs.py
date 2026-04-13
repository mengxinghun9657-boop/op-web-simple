"""
容器日志 API
提供实时容器日志流功能
"""

import asyncio
import subprocess
import threading
import queue
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_admin
from app.models.user import User

router = APIRouter(prefix="/logs", tags=["容器日志"])

# 允许的容器名称映射
ALLOWED_CONTAINERS = {
    "backend": "cluster-backend-api",
    "backend_worker": "cluster-backend-worker",
    "mysql": "cluster-mysql",
    "redis": "cluster-redis",
    "minio": "cluster-minio",
    "frontend": "cluster-frontend"
}


def get_current_user_from_token(
    token: str = Query(..., description="认证令牌"),
    db: Session = Depends(get_db)
):
    """从URL参数获取当前用户（用于SSE连接）"""
    return get_current_user(credentials=None, db=db, token=token)


def require_admin_sse(
    current_user: User = Depends(get_current_user_from_token)
):
    """SSE连接的管理员权限检查"""
    if current_user.role not in ['super_admin', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


@router.get("/stream/{container_name}")
async def stream_container_logs(
    container_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_sse)
):
    """
    实时流式获取容器日志 (SSE)

    需要管理员权限

    Args:
        container_name: 容器标识名 (backend/mysql/redis/minio/frontend)

    Returns:
        SSE 流，每行日志作为一个事件
    """
    # 验证容器名称
    if container_name not in ALLOWED_CONTAINERS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的容器名称。允许的容器: {', '.join(ALLOWED_CONTAINERS.keys())}"
        )

    actual_container = ALLOWED_CONTAINERS[container_name]

    async def log_generator():
        """生成日志流 - 使用线程避免阻塞事件循环"""
        log_queue = queue.Queue()
        stop_event = threading.Event()
        process = None

        def read_logs():
            """在后台线程中读取日志"""
            nonlocal process
            try:
                process = subprocess.Popen(
                    ["docker", "logs", "-f", "--tail", "100", actual_container],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # 发送初始连接成功消息
                log_queue.put(f"[系统] 已连接到 {actual_container} 日志流")

                # 持续读取日志
                while not stop_event.is_set() and process.poll() is None:
                    try:
                        line = process.stdout.readline()
                        if line:
                            clean_line = line.rstrip('\n\r')
                            if clean_line:
                                log_queue.put(clean_line)
                        else:
                            # 没有新数据，短暂等待
                            stop_event.wait(0.1)
                    except Exception as e:
                        log_queue.put(f"[错误] 读取日志失败: {str(e)}")
                        break

                # 进程结束
                if process.poll() is not None:
                    log_queue.put("[系统] 日志流已断开")

            except Exception as e:
                log_queue.put(f"[错误] 日志流异常: {str(e)}")
            finally:
                if process and process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=2)
                    except:
                        try:
                            process.kill()
                        except:
                            pass

        # 启动后台线程读取日志
        reader_thread = threading.Thread(target=read_logs, daemon=True)
        reader_thread.start()

        try:
            while True:
                try:
                    # 非阻塞方式从队列获取日志，带超时
                    line = log_queue.get(timeout=0.1)
                    # SSE 格式: data: <message>\n\n
                    yield f"data: {line}\n\n"
                except queue.Empty:
                    # 队列为空，让出控制权
                    await asyncio.sleep(0.05)
                    continue
        finally:
            # 客户端断开连接时清理
            stop_event.set()
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                    except:
                        pass

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/containers")
async def get_available_containers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取可查看日志的容器列表

    需要管理员权限
    """
    return {
        "containers": [
            {"id": key, "name": value, "description": get_container_description(key)}
            for key, value in ALLOWED_CONTAINERS.items()
        ]
    }


def get_container_description(container_key: str) -> str:
    """获取容器描述"""
    descriptions = {
        "backend": "后端 API 服务日志",
        "backend_worker": "后端 Worker 服务日志",
        "mysql": "MySQL 数据库日志",
        "redis": "Redis 缓存日志",
        "minio": "MinIO 对象存储日志",
        "frontend": "前端 Nginx 服务日志"
    }
    return descriptions.get(container_key, "未知服务")
