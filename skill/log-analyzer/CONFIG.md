# Log Analyzer 配置指南

本文档提供日志分析组件所有配置参数的详细说明。

## 配置文件位置

主配置文件位于：
```
log_analyzer/config/config.json
```

对于敏感信息（如API密钥等），请使用：
```
log_analyzer/config/config.local.json
```

> 注意：`config.local.json` 会被git自动忽略，并且会覆盖 `config.json` 中的值。

---

## 配置结构

### 完整配置示例

```json
{
  "llm": {
    "api_url": "https://api.example.com/v1/chat/completions",
    "model_name": "qwen3-235b-a22b",
    "api_key": "",
    "backup_model": "deepseek-v3.2",
    "max_tokens": 4096,
    "temperature": 0.7,
    "timeout": 60
  },
  "processing": {
    "chunk_size": 10000,
    "max_retries": 3,
    "retry_delay": 1.0,
    "max_concurrent_requests": 10,
    "enable_streaming": true
  },
  "app": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false,
    "workers": 4,
    "log_level": "INFO"
  },
  "security": {
    "max_file_size_mb": 500,
    "max_files_per_request": 10,
    "allowed_file_types": [".log", ".txt", ".zip", ".pcap"],
    "enable_rate_limiting": false,
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  },
  "server_paths": {
    "allowed_directories": ["/var/log", "/opt/logs", "/tmp", "/home"],
    "max_recursive_depth": 5,
    "max_files_per_scan": 1000
  },
  "storage": {
    "max_reports_per_user": 50,
    "max_uploads_per_user": 100,
    "report_cleanup_days": 30,
    "enable_auto_cleanup": true
  },
  "report": {
    "default_formats": ["pdf", "markdown", "html"],
    "include_raw_logs": false,
    "max_error_samples": 10,
    "enable_charts": true
  }
}
```

---

## 配置项详细说明

### 1. LLM配置 (`llm`)

大语言模型集成配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_url` | string | - | LLM API端点URL |
| `model_name` | string | `qwen3-235b-a22b` | 主模型名称 |
| `api_key` | string | - | API认证密钥（应存储在config.local.json中） |
| `backup_model` | string | `deepseek-v3.2` | 主模型失败时的备用模型 |
| `max_tokens` | int | 4096 | 响应的最大token数 |
| `temperature` | float | 0.7 | 响应随机性（0.0-1.0） |
| `timeout` | int | 60 | API请求超时时间（秒） |

**示例：**
```json
{
  "llm": {
    "api_url": "https://api.openai.com/v1/chat/completions",
    "model_name": "gpt-4",
    "api_key": "sk-xxx",
    "max_tokens": 4096,
    "temperature": 0.7
  }
}
```

**最佳实践：**
- 仅在 `config.local.json` 中存储 `api_key`
- 使用 `backup_model` 提高可用性
- 设置较低的 `temperature`（0.3-0.5）以获得更确定的分析结果
- 对于大日志文件，增加 `timeout`

---

### 2. 处理配置 (`processing`)

日志处理行为配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_size` | int | 10000 | 每个处理块的行数 |
| `max_retries` | int | 3 | 失败操作的最大重试次数 |
| `retry_delay` | float | 1.0 | 重试间隔时间（秒） |
| `max_concurrent_requests` | int | 10 | 最大并发LLM API调用数 |
| `enable_streaming` | bool | true | 是否启用大文件流式处理 |

**分块大小建议：**

| 文件大小 | 推荐分块大小 | 原因 |
|----------|-------------|------|
| < 10MB | 10,000行 | 处理更快，内存占用更低 |
| 10-100MB | 50,000行 | 性能平衡 |
| > 100MB | 100,000行 | 减少API调用，提高吞吐量 |

**示例：**
```json
{
  "processing": {
    "chunk_size": 50000,
    "max_retries": 5,
    "retry_delay": 2.0,
    "max_concurrent_requests": 20,
    "enable_streaming": true
  }
}
```

---

