# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- 数据库存储后端（PostgreSQL / SQLite）
- 集群部署支持
- LLM 调用成本统计与限制
- 报告订阅与定期分析
- 实时流式日志接入（Kafka / Syslog）

---

## [2.5.2] - 2026-06-05

### Added
- **跨平台部署脚本**：
  - 新建 `scripts/install.sh`、`scripts/install.bat`、`scripts/start.sh`、`scripts/start.bat`、`scripts/build.sh`
  - 支持一键安装依赖和启动服务
  - 支持 Linux/macOS/Windows 跨平台部署
  - 添加 `scripts/README.md` 说明文档

- **打包工具**：
  - 新建 `scripts/build.sh` 一键打包脚本
  - 自动生成版本化压缩包
  - 自动排除运行时生成的文件

### Changed
- **LLM 配置统一管理**：
  - 删除独立的 `llmconfig` 文件
  - 将 LLM 配置迁移到 `config/config.json`
  - 更新所有引用的代码文件
  - 更新文档说明

- **PDF 报告优化**：
  - 优化趋势识别部分的展示格式
  - 优化故障时间线的表格展示
  - 添加事件类型图标标识（首次异常、错误峰值、恢复、故障确认）
  - 使用中文字段名替代英文字段名

- **项目结构优化**：
  - 将启动脚本集中到 `scripts/` 目录
  - 更新 `DEPLOY.md` 部署指南
  - 更新 `.gitignore` 配置

### Removed
- 删除独立的 `llmconfig` 配置文件

---

## [2.5.1] - 2026-06-04

### Added
- **提示词库管理文档**：
  - 新建 `docs/PROMPTS.md`，汇总并优化所有 LLM 提示词
  - 包含日志分析提示词和 PCAP 网络分析提示词
  - 提供提示词设计原则和维护建议

### Changed
- **文档精简与整合**：
  - 删除冗余和临时文档：SUMMARY.md、Architecture_Refactoring_Plan.md、Code_Comparison_and_Improvements.md、LANGCHAIN_COMPARISON_EVALUATION.md、QUICKSTART_SERVER_PATH.md、SERVER_PATH_SINGLE_API.md、history_records_postman_collection.json、server_path_feature.md、table_schema.md
  - 更新 README.md，将分散的文档内容整合
  - 保留核心文档：USER_GUIDE.md、DEVELOPER_GUIDE.md、RULE_MODE_GUIDE.md、API.md、CHANGELOG.md、QUICK_REFERENCE.md、PROMPTS.md、PROJECT_OVERVIEW.md

- **API 文档优化**：
  - 优化目录结构，添加接口中文名称和路径
  - 删除 `/api/read-path` 接口（功能已被 `/api/list-dir` 替代）
  - 完善 username 参数说明，明确其仅用于界面显示
  - 更新接口变更说明

### Fixed
- **路径读取任务处理逻辑修复**：
  - 修复 `process_files_from_path` 函数中的 Logger 变量名错误：logger → task_logger
  - 完全重构路径任务处理流程，与上传文件处理流程保持一致
  - 正确初始化 ChunkProcessor，包含 parser、checkpoint_manager、enable_checkpoint 等参数
  - 支持 PCAP 文件处理逻辑，与上传功能一致
  - 修复报告保存路径问题，使用正确的 ReportGenerator 初始化

---

## [2.5.0] - 2026-06-04

### Added
- **操作日志埋点功能**：
  - 文件上传时记录 `file_upload` 操作
  - 任务开始时记录 `task_start` 操作
  - 任务完成时记录 `task_complete` 操作
  - 任务失败时记录 `task_failed` 操作
  - 日志存储路径：`data/action_logs/{user_id}/{date}.json`

- **通用API请求函数**：
  - 新增 `apiRequest()` 函数，自动设置用户请求头
  - 所有API调用统一使用，确保身份一致性
  - 支持Content-Type和自定义headers

