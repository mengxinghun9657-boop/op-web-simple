"""
文件监控服务
监控指定目录下的告警文件，自动解析并存储到数据库
支持动态配置、多路径监控、优先级控制、文件模式匹配
"""
import time
import asyncio
import fnmatch
from pathlib import Path
from typing import Optional, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from sqlalchemy.orm import Session
from loguru import logger

from app.services.alert.alert_processor import AlertProcessor
from app.core.config_alert import settings


class PathSpecificHandler(FileSystemEventHandler):
    """特定路径的事件处理器"""
    
    def __init__(self, path_config, processor_factory, redis_client=None):
        """
        Args:
            path_config: 路径配置对象
            processor_factory: AlertProcessor工厂函数（返回新的processor实例）
            redis_client: Redis客户端
        """
        self.path_config = path_config
        self.processor_factory = processor_factory  # 工厂函数，按需创建processor
        self.redis_client = redis_client  # Redis客户端，用于跨进程去重
        self.redis_key_prefix = "alert:processed_file:"  # Redis key前缀
        self.redis_ttl = 3600  # 1小时过期（避免Redis无限增长）
    
    def try_acquire_file_lock(self, file_path: str) -> bool:
        """
        尝试获取文件处理锁（原子操作）
        使用Redis SETNX确保只有一个worker处理文件
        
        Returns:
            True: 成功获取锁，可以处理文件
            False: 文件已被其他worker处理，跳过
        """
        if not self.redis_client:
            return True  # Redis不可用时降级为允许处理
        
        try:
            redis_key = f"{self.redis_key_prefix}{file_path}"
            # SETNX: 只有key不存在时才设置，返回1表示成功，0表示已存在
            acquired = self.redis_client.set(redis_key, "1", nx=True, ex=self.redis_ttl)
            if acquired:
                logger.debug(f"获取文件处理锁成功: {file_path}")
                return True
            else:
                logger.debug(f"文件已被其他worker处理，跳过: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Redis获取锁失败: {str(e)}")
            return True  # 异常时降级为允许处理
    
    def unmark_file_processed(self, file_path: str):
        """取消标记（处理失败时）"""
        if not self.redis_client:
            return
        
        try:
            redis_key = f"{self.redis_key_prefix}{file_path}"
            self.redis_client.delete(redis_key)
            logger.debug(f"取消标记文件: {file_path}")
        except Exception as e:
            logger.error(f"Redis取消标记失败: {str(e)}")
    
    def match_pattern(self, file_path: str) -> bool:
        """匹配文件模式"""
        filename = Path(file_path).name
        return fnmatch.fnmatch(filename, self.path_config.file_pattern)
    
    def is_file_stable(self, file_path: str, max_wait: float = 3.0, check_interval: float = 0.1, stable_threshold: int = 3) -> bool:
        """
        检查文件是否稳定（大小不再变化）

        用于判断 scp/rsync 等工具是否已完成文件上传

        Args:
            file_path: 文件路径
            max_wait: 最大等待时间（秒）
            check_interval: 检查间隔（秒）
            stable_threshold: 连续几次大小相同认为稳定

        Returns:
            True: 文件稳定，可以处理
            False: 文件不稳定或检查失败
        """
        try:
            last_size = -1
            stable_count = 0
            start_time = time.time()

            while time.time() - start_time < max_wait:
                try:
                    current_size = Path(file_path).stat().st_size
                except FileNotFoundError:
                    # 文件被删除
                    return False

                if current_size == last_size:
                    stable_count += 1
                    # 连续 stable_threshold 次大小相同，认为文件稳定
                    if stable_count >= stable_threshold:
                        logger.debug(f"文件已稳定: {file_path}, 大小: {current_size}字节, 等待时间: {time.time() - start_time:.2f}秒")
                        return True
                else:
                    # 大小变化，重置计数器
                    stable_count = 0
                    last_size = current_size

                time.sleep(check_interval)

            # 超时，但文件至少稳定过一次
            if stable_count > 0:
                logger.warning(f"文件稳定检查超时，但文件已稳定: {file_path}, 大小: {last_size}字节")
                return True

            logger.warning(f"文件稳定检查超时: {file_path}")
            return False

        except Exception as e:
            logger.error(f"检查文件稳定性失败: {file_path}, 错误: {e}")
            return False

    def process_file(self, file_path: str):
        """处理文件（直接解析，无需文件同步）"""
        # 验证文件格式
        if not self.match_pattern(file_path):
            return

        # 检查文件稳定性（确保 scp/rsync 等工具已完成上传）
        if not self.is_file_stable(file_path):
            logger.debug(f"文件不稳定（可能正在上传），跳过: {file_path}")
            return

        # 获取文件大小（用于日志）
        try:
            file_size = Path(file_path).stat().st_size
        except:
            file_size = 0

        # 使用Redis原子操作获取文件处理锁（防止多worker重复处理）
        if not self.try_acquire_file_lock(file_path):
            logger.debug(f"文件已处理过（Redis原子锁），跳过: {file_path}")
            return

        logger.info(f"检测到新文件: {file_path} (路径: {self.path_config.path}, 优先级: {self.path_config.priority}, 大小: {file_size}字节)")

        try:
            # 使用线程池执行异步任务
            import concurrent.futures

            def run_async_task():
                """在新线程中运行异步任务"""
                processor = None
                try:
                    # 创建新的processor实例
                    processor = self.processor_factory()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(processor.process_alert_file(file_path))
                        logger.info(f"文件处理完成: {file_path}")
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(f"异步任务执行失败: {str(e)}", exc_info=True)
                    # 处理失败时取消标记，允许重试
                    self.unmark_file_processed(file_path)

            # 使用线程池执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async_task)
                # 不等待完成，避免阻塞文件监控

        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {str(e)}", exc_info=True)
            # 处理失败时取消标记，允许重试
            self.unmark_file_processed(file_path)
    
    def on_created(self, event: FileCreatedEvent):
        """新文件创建时触发"""
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event: FileModifiedEvent):
        """文件修改时触发

        使用 inotify (Observer) 时，scp 上传文件会触发：
        1. on_created - 创建空文件
        2. on_modified - 写入内容

        需要处理修改事件，因为文件可能在创建后才有完整内容
        """
        if not event.is_directory:
            # 使用 Redis 锁防止重复处理同一文件
            # process_file 内部会检查文件锁
            self.process_file(event.src_path)


