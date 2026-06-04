"""基于规则的日志分析器 - 不依赖LLM的日志分析功能"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from datetime import datetime

# 延迟导入以避免循环依赖
_log_parser = None
_analysis_result = None

def _get_parser():
    global _log_parser
    if _log_parser is None:
        # 尝试多种导入方式
        try:
            from parser.log_parser import LogParser, ParsedLogEntry, LogLevel, ErrorPattern
        except ImportError:
            from ..parser.log_parser import LogParser, ParsedLogEntry, LogLevel, ErrorPattern
        _log_parser = (LogParser, ParsedLogEntry, LogLevel, ErrorPattern)
    return _log_parser

def _get_analysis_result():
    global _analysis_result
    if _analysis_result is None:
        # 尝试多种导入方式
        try:
            from llm.client import AnalysisResult
        except ImportError:
            from ..llm.client import AnalysisResult
        _analysis_result = AnalysisResult
    return _analysis_result


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class RuleBasedAnalysisResult:
    """规则分析结果"""
    chunk_id: int
    summary: str
    key_errors: List[Dict[str, Any]]
    frequency_stats: Dict[str, Any] = field(default_factory=dict)
    affected_classes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'summary': self.summary,
            'key_errors': self.key_errors,
            'frequency_stats': self.frequency_stats,
            'affected_classes': self.affected_classes,
            'recommendations': self.recommendations,
            'root_causes': self.root_causes,
            'severity_distribution': self.severity_distribution
        }
    
    def to_analysis_result(self):
        """转换为与LLM AnalysisResult兼容的格式"""
        AnalysisResult = _get_analysis_result()
        
        # 将 key_errors 转换为 LLM 格式
        key_errors = []
        for err in self.key_errors:
            key_errors.append({
                'error_type': err.get('error_type', ''),
                'description': err.get('description', ''),
                'severity': err.get('severity', 'medium'),
                'count': err.get('count', 1),
                'affected_classes': err.get('affected_classes', []),
                'examples': err.get('examples', [])
            })
        
        # 将 recommendations 转换为 suggestions
        suggestions = self.recommendations if self.recommendations else []
        
        # 将 root_causes 转换为 root_cause 格式
        root_cause = {
            'root_causes': self.root_causes if self.root_causes else [],
            'confidence': 'high' if self.root_causes else 'low'
        }
        
        return AnalysisResult(
            chunk_id=self.chunk_id,
            summary=self.summary,
            key_errors=key_errors,
            frequency_stats=self.frequency_stats,
            trends=[],
            suggestions=suggestions,
            ops_suggestions=suggestions,
            dev_suggestions=suggestions,
            timeline={},
            root_cause=root_cause,
            causal_chain={},
            remediation={},
            response_actions={},
            evidence_chain={}
        )


class ErrorClassifier:
    """错误分类器 - 基于规则对错误进行分类"""
    
    # 严重程度映射
    SEVERITY_LEVELS = {
        'critical': ['NullPointerException', 'OutOfMemoryError', 'StackOverflowError',
                    'NoClassDefFoundError', 'UnsatisfiedLinkError'],
        'high': ['SQLException', 'IOException', 'ConnectionException', 
                'AuthenticationException', 'AuthorizationException',
                'TimeoutException', 'ServiceException'],
        'medium': ['IllegalArgumentException', 'IllegalStateException', 
                  'ValidationException', 'ParseException'],
        'low': ['Warning', 'Deprecation', 'ConfigurationError']
    }
    
    # 根因关键词映射
    ROOT_CAUSE_KEYWORDS = {
        'null_reference': ['null', 'NullPointer', 'NPE', 'cannot invoke'],
        'resource_leak': ['leak', 'resource', 'connection', 'stream not closed'],
        'timeout': ['timeout', '超时', 'timed out', 'TTL'],
        'authentication': ['auth', 'token', 'credential', 'login', 'permission', '权限'],
        'database': ['sql', 'database', 'JDBC', 'transaction', 'deadlock'],
        'network': ['network', 'connection', 'socket', 'connect', 'refused'],
        'configuration': ['config', 'property', 'yml', 'xml', 'properties'],
        'memory': ['memory', 'heap', 'OutOfMemory', 'GC', '溢出']
    }
    
    @classmethod
    def classify_severity(cls, error_type: str, message: str) -> str:
        """根据错误类型和消息分类严重程度"""
        text = f"{error_type} {message}".lower()
        
        for severity, patterns in cls.SEVERITY_LEVELS.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    return severity
        return 'medium'
    
    @classmethod
    def identify_root_causes(cls, error_type: str, message: str, 
                            stack_trace: Optional[List[str]] = None) -> List[str]:
        """识别可能的根本原因"""
        causes = []
        text = f"{error_type} {message}".lower()
        
        if stack_trace:
            text += ' ' + ' '.join(stack_trace).lower()
        
        for cause, keywords in cls.ROOT_CAUSE_KEYWORDS.items():
            if any(keyword.lower() in text for keyword in keywords):
                causes.append(cause)
        
        return causes if causes else ['unknown']
    
    @classmethod
    def suggest_recommendations(cls, error_type: str, root_causes: List[str]) -> List[str]:
        """根据错误类型和根本原因生成建议"""
        recommendations = []
        error_lower = error_type.lower()
        
        # 基于错误类型的建议
        if 'null' in error_lower or 'npe' in error_lower:
            recommendations.append("检查对象是否为null再进行操作")
            recommendations.append("使用Optional处理可能为空的值")
        
        if 'timeout' in error_lower:
            recommendations.append("检查网络连接和超时配置")
            recommendations.append("考虑增加超时时间或实现重试机制")
        
        if 'sql' in error_lower or 'database' in error_lower:
            recommendations.append("检查SQL语句和数据库连接")
            recommendations.append("确保事务正确提交或回滚")
        
        if 'auth' in error_lower or 'permission' in error_lower:
            recommendations.append("检查用户权限配置")
            recommendations.append("验证token或凭证的有效性")
        
        if 'outofmemory' in error_lower:
            recommendations.append("增加JVM堆内存配置")
            recommendations.append("检查内存泄漏问题")
        
        if 'io' in error_lower or 'file' in error_lower:
            recommendations.append("检查文件路径和权限")
            recommendations.append("确保资源正确关闭")
        
        # 基于根本原因的建议
        if 'null_reference' in root_causes:
            recommendations.append("添加null检查逻辑")
            recommendations.append("使用防御性编程")
        
        if 'timeout' in root_causes:
            recommendations.append("优化网络调用或增加超时时间")
            recommendations.append("实现熔断和降级机制")
        
        if 'memory' in root_causes:
            recommendations.append("分析内存使用情况")
            recommendations.append("优化对象生命周期管理")
        
        # 如果没有特定建议，返回通用建议
        if not recommendations:
            recommendations.append("查看完整堆栈跟踪定位问题")
            recommendations.append("检查相关日志上下文")
        
        return recommendations[:3]  # 最多返回3条建议


class RuleBasedAnalyzer:
    """基于规则的日志分析器"""
    
    def __init__(self, parser=None):
        LogParser, ParsedLogEntry, LogLevel, ErrorPattern = _get_parser()
        self.parser = parser or LogParser()
        self.classifier = ErrorClassifier()
        
        logger.info("[RuleBasedAnalyzer] 初始化完成")
    
    def analyze_entries(self, entries, chunk_id: int = 0) -> RuleBasedAnalysisResult:
        """
        分析日志条目并生成分析结果
        
        Args:
            entries: 解析后的日志条目列表
            chunk_id: 分块ID
            
        Returns:
            RuleBasedAnalysisResult: 规则分析结果
        """
        logger.info(f"[RuleBasedAnalyzer] 开始分析 Chunk #{chunk_id}, 条目数: {len(entries)}")
        
        # 获取 LogLevel 枚举
        LogParser, ParsedLogEntry, LogLevel, ErrorPattern = _get_parser()
        
        # 筛选错误和致命日志
        error_entries = []
        for e in entries:
            # 支持字典和对象两种格式
            if isinstance(e, dict):
                level_str = e.get('level', '')
                # 只保留 ERROR 和 FATAL 级别
                if level_str not in ['ERROR', 'FATAL', 'error', 'fatal']:
                    continue
                # 将字典转换为简单的错误信息对象
                error_entry = type('ErrorEntry', (), {
                    'level': level_str.upper() if isinstance(level_str, str) else 'ERROR',
                    'error_type': e.get('error_type', 'UnknownError'),
                    'message': e.get('message', ''),
                    'class_name': e.get('class_name', 'UnknownClass'),
                    'timestamp': e.get('timestamp', datetime.now()),
                    'stack_trace': e.get('stack_trace', None)
                })()
                error_entries.append(error_entry)
            else:
                level_str = e.level.value if hasattr(e.level, 'value') else str(e.level)
                # 只保留 ERROR 和 FATAL 级别
                if level_str not in ['ERROR', 'FATAL']:
                    continue
                error_entries.append(e)
        
        logger.info(f"[RuleBasedAnalyzer] 错误条目数: {len(error_entries)}")
        
        if not error_entries:
            return RuleBasedAnalysisResult(
                chunk_id=chunk_id,
                summary="未发现错误日志",
                key_errors=[],
                frequency_stats={},
                affected_classes=[],
                recommendations=["继续监控日志"],
                root_causes=[],
                severity_distribution={'error': 0, 'fatal': 0}
            )
        
        # 统计信息（仅当所有条目都是 ParsedLogEntry 对象时才调用）
        try:
            # 检查第一个条目是否是字典
            if entries and isinstance(entries[0], dict):
                # 如果是字典，生成简单的统计信息
                statistics = {
                    'total_entries': len(entries),
                    'error_count': len(error_entries),
                    'fatal_count': sum(1 for e in error_entries if e.level == 'FATAL'),
                    'error_level_count': sum(1 for e in error_entries if e.level == 'ERROR')
                }
            else:
                statistics = self.parser.get_error_statistics(entries)
        except Exception:
            # 如果出错，使用默认统计
            statistics = {
                'total_entries': len(entries),
                'error_count': len(error_entries)
            }
        
        # 错误分析
        error_analysis = self._analyze_errors(error_entries)
        
        # 根本原因分析
        root_causes = self._identify_root_causes(error_entries)
        
        # 生成建议
        recommendations = self._generate_recommendations(error_analysis, root_causes)
        
        # 生成摘要
        summary = self._generate_summary(error_analysis, len(entries))
        
        # 严重程度分布
        severity_dist = self._calculate_severity_distribution(error_entries)
        
        logger.info(f"[RuleBasedAnalyzer] 分析完成, 识别出 {len(error_analysis)} 种错误类型")
        
        return RuleBasedAnalysisResult(
            chunk_id=chunk_id,
            summary=summary,
            key_errors=error_analysis,
            frequency_stats=statistics,
            affected_classes=list(set([e.class_name for e in error_entries])),
            recommendations=recommendations,
            root_causes=root_causes,
            severity_distribution=severity_dist
        )
    
    def _analyze_errors(self, error_entries: List[ParsedLogEntry]) -> List[Dict[str, Any]]:
        """分析错误条目并分类"""
        # 按错误类型分组
        error_groups = {}
        
        for entry in error_entries:
            error_type = entry.error_type or self._extract_error_type(entry.message)
            severity = self.classifier.classify_severity(error_type, entry.message)
            
            key = (error_type, severity)
            if key not in error_groups:
                error_groups[key] = {
                    'error_type': error_type,
                    'severity': severity,
                    'count': 0,
                    'messages': [],
                    'classes': set(),
                    'first_occurrence': entry.timestamp,
                    'last_occurrence': entry.timestamp
                }
            
            group = error_groups[key]
            group['count'] += 1
            group['messages'].append(entry.message)
            group['classes'].add(entry.class_name)
            
            if entry.timestamp < group['first_occurrence']:
                group['first_occurrence'] = entry.timestamp
            if entry.timestamp > group['last_occurrence']:
                group['last_occurrence'] = entry.timestamp
        
        # 转换为列表格式
        result = []
        for (error_type, severity), group in error_groups.items():
            # 统计最常见的消息
            message_counter = Counter(group['messages'])
            top_messages = message_counter.most_common(3)
            examples = [
                {'message': msg, 'count': count}
                for msg, count in top_messages
            ]
            
            result.append({
                'error_type': error_type,
                'description': self._generate_description(error_type, group['messages']),
                'count': group['count'],
                'severity': severity,
                'affected_classes': list(group['classes']),
                'examples': examples,
                'first_occurrence': group['first_occurrence'].isoformat() if group['first_occurrence'] else None,
                'last_occurrence': group['last_occurrence'].isoformat() if group['last_occurrence'] else None
            })
        
        # 按严重程度和出现次数排序
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        result.sort(key=lambda x: (severity_order.get(x['severity'], 4), -x['count']))
        
        return result[:10]  # 最多返回10种错误类型
    
    def _extract_error_type(self, message: str) -> str:
        """从消息中提取错误类型"""
        match = re.search(r'([\w\.]+(?:Exception|Error))', message)
        if match:
            return match.group(1)
        return "UnknownError"
    
    def _generate_description(self, error_type: str, messages: List[str]) -> str:
        """生成错误描述"""
        # 使用最常见的消息作为描述
        counter = Counter(messages)
        most_common_msg = counter.most_common(1)[0][0]
        
        # 截断过长描述
        if len(most_common_msg) > 100:
            return f"{most_common_msg[:100]}..."
        return most_common_msg
    
    def _identify_root_causes(self, error_entries: List[ParsedLogEntry]) -> List[str]:
        """识别主要根本原因"""
        all_causes = []
        
        for entry in error_entries:
            causes = self.classifier.identify_root_causes(
                entry.error_type or "",
                entry.message,
                entry.stack_trace
            )
            all_causes.extend(causes)
        
        # 统计根本原因频率
        cause_counter = Counter(all_causes)
        
        # 返回最常见的根本原因
        top_causes = cause_counter.most_common(3)
        return [cause for cause, count in top_causes]
    
    def _generate_recommendations(self, error_analysis: List[Dict[str, Any]],
                                  root_causes: List[str]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于最严重的错误生成建议
        if error_analysis:
            top_error = error_analysis[0]
            error_recommendations = self.classifier.suggest_recommendations(
                top_error['error_type'],
                root_causes
            )
            recommendations.extend(error_recommendations)
        
        # 添加通用建议
        if len(error_analysis) > 3:
            recommendations.append("系统存在多种错误类型，建议进行系统性排查")
        
        if any(e['severity'] == 'critical' for e in error_analysis):
            recommendations.append("发现严重错误，建议立即处理")
        
        return list(set(recommendations))[:5]  # 去重，最多5条
    
    def _generate_summary(self, error_analysis: List[Dict[str, Any]], 
                         total_entries: int) -> str:
        """生成摘要"""
        if not error_analysis:
            return "日志中未发现错误。"
        
        total_errors = sum(e['count'] for e in error_analysis)
        unique_types = len(error_analysis)
        
        # 统计严重程度
        severity_counts = {}
        for e in error_analysis:
            severity = e['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + e['count']
        
        summary_parts = []
        
        summary_parts.append(f"共发现 {total_errors} 条错误记录，涉及 {unique_types} 种错误类型。")
        
        if 'critical' in severity_counts:
            summary_parts.append(f"其中包含 {severity_counts['critical']} 条严重错误。")
        
        if 'high' in severity_counts:
            summary_parts.append(f"高严重程度错误 {severity_counts['high']} 条。")
        
        # 添加最常见错误的信息
        if error_analysis:
            top_error = error_analysis[0]
            summary_parts.append(
                f"最频繁的错误是 {top_error['error_type']}，出现 {top_error['count']} 次。"
            )
        
        return " ".join(summary_parts)
    
    def _calculate_severity_distribution(self, 
                                       error_entries: List[ParsedLogEntry]) -> Dict[str, int]:
        """计算严重程度分布"""
        # 获取 LogLevel 枚举
        LogParser, ParsedLogEntry, LogLevel, ErrorPattern = _get_parser()
        
        distribution = {
            'error': 0,
            'fatal': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for entry in error_entries:
            level = entry.level
            # 支持字符串和枚举两种格式
            if isinstance(level, str):
                if level.upper() == 'FATAL':
                    distribution['fatal'] += 1
                elif level.upper() == 'ERROR':
                    distribution['error'] += 1
            else:
                if level == LogLevel.FATAL:
                    distribution['fatal'] += 1
                elif level == LogLevel.ERROR:
                    distribution['error'] += 1
            
            # 根据错误类型分类
            severity = self.classifier.classify_severity(
                entry.error_type or "",
                entry.message
            )
            distribution[severity] = distribution.get(severity, 0) + 1
        
        return distribution


def create_rule_based_result(entries: List[ParsedLogEntry], 
                             chunk_id: int = 0) -> AnalysisResult:
    """
    便捷函数：创建基于规则的分析结果
    
    Args:
        entries: 解析后的日志条目列表
        chunk_id: 分块ID
        
    Returns:
        AnalysisResult: 与LLM兼容的分析结果
    """
    analyzer = RuleBasedAnalyzer()
    rule_result = analyzer.analyze_entries(entries, chunk_id)
    return rule_result.to_analysis_result()
