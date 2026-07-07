---
name: log-analyzer
description: "智能日志文件分析工具，支持LLM和规则双模式。用于日志分析、错误诊断、PCAP文件处理等场景。"
---

# Log Analyzer Skill - 日志分析组件

这是一个功能强大的智能日志分析组件，提供日志文件处理、错误检测、根因分析和报告生成等完整功能。支持LLM深度分析和规则快速分析两种模式。

## 何时使用此组件

在以下场景中使用此组件：
- 用户需要分析日志文件（.log、.txt、.zip、.pcap）
- 用户需要识别错误及其根本原因
- 用户需要生成分析报告（PDF、Word、Markdown、HTML）
- 用户需要处理网络抓包文件（PCAP）
- 用户询问日志分析、错误诊断或系统故障排查
- 用户提到"日志分析"、"错误检测"、"根因分析"、"PCAP分析"等关键词

## 核心功能

### 1. 双模式分析

| 模式 | 说明 | 速度 | 成本 | 适用场景 |
|------|------|------|------|----------|
| **LLM模式** | 使用大语言模型进行深度语义分析 | 5-30秒/千行 | 有API调用成本 | 复杂问题诊断 |
| **规则模式** | 使用预定义规则进行快速模式匹配 | <1秒/千行 | 免费 | 批量扫描、实时监控 |

### 2. 支持的文件类型

| 类型 | 扩展名 | 功能 |
|------|--------|------|
| 日志文件 | `.log`、`.txt` | 多格式解析、流式处理 |
| 压缩包 | `.zip` | 自动解压、批量处理 |
| 网络抓包 | `.pcap`、`.pcapng` | 协议分析、流量统计 |

### 3. 错误检测

支持检测8类错误：
- 空引用错误
- 资源泄漏
- 超时错误
- 认证失败
- 数据库错误
- 网络问题
- 配置错误
- 内存问题

### 4. 报告生成

支持多种格式的报告生成：
- **PDF**：格式化文档，支持中文排版
- **Word**：可编辑文档，支持表格和样式
- **Markdown**：纯文本格式，适合版本控制
- **HTML**：网页格式，支持预览

## API参考

### 基础URL
```
http://localhost:8000
```

### 通用请求头

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-User-Id` | 否 | 用户ID，用于数据隔离（默认：`default_user`） |
| `X-User-Name` | 否 | 用户显示名称 |
| `Content-Type` | 是 | `application/json` 或 `multipart/form-data` |

### 响应格式

```json
{
    "code": 0,
    "message": "成功",
    "data": { ... }
}
```

### 接口列表

#### 1. 上传文件

```http
POST /api/upload
Content-Type: multipart/form-data

file: <文件>
```

**响应示例：**
```json
{
    "code": 0,
    "message": "上传成功",
    "data": {
        "file_path": "/users/user_001/uploads/error.log",
        "file_name": "error.log",
        "file_size": "10.5 KB"
    }
}
```

#### 2. 开始分析

```http
POST /api/process
Content-Type: application/json

{
    "file_path": "/path/to/log/file.log",
    "source": "upload",
    "chunk_size": 50000,
    "use_llm": true,
    "force_restart": false
}
```

**参数说明：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file_path` | string | 是 | - | 文件或目录路径 |
| `source` | string | 否 | `upload` | `upload`（上传）或 `server`（服务器路径） |
| `chunk_size` | int | 否 | 50000 | 处理块大小（行数） |
| `use_llm` | bool | 否 | true | 是否使用LLM模式（false为规则模式） |
| `force_restart` | bool | 否 | false | 是否强制重启现有任务 |

**响应示例：**
```json
{
    "code": 0,
    "message": "任务已创建",
    "data": {
        "task_id": "user_001_20260601_100000_123456",
        "status": "pending"
    }
}
```

#### 3. 获取任务状态

