"""Chunk processor for handling large log files - Optimized Version."""

import os
import time
import logging
import asyncio
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Tuple

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
        chunk_size: int = 10000,
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
        self.merge_threshold = merge_threshold
        self.use_llm = use_llm
        
        self._checkpoint_batch = []
        self._checkpoint_batch_size = 5
        
        # 初始化规则分析器（当 use_llm=False 时使用）
        self._rule_based_analyzer = None

        logger.info("=" * 80)
        logger.info("[ChunkProcessor] 初始化完成")
        logger.info(f"  Chunk Size: {chunk_size}")
        logger.info(f"  Checkpoint Enabled: {enable_checkpoint}")
        logger.info(f"  Parallel Workers: {parallel_workers}")
        logger.info(f"  Parallel Processing: {enable_parallel_processing}")
        logger.info(f"  Merge Threshold: {merge_threshold}")
        logger.info(f"  Use LLM: {use_llm}")
        if not use_llm:
            logger.info("  ⚠️  警告: 使用规则模式，不调用LLM")
        logger.info("=" * 80)

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

        logger.info(f"  Error Entries: {len(error_entries)}")

        statistics = self.parser.get_error_statistics(entries)
        logger.info(f"[Processor] 错误统计信息: {statistics}")

        logger.info(f"[Processor] 准备调用 LLM 进行 Chunk #{chunk_id} 分析...")

        result = await self.llm_client.analyze_log_chunk(
            error_entries=error_entries,
            statistics=statistics,
            chunk_id=chunk_id
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
        force_restart: bool = False
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

        all_entries = []
        analysis_results = []
        chunk_results = {}
        
        try:
            parsing_start = time.time()
            all_chunks = []
            
            for entries, cid, end_line in self.parser.parse_file_stream_mmap(file_path):
                if cid < start_chunk_id:
                    continue
                all_chunks.append((entries, cid, end_line))
            
            parsing_time = time.time() - parsing_start
            logger.info(f"[Process File] 文件解析完成，共 {len(all_chunks)} 个块 (耗时: {parsing_time:.2f}s)")

            llm_start = time.time()
            
            for entries, cid, end_line in all_chunks:
                for entry in entries:
                    all_entries.append(entry)
                    level_key = entry.level.value if isinstance(entry.level, LogLevel) else str(entry.level)
                    all_stats['by_level'][level_key] = all_stats['by_level'].get(level_key, 0) + 1
                    if entry.error_type:
                        all_stats['error_types'][entry.error_type] = all_stats['error_types'].get(entry.error_type, 0) + 1
                    if entry.class_name:
                        all_stats['top_classes'][entry.class_name] = all_stats['top_classes'].get(entry.class_name, 0) + 1
            
            total_chunks_count = len(all_chunks)
            
            if total_chunks_count <= self.merge_threshold:
                if self.use_llm and self.llm_client:
                    logger.info(f"[Process File] 分块数 {total_chunks_count} <= 合并阈值 {self.merge_threshold}，执行合并分析策略")
                    logger.info(f"[Process File] 将所有 {total_chunks_count} 个分块的统计信息合并后进行单次LLM调用")
                    
                    all_error_entries = []
                    all_chunk_statistics = []
                    
                    for entries, cid, end_line in all_chunks:
                        error_entries = [
                            e.to_dict() for e in entries
                            if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL
                        ]
                        all_error_entries.extend(error_entries)
                        
                        statistics = self.parser.get_error_statistics(entries)
                        statistics['chunk_id'] = cid
                        all_chunk_statistics.append(statistics)
                    
                    logger.info(f"[Process File] 合并后总错误条目数: {len(all_error_entries)}")
                    logger.info(f"[Process File] 合并后统计信息数: {len(all_chunk_statistics)}")
                    
                    merged_result = await self.llm_client.analyze_merged_chunks(
                        all_error_entries=all_error_entries,
                        all_statistics=all_chunk_statistics,
                        total_chunks=total_chunks_count
                    )
                    
                    merged_result.chunk_id = 0
                    
                    for entries, cid, end_line in all_chunks:
                        chunk_results[cid] = (merged_result, end_line)
                else:
                    logger.info(f"[Process File] 使用规则模式处理 {total_chunks_count} 个分块")
                    for entries, cid, end_line in all_chunks:
                        chunk_result = await self._process_chunk_with_rules(entries, cid)
                        chunk_results[cid] = (chunk_result, end_line)
            
            elif self.enable_parallel_processing and total_chunks_count > 1:
                if self.use_llm and self.llm_client:
                    logger.info(f"[Process File] 使用并行处理模式，{self.parallel_workers} 个并发连接")
                    
                    chunks_data = []
                    for entries, cid, end_line in all_chunks:
                        error_entries = [
                            e.to_dict() for e in entries
                            if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL
                        ]
                        statistics = self.parser.get_error_statistics(entries)
                        chunks_data.append((cid, error_entries, statistics))
                    
                    analysis_results = await self.llm_client.batch_analyze(
                        chunks_data=chunks_data,
                        max_concurrent=self.parallel_workers
                    )
                    
                    for i, (entries, cid, end_line) in enumerate(all_chunks):
                        chunk_results[cid] = (analysis_results[i], end_line)
                else:
                    logger.info(f"[Process File] 使用并行处理模式（规则模式），{self.parallel_workers} 个并发连接")
                    import asyncio
                    semaphore = asyncio.Semaphore(self.parallel_workers)
                    
                    async def process_with_rules(entries, cid, end_line):
                        async with semaphore:
                            result = await self._process_chunk_with_rules(entries, cid)
                            return (cid, result, end_line)
                    
                    tasks = [
                        process_with_rules(entries, cid, end_line) 
                        for entries, cid, end_line in all_chunks
                    ]
                    
                    results = await asyncio.gather(*tasks)
                    for cid, result, end_line in results:
                        chunk_results[cid] = (result, end_line)
            else:
                chunk_id = start_chunk_id
                for entries, cid, end_line in all_chunks:
                    if cid < start_chunk_id:
                        continue

                    logger.info(f"[Process File] ========== 处理 Chunk #{cid} ==========")
                    logger.info(f"[Process File] 解析得到 {len(entries)} 条日志条目")

                    chunk_result = await self.process_chunk_async(entries, chunk_id)
                    chunk_results[cid] = (chunk_result, end_line)

                    chunk_id += 1

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
                'chunks_per_second': len(all_chunks) / total_time if total_time > 0 else 0,
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
            checkpoint = self.checkpoint_manager.update_checkpoint(
                checkpoint=checkpoint,
                processed_lines=end_line,
                chunk_id=cid,
                last_chunk_line=end_line,
                chunk_result=chunk_result.to_dict()
            )
        
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
        resume: bool = True
    ) -> List[ProcessingResult]:
        tasks = [self.process_file_async(fp, resume) for fp in file_paths]
        return await asyncio.gather(*tasks)