"""
规则模式日志分析测试用例
测试不依赖LLM的规则处理模式功能
"""

import unittest
import os
import sys
from datetime import datetime
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from log_analyzer.parser.log_parser import LogParser, LogLevel, ParsedLogEntry
from log_analyzer.report.rule_based_analyzer import (
    RuleBasedAnalyzer,
    ErrorClassifier,
    RuleBasedAnalysisResult,
    create_rule_based_result
)
from log_analyzer.llm.client import AnalysisResult


class TestErrorClassifier(unittest.TestCase):
    """测试错误分类器"""
    
    def test_classify_null_pointer_severity(self):
        """测试空指针异常分类为严重"""
        severity = ErrorClassifier.classify_severity(
            "NullPointerException",
            "Cannot invoke method on null object"
        )
        self.assertEqual(severity, "critical")
    
    def test_classify_timeout_severity(self):
        """测试超时错误分类"""
        severity = ErrorClassifier.classify_severity(
            "TimeoutException",
            "Connection timeout after 30000ms"
        )
        self.assertEqual(severity, "high")
    
    def test_classify_sql_exception_severity(self):
        """测试SQL异常分类"""
        severity = ErrorClassifier.classify_severity(
            "SQLException",
            "Database connection failed"
        )
        self.assertEqual(severity, "high")
    
    def test_identify_null_reference_root_cause(self):
        """测试识别空引用根本原因"""
        causes = ErrorClassifier.identify_root_causes(
            "NullPointerException",
            "Cannot invoke toString() on null object",
            None
        )
        self.assertIn("null_reference", causes)
    
    def test_identify_timeout_root_cause(self):
        """测试识别超时根本原因"""
        causes = ErrorClassifier.identify_root_causes(
            "TimeoutException",
            "Request timeout after 5000ms",
            None
        )
        self.assertIn("timeout", causes)
    
    def test_suggest_recommendations_for_null(self):
        """测试空指针错误的建议"""
        recommendations = ErrorClassifier.suggest_recommendations(
            "NullPointerException",
            ["null_reference"]
        )
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(any("null" in r.lower() for r in recommendations))


