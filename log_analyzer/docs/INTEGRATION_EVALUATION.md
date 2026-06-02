# 用户操作历史记录功能整合评估报告

## 一、需求分析

### 1.1 新需求：用户操作历史记录

| 需求点 | 描述 |
|--------|------|
| 功能定义 | 记录用户在系统中的所有关键操作行为，包括页面访问、按钮点击、API请求等 |
| 数据存储 | 持久化存储在后台文件系统中，确保数据安全性和可追溯性 |
| 查询接口 | 支持按用户ID、时间范围、操作类型等条件进行筛选查询 |
| 性能要求 | 高效记录，不影响主系统响应速度；支持分页查询 |
| 权限控制 | 用户只能访问自己的历史记录 |

### 1.2 现有功能：历史报告

| 功能点 | 描述 |
|--------|------|
| 功能定义 | 记录用户的日志分析报告元数据 |
| 数据存储 | 持久化存储在 `data/reports_db/{user_id}/` |
| 查询接口 | 支持关键词搜索、分页列表 |
| 数据结构 | 包含标题、摘要、统计数据、分析结果、关联文件等 |

---

## 二、兼容性分析

### 2.1 数据结构对比

**历史报告数据结构**：
```python
{
    "report_id": "rpt_20260601_143000_abc123",
    "user_id": "user_001",
    "title": "系统异常分析报告",
    "file_name": "error.log",
    "file_type": "log",
    "summary": "...",
    "statistics": {...},
    "analysis": {...},
    "files": [...],
    "tags": [],
    "metadata": {},
    "created_at": "2026-06-01T14:30:00",
    "updated_at": "2026-06-01T14:30:00",
    "version": 1
}
```

**操作历史数据结构**：
```python
{
    "action_id": "act_20260602_100000_abc123",
    "user_id": "user_001",
    "action_type": "api_request",
    "action_name": "POST /api/process",
    "resource": "/api/process",
    "details": {...},
    "timestamp": "2026-06-02T10:00:00",
    "duration_ms": 1500,
    "status": "success"
}
```

### 2.2 存储方式对比

| 维度 | 历史报告 | 操作历史 |
|------|---------|---------|
| **存储路径** | `data/reports_db/{user_id}/{report_id}.json` | `data/action_logs/{user_id}/{date}.json` |
| **分片策略** | 按报告ID | 按日期分片 |
| **索引方式** | `_index.json` | `_index.json` + 日期列表 |
| **数据大小** | KB-MB级 | 字节级 |

### 2.3 查询需求对比

| 维度 | 历史报告 | 操作历史 |
|------|---------|---------|
| **主要查询方式** | 关键词搜索 | 时间范围筛选 |
| **次要查询方式** | 分页列表 | 操作类型筛选 |
| **排序方式** | 按创建时间 | 按时间降序 |
| **查询频率** | 低频 | 中高频 |

### 2.4 核心差异矩阵

| 维度 | 历史报告 | 操作历史 | 差异程度 |
|------|---------|---------|---------|
| 数据类型 | 重量级分析结果 | 轻量级行为记录 | 高 |
| 数据大小 | KB-MB | 字节级 | 高 |
| 写入频率 | 低频（分析完成后） | 高频（每次交互） | 高 |
| 查询模式 | 关键词搜索 | 时间范围筛选 | 高 |
| 保留周期 | 长期保留 | 可配置保留期限 | 中 |
| 数据结构 | 复杂嵌套 | 扁平简单 | 中 |

---

## 三、整合可行性评估

### 3.1 整合方案分析

**方案A：统一存储**
- 将操作历史和历史报告存储在同一目录结构下
- 共用索引文件和查询接口
- **优点**：统一管理，减少代码重复
- **缺点**：
  - 写入模式冲突：高频写入 vs 低频写入
  - 查询模式冲突：时间范围 vs 关键词搜索
  - 数据生命周期不同：需要定期清理操作历史，但保留报告
  - 性能影响：高频写入可能影响报告查询性能

**方案B：独立存储，统一接口**
- 各自独立存储，但通过统一的API网关对外提供服务
- **优点**：内部独立，对外统一
- **缺点**：增加复杂度，需要额外的API聚合层

**方案C：完全独立**
- 各自独立实现存储和接口
- 保持一致的设计模式（抽象接口、用户隔离、分页查询）
- **优点**：
  - 互不影响，各自优化
  - 便于独立扩展和维护
  - 保留未来整合的可能性
- **缺点**：代码略有重复

### 3.2 决策依据

