
"""
数据模型模块 - 定义所有Pydantic模型和数据结构
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ==================== 处理请求和响应模型 ====================

class ProcessRequest(BaseModel):
    """日志处理请求模型"""
    file_path: Optional[str] = None
    directory_path: Optional[str] = None
    chunk_size: int = 50000
    force_restart: bool = False


class ProcessResponse(BaseModel):
    """日志处理响应模型"""
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str
    progress: float
    message: str
    reports: Optional[List[Dict[str, str]]] = None
    error: Optional[str] = None


# ==================== 路径读取模型 ====================

class PathReadRequest(BaseModel):
    """从服务器路径读取日志文件的请求模型"""
    path: str  # 文件或目录路径
    recursive: bool = False  # 是否递归读取子目录
    max_file_size: int = 100 * 1024 * 1024  # 最大文件大小：100MB
    file_patterns: Optional[List[str]] = None  # 文件匹配模式，如 ["*.log", "*.txt"]


class PathReadResponse(BaseModel):
    """路径读取响应模型"""
    success: bool
    path: str
    file_count: int = 0
    total_size: int = 0
    files: Optional[List[Dict[str, Any]]] = None
    preview: Optional[str] = None
    error: Optional[str] = None


# ==================== 认证模型 ====================

class IdentifyRequest(BaseModel):
    """用户身份识别请求模型"""
    user_id: Optional[str] = None
    username: Optional[str] = None


# ==================== 对话管理模型 ====================

class ConversationCreate(BaseModel):
    """创建对话请求模型"""
    title: Optional[str] = "新对话"
    metadata: Optional[Dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    """更新对话请求模型"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    """创建消息请求模型"""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    stream: bool = False


class Conversation(BaseModel):
    """对话模型"""
    conversation_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """消息模型"""
    message_id: str
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


# ==================== 工具调用模型 ====================

class ToolCall(BaseModel):
    """工具调用请求模型"""
    tool_name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """工具调用结果模型"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0


# ==================== 意图识别模型 ====================

class IntentClassification(BaseModel):
    """意图识别结果模型"""
    intent: str
    confidence: float
    entities: Optional[List[Dict[str, Any]]] = None
    suggested_tools: Optional[List[str]] = None
