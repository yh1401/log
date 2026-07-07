"""Log Analyzer - Main entry point."""

import os
import sys
import asyncio
import argparse
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import log_analyzer.config.settings as config_module
import log_analyzer.parser.log_parser as parser_module
import log_analyzer.checkpoint.manager as checkpoint_module
import log_analyzer.llm.client as llm_module
import log_analyzer.processor.chunk_processor as processor_module
import log_analyzer.report.generator as report_module
import log_analyzer.utils.helpers as utils_module

Settings = config_module.Settings
load_llm_config = config_module.load_llm_config
init_settings = config_module.init_settings
LogParser = parser_module.LogParser
CheckpointManager = checkpoint_module.CheckpointManager
Checkpoint = checkpoint_module.Checkpoint
LLMClient = llm_module.LLMClient
AnalysisResult = llm_module.AnalysisResult
ChunkProcessor = processor_module.ChunkProcessor
ProcessingResult = processor_module.ProcessingResult
ReportGenerator = report_module.ReportGenerator
Report = report_module.Report
ensure_dir = utils_module.ensure_dir
get_file_size_str = utils_module.get_file_size_str


def setup_logging(log_dir: str, log_level: int = logging.INFO) -> str:
    ensure_dir(log_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'process_{timestamp}.log')

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger.info(f"日志文件: {log_file}")
    return log_file


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log Analyzer - Large-scale log file analysis with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single log file
  python main.py --file /path/to/error.log

  # Process all log files in directory
  python main.py --dir /path/to/logs

  # Resume processing from checkpoint
  python main.py --file /path/to/error.log --resume

  # Force restart processing
  python main.py --file /path/to/error.log --force-restart

  # Generate JSON report only
  python main.py --file /path/to/error.log --format json
        """
    )

    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Path to a single log file to process'
    )

    parser.add_argument(
        '--dir', '-d',
        type=str,
        help='Path to directory containing log files'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to JSON configuration file (optional, uses config/config.json by default)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=str(SCRIPT_DIR / "reports"),
        help='Output directory for reports'
    )

    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        default=str(SCRIPT_DIR / "checkpoints"),
        help='Directory for checkpoint files'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=10000,
        help='Number of lines per chunk (default: 10000)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        default=True,
        help='Resume from checkpoint if available'
    )

    parser.add_argument(
        '--force-restart',
        action='store_true',
        help='Force restart processing, ignoring existing checkpoints'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'both'],
        default='both',
        help='Output report format (default: both)'
    )

    parser.add_argument(
        '--no-checkpoint',
        action='store_true',
        help='Disable checkpoint saving'
    )

    parser.add_argument(
        '--merge-threshold',
        type=int,
        default=5,
        help='Merge threshold for chunks - when chunks count <= this value, merge all and call LLM once (default: 5)'
    )

    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retries for LLM calls (default: 3)'
    )

    parser.add_argument(
        '--retry-delay',
        type=float,
        default=1.0,
        help='Delay between retries in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--list-files',
        action='store_true',
        help='List available log files and exit'
    )

    parser.add_argument(
        '--log-dir',
        type=str,
        default=str(SCRIPT_DIR / "logs"),
        help='Directory for log files'
    )

    return parser.parse_args()


def get_log_files(path: str) -> List[str]:
    if os.path.isfile(path):
        return [path]

    if os.path.isdir(path):
        files = []
        for file_name in os.listdir(path):
            file_path = os.path.join(path, file_name)
            # 支持所有日志文件和trace文件
            if os.path.isfile(file_path) and (
                file_name.endswith('.log') or 
                file_name.endswith('.txt') or
                'trace' in file_name.lower() or
                'stream' in file_name.lower() or
                'statistics' in file_name.lower()
            ):
                files.append(file_path)
        return sorted(files)

    return []


def print_banner():
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                    Log Analyzer v1.0                            ║
║        Large-scale Log Analysis with LLM Integration           ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_progress(current: int, total: int, prefix: str = "Progress"):
    if total > 0:
        percent = (current / total) * 100
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f'\r{prefix}: |{bar}| {percent:.1f}% ({current}/{total})', end='', flush=True)
        if current >= total:
            print()


async def async_main(args):
    print_banner()

    logging.info("=" * 80)
    logging.info("Log Analyzer v1.0 启动")
    logging.info("=" * 80)

    log_file = setup_logging(args.log_dir)
    logging.info(f"日志文件: {log_file}")
    logging.info(f"Log Dir: {args.log_dir}")
    logging.info(f"Config: {args.config}")
    logging.info(f"Output: {args.output}")
    logging.info(f"Checkpoint: {args.checkpoint_dir}")
    logging.info(f"Chunk Size: {args.chunk_size}")
    logging.info("=" * 80)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Log file: {log_file}")

    # 使用统一配置体系
    settings = init_settings(args.config)
    llm_config = settings.llm
    
    # 如果命令行参数未指定，则使用配置文件中的默认值
    chunk_size = args.chunk_size if args.chunk_size else settings.processing.chunk_size
    max_retries = args.max_retries if args.max_retries else settings.processing.max_retries
    retry_delay = args.retry_delay if args.retry_delay else settings.processing.retry_delay
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] LLM Config: {llm_config.model_name}")

    ensure_dir(args.output)
    ensure_dir(args.checkpoint_dir)

    llm_client = LLMClient(
        config=llm_config,
        max_retries=max_retries,
        retry_delay=retry_delay
    )

    parser = LogParser(chunk_size=chunk_size)

    checkpoint_manager = CheckpointManager(
        checkpoint_dir=args.checkpoint_dir
    )

    processor = ChunkProcessor(
        parser=parser,
        llm_client=llm_client,
        checkpoint_manager=checkpoint_manager,
        chunk_size=args.chunk_size,
        enable_checkpoint=not args.no_checkpoint,
        progress_callback=lambda c, t: print_progress(c, t, f"Chunk {c}/{t}"),
        merge_threshold=args.merge_threshold
    )

    # 如果未指定 file 或 dir，使用默认目录
    target_path = args.file or args.dir or str(SCRIPT_DIR / "logs")
    if target_path is None:
        print("[ERROR] 请指定 --file 或 --dir 参数")
        return 1

    log_files = get_log_files(target_path)

    if not log_files:
        print(f"[ERROR] No log files found in {target_path}")
        return 1

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(log_files)} log file(s)")

    # 根据文件数量选择处理策略
    if len(log_files) == 1:
        # 单文件：串行处理
        log_file = log_files[0]
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing: {log_file}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] File size: {get_file_size_str(log_file)}")

        result = await processor.process_file_async(
            file_path=log_file,
            resume=args.resume,
            force_restart=args.force_restart
        )

        if result.status == "completed":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing completed!")

            report_generator = ReportGenerator(output_dir=args.output)
            report = report_generator.generate_report(result)
            saved_files = report_generator.save_report(report, format=args.format)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Reports saved:")
            for saved_file in saved_files:
                print(f"  - {saved_file}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing failed: {result.error_message}")
    else:
        # 多文件：并行处理
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 启用并行处理模式")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 文件列表:")
        for idx, log_file in enumerate(log_files, 1):
            print(f"  {idx}. {os.path.basename(log_file)} ({get_file_size_str(log_file)})")
        
        # 使用并行处理（最多2个并发，避免内存溢出）
        results = await processor.process_files_batch_async(
            file_paths=log_files,
            resume=args.resume,
            max_concurrent=2
        )

        # 生成报告
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始生成报告...")
        report_generator = ReportGenerator(output_dir=args.output)
        
        for idx, result in enumerate(results, 1):
            if result.status == "completed":
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 报告 {idx}/{len(results)}:")
                print(f"  文件: {os.path.basename(result.file_path)}")
                report = report_generator.generate_report(result)
                saved_files = report_generator.save_report(report, format=args.format)
                print(f"  保存:")
                for saved_file in saved_files:
                    print(f"    - {saved_file}")
            else:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 报告 {idx} 失败: {result.error_message}")

    await llm_client.close()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] All processing completed!")
    logging.info("=" * 80)
    logging.info("所有文件处理完成")
    logging.info(f"日志文件: {log_file}")
    logging.info("=" * 80)
    return 0


def main():
    args = parse_arguments()

    if args.list_files:
        log_files = get_log_files(args.file if args.file else args.dir)
        print("Available log files:")
        for f in log_files:
            print(f"  - {f} ({get_file_size_str(f)})")
        return 0

    try:
        exit_code = asyncio.run(async_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Processing was interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
