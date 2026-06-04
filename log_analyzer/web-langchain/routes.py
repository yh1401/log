
"""
路由处理模块 - 路径读取和处理相关的路由
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from .models import PathReadRequest
from .path_handler import validate_and_resolve_path, scan_directory_for_logs, read_file_preview, format_bytes
from .auth import get_current_user
from .task_processor import process_files_from_path

logger = logging.getLogger("web.routes")

# ==================== 路由初始化 ====================

router = APIRouter(prefix="/api", tags=["path-processing"])


# ==================== 路由定义 ====================

@router.post("/read-path")
async def read_path(
    request: PathReadRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    从服务器指定路径读取日志文件
    
    功能：
    - 读取指定文件或目录
    - 支持递归扫描子目录
    - 支持文件模式过滤（*.log, *.txt）
    - 提供文件预览功能
    
    安全特性：
    - 路径遍历攻击防护
    - 只允许访问指定目录（白名单）
    - 权限检查
    """
    from .app import PROJECT_ROOT  # 避免循环导入
    
    # 验证路径
    resolved_path, error = validate_and_resolve_path(request.path, PROJECT_ROOT)
    
    if error:
        return JSONResponse({
            "code": 1,
            "message": error,
            "data": None
        }, status_code=400)
    
    # 扫描目录查找日志文件
    files, scan_error = scan_directory_for_logs(
        dir_path=resolved_path,
        recursive=request.recursive,
        patterns=request.file_patterns,
        max_size=request.max_file_size
    )
    
    if scan_error:
        return JSONResponse({
            "code": 1,
            "message": scan_error,
            "data": None
        }, status_code=500)
    
    # 统计信息
    total_size = sum(f['size'] for f in files)
    file_count = len(files)
    
    # 如果是单个文件，提供预览
    preview = None
    if file_count == 1 and not Path(resolved_path).is_dir():
        preview, preview_error = read_file_preview(resolved_path, max_lines=50)
    
    return JSONResponse({
        "code": 0,
        "message": "读取成功",
        "data": {
            "success": True,
            "path": resolved_path,
            "file_count": file_count,
            "total_size": total_size,
            "total_size_str": format_bytes(total_size),
            "files": files if file_count > 0 else None,
            "preview": preview if preview else None,
            "user_id": current_user["user_id"],
            "timestamp": datetime.now().isoformat()
        }
    })


@router.post("/process-from-path")
async def process_from_path_endpoint(
    request: PathReadRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    从服务器指定路径读取日志文件并开始分析
    
    功能：
    - 读取指定路径的日志文件
    - 自动验证和过滤
    - 后台异步处理
    - 生成多格式报告
    
    与 /api/upload + /api/process 的区别：
    - 无需先上传文件到服务器
    - 直接从服务器指定路径读取
    - 适用于已存在于服务器上的日志文件
    """
    from .app import PROJECT_ROOT, TASKS_DIR, processing_tasks  # 避免循环导入
    
    # 验证路径
    resolved_path, error = validate_and_resolve_path(request.path, PROJECT_ROOT)
    
    if error:
        return JSONResponse({
            "code": 1,
            "message": error,
            "data": None
        }, status_code=400)
    
    # 扫描目录查找日志文件
    files, scan_error = scan_directory_for_logs(
        dir_path=resolved_path,
        recursive=request.recursive,
        patterns=request.file_patterns,
        max_size=request.max_file_size
    )
    
    if scan_error:
        return JSONResponse({
            "code": 1,
            "message": scan_error,
            "data": None
        }, status_code=500)
    
    if not files:
        return JSONResponse({
            "code": 1,
            "message": "未找到符合条件的日志文件",
            "data": {
                "path": resolved_path,
                "file_count": 0,
                "suggestion": "请检查路径是否正确，或尝试调整文件过滤模式"
            }
        }, status_code=404)
    
    # 生成任务ID
    task_id = f"path_{current_user['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    # 记录任务信息
    task_info = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "message": "正在准备处理...",
        "file_count": len(files),
        "total_size": sum(f['size'] for f in files),
        "start_time": datetime.now().isoformat(),
        "source": "path",  # 标记为路径读取
        "source_path": resolved_path
    }
    
    # 保存任务信息
    try:
        tasks_file = TASKS_DIR / f"{task_id}.json"
        with open(tasks_file, 'w') as f:
            json.dump(task_info, f, indent=2)
    except Exception as e:
        logger.error(f"[Task {task_id}] 保存任务信息失败: {e}")
    
    # 将文件路径列表添加到任务信息中
    task_info["files"] = [f['path'] for f in files]
    processing_tasks[task_id] = task_info
    
    # 后台任务：开始处理
    background_tasks.add_task(
        process_files_from_path,
        task_id=task_id,
        file_paths=[f['path'] for f in files],
        user_id=current_user["user_id"],
        task_info=task_info
    )
    
    logger.info(f"[Task {task_id}] 路径读取任务已创建，文件数: {len(files)}")
    
    return JSONResponse({
        "code": 0,
        "message": "任务已创建，正在后台处理",
        "data": {
            "task_id": task_id,
            "status": "pending",
            "file_count": len(files),
            "total_size": format_bytes(sum(f['size'] for f in files)),
            "source_path": resolved_path,
            "status_url": f"/api/task/{task_id}"
        }
    })

