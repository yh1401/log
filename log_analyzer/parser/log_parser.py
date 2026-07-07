"""Log file parser with support for large files - Optimized Version."""

import re
import os
import mmap
import json
import asyncio
import aiofiles
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Iterator, Tuple, AsyncIterator
from enum import Enum
from functools import lru_cache

# 导入统一格式解析器
from .format_parser import (
    FormatParserFactory, FormatType, 
    LogEntry, FormatParser,
    JSONFormatParser, CSVFormatParser, XMLFormatParser,
    ExcelFormatParser, PDFFormatParser
)


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"
    UNKNOWN = "UNKNOWN"

    @classmethod
    @lru_cache(maxsize=64)
    def from_string(cls, level_str: str) -> 'LogLevel':
        level_str = level_str.upper().strip()
        mapping = {
            'DEBUG': cls.DEBUG,
            'INFO': cls.INFO,
            'WARN': cls.WARN,
            'WARNING': cls.WARN,
            'ERROR': cls.ERROR,
            'ERR': cls.ERROR,
            'FATAL': cls.FATAL,
            'CRITICAL': cls.FATAL
        }
        return mapping.get(level_str, cls.UNKNOWN)


LOG_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'  # timestamp
    r'\s+\[([^\]]+)\]'  # thread name
    r'\s+(\w+)'  # log level
    r'\s+([a-f0-9-]+)'  # uuid/trace_id
    r'\s+([^\s-]+)'  # class name
    r'\s+-\s+(.*)$'  # message
)

JAVA_LOG_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\]'  # timestamp [2026-06-21 20:00:00,000]
    r'\s+\[(\w+)\s*\]'  # log level [INFO ]
    r'\s+\[LOGID:([^\]]+)\]'  # LOGID [LOGID:xxx]
    r'\s+([^\s]+)'  # thread name
    r'\s+([^\s]+)'  # class name
    r'\s+-\s+(.*)$'  # message
)

TRACE_LOG_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'  # timestamp 2026-06-21 20:00:00.005
    r'\s+(\w+)'  # log level INFO/ERROR
    r'\s+([^\s]+)'  # method name
    r'\s*-\s*(.*)$'  # message
)

CSV_LOG_PATTERN = re.compile(
    r'^([a-f0-9]{32})\|'  # trace_id (32 hex chars)
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\|'  # timestamp
    r'([^\|]+)\|'  # class name
    r'([^\|]+)\|'  # method name
    r'([^\|]+)\|'  # device id
    r'([^\|]+)'  # other fields
)

STACK_TRACE_START = re.compile(r'^[\t ]*(?:at |Caused by:|Suppressed:)')
EXCEPTION_LINE = re.compile(r'^([a-zA-Z0-9\.]+(?:\.[a-zA-Z0-9\.]+)+):\s*(.*)$')

ERROR_EXTRACT_PATTERN = re.compile(r'([\w\.]+Exception|[\w\.]+Error):\s*(.*)$')

ERROR_INDICATORS = re.compile(
    r'\b(?:Exception|Error|error|fail|failed|failure|exception|Exception|Error|'
    r'Throwable|RuntimeException|IOException|NullPointerException|OutOfMemoryError|'
    r'SocketTimeoutException|ConnectException|TimeoutException|IllegalArgumentException|'
    r'IndexOutOfBoundsException|ClassNotFoundException|NoSuchMethodException|'
    r'InvalidParameterException|UnauthorizedException|ForbiddenException|'
    r'InternalServerError|ServiceUnavailable|DownstreamException|'
    r'not found|notFound|NotFound|is null|is null|NullReference)\b',
    re.IGNORECASE
)


@dataclass(frozen=True)
class ErrorPattern:
    pattern_type: str
    regex: str
    description: str
    severity: str = "medium"
    count: int = 0


@dataclass
class ParsedLogEntry:
    timestamp: datetime
    thread_name: str
    level: LogLevel
    trace_id: str
    class_name: str
    message: str
    raw_line: str
    line_number: int
    stack_trace: Optional[List[str]] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'thread_name': self.thread_name,
            'level': self.level.value if isinstance(self.level, LogLevel) else self.level,
            'trace_id': self.trace_id,
            'class_name': self.class_name,
            'message': self.message,
            'line_number': self.line_number,
            'stack_trace': self.stack_trace,
            'error_type': self.error_type,
            'error_message': self.error_message
        }

    def get_summary(self) -> str:
        if self.stack_trace and self.error_type:
            return f"[{self.level.value}] {self.error_type}: {self.error_message}"
        return f"[{self.level.value}] {self.message[:100]}"

    def contains_error_indicators(self) -> bool:
        if self.level in (LogLevel.ERROR, LogLevel.FATAL):
            return True
        full_text = f"{self.message} {self.stack_trace or ''}"
        return bool(ERROR_INDICATORS.search(full_text))


