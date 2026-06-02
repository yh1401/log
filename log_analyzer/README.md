# Log Analyzer

> 基于 LLM 的大规模日志分析与网络抓包分析系统
>
> 版本: v2.2 | 最后更新: 2026-06-02

---

## 一、项目概述

### 1.1 项目定位

**Log Analyzer** 是一个面向运维工程师、SRE 团队和后端开发人员的**智能日志分析平台**。它通过调用大语言模型（LLM），对传统的海量应用日志和网络抓包文件进行**结构化分析、错误聚合、根因推断和整改建议生成**。

系统解决了以下核心痛点：

| 痛点 | 解决方案 |
|------|----------|
| 100MB+ 日志肉眼无法逐行排查 | 流式分块 + 内存映射 + LLM 智能聚合 |
| 错误模式难发现 | 内置 8 类错误模式识别 + LLM 语义归纳 |
| 多文件交叉对比低效 | 综合报告自动生成 + 跨文件趋势识别 |
| 网络抓包分析门槛高 | tshark 自动化解析 + 协议统计 + LLM 诊断 |
| 团队数据相互干扰 | 基于 `X-User-Id` 的用户隔离存储 |

### 1.2 核心能力

- **日志智能分析**：支持 GB 级日志文件，错误模式识别、故障时间线、根因推断、运维/开发双视角建议
- **PCAP 抓包分析**：基于 tshark 的网络协议解析、TCP 标志位统计、LLM 流量诊断
- **多格式报告导出**：Markdown、HTML、PDF、Word、JSON 多种格式（已实现 `reportlab`/`python-docx` 输出）
- **多用户数据隔离**：基于 `X-User-Id` 请求头识别身份，所有数据按用户隔离
- **历史报告持久化**：可对历史报告进行 CRUD、搜索、备份与恢复
- **断点续传**：大文件处理支持中断后从断点恢复
- **高并发支持**：默认配置支持 50+ QPS，可水平扩展

---

## 二、技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.10+ | 主开发语言 |
| Web 框架 | FastAPI 0.109+ | HTTP API 与异步处理 |
| ASGI 服务器 | Uvicorn | 4 worker 进程，支持高并发 |
| 异步 I/O | asyncio + httpx | 异步 LLM 调用与 HTTP 请求 |
| 文件 I/O 优化 | mmap + aiofiles | 大文件流式读取 |
| LLM 客户端 | httpx | 兼容 OpenAI / DeepSeek / Qwen / 自定义 |
| PDF 生成 | ReportLab | PDF 报告生成 |
| Word 生成 | python-docx | Word 报告生成 |
| 数据校验 | Pydantic | API 数据模型 |
| 日志框架 | Python logging | 进程日志（含按文件自动命名） |
| 前端 | 原生 HTML/CSS/JS | 零依赖单页应用 |

---

## 三、项目结构

```
log_analyzer/
├── main.py                       # CLI 入口（命令行日志分析）
├── web/                          # Web 服务模块
│   ├── app.py                    # FastAPI 主应用
│   ├── auth.py                   # 用户识别（无 Token 鉴权版）
│   ├── storage.py                # 报告存储抽象层（文件 + DB 预留）
│   ├── start.sh                  # 启动脚本
│   └── static/
│       └── index.html            # 前端单页应用
├── config/                       # 配置管理
│   ├── __init__.py
│   └── settings.py               # LLM/处理配置加载
├── parser/                       # 日志解析
│   ├── __init__.py
│   └── log_parser.py             # 日志条目解析（mmap + LRU 缓存）
├── processor/                    # 处理核心
│   ├── __init__.py
│   ├── chunk_processor.py        # 日志分块处理（并行 LLM 调用）
│   └── pcap_processor.py         # PCAP 抓包分析（tshark）
├── llm/                          # LLM 客户端
│   ├── __init__.py
│   └── client.py                 # LLM API 封装（重试 + 并发控制）
├── report/                       # 报告生成
│   ├── __init__.py
│   └── generator.py              # 多格式报告生成器
├── checkpoint/                   # 断点管理
│   ├── __init__.py
│   └── manager.py                # 断点保存/恢复
├── utils/                        # 工具函数
│   ├── __init__.py
│   └── helpers.py                # 哈希、进度、JSON 读写
├── docs/                         # 项目文档
│   ├── API.md                    # API 接口文档
│   ├── USER_GUIDE.md             # 用户使用手册
│   ├── DEVELOPER_GUIDE.md        # 开发者指南
│   ├── architecture_analysis.md  # 架构设计文档
│   ├── CHANGELOG.md              # 变更日志
│   ├── PERFORMANCE_ANALYSIS_REPORT.md  # 性能优化报告
│   ├── table_schema.md           # 数据表结构设计
│   └── debug/                    # 调试记录
│       └── upload-file-error.md
├── tests/                        # 测试代码
│   ├── performance/              # 性能测试
│   │   ├── performance_test.py
│   │   └── performance_report.txt
│   ├── scripts/                  # 测试辅助脚本
│   │   └── web_server.py
│   ├── logs/                     # 测试运行日志
│   ├── e2e/                      # 端到端测试（test_complete_e2e.py）
│   └── *.py, *.sh                # 单元/集成测试脚本
├── auth/                         # 用户与 Token（运行时）
├── users/                        # 用户隔离数据（每用户一个目录）
│   └── {user_id}/
│       ├── uploads/              # 用户上传文件
│       ├── reports/              # 用户报告
│       └── checkpoints/          # 用户检查点
├── data/                         # 持久化数据
│   ├── reports_db/               # 历史报告 DB（按用户ID分目录）
│   └── backups/                  # 数据备份
├── uploads/                      # 全局上传文件（兼容性保留）
├── reports/                      # 全局报告（兼容性保留）
├── checkpoints/                  # 全局检查点（兼容性保留）
├── logs/                         # 进程运行日志
├── .dbg/                         # 调试会话环境
├── requirements.txt              # 依赖列表
├── README.md                     # 本文件
└── .gitignore                    # Git 忽略配置
```

