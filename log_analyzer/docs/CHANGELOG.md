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

## [2.2.0] - 2026-06-02

### Added
- **PCAP提示词优化**：
  - 新增网络安全分析专家角色定位
  - 强化协议识别、异常行为检测、证据链等专业分析维度
  - 规范JSON输出格式，确保程序可解析
  - 新增9章报告结构：基础信息概览、连接生命周期分析、流量特征分析、协议识别与分析、异常行为检测、关键问题清单、优化建议、预期收益评估、证据链
- **报告结构优化**：
  - 日志分析报告结构统一：处理概览、统计分析、错误分析、趋势识别与故障时间线、根因分析、处置与整改建议、总体摘要
  - 合并相关章节，逻辑更清晰、层次更分明
  - 修复PDF格式转换问题，确保与Word/MD格式一致性

### Changed
- **PCAP处理器**：`processor/pcap_processor.py` 新增专业提示词生成方法
- **报告生成器**：`report/generator.py` 优化章节合并逻辑

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

### 从 2.0 升级到 2.1

**兼容升级**，无破坏性变更。前端自动兼容老版本 API。

---

[Unreleased]: https://example.com/log-analyzer/compare/v2.1.0...HEAD
[2.1.0]: https://example.com/log-analyzer/compare/v2.0.0...v2.1.0
[2.0.0]: https://example.com/log-analyzer/compare/v1.8.0...v2.0.0
[1.8.0]: https://example.com/log-analyzer/compare/v1.5.0...v1.8.0
[1.5.0]: https://example.com/log-analyzer/compare/v1.1.0...v1.5.0
[1.1.0]: https://example.com/log-analyzer/compare/v1.0.0...v1.1.0
[1.0.0]: https://example.com/log-analyzer/releases/tag/v1.0.0
