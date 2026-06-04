"""
FastAPI Web应用 - 日志分析器 (重构版)
按照单一职责原则拆分为多个模块
"""
import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 模块导入
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import log_analyzer.config.settings as config_module
import log_analyzer.parser.log_parser as parser_module
import log_analyzer.checkpoint.manager as checkpoint_module
import log_analyzer.llm.client as llm_module
import log_analyzer.processor.chunk_processor as processor_module
import log_analyzer.report.generator as report_module
import log_analyzer.utils.helpers as utils_module
from log_analyzer.utils.helpers import ensure_dir

# 本地模块导入
from .models import ProcessRequest, ProcessResponse, TaskStatus, IdentifyRequest
from .middleware import ConcurrencyLimitMiddleware
from .auth import user_manager, get_current_user
from .storage import get_storage
from .routes import router as path_router
from .utils import get_user_dir, get_user_upload_dir, get_user_reports_dir, get_user_checkpoints_dir, setup_logging
from .path_handler import format_bytes, validate_and_resolve_path, scan_directory_for_logs, read_file_preview
from .task_processor import process_files_from_path

# 配置和常量
Settings = config_module.Settings
load_llm_config = config_module.load_llm_config
init_settings = config_module.init_settings
LogParser = parser_module.LogParser
CheckpointManager = checkpoint_module.CheckpointManager
LLMClient = llm_module.LLMClient
ChunkProcessor = processor_module.ChunkProcessor
ProcessingResult = processor_module.ProcessingResult
ReportGenerator = report_module.ReportGenerator

# 目录设置
UPLOAD_DIR = PROJECT_ROOT / "log_analyzer" / "uploads"
REPORTS_DIR = PROJECT_ROOT / "log_analyzer" / "reports"
LOGS_DIR = PROJECT_ROOT / "log_analyzer" / "logs"
TASKS_DIR = PROJECT_ROOT / "log_analyzer" / "tasks"
USERS_DIR = PROJECT_ROOT / "log_analyzer" / "users"

# 确保目录存在
ensure_dir(str(UPLOAD_DIR))
ensure_dir(str(REPORTS_DIR))
ensure_dir(str(LOGS_DIR))
ensure_dir(str(TASKS_DIR))
ensure_dir(str(USERS_DIR))

# 应用初始化
app = FastAPI(
    title="Log Analyzer",
    description="Large-scale log file analysis with LLM",
    version="2.2.0"  # 版本更新以反映重构
)

# 日志配置
logger = logging.getLogger("web")
logger.setLevel(logging.INFO)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 并发限流中间件
app.add_middleware(ConcurrencyLimitMiddleware, max_concurrent=200)

# 静态文件挂载
app.mount("/static", StaticFiles(directory=str(SCRIPT_DIR.parent / "static")), name="static")

# 包含路径读取相关路由
app.include_router(path_router)

# 全局任务状态存储
processing_tasks: Dict[str, Dict[str, Any]] = {}

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = ('.log', '.txt', '.zip', '.pcap')


# ==================== 基础路由 ====================

@app.get("/")
async def root():
    """根页面 - 返回前端界面"""
    return FileResponse(str(SCRIPT_DIR.parent / "static" / "index.html"))


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "Log Analyzer API is running"}


# ==================== 认证路由 ====================


@app.post("/api/auth/identify")
async def identify_user(data: IdentifyRequest):
    """用户身份识别接口"""
    user_info = user_manager.get_or_create_user(data.user_id, data.username)
    return JSONResponse({
        "code": 0,
        "message": "识别成功",
        "data": user_info
    })


@app.get("/api/auth/current")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """获取当前请求的用户信息"""
    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": current_user
    })


# ==================== ZIP解压和PCAP处理辅助函数 ====================

def extract_zip(zip_path: Path, dest_dir: Path) -> List[str]:
    """解压ZIP文件并返回提取的文件路径列表"""
    import zipfile
    extracted_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_dir)
            for name in zf.namelist():
                extracted_path = dest_dir / name
                if extracted_path.is_file():
                    extracted_files.append(str(extracted_path))
        logging.info(f"ZIP文件解压完成: {zip_path}, 提取了 {len(extracted_files)} 个文件")
    except Exception as e:
        logging.error(f"解压ZIP文件失败: {str(e)}")
    return extracted_files


