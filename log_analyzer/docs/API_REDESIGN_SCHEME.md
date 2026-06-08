# API 接口改造方案

> 项目路径: `/Users/a666/Documents/trae_projects/log_analyz_chat/log/log_analyzer`
> 文档版本: v1.0
> 生成日期: 2026-06-07

---

## 一、接口改造概览

### 1.1 改造目标

将现有**单次请求-响应模式**升级为**多轮对话交互模式**，需要新增对话管理、消息发送、流式响应等接口。

### 1.2 改造策略

| 策略 | 说明 |
|------|------|
| **保留** | 现有文件上传、日志处理、报告下载等接口保持不变 |
| **增强** | 部分接口增加对话上下文支持 |
| **新增** | 对话管理、消息发送、流式响应等新接口 |

---

## 二、现有接口清单（改造前）

### 2.1 认证与基础接口

| API 路径 | HTTP 方法 | 功能描述 | 所属模块 |
|---------|----------|---------|---------|
| `/api/auth/identify` | POST | 用户身份识别 | web |
| `/api/auth/current` | GET | 获取当前用户信息 | web |
| `/api/health` | GET | 健康检查 | web |

### 2.2 文件与路径管理

| API 路径 | HTTP 方法 | 功能描述 | 所属模块 |
|---------|----------|---------|---------|
| `/api/upload` | POST | 上传日志文件 | web |
| `/api/list-dir` | POST | 列出目录内容 | web |
| `/api/read-path` | POST | 读取服务器路径 | web-langchain |
| `/api/process-from-path` | POST | 从路径处理日志 | web-langchain |

### 2.3 日志处理

| API 路径 | HTTP 方法 | 功能描述 | 所属模块 |
|---------|----------|---------|---------|
| `/api/process` | POST | 处理上传的日志文件 | web |
| `/api/task/{task_id}` | GET | 查询任务状态 | web |
| `/api/task/{task_id}/cancel` | POST | 取消任务 | web |

### 2.4 报告与历史

| API 路径 | HTTP 方法 | 功能描述 | 所属模块 |
|---------|----------|---------|---------|
| `/api/download/{file_path}` | GET | 下载文件 | web |
| `/api/reports` | GET | 获取报告列表 | web |
| `/api/history/reports` | GET/POST | 报告历史管理 | web |
| `/api/history/reports/{report_id}` | GET/PUT/DELETE | 单个报告操作 | web |
| `/api/history/actions` | POST/GET | 操作历史管理 | web |
| `/api/history/actions/{action_id}` | GET/DELETE | 单个操作记录 | web |

### 2.5 现有接口流程图

```
用户                    后端 API
 │                        │
 │─ 上传文件 ───────────→│ /api/upload
 │← 文件ID ──────────────│
 │                        │
 │─ 处理日志 ───────────→│ /api/process
 │← 任务ID ──────────────│
 │                        │
 │─ 查询状态 ───────────→│ /api/task/{id}
 │← 状态/报告 ───────────│
 │                        │
 │─ 下载报告 ───────────→│ /api/download/{path}
 │← 文件流 ──────────────│
```

---

## 三、新增接口清单（改造后）

### 3.1 对话管理接口

| API 路径 | HTTP 方法 | 功能描述 | 认证要求 |
|---------|----------|---------|---------|
| `/api/conversations` | GET | 获取对话列表 | ✅ |
| `/api/conversations` | POST | 创建新对话 | ✅ |
| `/api/conversations/{conv_id}` | GET | 获取对话详情 | ✅ |
| `/api/conversations/{conv_id}` | PUT | 更新对话信息（重命名） | ✅ |
| `/api/conversations/{conv_id}` | DELETE | 删除对话 | ✅ |

#### POST /api/conversations - 创建对话

**请求体：**
```json
{
    "title": "新对话",
    "metadata": {
        "source_file": "app.log",
        "tags": ["error", "payment"]
    }
}
```

**响应：**
```json
{
    "code": 0,
    "data": {
        "conversation_id": "conv_abc123",
        "title": "新对话",
        "created_at": "2024-01-15T10:30:00Z",
        "message_count": 0,
        "metadata": {
            "source_file": "app.log",
            "tags": ["error", "payment"]
        }
    }
}
```

#### GET /api/conversations - 获取对话列表

