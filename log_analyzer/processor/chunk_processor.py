"""Chunk processor for handling large log files - Optimized Version."""

import os
import time
import gc
import logging
import asyncio
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Tuple

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from ..parser.log_parser import LogParser, ParsedLogEntry, LogLevel
from ..checkpoint.manager import CheckpointManager, Checkpoint
from ..llm.client import LLMClient, AnalysisResult
from ..utils.helpers import ProgressTracker, calculate_file_hash


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


MEMORY_THRESHOLD_HIGH = 0.6  # 高水位：60%
MEMORY_THRESHOLD_CRITICAL = 0.1  # 临界水位：10%（降低阈值，避免频繁GC）
MEMORY_THRESHOLD_LOW = 0.5  # 低水位：50%

# GC冷却时间（秒），避免短时间内多次GC
_GC_COOLDOWN = 5.0
_last_gc_time = 0.0


def log_memory_usage(label: str):
    """记录当前内存使用情况"""
    if not HAS_PSUTIL:
        return
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()
        mem = psutil.virtual_memory()
        available_ratio = mem.available / mem.total
        logger.info(f"[Memory] {label} - RSS: {mem_info.rss / 1024 / 1024:.2f} MB, "
                    f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB, "
                    f"Percent: {mem_percent:.1f}%, "
                    f"Available: {available_ratio*100:.1f}%")
    except Exception as e:
        logger.warning(f"[Memory] Failed to log memory usage: {e}")


def get_memory_status() -> Dict[str, float]:
    """获取当前内存状态"""
    if not HAS_PSUTIL:
        return {'available_ratio': 0.15, 'used_percent': 85.0, 'available_mb': 256.0, 'total_mb': 2048.0}
    try:
        mem = psutil.virtual_memory()
        return {
            'available_ratio': mem.available / mem.total,
            'used_percent': mem.percent,
            'available_mb': mem.available / 1024 / 1024,
            'total_mb': mem.total / 1024 / 1024
        }
    except Exception as e:
        logger.warning(f"[Memory] Failed to get memory status: {e}")
        return {'available_ratio': 0.15, 'used_percent': 85.0, 'available_mb': 256.0, 'total_mb': 2048.0}


def calculate_optimal_chunk_size(total_lines: int, file_size_mb: float, current_chunk_size: int = 500000) -> int:
    """根据内存量计算最优的chunk_size
    
    策略：
    1. 获取可用内存
    2. 根据文件大小和可用内存比例计算合适的chunk_size
    3. 确保每个chunk占用的内存不超过可用内存的20%
    """
    status = get_memory_status()
    available_mb = status.get('available_mb', 2048.0)
    
    # 估算每条日志条目占用的内存（保守估计）
    # 一条典型的日志条目大约占用 500-1000 bytes
    ESTIMATED_BYTES_PER_ENTRY = 800
    
    # 计算当前chunk_size对应的内存占用（MB）
    current_chunk_memory_mb = (current_chunk_size * ESTIMATED_BYTES_PER_ENTRY) / (1024 * 1024)
    
    # 目标：每个chunk最多占用可用内存的20%
    max_chunk_memory_mb = available_mb * 0.2
    
    logger.info(f"[Memory] 可用内存: {available_mb:.1f} MB")
    logger.info(f"[Memory] 当前chunk_size: {current_chunk_size:,}，预计内存: {current_chunk_memory_mb:.1f} MB")
    logger.info(f"[Memory] 最大允许chunk内存: {max_chunk_memory_mb:.1f} MB")
    
    if current_chunk_memory_mb <= max_chunk_memory_mb:
        logger.info(f"[Memory] 当前chunk_size合适，无需调整")
        return current_chunk_size
    
    # 需要减小chunk_size
    new_chunk_size = int(max_chunk_memory_mb * (1024 * 1024) / ESTIMATED_BYTES_PER_ENTRY)
    
    # 确保最小chunk_size不小于10000
    new_chunk_size = max(new_chunk_size, 10000)
    
    # 确保至少分成2个chunk（如果文件足够大）
    if total_lines > new_chunk_size * 2:
        max_possible_chunks = (total_lines + new_chunk_size - 1) // new_chunk_size
        logger.info(f"[Memory] 需要调整chunk_size: {current_chunk_size:,} -> {new_chunk_size:,}")
        logger.info(f"[Memory] 预计分块数: {max_possible_chunks}")
        return new_chunk_size
    
    logger.info(f"[Memory] 文件较小，保持chunk_size: {current_chunk_size:,}")
    return current_chunk_size