@dataclass
class LogChunk:
    chunk_id: int
    entries: List[ParsedLogEntry]
    start_line: int
    end_line: int
    file_path: str
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def get_stats(self) -> Dict[str, int]:
        return {
            'total': len(self.entries),
            'errors': self.error_count,
            'warnings': self.warning_count,
            'info': self.info_count
        }


class LogParser:
    DEFAULT_PATTERNS = [
        ErrorPattern(
            pattern_type="device_offline",
            regex=r"设备不在线|device.*offline|device.*not.*online",
            description="Device is offline",
            severity="high"
        ),
        ErrorPattern(
            pattern_type="permission_denied",
            regex=r"无设备权限|permission.*denied|access.*denied|无权限",
            description="Permission denied",
            severity="high"
        ),
        ErrorPattern(
            pattern_type="null_pointer",
            regex=r"NullPointerException|NPE|null.*pointer",
            description="Null pointer exception",
            severity="critical"
        ),
        ErrorPattern(
            pattern_type="timeout",
            regex=r"timeout|超时|Connection.*timeout|SocketTimeout",
            description="Timeout error",
            severity="medium"
        ),
        ErrorPattern(
            pattern_type="validation_error",
            regex=r"id不能为空|validation.*error|参数.*错误|必填",
            description="Validation error",
            severity="medium"
        ),
        ErrorPattern(
            pattern_type="database_error",
            regex=r"SQLException|SQL.*error|数据库.*异常|Database.*error",
            description="Database error",
            severity="high"
        ),
        ErrorPattern(
            pattern_type="network_error",
            regex=r"Network.*error|网络.*异常|ConnectException|Connection.*refused",
            description="Network error",
            severity="medium"
        ),
        ErrorPattern(
            pattern_type="authentication_error",
            regex=r"authentication|认证.*失败|token.*invalid|登录.*失败",
            description="Authentication error",
            severity="high"
        )
    ]

    def __init__(self, chunk_size: int = 10000, custom_patterns: Optional[List[ErrorPattern]] = None):
        self.chunk_size = chunk_size
        self.patterns = custom_patterns or self.DEFAULT_PATTERNS
        self._compiled_regex_cache = {}
        self._compile_patterns()

    def _compile_patterns(self):
        for pattern in self.patterns:
            try:
                self._compiled_regex_cache[pattern.pattern_type] = re.compile(pattern.regex, re.IGNORECASE)
            except re.error:
                self._compiled_regex_cache[pattern.pattern_type] = re.compile(re.escape(pattern.regex), re.IGNORECASE)

    @lru_cache(maxsize=100000)
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        try:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.now()

    def parse_line(self, line: str, line_number: int) -> Optional[ParsedLogEntry]:
        match = LOG_PATTERN.match(line)
        if match:
            timestamp_str, thread_name, level_str, trace_id, class_name, message = match.groups()
            timestamp = self._parse_timestamp(timestamp_str)
            level = LogLevel.from_string(level_str)
            entry = ParsedLogEntry(
                timestamp=timestamp,
                thread_name=thread_name.strip(),
                level=level,
                trace_id=trace_id,
                class_name=class_name,
                message=message,
                raw_line=line,
                line_number=line_number
            )
            if level == LogLevel.ERROR or level == LogLevel.FATAL:
                self._extract_error_info(entry)
            return entry

        match = JAVA_LOG_PATTERN.match(line)
        if match:
            timestamp_str, level_str, trace_id, thread_name, class_name, message = match.groups()
            timestamp_str = timestamp_str.replace(',', '.')
            timestamp = self._parse_timestamp(timestamp_str)
            level = LogLevel.from_string(level_str)
            entry = ParsedLogEntry(
                timestamp=timestamp,
                thread_name=thread_name.strip(),
                level=level,
                trace_id=trace_id,
                class_name=class_name,
                message=message,
                raw_line=line,
                line_number=line_number
            )
            if level == LogLevel.ERROR or level == LogLevel.FATAL:
                self._extract_error_info(entry)
            return entry

        match = TRACE_LOG_PATTERN.match(line)
        if match:
            timestamp_str, level_str, method_name, message = match.groups()
            timestamp = self._parse_timestamp(timestamp_str)
            level = LogLevel.from_string(level_str)
            entry = ParsedLogEntry(
                timestamp=timestamp,
                thread_name="",
                level=level,
                trace_id="",
                class_name=method_name,
                message=message,
                raw_line=line,
                line_number=line_number
            )
            if level == LogLevel.ERROR or level == LogLevel.FATAL:
                self._extract_error_info(entry)
            return entry

        match = CSV_LOG_PATTERN.match(line)
        if match:
            trace_id, timestamp_str, class_name, method_name, device_id, other_fields = match.groups()
            timestamp = self._parse_timestamp(timestamp_str)
            message = f"method={method_name}, device_id={device_id}, fields={other_fields}"
            
            # 检测 other_fields 中是否包含错误关键词，动态决定日志级别
            level = LogLevel.INFO
            if ERROR_INDICATORS.search(other_fields):
                level = LogLevel.ERROR
            
            entry = ParsedLogEntry(
                timestamp=timestamp,
                thread_name="",
                level=level,
                trace_id=trace_id,
                class_name=class_name,
                message=message,
                raw_line=line,
                line_number=line_number
            )
            
            # 如果是错误级别，提取错误信息
            if level == LogLevel.ERROR:
                self._extract_error_info(entry)
            
            return entry

        return None

    def _extract_error_info(self, entry: ParsedLogEntry) -> None:
        msg = entry.message
        if 'BaseBackRuntimeException' in msg or 'BaseBackRuntimeException' in entry.class_name:
            ex_match = ERROR_EXTRACT_PATTERN.search(msg)
            if ex_match:
                entry.error_type = ex_match.group(1)
                entry.error_message = ex_match.group(2)
            else:
                entry.error_type = "BaseBackRuntimeException"
                entry.error_message = msg
        elif entry.message.startswith('at '):
            entry.error_type = "StackTrace"
            entry.error_message = "Stack trace element"

    def parse_stack_trace_line(self, line: str) -> bool:
        return bool(STACK_TRACE_START.match(line))

    def parse_file_stream(self, file_path: str) -> Iterator[Tuple[List[ParsedLogEntry], int, int]]:
        """解析文件流，支持多种格式自动检测"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Log file not found: {file_path}")

        # 检测文件格式
        file_format = FormatParserFactory.detect_format(file_path)
        
        # 如果是非标准日志格式，使用格式解析器
        if file_format in [FormatType.JSON, FormatType.CSV, FormatType.XML, 
                          FormatType.EXCEL, FormatType.PDF]:
            yield from self._parse_with_format_parser(file_path, file_format)
            return

        # 标准日志格式解析
        entries: List[ParsedLogEntry] = []
        line_number = 0
        chunk_id = 0
        current_entry: Optional[ParsedLogEntry] = None
        stack_trace_lines: List[str] = []
        lines_in_current_chunk = 0

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line_number += 1
                lines_in_current_chunk += 1
                line = line.rstrip('\n\r')

                if self.parse_stack_trace_line(line):
                    if current_entry:
                        stack_trace_lines.append(line)
                    continue

                if current_entry and stack_trace_lines:
                    current_entry.stack_trace = stack_trace_lines.copy()
                    stack_trace_lines.clear()

                entry = self.parse_line(line, line_number)

                if entry:
                    if current_entry and entries:
                        entries[-1].stack_trace = stack_trace_lines.copy() if stack_trace_lines else None
                        stack_trace_lines.clear()

                    entries.append(entry)
                    current_entry = entry

                    if lines_in_current_chunk >= self.chunk_size:
                        yield entries, chunk_id, line_number
                        entries = []
                        chunk_id += 1
                        lines_in_current_chunk = 0
                elif line.strip():
                    if current_entry:
                        if self.parse_stack_trace_line(line):
                            stack_trace_lines.append(line)

            if current_entry and stack_trace_lines:
                current_entry.stack_trace = stack_trace_lines.copy()

            if entries:
                yield entries, chunk_id, line_number

    def _parse_with_format_parser(self, file_path: str, file_format: FormatType) -> Iterator[Tuple[List[ParsedLogEntry], int, int]]:
        """使用格式解析器解析非标准格式文件"""
        parser = FormatParserFactory.get_parser(file_path)
        chunk_id = 0
        
        for log_entries in parser.parse(file_path, self.chunk_size):
            parsed_entries = [self._convert_log_entry(entry) for entry in log_entries]
            if parsed_entries:
                end_line = parsed_entries[-1].line_number
                yield parsed_entries, chunk_id, end_line
                chunk_id += 1

    def _convert_log_entry(self, entry: LogEntry) -> ParsedLogEntry:
        """将统一格式的 LogEntry 转换为 ParsedLogEntry"""
        # 解析时间戳
        timestamp = self._parse_timestamp(entry.timestamp) if entry.timestamp else datetime.now()
        
        # 解析日志级别
        level_map = {
            'DEBUG': LogLevel.DEBUG,
            'INFO': LogLevel.INFO,
            'WARN': LogLevel.WARN,
            'WARNING': LogLevel.WARN,
            'ERROR': LogLevel.ERROR,
            'ERR': LogLevel.ERROR,
            'FATAL': LogLevel.FATAL,
            'CRITICAL': LogLevel.FATAL
        }
        level = level_map.get(entry.level.upper(), LogLevel.INFO)
        
        # 提取错误信息
        parsed = ParsedLogEntry(
            timestamp=timestamp,
            thread_name=entry.raw_data.get('thread', ''),
            level=level,
            trace_id=entry.trace_id or entry.raw_data.get('trace_id', ''),
            class_name=entry.class_name,
            method=entry.method,
            message=entry.message,
            device_id=entry.device_id,
            raw_line=json.dumps(entry.raw_data, ensure_ascii=False) if entry.raw_data else entry.message,
            line_number=entry.line_number
        )
        
        # 如果是错误级别，提取错误信息
        if level in [LogLevel.ERROR, LogLevel.FATAL]:
            self._extract_error_info(parsed)
        
        return parsed

    def parse_file_stream_mmap(self, file_path: str) -> Iterator[Tuple[List[ParsedLogEntry], int, int]]:
        """使用mmap解析文件流，支持多种格式自动检测"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Log file not found: {file_path}")

        # 检测文件格式
        file_format = FormatParserFactory.detect_format(file_path)
        
        # 如果是非标准日志格式，使用格式解析器（mmap不适合这些格式）
        if file_format in [FormatType.JSON, FormatType.CSV, FormatType.XML, 
                          FormatType.EXCEL, FormatType.PDF]:
            yield from self._parse_with_format_parser(file_path, file_format)
            return

        # 标准日志格式解析（使用mmap优化大文件处理）
        entries: List[ParsedLogEntry] = []
        line_number = 0
        chunk_id = 0
        current_entry: Optional[ParsedLogEntry] = None
        stack_trace_lines: List[str] = []
        lines_in_current_chunk = 0

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mm:
                for line in iter(mm.readline, b''):
                    line_number += 1
                    lines_in_current_chunk += 1
                    line = line.decode('utf-8', errors='replace').rstrip('\n\r')

                    if self.parse_stack_trace_line(line):
                        if current_entry:
                            stack_trace_lines.append(line)
                        continue

                    if current_entry and stack_trace_lines:
                        current_entry.stack_trace = stack_trace_lines.copy()
                        stack_trace_lines.clear()

                    entry = self.parse_line(line, line_number)

                    if entry:
                        if current_entry and entries:
                            entries[-1].stack_trace = stack_trace_lines.copy() if stack_trace_lines else None
                            stack_trace_lines.clear()

                        entries.append(entry)
                        current_entry = entry

                        if lines_in_current_chunk >= self.chunk_size:
                            yield entries, chunk_id, line_number
                            entries = []
                            chunk_id += 1
                            lines_in_current_chunk = 0
                    elif line.strip():
                        if current_entry:
                            if self.parse_stack_trace_line(line):
                                stack_trace_lines.append(line)

            if current_entry and stack_trace_lines:
                current_entry.stack_trace = stack_trace_lines.copy()

            if entries:
                yield entries, chunk_id, line_number

    async def parse_file_stream_async(self, file_path: str) -> AsyncIterator[Tuple[List[ParsedLogEntry], int, int]]:
        """异步解析文件流，支持多种格式自动检测"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Log file not found: {file_path}")

        # 检测文件格式
        file_format = FormatParserFactory.detect_format(file_path)
        
        # 如果是非标准日志格式，使用格式解析器
        if file_format in [FormatType.JSON, FormatType.CSV, FormatType.XML, 
                          FormatType.EXCEL, FormatType.PDF]:
            # 异步迭代器
            for chunk in self._parse_with_format_parser(file_path, file_format):
                yield chunk
            return

        # 标准日志格式解析
        entries: List[ParsedLogEntry] = []
        line_number = 0
        chunk_id = 0
        current_entry: Optional[ParsedLogEntry] = None
        stack_trace_lines: List[str] = []
        lines_in_current_chunk = 0

        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            async for line in f:
                line_number += 1
                lines_in_current_chunk += 1
                line = line.rstrip('\n\r')

                if self.parse_stack_trace_line(line):
                    if current_entry:
                        stack_trace_lines.append(line)
                    continue

                if current_entry and stack_trace_lines:
                    current_entry.stack_trace = stack_trace_lines.copy()
                    stack_trace_lines.clear()

                entry = self.parse_line(line, line_number)

                if entry:
                    if current_entry and entries:
                        entries[-1].stack_trace = stack_trace_lines.copy() if stack_trace_lines else None
                        stack_trace_lines.clear()

                    entries.append(entry)
                    current_entry = entry

                    if lines_in_current_chunk >= self.chunk_size:
                        yield entries, chunk_id, line_number
                        entries = []
                        chunk_id += 1
                        lines_in_current_chunk = 0
                elif line.strip():
                    if current_entry:
                        if self.parse_stack_trace_line(line):
                            stack_trace_lines.append(line)

            if current_entry and stack_trace_lines:
                current_entry.stack_trace = stack_trace_lines.copy()

            if entries:
                yield entries, chunk_id, line_number

    def parse_file(self, file_path: str) -> List[ParsedLogEntry]:
        all_entries = []
        for entries, _, _ in self.parse_file_stream(file_path):
            all_entries.extend(entries)
        return all_entries

    def create_chunks(self, entries: List[ParsedLogEntry], chunk_id: int, start_line: int) -> LogChunk:
        error_count = sum(1 for e in entries if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL)
        warning_count = sum(1 for e in entries if e.level == LogLevel.WARN)
        info_count = sum(1 for e in entries if e.level == LogLevel.INFO)

        return LogChunk(
            chunk_id=chunk_id,
            entries=entries,
            start_line=start_line,
            end_line=start_line + len(entries) - 1,
            file_path="",
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count
        )

    def match_patterns(self, entry: ParsedLogEntry) -> List[ErrorPattern]:
        matched = []
        text = entry.message
        if entry.error_type:
            text += " " + entry.error_type
        if entry.error_message:
            text += " " + entry.error_message

        for pattern_type, compiled_regex in self._compiled_regex_cache.items():
            if compiled_regex.search(text):
                for p in self.patterns:
                    if p.pattern_type == pattern_type:
                        matched.append(p)
                        break

        return matched

    def get_error_statistics(self, entries: List[ParsedLogEntry]) -> Dict[str, Any]:
        stats = {
            'total': len(entries),
            'by_level': {
                'ERROR': 0,
                'WARN': 0,
                'INFO': 0,
                'DEBUG': 0,
                'FATAL': 0,
                'UNKNOWN': 0
            },
            'error_types': {},
            'patterns': {},
            'top_classes': {},
            'time_range': {
                'start': None,
                'end': None
            }
        }

        error_entries = [e for e in entries if e.level == LogLevel.ERROR or e.level == LogLevel.FATAL]

        for entry in entries:
            level_key = entry.level.value if isinstance(entry.level, LogLevel) else str(entry.level)
            stats['by_level'][level_key] = stats['by_level'].get(level_key, 0) + 1

            if entry.error_type:
                stats['error_types'][entry.error_type] = stats['error_types'].get(entry.error_type, 0) + 1

            class_name = entry.class_name
            if class_name:
                stats['top_classes'][class_name] = stats['top_classes'].get(class_name, 0) + 1

        for entry in error_entries:
            matched = self.match_patterns(entry)
            for pattern in matched:
                stats['patterns'][pattern.pattern_type] = stats['patterns'].get(pattern.pattern_type, 0) + 1

        if entries:
            timestamps = [e.timestamp for e in entries if e.timestamp]
            if timestamps:
                stats['time_range']['start'] = min(timestamps).isoformat()
                stats['time_range']['end'] = max(timestamps).isoformat()

        stats['top_classes'] = dict(sorted(
            stats['top_classes'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])

        stats['error_types'] = dict(sorted(
            stats['error_types'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])

        return stats

    @staticmethod
    def count_lines_fast(file_path: str) -> int:
        if not os.path.exists(file_path):
            return 0
        
        with open(file_path, 'rb') as f:
            return sum(1 for _ in f)

    @staticmethod
    def count_lines_mmap(file_path: str) -> int:
        if not os.path.exists(file_path):
            return 0
        
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as mm:
                chunk_size = 64 * 1024 * 1024
                count = 0
                while True:
                    chunk = mm.read(chunk_size)
                    if not chunk:
                        break
                    count += chunk.count(b'\n')
                return count