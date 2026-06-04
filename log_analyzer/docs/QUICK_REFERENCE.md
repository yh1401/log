# Log Analyzer 快速参考

> 版本: v2.5.0 | 更新日期: 2026-06-04

---

## 快速链接

- [完整文档](./PROJECT_OVERVIEW.md) - 详细的项目概述
- [API文档](./API.md) - 完整的接口规范
- [用户指南](./USER_GUIDE.md) - 详细使用说明
- [开发者指南](./DEVELOPER_GUIDE.md) - 开发规范
- [变更日志](./CHANGELOG.md) - 版本更新记录

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 日志分析 | 支持LLM模式和规则模式双模式分析 |
| 文件上传 | 支持.log、.txt、.zip格式 |
| 服务器路径读取 | 直接读取服务器指定路径的日志文件 |
| 报告生成 | 支持PDF、Word、Markdown、HTML格式 |
| 网络抓包分析 | PCAP/PCAPNG格式自动解析 |
| 操作日志 | 记录所有用户操作行为 |
| 历史报告管理 | CRUD操作，支持查询和删除 |

---

## 常用接口

### 认证
```http
POST /api/auth/identify    # 用户身份识别
GET  /api/auth/current     # 获取当前用户
```

### 文件管理
```http
POST /api/upload           # 上传文件
POST /api/list-dir          # 目录浏览/验证
POST /api/process-from-path # 从路径处理文件
```

### 任务管理
```http
POST /api/process           # 创建处理任务
GET  /api/task/{task_id}   # 查询任务状态
```

### 报告
```http
GET  /api/reports           # 获取报告列表
GET  /api/download/{path}   # 下载报告文件
```

### 历史管理
```http
POST /api/history/actions    # 查询操作日志
GET  /api/history/actions/count  # 操作统计
```

---

## 请求头

```http
X-User-Id: admin001        # 用户ID（必填）
X-Username: admin          # 用户名（可选）
Content-Type: application/json  # 或 multipart/form-data
```

---

## 响应格式

```json
{
    "code": 0,              // 0=成功，非0=失败
    "message": "操作成功",
    "data": { ... }
}
```

---

## 用户权限

| 功能 | 权限 |
|------|------|
| 历史报告管理 | 只能查看和管理自己的报告 |
| 操作日志查询 | 可以查看所有用户的操作记录 |
| 操作统计 | 可以查看所有用户的统计数据 |

---

## 文件命名规则

### 日志文件
- 普通任务：`web_process_YYYYMMDD_HHMMSS_文件名.log`
- 路径任务：`web_path_YYYYMMDD_HHMMSS_文件名.log`

### 报告文件
- 普通任务：`report_【文件名】_时间戳.html`
- 路径任务：`report_path_【文件名】_时间戳.html`

---

## 数据存储

| 类型 | 路径 |
|------|------|
| 上传文件 | `data/uploads/{user_id}/` |
| 报告文件 | `data/reports/{user_id}/` |
| 任务信息 | `data/tasks/` |
| 操作日志 | `data/action_logs/{user_id}/` |
| 系统日志 | `logs/` |

---

## 启动服务

```bash
cd web
./start.sh
# 服务地址：http://localhost:8000
```

---

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v2.5.0 | 2026-06-04 | 操作日志埋点、多用户权限优化 |
| v2.4.0 | 2026-06-03 | 规则模式日志分析器 |
| v2.3.0 | 2026-06-02 | 智能错误合并功能 |
| v2.2.0 | 2026-06-02 | PCAP提示词优化 |

---

*本文档为快速参考，详细信息请查看完整文档*
