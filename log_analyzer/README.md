# Log Analyzer

> 基于 LLM 的大规模日志分析与网络抓包分析系统
>
> 版本: v2.5.2 | 最后更新: 2026-06-05

---

## 一、项目概述

### 1.1 项目定位

**Log Analyzer** 是一个面向运维工程师、SRE 团队和后端开发人员的**智能日志分析平台**。它通过调用大语言模型（LLM），对传统的海量应用日志和网络抓包文件进行**结构化分析、错误聚合、根因推断和整改建议生成**。

系统支持**两种分析模式**：
- **LLM 模式**：调用大语言模型进行深度语义分析，适合复杂问题诊断
- **规则模式**：不依赖 LLM，使用预定义规则进行快速分析，零成本极速响应

### 1.2 核心能力

#### 📊 大规模日志处理

| 特性 | 说明 |
|------|------|
| 流式分块处理 | 支持 100MB+ 日志文件，内存占用稳定在 200MB 以内 |
| 内存映射技术 | 使用 `mmap` 零拷贝读取，避免大文件加载 |
| 断点续传 | 任务中断后可从上次进度继续，支持任务恢复 |
| 并发控制 | 内置信号量限制 LLM 并发调用，避免 API 限流 |

#### 🔍 智能错误识别

| 特性 | 说明 |
|------|------|
| 8 类错误模式 | 空引用、资源泄漏、超时、认证、数据库、网络、配置、内存 |
| 语义相似度合并 | 基于编辑距离算法合并相似错误，减少重复内容 |
| 动态内容提取 | 自动识别并标准化 UUID、IP、时间戳等动态内容 |
| 根因推断 | LLM 模式提供深度根因分析，规则模式提供关键词匹配 |

#### 📝 自动报告生成

| 格式 | 特点 |
|------|------|
| PDF | 格式化排版，支持中文，适合正式报告 |
| Word | 可编辑文档，支持表格和样式 |
| Markdown | 纯文本格式，适合版本控制和在线查看 |

#### 📦 网络抓包分析

| 特性 | 说明 |
|------|------|
| tshark 自动解析 | 支持 PCAP/PCAPNG 格式，自动提取协议字段 |
| 协议统计 | TCP/UDP/HTTP/DNS 等协议层级统计 |
| 流量分析 | 识别异常流量模式，生成诊断建议 |
| LLM 诊断 | 结合大模型进行协议级问题诊断 |

#### 👥 多用户隔离

| 特性 | 说明 |
|------|------|
| 用户 ID 隔离 | 基于 `X-User-Id` 请求头实现数据隔离 |
| 独立存储空间 | 每个用户拥有独立的报告和检查点目录 |
| 任务管理 | 支持任务状态查询、历史记录查看 |
| 操作日志 | 完整记录用户操作和系统事件 |

#### ⚡ 规则模式

| 特性 | 说明 |
|------|------|
| 零成本 | 不调用外部 API，无费用产生 |
| 极速响应 | <1 秒处理 1000 条日志 |
| 预定义规则 | 内置常见错误模式识别规则 |
| 可扩展 | 支持自定义错误分类和根因识别规则 |

#### 🗂️ 服务器路径读取

| 特性 | 说明 |
|------|------|
| 路径选择器 | 直观的服务器文件/目录选择界面 |
| 权限控制 | 支持配置可访问的目录列表 |
| 多文件扫描 | 自动扫描目录下符合条件的日志和 PCAP 文件 |
| 后台处理 | 任务自动在后台运行，支持进度查询 |

### 1.3 解决的痛点

| 痛点 | 解决方案 |
|------|----------|
| 100MB+ 日志肉眼无法逐行排查 | 流式分块 + 内存映射 + LLM/规则智能聚合 |
| 错误模式难发现 | 内置错误模式识别 + LLM 语义归纳 / 规则匹配 |
| 多文件交叉对比低效 | 综合报告自动生成 + 跨文件趋势识别 |
| 网络抓包分析门槛高 | tshark 自动化解析 + 协议统计 + LLM 诊断 |
| 团队数据相互干扰 | 基于 `X-User-Id` 的用户隔离存储 |
| LLM 调用成本高 | 规则模式零成本，极速响应 |
| 频繁上传大文件麻烦 | 直接读取服务器指定路径下的文件 |

---

## 二、技术栈

| 分类 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 主语言 | Python | 3.10+ | 核心业务逻辑 |
| Web 框架 | FastAPI | 0.100+ | RESTful API 服务 |
| 异步运行时 | uvicorn | 0.20+ | ASGI 服务器 |
| 前端 | HTML/CSS/JavaScript | - | Web 界面 |
| 数据库 | 本地 JSON | - | 任务状态存储 |
| PDF 生成 | ReportLab | 4.0+ | PDF 报告生成 |
| Word 生成 | python-docx | 0.8+ | Word 报告生成 |
| 网络分析 | tshark | 4.0+ | PCAP 文件解析 |
| HTTP 客户端 | httpx | 0.24+ | LLM API 调用 |

---

## 三、项目结构

