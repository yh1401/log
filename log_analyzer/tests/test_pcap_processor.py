#!/usr/bin/env python3
"""测试PCAP处理器功能"""

import sys
import os

# 直接导入模块，避免__init__.py的依赖问题
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
PCAPStatistics = pcap_processor.PCAPStatistics
PCAPPacket = pcap_processor.PCAPPacket

def test_pcap_processor():
    print("=== PCAP处理器测试 ===")
    
    # 测试PCAP处理器初始化
    processor = PCAPProcessor(max_packets=100)
    print("✅ PCAP处理器初始化成功")
    
    # 测试统计对象
    stats = processor.statistics
    print(f"初始统计: total_packets={stats.total_packets}, tcp_packets={stats.tcp_packets}")
    print("✅ 统计对象测试通过")
    
    # 测试提示词生成
    prompt = processor.generate_analysis_prompt()
    print(f"提示词长度: {len(prompt)} 字符")
    
    # 验证提示词内容
    assert "网络安全分析工程师" in prompt, "提示词缺少专家角色定义"
    assert "JSON格式" in prompt, "提示词缺少JSON格式要求"
    assert "protocol_analysis" in prompt, "提示词缺少协议分析字段"
    assert "anomaly_detection" in prompt, "提示词缺少异常检测字段"
    assert "evidence_chain" in prompt, "提示词缺少证据链字段"
    print("✅ 提示词生成测试通过")
    
    # 测试get_summary_for_report
    summary = processor.get_summary_for_report()
    assert 'statistics' in summary, "summary缺少statistics字段"
    assert 'sample_packets' in summary, "summary缺少sample_packets字段"
    assert 'errors' in summary, "summary缺少errors字段"
    assert 'warnings' in summary, "summary缺少warnings字段"
    print(f"summary keys: {list(summary.keys())}")
    print("✅ get_summary_for_report 测试通过")
    
    # 测试PCAPStatistics.to_dict()
    stats_dict = stats.to_dict()
    assert 'total_packets' in stats_dict, "to_dict缺少total_packets"
    assert 'tcp_packets' in stats_dict, "to_dict缺少tcp_packets"
    assert 'udp_packets' in stats_dict, "to_dict缺少udp_packets"
    print("✅ PCAPStatistics.to_dict() 测试通过")
    
    # 测试PCAPPacket
    packet = PCAPPacket(
        timestamp="2024-01-01 00:00:00",
        src_ip="192.168.1.1",
        dst_ip="192.168.1.2",
        protocol="TCP",
        src_port=12345,
        dst_port=80,
        flags="SYN",
        length=64,
        info="TCP SYN"
    )
    packet_dict = packet.to_dict()
    assert packet_dict['src_ip'] == "192.168.1.1", "PCAPPacket.to_dict错误"
    assert packet_dict['protocol'] == "TCP", "PCAPPacket.to_dict错误"
    print("✅ PCAPPacket 测试通过")
    
    print("\n=== 所有PCAP处理器基础测试通过! ===")

if __name__ == "__main__":
    test_pcap_processor()
