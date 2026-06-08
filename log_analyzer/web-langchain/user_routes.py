"""
用户相关API路由
"""
import logging
from datetime import datetime
from pathlib import Path
import json
from fastapi import APIRouter, Depends
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["用户"])

# 用户操作日志存储目录
USER_LOGS_DIR = Path(__file__).parent.parent / "users"


def get_user_logs_dir(user_id: str) -> Path:
    """获取用户操作日志目录"""
    user_dir = USER_LOGS_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "operation_logs.json"


def load_operation_logs(user_id: str) -> list:
    """加载用户操作日志"""
    log_file = get_user_logs_dir(user_id)
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户操作日志失败: {e}")
            return []
    return []


def save_operation_logs(user_id: str, logs: list):
    """保存用户操作日志"""
    log_file = get_user_logs_dir(user_id)
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存用户操作日志失败: {e}")


def add_operation_log(user_id: str, action: str, details: dict = None):
    """添加操作日志"""
    logs = load_operation_logs(user_id)
    new_log = {
        "id": len(logs) + 1,
        "action": action,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    logs.insert(0, new_log)
    # 只保留最近100条
    logs = logs[:100]
    save_operation_logs(user_id, logs)
    return new_log


@router.get("/info")
async def get_user_info(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        user_id = user.get("user_id", "")
        username = user.get("username", "")
        created_at = user.get("created_at", "")

        # 记录查看用户信息操作
        add_operation_log(user_id, "view_profile", {"username": username})

        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "user_id": user_id,
                "username": username,
                "created_at": created_at
            }
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}", exc_info=True)
        return {
            "code": -1,
            "message": f"获取用户信息失败: {str(e)}",
            "data": None
        }


@router.get("/operations")
async def get_user_operations(
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """获取用户操作日志"""
    try:
        user_id = user.get("user_id", "")
        logs = load_operation_logs(user_id)

        # 限制返回数量
        logs = logs[:limit]

        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "total": len(logs),
                "logs": logs
            }
        }
    except Exception as e:
        logger.error(f"获取用户操作日志失败: {e}", exc_info=True)
        return {
            "code": -1,
            "message": f"获取用户操作日志失败: {str(e)}",
            "data": None
        }


@router.post("/operations")
async def log_user_operation(
    action: str,
    details: dict = None,
    user: dict = Depends(get_current_user)
):
    """记录用户操作"""
    try:
        user_id = user.get("user_id", "")
        new_log = add_operation_log(user_id, action, details)

        return {
            "code": 0,
            "message": "记录成功",
            "data": new_log
        }
    except Exception as e:
        logger.error(f"记录用户操作失败: {e}", exc_info=True)
        return {
            "code": -1,
            "message": f"记录用户操作失败: {str(e)}",
            "data": None
        }
