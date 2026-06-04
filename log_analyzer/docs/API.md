# Log Analyzer API 接口文档 (v2.5 - 完整版本)

> 版本: v2.5.0
> 更新日期: 2026-06-04
> 基础URL: `http://localhost:8000`

---

## 目录

1. [概述](#1-概述)
   - [接口变更说明](#1-1-接口变更说明)
   - [分析模式对比](#1-2-分析模式对比)
   - [规则模式详解](#1-3-规则模式详解)
   - [认证机制](#1-4-认证机制)
   - [通用请求头](#1-5-通用请求头)
   - [统一响应格式](#1-6-统一响应格式)
   - [权限说明](#1-7-权限说明)
2. [用户识别机制](#2-用户识别机制)
3. [认证接口](#3-认证接口)
4. [文件管理接口](#4-文件管理接口)
5. [日志处理接口](#5-日志处理接口)
6. [任务管理接口](#6-任务管理接口)
7. [报告接口](#7-报告接口)
8. [历史报告 CRUD 接口](#8-历史报告-crud-接口)
9. [数据备份接口](#9-数据备份接口)
10. [用户操作历史记录接口](#10-用户操作历史记录接口)
11. [系统接口](#11-系统接口)
12. [错误码定义](#12-错误码定义)
13. [数据隔离与存储方案](#13-数据隔离与存储方案)

---

## 1. 概述

### 1.1 接口变更说明

本版本新增两项重要功能：

#### 规则模式分析
- **新增 `use_llm` 参数**：支持在 LLM 模式和规则模式间切换
- **规则模式**：不依赖 LLM，使用预定义规则进行快速分析
- **LLM 模式**：调用大语言模型进行深度语义分析（默认）

#### 服务器路径读取（单一接口）
- **新增 `POST /api/list-dir`**：整合目录浏览、路径验证和权限检查功能
- **单一接口实现**：通过参数控制不同操作模式
- **权限控制**：白名单机制，仅允许访问配置的目录

### 1.2 分析模式对比

| 特性 | LLM 模式 | 规则模式 |
|------|---------|---------|
| 语义理解 | 强，支持复杂分析 | 有限，基于规则匹配 |
| 响应速度 | 较慢（5-30秒/1000条） | 极快（<1秒/1000条） |
| API 成本 | 有（按调用计费） | 无（完全免费） |
| 内存占用 | ~200MB | ~50MB |
| 适用场景 | 复杂问题诊断、深度分析 | 快速原型、成本敏感、实时监控 |

### 1.3 规则模式详解

规则模式是一种轻量级的日志分析方式，不依赖大语言模型，使用预定义规则进行错误识别和分类。

**核心特性：**
- **多层次错误分类**：Critical、High、Medium、Low 四个级别
- **根本原因识别**：自动识别空引用、资源泄漏、超时、认证问题等
- **智能建议生成**：根据错误类型自动生成整改建议
- **统计分析**：日志级别分布、错误类型分布、时间趋势分析

**适用场景：**
- 批量日志快速扫描
- 日常监控告警
- CI/CD 流水线集成
- 成本敏感环境
- 离线分析场景

**不适用场景：**
- 需要深度语义分析
- 复杂跨系统问题诊断
- 需要自然语言总结
- 未知错误模式识别

### 1.4 认证机制

采用简化认证机制：
- **移除 Token 鉴权**：不再需要登录、Token验证、登出等流程
- **采用请求头识别用户身份**：通过 `X-User-Id` 头传递用户ID
- **默认用户支持**：未携带头时使用 `default_user`

### 1.5 通用请求头

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-User-Id` | 否 | 用户业务ID（缺失则使用 `default_user`） |
| `X-Username` | 否 | 用户名（用于显示，可选） |
| `Content-Type` | 是 | `application/json` 或 `multipart/form-data` |

### 1.6 统一响应格式

```json
{
    "code": 0,
    "message": "操作成功",
    "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0=成功，非0=失败 |
| message | string | 操作结果描述 |
| data | object/null | 响应数据 |

### 1.7 权限说明

**v2.5.0 权限优化**：移除了管理员权限限制，所有用户可访问以下功能：

| 权限级别 | 说明 | 适用接口 |
|----------|------|----------|
| 公开 | 无需认证 | `/api/health` |
| 用户级 | 需要 X-User-Id | 大部分业务接口 |
| 数据隔离 | 用户只能访问自己的数据 | 历史报告（仅自己的）、上传文件、任务 |
| 全局访问 | 可访问但数据隔离 | 历史报告管理、操作日志查询、操作统计 |

---

## 2. 用户识别机制

### 2.1 工作流程

```
┌─────────┐                              ┌─────────┐                          ┌─────────┐
│  客户端  │                              │  API    │                          │ 存储层  │
└────┬────┘                              └────┬────┘                          └────┬────┘
     │                                         │                                   │
     │  1. 任意API请求                          │                                   │
     │  Header: X-User-Id: user_001            │                                   │
     │────────────────────────────────────────>│                                   │
     │                                         │  2. 提取 X-User-Id                │
     │                                         │     (无值则用 default_user)       │
     │                                         │                                   │
     │                                         │  3. 获取/创建用户档案             │
     │                                         │──────────────────────────────────>│
     │                                         │                                   │
     │                                         │  4. 返回用户信息                  │
     │                                         │<──────────────────────────────────│
     │                                         │                                   │
     │                                         │  5. 执行业务逻辑（用户隔离）       │
     │                                         │──────────────────────────────────>│
     │                                         │                                   │
     │  6. 返回该用户的专属数据                 │                                   │
     │<────────────────────────────────────────│                                   │
     │                                         │                                   │
```

### 2.2 优势

- **前端无需登录逻辑**：首次访问自动创建用户档案
- **后端无需鉴权开销**：不验证 Token 签名
- **数据严格隔离**：所有操作都基于 user_id 进行隔离
- **保留扩展性**：后续可平滑接入 Token 鉴权

---

## 3. 认证接口

### 3.1 用户识别

**请求**
```http
POST /api/auth/identify
Content-Type: application/json

{
    "user_id": "user_001",
    "username": "张三"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户业务ID |
| username | string | 否 | 用户名（用于显示） |

**成功响应**
```json
{
    "code": 0,
    "message": "识别成功",
    "data": {
        "user_id": "user_001",
        "username": "张三",
        "created_at": "2026-06-01T10:00:00"
    }
}
```

### 3.2 获取当前用户信息

**请求**
```http
GET /api/auth/current
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "user_id": "user_001",
        "username": "张三",
        "created_at": "2026-06-01T10:00:00"
    }
}
```

> 此接口直接读取 `X-User-Id` 请求头，无需先调用 identify。

---

## 4. 文件管理接口

### 4.1 上传文件

**请求**
```http
POST /api/upload
X-User-Id: user_001
Content-Type: multipart/form-data

file: <文件>
```

**支持的文件类型**
- `.log` - 日志文件
- `.txt` - 文本文件
- `.zip` - ZIP压缩包（自动解压到用户目录）
- `.pcap` - 网络抓包文件（需系统安装 `tshark`）

**成功响应**
```json
{
    "code": 0,
    "message": "上传成功",
    "data": {
        "success": true,
        "file_path": "/path/to/uploaded/file.log",
        "file_name": "error.log",
        "file_size": "10.5 KB",
        "extracted_files": []
    }
}
```

**错误响应**
```json
{
    "code": 1,
    "message": "不支持的文件类型: test.exe\n支持的类型: .log, .txt, .zip, .pcap",
    "data": null
}
```

### 4.2 服务器路径读取（单一接口）

**请求**
```http
POST /api/list-dir
X-User-Id: user_001
Content-Type: application/json

{
    "path": "/var/log/nginx",
    "recursive": false,
    "file_patterns": ["*.log", "*.txt"],
    "validate_only": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| path | string | 是 | - | 文件或目录路径 |
| recursive | bool | 否 | false | 是否递归读取子目录 |
| file_patterns | array | 否 | ["*.log"] | 文件匹配模式列表 |
| validate_only | bool | 否 | false | 是否仅验证路径（不返回完整文件列表） |

**功能模式**

| 参数组合 | 功能 |
|---------|------|
| `validate_only: true` | 路径验证模式 - 验证路径有效性和权限 |
| `validate_only: false` | 目录浏览模式 - 返回目录内容列表 |
| `recursive: true` | 递归读取子目录 |
| `file_patterns: ["*.log"]` | 按通配符匹配文件 |

**成功响应 - 验证模式**
```json
{
    "code": 0,
    "message": "路径验证成功",
    "data": {
        "path": "/var/log/nginx",
        "is_file": false,
        "is_directory": true,
        "file_count": 5,
        "files": [
            {
                "name": "error.log",
                "path": "/var/log/nginx/error.log",
                "size": 1048576,
                "size_str": "1.00 MB",
                "modified": "2024-01-01T12:00:00"
            }
        ]
    }
}
```

**成功响应 - 浏览模式**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "current_path": "/var/log/nginx",
        "parent_path": "/var/log",
        "files": [
            {
                "name": "error.log",
                "path": "/var/log/nginx/error.log",
                "size": 1048576,
                "size_str": "1.00 MB",
                "type": "file"
            },
            {
                "name": "access/",
                "path": "/var/log/nginx/access",
                "size": 0,
                "size_str": "-",
                "type": "directory"
            }
        ]
    }
}
```

**安全特性**
- **路径遍历攻击防护**：解析绝对路径，防止 `../` 攻击
- **白名单目录限制**：只允许访问 `/var/log`, `/opt/logs`, `/tmp`, `/home`
- **自动权限检查**：验证系统读取权限
- **递归深度控制**：避免在大型目录上过度递归

**使用模式说明**

| 模式 | 参数配置 | 适用场景 |
|------|---------|---------|
| **验证模式** | `validate_only: true` | 验证路径有效性和权限 |
| **浏览模式** | `validate_only: false` | 浏览目录内容 |
| **递归模式** | `recursive: true` | 读取子目录中的文件 |
| **精确匹配** | `file_patterns: ["*.log"]` | 按通配符过滤文件 |

**错误响应**

| HTTP 状态码 | 错误场景 | 响应示例 |
|------------|---------|---------|
| 403 | 路径不在白名单 | `{"code": 1, "message": "路径 /etc 不在允许访问的目录范围内。允许的目录：/var/log, /opt/logs, /tmp, /home"}` |
| 404 | 路径不存在 | `{"code": 1, "message": "路径不存在"}` |
| 403 | 无读取权限 | `{"code": 1, "message": "没有读取路径 /var/log/secure 的权限"}` |
| 500 | 服务器错误 | `{"code": 1, "message": "服务器内部错误"}` |

**最佳实践**

1. **先验证后处理**：使用 `validate_only: true` 先验证路径有效性
2. **限制递归深度**：大目录建议关闭递归选项
3. **精确文件匹配**：使用 `file_patterns` 减少返回数据量
4. **权限检查**：确保应用进程有读取目标路径的权限

---

## 5. 日志处理接口

### 5.1 开始处理日志文件

**请求**
```http
POST /api/process
X-User-Id: user_001
Content-Type: application/json

{
    "file_path": "/path/to/log/file.log",
    "chunk_size": 50000,
    "force_restart": false,
    "use_llm": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_path | string | 否 | - | 单个文件路径（与 directory_path 二选一） |
| directory_path | string | 否 | - | 目录路径（与 file_path 二选一） |
| chunk_size | int | 否 | 50000 | 处理块大小 |
| force_restart | bool | 否 | false | 是否强制重启已存在的任务 |
| use_llm | bool | 否 | true | 是否使用LLM分析（false则使用规则引擎） |

**成功响应**
```json
{
    "code": 0,
    "message": "任务已创建，正在处理 1 个文件",
    "data": {
        "task_id": "user_001_20260601_100000_123456",
        "status": "pending"
    }
}
```

### 5.2 从服务器路径读取并处理

**请求**
```http
POST /api/process-from-path
X-User-Id: user_001
Content-Type: application/json

{
    "path": "/var/log",
    "recursive": true,
    "file_patterns": ["*.log"]
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| path | string | 是 | - | 文件或目录路径 |
| recursive | bool | 否 | false | 是否递归读取子目录 |
| max_file_size | int | 否 | 104857600 | 最大文件大小 |
| file_patterns | array | 否 | null | 文件匹配模式 |

**成功响应**
```json
{
    "code": 0,
    "message": "任务已创建，正在处理 3 个文件",
    "data": {
        "task_id": "path_user_001_20260601_100000_123456",
        "status": "pending",
        "file_count": 3,
        "total_size": 31457280
    }
}
```

**与 /api/upload + /api/process 的区别**
- 无需先上传文件到服务器
- 直接从服务器指定路径读取
- 适用于已存在于服务器上的日志文件

---

## 6. 任务管理接口

### 6.1 获取任务状态

**请求**
```http
GET /api/task/{task_id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务ID |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "task_id": "user_001_20260601_100000_123456",
        "status": "processing",
        "progress": 50.0,
        "message": "正在分析日志...",
        "reports": null,
        "error": null
    }
}
```

**任务状态说明**

| 状态 | 说明 |
|------|------|
| pending | 任务已创建，等待开始 |
| processing | 正在处理 |
| completed | 处理完成 |
| failed | 处理失败 |

**错误响应**
```json
{
    "code": 1,
    "message": "无权访问此任务",
    "data": null
}
```

---

## 7. 报告接口

### 7.1 获取报告列表

**请求**
```http
GET /api/reports
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "reports": [
            {
                "name": "report_error.log_20260601_100000.md",
                "path": "/path/to/report.md",
                "size": 10240,
                "size_str": "10.0 KB",
                "modified": "2026-06-01T10:00:00",
                "type": "markdown"
            }
        ]
    }
}
```

### 7.2 下载报告

**请求**
```http
GET /api/report/download/{report_name}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| report_name | string | 报告文件名 |

**成功响应**
- 返回文件流，Content-Type 根据文件类型自动设置

**错误响应**
```json
{
    "code": 1,
    "message": "报告不存在",
    "data": null
}
```

### 7.3 删除报告

**请求**
```http
DELETE /api/report/{report_name}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| report_name | string | 报告文件名 |

**成功响应**
```json
{
    "code": 0,
    "message": "删除成功",
    "data": null
}
```

---

## 8. 历史报告 CRUD 接口

### 8.1 获取历史报告列表

**请求**
```http
GET /api/history/reports
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "reports": [
            {
                "id": 1,
                "user_id": "user_001",
                "file_name": "error.log",
                "report_path": "/path/to/report.pdf",
                "created_at": "2026-06-01T10:00:00",
                "status": "completed",
                "error_count": 15,
                "warning_count": 30
            }
        ],
        "total": 100,
        "page": 1,
        "page_size": 20
    }
}
```

### 8.2 获取单个报告详情

**请求**
```http
GET /api/history/report/{id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | int | 报告记录ID |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "id": 1,
        "user_id": "user_001",
        "file_name": "error.log",
        "report_path": "/path/to/report.pdf",
        "created_at": "2026-06-01T10:00:00",
        "status": "completed",
        "error_count": 15,
        "warning_count": 30,
        "analysis_summary": "分析完成，共发现 15 个错误..."
    }
}
```

### 8.3 搜索历史报告

**请求**
```http
GET /api/history/reports/search?keyword=error&start_date=2026-06-01&end_date=2026-06-30
X-User-Id: user_001
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| start_date | string | 否 | 开始日期（YYYY-MM-DD） |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "reports": [...],
        "total": 5,
        "page": 1,
        "page_size": 20
    }
}
```

### 8.4 删除历史记录

**请求**
```http
DELETE /api/history/report/{id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | int | 报告记录ID |

**成功响应**
```json
{
    "code": 0,
    "message": "删除成功",
    "data": null
}
```

---

## 9. 数据备份接口

### 9.1 导出用户数据

**请求**
```http
POST /api/backup/export
X-User-Id: user_001
Content-Type: application/json

{
    "include_reports": true,
    "include_checkpoints": false
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| include_reports | bool | 否 | true | 是否包含报告文件 |
| include_checkpoints | bool | 否 | false | 是否包含检查点数据 |

**成功响应**
```json
{
    "code": 0,
    "message": "导出成功",
    "data": {
        "backup_path": "/path/to/backup.zip",
        "file_count": 15,
        "total_size": 10485760,
        "total_size_str": "10.0 MB"
    }
}
```

### 9.2 导入用户数据

**请求**
```http
POST /api/backup/import
X-User-Id: user_001
Content-Type: multipart/form-data

file: <backup.zip>
```

**成功响应**
```json
{
    "code": 0,
    "message": "导入成功",
    "data": {
        "imported_files": 15,
        "imported_reports": 10,
        "imported_checkpoints": 5
    }
}
```

---

## 10. 用户操作历史记录接口

### 10.1 获取操作记录列表

**请求**
```http
GET /api/history/actions
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "actions": [
            {
                "id": 1,
                "user_id": "user_001",
                "action_type": "upload",
                "action_desc": "上传文件 error.log",
                "created_at": "2026-06-01T10:00:00"
            }
        ],
        "total": 100,
        "page": 1,
        "page_size": 20
    }
}
```

### 10.2 获取操作类型统计

**请求**
```http
GET /api/history/actions/stats
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "upload": 50,
        "process": 45,
        "download": 30,
        "delete": 5
    }
}
```

---

## 11. 系统接口

### 11.1 健康检查

**请求**
```http
GET /api/health
```

**成功响应**
```json
{
    "code": 0,
    "message": "OK",
    "data": {
        "status": "healthy",
        "timestamp": "2026-06-01T10:00:00",
        "version": "2.5.0"
    }
}
```

### 11.2 获取系统配置

**请求**
```http
GET /api/system/config
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "max_file_size_mb": 500,
        "max_files_per_request": 10,
        "supported_formats": ["pdf", "word", "md"]
    }
}
```

---

## 12. 错误码定义

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 0 | 200 | 成功 |
| 1 | 400 | 请求参数错误 |
| 2 | 401 | 未授权 |
| 3 | 403 | 权限不足 |
| 4 | 404 | 资源不存在 |
| 5 | 500 | 服务器内部错误 |
| 100 | - | 文件上传失败 |
| 101 | - | 文件类型不支持 |
| 102 | - | 文件大小超限 |
| 200 | - | 任务不存在 |
| 201 | - | 任务已存在 |
| 300 | - | 报告生成失败 |
| 400 | - | 路径不在白名单范围内（服务器路径读取） |
| 401 | - | 路径不存在（服务器路径读取） |
| 402 | - | 没有读取路径权限（服务器路径读取） |

---

## 13. 数据隔离与存储方案

### 13.1 存储结构

```
users/
├── {user_id}/
│   ├── uploads/           # 上传的文件
│   ├── reports/           # 生成的报告
│   ├── checkpoints/       # 断点续传检查点
│   └── data/              # 用户数据
```

### 13.2 隔离机制

- **目录隔离**：每个用户拥有独立的目录
- **文件名隔离**：文件名包含 user_id 前缀
- **数据库隔离**：所有查询都带 user_id 条件

### 13.3 安全措施

- 文件权限：仅应用进程可读写
- 敏感数据：不存储明文密码或密钥
- 日志审计：记录所有操作日志