| 评估维度 | 方案A | 方案B | 方案C |
|----------|-------|-------|-------|
| 性能影响 | 高风险 | 中 | 低 |
| 代码复杂度 | 中 | 高 | 低 |
| 可维护性 | 中 | 中 | 高 |
| 扩展性 | 中 | 高 | 高 |
| 实现成本 | 低 | 高 | 中 |
| 数据隔离性 | 低 | 中 | 高 |

**综合评估**：选择方案C（完全独立）

**决策理由**：
1. **性能考虑**：操作历史是高频写入场景，独立存储可避免影响历史报告的查询性能
2. **数据生命周期**：操作历史可能需要定期清理，而历史报告需要长期保留，独立存储便于分别管理
3. **查询模式差异**：历史报告主要是关键词搜索，操作历史主要是时间范围查询，独立实现可各自优化
4. **代码清晰性**：保持各自的职责边界，代码更清晰，易于维护
5. **未来扩展性**：保持一致的设计模式，未来如需整合可通过API网关层实现

---

## 四、独立实现方案

### 4.1 存储结构设计

```
log_analyzer/
├── data/
│   ├── reports_db/              # 历史报告存储
│   │   └── {user_id}/
│   │       ├── {report_id}.json
│   │       └── _index.json
│   │
│   └── action_logs/             # 操作历史存储（新增）
│       └── {user_id}/
│           ├── {date}.json      # 按日期分片
│           └── _index.json
```

### 4.2 抽象接口设计

**ReportStorage（历史报告）**：
```python
class ReportStorage(ABC):
    def create(self, user_id, report_data) -> str
    def get(self, user_id, report_id) -> Optional[Dict]
    def list(self, user_id, limit, offset) -> List[Dict]
    def update(self, user_id, report_id, data) -> bool
    def delete(self, user_id, report_id) -> bool
    def search(self, user_id, keyword, limit) -> List[Dict]
```

**ActionLogStorage（操作历史）**：
```python
class ActionLogStorage(ABC):
    def record(self, user_id, action_type, action_name, ...) -> str
    def query(self, user_id, start_time, end_time, action_type, ...) -> Tuple[List[Dict], int]
    def get(self, user_id, action_id) -> Optional[Dict]
    def delete(self, user_id, action_id) -> bool
    def delete_by_time_range(self, user_id, before_time) -> int
    def count(self, user_id) -> int
```

### 4.3 API接口设计

| 历史报告接口 | 操作历史接口 |
|-------------|-------------|
| `POST /api/history/reports` | `POST /api/history/actions` |
| `GET /api/history/reports` | `GET /api/history/actions/{action_id}` |
| `GET /api/history/reports/{report_id}` | `DELETE /api/history/actions/{action_id}` |
| `PUT /api/history/reports/{report_id}` | `DELETE /api/history/actions/cleanup` |
| `DELETE /api/history/reports/{report_id}` | `GET /api/history/actions/count` |
| | `GET /api/history/actions/types` |

---

## 五、实现要点

### 5.1 性能优化

| 优化点 | 实现方式 |
|--------|----------|
| 高频写入 | 按日期分片存储，减少单文件大小 |
| 查询性能 | 索引文件记录日期列表，避免遍历所有文件 |
| 并发安全 | 使用锁机制保护写入操作 |
| 分页查询 | 支持 limit/offset 参数 |

### 5.2 权限控制

- 所有接口通过 `X-User-Id` 请求头识别用户身份
- 存储层按 `user_id` 隔离数据
- 查询时自动过滤非当前用户的数据

### 5.3 数据清理

- 提供 `delete_by_time_range` 接口支持按时间清理
- 建议定期执行清理任务（如保留最近30天数据）

---

## 六、总结

### 6.1 决策结论

**不建议将历史报告功能与用户操作历史记录功能整合**，应各自独立实现。

### 6.2 决策依据

1. **写入模式差异大**：操作历史是高频写入（每次用户交互），历史报告是低频写入（分析完成后）
2. **查询模式不同**：操作历史主要按时间范围查询，历史报告主要按关键词搜索
3. **数据生命周期不同**：操作历史可定期清理，历史报告需要长期保留
4. **性能要求不同**：操作历史需要高写入性能，历史报告需要高读取性能

### 6.3 实施建议

1. 创建独立的 `action_logger.py` 模块实现操作历史记录功能
2. 设计独立的存储结构 `data/action_logs/{user_id}/{date}.json`
3. 开发独立的API接口 `/api/history/actions/*`
4. 保持与历史报告相同的设计模式（抽象接口、用户隔离、分页查询）
5. 提供数据清理接口，支持定期清理旧数据

---

**文档版本**: v1.0.0  
**创建日期**: 2026-06-02  
**适用版本**: Log Analyzer v2.1+
