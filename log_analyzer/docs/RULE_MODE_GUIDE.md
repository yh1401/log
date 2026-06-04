# 规则模式使用指南

> 版本: v1.0 | 最后更新: 2026-06-03

---

## 目录

1. [概述](#1-概述)
2. [快速开始](#2-快速开始)
3. [功能特性](#3-功能特性)
4. [使用方法](#4-使用方法)
5. [前端交互](#5-前端交互)
6. [技术架构](#6-技术架构)
7. [适用场景](#7-适用场景)
8. [常见问题](#8-常见问题)

---

## 1. 概述

规则模式日志分析器是日志分析系统的可选功能，允许用户在不依赖 LLM（大语言模型）的情况下对日志进行分析。该模式使用预定义的规则和算法来识别、分类和总结错误，提供快速、轻量级的日志分析能力。

**核心优势：**
- **零成本**：不调用外部 API
- **极速响应**：<1 秒处理 1000 条日志
- **可预测**：结果基于预定义规则，输出格式稳定
- **脱机可用**：无需网络连接

---

## 2. 快速开始

### 2.1 API 调用

设置 `use_llm: false` 启用规则模式：

```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user_001" \
  -d '{
    "file_path": "/path/to/your.log",
    "use_llm": false
  }'
```

### 2.2 Web 界面使用

在 Web 界面上传日志文件时，取消勾选"使用 LLM 分析"复选框即可切换到规则模式。

### 2.3 Python SDK 使用

```python
from log_analyzer.processor.chunk_processor import ChunkProcessor
from log_analyzer.parser.log_parser import LogParser
from log_analyzer.checkpoint.manager import CheckpointManager

# 初始化组件
parser = LogParser()
checkpoint_manager = CheckpointManager()

# 创建处理器，use_llm=False 表示使用规则模式
processor = ChunkProcessor(
    parser=parser,
    checkpoint_manager=checkpoint_manager,
    use_llm=False  # 关键参数
)

# 处理文件
result = await processor.process_file("/path/to/logfile.log")
```

---

## 3. 功能特性

### 3.1 多层次错误分类

规则模式使用预定义的错误分类体系：

| 级别 | 描述 | 示例 |
|------|------|------|
| **Critical** | 系统级错误 | 空指针异常、内存溢出 |
| **High** | 服务级错误 | 数据库异常、网络错误 |
| **Medium** | 业务逻辑错误 | 验证错误、参数错误 |
| **Low** | 警告信息 | 弃用警告、配置建议 |

### 3.2 根本原因识别

系统通过关键词匹配识别错误的根本原因：

- 空引用（null_reference）
- 资源泄漏（resource_leak）
- 超时问题（timeout）
- 认证授权问题（authentication）
- 数据库错误（database）
- 网络错误（network）
- 配置错误（configuration）
- 内存问题（memory）

### 3.3 智能建议生成

根据错误类型自动生成整改建议：

```json
{
  "error_type": "database_connection",
  "suggestion": "检查数据库连接配置，确认数据库服务正在运行，验证网络连通性",
  "severity": "High"
}
```

### 3.4 统计分析

生成完整的统计报告：
- 日志级别分布
- 错误类型分布
- 时间趋势分析
- Top 错误统计

---

## 4. 使用方法

### 4.1 API 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | string | - | 日志文件路径（必填） |
| `use_llm` | bool | true | 是否使用 LLM（false 启用规则模式） |
| `output_format` | string | pdf | 输出格式：pdf/word/md |
| `merge_threshold` | float | 0.8 | 错误合并相似度阈值 |

### 4.2 环境变量

```bash
# 设置规则模式为默认模式
export LOG_ANALYZER_DEFAULT_MODE=rule

# 设置合并阈值
export LOG_ANALYZER_MERGE_THRESHOLD=0.75
```

### 4.3 CLI 命令

```bash
# 使用规则模式处理文件
python main.py --file /path/to/logfile.log --rule-based

# 设置合并阈值
python main.py --file /path/to/logfile.log --rule-based --threshold 0.7
```

---

## 5. 前端交互

### 5.1 UI 组件

在设置区域添加了"使用 LLM 分析"复选框：

```html
<div class="setting-item">
    <label class="setting-label checkbox-label">
        <input type="checkbox" id="useLlm" checked>
        使用 LLM 分析（取消则使用规则模式）
    </label>
</div>
```

### 5.2 模式说明

```html
<div class="setting-hint">
    <strong>💡 分析模式说明：</strong>
    <div><strong>LLM 模式</strong>：深度语义分析，适合复杂问题诊断（响应较慢，5-30 秒/1000 条）</div>
    <div><strong>规则模式</strong>：基于预定义规则快速分析，零成本（响应极快，<1 秒/1000 条）</div>
</div>
```

### 5.3 使用流程

1. 上传日志文件
2. 选择分析模式（LLM 模式 / 规则模式）
3. 点击"开始分析"按钮
4. 等待分析完成（规则模式通常 <1 秒）
5. 查看或下载报告

---

## 6. 技术架构

### 6.1 核心组件

```
┌─────────────────────────────────────────────────────┐
│                   规则分析器                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │  日志解析器  │ → │  规则匹配器  │ → │  报告生成器│ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
│         ↓                ↓                ↓        │
│  ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │  错误分类库  │   │  根因识别库  │   │  建议模板库│ │
│  └─────────────┘   └─────────────┘   └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### 6.2 数据流程

1. **日志解析**：将原始日志转换为结构化数据
2. **规则匹配**：根据预定义规则进行错误分类
3. **根因识别**：识别错误的根本原因
4. **建议生成**：根据错误类型生成整改建议
5. **报告输出**：生成格式化报告

### 6.3 扩展开发

#### 自定义错误分类

```python
from log_analyzer.report.rule_based_analyzer import RuleBasedAnalyzer

# 添加自定义错误分类
analyzer = RuleBasedAnalyzer()
analyzer.add_error_pattern(
    name="custom_error",
    pattern=r"CustomException: (.+)",
    severity="High",
    category="application"
)
```

#### 自定义根本原因

```python
analyzer.add_root_cause(
    name="custom_root_cause",
    keywords=["custom_error", "special_condition"],
    description="自定义错误场景",
    suggestion="检查相关配置"
)
```

---

## 7. 适用场景

### ✅ 推荐使用规则模式

- 批量日志快速扫描
- 日常监控告警
- CI/CD 流水线集成
- 成本敏感环境
- 离线分析场景

### ❌ 不适合使用规则模式

- 需要深度语义分析
- 复杂跨系统问题诊断
- 需要自然语言总结
- 未知错误模式识别

---

## 8. 常见问题

### Q: 如何判断应该使用哪种模式？

**规则模式**适合：快速扫描、批量处理、成本敏感场景
**LLM 模式**适合：复杂问题诊断、深度分析、需要自然语言总结

### Q: 规则模式的结果和 LLM 模式的结果一样吗？

不完全一样。LLM 模式提供更深度的语义分析和自然语言总结，规则模式提供结构化的错误分类和快速响应。

### Q: 如何切换回 LLM 模式？

在 API 调用时设置 `use_llm: true`，或在 Web 界面勾选"使用 LLM 分析"复选框。

### Q: 规则模式支持哪些日志格式？

支持常见日志格式：
- Apache/Nginx 访问日志
- Java 应用日志
- Python 日志
- 自定义格式（需配置解析规则）

---

## 性能对比

| 指标 | LLM 模式 | 规则模式 |
|------|----------|----------|
| 响应时间 | 5-30 秒/1000 条 | <1 秒/1000 条 |
| API 成本 | 有 | 无 |
| 网络依赖 | 需要 | 不需要 |
| 分析深度 | 高 | 中等 |
| 结果可读性 | 自然语言 | 结构化 |