---

## 四、快速开始

### 4.1 环境要求

- Python 3.10 及以上（推荐 3.11/3.12）
- macOS / Linux 操作系统
- 如需 PCAP 分析，需安装 `tshark`（Wireshark 命令行工具）

### 4.2 安装依赖

```bash
# 1. 进入项目目录
cd log_analyzer

# 2. （推荐）创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 4.3 配置 LLM

编辑 LLM 配置文件（默认路径：`/Users/a666/Documents/trae_projects/log/loggen/llm/llmconfig`）：

```
# 第1行：API URL
https://api.openai.com/v1/chat/completions

# 第2行：模型名称
gpt-4o-mini

# 第3行：API Key
sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 第4行（可选）：备用模型
gpt-3.5-turbo
```

### 4.4 启动 Web 服务

```bash
cd log_analyzer
bash web/start.sh
```

启动参数：
- `--workers 4`：4 个工作进程
- `--limit-concurrency 200`：每进程最大 200 并发
- `--backlog 2048`：等待队列长度

服务地址：
- 主页：http://localhost:8000
- Swagger API：http://localhost:8000/docs

### 4.5 CLI 模式

```bash
# 处理单个日志文件
python main.py --file /path/to/error.log

# 处理目录下所有日志
python main.py --dir /path/to/logs

# 断点续传
python main.py --file /path/to/error.log --resume

# 强制重新处理
python main.py --file /path/to/error.log --force-restart

# 只生成 JSON 报告
python main.py --file /path/to/error.log --format json
```

---

## 五、核心功能模块

### 5.1 日志分析流水线

```
原始日志文件 (.log/.txt)
    ↓
LogParser（流式解析 + 内存映射）
    ↓ ParsedLogEntry[]
ChunkProcessor（按行分块 + 合并策略）
    ↓ List[LogChunk]
LLMClient（异步批量分析 + 重试）
    ↓ List[AnalysisResult]
ReportGenerator（多格式输出）
    ↓
JSON / Markdown / HTML / PDF / Word 报告
```

### 5.2 PCAP 抓包分析流水线

```
PCAP 文件
    ↓
PCAPProcessor（调用 tshark）
    ↓ PCAPStatistics + List<PCAPPacket>
LLMClient（基于分析模板诊断）
    ↓
