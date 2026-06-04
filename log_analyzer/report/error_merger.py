"""Intelligent error merging and deduplication utilities."""

import re
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class MergeConfig:
    """
    合并规则配置类
    
    Attributes:
        exact_match_threshold: 完全匹配阈值（0-1），1表示完全相同
        semantic_similarity_threshold: 语义相似度阈值（0-1）
        max_examples_per_group: 每个错误组保留的最大示例数
        max_groups: 最大错误组数
        enable_semantic_merging: 是否启用语义合并
        merge_by_error_type: 是否按错误类型分组
        merge_by_message_pattern: 是否按消息模式分组
    """
    exact_match_threshold: float = 1.0
    semantic_similarity_threshold: float = 0.8
    max_examples_per_group: int = 5
    max_groups: int = 20
    enable_semantic_merging: bool = True
    merge_by_error_type: bool = True
    merge_by_message_pattern: bool = True


@dataclass
class MergedErrorGroup:
    """
    合并后的错误组
    
    Attributes:
        error_type: 错误类型
        description: 统一描述
        count: 总出现次数
        severity: 严重程度（取最严重的）
        examples: 示例列表
        affected_classes: 影响的类列表
        original_errors: 原始错误引用（用于保留上下文）
    """
    error_type: str
    description: str
    count: int = 0
    severity: str = "medium"
    examples: List[Dict[str, Any]] = field(default_factory=list)
    affected_classes: List[str] = field(default_factory=list)
    original_errors: List[Dict[str, Any]] = field(default_factory=list)