### 3. 应用配置 (`app`)

服务器和运行时配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | string | `0.0.0.0` | 服务器绑定地址 |
| `port` | int | 8000 | 服务器端口 |
| `debug` | bool | false | 是否启用调试模式 |
| `workers` | int | 4 | 工作进程数 |
| `log_level` | string | `INFO` | 日志级别（DEBUG、INFO、WARNING、ERROR） |

**示例：**
```json
{
  "app": {
    "host": "127.0.0.1",
    "port": 8080,
    "debug": true,
    "workers": 2,
    "log_level": "DEBUG"
  }
}
```

**不同环境的配置建议：**

| 环境 | Host | Workers | Debug | 日志级别 |
|------|------|---------|-------|----------|
| 开发环境 | `127.0.0.1` | 1 | true | DEBUG |
| 测试环境 | `0.0.0.0` | 2 | false | INFO |
| 生产环境 | `0.0.0.0` | 4+ | false | WARNING |

---

### 4. 安全配置 (`security`)

安全和访问控制设置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_file_size_mb` | int | 500 | 最大上传文件大小（MB） |
| `max_files_per_request` | int | 10 | 每次上传请求的最大文件数 |
| `allowed_file_types` | array | [`.log`, `.txt`, `.zip`, `.pcap`] | 允许的文件扩展名 |
| `enable_rate_limiting` | bool | false | 是否启用请求限流 |
| `rate_limit_requests` | int | 100 | 限流窗口内的最大请求数 |
| `rate_limit_window` | int | 60 | 限流窗口时间（秒） |

**示例：**
```json
{
  "security": {
    "max_file_size_mb": 1000,
    "max_files_per_request": 20,
    "allowed_file_types": [".log", ".txt", ".zip", ".pcap", ".pcapng"],
    "enable_rate_limiting": true,
    "rate_limit_requests": 200,
    "rate_limit_window": 60
  }
}
```

**安全最佳实践：**
- 根据可用磁盘空间设置 `max_file_size_mb`
- 将 `allowed_file_types` 限制为仅需要的格式
- 在生产环境中启用限流
- 在生产环境中使用HTTPS

---

### 5. 服务器路径配置 (`server_paths`)

服务器端文件访问配置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allowed_directories` | array | [] | 可访问目录白名单 |
| `max_recursive_depth` | int | 5 | 目录扫描的最大递归深度 |
| `max_files_per_scan` | int | 1000 | 每次扫描返回的最大文件数 |

**示例：**
```json
{
  "server_paths": {
    "allowed_directories": [
      "/var/log",
      "/opt/application/logs",
      "/home/user/logs"
    ],
    "max_recursive_depth": 3,
    "max_files_per_scan": 500
  }
}
```

**安全注意事项：**
- 空的 `allowed_directories` 允许访问所有路径（生产环境不推荐）
- 仅使用绝对路径
- 确保应用程序对指定目录有读取权限
- 避免允许系统关键目录（如 `/etc`、`/root`）

---

### 6. 存储配置 (`storage`)