# ==================== 上传和处理路由 ====================

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
):
    """上传文件接口（需要认证）"""
    try:
        if not file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
            return JSONResponse({
                "code": 1,
                "message": f"不支持的文件类型: {file.filename}\n支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}",
                "data": None
            }, status_code=400)

        user_upload_dir = get_user_upload_dir(current_user["user_id"])
        file_path = user_upload_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        result_files = []
        if file.filename.lower().endswith('.zip'):
            try:
                extracted_files = extract_zip(file_path, user_upload_dir)
                for extracted in extracted_files:
                    if extracted.lower().endswith(('.log', '.txt')):
                        result_files.append({
                            'path': extracted,
                            'name': Path(extracted).name,
                            'size': format_bytes(os.path.getsize(extracted)) if os.path.exists(extracted) else '0 B'
                        })
            except Exception as e:
                logging.error(f"ZIP解压失败: {str(e)}")

        if not file.filename.lower().endswith('.zip') or len(result_files) == 0:
            result_files.append({
                'path': str(file_path),
                'name': file.filename,
                'size': format_bytes(len(content))
            })

        return JSONResponse({
            "code": 0,
            "message": "上传成功",
            "data": {
                "success": True,
                "file_path": str(file_path),
                "file_name": file.filename,
                "file_size": format_bytes(len(content)),
                "extracted_files": result_files
            }
        })
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.get("/api/list-directory")
async def list_directory(
    path: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """列出目录内容（需要认证，使用用户目录）"""
    if path is None:
        user_upload_dir = get_user_upload_dir(current_user["user_id"])
        if user_upload_dir.exists() and any(user_upload_dir.iterdir()):
            path = str(user_upload_dir)
        else:
            path = str(PROJECT_ROOT)

    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return JSONResponse({
                "code": 1,
                "message": "目录不存在",
                "data": None
            }, status_code=404)

        files = []
        directories = []

        for item in dir_path.iterdir():
            if item.is_file() and item.suffix in ['.log', '.txt', '.zip', '.pcap']:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": stat.st_size,
                    "size_str": format_bytes(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            elif item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(item)
                })

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {
                "current_path": str(dir_path),
                "parent_path": str(dir_path.parent) if dir_path.parent != dir_path else None,
                "directories": sorted(directories, key=lambda x: x["name"]),
                "files": sorted(files, key=lambda x: x["name"])
            }
        })
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


