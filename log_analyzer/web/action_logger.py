"""用户操作历史记录模块

提供用户操作日志的记录、存储和查询功能。
支持按用户ID、时间范围、操作类型等条件进行筛选查询。
"""

import json
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod
from threading import Lock

import sys
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_analyzer.utils.helpers import ensure_dir


# ==================== 操作类型定义 ====================

ACTION_TYPES = [
    "page_view",        # 页面访问
    "button_click",     # 按钮点击
    "api_request",      # API请求
    "file_upload",      # 文件上传
    "file_download",    # 文件下载
    "report_view",      # 报告查看
    "task_start",       # 任务开始
    "task_complete",    # 任务完成
    "task_failed",      # 任务失败
    "user_login",       # 用户登录
    "user_logout",      # 用户登出
]


# ==================== 存储抽象接口 ====================

class ActionLogStorage(ABC):
    """操作日志存储抽象接口"""

    @abstractmethod
    def record(self, user_id: str, action_type: str, action_name: str, 
               resource: str = "", details: Dict = None, duration_ms: int = 0, 
               status: str = "success") -> str:
        """记录操作日志"""
        pass

    @abstractmethod
    def query(self, user_id: str, start_time: Optional[str] = None, 
              end_time: Optional[str] = None, action_type: Optional[str] = None,
              limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """查询操作日志"""
        pass

    @abstractmethod
    def get(self, user_id: str, action_id: str) -> Optional[Dict]:
        """获取单条操作记录"""
        pass

    @abstractmethod
    def delete(self, user_id: str, action_id: str) -> bool:
        """删除操作记录"""
        pass

    @abstractmethod
    def delete_by_time_range(self, user_id: str, before_time: str) -> int:
        """删除指定时间之前的记录"""
        pass

    @abstractmethod
    def count(self, user_id: str) -> int:
        """统计用户操作记录数"""
        pass


# ==================== 文件存储实现 ====================

class FileActionLogStorage(ActionLogStorage):
    """基于文件系统的操作日志存储
    
    按日期分片存储，提高写入和查询性能：
    - 存储路径: data/action_logs/{user_id}/{date}.json
    - 索引文件: data/action_logs/{user_id}/_index.json
    """

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            self.base_dir = PROJECT_ROOT / "log_analyzer" / "data" / "action_logs"
        else:
            self.base_dir = Path(base_dir)
        ensure_dir(str(self.base_dir))
        self._lock = Lock()

    def _get_user_dir(self, user_id: str) -> Path:
        """获取用户专属目录"""
        user_dir = self.base_dir / user_id
        ensure_dir(str(user_dir))
        return user_dir

    def _get_date_file_path(self, user_id: str, date_str: str) -> Path:
        """获取日期分片文件路径"""
        return self._get_user_dir(user_id) / f"{date_str}.json"

    def _get_index_path(self, user_id: str) -> Path:
        """获取用户索引文件路径"""
        return self._get_user_dir(user_id) / "_index.json"

    def _generate_action_id(self) -> str:
        """生成操作记录ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"act_{timestamp}_{random_part}"

    def _load_date_file(self, user_id: str, date_str: str) -> List[Dict]:
        """加载指定日期的操作日志"""
        file_path = self._get_date_file_path(user_id, date_str)
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_date_file(self, user_id: str, date_str: str, records: List[Dict]):
        """保存指定日期的操作日志"""
        file_path = self._get_date_file_path(user_id, date_str)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def _load_index(self, user_id: str) -> Dict:
        """加载用户索引"""
        index_path = self._get_index_path(user_id)
        if not index_path.exists():
            return {"dates": [], "total_count": 0}
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"dates": [], "total_count": 0}

    def _save_index(self, user_id: str, index: Dict):
        """保存用户索引"""
        index_path = self._get_index_path(user_id)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _get_current_date_str(self) -> str:
        """获取当前日期字符串 YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    def record(self, user_id: str, action_type: str, action_name: str, 
               resource: str = "", details: Dict = None, duration_ms: int = 0, 
               status: str = "success") -> str:
        """记录操作日志"""
        with self._lock:
            action_id = self._generate_action_id()
            date_str = self._get_current_date_str()
            
            record = {
                "action_id": action_id,
                "user_id": user_id,
                "action_type": action_type,
                "action_name": action_name,
                "resource": resource,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
                "duration_ms": duration_ms,
                "status": status
            }

            # 加载并追加到日期文件
            records = self._load_date_file(user_id, date_str)
            records.insert(0, record)  # 最新记录放在前面
            self._save_date_file(user_id, date_str, records)

            # 更新索引
            index = self._load_index(user_id)
            if date_str not in index["dates"]:
                index["dates"].append(date_str)
                index["dates"].sort(reverse=True)  # 按日期降序排列
            index["total_count"] = index.get("total_count", 0) + 1
            self._save_index(user_id, index)

            return action_id

    def query(self, user_id: str, start_time: Optional[str] = None, 
              end_time: Optional[str] = None, action_type: Optional[str] = None,
              limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """查询操作日志"""
        index = self._load_index(user_id)
        all_records = []

        # 遍历所有日期文件
        for date_str in index.get("dates", []):
            records = self._load_date_file(user_id, date_str)
            all_records.extend(records)

        # 按时间筛选
        if start_time:
            all_records = [r for r in all_records if r["timestamp"] >= start_time]
        if end_time:
            all_records = [r for r in all_records if r["timestamp"] <= end_time]

        # 按操作类型筛选
        if action_type:
            all_records = [r for r in all_records if r["action_type"] == action_type]

        # 按时间降序排序
        all_records.sort(key=lambda x: x["timestamp"], reverse=True)

        total_count = len(all_records)
        paginated_records = all_records[offset:offset + limit]

        return paginated_records, total_count

    def get(self, user_id: str, action_id: str) -> Optional[Dict]:
        """获取单条操作记录"""
        index = self._load_index(user_id)
        for date_str in index.get("dates", []):
            records = self._load_date_file(user_id, date_str)
            for record in records:
                if record.get("action_id") == action_id:
                    return record
        return None

    def delete(self, user_id: str, action_id: str) -> bool:
        """删除操作记录"""
        with self._lock:
            index = self._load_index(user_id)
            for date_str in index.get("dates", []):
                records = self._load_date_file(user_id, date_str)
                new_records = [r for r in records if r.get("action_id") != action_id]
                if len(new_records) != len(records):
                    self._save_date_file(user_id, date_str, new_records)
                    index["total_count"] = max(0, index.get("total_count", 0) - 1)
                    self._save_index(user_id, index)
                    return True
        return False

    def delete_by_time_range(self, user_id: str, before_time: str) -> int:
        """删除指定时间之前的记录"""
        with self._lock:
            deleted_count = 0
            index = self._load_index(user_id)
            
            for date_str in list(index.get("dates", [])):
                records = self._load_date_file(user_id, date_str)
                new_records = [r for r in records if r["timestamp"] >= before_time]
                if len(new_records) != len(records):
                    deleted_count += len(records) - len(new_records)
                    if new_records:
                        self._save_date_file(user_id, date_str, new_records)
                    else:
                        # 如果日期文件已空，删除文件并从索引移除
                        self._get_date_file_path(user_id, date_str).unlink(missing_ok=True)
                        index["dates"].remove(date_str)
            
            index["total_count"] = max(0, index.get("total_count", 0) - deleted_count)
            self._save_index(user_id, index)
            
            return deleted_count

    def count(self, user_id: str) -> int:
        """统计用户操作记录数"""
        index = self._load_index(user_id)
        return index.get("total_count", 0)


# ==================== 全局实例 ====================

_action_log_storage: Optional[ActionLogStorage] = None


def get_action_log_storage() -> ActionLogStorage:
    """获取操作日志存储实例（单例）"""
    global _action_log_storage
    if _action_log_storage is None:
        _action_log_storage = FileActionLogStorage()
    return _action_log_storage


# ==================== 便捷记录函数 ====================

def record_action(user_id: str, action_type: str, action_name: str, 
                  resource: str = "", details: Dict = None, 
                  duration_ms: int = 0, status: str = "success") -> str:
    """便捷记录操作日志"""
    storage = get_action_log_storage()
    return storage.record(user_id, action_type, action_name, resource, 
                         details, duration_ms, status)


def record_page_view(user_id: str, page: str):
    """记录页面访问"""
    record_action(user_id, "page_view", f"访问页面: {page}", resource=page)


def record_button_click(user_id: str, button_name: str, page: str = ""):
    """记录按钮点击"""
    record_action(user_id, "button_click", f"点击按钮: {button_name}", 
                 resource=page, details={"button": button_name})


def record_api_request(user_id: str, endpoint: str, method: str = "GET", 
                       status_code: int = 200, duration_ms: int = 0):
    """记录API请求"""
    status = "success" if status_code >= 200 and status_code < 400 else "failed"
    record_action(user_id, "api_request", f"{method} {endpoint}", 
                 resource=endpoint, 
                 details={"method": method, "status_code": status_code},
                 duration_ms=duration_ms, status=status)


def record_file_upload(user_id: str, file_name: str, file_size: int = 0):
    """记录文件上传"""
    record_action(user_id, "file_upload", f"上传文件: {file_name}", 
                 resource=file_name, details={"file_size": file_size})


def record_file_download(user_id: str, file_name: str):
    """记录文件下载"""
    record_action(user_id, "file_download", f"下载文件: {file_name}", 
                 resource=file_name)


def record_task_start(user_id: str, task_id: str, file_name: str):
    """记录任务开始"""
    record_action(user_id, "task_start", f"任务开始: {task_id}", 
                 resource=task_id, details={"file_name": file_name})


def record_task_complete(user_id: str, task_id: str, duration_ms: int = 0):
    """记录任务完成"""
    record_action(user_id, "task_complete", f"任务完成: {task_id}", 
                 resource=task_id, duration_ms=duration_ms)


def record_task_failed(user_id: str, task_id: str, error: str = ""):
    """记录任务失败"""
    record_action(user_id, "task_failed", f"任务失败: {task_id}", 
                 resource=task_id, details={"error": error}, status="failed")