PCAP 分析报告（Markdown / HTML / JSON）
```

### 5.3 用户隔离机制

系统采用**轻量级身份识别**方案：

```
客户端请求 → Header `X-User-Id` → 后端 get_current_user() → 数据按 user_id 隔离
```

- 无需登录：首次访问自动创建用户档案
- 无 Token 验证：后端直接信任 `X-User-Id` 头
- 严格隔离：所有上传、报告、检查点按 `user_id` 目录隔离

### 5.4 错误模式识别

内置 8 类错误模式（`parser/log_parser.py`）：

| 模式 | 严重度 | 触发条件示例 |
|------|--------|--------------|
| device_offline | high | 设备不在线 |
| permission_denied | high | 无权限、Access Denied |
| null_pointer | critical | NullPointerException |
| timeout | medium | 超时、Connection timeout |
| validation_error | medium | 参数错误、id不能为空 |
| database_error | high | SQLException、数据库异常 |
| network_error | medium | Connect refused、网络异常 |
| authentication_error | high | 认证失败、Token invalid |

### 5.5 LLM 集成

- **多供应商支持**：自动识别 OpenAI / DeepSeek / Qwen / 自定义
- **异步批量分析**：`batch_analyze()` 通过 `asyncio.Semaphore` 控制并发
- **重试机制**：指数退避，自动切换备用模型
- **断点续传**：检查点文件保存处理进度

### 5.6 报告生成

每次处理完成后自动生成 4-5 种格式（HTML/Markdown/PDF/Word/JSON）：

| 格式 | 用途 | 实现 |
|------|------|------|
| Markdown | 版本控制、快速查看 | 原生 |
| HTML | 网页浏览、在线分享 | 苹果风格响应式 |
| PDF | 打印归档 | ReportLab |
| Word | 二次编辑 | python-docx |
| JSON | 程序化处理 | 原生 |

---

## 六、关键业务流程

### 6.1 Web 端分析流程

1. 用户通过前端上传文件（支持 .log/.txt/.zip/.pcap）
2. 文件保存到 `users/{user_id}/uploads/`
3. 调用 `/api/process` 提交分析任务，返回 `task_id`
4. 后台异步执行 `process_log_files`：
   - 解析文件 → 分块 → 调用 LLM → 生成报告
5. 前端轮询 `/api/task/{task_id}` 获取进度
6. 完成后自动调用存储抽象层持久化历史报告

### 6.2 CLI 端分析流程

1. `python main.py --file <path>` 启动分析
2. 初始化 LLM 客户端、解析器、检查点管理器、报告生成器
3. 逐个处理文件，支持断点续传
4. 输出进度条与实时日志
5. 最终生成报告文件

### 6.3 报告管理流程

```
/api/history/reports (CRUD)
   ↓
FileReportStorage
   ↓
data/reports_db/{user_id}/rpt_*.json + _index.json
```

---

## 七、API 概览

详细接口文档参见 [docs/API.md](docs/API.md)。

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 健康检查 | `/api/health` | GET | 服务健康状态 |
| 用户识别 | `/api/auth/identify` | POST | 创建/获取用户 |
| 当前用户 | `/api/auth/current` | GET | 获取当前用户信息 |
| 文件上传 | `/api/upload` | POST | 上传日志/抓包 |
| 目录列表 | `/api/list-directory` | GET | 列出用户目录 |
| 文件下载 | `/api/download/{path}` | GET | 下载报告文件 |
| 开始处理 | `/api/process` | POST | 提交分析任务 |
| 任务状态 | `/api/task/{task_id}` | GET | 查询任务进度 |
| 报告列表 | `/api/reports` | GET | 列出报告文件 |
| 历史报告 | `/api/history/reports` | CRUD | 历史报告管理 |
| 数据备份 | `/api/backup/create` | POST | 备份用户数据 |

---

## 八、用户标识说明

所有需要识别用户的接口都依赖以下请求头：

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-User-Id` | 否 | 用户业务 ID（缺省 `default_user`） |
| `X-Username` | 否 | 用户名（仅显示用，可选） |

示例：

```bash
curl -H "X-User-Id: alice" http://localhost:8000/api/reports
```

---

## 九、配置参数

启动参数（`web/start.sh`）：

```bash
uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \              # 工作进程数
    --limit-concurrency 200 \  # 每进程并发上限
    --backlog 2048 \           # 等待队列
    --timeout-keep-alive 30    # 长连接超时
```

性能调优建议（`processor/chunk_processor.py`）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 10000 | 每个 chunk 的行数 |
| `parallel_workers` | 4 | LLM 并发数（建议 4-8） |
| `merge_threshold` | 5 | 分块数 ≤ 此值时合并为单次调用 |
| `enable_checkpoint` | True | 是否启用断点续传 |
| `max_retries` | 3 | LLM 调用失败重试次数 |
| `retry_delay` | 1.0 | 重试基础延迟（秒） |

---

## 十、性能指标

100MB 测试文件（`error.2026-05-26.48.log`，1,114,360 行）：

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 总耗时 | 78s | 40s | 48.7% |
| 解析耗时 | ~2s | 0.14s | 93% |
| LLM 耗时 | ~76s | ~39s | 48.7% |
| 内存占用 | ~500MB | ~200MB | 60% |

详细优化报告：[docs/PERFORMANCE_ANALYSIS_REPORT.md](docs/PERFORMANCE_ANALYSIS_REPORT.md)

---

## 十一、相关文档

- [用户使用手册](docs/USER_GUIDE.md)
- [API 接口文档](docs/API.md)
- [架构设计文档](docs/architecture_analysis.md)
- [开发者指南](docs/DEVELOPER_GUIDE.md)
- [数据表结构设计](docs/table_schema.md)
- [性能优化报告](docs/PERFORMANCE_ANALYSIS_REPORT.md)
- [变更日志](docs/CHANGELOG.md)

---

## 十二、许可证

MIT License