**响应：**
```json
{
    "code": 0,
    "data": [
        {
            "conversation_id": "conv_abc123",
            "title": "错误日志分析",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:45:00Z",
            "message_count": 8,
            "status": "active"
        },
        {
            "conversation_id": "conv_xyz789",
            "title": "性能分析",
            "created_at": "2024-01-14T09:00:00Z",
            "updated_at": "2024-01-14T10:30:00Z",
            "message_count": 12,
            "status": "active"
        }
    ]
}
```

#### DELETE /api/conversations/{conv_id} - 删除对话

**响应：**
```json
{
    "code": 0,
    "message": "对话删除成功",
    "data": {
        "conversation_id": "conv_abc123"
    }
}
```

### 3.2 消息发送接口

| API 路径 | HTTP 方法 | 功能描述 | 认证要求 |
|---------|----------|---------|---------|
| `/api/conversations/{conv_id}/messages` | GET | 获取消息历史 | ✅ |
| `/api/conversations/{conv_id}/messages` | POST | 发送消息（同步） | ✅ |
| `/api/conversations/{conv_id}/stream` | POST | 发送消息（流式响应） | ✅ |

#### POST /api/conversations/{conv_id}/messages - 同步消息

**请求体：**
```json
{
    "content": "分析最近1小时的错误日志",
    "metadata": {
        "source": "chat_input",
        "intent": "LOG_QUERY"
    }
}
```

**响应：**
```json
{
    "code": 0,
    "data": {
        "message_id": "msg_123",
        "role": "assistant",
        "content": "找到5条错误日志，主要来自payment-service...",
        "timestamp": "2024-01-15T12:00:00Z",
        "metadata": {
            "intent": "LOG_QUERY",
            "tools_used": ["search_logs"],
            "tokens_used": 1500
        }
    }
}
```

#### POST /api/conversations/{conv_id}/stream - 流式消息

**请求体：**
```json
{
    "content": "分析第一个错误的根本原因",
    "stream": true
}
```

**响应（SSE 流式）：**
```
event: message
data: {"type": "start", "message_id": "msg_456"}

event: message
data: {"type": "thinking", "content": "正在分析错误日志..."}

event: message
data: {"type": "tool_call", "tool": "analyze_errors", "args": {"error_id": "err_001"}}

event: message
data: {"type": "content", "content": "错误分析："}

event: message
data: {"type": "content", "content": "Connection timeout"}

event: message
data: {"type": "content", "content": "，发生在10:30:15"}

event: message
data: {"type": "finish", "metadata": {...}}
```

**事件类型说明：**

| 事件类型 | 说明 | 数据结构 |
|---------|------|---------|
| `start` | 响应开始 | `{message_id}` |
| `thinking` | 思考过程 | `{content}` |
| `tool_call` | 工具调用通知 | `{tool, args}` |
| `content` | 内容片段 | `{content}` |
| `finish` | 响应完成 | `{metadata}` |
| `error` | 错误发生 | `{error}` |

### 3.3 工具调用接口

| API 路径 | HTTP 方法 | 功能描述 | 认证要求 |
|---------|----------|---------|---------|
| `/api/tools` | GET | 获取可用工具列表 | ✅ |
| `/api/tools/{tool_name}` | POST | 直接调用工具 | ✅ |

#### GET /api/tools - 获取工具列表

**响应：**
```json
{
    "code": 0,
    "data": [
        {
            "name": "search_logs",
            "description": "搜索日志文件",
            "parameters": [
                {"name": "query", "type": "string", "required": true},
                {"name": "time_range", "type": "string", "required": false}
            ]
        },
        {
            "name": "analyze_errors",
            "description": "分析错误日志",
            "parameters": [
                {"name": "error_pattern", "type": "string", "required": true}
            ]
        },
        {
            "name": "generate_report",
            "description": "生成分析报告",
            "parameters": [
                {"name": "format", "type": "string", "enum": ["pdf", "word", "markdown"]},
                {"name": "include_charts", "type": "boolean"}
            ]
        }
    ]
}
```

#### POST /api/tools/{tool_name} - 调用工具

**请求体（search_logs）：**
```json
{
    "query": "Connection timeout",
    "time_range": "last_1_hour",
    "limit": 50
}
```

**响应：**
```json
{
    "code": 0,
    "data": {
        "tool_name": "search_logs",
        "result": {
            "total_count": 5,
            "logs": [...],
            "query_time": 120
        },
        "execution_time": 150
    }
}
```

### 3.4 上下文管理接口

| API 路径 | HTTP 方法 | 功能描述 | 认证要求 |
|---------|----------|---------|---------|
| `/api/conversations/{conv_id}/context` | GET | 获取对话上下文 | ✅ |
| `/api/conversations/{conv_id}/context/clear` | POST | 清空上下文 | ✅ |