```
log_analyzer/
├── __init__.py                 # 包初始化
├── main.py                     # CLI 主入口
│
├── config/                     # 配置管理
│   ├── __init__.py
│   ├── settings.py             # 全局配置
│   └── config.json             # 默认配置
│
├── parser/                     # 日志解析器
│   ├── __init__.py
│   └── log_parser.py           # 多格式日志解析
│
├── processor/                  # 核心处理器
│   ├── __init__.py
│   ├── chunk_processor.py      # 日志分块处理（核心流程）
│   └── pcap_processor.py       # 网络抓包处理
│
├── llm/                        # LLM 客户端
│   ├── __init__.py
│   └── client.py               # LLM API 调用、并发控制、重试机制
│
├── report/                     # 报告生成器
│   ├── __init__.py
│   ├── generator.py            # 报告生成（PDF/Word/Markdown/HTML）
│   ├── error_merger.py         # 智能错误合并
│   └── rule_based_analyzer.py  # 规则模式分析器
│
├── checkpoint/                 # 断点续传
│   ├── __init__.py
│   └── manager.py              # 检查点管理
│
├── web/                        # Web 服务
│   ├── __init__.py
│   ├── app.py                  # FastAPI 应用（路由、API）
│   ├── auth.py                 # 用户认证与授权
│   ├── action_logger.py        # 操作日志记录
│   ├── storage.py              # 数据存储管理
│   ├── start.sh                # 启动脚本
│   └── static/                 # 前端静态文件
│       └── index.html          # 主页面
│
├── docs/                       # 文档
│   ├── USER_GUIDE.md           # 用户使用手册
│   ├── DEVELOPER_GUIDE.md      # 开发者指南
│   ├── RULE_MODE_GUIDE.md      # 规则模式指南
│   ├── API.md                  # API 文档
│   ├── CHANGELOG.md            # 更新日志
│   ├── QUICK_REFERENCE.md      # 快速参考
│   ├── PROMPTS.md              # LLM 提示词库
│   └── PROJECT_OVERVIEW.md     # 项目概述
│
├── tests/                      # 测试用例
│   ├── performance/
│   └── test_*.py
│
├── users/                      # 用户数据（运行时生成）
│   └── {user_id}/
│       ├── reports/            # 用户报告
│       └── checkpoints/        # 用户检查点
│
├── tasks/                      # 任务状态（运行时生成）
├── logs/                       # 系统日志（运行时生成）
├── requirements.txt            # 依赖列表
└── README.md                   # 项目说明
```

---

## 四、快速开始

### 4.1 环境要求

- Python 3.10+
- pip 23+
- tshark（可选，用于网络抓包分析）

### 4.2 安装依赖

```bash
# 1. 进入项目目录
cd log_analyzer

# 2. （推荐）创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt
```

### 4.3 配置管理

配置文件位于 `config/config.json`：

```json
{
  "llm": {
    "api_url": "https://api.example.com/v1/chat/completions",
    "model_name": "qwen3-235b-a22b",
    "api_key": "",
    "backup_model": "deepseek-v3.2"
  },
  "processing": {
    "chunk_size": 10000,
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "app": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false
  },
  "security": {
    "max_file_size_mb": 500,
    "max_files_per_request": 10
  },
  "server_paths": {
    "allowed_directories": []
  }
}
```

**敏感信息**：创建 `config/config.local.json` 存储敏感信息（已添加到 `.gitignore`）。

**服务器路径配置**：在 `server_paths.allowed_directories` 中配置允许用户访问的目录列表。如果为空，则不限制访问权限。

### 4.4 启动 Web 服务

```bash
cd web
bash start.sh
```

启动后访问 [http://localhost:8000](http://localhost:8000)

### 4.5 主要功能使用

#### 4.5.1 上传文件分析

1. 点击「选择文件」或拖拽文件到上传区域
2. 选择分块大小（行数）
3. 选择是否使用 LLM 模式
4. 点击「开始分析」

#### 4.5.2 从服务器路径读取

1. 点击「从服务器路径读取」
2. 在弹窗中浏览并选择目录或文件
3. 确认选择并点击「开始分析」
4. 在任务列表中查看处理进度

#### 4.5.3 查看历史记录

1. 切换到「历史记录」标签
2. 查看所有用户的分析任务
3. 支持按状态、用户、时间筛选
4. 点击任务查看详情和下载报告

#### 4.5.4 查看操作日志

1. 切换到「操作日志」标签
2. 查看系统和用户的操作记录
3. 支持筛选和搜索

---

## 五、两种分析模式对比

| 维度 | LLM 模式 | 规则模式 |
|------|----------|----------|
| 分析深度 | 深度语义分析 | 规则匹配分析 |
| 响应速度 | 5-30 秒/1000 条 | <1 秒/1000 条 |
| 成本 | 有 API 调用成本 | 零成本 |
| 网络依赖 | 需要 | 不需要 |
| 适用场景 | 复杂问题诊断 | 快速批量分析 |
| 分析结果 | 自然语言总结 | 结构化报告 |
| 根因分析 | 深度推断 | 关键词匹配 |
| 建议质量 | 高（上下文感知） | 中等（模板化） |

---

## 六、文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 用户手册 | `docs/USER_GUIDE.md` | 详细使用说明 |
| 开发者指南 | `docs/DEVELOPER_GUIDE.md` | 二次开发参考 |
| 规则模式 | `docs/RULE_MODE_GUIDE.md` | 规则模式详细说明 |
| API 文档 | `docs/API.md` | API 接口文档 |
| 更新日志 | `docs/CHANGELOG.md` | 版本更新记录 |
| 快速参考 | `docs/QUICK_REFERENCE.md` | 常用功能速查 |
| 提示词库 | `docs/PROMPTS.md` | LLM 提示词管理 |

---

## 七、许可证

MIT License