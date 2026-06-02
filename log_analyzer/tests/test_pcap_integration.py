#!/usr/bin/env python3
"""PCAP处理器集成测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接从文件导入，避免processor/__init__.py的依赖
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pcap_processor", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "processor", "pcap_processor.py")
)
pcap_processor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcap_processor)
PCAPProcessor = pcap_processor.PCAPProcessor

def test_pcap_integration():
    print("=== PCAP处理器集成测试 ===")
    
    test_pcap_path = '/Users/a666/Documents/trae_projects/log/log_analyzer/uploads/192.168.169.234-reboot-device.pcap'
    
    if not os.path.exists(test_pcap_path):
        print(f"❌ 测试PCAP文件不存在: {test_pcap_path}")
        return
    
    print(f"测试PCAP文件: {test_pcap_path}")
    print(f"文件大小: {os.path.getsize(test_pcap_path):,} bytes")
    
    # 测试PCAP文件处理
    processor = PCAPProcessor(max_packets=100)
    stats, packets = processor.process_file(test_pcap_path)
    
    print("\n处理结果统计:")
    print(f"  总数据包数: {stats.total_packets}")
    print(f"  TCP数据包: {stats.tcp_packets}")
    print(f"  UDP数据包: {stats.udp_packets}")
    print(f"  ICMP数据包: {stats.icmp_packets}")
    print(f"  ASTERIX数据包: {stats.asterix_packets}")
    print(f"  错误数: {stats.error_count}")
    print(f"  警告数: {stats.warning_count}")
    print(f"  唯一IP数: {len(stats.unique_ips)}")
    print(f"  唯一端口数: {len(stats.unique_ports)}")
    
    print("\n数据包样本 (前3条):")
    for p in packets[:3]:
        print(f"  [{p.severity}] {p.timestamp[:23]} {p.protocol}: {p.src_ip}:{p.src_port or '-'} -> {p.dst_ip}:{p.dst_port or '-'}")
    
    # 测试生成分析提示词
    prompt = processor.generate_analysis_prompt()
    print(f"\n提示词生成: {len(prompt):,} 字符")
    
    # 验证提示词包含统计数据
    assert str(stats.total_packets) in prompt, "提示词未包含总数据包数"
    assert str(stats.tcp_packets) in prompt, "提示词未包含TCP数据包数"
    print("✅ 提示词包含统计数据")
    
    # 测试get_summary_for_report
    summary = processor.get_summary_for_report()
    assert len(summary['sample_packets']) > 0, "样本数据包为空"
    print(f"✅ get_summary_for_report 返回 {len(summary['sample_packets'])} 条样本")
    
    print("\n=== PCAP处理器集成测试通过! ===")

if __name__ == "__main__":
    test_pcap_integration()
