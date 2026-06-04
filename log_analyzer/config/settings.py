"""Application settings and configuration management.

统一配置管理模块，支持从多个来源加载配置：
1. config.json - 默认配置（版本控制）
2. config.local.json - 本地覆盖配置（gitignore）
3. 环境变量 - 运行时覆盖
4. 命令行参数 - 最高优先级
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class LLMConfig:
    """LLM 服务配置"""
    api_url: str
    model_name: str
    api_key: str
    backup_model: Optional[str] = None

    def validate(self) -> None:
        """验证配置有效性"""
        if not self.api_url:
            raise ValueError("LLM API URL 不能为空")
        if not self.model_name:
            raise ValueError("LLM 模型名称不能为空")


@dataclass
class ProcessingConfig:
    """日志处理配置"""
    chunk_size: int = 10000
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    checkpoint_interval: int = 1000
    enable_checkpoint: bool = True
    max_workers: int = 4
    merge_threshold: float = 0.8


@dataclass
class PathsConfig:
    """路径配置"""
    error_log_dir: str = "/Users/a666/Documents/trae_projects/log/loggen/data/error"
    output_dir: str = "/Users/a666/Documents/trae_projects/log/log_analyzer/reports"
    checkpoint_dir: str = "/Users/a666/Documents/trae_projects/log/log_analyzer/checkpoints"
    user_data_dir: str = "/Users/a666/Documents/trae_projects/log/log_analyzer/users"


@dataclass
class LoggingConfig:
    """日志配置"""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True


@dataclass
class AppConfig:
    """应用服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    api_prefix: str = "/api"


@dataclass
class SecurityConfig:
    """安全配置"""
    allowed_users: List[str] = field(default_factory=lambda: ["admin001", "test_user"])
    max_file_size_mb: int = 500
    max_files_per_request: int = 10


@dataclass
class ServerPathConfig:
    """服务器路径权限配置"""
    allowed_directories: List[str] = field(default_factory=list)
    max_paths: int = 5

    def validate(self) -> None:
        """验证配置有效性"""
        if len(self.allowed_directories) > self.max_paths:
            raise ValueError(f"允许的目录数量不能超过 {self.max_paths} 个")
        
        # 验证路径格式
        for path in self.allowed_directories:
            if not path:
                raise ValueError("路径不能为空")
            # 可以添加更多路径验证逻辑


