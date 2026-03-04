"""
告警文件同步服务
从只读源目录复制文件到可写处理目录，支持文件名修正
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Set
from loguru import logger

from app.services.alert.filename_corrector import FilenameCorrectorService


class FileSyncService:
    """文件同步服务：从源目录复制到处理目录"""
    
    def __init__(self, source_dir: str = "/app/alerts_source", target_dir: str = "/app/alerts"):
        """
        初始化文件同步服务
        
        Args:
            source_dir: 源目录（只读，宿主机挂载）
            target_dir: 目标目录（读写，Docker卷）
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.corrector = FilenameCorrectorService()
        
        # 确保目标目录存在
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # 已同步文件缓存（避免重复复制）
        self._synced_files: Set[str] = set()
        
        logger.info(f"文件同步服务初始化: {source_dir} -> {target_dir}")
    
    def sync_file(self, source_file_path: str) -> Optional[str]:
        """
        同步单个文件（复制+文件名修正）
        
        Args:
            source_file_path: 源文件路径
            
        Returns:
            目标文件路径，如果同步失败返回None
        """
        try:
            source_path = Path(source_file_path)
            
            # 检查源文件是否存在
            if not source_path.exists():
                logger.warning(f"源文件不存在: {source_file_path}")
                return None
            
            # 检查是否已同步过
            if source_file_path in self._synced_files:
                logger.debug(f"文件已同步过，跳过: {source_file_path}")
                return None
            
            # 获取文件名
            filename = source_path.name
            
            # 步骤1: 检查是否需要修正文件名
            if self.corrector.should_correct_filename(filename):
                # 提取IP地址
                ip = self.corrector.extract_ip_from_filename(filename)
                if ip:
                    # 查询正确的cluster_id
                    correct_cluster_id = self.corrector._query_correct_cluster_id(ip)
                    if correct_cluster_id:
                        # 生成修正后的文件名
                        new_filename = self.corrector.generate_corrected_filename(filename, correct_cluster_id)
                        if new_filename:
                            logger.info(f"文件名需要修正: {filename} -> {new_filename}")
                            filename = new_filename
            
            # 步骤2: 构建目标文件路径
            target_path = self.target_dir / filename
            
            # 检查目标文件是否已存在
            if target_path.exists():
                logger.debug(f"目标文件已存在，跳过: {target_path}")
                self._synced_files.add(source_file_path)
                return str(target_path)
            
            # 步骤3: 复制文件
            shutil.copy2(source_path, target_path)
            logger.info(f"✅ 文件同步成功: {source_path.name} -> {target_path.name}")
            
            # 标记为已同步
            self._synced_files.add(source_file_path)
            
            return str(target_path)
            
        except Exception as e:
            logger.error(f"文件同步失败: {source_file_path}, 错误={e}")
            return None
    
    def sync_directory(self, pattern: str = "*.txt") -> int:
        """
        同步整个目录（批量）
        
        Args:
            pattern: 文件模式（如 *.txt）
            
        Returns:
            成功同步的文件数量
        """
        synced_count = 0
        
        try:
            # 扫描源目录
            for source_file in self.source_dir.glob(pattern):
                if source_file.is_file():
                    result = self.sync_file(str(source_file))
                    if result:
                        synced_count += 1
            
            logger.info(f"目录同步完成: 成功同步 {synced_count} 个文件")
            return synced_count
            
        except Exception as e:
            logger.error(f"目录同步失败: {e}")
            return synced_count
    
    def cleanup_old_files(self, days: int = 7):
        """
        清理旧文件（保留最近N天）
        
        Args:
            days: 保留天数
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            deleted_count = 0
            for file_path in self.target_dir.glob("*.txt"):
                if file_path.is_file():
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"删除旧文件: {file_path.name}")
            
            if deleted_count > 0:
                logger.info(f"清理完成: 删除 {deleted_count} 个旧文件（超过{days}天）")
                
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")


# 全局单例
_file_sync_service: Optional[FileSyncService] = None


def get_file_sync_service() -> FileSyncService:
    """获取文件同步服务单例"""
    global _file_sync_service
    if _file_sync_service is None:
        _file_sync_service = FileSyncService()
    return _file_sync_service