- **操作日志查询接口增强**：
  - `/api/history/actions`：所有用户可查询所有用户的操作记录
  - `/api/history/actions/count`：返回按用户和操作类型的统计信息
  - 支持按时间范围、操作类型筛选

### Changed
- **权限优化**：
  - 移除历史报告接口的管理员权限限制
  - 所有用户可以查看和管理自己的历史报告
  - 操作日志查询和统计对所有用户开放
  - 历史报告列表接口 `/api/reports` 统一为用户级权限

- **日志文件命名规则**：
  - 普通任务日志：`web_process_YYYYMMDD_HHMMSS_文件名.log`
  - 路径任务日志：`web_path_YYYYMMDD_HHMMSS_文件名.log`
  - 普通报告：`report_【文件名】_时间戳.html`
  - 路径报告：`report_path_【文件名】_时间戳.html`

- **前端界面优化**：
  - 功能卡片区域标题从"管理员功能"改为"数据查询"
  - 操作日志、操作统计等功能对所有用户可见
  - 描述文本更新，明确功能范围

### Fixed
- 修复 `/api/reports` 接口的权限判断逻辑
- 修复任务处理函数中的埋点调用
- 修复前端API请求头设置不一致问题

---

## [2.4.0] - 2026-06-03

### Added
- **规则模式日志分析器**：
  - 新建 `report/rule_based_analyzer.py` 模块，实现不依赖 LLM 的日志分析功能
  - 多层次错误分类：Critical、High、Medium、Low 四个严重级别
  - 根本原因识别：支持 8 种根本原因类型（null_reference、resource_leak、timeout 等）
  - 智能建议生成：基于错误类型和根本原因自动生成修复建议
  - 统计分析：支持错误级别分布、错误类型、高频类等统计
  - 兼容 LLM 格式：输出与 `AnalysisResult` 完全兼容，可无缝集成
- **ChunkProcessor 改造**：
  - 新增 `use_llm` 参数，支持在 LLM 模式和规则模式间切换
  - 默认值为 `True`，保持向后兼容
  - 规则模式下完全跳过 LLM 调用，降低成本
  - 支持并行处理和串行处理两种模式
- **API 接口更新**：
  - `/api/process` 接口新增 `use_llm` 参数
  - 用户可选择不依赖 LLM 直接进行分析并生成报告
  - 保持与现有 API 的完全兼容
- **测试用例**：
  - 新建 `tests/test_rule_based_analyzer.py`，包含 7 个测试类
  - 新建 `tests/test_rule_based_standalone_v2.py`，独立验证脚本
  - 覆盖错误分类、错误分析、结果转换、性能测试等场景
- **文档**：
  - 新建 `docs/RULE_BASED_ANALOGER.md`，详细说明规则模式功能

### Changed
- **导入优化**：使用延迟导入避免循环依赖问题
- **类型支持增强**：规则分析器同时支持字典和对象格式的日志条目

### Advantages
- **无需 LLM**：不依赖外部 LLM 服务，完全离线工作
- **极速响应**：处理 1000 条日志在 1 秒内完成
- **零成本**：无需 API 调用费用
- **轻量级**：内存占用小，适合资源受限环境
- **可预测**：结果完全由规则决定，无随机性

### Limitations
- 语义理解能力有限
- 上下文理解能力弱于 LLM
- 建议的精准度可能不如 LLM

---

## [2.3.0] - 2026-06-02

### Added
- **智能错误合并功能**：
  - 新建 `report/error_merger.py` 模块，实现多层次错误合并策略
  - 精确匹配去重：完全相同的错误记录只保留一条
  - 语义相似合并：使用编辑距离算法识别相似错误
  - 模式匹配合并：自动提取消息模式，去除动态内容（UUID、IP、数字、路径等）
  - 可配置合并规则：支持调整相似度阈值、最大组数、示例数等参数
  - 保留关键上下文：合并时保留原始错误引用、影响类列表、示例消息