#### GET /api/conversations/{conv_id}/context

**响应：**
```json
{
    "code": 0,
    "data": {
        "conversation_id": "conv_abc123",
        "context_size": 15000,
        "message_count": 8,
        "referenced_entities": [
            {"id": "err_001", "type": "error", "content": "Connection timeout"},
            {"id": "log_001", "type": "log", "content": "..."},
        ],
        "current_topic": "error_analysis"
    }
}
```

---

## 四、接口改造对比表

### 4.1 功能模块对比

| 功能模块 | 改造前接口 | 改造后接口 | 变化说明 |
|---------|----------|----------|---------|
| **认证** | `/api/auth/identify`<br>`/api/auth/current` | 保持不变 | ✅ 保留 |
| **文件上传** | `/api/upload` | 保持不变 | ✅ 保留 |
| **日志处理** | `/api/process`<br>`/api/process-from-path` | 保持不变 + 新增对话参数 | ⚠️ 增强 |
| **任务管理** | `/api/task/{task_id}` | 保持不变 | ✅ 保留 |
| **报告管理** | `/api/reports`<br>`/api/history/reports` | 保持不变 | ✅ 保留 |
| **对话管理** | 无 | `/api/conversations` (CRUD) | 🆕 新增 |
| **消息发送** | 无 | `/api/conversations/{id}/messages`<br>`/api/conversations/{id}/stream` | 🆕 新增 |
| **工具调用** | 无 | `/api/tools`<br>`/api/tools/{tool_name}` | 🆕 新增 |
| **上下文管理** | 无 | `/api/conversations/{id}/context` | 🆕 新增 |

### 4.2 接口数量对比

| 类别 | 改造前 | 改造后 | 新增 |
|------|--------|--------|------|
| 认证 | 2 | 2 | 0 |
| 文件管理 | 4 | 4 | 0 |
| 日志处理 | 3 | 3 | 0 |
| 报告历史 | 8 | 8 | 0 |
| **对话管理** | 0 | 5 | **5** |
| **消息管理** | 0 | 2 | **2** |
| **工具调用** | 0 | 2 | **2** |
| **上下文管理** | 0 | 2 | **2** |
| **总计** | **17** | **27** | **11** |

---

## 五、新增接口详细设计

### 5.1 接口设计规范

**通用响应格式：**
```json
{
    "code": 0,          // 0=成功, 非0=错误码
    "message": "",      // 错误/成功消息
    "data": {},         // 业务数据
    "timestamp": ""     // 时间戳
}
```

**错误响应格式：**
```json
{
    "code": 404,
    "message": "对话不存在",
    "data": null,
    "timestamp": "2024-01-15T12:00:00Z"
}
```

### 5.2 接口安全规范

| 规范 | 说明 |
|------|------|
| **认证要求** | 所有接口均需 `X-User-Id` 或 `Authorization` 头 |
| **权限隔离** | 用户只能访问自己的对话和数据 |
| **请求限流** | 单用户每分钟最多10次消息请求 |
| **输入校验** | 所有输入参数进行严格校验 |
| **敏感信息** | 日志内容中的敏感信息自动脱敏 |

### 5.3 新增接口路由定义

