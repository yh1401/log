"""Unit tests for intelligent error merging functionality."""

import os
import sys
import time
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from log_analyzer.report.error_merger import ErrorMerger, MergeConfig, MergedErrorGroup


class TestErrorMerger(unittest.TestCase):
    """测试智能错误合并器"""
    
    def setUp(self):
        """设置测试环境"""
        self.default_merger = ErrorMerger()
        self.strict_merger = ErrorMerger(MergeConfig(
            semantic_similarity_threshold=0.95,
            enable_semantic_merging=False
        ))
        self.lenient_merger = ErrorMerger(MergeConfig(
            semantic_similarity_threshold=0.6,
            max_groups=50
        ))
    
    def test_exact_duplicate_removal(self):
        """测试完全相同错误的去重功能"""
        errors = [
            {'error_type': 'NullPointerException', 'description': 'Object is null', 'count': 10, 'severity': 'critical'},
            {'error_type': 'NullPointerException', 'description': 'Object is null', 'count': 10, 'severity': 'critical'},
            {'error_type': 'NullPointerException', 'description': 'Object is null', 'count': 10, 'severity': 'critical'},
            {'error_type': 'IOException', 'description': 'File not found', 'count': 5, 'severity': 'high'},
            {'error_type': 'IOException', 'description': 'File not found', 'count': 5, 'severity': 'high'},
        ]
        
        merged = self.default_merger.merge_errors(errors)
        
        self.assertEqual(len(merged), 2, "应该合并为2个错误组")
        self.assertEqual(merged[0].count, 30, "NullPointerException计数应该合并为30")
        self.assertEqual(merged[1].count, 10, "IOException计数应该合并为10")
    
    def test_semantic_similarity_merging(self):
        """测试语义相似错误的合并功能"""
        errors = [
            # 这些是非常相似的错误消息，应该合并
            {'error_type': 'NullPointerException', 'description': 'Cannot invoke "Object.toString()" because "obj" is null', 'count': 5, 'severity': 'critical'},
            {'error_type': 'NullPointerException', 'description': 'Cannot invoke "Object.hashCode()" because "obj" is null', 'count': 3, 'severity': 'critical'},
            {'error_type': 'NullPointerException', 'description': 'Cannot invoke "Object.equals()" because "obj" is null', 'count': 2, 'severity': 'high'},
            # 这些是相似的越界错误，应该合并
            {'error_type': 'IndexOutOfBoundsException', 'description': 'Index 10 out of bounds for length 5', 'count': 4, 'severity': 'high'},
            {'error_type': 'IndexOutOfBoundsException', 'description': 'Index 20 out of bounds for length 15', 'count': 2, 'severity': 'high'},
            {'error_type': 'IndexOutOfBoundsException', 'description': 'Index 5 out of bounds for length 3', 'count': 1, 'severity': 'medium'},
        ]
        
        merged = self.default_merger.merge_errors(errors)
        
        # 语义相似的NullPointerException应该合并，IndexOutOfBoundsException也应该合并
        self.assertLessEqual(len(merged), 2, "相似错误应该合并")
    
    def test_pattern_based_merging(self):
        """测试基于模式的错误合并"""
        errors = [
            {'error_type': 'TimeoutException', 'description': 'Connection timeout after 30000ms', 'count': 10},
            {'error_type': 'TimeoutException', 'description': 'Connection timeout after 20000ms', 'count': 8},
            {'error_type': 'TimeoutException', 'description': 'Connection timeout after 10000ms', 'count': 5},
            {'error_type': 'TimeoutException', 'description': 'Read timeout after 30000ms', 'count': 3},
        ]
        
        merged = self.default_merger.merge_errors(errors)
        
        # 前3个应该合并（模式相同），最后一个应该单独成组
        self.assertLessEqual(len(merged), 2, "相同模式的错误应该合并")
    
    def test_configurable_threshold(self):
        """测试可配置的合并阈值"""
        errors = [
            {'error_type': 'Exception', 'description': 'Error connecting to database', 'count': 5},
            {'error_type': 'Exception', 'description': 'Error connecting to DB', 'count': 3},
        ]
        
        # 使用严格配置（不合并）
        strict_merged = self.strict_merger.merge_errors(errors)
        self.assertEqual(len(strict_merged), 2, "严格模式下不应该合并")
        
        # 使用宽松配置（合并）
        lenient_merged = self.lenient_merger.merge_errors(errors)
        self.assertEqual(len(lenient_merged), 1, "宽松模式下应该合并")
    
    def test_severity_preservation(self):
        """测试严重程度的保留（取最严重的）"""
        errors = [
            {'error_type': 'Error', 'description': 'Test error', 'count': 5, 'severity': 'low'},
            {'error_type': 'Error', 'description': 'Test error', 'count': 3, 'severity': 'critical'},
            {'error_type': 'Error', 'description': 'Test error', 'count': 2, 'severity': 'medium'},
        ]
        
        merged = self.default_merger.merge_errors(errors)
        
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].severity, 'critical', "应该保留最严重的级别")
    
    def test_context_preservation(self):
        """测试上下文信息的保留"""
        errors = [
            {'error_type': 'Error', 'description': 'Test', 'count': 1, 'class_name': 'com.example.ClassA', 'timestamp': '2026-01-01 10:00:00'},
            {'error_type': 'Error', 'description': 'Test', 'count': 1, 'class_name': 'com.example.ClassB', 'timestamp': '2026-01-01 11:00:00'},
            {'error_type': 'Error', 'description': 'Test', 'count': 1, 'class_name': 'com.example.ClassA', 'timestamp': '2026-01-01 12:00:00'},
        ]
        
        merged = self.default_merger.merge_errors(errors)
        
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0].affected_classes), 2, "应该保留所有影响的类")
        self.assertIn('com.example.ClassA', merged[0].affected_classes)
        self.assertIn('com.example.ClassB', merged[0].affected_classes)
        self.assertEqual(len(merged[0].examples), 3, "应该保留示例")
    
    def test_large_dataset_performance(self):
        """测试大规模数据的处理性能（1000+错误）"""
        errors = []
        error_types = ['NullPointerException', 'IOException', 'TimeoutException', 'IndexOutOfBoundsException', 
                       'IllegalArgumentException', 'ConnectionRefusedException', 'UnknownHostException', 'SocketTimeoutException']
        
        for i in range(1000):
            errors.append({
                'error_type': error_types[i % len(error_types)],
                'description': f"Error message {i % 10}",
                'count': 1,
                'severity': 'high' if i % 3 == 0 else 'medium',
                'class_name': f'com.example.Class{i % 5}',
                'timestamp': f'2026-01-01 10:{i // 60}:{i % 60}'
            })
        
        start_time = time.time()
        merged = self.default_merger.merge_errors(errors)
        elapsed_time = time.time() - start_time
        
        self.assertLess(elapsed_time, 10, "处理1000条错误应该在10秒内完成")
        self.assertLessEqual(len(merged), 20, "合并后组数应该不超过配置的最大值")
        
        # 验证合并效果
        total_original = sum(e['count'] for e in errors)
        total_merged = sum(g.count for g in merged)
        self.assertEqual(total_original, total_merged, "总计数应该保持不变")
    
    def test_empty_input(self):
        """测试空输入"""
        merged = self.default_merger.merge_errors([])
        self.assertEqual(merged, [], "空输入应该返回空列表")
    
    def test_single_error(self):
        """测试单个错误"""
        errors = [{'error_type': 'TestError', 'description': 'Test', 'count': 1}]
        merged = self.default_merger.merge_errors(errors)
        
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].error_type, 'TestError')
        self.assertEqual(merged[0].count, 1)


