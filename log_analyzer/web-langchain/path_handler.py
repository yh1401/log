
"""
路径处理模块 - 路径验证、目录扫描、文件预览等功能
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

# ==================== 配置常量 ====================

ALLOWED_READ_PATHS = [
    "/var/log",           # 系统日志
    "/tmp",               # 临时文件
    "/home",              # 用户目录
    "/Users",             # macOS用户目录
]


# ==================== 工具函数 ====================

def format_bytes(size: int) -> str:
    """格式化字节大小为人类可读的格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


# ==================== 安全验证 ====================

def validate_and_resolve_path(requested_path: str, project_root: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    验证并解析路径，防止路径遍历攻击和越权访问
    
    Args:
        requested_path: 用户请求的路径
        project_root: 项目根目录
        
    Returns:
        tuple: (resolved_path, error_message)
        - 成功：返回绝对路径，error为None
        - 失败：path为None，error包含错误信息
    """
    if not requested_path:
        return None, "路径不能为空"
    
    try:
        # 解析路径，去除多余的斜杠和相对路径
        requested_path = requested_path.strip()
        resolved_path = Path(requested_path).resolve()
        
        # 路径遍历检查
        if '..' in requested_path:
            return None, "禁止使用 '..' 进行路径遍历"
        
        # 检查是否为绝对路径
        if not resolved_path.is_absolute():
            return None, "只支持绝对路径"
        
        # 检查路径是否存在
        if not resolved_path.exists():
            return None, f"路径不存在: {requested_path}"
        
        # 安全检查：确保路径在允许的目录内或项目目录内
        is_allowed = False
        
        # 检查是否在项目目录内（始终允许读取项目自身文件）
        try:
            project_resolved = project_root.resolve()
            if resolved_path.is_relative_to(project_resolved):
                is_allowed = True
        except (ValueError, OSError):
            pass
        
        # 检查是否在允许的系统目录内
        if not is_allowed:
            for allowed_base in ALLOWED_READ_PATHS:
                try:
                    if str(resolved_path).startswith(allowed_base):
                        is_allowed = True
                        break
                except (ValueError, OSError):
                    continue
        
        if not is_allowed:
            return None, f"路径不在允许的读取范围内。允许的目录: {', '.join(ALLOWED_READ_PATHS + [str(project_root)])}"
        
        # 检查读权限
        if not os.access(resolved_path, os.R_OK):
            return None, f"无读取权限: {requested_path}"
        
        return str(resolved_path), None
        
    except Exception as e:
        return None, f"路径验证失败: {str(e)}"


# ==================== 目录扫描 ====================

def scan_directory_for_logs(dir_path: str, recursive: bool = False, 
                           patterns: Optional[List[str]] = None,
                           max_size: int = 100 * 1024 * 1024) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    扫描目录查找日志文件
    
    Args:
        dir_path: 目录路径
        recursive: 是否递归扫描子目录
        patterns: 文件匹配模式列表
        max_size: 最大文件大小限制
        
    Returns:
        tuple: (files_list, error_message)
    """
    if patterns is None:
        patterns = ['*.log', '*.txt']
    
    log_files = []
    
    try:
        scan_path = Path(dir_path)
        
        # 如果是文件，直接返回
        if scan_path.is_file():
            if any(scan_path.match(pattern) for pattern in patterns):
                stat = scan_path.stat()
                if stat.st_size <= max_size:
                    log_files.append({
                        "name": scan_path.name,
                        "path": str(scan_path),
                        "size": stat.st_size,
                        "size_str": format_bytes(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": "file"
                    })
            return log_files, None
        
        # 目录扫描
        if recursive:
            # 递归扫描
            for pattern in patterns:
                for file_path in scan_path.rglob(pattern):
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            if stat.st_size <= max_size:
                                log_files.append({
                                    "name": file_path.name,
                                    "path": str(file_path),
                                    "size": stat.st_size,
                                    "size_str": format_bytes(stat.st_size),
                                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "type": "file",
                                    "relative_path": str(file_path.relative_to(scan_path))
                                })
                        except (OSError, PermissionError):
                            continue
        else:
            # 非递归扫描
            for pattern in patterns:
                for file_path in scan_path.glob(pattern):
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            if stat.st_size <= max_size:
                                log_files.append({
                                    "name": file_path.name,
                                    "path": str(file_path),
                                    "size": stat.st_size,
                                    "size_str": format_bytes(stat.st_size),
                                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "type": "file"
                                })
                        except (OSError, PermissionError):
                            continue
        
        # 按修改时间排序，最新的在前
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return log_files, None
        
    except Exception as e:
        return [], f"扫描目录失败: {str(e)}"


# ==================== 文件预览 ====================

def read_file_preview(file_path: str, max_lines: int = 100) -> Tuple[Optional[str], Optional[str]]:
    """
    读取文件预览内容
    
    Args:
        file_path: 文件路径
        max_lines: 最大预览行数
        
    Returns:
        tuple: (preview_content, error_message)
    """
    try:
        preview_lines = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                preview_lines.append(line.rstrip('\n\r'))
        
        return '\n'.join(preview_lines), None
        
    except Exception as e:
        return None, f"读取文件失败: {str(e)}"