```python
# web-langchain/routes/chat_routes.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any
from datetime import datetime
import asyncio

from .auth import get_current_user
from .conversation_store import ConversationStore
from .chat_manager import ChatManager
from .tool_executor import ToolExecutor

router = APIRouter(prefix="/api", tags=["chat"])

# ==================== 对话管理 ====================

@router.get("/conversations")
async def get_conversations(
    current_user: Dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """获取对话列表"""
    store = ConversationStore()
    conversations = await store.list_conversations(
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset
    )
    return JSONResponse({
        "code": 0,
        "data": conversations
    })

@router.post("/conversations")
async def create_conversation(
    request: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """创建新对话"""
    store = ConversationStore()
    conv_id = await store.create_conversation(
        user_id=current_user["user_id"],
        title=request.get("title", "新对话"),
        metadata=request.get("metadata", {})
    )
    conversation = await store.get_conversation(conv_id)
    return JSONResponse({
        "code": 0,
        "data": conversation
    })

@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取对话详情"""
    store = ConversationStore()
    conversation = await store.get_conversation(conv_id)
    
    if not conversation or conversation["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return JSONResponse({
        "code": 0,
        "data": conversation
    })

@router.put("/conversations/{conv_id}")
async def update_conversation(
    conv_id: str,
    request: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """更新对话信息"""
    store = ConversationStore()
    await store.update_conversation(
        conv_id=conv_id,
        updates=request,
        user_id=current_user["user_id"]
    )
    return JSONResponse({
        "code": 0,
        "message": "更新成功"
    })

@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """删除对话"""
    store = ConversationStore()
    await store.delete_conversation(
        conv_id=conv_id,
        user_id=current_user["user_id"]
    )
    return JSONResponse({
        "code": 0,
        "message": "删除成功"
    })

# ==================== 消息管理 ====================

@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv_id: str,
    current_user: Dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """获取消息历史"""
    store = ConversationStore()
    messages = await store.get_messages(
        conv_id=conv_id,
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset
    )
    return JSONResponse({
        "code": 0,
        "data": messages
    })

@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: str,
    request: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """发送消息（同步模式）"""
    chat_manager = ChatManager()
    response = await chat_manager.send_message(
        conversation_id=conv_id,
        user_id=current_user["user_id"],
        content=request["content"],
        metadata=request.get("metadata", {})
    )
    return JSONResponse({
        "code": 0,
        "data": response
    })

@router.post("/conversations/{conv_id}/stream")
async def stream_message(
    conv_id: str,
    request: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """发送消息（流式模式）"""
    async def generate():
        chat_manager = ChatManager()
        async for chunk in chat_manager.stream_message(
            conversation_id=conv_id,
            user_id=current_user["user_id"],
            content=request["content"]
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

# ==================== 工具管理 ====================

@router.get("/tools")
async def get_tools(current_user: Dict = Depends(get_current_user)):
    """获取可用工具列表"""
    executor = ToolExecutor()
    tools = executor.get_available_tools()
    return JSONResponse({
        "code": 0,
        "data": tools
    })

@router.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str,
    request: Dict,
    current_user: Dict = Depends(get_current_user)
):
    """调用工具"""
    executor = ToolExecutor()
    result = await executor.execute_tool(
        tool_name=tool_name,
        args=request,
        user_id=current_user["user_id"]
    )
    return JSONResponse({
        "code": 0,
        "data": result
    })

# ==================== 上下文管理 ====================

@router.get("/conversations/{conv_id}/context")
async def get_context(
    conv_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取对话上下文"""
    chat_manager = ChatManager()
    context = await chat_manager.get_context(conv_id)
    return JSONResponse({
        "code": 0,
        "data": context
    })

@router.post("/conversations/{conv_id}/context/clear")
async def clear_context(
    conv_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """清空对话上下文"""
    chat_manager = ChatManager()
    await chat_manager.clear_context(conv_id)
    return JSONResponse({
        "code": 0,
        "message": "上下文已清空"
    })
```

---

## 六、前后端交互流程

### 6.1 完整对话交互流程

```
用户                    前端                     后端 API
 │                        │                         │
 │─ 打开页面 ───────────→│                         │
 │                        │─ GET /api/conversations ─→│
 │                        │← 对话列表 ───────────────│
 │                        │                         │
 │─ 选择对话 ───────────→│                         │
 │                        │─ GET /api/conversations/{id}/messages ─→│
 │                        │← 消息历史 ───────────────│
 │                        │                         │
 │─ 输入消息 ───────────→│                         │
 │                        │─ POST /api/conversations/{id}/stream ─→│
 │                        │                         │
 │                        │← SSE: start ────────────│
 │                        │← SSE: thinking ─────────│
 │                        │← SSE: tool_call ────────│
 │← 显示思考过程 ────────│                         │
 │                        │← SSE: content ─────────│
 │← 显示内容 ────────────│                         │
 │                        │← SSE: finish ──────────│
 │                        │                         │
 │                        │─ POST /api/conversations/{id}/messages (保存) ─→│
```

### 6.2 工具调用交互流程

```
用户                    前端                     后端 API
 │                        │                         │
 │─ "分析这个错误" ─────→│                         │
 │                        │─ POST /api/conversations/{id}/stream ─→│
 │                        │                         │
 │                        │← SSE: tool_call ────────│
 │← "正在分析错误..." ───│                         │
 │                        │                         │
 │                        │─ 调用 analyze_errors 工具 ─→│
 │                        │                         │
 │                        │← 工具执行结果 ───────────│
 │                        │                         │
 │                        │← SSE: content ─────────│
 │← "错误分析结果: ..." ─│                         │
 │                        │← SSE: finish ──────────│
```

---

