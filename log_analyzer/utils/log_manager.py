"""日志文件管理器 - 实现日志大小和时间双限制"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

logger = logging.getLogger(__name__)


class LogManager:
    """
    日志文件管理器
    - 限制所有日志文件总大小不超过 MAX_TOTAL_SIZE
    - 保留最近 RETENTION_DAYS 天的日志文件
    - 两者取或的关系，达到任一条件即清理
    """
    
    # 默认配置
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    RETENTION_DAYS = 10  # 保留10天
    
    def __init__(self, log_dir: str, max_total_size: int = None, retention_days: int = None):
        """
        初始化日志管理器
        
        :param log_dir: 日志目录路径
        :param max_total_size: 最大总大小（字节），默认为2GB
        :param retention_days: 保留天数，默认为10天
        """
        self.log_dir = log_dir
        self.max_total_size = max_total_size or self.MAX_TOTAL_SIZE
        self.retention_days = retention_days or self.RETENTION_DAYS
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
    
    def get_log_files(self) -> List[Tuple[str, float, float]]:
        """
        获取所有日志文件列表
        
        :return: 列表，每个元素为 (文件路径, 修改时间戳, 文件大小)
        """
        log_files = []
        try:
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(self.log_dir, filename)
                    if os.path.isfile(filepath):
                        mtime = os.path.getmtime(filepath)
                        size = os.path.getsize(filepath)
                        log_files.append((filepath, mtime, size))
        except Exception as e:
            logger.error(f"获取日志文件列表失败: {str(e)}")
        
        return log_files
    
    def get_total_size(self) -> int:
        """获取所有日志文件的总大小"""
        total_size = 0
        for _, _, size in self.get_log_files():
            total_size += size
        return total_size
    
    def is_over_size_limit(self) -> bool:
        """检查是否超过大小限制"""
        return self.get_total_size() > self.max_total_size
    
    def get_files_over_retention(self) -> List[str]:
        """获取超过保留期限的日志文件"""
        cutoff_time = time.time() - (self.retention_days * 24 * 60 * 60)
        over_files = []
        
        for filepath, mtime, _ in self.get_log_files():
            if mtime < cutoff_time:
                over_files.append(filepath)
        
        return over_files
    
    def clean_old_logs(self) -> Tuple[int, int]:
        """
        清理旧日志文件
        
        清理策略（且关系）：
        - 只有当总大小超过限制 **并且** 文件超过保留期限时，才删除文件
        - 优先删除最旧的过期文件，直到总大小不超过限制
        
        :return: (删除的文件数, 释放的空间字节数)
        """
        deleted_count = 0
        freed_bytes = 0
        
        try:
            # 只有当总大小超过限制时才进行清理
            if not self.is_over_size_limit():
                logger.info(f"日志总大小({self.get_total_size()/1024/1024:.2f}MB)未超过限制({self.max_total_size/1024/1024/1024:.2f}GB)，无需清理")
                return (deleted_count, freed_bytes)
            
            # 获取所有超过保留期限的文件
            expired_files = self.get_files_over_retention()
            if not expired_files:
                logger.info(f"没有超过{self.retention_days}天的日志文件，无需清理")
                return (deleted_count, freed_bytes)
            
            logger.info(f"日志总大小超过限制，开始清理超过{self.retention_days}天的旧日志...")
            
            # 获取过期文件的详细信息并按时间排序（最旧的在前）
            expired_files_info = []
            for filepath in expired_files:
                try:
                    mtime = os.path.getmtime(filepath)
                    size = os.path.getsize(filepath)
                    expired_files_info.append((filepath, mtime, size))
                except Exception as e:
                    logger.error(f"获取文件信息失败 {filepath}: {str(e)}")
            
            # 按修改时间排序，最旧的在前
            expired_files_info.sort(key=lambda x: x[1])
            
            # 循环删除过期文件，直到总大小不超过限制
            for filepath, _, file_size in expired_files_info:
                # 检查是否还需要清理
                if not self.is_over_size_limit():
                    logger.info(f"日志总大小已降至限制以下，停止清理")
                    break
                
                try:
                    os.remove(filepath)
                    freed_bytes += file_size
                    deleted_count += 1
                    logger.info(f"删除日志文件: {filepath} (超过{self.retention_days}天)")
                except Exception as e:
                    logger.error(f"删除日志文件失败 {filepath}: {str(e)}")
            
            logger.info(f"日志清理完成: 删除文件{deleted_count}个, 释放空间{freed_bytes/1024/1024:.2f}MB")
            
        except Exception as e:
            logger.error(f"日志清理失败: {str(e)}")
        
        return (deleted_count, freed_bytes)
    
    def get_log_status(self) -> dict:
        """获取日志状态信息"""
        log_files = self.get_log_files()
        total_size = self.get_total_size()
        over_limit = self.is_over_size_limit()
        expired_files = self.get_files_over_retention()
        
        return {
            'log_dir': self.log_dir,
            'total_files': len(log_files),
            'total_size_bytes': total_size,
            'total_size_human': f"{total_size / 1024 / 1024:.2f} MB",
            'max_size_bytes': self.max_total_size,
            'max_size_human': f"{self.max_total_size / 1024 / 1024 / 1024:.2f} GB",
            'retention_days': self.retention_days,
            'over_size_limit': over_limit,
            'expired_files_count': len(expired_files),
            'expired_files': expired_files
        }


def setup_log_management(log_dir: str = None):
    """
    设置日志管理
    
    :param log_dir: 日志目录，默认为项目根目录下的logs文件夹
    """
    if log_dir is None:
        # 默认使用项目根目录下的logs文件夹
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'logs')
    
    log_manager = LogManager(log_dir)
    
    # 打印当前日志状态
    status = log_manager.get_log_status()
    logger.info(f"日志管理初始化:")
    logger.info(f"  日志目录: {status['log_dir']}")
    logger.info(f"  当前日志文件数: {status['total_files']}")
    logger.info(f"  当前日志总大小: {status['total_size_human']}")
    logger.info(f"  最大限制: {status['max_size_human']}")
    logger.info(f"  保留期限: {status['retention_days']}天")
    
    # 执行清理
    log_manager.clean_old_logs()
    
    return log_manager


if __name__ == "__main__":
    # 测试日志管理功能
    import sys
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    else:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    
    print(f"日志目录: {log_dir}")
    
    manager = LogManager(log_dir)
    status = manager.get_log_status()
    
    print("\n当前日志状态:")
    print(f"  文件数量: {status['total_files']}")
    print(f"  总大小: {status['total_size_human']}")
    print(f"  超过大小限制: {'是' if status['over_size_limit'] else '否'}")
    print(f"  过期文件数: {status['expired_files_count']}")
    
    print("\n执行日志清理...")
    deleted_expired, deleted_over_size, freed_bytes = manager.clean_old_logs()
    
    print(f"\n清理结果:")
    print(f"  删除过期文件: {deleted_expired} 个")
    print(f"  删除超大小文件: {deleted_over_size} 个")
    print(f"  释放空间: {freed_bytes / 1024 / 1024:.2f} MB")