class FileWatcherService:
    """文件监控服务
    
    监控源告警文件目录：/app/alerts_source（只读）
    文件会被同步到处理目录：/app/alerts（读写）
    """
    
    # 硬编码的监控路径配置
    ALERT_SOURCE_PATH = "/app/alerts_source"  # 源目录（只读）
    ALERT_PROCESS_PATH = "/app/alerts"        # 处理目录（读写）
    FILE_PATTERN = "*.txt"
    
    def __init__(self):
        """初始化文件监控服务（不持有数据库连接）"""
        self.observer: Optional[Observer] = None
        self.handler: Optional[PathSpecificHandler] = None
        self.processor = None  # 不在初始化时创建processor
        
        # 获取Redis客户端（用于跨进程去重）
        self.redis_client = None
        try:
            from app.core.redis_client import get_redis_client
            redis_wrapper = get_redis_client()
            self.redis_client = redis_wrapper.client  # 获取原始redis客户端
            logger.info("✅ 文件监控服务已连接Redis，启用跨进程去重")
        except Exception as e:
            logger.warning(f"⚠️ 无法连接Redis，文件去重功能将降级: {str(e)}")
    
    def _get_processor(self) -> AlertProcessor:
        """获取AlertProcessor实例（不再需要db参数）"""
        return AlertProcessor()
    
    def start_monitoring(self):
        """启动监控"""
        try:
            watch_path = Path(self.ALERT_SOURCE_PATH).expanduser()
            
            if not watch_path.exists():
                logger.error(f"告警源目录不存在: {watch_path}")
                return
            
            # 创建虚拟的路径配置对象（用于Handler）
            path_config = type('PathConfig', (), {
                'path': self.ALERT_SOURCE_PATH,
                'file_pattern': self.FILE_PATTERN,
                'priority': 100,
                'id': 1
            })()
            
            # 创建Observer和Handler（传入processor工厂函数）
            self.observer = Observer()
            self.handler = PathSpecificHandler(
                path_config=path_config,
                processor_factory=self._get_processor,  # 传入工厂函数
                redis_client=self.redis_client  # 传入Redis客户端
            )
            
            self.observer.schedule(self.handler, str(watch_path), recursive=False)
            self.observer.start()
            
            logger.info(f"文件监控服务已启动，监控源目录: {self.ALERT_SOURCE_PATH} (模式: {self.FILE_PATTERN})")
        except Exception as e:
            logger.error(f"启动文件监控失败: {str(e)}", exc_info=True)
    
    def add_watch_path(self, path_config):
        """添加监控路径（已弃用，保留用于兼容性）"""
        pass
    
    def remove_watch_path(self, path_id: int):
        """移除监控路径（已弃用，保留用于兼容性）"""
        pass
    
    def reload_paths(self):
        """重新加载监控路径（已弃用，保留用于兼容性）"""
        pass
    
    def stop(self):
        """停止监控"""
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
                logger.info("文件监控服务已停止")
            except Exception as e:
                logger.error(f"停止监控失败: {str(e)}", exc_info=True)
    
    def run(self):
        """运行监控（阻塞模式）"""
        self.start_monitoring()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def process_existing_files(self):
        """处理已存在的文件（初始化时使用）"""
        print(f"[DEBUG] process_existing_files() 方法开始执行")
        logger.info(f"[DEBUG] process_existing_files() 方法开始执行")
        print(f"[DEBUG] ALERT_SOURCE_PATH = {self.ALERT_SOURCE_PATH}")
        logger.info(f"[DEBUG] ALERT_SOURCE_PATH = {self.ALERT_SOURCE_PATH}")
        
        try:
            print(f"[DEBUG] 尝试创建Path对象...")
            logger.info(f"[DEBUG] 尝试创建Path对象...")
            watch_dir = Path(self.ALERT_SOURCE_PATH).expanduser()
            print(f"[DEBUG] Path对象创建成功: {watch_dir}")
            logger.info(f"[DEBUG] Path对象创建成功: {watch_dir}")
            
            print(f"[DEBUG] 检查目录是否存在...")
            logger.info(f"[DEBUG] 检查目录是否存在...")
            if not watch_dir.exists():
                print(f"[ERROR] 告警源目录不存在: {watch_dir}")
                logger.error(f"告警源目录不存在: {watch_dir}")
                return
            print(f"[DEBUG] 目录存在检查通过")
            logger.info(f"[DEBUG] 目录存在检查通过")
            
            print(f"[INFO] 开始处理已存在的文件，源路径: {watch_dir}")
            logger.info(f"开始处理已存在的文件，源路径: {watch_dir}")
            
            # 获取所有文件
            all_files = list(watch_dir.glob("*"))
            print(f"[INFO] 目录中共有 {len(all_files)} 个文件/文件夹")
            logger.info(f"目录中共有 {len(all_files)} 个文件/文件夹")
            
            # 打印所有文件名用于调试
            for f in all_files:
                print(f"  - {f.name} (is_file={f.is_file()})")
                logger.info(f"  - {f.name} (is_file={f.is_file()})")
            
            # 根据文件模式过滤
            matched_files = [
                f for f in all_files
                if f.is_file() and fnmatch.fnmatch(f.name, self.FILE_PATTERN)
            ]
            
            print(f"[INFO] 找到 {len(matched_files)} 个匹配 '{self.FILE_PATTERN}' 模式的文件")
            logger.info(f"找到 {len(matched_files)} 个匹配 '{self.FILE_PATTERN}' 模式的文件")
            
            # 处理每个文件
            for file_path in matched_files:
                try:
                    # 直接使用源文件路径
                    actual_file_path = file_path
                    
                    # 检查Redis去重（如果可用）
                    redis_key = f"alert:processed_file:{str(actual_file_path)}"
                    if self.redis_client:
                        try:
                            # 尝试获取锁
                            acquired = self.redis_client.set(redis_key, "1", nx=True, ex=3600)
                            if not acquired:
                                print(f"[DEBUG] 文件已处理过（Redis原子锁），跳过: {actual_file_path}")
                                logger.debug(f"文件已处理过（Redis原子锁），跳过: {actual_file_path}")
                                continue
                        except Exception as e:
                            print(f"[WARNING] Redis检查失败，继续处理: {str(e)}")
                            logger.warning(f"Redis检查失败，继续处理: {str(e)}")
                    
                    print(f"[INFO] 处理文件: {actual_file_path}")
                    logger.info(f"处理文件: {actual_file_path}")
                    
                    # 直接创建processor并处理（不依赖handler）
                    processor = self._get_processor()
                    
                    # 使用线程池执行异步任务
                    import concurrent.futures
                    
                    def run_async_task():
                        """在新线程中运行异步任务"""
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(processor.process_alert_file(str(actual_file_path)))
                                print(f"[INFO] 文件处理完成: {actual_file_path}")
                                logger.info(f"文件处理完成: {actual_file_path}")
                            finally:
                                loop.close()
                        except Exception as e:
                            print(f"[ERROR] 异步任务执行失败: {str(e)}")
                            logger.error(f"异步任务执行失败: {str(e)}", exc_info=True)
                            # 处理失败时取消标记，允许重试
                            if self.redis_client:
                                try:
                                    self.redis_client.delete(redis_key)
                                except:
                                    pass
                    
                    # 使用线程池执行
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_async_task)
                        # 等待完成（初始化时可以阻塞）
                        future.result(timeout=60)  # 最多等待60秒
                        
                except Exception as e:
                    print(f"[ERROR] 处理文件失败 {file_path}: {str(e)}")
                    logger.error(f"处理文件失败 {file_path}: {str(e)}", exc_info=True)
        
        except Exception as e:
            print(f"[ERROR] 处理已存在文件失败: {str(e)}")
            logger.error(f"处理已存在文件失败: {str(e)}", exc_info=True)
        
        print(f"[INFO] 已存在文件处理完成")
        logger.info("已存在文件处理完成")


# 全局文件监控服务实例（用于API调用）
_file_watcher_service: Optional[FileWatcherService] = None


def get_file_watcher_service() -> FileWatcherService:
    """获取文件监控服务实例（单例模式）"""
    global _file_watcher_service
    if _file_watcher_service is None:
        _file_watcher_service = FileWatcherService()
    return _file_watcher_service


def reload_file_watcher():
    """重新加载文件监控服务（API调用）"""
    service = get_file_watcher_service()
    service.reload_paths()
