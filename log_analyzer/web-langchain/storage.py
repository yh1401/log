"""数据存储抽象层

提供本地文件存储实现，预留数据库迁移接口。
所有业务数据都通过此模块访问，便于后续切换到数据库。
"""

import os
import json
import shutil
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Protocol
from abc import ABC, abstractmethod
from threading import Lock

import sys
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_analyzer.utils.helpers import ensure_dir


# ==================== 存储抽象接口 ====================

class ReportStorage(ABC):
    """报告存储抽象接口（预留数据库迁移）"""

    @abstractmethod
    def create(self, user_id: str, report_data: Dict) -> str:
        """创建报告，返回报告ID"""
        pass

    @abstractmethod
    def get(self, user_id: str, report_id: str) -> Optional[Dict]:
        """获取单个报告"""
        pass

    @abstractmethod
    def list(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出用户的所有报告"""
        pass

    @abstractmethod
    def update(self, user_id: str, report_id: str, data: Dict) -> bool:
        """更新报告"""
        pass

    @abstractmethod
    def delete(self, user_id: str, report_id: str) -> bool:
        """删除报告"""
        pass

    @abstractmethod
    def search(self, user_id: str, keyword: str = "", limit: int = 100) -> List[Dict]:
        """搜索报告"""
        pass


# ==================== 文件存储实现 ====================

class FileReportStorage(ReportStorage):
    """基于本地文件系统的报告存储"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            self.base_dir = PROJECT_ROOT / "log_analyzer" / "data" / "reports_db"
        else:
            self.base_dir = Path(base_dir)

        ensure_dir(str(self.base_dir))
        self._lock = Lock()

    def _get_user_dir(self, user_id: str) -> Path:
        """获取用户专属目录"""
        user_dir = self.base_dir / user_id
        ensure_dir(str(user_dir))
        return user_dir

    def _get_report_path(self, user_id: str, report_id: str) -> Path:
        """获取报告文件路径"""
        return self._get_user_dir(user_id) / f"{report_id}.json"

    def _get_index_path(self, user_id: str) -> Path:
        """获取用户索引文件路径"""
        return self._get_user_dir(user_id) / "_index.json"

    def _load_index(self, user_id: str) -> Dict:
        """加载用户报告索引"""
        index_path = self._get_index_path(user_id)
        if not index_path.exists():
            return {"reports": []}
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"reports": []}

    def _save_index(self, user_id: str, index: Dict):
        """保存用户报告索引"""
        index_path = self._get_index_path(user_id)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _generate_report_id(self) -> str:
        """生成报告ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"rpt_{timestamp}_{random_part}"

    def _hash_sensitive_data(self, data: str) -> str:
        """敏感数据哈希"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def create(self, user_id: str, report_data: Dict) -> str:
        """创建报告"""
        with self._lock:
            report_id = report_data.get("report_id") or self._generate_report_id()

            now = datetime.now().isoformat()
            report_record = {
                "report_id": report_id,
                "user_id": user_id,
                "title": report_data.get("title", ""),
                "file_name": report_data.get("file_name", ""),
                "file_type": report_data.get("file_type", "log"),
                "summary": report_data.get("summary", ""),
                "statistics": report_data.get("statistics", {}),
                "analysis": report_data.get("analysis", {}),
                "files": report_data.get("files", []),
                "tags": report_data.get("tags", []),
                "metadata": report_data.get("metadata", {}),
                "created_at": now,
                "updated_at": now,
                "version": 1
            }

            report_path = self._get_report_path(user_id, report_id)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_record, f, indent=2, ensure_ascii=False)

            index = self._load_index(user_id)
            index["reports"].insert(0, {
                "report_id": report_id,
                "title": report_record["title"],
                "file_name": report_record["file_name"],
                "file_type": report_record["file_type"],
                "created_at": now,
                "updated_at": now
            })
            self._save_index(user_id, index)

            return report_id

    def get(self, user_id: str, report_id: str) -> Optional[Dict]:
        """获取单个报告"""
        report_path = self._get_report_path(user_id, report_id)
        if not report_path.exists():
            return None
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def list(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出用户的所有报告"""
        index = self._load_index(user_id)
        reports = index.get("reports", [])
        return reports[offset:offset + limit]

    def update(self, user_id: str, report_id: str, data: Dict) -> bool:
        """更新报告"""
        with self._lock:
            report = self.get(user_id, report_id)
            if not report:
                return False

            for key, value in data.items():
                if key in ["report_id", "user_id", "created_at"]:
                    continue
                report[key] = value

            report["updated_at"] = datetime.now().isoformat()
            report["version"] = report.get("version", 1) + 1

            report_path = self._get_report_path(user_id, report_id)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            index = self._load_index(user_id)
            for item in index.get("reports", []):
                if item.get("report_id") == report_id:
                    item["title"] = report.get("title", item.get("title"))
                    item["updated_at"] = report["updated_at"]
                    break
            self._save_index(user_id, index)

            return True

    def delete(self, user_id: str, report_id: str) -> bool:
        """删除报告"""
        with self._lock:
            report_path = self._get_report_path(user_id, report_id)
            if not report_path.exists():
                return False

            report_path.unlink()

            index = self._load_index(user_id)
            index["reports"] = [
                item for item in index.get("reports", [])
                if item.get("report_id") != report_id
            ]
            self._save_index(user_id, index)

            return True

    def search(self, user_id: str, keyword: str = "", limit: int = 100) -> List[Dict]:
        """搜索报告"""
        all_reports = self.list(user_id, limit=10000)
        if not keyword:
            return all_reports[:limit]

        keyword_lower = keyword.lower()
        results = []
        for report in all_reports:
            searchable = " ".join([
                str(report.get("title", "")),
                str(report.get("file_name", "")),
                str(report.get("summary", ""))
            ]).lower()

            if keyword_lower in searchable:
                results.append(report)

        return results[:limit]

    def count(self, user_id: str) -> int:
        """统计用户报告数量"""
        index = self._load_index(user_id)
        return len(index.get("reports", []))

    def backup(self, user_id: str, backup_dir: str) -> str:
        """备份用户数据"""
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return None

        backup_path = Path(backup_dir) / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ensure_dir(str(backup_path))

        shutil.copytree(user_dir, backup_path / "data", dirs_exist_ok=True)
        return str(backup_path)

    def restore(self, user_id: str, backup_path: str) -> bool:
        """从备份恢复"""
        backup_dir = Path(backup_path) / "data"
        if not backup_dir.exists():
            return False

        user_dir = self._get_user_dir(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir)

        shutil.copytree(backup_dir, user_dir)
        return True


# ==================== 数据库迁移接口（预留） ====================

class DatabaseReportStorage(ReportStorage):
    """基于数据库的报告存储（预留接口，待实现）

    示例使用 SQLAlchemy:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "sqlite:///./reports.db")
        self.engine = None
        self.SessionLocal = None
        # self._init_db()

    def _init_db(self):
        """初始化数据库（待实现）"""
        # from sqlalchemy import create_engine
        # from sqlalchemy.orm import sessionmaker
        # self.engine = create_engine(self.db_url)
        # self.SessionLocal = sessionmaker(bind=self.engine)
        # Base.metadata.create_all(self.engine)
        pass

    def create(self, user_id: str, report_data: Dict) -> str:
        # TODO: 实现数据库插入
        raise NotImplementedError("数据库存储待实现")

    def get(self, user_id: str, report_id: str) -> Optional[Dict]:
        # TODO: 实现数据库查询
        raise NotImplementedError("数据库存储待实现")

    def list(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        # TODO: 实现数据库列表
        raise NotImplementedError("数据库存储待实现")

    def update(self, user_id: str, report_id: str, data: Dict) -> bool:
        # TODO: 实现数据库更新
        raise NotImplementedError("数据库存储待实现")

    def delete(self, user_id: str, report_id: str) -> bool:
        # TODO: 实现数据库删除
        raise NotImplementedError("数据库存储待实现")

    def search(self, user_id: str, keyword: str = "", limit: int = 100) -> List[Dict]:
        # TODO: 实现数据库搜索
        raise NotImplementedError("数据库存储待实现")


# ==================== 全局存储实例 ====================

_storage_instance: Optional[ReportStorage] = None


def get_storage() -> ReportStorage:
    """获取存储实例（单例）"""
    global _storage_instance
    if _storage_instance is None:
        # 当前使用文件存储，后续可通过环境变量切换
        storage_type = os.environ.get("STORAGE_TYPE", "file")
        if storage_type == "database":
            _storage_instance = DatabaseReportStorage()
        else:
            _storage_instance = FileReportStorage()
    return _storage_instance


def set_storage(storage: ReportStorage):
    """设置存储实例（用于测试和切换）"""
    global _storage_instance
    _storage_instance = storage