class TestMergeConfig(unittest.TestCase):
    """测试合并配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MergeConfig()
        self.assertEqual(config.exact_match_threshold, 1.0)
        self.assertEqual(config.semantic_similarity_threshold, 0.8)
        self.assertEqual(config.max_examples_per_group, 5)
        self.assertEqual(config.max_groups, 20)
        self.assertTrue(config.enable_semantic_merging)
        self.assertTrue(config.merge_by_error_type)
        self.assertTrue(config.merge_by_message_pattern)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MergeConfig(
            exact_match_threshold=0.9,
            semantic_similarity_threshold=0.7,
            max_examples_per_group=10,
            max_groups=50,
            enable_semantic_merging=False
        )
        
        self.assertEqual(config.exact_match_threshold, 0.9)
        self.assertEqual(config.semantic_similarity_threshold, 0.7)
        self.assertEqual(config.max_examples_per_group, 10)
        self.assertEqual(config.max_groups, 50)
        self.assertFalse(config.enable_semantic_merging)


class TestPatternExtraction(unittest.TestCase):
    """测试模式提取功能"""
    
    def setUp(self):
        self.merger = ErrorMerger()
    
    def test_extract_pattern_with_numbers(self):
        """测试移除数字"""
        message = "Connection timeout after 30000ms"
        pattern = self.merger.extract_pattern(message)
        self.assertEqual(pattern, "Connection timeout after [NUM]ms")
    
    def test_extract_pattern_with_uuid(self):
        """测试移除UUID"""
        message = "Request ID: 550e8400-e29b-41d4-a716-446655440000 failed"
        pattern = self.merger.extract_pattern(message)
        self.assertEqual(pattern, "Request ID: [UUID] failed")
    
    def test_extract_pattern_with_ip(self):
        """测试移除IP地址"""
        message = "Cannot connect to 192.168.1.100:8080"
        pattern = self.merger.extract_pattern(message)
        self.assertEqual(pattern, "Cannot connect to [IP]:[NUM]")
    
    def test_extract_pattern_with_path(self):
        """测试移除文件路径"""
        message = "File not found: /var/log/app.log"
        pattern = self.merger.extract_pattern(message)
        self.assertEqual(pattern, "File not found: [PATH]")
    
    def test_extract_pattern_with_strings(self):
        """测试移除引号内容"""
        message = 'Error: "user_id" cannot be null'
        pattern = self.merger.extract_pattern(message)
        self.assertEqual(pattern, 'Error: [STR] cannot be null')


if __name__ == '__main__':
    unittest.main(verbosity=2)
