"""Test script for the merged analysis strategy."""

import os
import sys
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SCRIPT_DIR)

from log_analyzer.parser.log_parser import LogParser
from log_analyzer.checkpoint.manager import CheckpointManager
from log_analyzer.processor.chunk_processor import ChunkProcessor
from log_analyzer.config.settings import load_llm_config
from log_analyzer.llm.client import LLMClient


async def test_merge_strategy():
    """Test the merged analysis strategy with small file."""
    
    print("=" * 80)
    print("         Testing Merged Analysis Strategy")
    print("=" * 80)
    
    # Use a small test file with fewer than 5 chunks
    test_file = "/Users/a666/Documents/trae_projects/log/loggen/data/error/error.2026-05-26.49-1kline.txt"
    
    if not os.path.exists(test_file):
        print(f"Error: Test file not found - {test_file}")
        return
    
    file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
    print(f"\nTest File: {os.path.basename(test_file)}")
    print(f"File Size: {file_size_mb:.2f} MB")
    
    try:
        llm_config = load_llm_config("/Users/a666/Documents/trae_projects/log/loggen/llm/llmconfig")
        
        parser = LogParser(chunk_size=5000)  # Large chunk size to get fewer chunks
        llm_client = LLMClient(llm_config)
        checkpoint_manager = CheckpointManager("/Users/a666/Documents/trae_projects/log/log_analyzer/checkpoints")
        
        processor = ChunkProcessor(
            parser=parser,
            llm_client=llm_client,
            checkpoint_manager=checkpoint_manager,
            chunk_size=5000,
            enable_checkpoint=False,
            enable_parallel_processing=True,
            parallel_workers=4,
            merge_threshold=5
        )
        
        print("\nStarting processing...")
        print("Expected: Chunks <= 5 will trigger merged analysis strategy")
        
        result = await processor.process_file_async(test_file, force_restart=True)
        
        print(f"\n✅ Processing completed!")
        print(f"Status: {result.status}")
        print(f"Total Lines: {result.total_lines:,}")
        print(f"Total Chunks: {result.total_chunks}")
        print(f"Completed Chunks: {result.completed_chunks}")
        print(f"Analysis Results: {len(result.analysis_results)}")
        
        if result.performance_metrics:
            print(f"\nPerformance Metrics:")
            print(f"  Total Time: {result.performance_metrics.get('total_time', 0):.2f}s")
            print(f"  Parse Time: {result.performance_metrics.get('parse_time', 0):.2f}s")
            print(f"  LLM Time: {result.performance_metrics.get('llm_time', 0):.2f}s")
        
        if result.analysis_results:
            print(f"\nAnalysis Summary:")
            for ar in result.analysis_results:
                print(f"  Chunk #{ar.chunk_id}: {ar.summary[:100]}...")
        
        await llm_client.close()
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_merge_strategy())