# Log Analyzer 用户使用手册

> 版本: v2.0 | 适用: 运维工程师 / SRE / 后端开发
>
> 最后更新: 2026-06-02

---

## 目录

1. [快速开始](#1-快速开始)
2. [Web 界面使用](#2-web-界面使用)
3. [CLI 命令行使用](#3-cli-命令行使用)
4. [任务状态与刷新恢复](#4-任务状态与刷新恢复)
5. [多用户协作](#5-多用户协作)
6. [报告下载与管理](#6-报告下载与管理)
7. [常见问题 FAQ](#7-常见问题-faq)

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
│  Settings:   分块大小 / 强制重处理       │
│  Actions:    开始分析 / 清除选择         │
│  Reconnect:  刷新恢复任务监控（见 §4）   │
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

> **建议**：1GB 文件推荐分块 500,000~1,000,000；小文件可适当减少。

### 2.4 进度阶段

```
📋 文件准备 → 📝 日志解析 → 🤖 AI 分析 → 📊 报告生成
```

- ✅ 灰色：未开始
- 🔵 蓝色高亮：进行中
- ✓ 绿色打勾：已完成

---

## 3. CLI 命令行使用

### 3.1 基本用法

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

### 3.2 完整参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--file` | 单个日志文件 | `--file /var/log/app.log` |
| `--dir` | 日志目录 | `--dir /var/log/app/` |
| `--config` | LLM 配置路径 | `--config /path/to/llmconfig` |
| `--output` | 报告输出目录 | `--output ./reports/` |
| `--checkpoint-dir` | 检查点目录 | `--checkpoint-dir ./checkpoints/` |
| `--chunk-size` | 分块行数 | `--chunk-size 500000` |
| `--merge-threshold` | 合并阈值 | `--merge-threshold 5` |
| `--resume` | 断点续传 | `--resume` |
| `--force-restart` | 强制重处理 | `--force-restart` |
| `--no-checkpoint` | 禁用检查点保存 | `--no-checkpoint` |
| `--format` | 输出格式 | `--format json` / `--format markdown` / `--format both` |
| `--max-retries` | LLM 重试次数 | `--max-retries 5` |
| `--retry-delay` | 重试间隔（秒） | `--retry-delay 1.5` |
| `--log-dir` | 日志目录 | `--log-dir ./logs/` |
| `--list-files` | 列出可用日志文件并退出 | `--list-files` |

### 3.3 典型场景示例

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

## 4. 任务状态与刷新恢复

> v2.0 重要特性：支持页面刷新后自动恢复任务监控。

### 4.1 工作原理

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

### 4.2 任务 URL 格式

`{API_BASE}/api/task/{task_id}`

示例：
```
http://localhost:8000/api/task/hanmeimei_20260602_022001_987023
```

其中 `task_id` 由服务端按 `{user_id}_{YYYYMMDD_HHMMSS}_{6位随机}` 规则生成。

### 4.3 状态轮询机制

| 状态 | 轮询间隔 | 重连策略 |
|------|----------|----------|
| 正常 | 1 秒 | 立即恢复 |
| 失败 | 1.5 → 2.25 → 3.4 → 5 秒 | 最多 10 次 |
| 失败超过限制 | 终止 | 提示用户手动重连 |

### 4.4 状态视觉反馈

| 状态 | 视觉提示 |
|------|----------|
| 已恢复任务 | 顶部蓝色横幅 + 旋转图标 |
| 监控中 | 进度条 + 阶段指示 + 状态文本 |
| 重新连接中 | 橙色横幅 + "重试 X/10" |
| 重新连接失败 | 橙色横幅 + 重新连接按钮 |
| 任务完成 | 绿色横幅（1.2 秒后消失） |

### 4.5 触发场景

| 场景 | 是否自动恢复 | 备注 |
|------|--------------|------|
| 浏览器刷新 | ✅ 是 | 通过 localStorage |
| 关闭再打开浏览器 | ✅ 是 | localStorage 持久 |
| 切换到其他用户 | ⚠️ 提示 | 检测到 user_id 不一致 |
| 服务端重启 | ✅ 是 | 服务端任务仍存在 |
| 网络中断 | ✅ 自动重连 | 指数退避 |

### 4.6 主动取消

如需放弃正在进行的任务，刷新页面后点击重新连接按钮（如果横幅显示）不会取消任务。如需彻底取消：

```bash
# CLI 模式：直接 Ctrl+C
# Web 模式：等待任务完成（无显式取消接口）
```

---

## 5. 多用户协作

### 5.1 用户识别原理

```
客户端 JS → 设置 localStorage[logAnalyzer.userId] = "alice"
                    ↓
所有 API 请求头 X-User-Id: alice
                    ↓
服务端 FastAPI 依赖注入 get_current_user() 解析
                    ↓
所有路径操作带 user_id = "alice"
```

### 5.2 切换用户

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

### 5.3 数据隔离验证

| 操作 | 用户 A | 用户 B |
|------|--------|--------|
| 上传日志 | `users/A/uploads/` | `users/B/uploads/` |
| 生成报告 | `users/A/reports/` | `users/B/reports/` |
| 历史记录 | `data/reports_db/A/` | `data/reports_db/B/` |

### 5.4 用户档案

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

## 6. 报告下载与管理

### 6.1 自动生成的格式

| 格式 | 文件后缀 | 用途 |
|------|----------|------|
| Markdown | .md | 版本控制、Markdown 编辑器 |
| HTML | .html | 浏览器直接打开（响应式） |
| PDF | .pdf | 打印、归档 |
| Word | .docx | 二次编辑 |
| JSON | .json | 程序化处理 |

### 6.2 单次报告

分析完成后，Web 界面会显示：

```
┌──────────────────────────────────────┐
│  📝 日志分析报告                      │
│  15.2 KB · 2026-06-02 02:20         │
│                              [下载]  │
└──────────────────────────────────────┘
```

### 6.3 历史报告管理

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

### 6.4 数据备份

```bash
curl -H "X-User-Id: alice" -X POST \
     http://localhost:8000/api/backup/create
```

备份目录：`data/backups/{user_id}_{timestamp}/`

---

## 7. 常见问题 FAQ

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
2. 调用 `/api/upload` 上传日志
3. 调用 `/api/process` 提交任务
4. 轮询 `/api/task/{task_id}` 获取进度
5. 通过 `/api/reports` 或 `/api/download/{path}` 拉取报告

### Q10: 是否支持集群部署？

当前版本为单机部署，集群支持计划在 v3.0 引入。临时方案：

- 多机部署多个实例，共享 LLM API 配额
- 使用 Nginx 做负载均衡
- 历史报告暂未做集中存储（需自行迁移到 DB）

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

如有问题，请在 `docs/debug/` 目录下记录并提交 issue。