- **预设合并配置**：
  - `DEFAULT_CONFIG`：标准配置（相似度阈值 0.8）
  - `STRICT_CONFIG`：严格模式（只合并完全相同的错误）
  - `LENIENT_CONFIG`：宽松模式（更多合并）
- **报告生成器集成**：`report/generator.py` 集成智能合并功能，优化错误分析章节
- **单元测试**：新建 `tests/test_intelligent_error_merger.py`，覆盖精确匹配、语义相似、模式匹配、性能测试等场景
- **文档更新**：更新 README.md、PROJECT_OVERVIEW.md、USER_GUIDE.md、DEVELOPER_GUIDE.md

### Changed
- **错误分析章节优化**：报告中错误分析部分现在展示合并后的错误组，减少重复内容
- **性能优化**：处理 1000+ 错误日志时，合并操作在 10 秒内完成

### Fixed
- 模式提取功能错误：调整正则表达式顺序，先处理复杂模式（UUID、IP）再处理简单数字替换
- 语义相似度合并测试失败：优化测试用例，使用更相似的错误消息

---

## [2.2.0] - 2026-06-02

### Added
- **PCAP提示词优化**：
  - 新增网络安全分析专家角色定义
  - 强化协议识别、异常检测、证据链等专业分析维度
  - 规范JSON输出格式，确保程序可解析
  - 新增9章节报告结构：基础信息概览、连接生命周期分析、流量特征分析、协议识别与分析、异常行为检测、关键问题清单、优化建议、预期收益评估、证据链
- **报告结构优化**：
  - 日志分析报告结构统一：处理概览、统计分析、错误分析、趋势识别与故障时间线、根因分析、处置与整改建议、总体摘要
  - 合并相关章节，逻辑更清晰、层次更分明
  - 修复PDF格式转换问题，确保与Word/MD格式一致性
- **路径读取功能**：
  - 新增 `POST /api/read-path` 端点：直接从服务器路径读取日志文件
  - 新增 `POST /api/process-from-path` 端点：从路径读取并分析日志
  - 实现路径安全验证（防遍历、防越权、白名单控制）
  - 支持目录递归扫描与文件过滤
  - 支持文件预览功能
  - 与现有上传功能平行互补，完善日志处理工作流
- **项目文档完善**：
  - 新增 `docs/PROJECT_OVERVIEW.md`：项目全面综述文档
  - 新增 `tests/TEST_SUMMARY.md`：测试结果总结
  - 更新 README：优化文档索引结构

### Changed
- **PCAP处理器**：`processor/pcap_processor.py` 新增专业提示词生成方法
- **报告生成器**：`report/generator.py` 优化章节合并逻辑
- **项目结构优化**：
  - 移除临时/冗余文件（`modify_client.py`、`optimized_prompt.md` 等）
  - 完善 `.gitignore` 规则
  - 精简测试套件，保留核心测试

### Fixed
- PCAP提示词JSON格式语法错误（`protocol_behavior: {}` → `protocol_behavior: {{}}`）
- Markdown到PDF转换中表格、代码块、中文标点显示异常问题

---

## [2.1.0] - 2026-06-02

### Added
- **前端页面刷新恢复机制**：
  - `buildTaskUrl(taskId)` 工具函数构建 `http://localhost:8000/api/task/{task_id}` 格式 URL
  - localStorage 持久化活动任务信息
  - 页面加载时自动检测并恢复任务监控
  - 指数退避重连策略（1s → 5s，最多 10 次）
  - 重新连接横幅 UI（连接中/重试中/失败三种状态）
- **文件结构整理**：
  - 移动 `performance_test.py` 与 `performance_report.txt` → `tests/performance/`
  - 移动 `web_server.py` → `tests/scripts/`
  - 移动 `web_server.log` → `tests/logs/`
  - 移动 `debug-upload-file-error.md` → `docs/debug/upload-file-error.md`
  - 新增 `.gitignore`（Python / macOS / IDE / Runtime 规则）
  - 清理 `__pycache__` 与 `.DS_Store`
