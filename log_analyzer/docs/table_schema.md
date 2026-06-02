# 数据库表结构设计文档

> 版本: v1.0.0
> 更新日期: 2026-06-01
> 数据库: PostgreSQL / MySQL / SQLite (任选)
> 字符集: UTF-8
> 排序规则: utf8mb4_unicode_ci

---

## 目录

1. [设计原则](#1-设计原则)
2. [表结构总览](#2-表结构总览)
3. [用户表 (users)](#3-用户表-users)
4. [历史报告表 (history_reports)](#4-历史报告表-history_reports)
5. [报告文件表 (report_files)](#5-报告文件表-report_files)
6. [任务表 (tasks)](#6-任务表-tasks)
7. [索引策略](#7-索引策略)
8. [数据迁移指南](#8-数据迁移指南)

---

## 1. 设计原则

- **用户隔离**: 所有业务表都包含 user_id 字段，建立严格的数据隔离
- **软删除**: 采用 `is_deleted` + `deleted_at` 实现软删除，保留历史
- **审计字段**: 包含 created_at、updated_at、created_by 等审计字段
- **版本控制**: history_reports 表包含 version 字段，支持乐观锁
- **JSON 字段**: 灵活数据（如 statistics、analysis）使用 JSON 类型
- **索引优化**: 针对高频查询字段（user_id、created_at）建立索引

---

## 2. 表结构总览

```
┌──────────────┐
│    users     │ 1
└──────┬───────┘
       │ 1:N
       ↓
┌──────────────┐         ┌─────────────────┐
│history_      │ 1     N │  report_files   │
│  reports     ├─────────┤                 │
└──────┬───────┘         └─────────────────┘
       │ 1:N
       ↓
┌──────────────┐
│    tasks     │
└──────────────┘
```

---

## 3. 用户表 (users)

存储用户基础信息。

### 3.1 表定义

```sql
CREATE TABLE users (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT  COMMENT '主键ID',
    user_id         VARCHAR(64)     NOT NULL UNIQUE             COMMENT '用户业务ID',
    username        VARCHAR(64)     NOT NULL                    COMMENT '用户名',
    email           VARCHAR(128)    DEFAULT NULL                COMMENT '邮箱',
    avatar          VARCHAR(256)    DEFAULT NULL                COMMENT '头像URL',
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE      COMMENT '是否激活',
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE     COMMENT '是否已删除（软删除）',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    last_login_at   DATETIME        DEFAULT NULL                COMMENT '最近登录时间',
    metadata        JSON            DEFAULT NULL                COMMENT '扩展元数据',
    CONSTRAINT uk_user_id UNIQUE (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户表';
```

### 3.2 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| id | BIGINT | 是 | 自增主键 |
| user_id | VARCHAR(64) | 是 | 用户业务ID，全局唯一 |
| username | VARCHAR(64) | 是 | 用户名 |
| email | VARCHAR(128) | 否 | 邮箱地址 |
| avatar | VARCHAR(256) | 否 | 头像URL |
| is_active | BOOLEAN | 是 | 账户是否激活 |
| is_deleted | BOOLEAN | 是 | 软删除标记 |
| created_at | DATETIME | 是 | 记录创建时间 |
| updated_at | DATETIME | 是 | 记录更新时间 |
| last_login_at | DATETIME | 否 | 最近登录时间 |
| metadata | JSON | 否 | 扩展元数据 |

### 3.3 索引

```sql
CREATE INDEX idx_users_user_id     ON users(user_id);
CREATE INDEX idx_users_is_active   ON users(is_active);
CREATE INDEX idx_users_created_at  ON users(created_at);
```

---

## 4. 历史报告表 (history_reports)

存储历史报告的核心元数据。

### 4.1 表定义

```sql
CREATE TABLE history_reports (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT  COMMENT '主键ID',
    report_id       VARCHAR(64)     NOT NULL UNIQUE             COMMENT '报告业务ID',
    user_id         VARCHAR(64)     NOT NULL                    COMMENT '所属用户ID（数据隔离关键字段）',
    title           VARCHAR(256)    NOT NULL                    COMMENT '报告标题',
    file_name       VARCHAR(256)    NOT NULL                    COMMENT '源文件名',
    file_type       VARCHAR(32)     NOT NULL DEFAULT 'log'      COMMENT '源文件类型（log/txt/zip/pcap）',
    summary         TEXT            DEFAULT NULL                COMMENT '报告摘要',
    statistics      JSON            DEFAULT NULL                COMMENT '统计数据（JSON）',
    analysis        JSON            DEFAULT NULL                COMMENT '分析结果（JSON）',
    tags            JSON            DEFAULT NULL                COMMENT '标签列表（JSON数组）',
    status          VARCHAR(32)     NOT NULL DEFAULT 'completed' COMMENT '报告状态（pending/processing/completed/failed）',
    version         INT             NOT NULL DEFAULT 1          COMMENT '版本号（乐观锁）',
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE     COMMENT '是否已删除（软删除）',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted_at      DATETIME        DEFAULT NULL                COMMENT '删除时间',
    metadata        JSON            DEFAULT NULL                COMMENT '扩展元数据',
    CONSTRAINT uk_report_id UNIQUE (report_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='历史报告表';
```

### 4.2 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| id | BIGINT | 是 | 自增主键 |
| report_id | VARCHAR(64) | 是 | 报告业务ID，全局唯一 |
| user_id | VARCHAR(64) | 是 | **所属用户ID，数据隔离关键字段** |
| title | VARCHAR(256) | 是 | 报告标题 |
| file_name | VARCHAR(256) | 是 | 源文件名 |
| file_type | VARCHAR(32) | 是 | 文件类型 |
| summary | TEXT | 否 | 报告摘要 |
| statistics | JSON | 否 | 统计数据（处理耗时、文件大小、错误数等） |
| analysis | JSON | 否 | 分析结果（LLM 分析内容、错误聚合等） |
| tags | JSON | 否 | 标签列表 |
| status | VARCHAR(32) | 是 | 报告状态 |
| version | INT | 是 | 版本号，用于乐观锁 |
| is_deleted | BOOLEAN | 是 | 软删除标记 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |
| deleted_at | DATETIME | 否 | 删除时间 |
| metadata | JSON | 否 | 扩展元数据 |

### 4.3 索引（关键性能优化）

```sql
-- 用户维度查询主索引（数据隔离 + 性能）
CREATE INDEX idx_hr_user_created  ON history_reports(user_id, created_at DESC);

-- 单用户状态过滤
CREATE INDEX idx_hr_user_status   ON history_reports(user_id, status);

-- 软删除过滤
CREATE INDEX idx_hr_user_active   ON history_reports(user_id, is_deleted, created_at DESC);

-- 报告ID查询
CREATE UNIQUE INDEX uk_hr_report_id ON history_reports(report_id);

-- 全文搜索（可选，用于搜索 title/summary）
CREATE FULLTEXT INDEX ft_hr_title_summary ON history_reports(title, summary);
```

---

## 5. 报告文件表 (report_files)

存储报告的关联文件（MD、HTML、PDF、Word 等多格式）。

### 5.1 表定义

```sql
CREATE TABLE report_files (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT  COMMENT '主键ID',
    file_id         VARCHAR(64)     NOT NULL UNIQUE             COMMENT '文件业务ID',
    report_id       VARCHAR(64)     NOT NULL                    COMMENT '所属报告ID',
    user_id         VARCHAR(64)     NOT NULL                    COMMENT '所属用户ID',
    file_format     VARCHAR(16)     NOT NULL                    COMMENT '文件格式（md/html/pdf/docx/json）',
    file_name       VARCHAR(256)    NOT NULL                    COMMENT '文件名',
    file_path       VARCHAR(512)    NOT NULL                    COMMENT '文件存储路径',
    file_size       BIGINT          NOT NULL DEFAULT 0          COMMENT '文件大小（字节）',
    mime_type       VARCHAR(64)     DEFAULT NULL                COMMENT 'MIME 类型',
    checksum        VARCHAR(64)     DEFAULT NULL                COMMENT '文件校验和（SHA256）',
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE     COMMENT '是否已删除（软删除）',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT uk_file_id UNIQUE (file_id),
    CONSTRAINT fk_rf_report_id FOREIGN KEY (report_id) REFERENCES history_reports(report_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='报告文件表';
```

### 5.2 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| id | BIGINT | 是 | 自增主键 |
| file_id | VARCHAR(64) | 是 | 文件业务ID |
| report_id | VARCHAR(64) | 是 | 所属报告ID（外键） |
| user_id | VARCHAR(64) | 是 | 所属用户ID（冗余字段，便于查询） |
| file_format | VARCHAR(16) | 是 | 文件格式 |
| file_name | VARCHAR(256) | 是 | 文件名 |
| file_path | VARCHAR(512) | 是 | 文件存储路径 |
| file_size | BIGINT | 是 | 文件大小（字节） |
| mime_type | VARCHAR(64) | 否 | MIME 类型 |
| checksum | VARCHAR(64) | 否 | SHA256 校验和 |
| is_deleted | BOOLEAN | 是 | 软删除标记 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

### 5.3 索引

```sql
CREATE INDEX idx_rf_user_id     ON report_files(user_id);
CREATE INDEX idx_rf_report_id   ON report_files(report_id);
CREATE INDEX idx_rf_format      ON report_files(user_id, file_format);
```

---

## 6. 任务表 (tasks)

存储分析任务记录。

### 6.1 表定义

```sql
CREATE TABLE tasks (
    id              BIGINT          PRIMARY KEY AUTO_INCREMENT  COMMENT '主键ID',
    task_id         VARCHAR(64)     NOT NULL UNIQUE             COMMENT '任务业务ID',
    user_id         VARCHAR(64)     NOT NULL                    COMMENT '所属用户ID',
    status          VARCHAR(32)     NOT NULL DEFAULT 'pending'  COMMENT '任务状态',
    progress        DECIMAL(5,2)    NOT NULL DEFAULT 0.00       COMMENT '进度（0-100）',
    message         TEXT            DEFAULT NULL                COMMENT '状态消息',
    file_paths      JSON            DEFAULT NULL                COMMENT '处理文件列表（JSON数组）',
    chunk_size      INT             DEFAULT 50000               COMMENT '分块大小',
    force_restart   BOOLEAN         NOT NULL DEFAULT FALSE      COMMENT '是否强制重启',
    result          JSON            DEFAULT NULL                COMMENT '处理结果',
    error           TEXT            DEFAULT NULL                COMMENT '错误信息',
    started_at      DATETIME        DEFAULT NULL                COMMENT '开始时间',
    finished_at     DATETIME        DEFAULT NULL                COMMENT '结束时间',
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE     COMMENT '是否已删除',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT uk_task_id UNIQUE (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='任务表';
```

### 6.2 索引

```sql
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_user_status  ON tasks(user_id, status);
```

---

## 7. 索引策略

### 7.1 高频查询场景与索引

| 场景 | SQL 示例 | 使用的索引 |
|------|----------|-----------|
| 用户报告列表（按时间倒序） | `SELECT * FROM history_reports WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC` | `idx_hr_user_active` |
| 用户报告搜索 | `SELECT * FROM history_reports WHERE user_id = ? AND title LIKE ?` | `idx_hr_user_active` + `ft_hr_title_summary` |
| 按状态查询 | `SELECT * FROM history_reports WHERE user_id = ? AND status = ?` | `idx_hr_user_status` |
| 单报告查询 | `SELECT * FROM history_reports WHERE report_id = ?` | `uk_hr_report_id` |
| 报告文件查询 | `SELECT * FROM report_files WHERE report_id = ?` | `idx_rf_report_id` |

### 7.2 索引设计原则

1. **最左前缀原则**: 复合索引按查询条件顺序建立
2. **覆盖索引**: 对频繁查询的所有字段建立联合索引
3. **避免过多索引**: 单表索引不超过 6 个
4. **定期分析**: 使用 `EXPLAIN` 分析慢查询

### 7.3 性能预估

| 数据量 | user_id 查询耗时 | 全表扫描耗时 |
|--------|------------------|--------------|
| 1万 | < 5ms | ~50ms |
| 100万 | < 20ms | ~2000ms |
| 1000万 | < 50ms | ~20000ms |

> 注：以上数据基于 MySQL 8.0 + SSD 环境测试

---

## 8. 数据迁移指南

### 8.1 从本地文件迁移到数据库

#### 步骤 1: 设计迁移脚本

```python
# migrate_files_to_db.py
import json
from pathlib import Path
from storage import FileReportStorage
from db_storage import DatabaseReportStorage


def migrate():
    file_storage = FileReportStorage()
    db_storage = DatabaseReportStorage()

    base_dir = Path("log_analyzer/users")
    for user_dir in base_dir.iterdir():
        if not user_dir.is_dir():
            continue

        user_id = user_dir.name
        reports = file_storage.list(user_id, limit=10000)

        for report in reports:
            report_id = report["report_id"]
            full_report = file_storage.get(user_id, report_id)
            if full_report:
                db_storage.create(user_id, full_report)
                print(f"Migrated: {user_id}/{report_id}")

    print("Migration completed!")


if __name__ == "__main__":
    migrate()
```

#### 步骤 2: 双写过渡期

```python
class HybridStorage(ReportStorage):
    """文件 + 数据库双写"""

    def __init__(self):
        self.file_storage = FileReportStorage()
        self.db_storage = DatabaseReportStorage()
        self.write_mode = "both"  # file / db / both

    def create(self, user_id, report_data):
        if self.write_mode in ("file", "both"):
            report_id = self.file_storage.create(user_id, report_data)
        if self.write_mode in ("db", "both"):
            report_id = self.db_storage.create(user_id, report_data)
        return report_id
```

#### 步骤 3: 切换读源

```python
class HybridStorage:
    def get(self, user_id, report_id):
        if self.read_mode == "db":
            return self.db_storage.get(user_id, report_id)
        return self.file_storage.get(user_id, report_id)
```

### 8.2 切换存储后端

通过环境变量切换：

```bash
# 使用文件存储
export STORAGE_TYPE=file

# 使用数据库存储
export STORAGE_TYPE=database
export DATABASE_URL=postgresql://user:pass@localhost/log_analyzer
```

### 8.3 数据库选型建议

| 场景 | 推荐数据库 | 理由 |
|------|-----------|------|
| 中小规模 (< 100万报告) | SQLite | 零配置、易部署 |
| 中大规模 (100万-1000万) | MySQL 8.0 | 成熟稳定、性能好 |
| 大规模 (> 1000万) | PostgreSQL 14+ | JSON 支持强、扩展性好 |
| 海量数据 + 全文搜索 | Elasticsearch | 搜索性能最佳 |

---

## 9. 附录

### A. ER 图

```
┌──────────────────────────────────────┐
│              users                   │
├──────────────────────────────────────┤
│ id (PK)                              │
│ user_id (UK)                         │
│ username                             │
│ email                                │
│ is_active                            │
│ created_at                           │
│ updated_at                           │
└────────────┬─────────────────────────┘
             │ 1:N
             ↓
┌──────────────────────────────────────┐
│         history_reports              │
├──────────────────────────────────────┤
│ id (PK)                              │
│ report_id (UK)                       │
│ user_id (FK)                         │
│ title                                │
│ file_name                            │
│ file_type                            │
│ summary (TEXT)                       │
│ statistics (JSON)                    │
│ analysis (JSON)                      │
│ tags (JSON)                          │
│ status                               │
│ version                              │
│ is_deleted                           │
│ created_at                           │
│ updated_at                           │
│ deleted_at                           │
└────────────┬─────────────────────────┘
             │ 1:N
             ↓
┌──────────────────────────────────────┐
│          report_files                │
├──────────────────────────────────────┤
│ id (PK)                              │
│ file_id (UK)                         │
│ report_id (FK)                       │
│ user_id                              │
│ file_format                          │
│ file_name                            │
│ file_path                            │
│ file_size                            │
│ checksum                             │
│ created_at                           │
│ updated_at                           │
└──────────────────────────────────────┘
```

### B. 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 表名 | 小写+下划线 | `history_reports` |
| 字段名 | 小写+下划线 | `user_id` |
| 主键 | `id` | `id` |
| 业务ID | `{实体}_id` | `report_id`、`user_id` |
| 索引 | `idx_{表}_{字段}` | `idx_hr_user_id` |
| 唯一索引 | `uk_{表}_{字段}` | `uk_hr_report_id` |
| 全文索引 | `ft_{表}_{字段}` | `ft_hr_title_summary` |
| 外键 | `fk_{表}_{关联表}` | `fk_rf_report_id` |

### C. 数据保留策略

```sql
-- 自动清理30天前的软删除记录
DELETE FROM history_reports
WHERE is_deleted = TRUE
  AND deleted_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

---

*文档版本: v1.0.0*
*最后更新: 2026-06-01*
