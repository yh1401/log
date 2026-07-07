# Log Analyzer Skill - 日志分析组件

一个功能强大的智能日志分析组件，支持LLM和规则双模式分析。

## 概述

此组件提供以下功能：
- 日志文件上传与处理
- 错误检测与根因分析
- 网络抓包（PCAP）分析
- 多格式报告生成（PDF、Word、Markdown、HTML）
- 服务器路径访问与分析
- 任务管理与监控

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 主要组件定义，包含API参考和使用指南 |
| `CONFIG.md` | 详细的配置参数说明文档 |
| `test_log_analyzer.py` | 全面的单元测试套件 |
| `examples.py` | 实用的代码示例集合 |
| `README.md` | 本文件 - 快速入门指南 |

## 快速开始

### 1. 前置条件

- Log Analyzer服务器运行在 `http://localhost:8000`
- Python 3.10+ 并安装 `requests` 库

### 2. 基本用法

```python
import requests

# 上传日志文件
with open('error.log', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f},
        headers={'X-User-Id': 'my_user'}
    )

file_path = response.json()['data']['file_path']

# 开始分析
response = requests.post(
    'http://localhost:8000/api/process',
    json={
        'file_path': file_path,
        'use_llm': True
    },
    headers={'X-User-Id': 'my_user'}
)

task_id = response.json()['data']['task_id']
print(f"任务已启动: {task_id}")
```

### 3. 运行测试

```bash
# 运行所有测试
pytest test_log_analyzer.py -v

# 运行特定测试类
pytest test_log_analyzer.py -v -k "TestFileUpload"

# 运行测试并生成覆盖率报告
pytest test_log_analyzer.py -v --cov=log_analyzer
```

### 4. 运行示例

```bash
# 运行示例脚本
python examples.py
```

## 文档说明

- **API参考**：查看 `SKILL.md` 获取完整的API文档
- **配置说明**：查看 `CONFIG.md` 了解配置选项
- **使用示例**：查看 `examples.py` 获取实用代码示例
- **测试用例**：查看 `test_log_analyzer.py` 了解测试案例

## 分析模式

### LLM模式
- 深度语义分析
- 每千行5-30秒
- 需要API密钥
- 适合复杂问题诊断

### 规则模式
- 快速模式匹配
- 每千行小于1秒
- 无需API调用
- 适合批量扫描和监控

## 常见使用场景

1. **错误检测**：识别和分类应用日志中的错误
2. **根因分析**：确定故障的根本原因
3. **网络分析**：解析和分析PCAP文件
4. **报告生成**：创建格式化的分析报告
5. **CI/CD集成**：在流水线中自动分析日志
6. **监控集成**：在告警时触发分析

## 支持与反馈

如有问题和建议：
1. 查看 `SKILL.md` 了解API详情
2. 查看 `CONFIG.md` 了解配置选项
3. 查看 `examples.py` 了解使用模式
4. 运行 `test_log_analyzer.py` 中的测试验证功能

## 版本信息

- Skill版本：1.0.0
- 兼容Log Analyzer v2.6.0+