- **完整文档体系**：
  - 新增 `docs/USER_GUIDE.md`（用户使用手册）
  - 新增 `docs/DEVELOPER_GUIDE.md`（开发者指南）
  - 新增 `docs/CHANGELOG.md`（本文件）
  - 新增 `docs/architecture_analysis.md`（架构设计文档）
  - 重写 `README.md`（全面项目介绍）
  - 扩展 `docs/architecture_analysis.md`（新增用户隔离与存储抽象章节）
- **架构文档**：
  - 第十二章：用户隔离机制（v2.0 新增）
  - 第十三章：报告存储抽象层
  - 第十四章：PCAP 网络抓包分析增强
  - 第十五章：版本演进路线

### Changed
- **前端 `index.html`**：用 `pollTaskUntilDone` 替换原 `waitForTask`
  - 主动轮询替代 `setInterval`
  - 失败时重置延迟（指数退避）
  - 任务完成/失败时自动清理 localStorage
- **README.md**：完全重写，新增项目结构、快速开始、配置参数、性能指标

### Fixed
- 上传文件未带 `X-User-Id` 头部时身份识别失败（参考 `docs/debug/upload-file-error.md`）

---

## [2.0.0] - 2026-06-01

### Added
- **用户隔离机制**（基于 `X-User-Id` 请求头）：
  - 移除 Token 鉴权流程
  - 引入 `get_current_user()` 依赖注入
  - 用户档案 `auth/users.json`
  - 数据按 `user_id` 隔离到 `users/{user_id}/`
- **历史报告 CRUD**：
  - `POST /api/history/reports` 创建
  - `GET /api/history/reports` 列表（支持搜索）
  - `GET /api/history/reports/{id}` 详情
  - `PUT /api/history/reports/{id}` 更新
  - `DELETE /api/history/reports/{id}` 删除
- **报告存储抽象层**：
  - `ReportStorage` 抽象基类
  - `FileReportStorage` 文件实现
  - `DatabaseReportStorage` 数据库实现（预留）
  - 工厂方法 `get_storage()`
- **数据备份与恢复**：
  - `POST /api/backup/create`
  - 备份目录 `data/backups/{user_id}_{timestamp}/`
- **目录浏览**：
  - `GET /api/list-directory`
  - `GET /api/download/{path}`
- **统一响应格式**：`{code, message, data}`
- **PCAP 抓包分析增强**：
  - 协议统计（TCP/UDP/HTTP/DNS）
  - TCP 标志位分布
  - LLM 流量诊断

### Changed
- **架构重构**：
  - 新增 `web/auth.py`（用户识别）
  - 新增 `web/storage.py`（存储抽象）
  - `web/app.py` 重构为依赖注入风格
- **API 文档**：完全重写 `docs/API.md`
  - v2.0 简化认证版
  - 12 章节，含数据隔离方案

### Performance
- 历史报告查询：< 100ms（文件存储）
- 数据备份：< 5s（10 个报告 / 用户）

---

## [1.8.0] - 2026-05-28

### Added
- **断点续传**：
  - 基于文件 SHA256 哈希的检查点
  - 中断后从断点恢复
  - 支持强制重处理
- **检查点批量保存**：
  - 每 5 个 chunk 批量持久化
  - 减少 I/O 操作
- **历史报告列表**：`GET /api/reports`
- **进程日志自动命名**：按源文件命名日志

### Changed
- **性能优化**：
  - 检查点写入从 1 次/chunk 优化为 1 次/5 chunks
  - 日志命名规则从固定名改为动态

### Fixed
- 大文件处理中意外中断后无法恢复

---

## [1.5.0] - 2026-05-25

### Added
- **并行处理**：
  - `asyncio.gather` 并发调用 LLM
  - 可配置 `parallel_workers`（默认 4）
- **批量异步 LLM 调用**：
  - `LLMClient.batch_analyze(chunks_data, max_concurrent)`
  - `asyncio.Semaphore` 控制并发
