"""Checkpoint manager for tracking processing progress."""

import os
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..utils.helpers import ensure_dir, safe_json_load, safe_json_dump


@dataclass
class Checkpoint:
    file_path: str
    file_hash: str
    total_lines: int
    processed_lines: int
    chunk_id: int
    last_chunk_line: int
    status: str = "in_progress"
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    processed_chunks: List[Dict[str, Any]] = field(default_factory=list)
    chunk_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        return cls(**data)

    def save(self, checkpoint_path: str) -> bool:
        self.updated_at = datetime.now().isoformat()
        return safe_json_dump(self.to_dict(), checkpoint_path)

    @classmethod
    def load(cls, checkpoint_path: str) -> Optional['Checkpoint']:
        data = safe_json_load(checkpoint_path)
        if data:
            return cls.from_dict(data)
        return None

    def is_complete(self) -> bool:
        return self.status == "completed"

    def get_progress(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return (self.processed_lines / self.total_lines) * 100

    def needs_resume(self) -> bool:
        return (
            self.status == "in_progress" and
            self.processed_lines > 0 and
            not self.is_complete()
        )


class CheckpointManager:
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir
        ensure_dir(checkpoint_dir)

    def _get_checkpoint_path(self, file_path: str) -> str:
        file_name = os.path.basename(file_path)
        checkpoint_name = f".checkpoint_{file_name}.json"
        return os.path.join(self.checkpoint_dir, checkpoint_name)

    def save_checkpoint(self, checkpoint: Checkpoint) -> str:
        checkpoint_path = self._get_checkpoint_path(checkpoint.file_path)
        checkpoint.save(checkpoint_path)
        return checkpoint_path

    def load_checkpoint(self, file_path: str) -> Optional[Checkpoint]:
        checkpoint_path = self._get_checkpoint_path(file_path)
        if not os.path.exists(checkpoint_path):
            return None

        checkpoint = Checkpoint.load(checkpoint_path)
        if checkpoint and checkpoint.file_path == file_path:
            return checkpoint
        return None

    def has_checkpoint(self, file_path: str) -> bool:
        return os.path.exists(self._get_checkpoint_path(file_path))

    def delete_checkpoint(self, file_path: str) -> bool:
        checkpoint_path = self._get_checkpoint_path(file_path)
        try:
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
                return True
        except OSError:
            pass
        return False

    def create_checkpoint(
        self,
        file_path: str,
        file_hash: str,
        total_lines: int
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            file_path=file_path,
            file_hash=file_hash,
            total_lines=total_lines,
            processed_lines=0,
            chunk_id=0,
            last_chunk_line=0,
            status="in_progress",
            started_at=datetime.now().isoformat()
        )
        self.save_checkpoint(checkpoint)
        return checkpoint

    def update_checkpoint(
        self,
        checkpoint: Checkpoint,
        processed_lines: int,
        chunk_id: int,
        last_chunk_line: int,
        chunk_result: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        checkpoint.processed_lines = processed_lines
        checkpoint.chunk_id = chunk_id
        checkpoint.last_chunk_line = last_chunk_line
        checkpoint.updated_at = datetime.now().isoformat()

        if chunk_result:
            checkpoint.chunk_results.append(chunk_result)

        self.save_checkpoint(checkpoint)
        return checkpoint

    def mark_complete(self, checkpoint: Checkpoint) -> Checkpoint:
        checkpoint.status = "completed"
        checkpoint.completed_at = datetime.now().isoformat()
        checkpoint.updated_at = datetime.now().isoformat()
        self.save_checkpoint(checkpoint)
        return checkpoint

    def mark_failed(self, checkpoint: Checkpoint, error_message: str) -> Checkpoint:
        checkpoint.status = "failed"
        checkpoint.error_message = error_message
        checkpoint.updated_at = datetime.now().isoformat()
        self.save_checkpoint(checkpoint)
        return checkpoint

    def get_all_checkpoints(self) -> List[Checkpoint]:
        checkpoints = []
        if not os.path.exists(self.checkpoint_dir):
            return checkpoints

        for file_name in os.listdir(self.checkpoint_dir):
            if file_name.startswith('.checkpoint_') and file_name.endswith('.json'):
                checkpoint_path = os.path.join(self.checkpoint_dir, file_name)
                checkpoint = Checkpoint.load(checkpoint_path)
                if checkpoint:
                    checkpoints.append(checkpoint)

        return checkpoints

    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        cleaned = 0
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        if not os.path.exists(self.checkpoint_dir):
            return cleaned

        for file_name in os.listdir(self.checkpoint_dir):
            if not file_name.startswith('.checkpoint_') or not file_name.endswith('.json'):
                continue

            checkpoint_path = os.path.join(self.checkpoint_dir, file_name)
            try:
                file_age = current_time - os.path.getmtime(checkpoint_path)
                if file_age > max_age_seconds:
                    os.remove(checkpoint_path)
                    cleaned += 1
            except OSError:
                continue

        return cleaned
