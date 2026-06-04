"""Performance testing script for Log Analyzer optimization."""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SCRIPT_DIR)


class PerformanceTestResult:
    def __init__(self, file_path: str, file_size_mb: float):
        self.file_path = file_path
        self.file_size_mb = file_size_mb
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.total_lines = None
        self.processed_lines = None
        self.chunks_processed = None
        self.errors_found = None
        self.success = False
        self.error_message = None
        self.metrics: Dict[str, float] = {}
    
    def start(self):
        self.start_time = time.time()
    
    def end(self, success: bool = True, error_message: str = None):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message


def print_test_header():
    print("=" * 80)
    print("                    Log Analyzer Performance Test")
    print("=" * 80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    print("=" * 80)


def run_optimized_test(file_path: str) -> PerformanceTestResult:
    """Run the optimized version test."""
    result = PerformanceTestResult(file_path, os.path.getsize(file_path) / (1024 * 1024))
    result.start()
    
    try:
        import log_analyzer.parser.log_parser as parser_module
        import log_analyzer.llm.client as llm_module
        import log_analyzer.checkpoint.manager as checkpoint_module
        import log_analyzer.processor.chunk_processor as processor_module
        import log_analyzer.config.settings as config_module
        
        LogParser = parser_module.LogParser
        LLMClient = llm_module.LLMClient
        CheckpointManager = checkpoint_module.CheckpointManager
        ChunkProcessor = processor_module.ChunkProcessor
        init_settings = config_module.init_settings
        load_llm_config = config_module.load_llm_config
        
        init_settings()
        llm_config = load_llm_config("/Users/a666/Documents/trae_projects/log/log_analyzer/llmconfig")
        
        parser = LogParser(chunk_size=10000)
        llm_client = LLMClient(llm_config)
        checkpoint_manager = CheckpointManager("/Users/a666/Documents/trae_projects/log/log_analyzer/checkpoints")
        
        processor = ChunkProcessor(
            parser=parser,
            llm_client=llm_client,
            checkpoint_manager=checkpoint_manager,
            chunk_size=10000,
            enable_checkpoint=False,
            enable_parallel_processing=True,
            parallel_workers=4
        )
        
        processing_result = processor.process_file(file_path, force_restart=True)
        
        result.end(success=True)
        result.total_lines = processing_result.total_lines
        result.processed_lines = processing_result.processed_lines
        result.chunks_processed = processing_result.completed_chunks
        result.errors_found = processing_result.statistics.get('by_level', {}).get('ERROR', 0)
        result.metrics = processing_result.performance_metrics
        
    except Exception as e:
        result.end(success=False, error_message=str(e))
    
    return result


def generate_report(test_results: List[PerformanceTestResult], output_file: str = None):
    """Generate a comprehensive performance report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("          Log Analyzer Performance Test Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    total_duration = sum(r.duration for r in test_results if r.duration)
    avg_duration = total_duration / len(test_results) if test_results else 0
    
    report_lines.append("📊 Test Summary")
    report_lines.append("-" * 40)
    report_lines.append(f"Total Tests: {len(test_results)}")
    report_lines.append(f"Successful: {sum(1 for r in test_results if r.success)}")
    report_lines.append(f"Failed: {sum(1 for r in test_results if not r.success)}")
    report_lines.append(f"Total Duration: {total_duration:.2f}s")
    report_lines.append(f"Average Duration: {avg_duration:.2f}s")
    report_lines.append("")
    
    report_lines.append("📈 Detailed Results")
    report_lines.append("-" * 40)
    
    for i, result in enumerate(test_results, 1):
        report_lines.append(f"\nTest #{i}: {result.file_path}")
        report_lines.append(f"  File Size: {result.file_size_mb:.2f} MB")
        report_lines.append(f"  Status: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            report_lines.append(f"  Duration: {result.duration:.2f}s")
            report_lines.append(f"  Lines Processed: {result.processed_lines:,}")
            report_lines.append(f"  Chunks Processed: {result.chunks_processed}")
            report_lines.append(f"  Errors Found: {result.errors_found:,}")
            if result.metrics:
                report_lines.append(f"  Performance Metrics:")
                for key, value in result.metrics.items():
                    if key == 'total_time':
                        report_lines.append(f"    - Total Time: {value:.2f}s")
                    elif key == 'parse_time':
                        report_lines.append(f"    - Parse Time: {value:.2f}s")
                    elif key == 'llm_time':
                        report_lines.append(f"    - LLM Time: {value:.2f}s")
                    elif key == 'parsing_time':
                        report_lines.append(f"    - Parsing Time: {value:.2f}s")
                    elif key == 'lines_per_second':
                        report_lines.append(f"    - Lines/Second: {value:.2f}")
                    elif key == 'chunks_per_second':
                        report_lines.append(f"    - Chunks/Second: {value:.2f}")
        else:
            report_lines.append(f"  Error: {result.error_message}")
    
    report_lines.append("\n" + "=" * 80)
    report_lines.append("             Performance Comparison (Expected vs Optimized)")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    for result in test_results:
        if result.success:
            original_time = 78.0
            file_ratio = result.file_size_mb / 100
            expected_time = original_time * file_ratio
            
            speedup = expected_time / result.duration if result.duration > 0 else 0
            
            report_lines.append(f"\n{result.file_path} ({result.file_size_mb:.2f} MB):")
            report_lines.append(f"  Expected (Original): {expected_time:.2f}s")
            report_lines.append(f"  Actual (Optimized): {result.duration:.2f}s")
            report_lines.append(f"  Speedup: {speedup:.2f}x faster")
            report_lines.append(f"  Lines/Second: {result.processed_lines / result.duration:.0f}")
    
    report = "\n".join(report_lines)
    
    print("\n" + "=" * 80)
    print("                    TEST REPORT")
    print("=" * 80)
    print(report)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nReport saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Log Analyzer Performance Test")
    parser.add_argument('--file', '-f', type=str, help='Single file to test')
    parser.add_argument('--dir', '-d', type=str, help='Directory containing test files')
    parser.add_argument('--output', '-o', type=str, help='Output report file')
    args = parser.parse_args()
    
    test_files = []
    
    if args.file:
        if os.path.exists(args.file):
            test_files.append(args.file)
        else:
            print(f"Error: File not found - {args.file}")
            sys.exit(1)
    elif args.dir:
        if os.path.isdir(args.dir):
            for filename in os.listdir(args.dir):
                if filename.endswith('.log') or filename.endswith('.txt'):
                    filepath = os.path.join(args.dir, filename)
                    if os.path.isfile(filepath):
                        test_files.append(filepath)
            test_files.sort(key=lambda x: os.path.getsize(x))
        else:
            print(f"Error: Directory not found - {args.dir}")
            sys.exit(1)
    else:
        print("Error: Please specify --file or --dir")
        sys.exit(1)
    
    print_test_header()
    print(f"\nFound {len(test_files)} test file(s):")
    for f in test_files:
        size = os.path.getsize(f) / (1024 * 1024)
        print(f"  - {os.path.basename(f)}: {size:.2f} MB")
    
    test_results = []
    
    for i, file_path in enumerate(test_files, 1):
        print(f"\n{'=' * 80}")
        print(f"Running test {i}/{len(test_files)}: {os.path.basename(file_path)}")
        print(f"{'=' * 80}")
        
        result = run_optimized_test(file_path)
        
        if result.success:
            print(f"✅ Test completed in {result.duration:.2f}s")
            print(f"   Lines processed: {result.processed_lines:,}")
            print(f"   Errors found: {result.errors_found:,}")
        else:
            print(f"❌ Test failed: {result.error_message}")
        
        test_results.append(result)
    
    generate_report(test_results, args.output)


if __name__ == '__main__':
    main()