- **性能测试脚本**：`performance_test.py`

### Changed
- **解析器优化**：
  - 预编译正则 `LOG_PATTERN`
  - LRU 缓存 `from_string()` / `_parse_timestamp()`
  - `dataclass(slots=True)` 减少内存
- **处理流水线**：
  - `parse_file_stream_mmap` 流式解析
  - 内存映射替代逐行读取
- **报告生成**：
  - 移除 `pattern` 字段（避免误判）
  - 优化汇总生成逻辑

### Performance
- 100MB 文件处理时间：**78s → 40s**（48.7% 提升）
- 解析时间：**~2s → 0.14s**（93% 提升）
- 内存占用：**~500MB → ~200MB**（60% 下降）

---

## [1.1.0] - 2026-05-22

### Added
- **Web 界面**：
  - 单页应用（HTML + CSS + JS）
  - 苹果风格设计
  - 拖拽上传
  - 进度可视化（4 阶段）
- **FastAPI 应用**：
  - `/api/upload` 文件上传
  - `/api/process` 提交任务
  - `/api/task/{id}` 任务状态
- **CLI 模式**：`main.py`
  - `--file` / `--dir` 参数
  - `--resume` 断点续传
  - `--force-restart` 强制重处理

### Changed
- 启动脚本 `web/start.sh`：
  - 4 worker 进程
  - 每进程 200 并发
  - 等待队列 2048

---

## [1.0.0] - 2026-05-20

### Added
- 基础日志分块处理
- LLM API 集成（OpenAI 兼容）
- JSON / Markdown 报告生成
- 错误模式识别（8 种内置）
- 多线程处理框架

---

## 版本对照表

| 版本 | 主要变化 | 关键指标 |
|------|----------|----------|
| 2.3.0 | 智能错误合并 | 支持 1000+ 错误合并 |
| 2.2.0 | PCAP增强 + 报告优化 | 9章节专业报告结构 |
| 2.1.0 | 刷新恢复 + 文档体系 | 完整文档 |
| 2.0.0 | 用户隔离 + 历史报告 | 21 个 API 路由 |
| 1.8.0 | 断点续传 | 检查点批量保存 |
| 1.5.0 | 性能优化 | 100MB 处理 40s |
| 1.1.0 | Web UI | FastAPI + 单页应用 |
| 1.0.0 | MVP | CLI + LLM 集成 |

---

## 升级指南

### 从 1.x 升级到 2.0

**破坏性变更**：

1. 移除 Token 鉴权
2. 客户端必须发送 `X-User-Id` 头（或使用 `default_user`）
3. 文件路径需从 `uploads/` 迁移到 `users/{user_id}/uploads/`

**迁移脚本**：

```python
# migrate_v1_to_v2.py
import shutil
from pathlib import Path

for file in Path("uploads").glob("*"):
    user_id = "default_user"
    target = Path(f"users/{user_id}/uploads/{file.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, target)
```

### 从 2.1 升级到 2.2

**兼容升级**，无破坏性变更。

### 从 2.2 升级到 2.3

**兼容升级**，无破坏性变更。

**新增功能**：
- 智能错误合并功能自动启用
- API `/api/process` 新增 `merge_config` 参数用于自定义合并策略
- 环境变量支持配置合并参数（见 USER_GUIDE.md）

---

[Unreleased]: https://example.com/log-analyzer/compare/v2.1.0...HEAD
[2.1.0]: https://example.com/log-analyzer/compare/v2.0.0...v2.1.0
[2.0.0]: https://example.com/log-analyzer/compare/v1.8.0...v2.0.0
[1.8.0]: https://example.com/log-analyzer/compare/v1.5.0...v1.8.0
[1.5.0]: https://example.com/log-analyzer/compare/v1.1.0...v1.5.0
[1.1.0]: https://example.com/log-analyzer/compare/v1.0.0...v1.1.0
[1.0.0]: https://example.com/log-analyzer/releases/tag/v1.0.0
