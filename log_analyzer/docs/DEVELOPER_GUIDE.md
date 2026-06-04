# Log Analyzer 开发者指南

> 版本: v2.2 | 适用: 二次开发 / 插件开发 / 性能调优
>
> 最后更新: 2026-06-02

---

## 目录

1. [开发环境搭建](#1-开发环境搭建)
2. [代码组织约定](#2-代码组织约定)
3. [核心模块开发指南](#3-核心模块开发指南)
4. [扩展点与插件机制](#4-扩展点与插件机制)
5. [API 开发规范](#5-api-开发规范)
6. [前端开发规范](#6-前端开发规范)
7. [性能调优指南](#7-性能调优指南)
8. [测试规范](#8-测试规范)
9. [发布流程](#9-发布流程)

---

## 1. 开发环境搭建

### 1.1 工具链

| 工具 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.10+ | 主语言 |
| pip | 23+ | 包管理 |
| Node.js | 18+ | 前端语法检查 |
| Git | 2.30+ | 版本管理 |
| tshark | 3.6+ | PCAP 分析（可选） |

### 1.2 开发依赖

```bash
pip install -r requirements.txt

# 额外的开发工具
pip install pytest pytest-asyncio black flake8 mypy
```

### 1.3 IDE 推荐配置

#### VSCode

`.vscode/settings.json`：

```json
{
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "120"],
  "[javascript]": {
    "editor.formatOnSave": true
  }
}
```

#### PyCharm

- 标记 `tests/` 为 Test Sources Root
- 标记 `web/static/` 为 Resource Root
- 启用 FastAPI 插件

### 1.4 调试模式

```bash
# 单进程调试（不要用于生产）
uvicorn web.app:app --reload --log-level debug

# 启用性能 profiling
python -m cProfile -o profile.stats main.py --file big.log
```

---

## 2. 代码组织约定

### 2.1 模块划分

```
log_analyzer/
├── parser/         # 纯函数/类库，无状态
├── processor/      # 业务流程，含 I/O
├── llm/            # 外部 API 客户端
├── report/         # 输出生成
├── checkpoint/     # 状态管理
├── config/         # 全局配置
├── utils/          # 通用工具
└── web/            # HTTP 层
```

### 2.2 命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| 类名 | PascalCase | `ChunkProcessor` |
| 函数/方法 | snake_case | `process_file_async` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| 私有方法 | _snake_case | `_load_or_create_checkpoint` |
| 异步函数 | snake_case（不加 _async 后缀） | `process_file()` |
| 数据类 | PascalCase + 名词 | `AnalysisResult` |

### 2.3 类型注解

**强制使用类型注解**：

```python
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class ProcessingResult:
    file_path: str
    total_lines: int
    processed_lines: int
    statistics: Dict[str, int]
    error_entries: List[Dict]
    status: str = "pending"
```

### 2.4 异步编程规范

- **I/O 密集型** → `async/await`
- **CPU 密集型** → `ProcessPoolExecutor` 或 C 扩展
- **混合型** → `asyncio.to_thread()`
- **避免**在同步函数中调用 `asyncio.run` / `loop.run_until_complete`

```python
async def fetch_async(url: str) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 2.5 错误处理

```python
class LogAnalyzerError(Exception):
    """基础异常"""
    pass

class ParseError(LogAnalyzerError):
    """日志解析错误"""
    pass

class LLMError(LogAnalyzerError):
    """LLM 调用错误"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
```

### 2.6 日志规范

```python
import logging
logger = logging.getLogger(__name__)

# 推荐风格
logger.info("开始处理文件: %s, 大小: %d MB", file_path, size_mb)
logger.warning("LLM 调用失败，1s 后重试 (attempt=%d/%d)", attempt, max_attempts)
logger.error("任务处理失败: %s", error, exc_info=True)
```

---

## 3. 核心模块开发指南

### 3.1 解析器扩展（parser/）

**场景**：支持新的日志格式

#### 步骤 1：定义模式

在 `parser/log_parser.py` 中添加正则：

```python
NEW_LOG_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    r'.*?'
    r'\[(?P<level>\w+)\]'
    r'\s*'
    r'(?P<message>.*)$'
)
```

#### 步骤 2：实现解析函数

```python
def parse_new_format(line: str) -> Optional[ParsedLogEntry]:
    match = NEW_LOG_PATTERN.match(line)
    if not match:
        return None
    return ParsedLogEntry(
        timestamp=parse_timestamp(match.group('timestamp')),
        level=parse_level(match.group('level')),
        message=match.group('message'),
        raw_line=line,
        line_number=...,
    )
```

#### 步骤 3：注册到主解析器

```python
class LogParser:
    def __init__(self):
        self.parsers = [
            parse_new_format,
            parse_standard_format,
        ]
```

### 3.2 LLM 客户端扩展（llm/）

**场景**：接入新的 LLM 供应商

#### 步骤 1：实现 Provider 类

```python
class AnthropicProvider(LLMProvider):
    BASE_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    async def chat(self, messages: List[Dict]) -> str:
        # 调用 Anthropic API
        ...
        return response_text
```

#### 步骤 2：注册 Provider

```python
# llm/client.py
PROVIDERS = {
    "openai": OpenAIProvider,
    "deepseek": OpenAIProvider,  # 兼容 OpenAI 协议
    "anthropic": AnthropicProvider,
    "custom": CustomProvider,
}
```

#### 步骤 3：自动识别

```python
def detect_provider(api_url: str) -> str:
    if "anthropic.com" in api_url:
        return "anthropic"
    if "deepseek.com" in api_url:
        return "deepseek"
    return "openai"
```

### 3.3 智能错误合并扩展（report/）

**场景**：扩展错误合并策略、自定义相似度算法、添加新的模式提取规则

#### 步骤 1：自定义合并配置

```python
from report.error_merger import MergeConfig, ErrorMerger

# 创建自定义配置
custom_config = MergeConfig(
    semantic_similarity_threshold=0.7,
    max_examples_per_group=10,
    max_groups=30,
    enable_semantic_merging=True,
    merge_by_error_type=True,
    merge_by_message_pattern=True
)

# 使用配置
merger = ErrorMerger(custom_config)
merged_errors = merger.merge_errors(errors)
```

#### 步骤 2：扩展模式提取规则

```python
class CustomErrorMerger(ErrorMerger):
    def extract_pattern(self, message: str) -> str:
        pattern = super().extract_pattern(message)
        
        # 添加自定义模式提取规则
        # 移除时间戳格式
        pattern = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '[TIME]', pattern)
        # 移除邮箱地址
        pattern = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '[EMAIL]', pattern)
        # 移除电话号码
        pattern = re.sub(r'1[3-9]\d{9}', '[PHONE]', pattern)
        
        return pattern
```

#### 步骤 3：自定义相似度算法

```python
class CustomErrorMerger(ErrorMerger):
    def calculate_string_similarity(self, str1: str, str2: str) -> float:
        # 使用 difflib 的 SequenceMatcher
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
```

#### 步骤 4：自定义合并逻辑

```python
class CustomErrorMerger(ErrorMerger):
    def is_similar_error(self, error1: Dict[str, Any], error2: Dict[str, Any]) -> bool:
        # 先检查默认规则
        if super().is_similar_error(error1, error2):
            return True
        
        # 添加自定义相似度规则
        # 例如：基于错误发生时间的相似性
        time1 = error1.get('timestamp', '')
        time2 = error2.get('timestamp', '')
        if time1 and time2 and time1[:10] == time2[:10]:  # 同一天
            return True
        
        return False
```

#### 预设配置

模块提供三种预设配置：

```python
from report.error_merger import DEFAULT_CONFIG, STRICT_CONFIG, LENIENT_CONFIG

# 默认配置
merger = ErrorMerger(DEFAULT_CONFIG)

# 严格配置（只合并完全相同的错误）
merger = ErrorMerger(STRICT_CONFIG)

# 宽松配置（更多合并）
merger = ErrorMerger(LENIENT_CONFIG)
```

#### 单元测试

参考 `tests/test_intelligent_error_merger.py`：

```python
class TestCustomMerger(unittest.TestCase):
    def test_custom_pattern_extraction(self):
        merger = CustomErrorMerger()
        message = "Error at 2026-06-01 10:00:00 user@example.com"
        pattern = merger.extract_pattern(message)
        self.assertIn('[TIME]', pattern)
        self.assertIn('[EMAIL]', pattern)
```

### 3.4 报告生成扩展（report/）

**场景**：添加新的报告格式（如 Excel）

```python
class ExcelReportWriter:
    def write(self, report: Report, output_path: Path) -> None:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "概览"
        # 填充数据 ...
        wb.save(output_path)
```

注册：

```python
WRITERS = {
    "markdown": MarkdownWriter,
    "html": HTMLWriter,
    "pdf": PDFWriter,
    "docx": DocxWriter,
    "xlsx": ExcelReportWriter,
}
```

### 3.4 存储后端扩展（web/storage.py）

**场景**：实现数据库后端

```python
class DatabaseReportStorage(ReportStorage):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
    
    def create(self, user_id: str, report_data: Dict) -> str:
        with self.engine.connect() as conn:
            report = ReportORM(
                user_id=user_id,
                **report_data
            )
            conn.add(report)
            conn.commit()
            return report.report_id
    
    # ... 其他方法
```

切换：

```python
def get_storage() -> ReportStorage:
    if os.getenv("STORAGE_TYPE") == "database":
        return DatabaseReportStorage(os.getenv("DATABASE_URL"))
    return FileReportStorage()
```

---

## 4. 扩展点与插件机制

### 4.1 自定义错误模式

```python
# parser/log_parser.py
ERROR_PATTERNS = {
    "device_offline": {
        "severity": "high",
        "regex": r"设备不在线|device.*offline",
    },
    # 添加你的自定义模式
    "custom_pattern": {
        "severity": "medium",
        "regex": r"your_pattern_here",
    },
}
```

### 4.2 自定义检查点策略

```python
# checkpoint/manager.py
class CustomCheckpointManager(CheckpointManager):
    def should_save(self, chunk_id: int) -> bool:
        # 自定义保存策略
        return chunk_id % 5 == 0  # 每 5 个 chunk 保存一次
```

### 4.3 自定义报告模板

修改 `report/generator.py` 的 section 方法：

```python
def _create_custom_section(self, result):
    return ReportSection(
        title="自定义分析",
        content="<h2>业务影响评估</h2>..."
    )
```

---

## 5. API 开发规范

### 5.1 路由组织

```python
# web/app.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/history")

@router.get("/reports")
async def list_reports(...): ...

@router.post("/reports")
async def create_report(...): ...
```

### 5.2 响应模型

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "操作成功"
    data: Optional[T] = None
```

### 5.3 错误处理

```python
from fastapi import HTTPException

@router.get("/reports/{report_id}")
async def get_report(report_id: str, user_id: str = Depends(get_current_user_id)):
    report = storage.get(user_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return ApiResponse(data=report)
```

### 5.4 输入验证

```python
from pydantic import BaseModel, Field, validator

class ProcessRequest(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=512)
    chunk_size: int = Field(50000, ge=10000, le=10_000_000)
    force_restart: bool = False
    
    @validator('file_path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('路径不允许包含 ..')
        return v
```

### 5.5 Swagger 注释

```python
@router.post(
    "/process",
    summary="开始处理日志",
    description="提交日志文件进行分析任务，返回 task_id 用于后续查询进度。",
    response_model=ApiResponse[TaskInfo]
)
async def process_file(...):
    """
    - **file_path**: 用户隔离目录下的文件路径
    - **chunk_size**: 分块行数（10K-10M）
    - **force_restart**: 忽略已有检查点
    """
    ...
```

### 5.6 依赖注入

```python
from fastapi import Depends

async def get_report_storage() -> ReportStorage:
    return get_storage()  # 工厂方法

@router.get("/reports")
async def list_reports(
    storage: ReportStorage = Depends(get_report_storage),
    user: UserProfile = Depends(get_current_user)
):
    return ApiResponse(data=storage.list(user.user_id))
```

---

## 6. 前端开发规范

### 6.1 文件结构

```
web/static/
└── index.html    # 单页应用（HTML + CSS + JS 全部内联）
```

> 当前版本采用单文件零依赖方案，便于部署和离线运行。

### 6.2 命名空间

```javascript
// 全局状态
let selectedFiles = [];
let currentTaskId = null;

// 工具函数
function getCurrentUserId() { ... }
function buildTaskUrl(taskId) { ... }

// 业务函数
async function uploadFile(file) { ... }
async function pollTaskUntilDone(taskInfo) { ... }

// 渲染函数
function renderReports(reports) { ... }
```

### 6.3 状态管理

使用 localStorage 持久化关键状态：

```javascript
const STORAGE_KEYS = {
    ACTIVE_TASK: 'logAnalyzer.activeTask',
    USER_ID: 'logAnalyzer.userId',
};

// 保存
localStorage.setItem(STORAGE_KEYS.ACTIVE_TASK, JSON.stringify(taskInfo));

// 读取
const info = JSON.parse(localStorage.getItem(STORAGE_KEYS.ACTIVE_TASK));

// 清除
localStorage.removeItem(STORAGE_KEYS.ACTIVE_TASK);
```

### 6.4 异步错误处理

```javascript
async function pollTaskUntilDone(taskInfo) {
    return new Promise((resolve, reject) => {
        const tick = async () => {
            try {
                const response = await fetch(buildTaskUrl(taskInfo.task_id));
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const task = await response.json();
                
                if (task.status === 'completed') {
                    resolve(task);
                } else {
                    setTimeout(tick, 1000);
                }
            } catch (err) {
                if (reconnectAttempts > MAX) {
                    reject(err);
                } else {
                    setTimeout(tick, retryDelay);
                }
            }
        };
        tick();
    });
}
```

### 6.5 UI 反馈原则

| 操作 | 反馈方式 |
|------|----------|
| 上传成功 | 列表添加 + 状态变化 |
| 上传失败 | 错误横幅 |
| 任务开始 | 进度条出现 |
| 任务完成 | 进度条 100% + 报告列表 |
| 任务失败 | 错误提示 + 重试按钮 |
| 网络中断 | 橙色横幅 + 自动重连 |

---

## 7. 性能调优指南

### 7.1 解析层优化

| 优化项 | 实现 |
|--------|------|
| 大文件读取 | `mmap` 而非逐行 readline |
| 正则编译 | 模块级预编译 |
| 时间戳解析 | `lru_cache` 装饰 |
| 日志对象 | `dataclass(slots=True)` |

### 7.2 LLM 层优化

```python
# llm/client.py
class LLMClient:
    def __init__(self, ...):
        self.semaphore = asyncio.Semaphore(4)  # 控制并发
    
    async def batch_analyze(self, chunks_data, max_concurrent=4):
        tasks = [self._analyze_one(c) for c in chunks_data]
        return await asyncio.gather(*tasks)  # 并行
```

调优参数：

| 参数 | 默认 | 调优建议 |
|------|------|----------|
| 并发数 | 4 | = (API RPM 限制 / 60) × 0.8 |
| 重试次数 | 3 | 5（生产环境） |
| 退避基数 | 1s | 1.5s |
| 超时 | 60s | 120s（长上下文） |

### 7.3 报告生成优化

- 大报告采用流式写入
- PDF/Word 用模板引擎而非拼接
- HTML 静态资源外置

### 7.4 数据库优化（迁移到 DB 时）

```sql
-- 索引
CREATE INDEX idx_reports_user_created 
    ON reports (user_id, created_at DESC);

CREATE INDEX idx_reports_tags 
    ON reports USING gin (tags);

-- 分区
CREATE TABLE reports_2026q2 PARTITION OF reports
    FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
```

### 7.5 性能分析

```bash
# CPU profiling
py-spy record -o profile.svg -- uvicorn web.app:app

# 内存分析
python -m memory_profiler main.py --file big.log

# 网络分析
mitmproxy --mode regular -p 8888
```

---

## 8. 测试规范

### 8.1 目录约定

```
tests/
├── performance/      # 性能基准
│   ├── performance_test.py
│   └── performance_report.txt
├── scripts/          # 测试辅助
├── logs/             # 测试日志
├── test_complete_e2e.py  # E2E 测试
├── test_e2e.sh           # 端到端
├── test_pcap.py
├── test_error_aggregation.py
└── test_merge_strategy.py
```

### 8.2 单元测试

```python
# tests/test_parser.py
import pytest
from parser.log_parser import LogParser

def test_parse_standard_format():
    parser = LogParser()
    line = "2026-06-01 10:00:00 INFO [main] Hello"
    entry = parser.parse_line(line)
    assert entry.level == LogLevel.INFO
    assert entry.message == "Hello"

def test_parse_error_level():
    parser = LogParser()
    line = "2026-06-01 10:00:00 ERROR [main] Failed"
    entry = parser.parse_line(line)
    assert entry.level == LogLevel.ERROR
```

### 8.3 异步测试

```python
import pytest
from llm.client import LLMClient

@pytest.mark.asyncio
async def test_batch_analyze():
    client = LLMClient(config)
    chunks = [...]
    results = await client.batch_analyze(chunks)
    assert len(results) == len(chunks)
```

### 8.4 端到端测试

```python
# tests/test_complete_e2e.py
import requests

def test_full_workflow():
    # 1. 上传
    files = {'file': open('sample.log', 'rb')}
    r = requests.post(
        f"{BASE_URL}/api/upload",
        headers={'X-User-Id': 'test_user'},
        files=files
    )
    assert r.status_code == 200
    
    # 2. 提交任务
    r = requests.post(
        f"{BASE_URL}/api/process",
        headers={'X-User-Id': 'test_user', 'Content-Type': 'application/json'},
        json={'file_path': '...'}
    )
    task_id = r.json()['data']['task_id']
    
    # 3. 轮询
    while True:
        r = requests.get(f"{BASE_URL}/api/task/{task_id}")
        task = r.json()['data']
        if task['status'] == 'completed':
            break
        time.sleep(1)
    
    # 4. 下载报告
    ...
```

### 8.5 性能基准

参考 `tests/performance/performance_test.py`：

```python
def test_100mb_performance():
    start = time.time()
    result = process_file('testdata/100mb.log')
    elapsed = time.time() - start
    
    assert elapsed < 60  # 必须在 60 秒内
    assert result.processed_lines == result.total_lines
```

---

## 9. 发布流程

### 9.1 版本号规范

采用 [SemVer](https://semver.org/lang/zh-CN/)：

- 主版本：破坏性变更
- 次版本：功能新增
- 修订号：问题修复

### 9.2 发布清单

- [ ] 所有测试通过
- [ ] CHANGELOG.md 更新
- [ ] 版本号更新
- [ ] Git tag 标记
- [ ] 文档同步
- [ ] 性能基准报告

### 9.3 Git 工作流

```bash
# 功能开发
git checkout -b feature/new-llm-provider
git commit -m "feat: 添加 Anthropic Provider"
git push origin feature/new-llm-provider

# 合并到 main
git checkout main
git merge --no-ff feature/new-llm-provider

# 打 tag
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0
```

### 9.4 提交信息规范

```
<type>(<scope>): <subject>

type: feat / fix / docs / refactor / perf / test
scope: parser / processor / llm / report / web / docs
subject: 简要描述
```

示例：

```
feat(llm): 添加 Anthropic Provider 支持
fix(parser): 修复时间戳解析时区错误
docs(readme): 更新快速开始章节
perf(processor): 优化 mmap 读取性能
```

---

## 附录 A：常见开发任务清单

| 任务 | 文件 | 步骤 |
|------|------|------|
| 添加新 LLM | `llm/client.py` | 实现 Provider + 注册 |
| 添加新报告格式 | `report/generator.py` | 实现 Writer + 注册 |
| 添加新 API | `web/app.py` | 新路由 + 依赖注入 |
| 添加新错误模式 | `parser/log_parser.py` | ERROR_PATTERNS |
| 修改存储后端 | `web/storage.py` | 实现 ReportStorage 子类 |
| 修改前端 | `web/static/index.html` | 单文件 SPA |

---

## 附录 B：依赖说明

| 包 | 用途 | 必须 |
|---|------|------|
| fastapi | Web 框架 | ✓ |
| uvicorn | ASGI 服务器 | ✓ |
| httpx | 异步 HTTP 客户端 | ✓ |
| pydantic | 数据校验 | ✓ |
| aiofiles | 异步文件 I/O | ✓ |
| python-docx | Word 报告 | ✓ |
| reportlab | PDF 报告 | ✓ |
| pytest | 测试 | 开发环境 |
| pytest-asyncio | 异步测试 | 开发环境 |
| black | 格式化 | 开发环境 |
| flake8 | 代码检查 | 开发环境 |
| mypy | 类型检查 | 开发环境 |

---

如有问题或建议，请在项目根目录创建 `docs/debug/your-issue.md` 记录并提交 PR。
