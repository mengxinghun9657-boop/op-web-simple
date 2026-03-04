"""
长安告警文件名修正服务
修正文件名中的cluster_id，通过宿主机数据库查询正确的集群ID
"""
import os
import re
import pymysql
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.core.config_alert import settings


class FilenameCorrectorService:
    """文件名修正服务"""
    
    def __init__(self):
        """初始化服务"""
        # 宿主机数据库配置（用于查询正确的cluster_id）
        # 注意：容器内访问宿主机需要使用宿主机IP，不能用127.0.0.1
        # 从环境变量获取宿主机IP，默认使用host.docker.internal（Mac/Windows）
        host_ip = os.getenv("HOST_MYSQL_IP", "host.docker.internal")
        
        self.host_db_config = {
            "host": host_ip,  # 宿主机IP或host.docker.internal
            "user": "root",
            "password": "DF210354ws!",
            "database": "mydb",
            "charset": "utf8mb4",
            "port": 8306  # 宿主机MySQL端口
        }
        
        # 缓存查询结果，避免重复查询
        self._cluster_cache: Dict[str, str] = {}
    
    def _get_host_db_connection(self):
        """获取宿主机数据库连接"""
        try:
            return pymysql.connect(**self.host_db_config)
        except Exception as e:
            logger.error(f"连接宿主机数据库失败: {e}")
            return None
    
    def _query_correct_cluster_id(self, ip: str) -> Optional[str]:
        """
        通过IP查询正确的cluster_id
        
        Args:
            ip: 节点IP地址
            
        Returns:
            正确的cluster_id，如果查询失败返回None
        """
        # 检查缓存
        if ip in self._cluster_cache:
            return self._cluster_cache[ip]
        
        conn = self._get_host_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            # 查询bce_cce_nodes表，通过节点名称（IP）获取cluster_id
            cursor.execute(
                "SELECT cluster_id FROM bce_cce_nodes WHERE `节点名称`=%s LIMIT 1",
                (ip,)
            )
            result = cursor.fetchone()
            
            if result:
                correct_cluster_id = str(result[0])
                # 去掉数据库里多余的 cce- 前缀
                if correct_cluster_id.startswith("cce-"):
                    correct_cluster_id = correct_cluster_id[4:]
                
                # 缓存结果
                self._cluster_cache[ip] = correct_cluster_id
                logger.debug(f"查询到正确的cluster_id: IP={ip} -> cluster_id={correct_cluster_id}")
                return correct_cluster_id
            else:
                logger.warning(f"未找到IP对应的cluster_id: {ip}")
                return None
                
        except Exception as e:
            logger.error(f"查询cluster_id失败: IP={ip}, 错误={e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def should_correct_filename(self, filename: str) -> bool:
        """
        判断文件名是否需要修正
        
        Args:
            filename: 文件名
            
        Returns:
            是否需要修正
        """
        return filename.startswith("长安-")
    
    def extract_ip_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取IP地址
        
        Args:
            filename: 文件名
            
        Returns:
            IP地址，如果提取失败返回None
        """
        match = re.search(r'(\d+\.\d+\.\d+\.\d+)\.txt$', filename)
        if match:
            return match.group(1)
        return None
    
    def generate_corrected_filename(self, original_filename: str, correct_cluster_id: str) -> Optional[str]:
        """
        生成修正后的文件名
        
        Args:
            original_filename: 原始文件名
            correct_cluster_id: 正确的cluster_id
            
        Returns:
            修正后的文件名，如果无法修正返回None
        """
        try:
            parts = original_filename.split("-")
            
            # 查找cce部分的位置
            if "cce" not in parts:
                logger.warning(f"文件名中未找到cce部分: {original_filename}")
                return None
            
            cce_index = parts.index("cce")
            if cce_index + 1 >= len(parts):
                logger.warning(f"文件名格式异常，cce后无cluster_id: {original_filename}")
                return None
            
            # 获取当前的cluster_id
            old_cluster_id = parts[cce_index + 1]
            
            # 如果cluster_id已经正确，不需要修正
            if old_cluster_id == correct_cluster_id:
                logger.debug(f"文件名cluster_id已正确，无需修正: {original_filename}")
                return None
            
            # 替换cluster_id
            parts[cce_index + 1] = correct_cluster_id
            new_filename = "-".join(parts)
            
            logger.info(f"生成修正文件名: {original_filename} -> {new_filename}")
            return new_filename
            
        except Exception as e:
            logger.error(f"生成修正文件名失败: {original_filename}, 错误={e}")
            return None
    
    def correct_filename_if_needed(self, file_path: str, dry_run: bool = False) -> Optional[str]:
        """
        如果需要，修正文件名
        
        Args:
            file_path: 文件完整路径
            dry_run: 是否为试运行模式（不实际重命名）
            
        Returns:
            修正后的文件路径，如果不需要修正或修正失败返回None
        """
        try:
            path_obj = Path(file_path)
            filename = path_obj.name
            directory = path_obj.parent
            
            # 检查是否需要修正
            if not self.should_correct_filename(filename):
                return None
            
            # 提取IP地址
            ip = self.extract_ip_from_filename(filename)
            if not ip:
                logger.warning(f"无法从文件名提取IP地址: {filename}")
                return None
            
            # 查询正确的cluster_id
            correct_cluster_id = self._query_correct_cluster_id(ip)
            if not correct_cluster_id:
                logger.warning(f"无法查询到正确的cluster_id: IP={ip}")
                return None
            
            # 生成修正后的文件名
            new_filename = self.generate_corrected_filename(filename, correct_cluster_id)
            if not new_filename:
                return None
            
            # 构建新的文件路径
            new_file_path = directory / new_filename
            
            # 检查目标文件是否已存在
            if new_file_path.exists():
                logger.warning(f"目标文件已存在，跳过修正: {new_filename}")
                return None
            
            if dry_run:
                logger.info(f"[DRY RUN] 将修正文件名: {filename} -> {new_filename}")
                return str(new_file_path)
            
            # 执行重命名（如果是只读文件系统，则复制到可写的临时目录）
            try:
                os.rename(file_path, new_file_path)
                logger.info(f"✅ 文件名修正成功: {filename} -> {new_filename}")
                return str(new_file_path)
            except OSError as e:
                # 只读文件系统错误（Errno 30），复制到可写的临时目录
                if e.errno == 30:  # Read-only file system
                    logger.info(f"⚠️  源目录为只读，复制文件到临时目录: {filename} -> {new_filename}")
                    try:
                        import shutil
                        import tempfile
                        
                        # 创建临时目录（在 /app/data/alerts_corrected/ 下）
                        temp_dir = Path("/app/data/alerts_corrected")
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 目标文件路径（使用正确的文件名）
                        corrected_file_path = temp_dir / new_filename
                        
                        # 检查目标文件是否已存在
                        if corrected_file_path.exists():
                            logger.warning(f"临时目录中目标文件已存在，跳过: {new_filename}")
                            return str(corrected_file_path)
                        
                        # 复制文件到临时目录
                        shutil.copy2(file_path, corrected_file_path)
                        logger.info(f"✅ 文件复制成功（只读文件系统）: {filename} -> {corrected_file_path}")
                        return str(corrected_file_path)
                    except Exception as copy_error:
                        logger.error(f"❌ 文件复制失败: {filename} -> {new_filename}, 错误={copy_error}")
                        return None
                else:
                    logger.error(f"❌ 文件重命名失败: {filename} -> {new_filename}, 错误={e}")
                    return None
            except Exception as e:
                logger.error(f"❌ 文件重命名失败: {filename} -> {new_filename}, 错误={e}")
                return None
                
        except Exception as e:
            logger.error(f"修正文件名过程异常: {file_path}, 错误={e}")
            return None
    
    def batch_correct_directory(self, directory_path: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        批量修正目录中的文件名
        
        Args:
            directory_path: 目录路径
            dry_run: 是否为试运行模式
            
        Returns:
            修正结果统计
        """
        stats = {
            "total_files": 0,
            "need_correction": 0,
            "corrected": 0,
            "failed": 0,
            "skipped": 0
        }
        
        try:
            directory = Path(directory_path)
            if not directory.exists():
                logger.error(f"目录不存在: {directory_path}")
                return stats
            
            # 扫描所有txt文件
            for file_path in directory.glob("*.txt"):
                stats["total_files"] += 1
                filename = file_path.name
                
                # 检查是否需要修正
                if not self.should_correct_filename(filename):
                    continue
                
                stats["need_correction"] += 1
                
                # 尝试修正
                result = self.correct_filename_if_needed(str(file_path), dry_run)
                if result:
                    stats["corrected"] += 1
                elif result is None:
                    # 可能是已存在或其他原因跳过
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1
            
            logger.info(f"批量修正完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"批量修正异常: {directory_path}, 错误={e}")
            return stats


# 全局实例
_filename_corrector: Optional[FilenameCorrectorService] = None


def get_filename_corrector() -> FilenameCorrectorService:
    """获取文件名修正服务实例（单例模式）"""
    global _filename_corrector
    if _filename_corrector is None:
        _filename_corrector = FilenameCorrectorService()
    return _filename_corrector