async def process_log_files(
    task_id: str,
    file_paths: List[str],
    chunk_size: int = 50000,
    force_restart: bool = False
):
    """后台处理上传的日志文件"""
    task_info = processing_tasks[task_id]
    task_info["status"] = "processing"
    task_info["progress"] = 0.0
    task_info["message"] = "开始处理日志文件..."

    user_id = task_info.get("user_id", "default")
    user_reports_dir = Path(task_info.get("reports_dir", REPORTS_DIR))
    user_checkpoints_dir = Path(task_info.get("checkpoints_dir", str(PROJECT_ROOT / "log_analyzer" / "checkpoints")))

    ensure_dir(str(user_reports_dir))
    ensure_dir(str(user_checkpoints_dir))

    try:
        log_file, task_logger = setup_logging(task_id, LOGS_DIR, file_paths)
        task_info["log_file"] = log_file

        llm_config = load_llm_config()
        llm_client = LLMClient(config=llm_config, max_retries=3, retry_delay=1.0)
        parser = LogParser(chunk_size=chunk_size)
        checkpoint_manager = CheckpointManager(checkpoint_dir=str(user_checkpoints_dir))
        report_generator = ReportGenerator(output_dir=str(user_reports_dir))
        processor = ChunkProcessor(
            parser=parser,
            llm_client=llm_client,
            checkpoint_manager=checkpoint_manager,
            chunk_size=chunk_size,
            enable_checkpoint=False
        )

        total_files = len(file_paths)
        processed_files = 0
        all_reports = []
        all_results = []

        for idx, file_path in enumerate(file_paths):
            file_name = Path(file_path).name
            task_info["message"] = f"正在处理文件 {idx + 1}/{total_files}: {file_name}"
            task_info["progress"] = idx / total_files * 80

            try:
                task_logger.info(f"[Task {task_id}] 开始处理文件: {file_path}")

                if file_path.lower().endswith('.pcap'):
                    task_logger.info(f"[Task {task_id}] PCAP文件，使用通用处理: {file_path}")

                # 通用处理
                result = await processor.process_file_async(
                    file_path=file_path,
                    resume=True,
                    force_restart=True
                )
                all_results.append(result)
                task_logger.info(f"[Task {task_id}] 文件处理完成，状态: {result.status}")

                if result.status == "completed":
                    report = report_generator.generate_report(result)
                    saved_files = report_generator.save_report(report, format="html+md+pdf+word")
                    task_logger.info(f"[Task {task_id}] 报告已保存: {saved_files}")
                    for saved_file in saved_files:
                        file_type = "html" if saved_file.endswith(".html") else \
                                     "pdf" if saved_file.endswith(".pdf") else \
                                     "word" if saved_file.endswith(".docx") else \
                                     "markdown" if saved_file.endswith(".md") else "json"
                        all_reports.append({
                            "name": Path(saved_file).name,
                            "path": saved_file,
                            "type": file_type
                        })
                    processed_files += 1

            except Exception as e:
                import traceback
                task_logger.error(f"[Task {task_id}] 处理文件失败: {file_path}")
                task_logger.error(traceback.format_exc())
                task_info["message"] = f"处理文件失败: {str(e)}"
                continue

        # 生成综合报告
        if len(all_results) > 1:
            task_info["message"] = "正在生成综合报告..."
            task_info["progress"] = 95.0
            try:
                combined_report = report_generator.generate_combined_report(all_results)
                combined_files = report_generator.save_report(combined_report, format="html+md+pdf+word", prefix="combined")
                task_logger.info(f"[Task {task_id}] 综合报告已保存: {combined_files}")
                for saved_file in combined_files:
                    file_type = "html" if saved_file.endswith(".html") else \
                                 "pdf" if saved_file.endswith(".pdf") else \
                                 "word" if saved_file.endswith(".docx") else \
                                 "markdown" if saved_file.endswith(".md") else "json"
                    all_reports.append({
                        "name": Path(saved_file).name,
                        "path": saved_file,
                        "type": file_type
                    })
            except Exception as e:
                task_logger.error(f"[Task {task_id}] 生成综合报告失败: {e}")

        # 更新最终状态
        task_info["status"] = "completed"
        task_info["progress"] = 100.0
        task_info["message"] = f"处理完成！成功处理 {processed_files}/{len(file_paths)} 个文件"
        task_info["reports"] = all_reports
        task_info["end_time"] = datetime.now().isoformat()

        # 保存历史记录
        if all_results and user_id:
            try:
                storage = get_storage()
                stats_summary = {
                    "total_files": len(file_paths),
                    "processed_files": processed_files,
                    "total_chunks": sum(len(r.chunks) if hasattr(r, 'chunks') else 0 for r in all_results)
                }
                for result in all_results:
                    file_name = Path(result.file_path).name if hasattr(result, 'file_path') else "unknown"
                    history_record = {
                        "title": f"日志分析报告 - {file_name}",
                        "file_name": file_name,
                        "file_type": Path(file_name).suffix.lstrip('.') or "log",
                        "summary": result.summary if hasattr(result, 'summary') else "",
                        "statistics": stats_summary,
                        "analysis": result.to_dict() if hasattr(result, 'to_dict') else {},
                        "files": [r for r in all_reports if Path(r.get("path", "")).name.startswith(file_name.rsplit('.', 1)[0])],
                        "tags": ["auto-generated"],
                        "metadata": {
                            "task_id": task_id
                        }
                    }
                    storage.create(user_id, history_record)
                task_logger.info(f"[Task {task_id}] 已持久化 {len(all_results)} 条历史报告")
            except Exception as e:
                task_logger.error(f"[Task {task_id}] 持久化历史报告失败: {e}")

        with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
            json.dump(task_info, f, indent=2)

        task_logger.info(f"[Task {task_id}] 任务完成！成功处理 {processed_files}/{len(file_paths)} 个文件")

    except Exception as e:
        import traceback
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["message"] = f"任务失败: {str(e)}"
        with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
            json.dump(task_info, f, indent=2)
        logging.error(f"处理任务 {task_id} 失败: {str(e)}")
        logging.error(traceback.format_exc())