def ensure_memory_safety() -> bool:
    """确保内存安全，必要时强制GC（带冷却时间限制）"""
    global _last_gc_time
    
    status = get_memory_status()
    
    # 检查是否需要GC（仅在低于临界值且冷却时间已过）
    if status['available_ratio'] < MEMORY_THRESHOLD_CRITICAL:
        current_time = time.time()
        
        # 如果距离上次GC时间太短，跳过此次检查
        if current_time - _last_gc_time < _GC_COOLDOWN:
            return True
        
        logger.warning(f"[Memory] 内存临界! 可用 {status['available_ratio']*100:.1f}%，强制GC...")
        gc.collect()
        _last_gc_time = time.time()
        
        status = get_memory_status()
        if status['available_ratio'] < MEMORY_THRESHOLD_CRITICAL:
            logger.error(f"[Memory] GC后内存仍不足: {status['available_ratio']*100:.1f}%")
            return False
        logger.info(f"[Memory] GC完成，可用 {status['available_ratio']*100:.1f}%")
    return True


class StreamingStatsAggregator:
    """流式统计聚合器：边解析边聚合，不保留原始条目"""
    
    def __init__(
        self,
        max_error_samples: int = 500,
        max_warn_samples: int = 1000,
        max_info_samples: int = 200,
        top_classes_limit: int = 20,
        top_error_types_limit: int = 20
    ):
        self.stats = {
            'by_level': {},
            'error_types': {},
            'patterns': {},
            'top_classes': {}
        }
        self.error_samples = []
        self.warn_samples = []
        self.info_samples = []
        self.max_error_samples = max_error_samples
        self.max_warn_samples = max_warn_samples
        self.max_info_samples = max_info_samples
        self.top_classes_limit = top_classes_limit
        self.top_error_types_limit = top_error_types_limit
        
        self._error_classes_seen = set()
        self._warn_classes_seen = set()
        self._info_classes_seen = set()
        
        self._chunk_statistics = []
        self._chunks_info = []
        
        self._total_entries = 0
        self._chunk_count = 0
    
    def ingest_chunk(self, entries: List[ParsedLogEntry], chunk_id: int, end_line: int):
        """摄入一个chunk的数据，即时聚合"""
        self._chunk_count += 1
        chunk_error_count = 0
        chunk_warn_count = 0
        chunk_info_count = 0
        
        for entry in entries:
            self._total_entries += 1
            
            level = entry.level.value if isinstance(entry.level, LogLevel) else str(entry.level)
            
            self.stats['by_level'][level] = self.stats['by_level'].get(level, 0) + 1
            
            if entry.class_name:
                self.stats['top_classes'][entry.class_name] = \
                    self.stats['top_classes'].get(entry.class_name, 0) + 1
            
            if entry.error_type:
                self.stats['error_types'][entry.error_type] = \
                    self.stats['error_types'].get(entry.error_type, 0) + 1
            
            if level in ('ERROR', 'FATAL'):
                chunk_error_count += 1
                self._smart_sample(entry, self.error_samples, self.max_error_samples, 
                                  self._error_classes_seen)
            elif level == 'WARN':
                chunk_warn_count += 1
                self._smart_sample(entry, self.warn_samples, self.max_warn_samples,
                                  self._warn_classes_seen)
            elif level == 'INFO':
                chunk_info_count += 1
                if len(self.info_samples) < self.max_info_samples:
                    self._smart_sample(entry, self.info_samples, self.max_info_samples,
                                      self._info_classes_seen)
        
        chunk_statistics = {
            'chunk_id': chunk_id,
            'total_entries': len(entries),
            'error_count': chunk_error_count,
            'warn_count': chunk_warn_count,
            'info_count': chunk_info_count
        }
        self._chunk_statistics.append(chunk_statistics)
        self._chunks_info.append((chunk_id, end_line, len(entries)))
    
    def _smart_sample(self, entry: ParsedLogEntry, samples_list: list, max_samples: int, 
                      classes_seen: set):
        """智能采样：确保每个类都有代表性样本"""
        if len(samples_list) >= max_samples:
            return
        
        class_name = entry.class_name or 'UNKNOWN'
        
        if class_name not in classes_seen:
            samples_list.append(entry.to_dict())
            classes_seen.add(class_name)
        elif len(samples_list) < max_samples // 2:
            samples_list.append(entry.to_dict())
    
    def get_final_stats(self):
        """获取最终聚合结果，截断到限制数量"""
        self.stats['top_classes'] = dict(sorted(
            self.stats['top_classes'].items(),
            key=lambda x: x[1], reverse=True
        )[:self.top_classes_limit])
        
        self.stats['error_types'] = dict(sorted(
            self.stats['error_types'].items(),
            key=lambda x: x[1], reverse=True
        )[:self.top_error_types_limit])
        
        return self.stats
    
    def get_chunk_statistics(self):
        """获取所有chunk的统计信息"""
        return self._chunk_statistics
    
    def get_chunks_info(self):
        """获取所有chunk的基本信息"""
        return self._chunks_info
    
    def get_sample_data(self):
        """获取采样数据"""
        return {
            'error_entries': self.error_samples,
            'warn_entries': self.warn_samples,
            'info_entries': self.info_samples
        }
    
    def get_summary(self):
        """获取聚合器摘要信息"""
        return {
            'total_entries': self._total_entries,
            'chunk_count': self._chunk_count,
            'error_samples_count': len(self.error_samples),
            'warn_samples_count': len(self.warn_samples),
            'info_samples_count': len(self.info_samples),
            'memory_estimate_mb': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self):
        """估算当前聚合器占用的内存（MB），考虑 Python 对象开销"""
        # Python 对象通常有约 50-100 字节的额外开销
        OBJECT_OVERHEAD = 56  # 每个 dict 对象的基础开销
        
        total_bytes = 0
        
        # 计算样本内存
        for sample in self.error_samples + self.warn_samples + self.info_samples:
            # 字符串内容
            for key, value in sample.items():
                if isinstance(value, str):
                    total_bytes += len(value.encode('utf-8'))
                else:
                    total_bytes += len(str(value))
            # dict 对象开销
            total_bytes += OBJECT_OVERHEAD
        
        # 计算统计对象内存
        for stat in self._chunk_statistics:
            total_bytes += len(str(stat).encode('utf-8')) + OBJECT_OVERHEAD
        
        # 计算内部数据结构内存
        total_bytes += len(self._error_classes_seen) * 50  # set 中每个元素约 50 字节
        total_bytes += len(self._warn_classes_seen) * 50
        total_bytes += len(self._info_classes_seen) * 50
        
        return total_bytes / 1024 / 1024


