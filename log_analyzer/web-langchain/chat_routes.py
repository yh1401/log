"""
聊天相关 API 路由 - 完整集成原有日志分析系统
"""
import logging
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .conversation_store import get_conversation_store
from .chat_manager import get_chat_manager
from .tool_executor import get_tool_executor
from .auth import get_current_user

logger = logging.getLogger("web-langchain.chat_routes")

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: str = "新对话"
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None  # 新增：暂存文件信息
    stream: bool = False


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """创建新对话"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    conversation_id = f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    conversation = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": request.title,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message_count": 0,
        "status": "active",
        "metadata": request.metadata or {}
    }

    store.save_conversation(conversation)

    return {
        "code": 0,
        "message": "创建成功",
        "data": conversation
    }


@router.get("/conversations")
async def get_conversations(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取对话列表"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    conversations = store.list_conversations()

    return {
        "code": 0,
        "message": "获取成功",
        "data": conversations
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取单个对话详情"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    conversation = store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    return {
        "code": 0,
        "message": "获取成功",
        "data": conversation
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取对话消息"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    messages = store.get_messages(conversation_id, limit=limit, offset=offset)

    return {
        "code": 0,
        "message": "获取成功",
        "data": messages
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """发送消息（非流式）"""
    user_id = user.get("user_id", "hanmeimei")
    chat_manager = get_chat_manager(user_id=user_id)

    result = await chat_manager.send_message(
        conversation_id=conversation_id,
        content=request.content,
        metadata=request.metadata
    )

    return {
        "code": 0,
        "message": "发送成功",
        "data": result.get("assistant_message", {})
    }


@router.post("/conversations/{conversation_id}/stream")
async def stream_message(
    conversation_id: str,
    request: SendMessageRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """发送消息（流式 SSE）"""
    logger.info("=" * 60)
    logger.info(f"📬 收到 API 请求: POST /conversations/{conversation_id}/stream")
    logger.info(f"👤 用户信息: user_id={user.get('user_id')}, username={user.get('username')}")
    logger.info(f"📝 请求内容: content={request.content}")
    if request.files:
        logger.info(f"📁 文件信息: {json.dumps(request.files, ensure_ascii=False, indent=2)}")
    logger.info(f"⚙️ 是否流式: {request.stream}")
    logger.info("=" * 60)
    
    user_id = user.get("user_id", "hanmeimei")
    chat_manager = get_chat_manager(user_id=user_id)

    async def event_generator():
        try:
            logger.info("🚀 开始处理流式响应...")
            chunk_count = 0
            async for chunk in chat_manager.stream_message(
                conversation_id=conversation_id,
                content=request.content,
                metadata=request.metadata,
                files=request.files  # 传递文件信息
            ):
                chunk_count += 1
                logger.debug(f"📤 发送第 {chunk_count} 个响应块: type={chunk.get('type')}")
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            logger.info(f"✅ 流式响应完成! 共发送 {chunk_count} 个块")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ 流式响应错误: {e}", exc_info=True)
            error_chunk = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """删除对话"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    store.delete_conversation(conversation_id)

    return {
        "code": 0,
        "message": "删除成功",
        "data": {
            "conversation_id": conversation_id
        }
    }


@router.delete("/conversations/{conversation_id}/messages")
async def delete_conversation_messages(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """删除对话消息（清空对话）"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    store.clear_messages(conversation_id)

    return {
        "code": 0,
        "message": "消息已清空",
        "data": {
            "conversation_id": conversation_id
        }
    }


@router.get("/conversations/{conversation_id}/reports")
async def get_conversation_reports(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取指定对话的历史报告"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    result = tool_executor._handle_list_reports()

    if result.get("success"):
        reports = result.get("reports", [])
        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "conversation_id": conversation_id,
                "reports": reports
            }
        }
    else:
        return {
            "code": 1,
            "message": result.get("error", "获取失败"),
            "data": {
                "conversation_id": conversation_id,
                "reports": []
            }
        }


@router.post("/conversations/{conversation_id}/context/clear")
async def clear_conversation_context(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """清空对话上下文"""
    user_id = user.get("user_id", "hanmeimei")
    store = get_conversation_store(user_id=user_id)

    store.clear_messages(conversation_id)

    return {
        "code": 0,
        "message": "上下文已清空",
        "data": {
            "conversation_id": conversation_id
        }
    }


@router.get("/tools")
async def get_tools(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """获取可用工具列表"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    tools_info = []
    for tool_name, tool_def in tool_executor.tools.items():
        tools_info.append({
            "name": tool_name,
            "description": tool_def.get("description", ""),
            "parameters": tool_def.get("parameters", {})
        })

    return {
        "code": 0,
        "message": "获取成功",
        "data": tools_info
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """上传日志文件"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    try:
        filename = file.filename
        upload_dir = tool_executor.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename

        counter = 1
        while file_path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            file_path = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = file_path.stat().st_size

        return {
            "code": 0,
            "message": "上传成功",
            "data": {
                "filename": file_path.name,
                "size": file_size,
                "size_formatted": tool_executor._format_bytes(file_size),
                "path": str(file_path)
            }
        }
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/files")
async def list_uploaded_files(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """列出已上传文件"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    result = tool_executor._handle_list_uploaded_files()

    if result.get("success"):
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
    else:
        return {
            "code": 1,
            "message": result.get("error", "获取失败"),
            "data": None
        }


@router.get("/reports")
async def list_reports(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """列出历史报告"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    result = tool_executor._handle_list_reports()

    if result.get("success"):
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
    else:
        return {
            "code": 1,
            "message": result.get("error", "获取失败"),
            "data": None
        }


@router.get("/reports/{filename}")
async def download_report(
    filename: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """下载报告文件"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    report_path = tool_executor.reports_dir / filename
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=str(report_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/server/directories")
async def list_server_directories(
    path: str = "",
    user: Dict[str, Any] = Depends(get_current_user)
):
    """列出服务器目录"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    result = tool_executor._handle_list_server_directories(path=path)

    if result.get("success"):
        return {
            "code": 0,
            "message": "获取成功",
            "data": result
        }
    else:
        return {
            "code": 1,
            "message": result.get("error", "获取失败"),
            "data": None
        }


@router.post("/execute-tool")
async def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user)
):
    """执行工具"""
    user_id = user.get("user_id", "hanmeimei")
    tool_executor = get_tool_executor(user_id=user_id)

    result = await tool_executor.execute_tool(tool_name, parameters)

    if result.get("success"):
        return {
            "code": 0,
            "message": "执行成功",
            "data": result
        }
    else:
        return {
            "code": 1,
            "message": result.get("error", "执行失败"),
            "data": result
        }


import json