```http
GET /api/task/{task_id}
```

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "task_id": "user_001_20260601_100000_123456",
        "status": "processing",
        "progress": 50.0,
        "message": "正在分析日志...",
        "current_file": "error.log"
    }
}
```

**任务状态说明：**
- `pending`：任务已创建，等待开始
- `processing`：正在处理中
- `completed`：处理完成
- `failed`：处理失败
- `cancelled`：任务已取消

#### 4. 取消任务

```http
POST /api/task/{task_id}/cancel
```

#### 5. 获取报告列表

```http
GET /api/reports
```

**响应示例：**
```json
{
    "code": 0,
    "data": {
        "reports": [
            {
                "name": "report_error.log_20260601_100000.md",
                "size": 10240,
                "modified": "2026-06-01T10:00:00",
                "type": "markdown"
            }
        ]
    }
}
```

#### 6. 下载报告

```http
GET /api/report/download/{report_name}
```

#### 7. 服务器路径浏览

```http
POST /api/list-dir
Content-Type: application/json

{
    "path": "/var/log",
    "recursive": false,
    "file_patterns": ["*.log"],
    "validate_only": false
}
```

**参数说明：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | string | 是 | - | 目录或文件路径 |
| `recursive` | bool | 否 | false | 是否递归读取子目录 |
| `file_patterns` | array | 否 | `["*.log"]` | 文件匹配模式 |
| `validate_only` | bool | 否 | false | 是否仅验证路径，不列出文件 |

#### 8. 健康检查

```http
GET /api/health
```

## 使用示例

### 示例1：上传并分析日志文件（LLM模式）

```python
import requests

# 1. 上传文件
with open('error.log', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f},
        headers={'X-User-Id': 'user_001'}
    )
file_path = response.json()['data']['file_path']

# 2. 开始分析
response = requests.post(
    'http://localhost:8000/api/process',
    json={
        'file_path': file_path,
        'source': 'upload',
        'use_llm': True
    },
    headers={'X-User-Id': 'user_001'}
)
task_id = response.json()['data']['task_id']

# 3. 轮询任务状态
import time
while True:
    response = requests.get(
        f'http://localhost:8000/api/task/{task_id}',
        headers={'X-User-Id': 'user_001'}
    )
    status = response.json()['data']['status']
    if status in ['completed', 'failed', 'cancelled']:
        break
    time.sleep(2)

# 4. 获取报告
response = requests.get(
    'http://localhost:8000/api/reports',
    headers={'X-User-Id': 'user_001'}
)
reports = response.json()['data']['reports']
```

### 示例2：分析服务器路径（规则模式）

```python
import requests

# 1. 验证路径
response = requests.post(
    'http://localhost:8000/api/list-dir',
    json={
        'path': '/var/log/nginx',
        'validate_only': True
    },
    headers={'X-User-Id': 'user_001'}
)

# 2. 使用规则模式开始分析
response = requests.post(
    'http://localhost:8000/api/process',
    json={
        'file_path': '/var/log/nginx/error.log',
        'source': 'server',
        'use_llm': False  # 规则模式
    },
    headers={'X-User-Id': 'user_001'}
)
task_id = response.json()['data']['task_id']
```

### 示例3：取消运行中的任务

```python
import requests

response = requests.post(
    f'http://localhost:8000/api/task/{task_id}/cancel',
    headers={'X-User-Id': 'user_001'}
)
```

### 示例4：下载报告

```python
import requests

response = requests.get(
    'http://localhost:8000/api/report/download/report_error.log_20260601_100000.pdf',
    headers={'X-User-Id': 'user_001'}
)

with open('analysis_report.pdf', 'wb') as f:
    f.write(response.content)
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LOG_ANALYZER_HOST` | 服务器地址 | `0.0.0.0` |
| `LOG_ANALYZER_PORT` | 服务器端口 | `8000` |
| `LOG_ANALYZER_LLM_API_URL` | LLM API地址 | - |
| `LOG_ANALYZER_LLM_API_KEY` | LLM API密钥 | - |
| `LOG_ANALYZER_LLM_MODEL` | LLM模型名称 | `qwen3-235b-a22b` |

### 配置文件

配置文件位于 `log_analyzer/config/config.json`：

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
    "allowed_directories": ["/var/log", "/opt/logs", "/tmp", "/home"]
  }
}
```

### 敏感配置

创建 `config/config.local.json` 存储敏感信息（会被git自动忽略）：