class ErrorMerger:
    """
    智能错误合并器
    
    功能：
    1. 完全相同错误去重
    2. 语义相似错误合并
    3. 可配置的合并策略
    4. 保留关键上下文信息
    """
    
    SEVERITY_ORDER = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
    
    def __init__(self, config: Optional[MergeConfig] = None):
        self.config = config or MergeConfig()
    
    def calculate_string_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度（使用简化的编辑距离算法）
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            
        Returns:
            相似度分数（0-1），1表示完全相同
        """
        if str1 == str2:
            return 1.0
        
        len1, len2 = len(str1), len(str2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # 创建距离矩阵
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1[i-1] == str2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # 删除
                    dp[i][j-1] + 1,      # 插入
                    dp[i-1][j-1] + cost  # 替换
                )
        
        max_len = max(len1, len2)
        return 1.0 - (dp[len1][len2] / max_len)
    
    def extract_pattern(self, message: str) -> str:
        """
        从错误消息中提取模式（去除动态内容）
        
        Args:
            message: 原始错误消息
            
        Returns:
            提取的模式字符串
        """
        if not message:
            return ""
        
        # 移除数字、ID、时间戳等动态内容
        pattern = message
        
        # 注意：替换顺序很重要，需要先替换复杂模式，再替换简单模式
        
        # 1. 移除UUID（必须在数字替换之前）
        pattern = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[UUID]', pattern, flags=re.IGNORECASE)
        
        # 2. 移除IP地址（必须在数字替换之前）
        pattern = re.sub(r'\b(\d{1,3}\.){3}\d{1,3}\b', '[IP]', pattern)
        
        # 3. 移除文件路径
        pattern = re.sub(r'(/[\w.-]+)+', '[PATH]', pattern)
        
        # 4. 移除引号内的内容
        pattern = re.sub(r'"[^"]*"', '[STR]', pattern)
        pattern = re.sub(r"'[^']*'", '[STR]', pattern)
        
        # 5. 移除尖括号内容
        pattern = re.sub(r'<[^>]*>', '[TAG]', pattern)
        
        # 6. 最后移除独立的数字序列（如ID、行号、时间等）
        # 匹配数字后面跟着非数字字符或字符串结尾的情况
        pattern = re.sub(r'\d+(?=\D|$)', '[NUM]', pattern)
        
        return pattern.strip()
    
    def is_similar_error(self, error1: Dict[str, Any], error2: Dict[str, Any]) -> bool:
        """
        判断两个错误是否相似
        
        Args:
            error1: 第一个错误
            error2: 第二个错误
            
        Returns:
            是否相似
        """
        # 首先检查错误类型
        if self.config.merge_by_error_type:
            type1 = error1.get('error_type', '')
            type2 = error2.get('error_type', '')
            if type1 != type2:
                return False
        
        # 检查消息相似度
        msg1 = error1.get('description', '') or error1.get('message', '')
        msg2 = error2.get('description', '') or error2.get('message', '')
        
        if self.config.merge_by_message_pattern:
            # 使用模式匹配
            pattern1 = self.extract_pattern(msg1)
            pattern2 = self.extract_pattern(msg2)
            
            if pattern1 and pattern2 and pattern1 == pattern2:
                return True
        
        # 使用语义相似度
        if self.config.enable_semantic_merging:
            similarity = self.calculate_string_similarity(msg1, msg2)
            if similarity >= self.config.semantic_similarity_threshold:
                return True
        
        return False
    
    def merge_errors(self, errors: List[Dict[str, Any]]) -> List[MergedErrorGroup]:
        """
        合并错误列表
        
        Args:
            errors: 原始错误列表
            
        Returns:
            合并后的错误组列表
        """
        if not errors:
            return []
        
        groups: List[MergedErrorGroup] = []
        
        for error in errors:
            matched = False
            
            # 尝试找到相似的错误组
            for group in groups:
                if self.is_similar_error(error, {
                    'error_type': group.error_type,
                    'description': group.description
                }):
                    # 合并到现有组
                    group.count += error.get('count', 1)
                    group.original_errors.append(error)
                    
                    # 更新严重程度（取最严重的）
                    error_severity = error.get('severity', 'medium')
                    if self.SEVERITY_ORDER.get(error_severity, 0) > self.SEVERITY_ORDER.get(group.severity, 0):
                        group.severity = error_severity
                    
                    # 添加示例（限制数量）
                    if len(group.examples) < self.config.max_examples_per_group:
                        group.examples.append({
                            'message': error.get('description', '') or error.get('message', ''),
                            'timestamp': error.get('timestamp', ''),
                            'class_name': error.get('class_name', '')
                        })
                    
                    # 添加影响的类
                    class_name = error.get('class_name', '')
                    if class_name and class_name not in group.affected_classes:
                        group.affected_classes.append(class_name)
                    
                    matched = True
                    break
            
            if not matched:
                # 创建新组
                new_group = MergedErrorGroup(
                    error_type=error.get('error_type', 'Unknown'),
                    description=error.get('description', '') or error.get('message', 'No description'),
                    count=error.get('count', 1),
                    severity=error.get('severity', 'medium'),
                    examples=[{
                        'message': error.get('description', '') or error.get('message', ''),
                        'timestamp': error.get('timestamp', ''),
                        'class_name': error.get('class_name', '')
                    }],
                    affected_classes=[error.get('class_name', '')] if error.get('class_name') else [],
                    original_errors=[error]
                )
                groups.append(new_group)
        
        # 按出现次数排序
        groups.sort(key=lambda g: g.count, reverse=True)
        
        # 限制最大组数
        if self.config.max_groups > 0:
            groups = groups[:self.config.max_groups]
        
        return groups
    
    def merge_from_analysis_results(self, analysis_results: List[Any]) -> List[Dict[str, Any]]:
        """
        从多个分析结果中合并错误
        
        Args:
            analysis_results: 分析结果列表（包含key_errors字段）
            
        Returns:
            合并后的错误列表（转换为字典格式）
        """
        # 收集所有错误
        all_errors = []
        for analysis in analysis_results:
            if hasattr(analysis, 'key_errors'):
                for error in analysis.key_errors:
                    all_errors.append(error)
        
        # 合并错误
        merged_groups = self.merge_errors(all_errors)
        
        # 转换为字典格式
        result = []
        for group in merged_groups:
            result.append({
                'error_type': group.error_type,
                'description': group.description,
                'count': group.count,
                'severity': group.severity,
                'examples': group.examples,
                'affected_classes': group.affected_classes,
                'original_count': len(group.original_errors)
            })
        
        return result


# 预设配置
DEFAULT_CONFIG = MergeConfig()
STRICT_CONFIG = MergeConfig(
    semantic_similarity_threshold=0.95,
    enable_semantic_merging=False,
    max_examples_per_group=3
)
LENIENT_CONFIG = MergeConfig(
    semantic_similarity_threshold=0.6,
    max_examples_per_group=10,
    max_groups=30
)