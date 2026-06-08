# Log Analyzer - 智能日志分析平台

> 多轮对话式智能日志分析系统，支持上传文件、服务器路径、日志分析、报告生成等功能

## 核心功能

### 🎯 主要特性

- **多轮对话式交互**：基于聊天的日志分析体验，支持上下文理解和指代消解
- **真实LLM集成**：集成多种大语言模型API，支持流式响应和智能回复
- **智能上下文压缩**：自动压缩长对话历史，保持上下文简洁高效
- **真实日志搜索**：连接真实的日志搜索功能，支持关键词、错误级别过滤
- **多文件分析**：支持批量分析服务器目录下的多个日志文件
- **文件暂存与合并发送**：上传文件后暂存，与提示词合并发送进行分析
- **文件上传**：支持拖拽上传.log、.txt、.zip、.pcap等格式文件
- **服务器文件浏览**：通过目录浏览器选择服务器上的日志文件
- **多格式报告**：支持PDF、Word、Markdown、HTML格式的报告生成
- **PCAP分析**：支持网络抓包文件分析（PCAP/PCAPNG）
- **历史报告管理**：查看、下载、删除历史生成的报告
- **用户维度功能**：支持用户信息展示、历史对话、操作日志等用户维度数据

### 🎨 界面布局

```
┌─────────────────────────────────────────────────────────────────┐
│                          应用容器                               │
├───────────────┬───────────────────────────┬───────────────────┤
│   左侧：对话列表 │     中间：聊天区域         │   右侧：功能面板   │
│               │                           │                   │
│  • 标题       │  • 对话标题               │  • 快捷操作       │
│  • 新建对话   │  • 消息列表（最多20条）    │    - 智能错误分析 │
│  • 对话列表   │    - 暂存文件区域         │    - 查询日志统计 │
│    - 标题     │  • 输入框                 │    - 生成报告     │
│    - 消息数   │    - 上传文件按钮          │    - PCAP分析     │
│    - 更新时间 │    - 选择服务器文件按钮    │                   │
│               │    - 发送按钮              │  • 工具调用状态   │
│  • 用户信息区  │                           │    - search_logs  │
│    - 用户头像  │                           │    - analyze_err  │
│    - 用户名    │                           │    - get_stats    │
│    - 使用时间  │                           │    - gen_report   │
│               │                           │                   │
│               │                           │  • 该对话历史报告 │
│               │                           │    - 报告列表     │
│               │                           │    - 下载链接     │
└───────────────┴───────────────────────────┴───────────────────┘
```

### ⚡ 快捷操作

- 🔍 **智能错误分析**：自动识别并合并相似错误
- 📊 **查询日志统计**：获取错误数、警告数等统计信息
- 📄 **生成报告**：为当前分析结果生成多格式报告
- 📶 **PCAP分析**：分析网络抓包文件

## 技术架构

### 🏗️ 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | 高性能异步Web框架 |
| LLM集成 | LangChain | 支持多种LLM提供商 |
| 日志解析 | 自定义解析器 | 支持多种日志格式 |
| 报告生成 | ReportLab/python-docx | PDF/Word报告 |
| 网络分析 | Tshark | PCAP文件解析 |
| 前端 | HTML/CSS/JavaScript | 响应式设计 |

### 📁 项目结构

```
log_analyzer/
├── web-langchain/          # Web服务（对话版本）
│   ├── app.py              # FastAPI应用入口
│   ├── chat_routes.py      # 对话API路由
│   ├── user_routes.py      # 用户管理API路由（用户信息、操作日志）
│   ├── chat_manager.py     # 聊天管理器（LLM、指代消解、上下文压缩）
│   ├── tool_executor.py    # 工具执行器（日志搜索、多文件分析）
│   ├── conversation_store.py # 对话存储
│   ├── auth.py             # 认证相关
│   ├── storage.py          # 存储管理
│   └── web/                # Web服务（旧版）
│       ├── app.py          # 旧版应用
│       ├── auth.py         # 认证
│       └── action_logger.py # 操作日志
├── parser/                 # 日志解析
│   └── log_parser.py      # 日志解析器
├── processor/              # 日志处理
│   └── chunk_processor.py # 分块处理器
├── report/                 # 报告生成
│   ├── generator.py       # 报告生成器
│   └── rule_based_analyzer.py # 规则分析器
├── llm/                    # LLM集成
│   └── client.py          # LLM客户端
├── config/                 # 配置
│   └── config.json        # 主配置
├── static/                # 静态资源
│   └── chat.html         # 对话界面
├── users/                 # 用户数据目录（按user_id隔离）
├── docs/                  # 文档
└── tests/                 # 测试
```

## 快速开始

### 🚀 环境要求

- Python 3.10+
- tshark (Wireshark命令行工具)
- 网络连接（使用LLM模式时）

### 📦 安装依赖

```bash
cd /Users/a666/Documents/trae_projects/log_analyz_chat/log/log_analyzer
pip install -r requirements.txt
```

### ▶️ 启动服务

```bash
cd /Users/a666/Documents/trae_projects/log_analyz_chat/log
PYTHONPATH=/Users/a666/Documents/trae_projects/log_analyz_chat/log \
python3 -m uvicorn log_analyzer.web-langchain.app:app \
  --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：http://localhost:8000/chat

## 核心模块说明

### 🤖 ChatManager（聊天管理器）

**位置**: `web-langchain/chat_manager.py`

**核心功能**:
- **真实LLM调用**：集成LLMClient，支持流式响应
- **指代消解**：自动解析"这个文件"、"刚才的分析"等代词引用
- **上下文压缩**：智能压缩对话历史，避免上下文过长
- **意图检测**：自动识别用户意图（搜索、分析、报告等）

**使用示例**:
```python
from log_analyzer.web_langchain import get_chat_manager