```json
{
  "llm": {
    "api_key": "your-secret-api-key"
  }
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 操作失败 |
| 101 | 不支持的文件类型 |
| 200 | 任务不存在 |
| 400 | 路径不在白名单 |
| 401 | 路径不存在 |
| 402 | 无读取权限 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 性能特性

### LLM模式
- **处理速度**：每千行5-30秒
- **内存占用**：处理100MB+文件时稳定在约200MB
- **并发支持**：支持200+并发请求
- **最大文件**：单文件最大500MB

### 规则模式
- **处理速度**：每千行小于1秒
- **内存占用**：极小开销
- **成本**：免费（无API调用）
- **网络**：不需要网络连接

## 最佳实践

### 1. 选择合适的模式

| 场景 | 推荐模式 |
|------|----------|
| 复杂问题诊断 | LLM模式 |
| 批量日志扫描 | 规则模式 |
| 实时监控 | 规则模式 |
| 根因分析 | LLM模式 |
| 快速错误检测 | 规则模式 |

### 2. 优化分块大小

| 文件大小 | 推荐分块大小 |
|----------|-------------|
| < 10MB | 10,000行 |
| 10-100MB | 50,000行 |
| > 100MB | 100,000行 |

### 3. 处理大文件

- 使用流式处理（自动启用）
- 定期监控任务进度
- 实现超时处理机制
- 考虑拆分超大文件

### 4. 安全注意事项

- 配置服务器路径访问的`allowed_directories`
- 使用`X-User-Id`进行数据隔离
- 处理前验证文件类型
- 生产环境实现限流

## 故障排查

### 问题：任务卡在处理中

**解决方案：**
1. 使用 `GET /api/task/{task_id}` 检查任务状态
2. 使用 `POST /api/task/{task_id}/cancel` 取消任务
3. 使用 `force_restart: true` 重启任务

### 问题：LLM API错误

**解决方案：**
1. 验证API密钥配置
2. 检查网络连接
3. 审查API调用限制
4. 考虑使用规则模式作为备选

### 问题：路径访问被拒绝

**解决方案：**
1. 验证路径在`allowed_directories`中
2. 检查文件系统权限
3. 确保路径存在且可读

### 问题：报告生成失败

**解决方案：**
1. 检查可用磁盘空间
2. 验证写入权限
3. 查看任务日志中的错误

## 集成模式

### 模式1：CI/CD流水线集成

```yaml
# .gitlab-ci.yml
log_analysis:
  stage: test
  script:
    - |
      curl -X POST http://log-analyzer:8000/api/process \
        -H "Content-Type: application/json" \
        -H "X-User-Id: ci-pipeline" \
        -d '{"file_path": "logs/app.log", "use_llm": false}'
```

### 模式2：监控告警集成

```python
# Prometheus alertmanager webhook
def analyze_error_logs(alert):
    response = requests.post(
        'http://log-analyzer:8000/api/process',
        json={
            'file_path': '/var/log/app/errors.log',
            'source': 'server',
            'use_llm': True
        }
    )
    return response.json()
```

### 模式3：定时分析任务

```python
# 每日日志分析定时任务
import schedule
import requests

def daily_analysis():
    requests.post(
        'http://log-analyzer:8000/api/process',
        json={
            'file_path': '/var/log/app',
            'source': 'server',
            'recursive': True,
            'use_llm': False
        }
    )

schedule.every().day.at("02:00").do(daily_analysis)
```

## 相关资源

- **API文档**：`log_analyzer/docs/API.md`
- **用户手册**：`log_analyzer/docs/USER_GUIDE.md`
- **开发者指南**：`log_analyzer/docs/DEVELOPER_GUIDE.md`
- **规则模式指南**：`log_analyzer/docs/RULE_MODE_GUIDE.md`
- **项目概述**：`log_analyzer/docs/PROJECT_OVERVIEW.md`

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v2.6.0 | 2026-06-05 | 统一处理API，增强服务器路径处理 |
| v2.5.1 | 2026-06-05 | 任务取消、HTML预览、并发优化 |
| v2.5.0 | 2026-06-04 | 操作日志、多用户权限 |
| v2.4.0 | 2026-06-03 | 规则分析器 |
| v2.3.0 | 2026-06-02 | 智能错误合并 |

## 许可证

MIT License
