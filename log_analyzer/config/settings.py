"""Application settings and configuration management."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class LLMConfig:
    api_url: str
    model_name: str
    api_key: str
    backup_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'api_url': self.api_url,
            'model_name': self.model_name,
            'api_key': self.api_key,
            'backup_model': self.backup_model
        }


@dataclass
class ProcessingConfig:
    chunk_size: int = 10000
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    checkpoint_interval: int = 1000
    enable_checkpoint: bool = True
    max_workers: int = 4


@dataclass
class Settings:
    llm: LLMConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    error_log_dir: str = "/Users/a666/Documents/trae_projects/log/loggen/data/error"
    output_dir: str = "/Users/a666/Documents/trae_projects/log/log_analyzer/reports"
    checkpoint_dir: str = "/Users/a666/Documents/trae_projects/log/log_analyzer/checkpoints"
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        llm_data = data.get('llm', {})
        llm_config = LLMConfig(
            api_url=llm_data.get('api_url', ''),
            model_name=llm_data.get('model_name', ''),
            api_key=llm_data.get('api_key', ''),
            backup_model=llm_data.get('backup_model')
        )

        processing_data = data.get('processing', {})
        processing_config = ProcessingConfig(
            chunk_size=processing_data.get('chunk_size', 10000),
            max_retries=processing_data.get('max_retries', 3),
            retry_delay=processing_data.get('retry_delay', 1.0),
            batch_size=processing_data.get('batch_size', 100),
            checkpoint_interval=processing_data.get('checkpoint_interval', 1000),
            enable_checkpoint=processing_data.get('enable_checkpoint', True),
            max_workers=processing_data.get('max_workers', 4)
        )

        return cls(
            llm=llm_config,
            processing=processing_config,
            error_log_dir=data.get('error_log_dir', Settings.error_log_dir),
            output_dir=data.get('output_dir', Settings.output_dir),
            checkpoint_dir=data.get('checkpoint_dir', Settings.checkpoint_dir),
            log_level=data.get('log_level', 'INFO')
        )


def load_llm_config(config_path: str = "/Users/a666/Documents/trae_projects/log/loggen/llm/llmconfig") -> LLMConfig:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"LLM config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) < 3:
        raise ValueError(f"Invalid LLM config format in {config_path}")

    return LLMConfig(
        api_url=lines[0],
        model_name=lines[1],
        api_key=lines[2],
        backup_model=lines[3] if len(lines) > 3 else None
    )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        llm_config = load_llm_config()
        _settings = Settings(llm=llm_config)
    return _settings


def init_settings(**kwargs) -> Settings:
    global _settings
    llm_config = kwargs.get('llm')
    if llm_config is None:
        llm_config = load_llm_config()

    processing_config = kwargs.get('processing')
    if processing_config is None:
        processing_config = ProcessingConfig()

    _settings = Settings(
        llm=llm_config,
        processing=processing_config,
        error_log_dir=kwargs.get('error_log_dir', Settings.error_log_dir),
        output_dir=kwargs.get('output_dir', Settings.output_dir),
        checkpoint_dir=kwargs.get('checkpoint_dir', Settings.checkpoint_dir),
        log_level=kwargs.get('log_level', 'INFO')
    )
    return _settings