@dataclass
class Settings:
    """应用全局配置"""
    llm: LLMConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    app: AppConfig = field(default_factory=AppConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    server_path: ServerPathConfig = field(default_factory=ServerPathConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Settings':
        """
        从多个来源加载配置，优先级从低到高：
        1. config.json - 默认配置
        2. config.local.json - 本地覆盖
        3. 环境变量 - 运行时覆盖
        """
        config_dir = Path(__file__).parent
        
        # 1. 加载默认配置文件
        config_data = cls._load_from_file(config_dir / "config.json")
        
        # 2. 加载本地覆盖配置（如果存在）
        local_config = cls._load_from_file(config_dir / "config.local.json")
        if local_config:
            config_data = cls._deep_merge(config_data, local_config)
        
        # 3. 加载环境变量覆盖
        config_data = cls._load_from_env(config_data)
        
        # 4. 使用指定路径的配置文件（如果提供）
        if config_path and os.path.exists(config_path):
            custom_config = cls._load_from_file(Path(config_path))
            if custom_config:
                config_data = cls._deep_merge(config_data, custom_config)
        
        return cls._from_dict(config_data)

    @staticmethod
    def _load_from_file(file_path: Path) -> Dict[str, Any]:
        """从 JSON 文件加载配置"""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"警告：配置文件 {file_path} 格式错误: {e}")
        return {}

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """深度合并两个配置字典"""
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = Settings._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _load_from_env(config: Dict) -> Dict:
        """从环境变量加载配置"""
        env_mapping = {
            # LLM 配置
            'LLM_API_URL': ('llm', 'api_url'),
            'LLM_MODEL_NAME': ('llm', 'model_name'),
            'LLM_API_KEY': ('llm', 'api_key'),
            'LLM_BACKUP_MODEL': ('llm', 'backup_model'),
            
            # 处理配置
            'PROCESSING_CHUNK_SIZE': ('processing', 'chunk_size', int),
            'PROCESSING_MAX_RETRIES': ('processing', 'max_retries', int),
            'PROCESSING_RETRY_DELAY': ('processing', 'retry_delay', float),
            'PROCESSING_BATCH_SIZE': ('processing', 'batch_size', int),
            'PROCESSING_CHECKPOINT_INTERVAL': ('processing', 'checkpoint_interval', int),
            'PROCESSING_ENABLE_CHECKPOINT': ('processing', 'enable_checkpoint', bool),
            'PROCESSING_MAX_WORKERS': ('processing', 'max_workers', int),
            'PROCESSING_MERGE_THRESHOLD': ('processing', 'merge_threshold', float),
            
            # 路径配置
            'PATHS_ERROR_LOG_DIR': ('paths', 'error_log_dir'),
            'PATHS_OUTPUT_DIR': ('paths', 'output_dir'),
            'PATHS_CHECKPOINT_DIR': ('paths', 'checkpoint_dir'),
            'PATHS_USER_DATA_DIR': ('paths', 'user_data_dir'),
            
            # 日志配置
            'LOGGING_LOG_LEVEL': ('logging', 'log_level'),
            'LOGGING_LOG_FORMAT': ('logging', 'log_format'),
            'LOGGING_ENABLE_FILE_LOGGING': ('logging', 'enable_file_logging', bool),
            
            # 应用配置
            'APP_HOST': ('app', 'host'),
            'APP_PORT': ('app', 'port', int),
            'APP_DEBUG': ('app', 'debug', bool),
            'APP_API_PREFIX': ('app', 'api_prefix'),
        }
        
        for env_key, mapping in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                section, key = mapping[0], mapping[1]
                converter = mapping[2] if len(mapping) > 2 else str
                
                if section not in config:
                    config[section] = {}
                
                try:
                    config[section][key] = converter(value)
                except ValueError:
                    print(f"警告：无法转换环境变量 {env_key} 的值 '{value}'")
        
        return config

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> 'Settings':
        """从字典创建 Settings 对象"""
        # LLM 配置
        llm_data = data.get('llm', {})
        llm_config = LLMConfig(
            api_url=llm_data.get('api_url', ''),
            model_name=llm_data.get('model_name', ''),
            api_key=llm_data.get('api_key', ''),
            backup_model=llm_data.get('backup_model')
        )
        llm_config.validate()
        
        # 处理配置
        processing_data = data.get('processing', {})
        processing_config = ProcessingConfig(
            chunk_size=processing_data.get('chunk_size', 10000),
            max_retries=processing_data.get('max_retries', 3),
            retry_delay=processing_data.get('retry_delay', 1.0),
            batch_size=processing_data.get('batch_size', 100),
            checkpoint_interval=processing_data.get('checkpoint_interval', 1000),
            enable_checkpoint=processing_data.get('enable_checkpoint', True),
            max_workers=processing_data.get('max_workers', 4),
            merge_threshold=processing_data.get('merge_threshold', 0.8)
        )
        
        # 路径配置
        paths_data = data.get('paths', {})
        paths_config = PathsConfig(
            error_log_dir=paths_data.get('error_log_dir', PathsConfig.error_log_dir),
            output_dir=paths_data.get('output_dir', PathsConfig.output_dir),
            checkpoint_dir=paths_data.get('checkpoint_dir', PathsConfig.checkpoint_dir),
            user_data_dir=paths_data.get('user_data_dir', PathsConfig.user_data_dir)
        )
        
        # 日志配置
        logging_data = data.get('logging', {})
        logging_config = LoggingConfig(
            log_level=logging_data.get('log_level', 'INFO'),
            log_format=logging_data.get('log_format', LoggingConfig.log_format),
            enable_file_logging=logging_data.get('enable_file_logging', True)
        )
        
        # 应用配置
        app_data = data.get('app', {})
        app_config = AppConfig(
            host=app_data.get('host', '0.0.0.0'),
            port=app_data.get('port', 8000),
            debug=app_data.get('debug', False),
            api_prefix=app_data.get('api_prefix', '/api')
        )
        
        # 安全配置
        security_data = data.get('security', {})
        security_config = SecurityConfig(
            allowed_users=security_data.get('allowed_users', ["admin001", "test_user"]),
            max_file_size_mb=security_data.get('max_file_size_mb', 500),
            max_files_per_request=security_data.get('max_files_per_request', 10)
        )
        
        # 服务器路径配置
        server_path_data = data.get('server_path', {})
        server_path_config = ServerPathConfig(
            allowed_directories=server_path_data.get('allowed_directories', []),
            max_paths=server_path_data.get('max_paths', 5)
        )
        server_path_config.validate()
        
        return Settings(
            llm=llm_config,
            processing=processing_config,
            paths=paths_config,
            logging=logging_config,
            app=app_config,
            security=security_config,
            server_path=server_path_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'llm': {
                'api_url': self.llm.api_url,
                'model_name': self.llm.model_name,
                'api_key': '***',  # 敏感信息脱敏
                'backup_model': self.llm.backup_model
            },
            'processing': {
                'chunk_size': self.processing.chunk_size,
                'max_retries': self.processing.max_retries,
                'retry_delay': self.processing.retry_delay,
                'batch_size': self.processing.batch_size,
                'checkpoint_interval': self.processing.checkpoint_interval,
                'enable_checkpoint': self.processing.enable_checkpoint,
                'max_workers': self.processing.max_workers,
                'merge_threshold': self.processing.merge_threshold
            },
            'paths': {
                'error_log_dir': self.paths.error_log_dir,
                'output_dir': self.paths.output_dir,
                'checkpoint_dir': self.paths.checkpoint_dir,
                'user_data_dir': self.paths.user_data_dir
            },
            'logging': {
                'log_level': self.logging.log_level,
                'log_format': self.logging.log_format,
                'enable_file_logging': self.logging.enable_file_logging
            },
            'app': {
                'host': self.app.host,
                'port': self.app.port,
                'debug': self.app.debug,
                'api_prefix': self.app.api_prefix
            },
            'security': {
                'allowed_users': self.security.allowed_users,
                'max_file_size_mb': self.security.max_file_size_mb,
                'max_files_per_request': self.security.max_files_per_request
            }
        }


# 全局设置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def init_settings(config_path: Optional[str] = None) -> Settings:
    """初始化全局配置"""
    global _settings
    _settings = Settings.load(config_path)
    return _settings


def load_llm_config(config_path: str = None) -> LLMConfig:
    """
    兼容旧接口：加载 LLM 配置
    
    Args:
        config_path: 配置文件路径（可选，为保持向后兼容保留）
    
    Returns:
        LLMConfig 对象
    """
    if config_path and os.path.exists(config_path):
        # 兼容旧的 llmconfig 纯文本格式
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if len(lines) >= 3:
                return LLMConfig(
                    api_url=lines[0],
                    model_name=lines[1],
                    api_key=lines[2],
                    backup_model=lines[3] if len(lines) > 3 else None
                )
        except Exception as e:
            print(f"警告：加载旧格式配置文件失败，使用新配置体系: {e}")
    
    # 使用新的配置体系
    return get_settings().llm
