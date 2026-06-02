"""Helper utility functions."""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict


def ensure_dir(path: str) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def format_timestamp(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def calculate_file_hash(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""

    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size_str(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "0 B"

    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def safe_json_load(file_path: str, default: Any = None) -> Any:
    try:
        if not os.path.exists(file_path):
            return default
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def safe_json_dump(data: Any, file_path: str, indent: int = 2) -> bool:
    try:
        ensure_dir(os.path.dirname(file_path))
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (IOError, TypeError):
        return False


class ProgressTracker:
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.last_percent = -1

    def update(self, increment: int = 1) -> None:
        self.current += increment
        percent = int((self.current / self.total) * 100) if self.total > 0 else 0
        if percent != self.last_percent and percent % 5 == 0:
            self.last_percent = percent
            print(f"\r{self.description}: {percent}% ({self.current}/{self.total})", end="", flush=True)

    def finish(self) -> None:
        print(f"\r{self.description}: 100% ({self.current}/{self.total}) - Complete!")

    def get_progress(self) -> float:
        return (self.current / self.total) * 100 if self.total > 0 else 0