class TestRuleBasedAnalyzer(unittest.TestCase):
    """测试规则分析器"""
    
    def setUp(self):
        """设置测试环境"""
        self.analyzer = RuleBasedAnalyzer()
        self.parser = LogParser()
    
    def _create_mock_entry(
        self,
        level: LogLevel = LogLevel.ERROR,
        error_type: str = None,
        message: str = "Test error message",
        class_name: str = "TestClass"
    ) -> ParsedLogEntry:
        """创建模拟日志条目"""
        return ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="main",
            level=level,
            trace_id="test-trace-id",
            class_name=class_name,
            message=message,
            raw_line=f"2024-01-01 10:00:00.000 [main] ERROR test - {message}",
            line_number=1,
            error_type=error_type,
            error_message=message if error_type else None
        )
    
    def test_analyze_empty_entries(self):
        """测试空条目分析"""
        result = self.analyzer.analyze_entries([], chunk_id=0)
        
        self.assertEqual(result.chunk_id, 0)
        self.assertEqual(len(result.key_errors), 0)
        self.assertIn("未发现错误", result.summary)
    
    def test_analyze_no_error_entries(self):
        """测试无错误条目分析"""
        entries = [
            self._create_mock_entry(level=LogLevel.INFO, message="Info message"),
            self._create_mock_entry(level=LogLevel.DEBUG, message="Debug message")
        ]
        
        result = self.analyzer.analyze_entries(entries, chunk_id=0)
        
        self.assertEqual(len(result.key_errors), 0)
        self.assertIn("未发现错误", result.summary)
    
    def test_analyze_single_error(self):
        """测试单个错误分析"""
        entries = [
            self._create_mock_entry(
                level=LogLevel.ERROR,
                error_type="NullPointerException",
                message="Cannot invoke method on null object"
            )
        ]
        
        result = self.analyzer.analyze_entries(entries, chunk_id=1)
        
        self.assertEqual(result.chunk_id, 1)
        self.assertEqual(len(result.key_errors), 1)
        self.assertEqual(result.key_errors[0]['error_type'], "NullPointerException")
        self.assertEqual(result.key_errors[0]['count'], 1)
        self.assertEqual(result.key_errors[0]['severity'], "critical")
    
    def test_analyze_multiple_errors(self):
        """测试多个错误分析"""
        entries = [
            self._create_mock_entry(
                level=LogLevel.ERROR,
                error_type="NullPointerException",
                message="Cannot invoke method on null object"
            ),
            self._create_mock_entry(
                level=LogLevel.ERROR,
                error_type="NullPointerException",
                message="Cannot invoke toString() because obj is null"
            ),
            self._create_mock_entry(
                level=LogLevel.ERROR,
                error_type="TimeoutException",
                message="Connection timeout"
            )
        ]
        
        result = self.analyzer.analyze_entries(entries, chunk_id=2)
        
        # 应该识别出2种错误类型
        self.assertEqual(len(result.key_errors), 2)
        
        # NullPointerException 应该排在最前面（严重程度高）
        self.assertEqual(result.key_errors[0]['error_type'], "NullPointerException")
        self.assertEqual(result.key_errors[0]['count'], 2)
        
        # TimeoutException 排在后面
        self.assertEqual(result.key_errors[1]['error_type'], "TimeoutException")
        self.assertEqual(result.key_errors[1]['count'], 1)
    
    def test_analyze_fatal_errors(self):
        """测试致命错误分析"""
        entries = [
            self._create_mock_entry(
                level=LogLevel.FATAL,
                error_type="OutOfMemoryError",
                message="Java heap space out of memory"
            )
        ]
        
        result = self.analyzer.analyze_entries(entries, chunk_id=3)
        
        self.assertEqual(len(result.key_errors), 1)
        self.assertEqual(result.key_errors[0]['severity'], "critical")
    
    def test_extract_error_type(self):
        """测试错误类型提取"""
        error_type = self.analyzer._extract_error_type(
            "java.lang.NullPointerException: Cannot invoke method"
        )
        self.assertEqual(error_type, "java.lang.NullPointerException")
    
    def test_generate_description(self):
        """测试描述生成"""
        messages = [
            "Error message 1",
            "Error message 1",
            "Error message 2"
        ]
        
        description = self.analyzer._generate_description("TestError", messages)
        self.assertEqual(description, "Error message 1")  # 最常见的消息
    
    def test_severity_distribution(self):
        """测试严重程度分布"""
        entries = [
            self._create_mock_entry(level=LogLevel.ERROR),
            self._create_mock_entry(level=LogLevel.ERROR),
            self._create_mock_entry(level=LogLevel.FATAL)
        ]
        
        result = self.analyzer.analyze_entries(entries, chunk_id=4)
        
        self.assertEqual(result.severity_distribution['error'], 2)
        self.assertEqual(result.severity_distribution['fatal'], 1)