数据存储和清理设置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_reports_per_user` | int | 50 | 每个用户的最大报告数 |
| `max_uploads_per_user` | int | 100 | 每个用户的最大上传文件数 |
| `report_cleanup_days` | int | 30 | 报告保留天数，超过后清理 |
| `enable_auto_cleanup` | bool | true | 是否启用旧文件自动清理 |

**示例：**
```json
{
  "storage": {
    "max_reports_per_user": 100,
    "max_uploads_per_user": 200,
    "report_cleanup_days": 60,
    "enable_auto_cleanup": true
  }
}
```

**存储管理：**
- 报告存储在 `data/reports/{user_id}/`
- 上传文件存储在 `data/uploads/{user_id}/`
- 当超过限制时自动执行清理
- 首先删除最旧的文件

---

### 7. 报告配置 (`report`)

报告生成设置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `default_formats` | array | [`pdf`, `markdown`, `html`] | 默认输出格式 |
| `include_raw_logs` | bool | false | 是否在报告中包含原始日志片段 |
| `max_error_samples` | int | 10 | 每个类别最大错误样本数 |
| `enable_charts` | bool | true | 是否在报告中包含图表 |

**示例：**
```json
{
  "report": {
    "default_formats": ["pdf", "markdown", "html", "docx"],
    "include_raw_logs": true,
    "max_error_samples": 20,
    "enable_charts": true
  }
}
```

---

## 环境变量

配置可以通过环境变量覆盖：

| 环境变量 | 对应配置路径 | 示例 |
|----------|-------------|------|
| `LOG_ANALYZER_HOST` | `app.host` | `0.0.0.0` |
| `LOG_ANALYZER_PORT` | `app.port` | `8000` |
| `LOG_ANALYZER_DEBUG` | `app.debug` | `true` |
| `LOG_ANALYZER_LLM_API_URL` | `llm.api_url` | `https://api.example.com/v1/chat/completions` |
| `LOG_ANALYZER_LLM_API_KEY` | `llm.api_key` | `sk-xxx` |
| `LOG_ANALYZER_LLM_MODEL` | `llm.model_name` | `gpt-4` |
| `LOG_ANALYZER_MAX_FILE_SIZE` | `security.max_file_size_mb` | `500` |

**使用示例：**
```bash
export LOG_ANALYZER_PORT=8080
export LOG_ANALYZER_LLM_API_KEY=sk-your-key-here
python -m log_analyzer.main
```

---

## 配置验证

系统在启动时验证配置。无效配置会导致错误。

### 验证规则

1. **LLM配置验证**
   - `api_url` 必须是有效的URL
   - `model_name` 不能为空
   - `max_tokens` 必须是正整数
   - `temperature` 必须在0.0到1.0之间

2. **处理配置验证**
   - `chunk_size` 必须在1000到1000000之间
   - `max_retries` 必须是非负整数
   - `retry_delay` 必须是非负数

3. **安全配置验证**
   - `max_file_size_mb` 必须是正数
   - `allowed_file_types` 必须是非空数组

4. **服务器路径配置验证**
   - `allowed_directories` 必须包含有效路径
   - `max_recursive_depth` 必须在1到10之间

---

## 配置最佳实践

### 开发环境配置

```json
{
  "llm": {
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7
  },
  "app": {
    "debug": true,
    "log_level": "DEBUG"
  },
  "security": {
    "max_file_size_mb": 100
  }
}
```

### 生产环境配置

```json
{
  "llm": {
    "model_name": "gpt-4",
    "temperature": 0.3,
    "timeout": 120
  },
  "app": {
    "workers": 8,
    "log_level": "WARNING"
  },
  "security": {
    "max_file_size_mb": 500,
    "enable_rate_limiting": true
  },
  "server_paths": {
    "allowed_directories": ["/var/log/app"]
  }
}
```

### 高吞吐量处理配置

```json
{
  "processing": {
    "chunk_size": 100000,
    "max_concurrent_requests": 50
  },
  "app": {
    "workers": 16
  },
  "storage": {
    "max_reports_per_user": 200
  }
}
```

---

## 配置问题排查

### 问题：LLM API连接失败

**检查项：**
1. `llm.api_url` 是否正确且可访问
2. `llm.api_key` 是否有效
3. 与API端点的网络连接是否正常

### 问题：文件上传被拒绝

**检查项：**
1. 文件大小是否小于 `security.max_file_size_mb`
2. 文件扩展名是否在 `security.allowed_file_types` 中
3. 是否有足够的磁盘空间

### 问题：服务器路径访问被拒绝

**检查项：**
1. 路径是否在 `server_paths.allowed_directories` 中
2. 应用程序是否有读取权限
3. 路径是否存在且可访问

### 问题：报告未生成

**检查项：**
1. `report.default_formats` 是否配置
2. 报告目录是否有足够的磁盘空间
3. 用户是否未超过 `storage.max_reports_per_user` 限制
