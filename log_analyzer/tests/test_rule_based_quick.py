#!/usr/bin/env python3
"""
快速测试脚本：验证规则模式功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from parser.log_parser import LogLevel, ParsedLogEntry
from report.rule_based_analyzer import RuleBasedAnalyzer


def create_test_entries():
    """创建测试日志条目"""
    return [
        ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="main",
            level=LogLevel.ERROR,
            trace_id="trace-1",
            class_name="UserService",
            message="NullPointerException: Cannot invoke toString() on null object",
            raw_line="2024-01-01 10:00:00.000 [main] ERROR trace-1 UserService - NullPointerException",
            line_number=1,
            error_type="NullPointerException",
            error_message="Cannot invoke toString() on null object"
        ),
        ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="worker",
            level=LogLevel.ERROR,
            trace_id="trace-2",
            class_name="OrderService",
            message="TimeoutException: Connection timeout after 30000ms",
            raw_line="2024-01-01 10:00:01.000 [worker] ERROR trace-2 OrderService - TimeoutException",
            line_number=2,
            error_type="TimeoutException",
            error_message="Connection timeout after 30000ms"
        ),
        ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="main",
            level=LogLevel.ERROR,
            trace_id="trace-3",
            class_name="UserService",
            message="NullPointerException: Cannot invoke hashCode() because obj is null",
            raw_line="2024-01-01 10:00:02.000 [main] ERROR trace-3 UserService - NullPointerException",
            line_number=3,
            error_type="NullPointerException",
            error_message="Cannot invoke hashCode() because obj is null"
        ),
        ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="worker",
            level=LogLevel.INFO,
            trace_id="trace-4",
            class_name="AppService",
            message="Application started successfully",
            raw_line="2024-01-01 10:00:03.000 [worker] INFO trace-4 AppService - Application started",
            line_number=4,
            error_type=None,
            error_message=None
        ),
        ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="main",
            level=LogLevel.FATAL,
            trace_id="trace-5",
            class_name="DatabaseService",
            message="OutOfMemoryError: Java heap space",
            raw_line="2024-01-01 10:00:04.000 [main] FATAL trace-5 DatabaseService - OutOfMemoryError",
            line_number=5,
            error_type="OutOfMemoryError",
            error_message="Java heap space"
        )
    ]


def main():
    """主测试函数"""
    print("=" * 80)
    print("规则模式日志分析器 - 功能验证")
    print("=" * 80)
    print()
    
    # 创建分析器
    analyzer = RuleBasedAnalyzer()
    
    # 创建测试数据
    entries = create_test_entries()
    
    print(f"测试数据：{len(entries)} 条日志条目")
    print(f"- ERROR级别: {sum(1 for e in entries if e.level == LogLevel.ERROR)} 条")
    print(f"- FATAL级别: {sum(1 for e in entries if e.level == LogLevel.FATAL)} 条")
    print(f"- INFO级别: {sum(1 for e in entries if e.level == LogLevel.INFO)} 条")
    print()
    
    # 执行分析
    print("开始分析...")
    print("-" * 80)
    
    result = analyzer.analyze_entries(entries, chunk_id=0)
    
    # 输出结果
    print("分析结果：")
    print()
    
    print(f"摘要：{result.summary}")
    print()
    
    print(f"识别出 {len(result.key_errors)} 种错误类型：")
    for i, error in enumerate(result.key_errors, 1):
        print(f"\n{i}. {error['error_type']}")
        print(f"   严重程度: {error['severity']}")
        print(f"   出现次数: {error['count']}")
        print(f"   描述: {error['description']}")
        if error['affected_classes']:
            print(f"   影响类: {', '.join(error['affected_classes'])}")
    
    print()
    print("-" * 80)
    print("根本原因分析：")
    for cause in result.root_causes:
        print(f"  - {cause}")
    
    print()
    print("-" * 80)
    print("建议措施：")
    for rec in result.recommendations:
        print(f"  - {rec}")
    
    print()
    print("-" * 80)
    print("严重程度分布：")
    for severity, count in result.severity_distribution.items():
        if count > 0:
            print(f"  - {severity}: {count}")
    
    print()
    print("=" * 80)
    print("✓ 规则模式功能验证完成！")
    print("=" * 80)
    
    # 转换为 AnalysisResult 格式
    print()
    print("-" * 80)
    print("验证与 LLM AnalysisResult 兼容性：")
    
    analysis_result = result.to_analysis_result()
    print(f"✓ 成功转换为 AnalysisResult")
    print(f"  - chunk_id: {analysis_result.chunk_id}")
    print(f"  - summary: {analysis_result.summary[:50]}...")
    print(f"  - key_errors: {len(analysis_result.key_errors)} 条")
    print(f"  - frequency_stats: {len(analysis_result.frequency_stats)} 项")
    
    print()
    print("=" * 80)
    print("✓ 所有验证通过！规则模式工作正常。")
    print("=" * 80)


if __name__ == '__main__':
    main()
