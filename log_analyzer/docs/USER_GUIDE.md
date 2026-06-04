# Log Analyzer 用户使用手册

> 版本: v2.5 | 适用: 运维工程师 / SRE / 后端开发
>
> 最后更新: 2026-06-03

---

## 目录

1. [快速开始](#1-快速开始)
2. [Web 界面使用](#2-web-界面使用)
3. [服务器路径读取](#3-服务器路径读取)
4. [CLI 命令行使用](#4-cli-命令行使用)
5. [任务状态与刷新恢复](#5-任务状态与刷新恢复)
6. [多用户协作](#6-多用户协作)
7. [报告下载与管理](#7-报告下载与管理)
8. [常见问题 FAQ](#8-常见问题-faq)

---

## 1. 快速开始

### 1.1 启动服务

```bash
cd log_analyzer
bash web/start.sh
```

启动后访问 [http://localhost:8000](http://localhost:8000)。

### 1.2 上传第一个日志

1. 打开浏览器访问主页
2. 在 **上传文件** 标签页，将日志文件拖到上传区
3. 默认 `X-User-Id = hanmeimei`（自动写入 localStorage）
4. 点击 **开始分析**

### 1.3 查看报告

分析完成后可：

- 在主页面 **报告生成** 区域直接下载
- 切换到 **历史报告** 标签查看所有历史记录
- 直接访问磁盘：`users/hanmeimei/reports/`

---

## 2. Web 界面使用

### 2.1 界面分区

```
┌─────────────────────────────────────────┐
│  Header: Log Analyzer + 副标题           │
├─────────────────────────────────────────┤
│  Tabs: 上传文件 | 历史报告               │
├─────────────────────────────────────────┤
│  Upload Area: 拖拽 / 点击上传           │
│  Server Path: 从服务器路径读取按钮       │
│  Settings:   分块大小 / 强制重处理       │
│  Actions:    开始分析 / 清除选择         │
│  Reconnect:  刷新恢复任务监控（见 §5）   │
│  Progress:   4 阶段进度条 + 状态文本     │
│  Reports:    本次报告下载               │
└─────────────────────────────────────────┘
```

### 2.2 上传方式

| 方式 | 操作 | 支持格式 |
|------|------|----------|
| 点击 | 点击上传区域选择文件 | .log .txt .zip .pcap |
| 拖放 | 直接拖到上传区域 | 同上 |
| ZIP | 上传后自动解压到同目录 | 解压后内含日志 |

### 2.3 处理配置

| 配置项 | 默认 | 范围 | 说明 |
|--------|------|------|------|
| 分块大小 | 10,000 | 10,000 - 10,000,000 | 每块行数 |
| 强制重处理 | ❌ | - | 忽略检查点重新分析 |
| 使用 LLM 分析 | ✅ | - | 取消则使用规则模式 |

> **建议**：1GB 文件推荐分块 500,000~1,000,000；小文件可适当减少。

### 2.4 分析模式选择

系统支持两种分析模式：

#### LLM 模式（默认）
- **特点**：使用大语言模型进行深度语义分析
- **优势**：支持复杂问题诊断、自然语言总结
- **适用场景**：复杂问题诊断、深度分析
- **响应时间**：5-30 秒/1000 条日志

#### 规则模式
- **特点**：使用预定义规则进行快速分析
- **优势**：零成本、极速响应、离线可用
- **适用场景**：批量日志快速扫描、日常监控、CI/CD 集成
- **响应时间**：<1 秒/1000 条日志

**切换方式**：在上传区域取消勾选"使用 LLM 分析"复选框即可切换到规则模式。

**模式对比**：

| 指标 | LLM 模式 | 规则模式 |
|------|----------|----------|
| 语义理解 | 强 | 有限 |
| 响应时间 | 5-30秒/1000条 | <1秒/1000条 |
| API 成本 | 有 | 无 |
| 网络依赖 | 需要 | 不需要 |
| 分析深度 | 高 | 中等 |

### 2.5 进度阶段

```
📋 文件准备 → 📝 日志解析 → 🤖 AI 分析 → 📊 报告生成
```

- ✅ 灰色：未开始
- 🔵 蓝色高亮：进行中
- ✓ 绿色打勾：已完成

---

## 3. 服务器路径读取

### 3.1 功能概述

服务器路径读取功能允许您直接从服务器上的指定目录读取日志文件，无需手动上传。该功能通过权限控制确保安全性，并提供直观的交互界面。

### 3.2 功能入口

在 **上传文件** 标签页中，点击上传区域右侧的 **"🖥️ 从服务器路径读取"** 按钮。

### 3.3 使用流程

#### 方法一：手动输入路径

1. 点击入口按钮，打开配置模态框
2. 在输入框中输入服务器路径（如 `/var/log/nginx/error.log`）
3. 点击 **"验证"** 按钮验证路径有效性
4. 验证通过后，点击 **"开始分析"**

#### 方法二：浏览选择路径

1. 点击入口按钮，打开配置模态框
2. 点击 **"浏览"** 按钮打开目录浏览器
3. 在目录树中导航选择目标路径
4. 点击 **"选择此路径"** 确认选择
5. 系统自动验证路径
6. 点击 **"开始分析"**

### 3.4 高级选项

点击 **"高级选项"** 展开配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 递归读取子目录 | 开启 | 如果路径是目录，将读取所有子目录中的文件 |
| 文件匹配模式 | `*.log` | 支持多个模式，用逗号分隔（如 `*.log, *.txt`） |
| 最大文件大小 | 500MB | 超过此大小的文件将被跳过 |

### 3.5 权限说明

系统默认允许访问以下目录：

- `/var/log` - 系统日志目录
- `/opt/logs` - 应用日志目录
- `/tmp` - 临时目录
- `/home` - 用户目录

如需添加其他目录，请联系管理员编辑 `web/app.py` 配置文件。

### 3.6 验证结果

| 状态 | 视觉提示 | 说明 |
|------|----------|------|
| ✅ 成功 | 绿色提示横幅 | 显示检测到的文件数量 |
| ❌ 失败 | 红色提示横幅 | 显示具体错误原因 |

### 3.7 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| 路径不在允许访问的目录范围内 | 路径不在白名单中 | 使用允许的目录或联系管理员 |
| 路径不存在 | 输入的路径不存在 | 检查路径拼写或使用浏览功能 |
| 没有读取路径的权限 | 系统权限不足 | 检查文件权限或联系管理员 |

### 3.8 最佳实践

#### ✅ 推荐做法

1. **使用绝对路径**：避免相对路径导致的权限问题
2. **先验证后处理**：点击"验证"确认路径有效
3. **限制递归深度**：大目录建议关闭递归选项
4. **设置文件大小限制**：避免处理超大文件
5. **使用浏览功能**：对于不确定的路径，使用"浏览"功能选择

#### ❌ 避免做法

1. 直接输入 `/etc` 等系统目录（不在白名单中）
2. 处理未经验证的路径
3. 在大型目录上开启递归（如 `/`）
4. 忽略文件大小限制

### 3.9 技术架构

#### 前端
- **模态框交互**：点击按钮打开配置窗口
- **目录浏览**：树形结构导航
- **实时验证**：输入路径后即时反馈
- **文件预览**：显示匹配的文件列表

#### 后端
- **单一路由**：`POST /api/list-dir` 统一处理
- **权限验证**：白名单机制确保安全
- **文件匹配**：`fnmatch` 模块实现通配符
- **安全检查**：路径解析、存在性检查、权限验证

---

## 4. CLI 命令行使用

### 4.1 基本用法

```bash
# 处理单个文件
python main.py --file /path/to/error.log

# 处理目录下所有日志
python main.py --dir /path/to/logs

# 断点续传
python main.py --file /path/to/error.log --resume

# 强制重新处理
python main.py --file /path/to/error.log --force-restart

# 限制输出格式
python main.py --file /path/to/error.log --format json
```

### 4.2 完整参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--file` | 单个日志文件 | `--file /var/log/app.log` |
| `--dir` | 日志目录 | `--dir /var/log/app/` |
| `--config` | LLM 配置路径 | `--config /path/to/llmconfig` |
| `--output` | 报告输出目录 | `--output ./reports/` |
| `--checkpoint-dir` | 检查点目录 | `--checkpoint-dir ./checkpoints/` |
| `--chunk-size` | 分块行数 | `--chunk-size 500000` |
| `--merge-threshold` | 分块合并阈值 | `--merge-threshold 5` |
| `--resume` | 断点续传 | `--resume` |
| `--force-restart` | 强制重处理 | `--force-restart` |
| `--no-checkpoint` | 禁用检查点保存 | `--no-checkpoint` |
| `--format` | 输出格式 | `--format json` / `--format markdown` / `--format both` |
| `--max-retries` | LLM 重试次数 | `--max-retries 5` |
| `--retry-delay` | 重试间隔（秒） | `--retry-delay 1.5` |
| `--log-dir` | 日志目录 | `--log-dir ./logs/` |
| `--list-files` | 列出可用日志文件并退出 | `--list-files` |

### 4.3 智能错误合并配置

系统支持智能错误合并功能，可通过环境变量或配置文件调整合并策略：

**环境变量配置**：

```bash
# 设置语义相似度阈值（0-1，越高越严格）
export MERGE_SEMANTIC_THRESHOLD=0.75

# 设置每组最大示例数
export MERGE_MAX_EXAMPLES=3

# 设置最大错误组数
export MERGE_MAX_GROUPS=10

# 是否启用语义合并
export MERGE_ENABLE_SEMANTIC=true

# 是否按错误类型分组
export MERGE_BY_TYPE=true

# 是否按消息模式分组
export MERGE_BY_PATTERN=true
```

**合并策略说明**：

| 策略 | 说明 | 效果 |
|------|------|------|
| **精确匹配去重** | 完全相同的错误记录只保留一条 | 消除重复内容 |
| **语义相似合并** | 使用编辑距离算法识别相似错误 | 合并同类错误 |
| **模式匹配合并** | 提取消息模式，去除动态内容 | 识别变体错误 |

**配置示例场景**：

```bash
# 严格模式：只合并完全相同的错误
export MERGE_SEMANTIC_THRESHOLD=1.0
export MERGE_ENABLE_SEMANTIC=false

# 宽松模式：更多合并
export MERGE_SEMANTIC_THRESHOLD=0.6
export MERGE_MAX_GROUPS=30

# 标准模式（默认）
export MERGE_SEMANTIC_THRESHOLD=0.75
export MERGE_MAX_EXAMPLES=3
```

**模式提取规则**：
- UUID → `[UUID]`
- IP地址 → `[IP]`
- 文件路径 → `[PATH]`
- 引号内容 → `[STR]`
- 数字 → `[NUM]`

例如，以下错误消息会被识别为相同模式：
- `"Connection timeout after 30000ms"` → `"Connection timeout after [NUM]ms"`
- `"Connection timeout after 20000ms"` → `"Connection timeout after [NUM]ms"`

### 4.4 典型场景示例

#### 场景 1：分析 500MB 错误日志

```bash
python main.py --file /var/log/error.log.2026-05-26 \
    --chunk-size 500000 \
    --format markdown \
    --output ./reports/
```

#### 场景 2：批量处理多日日志

```bash
python main.py --dir /var/log/app/2026-05/ \
    --format markdown \
    --output ./monthly-reports/
```

#### 场景 3：中断后恢复

```bash
# 程序意外退出后，重新运行相同命令
python main.py --file /var/log/big.log --resume
# 自动从断点继续
```

---

## 5. 任务状态与刷新恢复

> v2.0 重要特性：支持页面刷新后自动恢复任务监控。

### 5.1 工作原理

```
启动任务 → 保存 task_id 到 localStorage → 轮询任务状态
                                ↓
                          页面刷新
                                ↓
                  init() 检测 localStorage
                                ↓
            buildTaskUrl(taskId) → 重新发起轮询
                                ↓
                       继续显示进度直至完成
```

### 5.2 任务 URL 格式

`{API_BASE}/api/task/{task_id}`

示例：
```
http://localhost:8000/api/task/hanmeimei_20260602_022001_987023
```

其中 `task_id` 由服务端按 `{user_id}_{YYYYMMDD_HHMMSS}_{6位随机}` 规则生成。

### 5.3 状态轮询机制

| 状态 | 轮询间隔 | 重连策略 |
|------|----------|----------|
| 正常 | 1 秒 | 立即恢复 |
| 失败 | 1.5 → 2.25 → 3.4 → 5 秒 | 最多 10 次 |
| 失败超过限制 | 终止 | 提示用户手动重连 |

### 5.4 状态视觉反馈

| 状态 | 视觉提示 |
|------|----------|
| 已恢复任务 | 顶部蓝色横幅 + 旋转图标 |
| 监控中 | 进度条 + 阶段指示 + 状态文本 |
| 重新连接中 | 橙色横幅 + "重试 X/10" |
| 重新连接失败 | 橙色横幅 + 重新连接按钮 |
| 任务完成 | 绿色横幅（1.2 秒后消失） |

### 5.5 触发场景

| 场景 | 是否自动恢复 | 备注 |
|------|--------------|------|
| 浏览器刷新 | ✅ 是 | 通过 localStorage |
| 关闭再打开浏览器 | ✅ 是 | localStorage 持久 |
| 切换到其他用户 | ⚠️ 提示 | 检测到 user_id 不一致 |
| 服务端重启 | ✅ 是 | 服务端任务仍存在 |
| 网络中断 | ✅ 自动重连 | 指数退避 |

### 5.6 主动取消

如需放弃正在进行的任务，刷新页面后点击重新连接按钮（如果横幅显示）不会取消任务。如需彻底取消：

```bash
# CLI 模式：直接 Ctrl+C
# Web 模式：等待任务完成（无显式取消接口）
```

---

## 6. 多用户协作

### 6.1 用户识别原理

```
客户端 JS → 设置 localStorage[logAnalyzer.userId] = "alice"
                    ↓
所有 API 请求头 X-User-Id: alice
                    ↓
服务端 FastAPI 依赖注入 get_current_user() 解析
                    ↓
所有路径操作带 user_id = "alice"
```

### 6.2 切换用户

#### 浏览器 1 - 开发者

```javascript
// 浏览器 Console
localStorage.setItem('logAnalyzer.userId', 'dev_alice');
location.reload();
```

#### 浏览器 2 - 测试者

```javascript
localStorage.setItem('logAnalyzer.userId', 'test_bob');
location.reload();
```

#### Curl 调用

```bash
curl -H "X-User-Id: ci_pipeline" http://localhost:8000/api/reports
```

### 6.3 数据隔离验证

| 操作 | 用户 A | 用户 B |
|------|--------|--------|
| 上传日志 | `users/A/uploads/` | `users/B/uploads/` |
| 生成报告 | `users/A/reports/` | `users/B/reports/` |
| 历史记录 | `data/reports_db/A/` | `data/reports_db/B/` |

### 6.4 用户档案

每个用户首次访问自动创建：

```json
{
  "user_id": "alice",
  "username": "Alice",
  "created_at": "2026-06-01T10:00:00"
}
```

存储于 `auth/users.json`。

---

## 7. 报告下载与管理

### 7.1 自动生成的格式

| 格式 | 文件后缀 | 用途 |
|------|----------|------|
| Markdown | .md | 版本控制、Markdown 编辑器 |
| HTML | .html | 浏览器直接打开（响应式） |
| PDF | .pdf | 打印、归档 |
| Word | .docx | 二次编辑 |
| JSON | .json | 程序化处理 |

### 7.2 单次报告

分析完成后，Web 界面会显示：

```
┌──────────────────────────────────────┐
│  📝 日志分析报告                      │
│  15.2 KB · 2026-06-02 02:20         │
│                              [下载]  │
└──────────────────────────────────────┘
```

### 7.3 历史报告管理

通过 `历史报告` 标签访问，支持：

- 列表浏览
- 关键词搜索（标题/文件名/摘要）
- 下载报告文件
- CRUD 管理（通过 API）

```bash
# API 列表查询
curl -H "X-User-Id: alice" http://localhost:8000/api/history/reports

# API 关键词搜索
curl -H "X-User-Id: alice" "http://localhost:8000/api/history/reports?keyword=error"

# API 删除
curl -H "X-User-Id: alice" -X DELETE \
     http://localhost:8000/api/history/reports/rpt_20260601_143000_abc12345
```

### 7.4 数据备份

```bash
curl -H "X-User-Id: alice" -X POST \
     http://localhost:8000/api/backup/create
```

备份目录：`data/backups/{user_id}_{timestamp}/`

---

## 8. 常见问题 FAQ

### Q1: 上传后没有任何反应？

**A:** 检查浏览器 Console，确认：

- 请求头 `X-User-Id` 未正确传递，或浏览器本地缓存未写入用户 ID
- 文件类型不在 [.log, .txt, .zip, .pcap] 中
- 文件大小超过 500MB（默认限制）

### Q2: LLM 调用一直超时？

**A:** 排查步骤：

1. 检查 `llmconfig` 文件的 API Key 是否有效
2. 验证网络：`curl $API_URL -H "Authorization: Bearer $API_KEY"`
3. 减少 `--chunk-size` 或改用更小的分块数
4. 增加 `--max-retries 5 --retry-delay 2`

### Q3: 任务卡在某个阶段？

**A:** 查看 `logs/` 目录下的进程日志：

```bash
ls -lt logs/*.log | head -5
tail -f logs/web_process_*.log
```

### Q4: 报告里没有错误模式识别？

**A:** 确认：

- 文件确实包含 ERROR/FATAL 级别日志
- LLM 正常返回结果（查看进度阶段的"AI 分析"）
- 日志格式被识别（自定义格式可能需要适配）

### Q5: 如何清空所有用户数据？

```bash
rm -rf users/* data/reports_db/* data/backups/*
```

### Q6: PCAP 文件怎么分析？

1. **上传 .pcap 文件**：在上传区域选择或拖放 .pcap 文件
2. **确认系统已安装 `tshark`**：

```bash
# macOS
brew install wireshark

# Ubuntu/Debian
sudo apt install tshark
```

3. **启动分析**：系统自动调用 tshark 解析流量并生成分析报告

**PCAP分析报告包含**：
- **基础信息概览**：分析日期、抓包文件标识、流量概览、通信矩阵、协议分布
- **连接生命周期分析**：TCP握手分析、连接状态追踪、链路质量评估
- **流量特征分析**：流量分布、包大小分析、TCP窗口分析
- **协议识别与分析**：协议分类统计、协议行为分析、特殊协议识别（如ASTERIX航空监控协议）
- **异常行为检测**：连接异常、流量异常、协议异常、安全风险
- **关键问题清单**：按严重程度分级列出问题及根因分析
- **优化建议**：分优先级给出具体可落地的优化方案
- **证据链**：支撑分析结论的关键数据包证据

### Q7: 页面刷新后任务状态丢失？

**A:** v2.0 已支持。检查：

- 浏览器是否禁用 localStorage
- 隐身模式（localStorage 关闭后清除）
- Console 错误：`localStorage.setItem` 失败

### Q8: 并发上限是多少？

| 配置 | 默认 | 推荐 |
|------|------|------|
| Worker 进程 | 4 | 4-8 (CPU 核数) |
| 每进程并发 | 200 | 100-200 |
| LLM 并发 | 4 | 4-8 |

理论峰值 QPS = 4 × 200 = 800 req/s。

### Q9: 如何集成到自己的系统？

1. 调用 `/api/auth/identify` 注册用户
2. 调用 `/api/upload` 上传日志（或使用 `/api/list-dir` 从服务器路径读取）
3. 调用 `/api/process` 或 `/api/process-from-path` 提交任务
4. 轮询 `/api/task/{task_id}` 获取进度
5. 通过 `/api/reports` 或 `/api/download/{path}` 拉取报告

### Q10: 是否支持集群部署？

当前版本为单机部署，集群支持计划在 v3.0 引入。临时方案：

- 多机部署多个实例，共享 LLM API 配额
- 使用 Nginx 做负载均衡
- 历史报告暂未做集中存储（需自行迁移到 DB）

### Q11: 服务器路径读取功能支持哪些目录？

**A:** 系统默认允许访问以下目录：
- `/var/log` - 系统日志目录
- `/opt/logs` - 应用日志目录
- `/tmp` - 临时目录
- `/home` - 用户目录

如需添加其他目录，请联系管理员编辑 `web/app.py` 中的 `ALLOWED_DIRECTORIES` 配置。

### Q12: 服务器路径验证失败怎么办？

**A:** 请检查：
1. 路径是否正确拼写
2. 路径是否在允许的目录范围内
3. 是否有读取该路径的系统权限
4. 可以尝试使用"浏览"功能选择路径

---

## 附录 A：快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl/Cmd + U` | 触发文件上传 |
| `Esc` | 关闭错误提示 |
| `Ctrl/Cmd + R` | 刷新（会触发任务恢复） |

## 附录 B：日志位置

| 类别 | 路径 |
|------|------|
| 进程日志 | `logs/web_process_*.log` |
| 业务日志 | `logs/web_*.log` |
| 错误日志 | `logs/web_error_*.log` |
| 用户上传 | `users/{user_id}/uploads/` |
| 用户报告 | `users/{user_id}/reports/` |
| 用户检查点 | `users/{user_id}/checkpoints/` |
| 历史报告 | `data/reports_db/{user_id}/` |
| 备份 | `data/backups/{user_id}_{timestamp}/` |

---

## 附录 C：服务器路径读取 API

### 单一接口

```
POST /api/list-dir
```

### 请求参数

```json
{
  "path": "/var/log/nginx",
  "recursive": false,
  "file_patterns": ["*.log"],
  "validate_only": true
}
```

### 响应示例

**验证模式**：
```json
{
  "code": 0,
  "message": "路径验证成功",
  "data": {
    "path": "/var/log/nginx",
    "is_directory": true,
    "file_count": 5,
    "files": [...]
  }
}
```

**浏览模式**：
```json
{
  "code": 0,
  "message": "获取成功",
  "data": {
    "current_path": "/var/log/nginx",
    "parent_path": "/var/log",
    "files": [...]
  }
}
```

---

如有问题，请在 `docs/debug/` 目录下记录并提交 issue。