@app.post("/api/process")
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """开始处理日志文件（需要认证）"""
    task_id = f"{current_user['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    file_paths = []

    if request.file_path:
        if not Path(request.file_path).exists():
            return JSONResponse({
                "code": 1,
                "message": "文件不存在",
                "data": None
            }, status_code=404)
        file_paths.append(request.file_path)
    elif request.directory_path:
        dir_path = Path(request.directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return JSONResponse({
                "code": 1,
                "message": "目录不存在",
                "data": None
            }, status_code=404)

        for file in dir_path.iterdir():
            if file.is_file() and (file.suffix in ['.log', '.txt', '.pcap'] or 'error' in file.name.lower()):
                file_paths.append(str(file))

    if not file_paths:
        return JSONResponse({
            "code": 1,
            "message": "未找到可处理的日志文件",
            "data": None
        }, status_code=400)

    user_reports_dir = get_user_reports_dir(current_user["user_id"])
    user_checkpoints_dir = get_user_checkpoints_dir(current_user["user_id"])

    processing_tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "任务已创建，等待开始...",
        "file_paths": file_paths,
        "reports": None,
        "error": None,
        "user_id": current_user["user_id"],
        "reports_dir": str(user_reports_dir),
        "checkpoints_dir": str(user_checkpoints_dir)
    }

    background_tasks.add_task(
        process_log_files,
        task_id,
        file_paths,
        request.chunk_size,
        request.force_restart
    )

    return JSONResponse({
        "code": 0,
        "message": f"任务已创建，正在处理 {len(file_paths)} 个文件",
        "data": {
            "task_id": task_id,
            "status": "pending"
        }
    })


# ==================== 任务状态和下载路由 ====================

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str, current_user: Dict = Depends(get_current_user)):
    """查询任务状态"""
    task_info = None

    # 首先在内存中查找
    if task_id in processing_tasks:
        task_info = processing_tasks[task_id]
    else:
        # 尝试从文件加载
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            try:
                with open(task_file, 'r') as f:
                    task_info = json.load(f)
            except Exception:
                pass

    if not task_info:
        return JSONResponse({
            "code": 1,
            "message": "任务不存在",
            "data": None
        }, status_code=404)

    # 检查用户权限
    if task_info.get("user_id") != current_user["user_id"]:
        return JSONResponse({
            "code": 1,
            "message": "无权访问此任务",
            "data": None
        }, status_code=403)

    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": task_info
    })


@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str, current_user: Dict = Depends(get_current_user)):
    """下载文件（需要 X-User-Id 头，仅能下载用户自己的文件）"""
    try:
        path = Path(file_path)
        if not path.exists():
            return JSONResponse({
                "code": 1,
                "message": "文件不存在",
                "data": None
            }, status_code=404)

        user_reports_dir = get_user_reports_dir(current_user["user_id"])
        user_upload_dir = get_user_upload_dir(current_user["user_id"])

        if not (str(path).startswith(str(user_reports_dir)) or str(path).startswith(str(user_upload_dir))):
            return JSONResponse({
                "code": 1,
                "message": "无权访问此文件",
                "data": None
            }, status_code=403)

        return FileResponse(
            path=str(path),
            filename=path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


# ==================== 历史记录路由 ====================

@app.get("/api/history")
async def get_history(
    page: int = 1,
    page_size: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """获取用户历史记录（需要认证）"""
    storage = get_storage()
    records = storage.list(current_user["user_id"], page=page, page_size=page_size)
    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": {
            "records": records,
            "page": page,
            "page_size": page_size
        }
    })


@app.get("/api/history/{record_id}")
async def get_history_record(record_id: str, current_user: Dict = Depends(get_current_user)):
    """获取单条历史记录详情（需要认证）"""
    storage = get_storage()
    record = storage.get(current_user["user_id"], record_id)
    if not record:
        return JSONResponse({
            "code": 1,
            "message": "记录不存在",
            "data": None
        }, status_code=404)

    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": record
    })


@app.delete("/api/history/{record_id}")
async def delete_history_record(record_id: str, current_user: Dict = Depends(get_current_user)):
    """删除历史记录（需要认证）"""
    storage = get_storage()
    storage.delete(current_user["user_id"], record_id)
    return JSONResponse({
        "code": 0,
        "message": "删除成功",
        "data": None
    })
