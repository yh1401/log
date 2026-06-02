"""Test script to verify PCAPProcessor import."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from log_analyzer.processor.pcap_processor import PCAPProcessor
    print("✅ PCAPProcessor 导入成功!")
    
    # 创建实例测试
    processor = PCAPProcessor(max_packets=1000)
    print("✅ PCAPProcessor 实例创建成功!")
    
    # 检查方法
    if hasattr(processor, 'process_file'):
        print("✅ process_file 方法存在")
    if hasattr(processor, 'generate_analysis_prompt'):
        print("✅ generate_analysis_prompt 方法存在")
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
except Exception as e:
    print(f"❌ 测试失败: {e}")