@dataclass
class ProcessingResult:
    file_path: str
    total_lines: int
    processed_lines: int
    total_chunks: int
    completed_chunks: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    checkpoint: Optional[Checkpoint] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'total_lines': self.total_lines,
            'processed_lines': self.processed_lines,
            'total_chunks': self.total_chunks,
            'completed_chunks': self.completed_chunks,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'analysis_results': [r.to_dict() for r in self.analysis_results],
            'statistics': self.statistics,
            'performance_metrics': self.performance_metrics
        }

    def get_progress_percentage(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return (self.processed_lines / self.total_lines) * 100


class ChunkProcessor:
    def __init__(
        self,
        parser: LogParser,
        llm_client: Optional[LLMClient],
        checkpoint_manager: CheckpointManager,
        chunk_size: int = 5000000,
        enable_checkpoint: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        parallel_workers: int = 4,
        enable_parallel_processing: bool = True,
        merge_threshold: int = 5,
        use_llm: bool = True
    ):
        self.parser = parser
        self.llm_client = llm_client
        self.checkpoint_manager = checkpoint_manager
        self.chunk_size = chunk_size
        self.enable_checkpoint = enable_checkpoint
        self.progress_callback = progress_callback
        self.parallel_workers = parallel_workers
        self.enable_parallel_processing = enable_parallel_processing
        self.merge_threshold = max(1, int(round(merge_threshold)))
        self.use_llm = use_llm
        
        self._checkpoint_batch = []
        self._checkpoint_batch_size = 5
        
        # 初始化规则分析器（当 use_llm=False 时使用）
        self._rule_based_analyzer = None
        
        # 自适应内存控制
        self._adapt_chunk_size_based_on_memory()
        
        # 记录初始内存状态
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            logger.info(f"[Memory] 系统可用内存: {mem.available / 1024 / 1024:.0f} MB ({(mem.available/mem.total)*100:.1f}%)")

        logger.info("=" * 80)
        logger.info("[ChunkProcessor] 初始化完成")
        logger.info(f"  Chunk Size: {chunk_size:,}")
        logger.info(f"  Checkpoint Enabled: {enable_checkpoint}")
        logger.info(f"  Parallel Workers: {parallel_workers}")
        logger.info(f"  Parallel Processing: {enable_parallel_processing}")
        logger.info(f"  Merge Threshold: {merge_threshold}")
        logger.info(f"  Use LLM: {use_llm}")
        if not use_llm:
            logger.info("  ⚠️  警告: 使用规则模式，不调用LLM")
        logger.info("=" * 80)
    
    def _adapt_chunk_size_based_on_memory(self):
        """根据系统可用内存自适应调整分块大小"""
        if not HAS_PSUTIL:
            logger.info("[Memory] 未检测到 psutil，使用默认分块大小")
            return

        mem = psutil.virtual_memory()
        available_ratio = mem.available / mem.total
        original_size = self.chunk_size

        # 注意：内存紧张时应当减小 chunk_size（缩小每个chunk的条目数）
        if available_ratio < 0.2:
            self.chunk_size = max(10000, self.chunk_size // 4)
            logger.warning(f"[Memory] 内存严重不足 ({available_ratio*100:.1f}%)，大幅减小分块: {original_size:,} -> {self.chunk_size:,}")
        elif available_ratio < 0.3:
            self.chunk_size = max(20000, self.chunk_size // 2)
            logger.warning(f"[Memory] 内存紧张 ({available_ratio*100:.1f}%)，减小分块: {original_size:,} -> {self.chunk_size:,}")
        elif available_ratio < 0.5:
            self.chunk_size = int(self.chunk_size * 0.8)
            logger.info(f"[Memory] 内存偏低 ({available_ratio*100:.1f}%)，适当减小分块: {original_size:,} -> {self.chunk_size:,}")
        else:
            logger.info(f"[Memory] 内存充足 ({available_ratio*100:.1f}%)，使用默认分块大小 {self.chunk_size:,}")
    
    def _should_use_sequential_mode(self, total_chunks: int) -> bool:
        """判断是否应降级为顺序处理模式"""
        if not HAS_PSUTIL:
            return total_chunks > 3
        
        mem_status = get_memory_status()
        available_ratio = mem_status['available_ratio']
        
        if available_ratio < MEMORY_THRESHOLD_CRITICAL:
            logger.error(f"[Memory] 内存严重不足 ({available_ratio*100:.1f}%)，强制降级为顺序模式")
            return True
        
        if available_ratio < MEMORY_THRESHOLD_LOW or total_chunks > 3:
            logger.info(f"[Memory] 内存 {available_ratio*100:.1f}% / 分块数 {total_chunks}，使用顺序模式")
            return True
        
        return False

    def count_lines(self, file_path: str) -> int:
        start_time = time.time()
        logger.info(f"[File Stats] 开始统计文件行数: {file_path}")
        count = self.parser.count_lines_mmap(file_path)
        elapsed = time.time() - start_time
        logger.info(f"[File Stats] 文件行数统计完成: {count:,} 行 (耗时: {elapsed:.2f}s)")
        return count

    async def process_chunk_async(
        self,
        entries: List[ParsedLogEntry],
        chunk_id: int
    ) -> AnalysisResult:
        logger.info(f"[Processor] 开始处理 Chunk #{chunk_id}")
        logger.info(f"  Total Entries: {len(entries)}")
        
        # 根据配置选择使用 LLM 或规则分析
        if self.use_llm and self.llm_client:
            return await self._process_chunk_with_llm(entries, chunk_id)
        else:
            return await self._process_chunk_with_rules(entries, chunk_id)
    
    async def _process_chunk_with_llm(
        self,
        entries: List[ParsedLogEntry],
        chunk_id: int
    ) -> AnalysisResult:
        """使用 LLM 进行日志分析"""
        logger.info(f"[Processor] 使用 LLM 模式处理 Chunk #{chunk_id}")

        error_entries = [
            e.to_dict() for e in entries
            if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL
        ]

        warn_entries = [
            e.to_dict() for e in entries
            if e.level == LogLevel.WARN
        ]

        info_entries = [
            e.to_dict() for e in entries
            if e.level == LogLevel.INFO
        ][:50]

        logger.info(f"  Error Entries: {len(error_entries)}")
        logger.info(f"  Warn Entries: {len(warn_entries)}")
        logger.info(f"  Info Entries: {len(info_entries)}")

        statistics = self.parser.get_error_statistics(entries)
        logger.info(f"[Processor] 错误统计信息: {statistics}")

        logger.info(f"[Processor] 准备调用 LLM 进行 Chunk #{chunk_id} 分析...")

        result = await self.llm_client.analyze_log_chunk(
            error_entries=error_entries,
            statistics=statistics,
            chunk_id=chunk_id,
            warn_entries=warn_entries,
            info_entries=info_entries
        )

        logger.info(f"[Processor] Chunk #{chunk_id} 处理完成")
        logger.info(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")

        return result
    
    async def _process_chunk_with_rules(
        self,
        entries: List[ParsedLogEntry],
        chunk_id: int
    ) -> AnalysisResult:
        """使用规则引擎进行日志分析（不依赖 LLM）"""
        logger.info(f"[Processor] 使用规则模式处理 Chunk #{chunk_id}")

        # 初始化规则分析器（延迟初始化）
        if self._rule_based_analyzer is None:
            from ..report.rule_based_analyzer import RuleBasedAnalyzer
            self._rule_based_analyzer = RuleBasedAnalyzer(self.parser)
            logger.info("[Processor] 规则分析器初始化完成")

        error_entries = [
            e for e in entries
            if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL
        ]

        logger.info(f"  Error Entries: {len(error_entries)}")

        # 使用规则分析器处理日志条目
        rule_result = self._rule_based_analyzer.analyze_entries(entries, chunk_id)
        
        # 转换为 AnalysisResult 格式
        result = rule_result.to_analysis_result()

        logger.info(f"[Processor] Chunk #{chunk_id} 规则分析完成")
        logger.info(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")

        return result

    def process_chunk_sync_wrapper(self, args: Tuple[List[ParsedLogEntry], int, LogParser, Dict, bool]) -> AnalysisResult:
        """同步包装器，支持可选 LLM 模式"""
        entries, chunk_id, parser, llm_config, use_llm = args
        
        if use_llm and llm_config:
            return self._process_chunk_sync_with_llm(entries, chunk_id, parser, llm_config)
        else:
            return self._process_chunk_sync_with_rules(entries, chunk_id, parser)
    
    def _process_chunk_sync_with_llm(
        self, 
        entries: List[ParsedLogEntry], 
        chunk_id: int, 
        parser: LogParser,
        llm_config: Dict
    ) -> AnalysisResult:
        """使用 LLM 进行同步日志分析"""
        error_entries = [
            e.to_dict() for e in entries
            if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL
        ]

        statistics = parser.get_error_statistics(entries)

        try:
            from ..llm.client import LLMClient
            llm_client = LLMClient(llm_config)
            result = asyncio.run(llm_client.analyze_log_chunk(
                error_entries=error_entries,
                statistics=statistics,
                chunk_id=chunk_id
            ))
            return result
        except Exception as e:
            logger.error(f"[Processor] Chunk #{chunk_id} 处理失败: {e}")
            return AnalysisResult(chunk_id=chunk_id, summary="", key_errors=[])
    
    def _process_chunk_sync_with_rules(
        self, 
        entries: List[ParsedLogEntry], 
        chunk_id: int, 
        parser: LogParser
    ) -> AnalysisResult:
        """使用规则引擎进行同步日志分析（不依赖 LLM）"""
        try:
            from ..report.rule_based_analyzer import RuleBasedAnalyzer
            analyzer = RuleBasedAnalyzer(parser)
            rule_result = analyzer.analyze_entries(entries, chunk_id)
            return rule_result.to_analysis_result()
        except Exception as e:
            logger.error(f"[Processor] Chunk #{chunk_id} 规则分析失败: {e}")
            return AnalysisResult(chunk_id=chunk_id, summary="", key_errors=[])

    async def process_file_async(
        self,
        file_path: str,
        resume: bool = True,
        force_restart: bool = False,
        progress_callback: callable = None,
        content_callback: Optional[Callable[[str], None]] = None
    ) -> ProcessingResult:
        start_total = time.time()
        logger.info("=" * 80)
        logger.info(f"[Process File] 开始处理文件")
        logger.info(f"  File Path: {file_path}")
        logger.info(f"  Resume: {resume}, Force Restart: {force_restart}")
        logger.info("=" * 80)

        if not os.path.exists(file_path):
            logger.error(f"[Process File] 文件不存在: {file_path}")
            return ProcessingResult(
                file_path=file_path,
                total_lines=0,
                processed_lines=0,
                total_chunks=0,
                completed_chunks=0,
                status="failed",
                started_at=datetime.now(),
                error_message=f"File not found: {file_path}"
            )

        file_hash = calculate_file_hash(file_path)
        logger.info(f"[Process File] File Hash: {file_hash}")

        parse_start = time.time()
        total_lines = self.count_lines(file_path)
        
        # 根据内存自动调整chunk_size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        optimal_chunk_size = calculate_optimal_chunk_size(total_lines, file_size_mb, self.chunk_size)
        
        if optimal_chunk_size != self.chunk_size:
            logger.info(f"[Process File] 自动调整chunk_size: {self.chunk_size:,} -> {optimal_chunk_size:,}")
            # 创建临时parser使用新的chunk_size
            temp_parser = LogParser(chunk_size=optimal_chunk_size)
            self.parser = temp_parser
            self.chunk_size = optimal_chunk_size
        
        total_chunks = (total_lines + self.chunk_size - 1) // self.chunk_size
        parse_time = time.time() - parse_start

        logger.info(f"[Process File] 文件统计:")
        logger.info(f"  - Total Lines: {total_lines:,}")
        logger.info(f"  - Chunk Size: {self.chunk_size:,}")
        logger.info(f"  - Total Chunks: {total_chunks}")

        started_at = datetime.now()
        result = ProcessingResult(
            file_path=file_path,
            total_lines=total_lines,
            processed_lines=0,
            total_chunks=total_chunks,
            completed_chunks=0,
            status="in_progress",
            started_at=started_at
        )

        checkpoint = None
        if resume and not force_restart and self.enable_checkpoint:
            logger.info("[Process File] 检查是否存在有效检查点...")
            checkpoint = self.checkpoint_manager.load_checkpoint(file_path)

            if checkpoint and checkpoint.file_hash == file_hash:
                if checkpoint.is_complete():
                    completed_chunks = checkpoint.chunk_id + 1
                    if completed_chunks < total_chunks:
                        logger.warning(f"[Process File] 检查点标记为完成但块数不完整!")
                        logger.warning(f"  - 已完成块: {completed_chunks}, 总块数: {total_chunks}")
                        logger.info(f"[Process File] 将继续从第 {completed_chunks} 块开始处理")
                    else:
                        logger.info("[Process File] 文件已完全处理，跳过")
                        result.status = "completed"
                        result.checkpoint = checkpoint
                        result.processed_lines = checkpoint.processed_lines
                        result.completed_chunks = completed_chunks
                        return result

                if checkpoint.needs_resume():
                    logger.info(f"[Process File] 发现检查点，准备恢复:")
                    logger.info(f"  - Processed Lines: {checkpoint.processed_lines:,}")
                    logger.info(f"  - Last Chunk ID: {checkpoint.chunk_id}")
                    logger.info(f"  - Last Chunk Line: {checkpoint.last_chunk_line}")
                    result.checkpoint = checkpoint
            else:
                logger.info("[Process File] 检查点无效或文件已变更，将重新处理")
                checkpoint = None

        if checkpoint is None:
            logger.info("[Process File] 创建新检查点")
            checkpoint = self.checkpoint_manager.create_checkpoint(
                file_path=file_path,
                file_hash=file_hash,
                total_lines=total_lines
            )
            result.checkpoint = checkpoint

        start_chunk_id = 0
        start_line = 0

        if checkpoint and checkpoint.processed_lines > 0:
            start_chunk_id = checkpoint.chunk_id
            start_line = checkpoint.last_chunk_line

        all_stats = {
            'by_level': {},
            'error_types': {},
            'patterns': {},
            'top_classes': {}
        }

        logger.info("[Process File] 开始流式解析文件...")
        progress = ProgressTracker(total_lines, f"Processing {os.path.basename(file_path)}")
        log_memory_usage("Start processing")

        all_entries = []
        analysis_results = []
        chunk_results = {}
        
        try:
            llm_start = time.time()
            
            # 使用流式聚合器：边解析边聚合，不保留全部entries
            logger.info("[Process File] 使用流式聚合器进行第一遍扫描...")
            
            aggregator = StreamingStatsAggregator(
                max_error_samples=500,
                max_warn_samples=1000,
                max_info_samples=200,
                top_classes_limit=20,
                top_error_types_limit=20
            )
            
            parsing_start = time.time()
            last_progress_time = parsing_start
            for entries, cid, end_line in self.parser.parse_file_stream_mmap(file_path):
                if cid < start_chunk_id:
                    continue

                aggregator.ingest_chunk(entries, cid, end_line)

                # 定期输出解析进度
                now = time.time()
                if now - last_progress_time > 5.0:
                    elapsed = now - parsing_start
                    pct = (end_line / total_lines) * 100 if total_lines > 0 else 0
                    logger.info(f"[Process File] 解析进度: {end_line:,}/{total_lines:,} 行 ({pct:.1f}%), 耗时: {elapsed:.0f}s")
                    last_progress_time = now

                # 每处理一定数量的chunk后检查内存
                if cid % 5 == 0:
                    ensure_memory_safety()
            
            parsing_time = time.time() - parsing_start
            total_chunks_count = aggregator._chunk_count
            all_chunks_info = aggregator.get_chunks_info()
            
            log_memory_usage("After first pass scan")
            
            aggregator_summary = aggregator.get_summary()
            logger.info(f"[Process File] 第一遍扫描完成")
            logger.info(f"  总块数: {total_chunks_count}")
            logger.info(f"  总条目数: {aggregator_summary['total_entries']:,}")
            logger.info(f"  错误样本数: {aggregator_summary['error_samples_count']}")
            logger.info(f"  警告样本数: {aggregator_summary['warn_samples_count']}")
            logger.info(f"  INFO样本数: {aggregator_summary['info_samples_count']}")
            logger.info(f"  聚合器内存估算: {aggregator_summary['memory_estimate_mb']:.2f} MB")
            logger.info(f"  解析耗时: {parsing_time:.2f}s")
            
            # 获取最终统计信息
            all_stats = aggregator.get_final_stats()
            sample_data = aggregator.get_sample_data()
            all_chunk_statistics = aggregator.get_chunk_statistics()

            # 文件解析完成，准备开始AI分析
            if progress_callback:
                await progress_callback("ai_analysis_start")

            # === 统一路径：任何内存状态下，都使用第一遍扫描聚合的样本 + 统计信息，
            #     只调用一次 LLM（analyze_merged_chunks），不再走逐chunk调用 ===
            if self.use_llm and self.llm_client:
                logger.info(f"[Process File] 使用合并分析策略：基于第一遍扫描聚合结果，只调用一次 LLM")
                logger.info(f"[Process File] 合并分析 - 总块数: {total_chunks_count}")
                logger.info(f"[Process File] 合并分析 - 错误条目: {len(sample_data['error_entries'])}")
                logger.info(f"[Process File] 合并分析 - 警告条目: {len(sample_data['warn_entries'])}")
                logger.info(f"[Process File] 合并分析 - INFO条目: {len(sample_data['info_entries'])}")
                logger.info(f"[Process File] 合并分析 - 统计信息数: {len(all_chunk_statistics)}")

                merged_result = await self.llm_client.analyze_merged_chunks(
                    all_error_entries=sample_data['error_entries'],
                    all_statistics=all_chunk_statistics,
                    total_chunks=total_chunks_count,
                    all_warn_entries=sample_data['warn_entries'],
                    all_info_entries=sample_data['info_entries'],
                    content_callback=content_callback
                )

                merged_result.chunk_id = 0

                for cid, end_line, _ in all_chunks_info:
                    chunk_results[cid] = (merged_result, end_line)
            else:
                logger.info(f"[Process File] 使用规则模式处理 {total_chunks_count} 个分块")
                for entries, cid, end_line in self.parser.parse_file_stream_mmap(file_path):
                    if cid < start_chunk_id:
                        continue
                    ensure_memory_safety()
                    chunk_result = await self._process_chunk_with_rules(entries, cid)
                    chunk_results[cid] = (chunk_result, end_line)

            llm_time = time.time() - llm_start
            
            for cid in sorted(chunk_results.keys()):
                chunk_result, end_line = chunk_results[cid]
                analysis_results.append(chunk_result)
                
                if self.enable_checkpoint:
                    self._checkpoint_batch.append((cid, end_line, chunk_result))
                    if len(self._checkpoint_batch) >= self._checkpoint_batch_size:
                        self._flush_checkpoint_batch(checkpoint)
            
            if self._checkpoint_batch:
                self._flush_checkpoint_batch(checkpoint)
            
            result.analysis_results = analysis_results
            result.processed_lines = total_lines
            result.completed_chunks = len(analysis_results)

            logger.info("[Process File] 所有块处理完成，标记检查点为完成")
            checkpoint = self.checkpoint_manager.mark_complete(checkpoint)
            result.checkpoint = checkpoint
            result.status = "completed"
            result.completed_at = datetime.now()
            result.statistics = all_stats

            total_time = time.time() - start_total
            result.performance_metrics = {
                'total_time': total_time,
                'parse_time': parse_time,
                'parsing_time': parsing_time,
                'llm_time': llm_time,
                'chunks_per_second': total_chunks_count / total_time if total_time > 0 else 0,
                'lines_per_second': total_lines / total_time if total_time > 0 else 0
            }

            progress.finish()

            logger.info("=" * 80)
            logger.info("[Process File] 文件处理完成!")
            logger.info(f"  Status: {result.status}")
            logger.info(f"  Total Lines: {result.total_lines:,}")
            logger.info(f"  Processed Lines: {result.processed_lines:,}")
            logger.info(f"  Total Chunks: {result.total_chunks}")
            logger.info(f"  Completed Chunks: {result.completed_chunks}")
            logger.info(f"  Total Errors Found: {all_stats['by_level'].get('ERROR', 0):,}")
            logger.info(f"  Performance Metrics:")
            logger.info(f"    - Total Time: {total_time:.2f}s")
            logger.info(f"    - Parse Time: {parse_time:.2f}s")
            logger.info(f"    - Parsing Time: {parsing_time:.2f}s")
            logger.info(f"    - LLM Time: {llm_time:.2f}s")
            logger.info(f"    - Lines/Sec: {result.performance_metrics['lines_per_second']:.2f}")
            logger.info("=" * 80)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Process File] 处理文件时发生错误: {error_msg}")
            checkpoint = self.checkpoint_manager.mark_failed(checkpoint, error_msg)
            result.checkpoint = checkpoint
            result.status = "failed"
            result.error_message = error_msg
            result.completed_at = datetime.now()

        return result

    def _flush_checkpoint_batch(self, checkpoint):
        if not self._checkpoint_batch:
            return
        
        for cid, end_line, chunk_result in self._checkpoint_batch:
            checkpoint.chunk_id = cid
            checkpoint.last_chunk_line = end_line
            checkpoint.processed_lines = end_line
        
        self.checkpoint_manager.save_checkpoint(checkpoint)
        self._checkpoint_batch = []
        logger.info(f"[Checkpoint] 批量更新完成")

    def process_file(
        self,
        file_path: str,
        resume: bool = True,
        force_restart: bool = False
    ) -> ProcessingResult:
        try:
            # 检查当前是否有正在运行的事件循环
            loop = asyncio.get_running_loop()
            # 如果有正在运行的事件循环，使用 create_task
            return loop.run_until_complete(self.process_file_async(file_path, resume, force_restart))
        except RuntimeError:
            # 如果没有正在运行的事件循环，使用 asyncio.run
            return asyncio.run(self.process_file_async(file_path, resume, force_restart))

    def process_files_batch(
        self,
        file_paths: List[str],
        resume: bool = True
    ) -> List[ProcessingResult]:
        results = []

        logger.info("=" * 80)
        logger.info(f"[Batch Process] 开始批量处理 {len(file_paths)} 个文件")
        logger.info("=" * 80)

        for idx, file_path in enumerate(file_paths, 1):
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"[Batch Process] 处理文件 {idx}/{len(file_paths)}")
            logger.info(f"[Batch Process] File: {file_path}")
            logger.info("=" * 80)

            result = self.process_file(file_path, resume=resume)
            results.append(result)

            logger.info(f"[Batch Process] 文件 {idx} 处理完成:")
            logger.info(f"  - Status: {result.status}")
            logger.info(f"  - Processed: {result.processed_lines:,} / {result.total_lines:,} lines")
            if result.error_message:
                logger.info(f"  - Error: {result.error_message}")

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"[Batch Process] 批量处理完成!")
        logger.info(f"  Total Files: {len(file_paths)}")
        logger.info(f"  Successful: {sum(1 for r in results if r.status == 'completed')}")
        logger.info(f"  Failed: {sum(1 for r in results if r.status == 'failed')}")
        logger.info("=" * 80)

        return results

    async def process_files_batch_async(
        self,
        file_paths: List[str],
        resume: bool = True,
        max_concurrent: int = 2
    ) -> List[ProcessingResult]:
        """并行处理多个文件，带并发控制
        
        优化策略：
        1. 使用信号量限制并发数，避免内存溢出
        2. 并行解析 + 并行LLM调用
        3. 实时显示进度
        """
        from asyncio import Semaphore
        
        total_files = len(file_paths)
        results = [None] * total_files  # 保持顺序
        
        # 并发控制信号量
        semaphore = Semaphore(max_concurrent)
        
        # 进度跟踪
        completed_count = 0
        progress_lock = asyncio.Lock()
        
        async def process_single_file_with_progress(index: int, file_path: str):
            nonlocal completed_count
            
            async with semaphore:
                logger.info(f"[Parallel Process] 启动任务 {index+1}/{total_files}: {os.path.basename(file_path)}")
                
                try:
                    result = await self.process_file_async(file_path, resume=resume)
                    results[index] = result
                    
                    async with progress_lock:
                        completed_count += 1
                        logger.info(f"[Parallel Process] 任务 {completed_count}/{total_files} 完成: {os.path.basename(file_path)}")
                        if result.status == 'completed':
                            logger.info(f"  - 处理行数: {result.processed_lines:,} / {result.total_lines:,}")
                            logger.info(f"  - 耗时: {result.performance_metrics.get('total_time', 0):.2f}s")
                        else:
                            logger.info(f"  - 状态: {result.status}")
                            if result.error_message:
                                logger.info(f"  - 错误: {result.error_message}")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"[Parallel Process] 任务 {index+1} 失败: {e}")
                    error_result = ProcessingResult(
                        file_path=file_path,
                        total_lines=0,
                        processed_lines=0,
                        total_chunks=0,
                        completed_chunks=0,
                        status="failed",
                        started_at=datetime.now(),
                        error_message=str(e)
                    )
                    results[index] = error_result
                    
                    async with progress_lock:
                        completed_count += 1
                    
                    return error_result
        
        logger.info("=" * 80)
        logger.info(f"[Parallel Process] 开始并行处理 {total_files} 个文件")
        logger.info(f"  最大并发数: {max_concurrent}")
        logger.info(f"  预计加速比: ~{min(total_files, max_concurrent)}x")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # 创建所有任务并等待完成
        tasks = [
            process_single_file_with_progress(i, fp) 
            for i, fp in enumerate(file_paths)
        ]
        
        # 使用 gather 等待所有任务，但有并发控制
        await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # 统计结果
        successful = sum(1 for r in results if r and r.status == 'completed')
        failed = sum(1 for r in results if r and r.status == 'failed')
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"[Parallel Process] 批量处理完成!")
        logger.info(f"  总文件数: {total_files}")
        logger.info(f"  成功: {successful}")
        logger.info(f"  失败: {failed}")
        logger.info(f"  总耗时: {elapsed:.2f}s")
        logger.info(f"  串行预计耗时: ~{sum(r.performance_metrics.get('total_time', 0) for r in results if r):.2f}s")
        logger.info(f"  加速比: ~{(sum(r.performance_metrics.get('total_time', 0) for r in results if r) / elapsed):.2f}x")
        logger.info("=" * 80)
        
        return results