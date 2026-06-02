# Log Analyzer API 接口文档 (v2.2 - 简化认证版)

> 版本: v2.2.0
> 更新日期: 2026-06-02
> 基础URL: `http://localhost:8000`

---

## 目录

1. [概述](#1-概述)
2. [用户识别机制](#2-用户识别机制)
3. [认证接口](#3-认证接口)
4. [文件管理接口](#4-文件管理接口)
5. [日志处理接口](#5-日志处理接口)
6. [任务管理接口](#6-任务管理接口)
7. [报告接口](#7-报告接口)
8. [历史报告 CRUD 接口](#8-历史报告-crud-接口)
9. [用户操作历史记录接口](#13-用户操作历史记录接口)
10. [数据备份接口](#9-数据备份接口)
11. [系统接口](#10-系统接口)
12. [错误码定义](#11-错误码定义)
13. [数据隔离与存储方案](#12-数据隔离与存储方案)

---

## 1. 概述

### 1.1 接口变更说明

本版本对认证机制做了重大调整：
- **移除 Token 鉴权**：不再需要登录、Token验证、登出等流程
- **采用请求头识别用户身份**：通过 `X-User-Id` 头传递用户ID
- **默认用户支持**：未携带头时使用 `default_user`

### 1.2 通用请求头

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-User-Id` | 否 | 用户业务ID（缺失则使用 `default_user`） |
| `X-Username` | 否 | 用户名（用于显示，可选） |
| `Content-Type` | 是 | `application/json` 或 `multipart/form-data` |

### 1.3 统一响应格式

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
| username | string | 否 | 用户名 |

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

> 此接口直接读取 `X-User-Id` 请求头，无需调用 identify。

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
        "file_path": "/log_analyzer/users/user_001/uploads/example.log",
        "file_name": "example.log",
        "file_size": "1.23 MB",
        "extracted_files": [
            {
                "path": "/log_analyzer/users/user_001/uploads/example.log",
                "name": "example.log",
                "size": "1.23 MB"
            }
        ]
    }
}
```

### 4.2 列出目录

**请求**
```http
GET /api/list-directory?path=/some/path
X-User-Id: user_001
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 否 | 目录路径，缺省返回用户上传目录 |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "current_path": "/log_analyzer/users/user_001/uploads",
        "parent_path": "/log_analyzer/users/user_001",
        "directories": [...],
        "files": [...]
    }
}
```

### 4.3 下载文件

**请求**
```http
GET /api/download/{file_path}
X-User-Id: user_001
```

> 只能下载用户自己目录下的文件。

---

## 5. 日志处理接口

### 5.1 开始处理

**请求**
```http
POST /api/process
X-User-Id: user_001
Content-Type: application/json

{
    "file_path": "/log_analyzer/users/user_001/uploads/example.log",
    "chunk_size": 50000,
    "force_restart": false
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_path | string | 否 | 单个文件路径 |
| directory_path | string | 否 | 目录路径 |
| chunk_size | int | 否 | 分块大小，默认50000 |
| force_restart | bool | 否 | 是否强制重新处理 |

**成功响应**
```json
{
    "code": 0,
    "message": "任务已创建，正在处理 1 个文件",
    "data": {
        "task_id": "user_001_20260601_143000_123456",
        "status": "pending",
        "message": "任务已创建，正在处理 1 个文件"
    }
}
```

> 处理完成后，系统会自动创建历史报告记录。

---

## 6. 任务管理接口

### 6.1 查询任务状态

**请求**
```http
GET /api/task/{task_id}
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "task_id": "user_001_20260601_143000_123456",
        "status": "completed",
        "progress": 100.0,
        "message": "处理完成！共处理 3 个文件",
        "reports": [...],
        "error": null
    }
}
```

---

## 7. 报告接口

### 7.1 获取报告文件列表

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
                "name": "report_test.log_20260601_143000.md",
                "path": "/log_analyzer/users/user_001/reports/report_test.log_20260601_143000.md",
                "size": 12345,
                "size_str": "12.05 KB",
                "modified": "2026-06-01T14:30:00",
                "type": "markdown"
            }
        ]
    }
}
```

---

## 8. 历史报告 CRUD 接口

> 这些接口提供持久化的报告元数据管理，独立于文件报告。数据存储在 `log_analyzer/data/reports_db/{user_id}/`。

### 8.1 创建历史报告

**请求**
```http
POST /api/history/reports
X-User-Id: user_001
Content-Type: application/json

{
    "title": "系统异常分析报告",
    "file_name": "error.log",
    "file_type": "log",
    "summary": "本次共发现 12 个错误...",
    "statistics": {
        "total_chunks": 5,
        "error_count": 12
    },
    "analysis": {
        "key_findings": [...],
        "suggestions": [...]
    },
    "files": [
        {"name": "report.md", "type": "markdown", "path": "..."}
    ],
    "tags": ["urgent", "production"],
    "metadata": {
        "source": "auto",
        "version": "1.0"
    }
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 报告标题 |
| file_name | string | 是 | 源文件名 |
| file_type | string | 否 | 文件类型，默认 log |
| summary | string | 否 | 报告摘要 |
| statistics | object | 否 | 统计数据 |
| analysis | object | 否 | 分析结果 |
| files | array | 否 | 关联文件列表 |
| tags | array | 否 | 标签列表 |
| metadata | object | 否 | 扩展元数据 |

**成功响应**
```json
{
    "code": 0,
    "message": "创建成功",
    "data": {
        "report_id": "rpt_20260601_143000_abc12345"
    }
}
```

### 8.2 查询历史报告列表

**请求**
```http
GET /api/history/reports?limit=20&offset=0&keyword=error
X-User-Id: user_001
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量限制，默认100 |
| offset | int | 否 | 偏移量，默认0 |
| keyword | string | 否 | 搜索关键词（标题/文件名/摘要） |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "reports": [
            {
                "report_id": "rpt_20260601_143000_abc12345",
                "title": "系统异常分析报告",
                "file_name": "error.log",
                "file_type": "log",
                "created_at": "2026-06-01T14:30:00",
                "updated_at": "2026-06-01T14:30:00"
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0
    }
}
```

### 8.3 查询单个历史报告

**请求**
```http
GET /api/history/reports/{report_id}
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "report_id": "rpt_20260601_143000_abc12345",
        "user_id": "user_001",
        "title": "系统异常分析报告",
        "file_name": "error.log",
        "file_type": "log",
        "summary": "...",
        "statistics": {...},
        "analysis": {...},
        "files": [...],
        "tags": [...],
        "metadata": {...},
        "created_at": "2026-06-01T14:30:00",
        "updated_at": "2026-06-01T14:30:00",
        "version": 1
    }
}
```

### 8.4 更新历史报告

**请求**
```http
PUT /api/history/reports/{report_id}
X-User-Id: user_001
Content-Type: application/json

{
    "title": "更新后的标题",
    "summary": "更新后的摘要",
    "tags": ["resolved", "archived"]
}
```

**成功响应**
```json
{
    "code": 0,
    "message": "更新成功",
    "data": null
}
```

### 8.5 删除历史报告

**请求**
```http
DELETE /api/history/reports/{report_id}
X-User-Id: user_001
```

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

### 9.1 创建数据备份

**请求**
```http
POST /api/backup/create
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "备份成功",
    "data": {
        "backup_path": "/log_analyzer/data/backups/user_001_20260601_143000"
    }
}
```

---

## 10. 系统接口

### 10.1 健康检查

**请求**
```http
GET /api/health
```

**响应**
```json
{
    "status": "ok",
    "message": "Log Analyzer API is running"
}
```

---

## 11. 错误码定义

### 11.1 业务错误码

| code | message | 说明 |
|------|---------|------|
| 0 | 成功 | 操作成功 |
| 1 | 操作失败 | 通用错误码 |

### 11.2 错误消息字典

| code | message | 说明 |
|------|---------|------|
| 1 | 不支持的文件类型 | 上传文件类型不符 |
| 1 | 文件不存在 | 文件路径不存在 |
| 1 | 目录不存在 | 目录路径不存在 |
| 1 | 未找到可处理的日志文件 | 指定路径下无日志文件 |
| 1 | 任务不存在 | task_id无效 |
| 1 | 报告不存在 | report_id无效 |
| 1 | 无权访问此文件 | 跨用户访问文件 |

---

## 12. 数据隔离与存储方案

### 12.1 本地文件存储结构

```
log_analyzer/
├── users/                          # 用户文件目录
│   └── {user_id}/
│       ├── uploads/                # 用户上传文件
│       ├── reports/                # 用户报告文件（md/html/pdf/docx）
│       └── checkpoints/            # 用户检查点
│
├── data/                           # 用户数据存储目录
│   ├── reports_db/                 # 历史报告数据库（文件版）
│   │   └── {user_id}/
│   │       ├── {report_id}.json   # 单个报告完整数据
│   │       └── _index.json        # 用户报告索引
│   │
│   └── backups/                    # 数据备份
│       └── {user_id}_{timestamp}/
│           └── data/...
│
└── auth/
    └── users.json                  # 用户档案
```

### 12.2 数据隔离机制

所有业务接口都基于 `X-User-Id` 请求头识别用户身份，确保：

1. **文件存储隔离**: 每个用户的文件存储在 `users/{user_id}/` 目录下
2. **报告数据隔离**: 历史报告按 `user_id` 字段隔离存储
3. **下载权限隔离**: 用户只能下载 `users/{user_id}/` 目录下的文件
4. **备份隔离**: 每个用户的数据独立备份

### 12.3 数据库迁移准备

当前使用 `FileReportStorage` 实现，支持平滑迁移到数据库：

```python
# 切换存储后端
export STORAGE_TYPE=database
export DATABASE_URL=postgresql://user:pass@localhost/log_analyzer
```

`DatabaseReportStorage` 已预留接口，详见 [docs/table_schema.md](table_schema.md)。

### 12.4 抽象接口

```python
class ReportStorage(ABC):
    def create(self, user_id, report_data) -> str
    def get(self, user_id, report_id) -> Optional[Dict]
    def list(self, user_id, limit, offset) -> List[Dict]
    def update(self, user_id, report_id, data) -> bool
    def delete(self, user_id, report_id) -> bool
    def search(self, user_id, keyword, limit) -> List[Dict]
```

---

## 13. 用户操作历史记录接口

### 13.1 概述

用户操作历史记录功能用于记录用户在系统中的所有关键操作行为，包括页面访问、按钮点击、API请求等交互行为，形成完整的用户使用轨迹。

### 13.2 操作类型定义

| 类型 | 说明 |
|------|------|
| `page_view` | 页面访问 |
| `button_click` | 按钮点击 |
| `api_request` | API请求 |
| `file_upload` | 文件上传 |
| `file_download` | 文件下载 |
| `report_view` | 报告查看 |
| `task_start` | 任务开始 |
| `task_complete` | 任务完成 |
| `task_failed` | 任务失败 |
| `user_login` | 用户登录 |
| `user_logout` | 用户登出 |

### 13.3 查询操作历史记录

**请求**
```http
POST /api/history/actions
X-User-Id: user_001
Content-Type: application/json

{
    "start_time": "2026-06-01T00:00:00",
    "end_time": "2026-06-30T23:59:59",
    "action_type": "api_request",
    "limit": 20,
    "offset": 0
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_time | string | 否 | 开始时间（ISO格式） |
| end_time | string | 否 | 结束时间（ISO格式） |
| action_type | string | 否 | 操作类型筛选 |
| limit | int | 否 | 返回数量限制，默认100 |
| offset | int | 否 | 偏移量，默认0 |

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "records": [
            {
                "action_id": "act_20260602_100000_abc123",
                "user_id": "user_001",
                "action_type": "api_request",
                "action_name": "POST /api/process",
                "resource": "/api/process",
                "details": {
                    "method": "POST",
                    "status_code": 200
                },
                "timestamp": "2026-06-02T10:00:00",
                "duration_ms": 1500,
                "status": "success"
            }
        ],
        "total": 150,
        "limit": 20,
        "offset": 0
    }
}
```

### 13.4 获取单条操作记录

**请求**
```http
GET /api/history/actions/{action_id}
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "action_id": "act_20260602_100000_abc123",
        "user_id": "user_001",
        "action_type": "file_upload",
        "action_name": "上传文件: error.log",
        "resource": "error.log",
        "details": {"file_size": 123456},
        "timestamp": "2026-06-02T10:00:00",
        "duration_ms": 0,
        "status": "success"
    }
}
```

### 13.5 删除单条操作记录

**请求**
```http
DELETE /api/history/actions/{action_id}
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "删除成功",
    "data": null
}
```

### 13.6 清理历史记录

**请求**
```http
DELETE /api/history/actions/cleanup?before_time=2026-01-01T00:00:00
X-User-Id: user_001
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| before_time | string | 是 | 删除此时间之前的所有记录 |

**成功响应**
```json
{
    "code": 0,
    "message": "清理成功",
    "data": {"deleted_count": 50}
}
```

### 13.7 统计操作记录数

**请求**
```http
GET /api/history/actions/count
X-User-Id: user_001
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {"count": 150}
}
```

### 13.8 获取操作类型列表

**请求**
```http
GET /api/history/actions/types
```

**成功响应**
```json
{
    "code": 0,
    "message": "获取成功",
    "data": {
        "types": ["page_view", "button_click", "api_request", ...],
        "description": {
            "page_view": "页面访问",
            "button_click": "按钮点击",
            "api_request": "API请求",
            "file_upload": "文件上传",
            "file_download": "文件下载",
            "report_view": "报告查看",
            "task_start": "任务开始",
            "task_complete": "任务完成",
            "task_failed": "任务失败",
            "user_login": "用户登录",
            "user_logout": "用户登出"
        }
    }
}
```

---

## 14. 附录

### A. 前端调用示例

```javascript
const API_BASE = 'http://localhost:8000';
const USER_ID = 'user_001';

const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': USER_ID
};

// 创建历史报告
async function createReport(data) {
    return fetch(`${API_BASE}/api/history/reports`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
    }).then(r => r.json());
}

// 查询历史报告
async function listReports(keyword = '') {
    return fetch(`${API_BASE}/api/history/reports?keyword=${keyword}`, {
        headers
    }).then(r => r.json());
}

// 更新历史报告
async function updateReport(reportId, data) {
    return fetch(`${API_BASE}/api/history/reports/${reportId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(data)
    }).then(r => r.json());
}

// 删除历史报告
async function deleteReport(reportId) {
    return fetch(`${API_BASE}/api/history/reports/${reportId}`, {
        method: 'DELETE',
        headers
    }).then(r => r.json());
}
```

### B. 相关文档

- [API 详细设计](API.md)
- [数据库表结构](table_schema.md)
- [项目 README](../README.md)

---

*文档版本: v2.0.0*
*最后更新: 2026-06-01*