class TestRuleBasedAnalysisResult(unittest.TestCase):
    """测试规则分析结果"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = RuleBasedAnalysisResult(
            chunk_id=0,
            summary="Test summary",
            key_errors=[],
            frequency_stats={},
            affected_classes=[],
            recommendations=[],
            root_causes=[],
            severity_distribution={}
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['chunk_id'], 0)
        self.assertEqual(result_dict['summary'], "Test summary")
    
    def test_to_analysis_result(self):
        """测试转换为 AnalysisResult"""
        result = RuleBasedAnalysisResult(
            chunk_id=1,
            summary="Test summary",
            key_errors=[
                {
                    'error_type': 'NullPointerException',
                    'description': 'Test error',
                    'count': 5,
                    'severity': 'critical'
                }
            ],
            frequency_stats={'total': 5},
            affected_classes=['TestClass'],
            recommendations=['Fix the null check'],
            root_causes=['null_reference'],
            severity_distribution={'critical': 5}
        )
        
        analysis_result = result.to_analysis_result()
        
        self.assertIsInstance(analysis_result, AnalysisResult)
        self.assertEqual(analysis_result.chunk_id, 1)
        self.assertEqual(analysis_result.summary, "Test summary")
        self.assertEqual(len(analysis_result.key_errors), 1)


class TestCreateRuleBasedResult(unittest.TestCase):
    """测试便捷函数"""
    
    def setUp(self):
        """设置测试环境"""
        self.parser = LogParser()
    
    def _create_mock_entry(
        self,
        level: LogLevel = LogLevel.ERROR,
        error_type: str = "TestException",
        message: str = "Test error"
    ) -> ParsedLogEntry:
        """创建模拟日志条目"""
        return ParsedLogEntry(
            timestamp=datetime.now(),
            thread_name="main",
            level=level,
            trace_id="test-trace-id",
            class_name="TestClass",
            message=message,
            raw_line=f"2024-01-01 10:00:00.000 [main] ERROR test - {message}",
            line_number=1,
            error_type=error_type,
            error_message=message
        )
    
    def test_create_rule_based_result(self):
        """测试创建规则基础结果"""
        entries = [
            self._create_mock_entry(
                error_type="NullPointerException",
                message="Null object error"
            )
        ]
        
        result = create_rule_based_result(entries, chunk_id=0)
        
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.chunk_id, 0)
        self.assertTrue(len(result.summary) > 0)


class TestRuleBasedAnalyzerIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_analyze_with_real_parser(self):
        """测试与分析器集成"""
        parser = LogParser()
        analyzer = RuleBasedAnalyzer(parser)
        
        # 创建一些测试条目
        entries = [
            ParsedLogEntry(
                timestamp=datetime.now(),
                thread_name="main",
                level=LogLevel.ERROR,
                trace_id="trace-1",
                class_name="UserService",
                message="NullPointerException: Cannot invoke toString() on null",
                raw_line="2024-01-01 10:00:00.000 [main] ERROR trace-1 UserService - NullPointerException",
                line_number=1,
                error_type="NullPointerException",
                error_message="Cannot invoke toString() on null"
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
            )
        ]
        
        result = analyzer.analyze_entries(entries, chunk_id=0)
        
        # 验证结果
        self.assertEqual(result.chunk_id, 0)
        self.assertEqual(len(result.key_errors), 2)
        
        # 验证严重错误排在前面
        self.assertEqual(result.key_errors[0]['severity'], 'critical')
        
        # 验证统计数据
        self.assertTrue(len(result.affected_classes) > 0)
        self.assertTrue(len(result.recommendations) > 0)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_analyze_large_number_of_errors(self):
        """测试大量错误的处理性能"""
        analyzer = RuleBasedAnalyzer()
        
        # 创建1000个错误条目
        entries = []
        for i in range(1000):
            error_type = f"ErrorType{i % 10}"  # 10种不同的错误类型
            entries.append(ParsedLogEntry(
                timestamp=datetime.now(),
                thread_name=f"thread-{i % 10}",
                level=LogLevel.ERROR,
                trace_id=f"trace-{i}",
                class_name=f"Class{i % 50}",
                message=f"Error message {i}",
                raw_line=f"2024-01-01 10:00:{i % 60:02d} [thread-{i % 10}] ERROR trace-{i} Class{i % 50} - Error message {i}",
                line_number=i,
                error_type=error_type,
                error_message=f"Error message {i}"
            ))
        
        import time
        start_time = time.time()
        result = analyzer.analyze_entries(entries, chunk_id=0)
        elapsed_time = time.time() - start_time
        
        # 验证性能：1000个错误应该在1秒内处理完成
        self.assertLess(elapsed_time, 1.0, f"处理时间过长: {elapsed_time:.2f}秒")
        
        # 验证结果
        self.assertEqual(len(result.key_errors), 10)  # 应该识别出10种错误类型
        self.assertTrue(result.summary)


if __name__ == '__main__':
    unittest.main()