## 七、接口版本兼容性

### 7.1 向后兼容策略

| 接口 | 兼容性 | 说明 |
|------|--------|------|
| `/api/upload` | ✅ 完全兼容 | 保持不变 |
| `/api/process` | ✅ 完全兼容 | 保持不变 |
| `/api/task/{id}` | ✅ 完全兼容 | 保持不变 |
| `/api/download/{path}` | ✅ 完全兼容 | 保持不变 |
| `/api/reports` | ✅ 完全兼容 | 保持不变 |

### 7.2 新增接口版本控制

```
/api/v1/conversations       # v1 版本
/api/v1/conversations/{id}/messages
/api/v1/tools
```

### 7.3 迁移建议

| 阶段 | 任务 | 说明 |
|------|------|------|
| Phase 1 | 新增接口开发 | 不影响现有功能 |
| Phase 2 | 前端改造 | 逐步迁移到新接口 |
| Phase 3 | 旧接口标记 | 标记为 deprecated |
| Phase 4 | 旧接口移除 | 发布新版本时移除 |

---

## 八、接口安全考虑

### 8.1 认证与授权

```python
# 认证依赖
async def get_current_user(
    x_user_id: str = Header(None),
    authorization: str = Header(None)
):
    """获取当前用户"""
    if x_user_id:
        return {"user_id": x_user_id, "auth_type": "header"}
    elif authorization:
        # JWT token 验证
        payload = verify_jwt_token(authorization)
        return {"user_id": payload["user_id"], "auth_type": "jwt"}
    else:
        raise HTTPException(status_code=401, detail="未授权")
```

### 8.2 输入校验

```python
from pydantic import BaseModel, Field, validator

class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4096)
    metadata: Dict = Field(default={})
    
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('内容不能为空')
        return v
```

### 8.3 限流策略

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@router.post("/conversations/{conv_id}/messages")
@limiter.limit("10/minute")
async def send_message(...):
    pass
```

---

## 九、总结

### 9.1 接口改造汇总

| 项目 | 数量 |
|------|------|
| 现有接口 | 17 个 |
| 新增接口 | 11 个 |
| 改造后总计 | 28 个 |

### 9.2 新增接口清单

1. **对话管理** (5个)
   - `GET /api/conversations` - 获取对话列表
   - `POST /api/conversations` - 创建对话
   - `GET /api/conversations/{id}` - 获取对话详情
   - `PUT /api/conversations/{id}` - 更新对话
   - `DELETE /api/conversations/{id}` - 删除对话

2. **消息管理** (2个)
   - `GET /api/conversations/{id}/messages` - 获取消息历史
   - `POST /api/conversations/{id}/stream` - 流式消息

3. **工具管理** (2个)
   - `GET /api/tools` - 获取工具列表
   - `POST /api/tools/{name}` - 调用工具

4. **上下文管理** (2个)
   - `GET /api/conversations/{id}/context` - 获取上下文
   - `POST /api/conversations/{id}/context/clear` - 清空上下文

### 9.3 实施优先级

| 优先级 | 接口 | 原因 |
|--------|------|------|
| **P0** | 对话 CRUD | 基础功能，必须优先实现 |
| **P0** | 消息发送 | 核心交互功能 |
| **P1** | 流式响应 | 提升用户体验 |
| **P1** | 工具调用 | Agent 能力支撑 |
| **P2** | 上下文管理 | 高级功能，可延后 |

---

## 附录

### A. 接口变更对照表

| 改造前 | 改造后 | 状态 |
|--------|--------|------|
| 无对话管理 | `/api/conversations` | 🆕 新增 |
| 无消息接口 | `/api/conversations/{id}/messages` | 🆕 新增 |
| 无流式响应 | `/api/conversations/{id}/stream` | 🆕 新增 |
| 无工具接口 | `/api/tools` | 🆕 新增 |
| `/api/upload` | `/api/upload` | ✅ 保留 |
| `/api/process` | `/api/process` | ✅ 保留 |
| `/api/task/{id}` | `/api/task/{id}` | ✅ 保留 |
| `/api/download/{path}` | `/api/download/{path}` | ✅ 保留 |

### B. HTTP 状态码说明

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | 成功 | 正常响应 |
| 201 | 创建成功 | 创建对话/消息 |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未授权 | 缺少认证信息 |
| 403 | 拒绝访问 | 权限不足 |
| 404 | 不存在 | 资源未找到 |
| 429 | 请求过多 | 限流触发 |
| 500 | 服务器错误 | 内部异常 |
