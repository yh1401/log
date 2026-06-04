# Log Analyzer API 接口文档 (v2.5.1 - 完整版本)

> 版本: v2.5.1
> 更新日期: 2026-06-04
> 基础URL: `http://localhost:8000`

---

## 目录

1. [概述](#1-概述)
   - [分析模式对比](#1-1-分析模式对比)
   - [认证机制](#1-2-认证机制)
   - [通用请求头](#1-3-通用请求头)
   - [统一响应格式](#1-4-统一响应格式)
   - [权限说明](#1-5-权限说明)
2. [用户识别机制](#2-用户识别机制)
3. [文件管理接口](#3-文件管理接口)
   - [POST /api/upload - 上传文件](#31-上传文件)
   - [POST /api/list-dir - 服务器路径浏览](#32-服务器路径浏览单一接口)
   - [GET /api/download/{file_path} - 文件下载](#33-文件下载)
4. [日志处理接口](#4-日志处理接口)
   - [POST /api/process - 开始处理日志文件](#41-开始处理日志文件)
   - [POST /api/process-from-path - 从服务器路径读取并处理](#42-从服务器路径读取并处理)
5. [任务管理接口](#5-任务管理接口)
   - [GET /api/task/{task_id} - 获取任务状态](#51-获取任务状态)
6. [报告接口](#6-报告接口)
   - [GET /api/reports - 获取报告列表](#61-获取报告列表)
   - [GET /api/report/download/{report_name} - 下载报告](#62-下载报告)
   - [DELETE /api/report/{report_name} - 删除报告](#63-删除报告)
7. [历史报告 CRUD 接口](#7-历史报告-crud-接口)
   - [POST /api/history/reports - 创建历史报告记录](#71-创建历史报告记录)
   - [GET /api/history/reports - 获取历史报告列表](#72-获取历史报告列表)
   - [GET /api/history/reports/{report_id} - 获取单个报告详情](#73-获取单个报告详情)
   - [PUT /api/history/reports/{report_id} - 更新报告记录](#74-更新报告记录)
   - [GET /api/history/reports/search - 搜索历史报告](#75-搜索历史报告)
   - [DELETE /api/history/reports/{report_id} - 删除历史记录](#76-删除历史记录)
8. [数据备份接口](#8-数据备份接口)
   - [POST /api/backup/create - 创建备份](#81-创建备份)
   - [POST /api/backup/export - 导出用户数据](#82-导出用户数据)
   - [POST /api/backup/import - 导入用户数据](#83-导入用户数据)
9. [用户操作历史记录接口](#9-用户操作历史记录接口)
   - [POST /api/history/actions - 创建操作记录](#91-创建操作记录)
   - [GET /api/history/actions - 获取操作记录列表](#92-获取操作记录列表)
   - [GET /api/history/actions/types - 获取操作类型列表](#93-获取操作类型列表)
   - [GET /api/history/actions/count - 获取操作统计](#94-获取操作统计)
   - [GET /api/history/actions/{action_id} - 获取单个操作记录](#95-获取单个操作记录)
   - [DELETE /api/history/actions/{action_id} - 删除操作记录](#96-删除操作记录)
   - [DELETE /api/history/actions/cleanup - 清理操作记录](#97-清理操作记录)
10. [系统接口](#10-系统接口)
    - [GET /api/health - 健康检查](#101-健康检查)
    - [GET /api/system/config - 获取系统配置](#102-获取系统配置)
    - [POST /api/initialize - 系统初始化](#103-系统初始化)
11. [错误码定义](#11-错误码定义)
12. [数据隔离与存储方案](#12-数据隔离与存储方案)
13. [接口调用示例](#13-接口调用示例)

---

## 1. 概述

### 1.1 分析模式对比

系统提供两种分析模式：

- **LLM模式**：基于大语言模型进行深度语义分析，支持复杂问题诊断，响应较慢（5-30秒/1000条），有API调用成本
- **规则模式**：基于预定义规则进行快速匹配，响应极快（<1秒/1000条），完全免费，适用于批量扫描和实时监控

### 1.2 认证机制

采用简化认证机制：
- **移除 Token 鉴权**：不再需要登录、Token验证、登出等流程
- **采用请求头识别用户身份**：通过 `X-User-Id` 头传递用户ID
- **默认用户支持**：未携带头时使用 `default_user`

### 1.3 通用请求头

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-User-Id` | 否 | 用户业务ID（缺失则使用 `default_user`），用于身份识别和数据隔离 |
| `X-Username` | 否 | 用户显示名称（可选，未提供时自动使用 user_id），用于界面显示 |
| `Content-Type` | 是 | `application/json` 或 `multipart/form-data` |

### 1.4 统一响应格式

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

### 1.5 权限说明

**v2.5.1 权限优化**：移除了管理员权限限制，所有用户可访问以下功能：

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

## 3. 文件管理接口

### 3.1 上传文件

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

**文件大小限制**
- 单个文件最大：500 MB
- ZIP压缩包解压后最大：1 GB

**成功响应**
```json
{
    "code": 0,
    "message": "上传成功",
    "data": {
        "success": true,
        "file_path": "/users/user_001/uploads/error.log",
        "file_name": "error.log",
        "file_size": "10.5 KB",
        "extracted_files": [],
        "upload_time": "2026-06-01T10:00:00"
    }
}
```

**错误响应**
```json
{
    "code": 101,
    "message": "不支持的文件类型: test.exe\n支持的类型: .log, .txt, .zip, .pcap",
    "data": null
}
```

### 3.2 服务器路径浏览（单一接口）

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
- **白名单目录限制**：只允许访问 `/var/log`, `/opt/logs`, `/tmp`, `/home`（可配置）
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

| HTTP 状态码 | 错误码 | 错误场景 | 响应示例 |
|------------|--------|---------|---------|
| 403 | 400 | 路径不在白名单 | `{"code": 400, "message": "路径 /etc 不在允许访问的目录范围内。允许的目录：/var/log, /opt/logs, /tmp, /home"}` |
| 404 | 401 | 路径不存在 | `{"code": 401, "message": "路径不存在"}` |
| 403 | 402 | 无读取权限 | `{"code": 402, "message": "没有读取路径 /var/log/secure 的权限"}` |
| 500 | 5 | 服务器错误 | `{"code": 5, "message": "服务器内部错误"}` |

**最佳实践**

1. **先验证后处理**：使用 `validate_only: true` 先验证路径有效性
2. **限制递归深度**：大目录建议关闭递归选项
3. **精确文件匹配**：使用 `file_patterns` 减少返回数据量
4. **权限检查**：确保应用进程有读取目标路径的权限

### 3.3 文件下载

**请求**
```http
GET /api/download/{file_path}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| file_path | string | 文件路径（URL编码） |

**成功响应**
- 返回文件流，Content-Type 根据文件类型自动设置
- Content-Disposition: attachment; filename="xxx"

**错误响应**
```json
{
    "code": 4,
    "message": "文件不存在或无权访问",
    "data": null
}
```

---

## 4. 日志处理接口

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
    "use_llm": true,
    "merge_config": "default"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_path | string | 否 | - | 单个文件路径（与 directory_path 二选一） |
| directory_path | string | 否 | - | 目录路径（与 file_path 二选一） |
| chunk_size | int | 否 | 1000000 | 处理块大小（字节），建议值：10000-1000000 |
| force_restart | bool | 否 | false | 是否强制重启已存在的任务 |
| use_llm | bool | 否 | true | 是否使用LLM分析（false则使用规则引擎） |
| merge_config | string | 否 | "default" | 错误合并策略：default/strict/lenient |

**成功响应**
```json
{
    "code": 0,
    "message": "任务已创建，正在处理 1 个文件",
    "data": {
        "task_id": "user_001_20260601_100000_123456",
        "status": "pending",
        "file_count": 1,
        "total_size": 10485760
    }
}
```

**错误响应**
```json
{
    "code": 1,
    "message": "file_path 和 directory_path 必须提供一个",
    "data": null
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
    "file_patterns": ["*.log"],
    "max_file_size": 104857600,
    "use_llm": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| path | string | 是 | - | 文件或目录路径 |
| recursive | bool | 否 | false | 是否递归读取子目录 |
| max_file_size | int | 否 | 104857600 | 最大文件大小（字节），默认100MB |
| file_patterns | array | 否 | null | 文件匹配模式，为空则匹配所有支持的类型 |
| use_llm | bool | 否 | true | 是否使用LLM分析 |
| chunk_size | int | 否 | 50000 | 处理块大小 |

**成功响应**
```json
{
    "code": 0,
    "message": "任务已创建，正在处理 3 个文件",
    "data": {
        "task_id": "path_user_001_20260601_100000_123456",
        "status": "pending",
        "file_count": 3,
        "total_size": 31457280,
        "files": [
            "/var/log/nginx/error.log",
            "/var/log/nginx/access.log",
            "/var/log/messages"
        ]
    }
}
```

**与 /api/upload + /api/process 的区别**
- 无需先上传文件到服务器
- 直接从服务器指定路径读取
- 适用于已存在于服务器上的日志文件
- 支持 PCAP 网络抓包文件分析

---

## 5. 任务管理接口

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
        "current_file": "error.log",
        "file_count": 1,
        "processed_files": 0,
        "start_time": "2026-06-01T10:00:00",
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
    "code": 200,
    "message": "任务不存在",
    "data": null
}
```

---

## 6. 报告接口

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
                "path": "/users/user_001/reports/report_error.log_20260601_100000.md",
                "size": 10240,
                "size_str": "10.0 KB",
                "modified": "2026-06-01T10:00:00",
                "type": "markdown",
                "source_file": "error.log"
            }
        ],
        "total": 10
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
- 支持格式：.md, .html, .pdf, .docx, .json

**错误响应**
```json
{
    "code": 4,
    "message": "报告不存在或无权访问",
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

## 7. 历史报告 CRUD 接口

### 8.1 创建历史报告记录

**请求**
```http
POST /api/history/reports
X-User-Id: user_001
Content-Type: application/json

{
    "file_name": "error.log",
    "report_path": "/path/to/report.pdf",
    "status": "completed",
    "error_count": 15,
    "warning_count": 30,
    "analysis_summary": "分析完成，共发现 15 个错误..."
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_name | string | 是 | 源文件名 |
| report_path | string | 是 | 报告文件路径 |
| status | string | 是 | 状态：completed/failed |
| error_count | int | 否 | 错误数量 |
| warning_count | int | 否 | 警告数量 |
| analysis_summary | string | 否 | 分析摘要 |

**成功响应**
```json
{
    "code": 0,
    "message": "创建成功",
    "data": {
        "id": 1,
        "user_id": "user_001",
        "file_name": "error.log",
        "report_path": "/path/to/report.pdf",
        "created_at": "2026-06-01T10:00:00"
    }
}
```

### 8.2 获取历史报告列表

**请求**
```http
GET /api/history/reports?page=1&page_size=20
X-User-Id: user_001
```

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量（最大100） |

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
                "warning_count": 30,
                "analysis_summary": "分析完成，共发现 15 个错误..."
            }
        ],
        "total": 100,
        "page": 1,
        "page_size": 20
    }
}
```

### 8.3 获取单个报告详情

**请求**
```http
GET /api/history/reports/{report_id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| report_id | int | 报告记录ID |

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
        "updated_at": "2026-06-01T10:00:00",
        "status": "completed",
        "error_count": 15,
        "warning_count": 30,
        "analysis_summary": "分析完成，共发现 15 个错误..."
    }
}
```

### 8.4 更新报告记录

**请求**
```http
PUT /api/history/reports/{report_id}
X-User-Id: user_001
Content-Type: application/json

{
    "status": "completed",
    "error_count": 20,
    "analysis_summary": "更新后的摘要..."
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态 |
| error_count | int | 否 | 错误数量 |
| warning_count | int | 否 | 警告数量 |
| analysis_summary | string | 否 | 分析摘要 |

**成功响应**
```json
{
    "code": 0,
    "message": "更新成功",
    "data": {
        "id": 1,
        "user_id": "user_001",
        "updated_at": "2026-06-01T10:30:00"
    }
}
```

### 8.5 搜索历史报告

**请求**
```http
GET /api/history/reports/search?keyword=error&start_date=2026-06-01&end_date=2026-06-30&page=1&page_size=20
X-User-Id: user_001
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键词（匹配文件名、摘要） |
| start_date | string | 否 | 开始日期（YYYY-MM-DD） |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） |
| page | int | 否 | 页码 |
| page_size | int | 否 | 每页数量 |

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

### 8.6 删除历史记录

**请求**
```http
DELETE /api/history/reports/{report_id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| report_id | int | 报告记录ID |

**成功响应**
```json
{
    "code": 0,
    "message": "删除成功",
    "data": null
}
```

---

## 8. 数据备份接口

### 9.1 创建备份

**请求**
```http
POST /api/backup/create
X-User-Id: user_001
Content-Type: application/json

{
    "include_reports": true,
    "include_checkpoints": false,
    "include_actions": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| include_reports | bool | 否 | true | 是否包含报告文件 |
| include_checkpoints | bool | 否 | false | 是否包含检查点数据 |
| include_actions | bool | 否 | true | 是否包含操作记录 |

**成功响应**
```json
{
    "code": 0,
    "message": "备份创建成功",
    "data": {
        "backup_path": "/data/backups/user_001_20260601_100000.zip",
        "file_count": 15,
        "total_size": 10485760,
        "total_size_str": "10.0 MB",
        "backup_time": "2026-06-01T10:00:00"
    }
}
```

### 9.2 导出用户数据

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

### 9.3 导入用户数据

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
        "imported_checkpoints": 5,
        "import_time": "2026-06-01T10:00:00"
    }
}
```

---

## 9. 用户操作历史记录接口

### 10.1 创建操作记录

**请求**
```http
POST /api/history/actions
X-User-Id: user_001
Content-Type: application/json

{
    "action_type": "upload",
    "action_desc": "上传文件 error.log",
    "details": {
        "file_name": "error.log",
        "file_size": 10240
    }
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action_type | string | 是 | 操作类型：upload/process/download/delete/backup/import |
| action_desc | string | 是 | 操作描述 |
| details | object | 否 | 详细信息 |

**成功响应**
```json
{
    "code": 0,
    "message": "记录成功",
    "data": {
        "id": 1,
        "user_id": "user_001",
        "action_type": "upload",
        "created_at": "2026-06-01T10:00:00"
    }
}
```

### 10.2 获取操作记录列表

**请求**
```http
GET /api/history/actions?page=1&page_size=20&action_type=upload&start_date=2026-06-01
X-User-Id: user_001
```

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量 |
| action_type | string | 否 | - | 操作类型筛选 |
| start_date | string | 否 | - | 开始日期 |
| end_date | string | 否 | - | 结束日期 |

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
                "details": {
                    "file_name": "error.log",
                    "file_size": 10240
                },
                "created_at": "2026-06-01T10:00:00"
            }
        ],
        "total": 100,
        "page": 1,
        "page_size": 20
    }
}
```

### 10.3 获取操作类型列表

**请求**
```http
GET /api/history/actions/types
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "types": [
            {"type": "upload", "name": "文件上传"},
            {"type": "process", "name": "日志处理"},
            {"type": "download", "name": "文件下载"},
            {"type": "delete", "name": "删除操作"},
            {"type": "backup", "name": "数据备份"},
            {"type": "import", "name": "数据导入"}
        ]
    }
}
```

### 10.4 获取操作统计

**请求**
```http
GET /api/history/actions/count?start_date=2026-06-01&end_date=2026-06-30
X-User-Id: user_001
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "by_type": {
            "upload": 50,
            "process": 45,
            "download": 30,
            "delete": 5,
            "backup": 10,
            "import": 5
        },
        "by_user": {
            "user_001": 80,
            "user_002": 65
        },
        "total": 145,
        "period": "2026-06-01 ~ 2026-06-30"
    }
}
```

### 10.5 获取单个操作记录

**请求**
```http
GET /api/history/actions/{action_id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| action_id | int | 操作记录ID |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "id": 1,
        "user_id": "user_001",
        "action_type": "upload",
        "action_desc": "上传文件 error.log",
        "details": {...},
        "created_at": "2026-06-01T10:00:00"
    }
}
```

### 10.6 删除操作记录

**请求**
```http
DELETE /api/history/actions/{action_id}
X-User-Id: user_001
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| action_id | int | 操作记录ID |

**成功响应**
```json
{
    "code": 0,
    "message": "删除成功",
    "data": null
}
```

### 10.7 清理操作记录

**请求**
```http
DELETE /api/history/actions/cleanup
X-User-Id: user_001
Content-Type: application/json

{
    "before_date": "2026-01-01",
    "keep_days": 90
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| before_date | string | 否 | - | 删除指定日期之前的记录（与 keep_days 二选一） |
| keep_days | int | 否 | 90 | 保留最近N天的记录 |

**成功响应**
```json
{
    "code": 0,
    "message": "清理成功",
    "data": {
        "deleted_count": 150,
        "remaining_count": 50
    }
}
```

---

## 10. 系统接口

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
        "version": "2.5.1",
        "uptime": "12:30:00",
        "memory_usage": "150 MB",
        "cpu_usage": "15%"
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
        "supported_formats": ["pdf", "word", "md", "html", "json"],
        "allowed_directories": ["/var/log", "/opt/logs", "/tmp", "/home"],
        "default_chunk_size": 50000,
        "parallel_workers": 4
    }
}
```

### 11.3 系统初始化

**请求**
```http
POST /api/initialize
Content-Type: application/json

{
    "reset": false,
    "create_default_user": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| reset | bool | 否 | false | 是否重置所有数据（谨慎使用） |
| create_default_user | bool | 否 | true | 是否创建默认用户 |

**成功响应**
```json
{
    "code": 0,
    "message": "初始化成功",
    "data": {
        "initialized": true,
        "created_at": "2026-06-01T10:00:00",
        "default_user_created": true
    }
}
```

---

## 11. 错误码定义

| 错误码 | HTTP 状态码 | 说明 | 解决方案 |
|--------|------------|------|---------|
| 0 | 200 | 成功 | - |
| 1 | 400 | 请求参数错误 | 检查请求参数是否完整、格式是否正确 |
| 2 | 401 | 未授权 | 确保请求头中包含 X-User-Id |
| 3 | 403 | 权限不足 | 检查用户是否有权限访问该资源 |
| 4 | 404 | 资源不存在 | 确认资源ID或路径是否正确 |
| 5 | 500 | 服务器内部错误 | 查看服务器日志，联系管理员 |
| 100 | 400 | 文件上传失败 | 检查网络连接和文件完整性 |
| 101 | 400 | 文件类型不支持 | 仅支持 .log, .txt, .zip, .pcap |
| 102 | 400 | 文件大小超限 | 单个文件最大500MB，压缩包解压后最大1GB |
| 200 | 404 | 任务不存在 | 确认task_id是否正确 |
| 201 | 409 | 任务已存在 | 使用force_restart参数或等待现有任务完成 |
| 300 | 500 | 报告生成失败 | 检查源文件是否有效，查看服务器日志 |
| 400 | 403 | 路径不在白名单范围内 | 确认路径是否在允许的目录列表中 |
| 401 | 404 | 路径不存在 | 确认路径是否正确 |
| 402 | 403 | 没有读取路径权限 | 联系管理员配置权限或选择其他路径 |

---

## 12. 数据隔离与存储方案

### 12.1 存储结构

```
users/
├── {user_id}/
│   ├── uploads/           # 上传的文件
│   ├── reports/           # 生成的报告
│   ├── checkpoints/       # 断点续传检查点
│   └── data/              # 用户数据
```

### 12.2 隔离机制

- **目录隔离**：每个用户拥有独立的目录
- **文件名隔离**：文件名包含 user_id 前缀
- **数据库隔离**：所有查询都带 user_id 条件

### 12.3 安全措施

- 文件权限：仅应用进程可读写
- 敏感数据：不存储明文密码或密钥
- 日志审计：记录所有操作日志

---

## 13. 接口调用示例

### 13.1 使用 cURL 调用

**上传文件**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-User-Id: user_001" \
  -F "file=@error.log"
```

**处理日志文件**
```bash
curl -X POST http://localhost:8000/api/process \
  -H "X-User-Id: user_001" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/users/user_001/uploads/error.log", "use_llm": false}'
```

**获取任务状态**
```bash
curl -X GET http://localhost:8000/api/task/user_001_20260601_100000_123456 \
  -H "X-User-Id: user_001"
```

**获取报告列表**
```bash
curl -X GET http://localhost:8000/api/reports \
  -H "X-User-Id: user_001"
```

### 13.2 使用 JavaScript 调用

```javascript
// 配置基础URL
const BASE_URL = 'http://localhost:8000';

// 请求封装
async function apiRequest(endpoint, method = 'GET', data = null, headers = {}) {
    const url = `${BASE_URL}${endpoint}`;
    
    const defaultHeaders = {
        'X-User-Id': 'user_001',
        'Content-Type': 'application/json'
    };
    
    const options = {
        method,
        headers: { ...defaultHeaders, ...headers }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    return response.json();
}

// 示例：上传文件
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${BASE_URL}/api/upload`, {
        method: 'POST',
        headers: { 'X-User-Id': 'user_001' },
        body: formData
    });
    
    return response.json();
}

// 示例：处理日志
async function processLog(filePath) {
    return apiRequest('/api/process', 'POST', {
        file_path: filePath,
        use_llm: false
    });
}

// 示例：轮询任务状态
async function pollTask(taskId) {
    let status;
    do {
        const response = await apiRequest(`/api/task/${taskId}`);
        status = response.data.status;
        console.log(`任务状态: ${status}, 进度: ${response.data.progress}%`);
        
        if (status === 'completed') {
            console.log('任务完成！报告:', response.data.reports);
            break;
        }
        
        if (status === 'failed') {
            console.error('任务失败:', response.data.error);
            break;
        }
        
        // 等待1秒后重试
        await new Promise(resolve => setTimeout(resolve, 1000));
    } while (status === 'pending' || status === 'processing');
}
```

### 13.3 使用 Python 调用

```python
import requests

BASE_URL = 'http://localhost:8000'
HEADERS = {'X-User-Id': 'user_001'}

# 上传文件
def upload_file(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f'{BASE_URL}/api/upload',
            headers={'X-User-Id': 'user_001'},
            files={'file': f}
        )
    return response.json()

# 处理日志
def process_log(file_path, use_llm=True):
    response = requests.post(
        f'{BASE_URL}/api/process',
        headers={**HEADERS, 'Content-Type': 'application/json'},
        json={'file_path': file_path, 'use_llm': use_llm}
    )
    return response.json()

# 获取任务状态
def get_task_status(task_id):
    response = requests.get(
        f'{BASE_URL}/api/task/{task_id}',
        headers=HEADERS
    )
    return response.json()

# 轮询任务
def poll_task(task_id):
    import time
    while True:
        result = get_task_status(task_id)
        status = result['data']['status']
        print(f"任务状态: {status}, 进度: {result['data']['progress']}%")
        
        if status == 'completed':
            print('任务完成！报告:', result['data']['reports'])
            break
        elif status == 'failed':
            print('任务失败:', result['data']['error'])
            break
            
        time.sleep(1)

# 使用示例
if __name__ == '__main__':
    # 上传文件
    upload_result = upload_file('error.log')
    print('上传结果:', upload_result)
    
    # 处理文件
    process_result = process_log(upload_result['data']['file_path'], use_llm=False)
    task_id = process_result['data']['task_id']
    print('任务ID:', task_id)
    
    # 轮询任务状态
    poll_task(task_id)
```