chat_manager = get_chat_manager(user_id="user123")

# 发送消息
result = await chat_manager.send_message(
    conversation_id="conv_123",
    content="分析这个日志文件"
)

# 流式消息
async for chunk in chat_manager.stream_message(
    conversation_id="conv_123",
    content="搜索ERROR日志"
):
    print(chunk)
```

### 🔍 ToolExecutor（工具执行器）

**位置**: `web-langchain/tool_executor.py`

**核心工具**:
- `search_logs`: 搜索日志内容
- `analyze_errors`: 分析错误
- `get_statistics`: 获取统计信息
- `generate_report`: 生成报告
- `list_uploaded_files`: 列出上传文件
- `list_server_directories`: 浏览服务器目录
- `analyze_from_server_path`: 从服务器路径分析
- `analyze_pcap`: 分析PCAP文件
- `analyze_nginx`: 分析Nginx日志

### 💬 ConversationStore（对话存储）

**位置**: `web-langchain/conversation_store.py`

**功能**:
- 多对话管理（创建、删除、列表）
- 消息存储与查询
- 对话上下文维护
- 对话维度的数据隔离

## API接口

### 对话相关接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/conversations` | GET | 获取对话列表 |
| `/api/conversations` | POST | 创建新对话 |
| `/api/conversations/{id}` | DELETE | 删除对话 |
| `/api/conversations/{id}/messages` | GET | 获取对话消息 |
| `/api/conversations/{id}/stream` | POST | 流式发送消息 |
| `/api/conversations/{id}/reports` | GET | 获取对话相关报告 |

### 文件相关接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传文件 |
| `/api/reports` | GET | 获取报告列表 |
| `/api/reports/{filename}` | GET | 下载报告 |

### 系统接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/initialize` | POST | 初始化系统 |

## 配置说明

### LLM配置

编辑 `config/config.json`:

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "your-api-key",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

### 服务器路径权限

```json
{
  "server_path": {
    "allowed_directories": ["/var/log", "/tmp"],
    "max_paths": 5
  }
}
```

## 高级功能

### 🎯 指代消解

系统自动识别并解析以下代词引用：

- **文件引用**: "这个文件"、"那个日志"、"该文件"
- **分析引用**: "刚才的分析"、"之前的分析"
- **动作引用**: "再分析一次"、"重新生成"

**示例**:
```
用户: 上传 app.log
AI: 已上传 app.log 文件

用户: 分析这个文件
系统自动解析为: 分析 app.log

用户: 刚才的分析结果怎么样？
系统自动解析为: app.log 的分析结果怎么样？
```

### 📚 上下文压缩

当对话历史超过15条消息时，系统自动压缩：

1. 保留最近5条消息
2. 将早期消息压缩为摘要
3. 摘要包含：首问、用户提问次数、AI回复次数

**压缩后的上下文示例**:
```
[对话历史摘要] 之前有 12 条消息的对话已压缩为摘要：
首问: 请帮我分析这个日志...；共 6 次用户提问；生成了 6 次回复

用户: 最近有什么错误？
AI: 根据分析结果...
```

### 🔄 多文件分析

支持分析服务器目录下的所有匹配文件：

```python
# 分析 /var/log 下的所有 .log 文件
result = await tool_executor.execute_tool(
    "analyze_from_server_path",
    {
        "path": "/var/log",
        "file_pattern": "*.log",
        "mode": "llm"
    }
)
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_chat.py -v

# 性能测试
pytest tests/concurrency_test.py -v
```

### 测试覆盖

- ✅ 对话管理功能测试
- ✅ 消息发送与流式响应测试
- ✅ 文件上传与处理测试
- ✅ 报告生成与下载测试
- ✅ 并发性能测试
- ✅ 用户数据隔离测试

## 常见问题

### Q: LLM调用失败怎么办？

**A**: 
1. 检查 `config/config.json` 中的API配置
2. 确认网络连接正常
3. 系统会自动降级到规则模式

### Q: 如何处理大文件？

**A**: 
1. 系统自动分块处理（默认5000行/块）
2. 支持断点续传
3. 可配置更大的chunk_size

### Q: 如何查看操作日志？

**A**: 
```bash
# 查看用户操作日志
cat data/action_logs/{user_id}/{date}.json
```

## 更新日志

详细更新日志请查看 [CHANGELOG.md](docs/CHANGELOG.md)

### 最新版本 v2.6.0

- ✅ 集成真实LLM API，替换模拟响应
- ✅ 实现指代消解和上下文压缩
- ✅ 优化前端体验（加载动画、消息编辑）
- ✅ 三栏式对话界面布局
- ✅ 对话维度的报告管理
- ✅ 修复API路由prefix问题
- ✅ 修复tool_calls处理错误

### 测试报告

详细功能测试报告请查看 [TEST_REPORT.md](docs/TEST_REPORT.md)

**测试结果**: 22项测试全部通过，通过率100%

## 文档目录

- [用户指南](docs/USER_GUIDE.md) - 详细使用说明
- [开发者指南](docs/DEVELOPER_GUIDE.md) - 开发文档
- [API文档](docs/API.md) - 接口文档
- [提示词库](docs/PROMPTS.md) - LLM提示词
- [规则模式指南](docs/RULE_MODE_GUIDE.md) - 规则分析模式
- [快速参考](docs/QUICK_REFERENCE.md) - 快速参考卡片
- [部署指南](DEPLOY.md) - 部署说明
- [项目概述](docs/PROJECT_OVERVIEW.md) - 完整项目说明
- [测试报告](docs/TEST_REPORT.md) - 功能测试报告 ✅ 新增

## License

MIT License
