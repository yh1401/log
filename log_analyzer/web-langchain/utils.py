
"""
工具函数模块 - 用户目录、日志设置等辅助功能
"""
import logging
from pathlib import Path
from typing import Tuple, List, Optional
from datetime import datetime
from log_analyzer.utils.helpers import ensure_dir


def get_user_dir(user_id: str, users_dir: Path) -> Path:
    """
    获取用户专属目录
    
    Args:
        user_id: 用户ID
        users_dir: 用户根目录
        
    Returns:
        用户目录Path对象
    """
    user_dir = users_dir / user_id
    ensure_dir(str(user_dir))
    return user_dir


def get_user_upload_dir(user_id: str, users_dir: Path) -> Path:
    """
    获取用户上传文件目录
    
    Args:
        user_id: 用户ID
        users_dir: 用户根目录
        
    Returns:
        上传目录Path对象
    """
    upload_dir = get_user_dir(user_id, users_dir) / "uploads"
    ensure_dir(str(upload_dir))
    return upload_dir


def get_user_reports_dir(user_id: str, users_dir: Path) -> Path:
    """
    获取用户报告目录
    
    Args:
        user_id: 用户ID
        users_dir: 用户根目录
        
    Returns:
        报告目录Path对象
    """
    reports_dir = get_user_dir(user_id, users_dir) / "reports"
    ensure_dir(str(reports_dir))
    return reports_dir


def get_user_checkpoints_dir(user_id: str, users_dir: Path) -> Path:
    """
    获取用户检查点目录
    
    Args:
        user_id: 用户ID
        users_dir: 用户根目录
        
    Returns:
        检查点目录Path对象
    """
    checkpoint_dir = get_user_dir(user_id, users_dir) / "checkpoints"
    ensure_dir(str(checkpoint_dir))
    return checkpoint_dir


def setup_logging(task_id: str, logs_dir: Path, file_paths: Optional[List[str]] = None) -> Tuple[str, logging.Logger]:
    """
    设置任务日志
    
    Args:
        task_id: 任务ID
        logs_dir: 日志目录
        file_paths: 处理的文件路径列表（用于生成日志文件名）
        
    Returns:
        (日志文件路径, 任务logger)
    """
    ensure_dir(str(logs_dir))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if file_paths:
        file_names = [Path(fp).stem for fp in file_paths[:3]]
        if len(file_names) == 1:
            file_label = file_names[0]
        else:
            file_label = f"{file_names[0]}_等{len(file_paths)}个文件"
        log_file = logs_dir / f'web_process_{timestamp}_{file_label}.log'
    else:
        log_file = logs_dir / f'web_process_{timestamp}_{task_id[:8]}.log'

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建任务专用logger
    task_logger = logging.getLogger(f'web_{task_id}')
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = True  # 允许传播到根logger

    for handler in task_logger.handlers[:]:
        task_logger.removeHandler(handler)

    # 获取根logger并添加文件handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除现有的文件handler（如果有）
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)

    # 添加新的文件handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 确保控制台输出（如果需要）
    has_console_handler = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return str(log_file), task_logger

