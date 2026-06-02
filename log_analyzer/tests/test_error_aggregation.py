"""Test script for intelligent error aggregation optimization."""

import os
import sys
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SCRIPT_DIR)

from log_analyzer.llm.client import LLMClient


def generate_test_error_entries(count: int = 1000):
    """生成测试错误条目数据"""
    error_types = [
        'NullPointerException',
        'IndexOutOfBoundsException',
        'IOException',
        'TimeoutException',
        'ConnectionRefusedException',
        'UnknownHostException',
        'SocketTimeoutException',
        'IllegalArgumentException'
    ]
    
    classes = [
        'com.example.service.UserService',
        'com.example.repository.OrderRepository',
        'com.example.controller.ApiController',
        'com.example.util.DataProcessor',
        'com.example.config.AppConfig'
    ]
    
    messages = [
        'Cannot invoke \"Object.toString()\" because \"obj\" is null',
        'Index: 10, Size: 5',
        'Connection reset by peer',
        'Read timed out',
        'Connection refused',
        'Unknown host: example.com',
        'Socket timeout while connecting',
        'Invalid parameter value: null'
    ]
    
    entries = []
    for i in range(count):
        error_type = error_types[i % len(error_types)]
        class_name = classes[i % len(classes)]
        message = messages[i % len(messages)]
        
        entries.append({
            'timestamp': datetime(2026, 5, 26, 10 + i // 100, (i % 60)).strftime('%Y-%m-%d %H:%M:%S'),
            'error_type': error_type,
            'message': f"{message} - instance #{i}",
            'class_name': class_name,
            'level': 'ERROR',
            'line_number': 100 + i
        })
    
    return entries


def test_error_aggregation():
    """测试智能错误聚合功能"""
    print("=" * 80)
    print("         Testing Intelligent Error Aggregation")
    print("=" * 80)
    
    # 生成测试数据
    test_entries = generate_test_error_entries(500)
    print(f"\n📊 测试数据生成完成")
    print(f"   总错误条目数: {len(test_entries)}")
    
    # 创建LLMClient实例（不需要实际配置，只测试聚合功能）
    client = LLMClient.__new__(LLMClient)
    
    # 测试聚合功能
    print("\n🔄 执行智能错误聚合...")
    error_summary, original_chars, compressed_chars, compression_ratio = client._aggregate_errors(test_entries)
    
    # 输出结果对比
    print("\n" + "=" * 80)
    print("📈 优化效果对比")
    print("=" * 80)
    
    print(f"\n┌─────────────────────────────────────────────┐")
    print(f"│ 指标                │ 优化前              │ 优化后              │")
    print(f"├─────────────────────┼─────────────────────┼─────────────────────┤")
    print(f"│ 错误条目数          │ {len(test_entries):>13,}           │ {len(error_summary['aggregated_errors']):>13,}           │")
    print(f"│ 字符数              │ {original_chars:>13,}           │ {compressed_chars:>13,}           │")
    print(f"└─────────────────────┴─────────────────────┴─────────────────────┘")
    print(f"\n🎯 压缩率: {compression_ratio:.1f}%")
    
    # 输出聚合后的错误类型统计
    print("\n" + "=" * 80)
    print("📋 聚合后的错误类型统计")
    print("=" * 80)
    
    print(f"\n总错误数: {error_summary['total_errors']:,}")
    print(f"唯一错误类型数: {error_summary['unique_error_types']}")
    print(f"时间范围: {error_summary['time_range']['start']} ~ {error_summary['time_range']['end']}")
    print(f"\n错误类型分布:")
    
    for error in error_summary['aggregated_errors']:
        print(f"\n┌─ {error['error_type']}")
        print(f"│  出现次数: {error['count']:,}")
        print(f"│  时间范围: {error['time_range']['start']} ~ {error['time_range']['end']}")
        print(f"│  影响类: {', '.join(error['affected_classes'])}")
        print(f"│  示例消息 ({len(error['examples'])}条):")
        for idx, example in enumerate(error['examples'], 1):
            msg = example['message'][:60] + "..." if len(example['message']) > 60 else example['message']
            print(f"│    {idx}. {msg}")
    
    # 验证关键信息完整性
    print("\n" + "=" * 80)
    print("✅ 关键信息验证")
    print("=" * 80)
    
    # 检查时间戳是否保留
    has_time_range = error_summary.get('time_range') is not None
    print(f"✓ 时间范围保留: {'是' if has_time_range else '否'}")
    
    # 检查错误类型是否完整
    all_types = set(e['error_type'] for e in test_entries)
    aggregated_types = set(e['error_type'] for e in error_summary['aggregated_errors'])
    type_coverage = len(aggregated_types & all_types) / len(all_types) * 100
    print(f"✓ 错误类型覆盖率: {type_coverage:.1f}%")
    
    # 检查示例消息是否保留
    has_examples = any(len(e['examples']) > 0 for e in error_summary['aggregated_errors'])
    print(f"✓ 示例消息保留: {'是' if has_examples else '否'}")
    
    print("\n🎉 智能错误聚合测试完成！")


if __name__ == '__main__':
    test_error_aggregation()