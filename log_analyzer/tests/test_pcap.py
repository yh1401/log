#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime

pcap_path = Path('/Users/a666/Documents/trae_projects/log/log_analyzer/uploads/192.168.169.234-reboot-device.pcap')
print('PCAP文件存在:', pcap_path.exists())
if pcap_path.exists():
    print('PCAP文件大小:', pcap_path.stat().st_size)

UPLOAD_DIR = Path('/Users/a666/Documents/trae_projects/log/log_analyzer/uploads')
log_content = []
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

try:
    from scapy.all import rdpcap, IP, TCP, UDP
    print('scapy导入成功')
    
    try:
        packets = rdpcap(str(pcap_path))
        print(f'成功读取 {len(packets)} 个数据包')
        
        log_content.append(f'{timestamp} [INFO] [PCAP] 文件路径: {pcap_path}')
        log_content.append(f'{timestamp} [INFO] [PCAP] 总数据包数: {len(packets)}')
        
        tcp_count = sum(1 for p in packets if TCP in p)
        udp_count = sum(1 for p in packets if UDP in p)
        
        log_content.append(f'{timestamp} [INFO] [PCAP] TCP数据包: {tcp_count}')
        log_content.append(f'{timestamp} [INFO] [PCAP] UDP数据包: {udp_count}')
        
        for i, packet in enumerate(packets[:20]):
            if IP in packet:
                src = packet[IP].src
                dst = packet[IP].dst
                if TCP in packet:
                    sport = packet[TCP].sport
                    dport = packet[TCP].dport
                    log_content.append(f'{timestamp} [INFO] [PCAP] TCP: {src}:{sport} -> {dst}:{dport}')
                elif UDP in packet:
                    sport = packet[UDP].sport
                    dport = packet[UDP].dport
                    log_content.append(f'{timestamp} [INFO] [PCAP] UDP: {src}:{sport} -> {dst}:{dport}')
        
        # 保存测试文件
        log_path = UPLOAD_DIR / f'test_pcap_converted.log'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
        
        print(f'转换成功! 保存到: {log_path}')
        print('\n文件内容:')
        with open(log_path, 'r') as f:
            print(f.read())
            
    except Exception as e:
        print(f'读取PCAP失败: {e}')
        import traceback
        traceback.print_exc()
        
except ImportError as e:
    print(f'scapy导入失败: {e}')
