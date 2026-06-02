"""PCAP file processor for network traffic analysis."""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PCAPStatistics:
    total_packets: int = 0
    total_bytes: int = 0
    tcp_packets: int = 0
    udp_packets: int = 0
    icmp_packets: int = 0
    other_packets: int = 0
    tcp_syn_count: int = 0
    tcp_rst_count: int = 0
    tcp_fin_count: int = 0
    tcp_ack_count: int = 0
    http_requests: int = 0
    dns_queries: int = 0
    error_count: int = 0
    warning_count: int = 0
    unique_ips: List[str] = field(default_factory=list)
    unique_ports: List[int] = field(default_factory=list)
    asterix_packets: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_packets': self.total_packets,
            'total_bytes': self.total_bytes,
            'tcp_packets': self.tcp_packets,
            'udp_packets': self.udp_packets,
            'icmp_packets': self.icmp_packets,
            'other_packets': self.other_packets,
            'tcp_syn_count': self.tcp_syn_count,
            'tcp_rst_count': self.tcp_rst_count,
            'tcp_fin_count': self.tcp_fin_count,
            'tcp_ack_count': self.tcp_ack_count,
            'http_requests': self.http_requests,
            'dns_queries': self.dns_queries,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'unique_ips': self.unique_ips[:10],
            'unique_ports': self.unique_ports[:20],
            'asterix_packets': self.asterix_packets
        }


@dataclass
class PCAPPacket:
    timestamp: str
    src_ip: str
    dst_ip: str
    protocol: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    flags: Optional[str] = None
    length: int = 0
    info: str = ""
    severity: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'protocol': self.protocol,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'flags': self.flags,
            'length': self.length,
            'info': self.info,
            'severity': self.severity
        }


class PCAPProcessor:
    """Direct PCAP file processor using tshark/tcpdump."""

    def __init__(self, max_packets: int = 1000):
        self.max_packets = max_packets
        self.statistics = PCAPStatistics()
        self.packets: List[PCAPPacket] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def process_file(self, pcap_path: str) -> Tuple[PCAPStatistics, List[PCAPPacket]]:
        """
        Process PCAP file and return statistics and packet details.

        Returns:
            Tuple of (statistics, packets)
        """
        logger.info(f"[PCAP Processor] 开始处理文件: {pcap_path}")

        p = Path(pcap_path)
        if not p.exists():
            raise FileNotFoundError(f"PCAP文件不存在: {pcap_path}")

        file_size = p.stat().st_size
        logger.info(f"[PCAP Processor] 文件大小: {file_size} bytes")

        self._extract_statistics(pcap_path)
        self._extract_packet_details(pcap_path)

        logger.info(f"[PCAP Processor] 处理完成:")
        logger.info(f"  - 总数据包: {self.statistics.total_packets}")
        logger.info(f"  - TCP数据包: {self.statistics.tcp_packets}")
        logger.info(f"  - UDP数据包: {self.statistics.udp_packets}")
        logger.info(f"  - 错误数: {self.statistics.error_count}")
        logger.info(f"  - 警告数: {self.statistics.warning_count}")

        return self.statistics, self.packets

    def _extract_statistics(self, pcap_path: str) -> None:
        """Extract protocol hierarchy statistics using tshark."""
        logger.info("[PCAP Processor] 提取协议统计信息...")

        try:
            cmd = ['tshark', '-r', pcap_path, '-q', '-z', 'io,phs']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, errors='replace')

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'frames:' in line and 'bytes:' in line:
                        bytes_match = line.split('bytes:')[1].split(')')[0].strip() if 'bytes:' in line else '0'
                        self.statistics.total_bytes = int(bytes_match.replace(',', ''))

                    if 'tcp' in line.lower():
                        self.statistics.tcp_packets = self._extract_frame_count(line)
                    elif 'udp' in line.lower():
                        self.statistics.udp_packets = self._extract_frame_count(line)
                    elif 'icmp' in line.lower():
                        self.statistics.icmp_packets = self._extract_frame_count(line)
                    elif 'asterix' in line.lower():
                        self.statistics.asterix_packets = self._extract_frame_count(line)

        except Exception as e:
            logger.error(f"[PCAP Processor] 统计提取失败: {e}")

        logger.info(f"[PCAP Processor] 协议统计: TCP={self.statistics.tcp_packets}, UDP={self.statistics.udp_packets}, ASTERIX={self.statistics.asterix_packets}")

    def _extract_frame_count(self, line: str) -> int:
        """Extract frame count from tshark output line."""
        try:
            if 'frames:' in line:
                count_str = line.split('frames:')[1].split('bytes:')[0].strip()
                return int(count_str.replace(',', ''))
        except:
            pass
        return 0

    def _extract_packet_details(self, pcap_path: str) -> None:
        """Extract detailed packet information."""
        logger.info("[PCAP Processor] 提取数据包详情...")

        try:
            cmd = [
                'tshark', '-r', pcap_path,
                '-T', 'fields',
                '-e', 'frame.time',
                '-e', 'ip.src',
                '-e', 'ip.dst',
                '-e', '_ws.col.Protocol',
                '-e', 'tcp.srcport',
                '-e', 'tcp.dstport',
                '-e', 'tcp.flags',
                '-e', 'tcp.len',
                '-e', '_ws.col.Info',
                '-E', 'separator=|'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, errors='replace')

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                self.statistics.total_packets = len(lines)

                unique_ips = set()
                unique_ports = set()

                for line in lines[:self.max_packets]:
                    parts = line.split('|')
                    if len(parts) < 5:
                        continue

                    try:
                        timestamp = parts[0] if parts[0] else datetime.now().isoformat()
                        src_ip = parts[1] if parts[1] else ''
                        dst_ip = parts[2] if parts[2] else ''
                        protocol = parts[3] if parts[3] else ''

                        if src_ip:
                            unique_ips.add(src_ip)
                        if dst_ip:
                            unique_ips.add(dst_ip)

                        packet = PCAPPacket(
                            timestamp=timestamp,
                            src_ip=src_ip,
                            dst_ip=dst_ip,
                            protocol=protocol,
                            info=parts[-1] if parts[-1] else ''
                        )

                        if protocol == 'TCP':
                            src_port = parts[4] if len(parts) > 4 and parts[4] else None
                            dst_port = parts[5] if len(parts) > 5 and parts[5] else None
                            flags = parts[6] if len(parts) > 6 and parts[6] else ''
                            length = parts[7] if len(parts) > 7 and parts[7] else '0'

                            packet.src_port = int(src_port) if src_port and src_port.isdigit() else None
                            packet.dst_port = int(dst_port) if dst_port and dst_port.isdigit() else None
                            packet.flags = flags
                            packet.length = int(length) if length.isdigit() else 0

                            if src_port and src_port.isdigit():
                                unique_ports.add(int(src_port))
                            if dst_port and dst_port.isdigit():
                                unique_ports.add(int(dst_port))

                            if 'RST' in flags:
                                packet.severity = 'ERROR'
                                self.statistics.tcp_rst_count += 1
                                self.statistics.error_count += 1
                                self.errors.append(f"TCP RST: {src_ip}:{packet.src_port} -> {dst_ip}:{packet.dst_port}")
                            elif 'SYN' in flags and 'ACK' not in flags:
                                packet.severity = 'WARN'
                                self.statistics.tcp_syn_count += 1
                                self.statistics.warning_count += 1
                            elif 'FIN' in flags:
                                self.statistics.tcp_fin_count += 1
                            elif 'ACK' in flags:
                                self.statistics.tcp_ack_count += 1

                        elif protocol == 'UDP':
                            src_port = parts[4] if len(parts) > 4 and parts[4] else None
                            dst_port = parts[5] if len(parts) > 5 and parts[5] else None

                            packet.src_port = int(src_port) if src_port and src_port.isdigit() else None
                            packet.dst_port = int(dst_port) if dst_port and dst_port.isdigit() else None

                            if src_port and src_port.isdigit():
                                unique_ports.add(int(src_port))
                            if dst_port and dst_port.isdigit():
                                unique_ports.add(int(dst_port))

                            if packet.dst_port == 53:
                                self.statistics.dns_queries += 1

                        elif protocol == 'HTTP':
                            self.statistics.http_requests += 1

                        self.packets.append(packet)

                    except (IndexError, ValueError) as e:
                        logger.warning(f"[PCAP Processor] 解析数据包行失败: {e}")
                        continue

                self.statistics.unique_ips = list(unique_ips)
                self.statistics.unique_ports = list(unique_ports)

        except Exception as e:
            logger.error(f"[PCAP Processor] 数据包详情提取失败: {e}")

    def generate_analysis_prompt(self) -> str:
        """Generate analysis prompt for LLM."""
        stats = self.statistics

        prompt = f"""你是一名资深的网络安全分析工程师和流量分析专家，擅长分析PCAP网络抓包数据、识别网络协议、检测异常行为，并提供专业的网络性能优化建议。

## 任务说明
请对提供的PCAP网络抓包数据进行深度分析，生成一份结构完整、内容详实的专业网络流量分析报告。

## 报告结构要求

### 一、基础信息概览
1. **分析信息**: 分析日期、抓包文件标识
2. **流量概览**: 抓包时长、总包数、总流量(字节)
3. **通信矩阵**: 生成通信角色表格，包含源IP、目的IP、端口、协议类型
4. **协议分布**: 传输层(TCP/UDP/ICMP)和应用层(HTTP/DNS等)协议占比

### 二、连接生命周期分析
1. **TCP握手分析**: SYN/SYN-ACK/ACK时序、握手耗时统计
2. **连接状态追踪**: 按时间线梳理连接建立、数据传输、连接关闭全流程
3. **链路质量评估**: 丢包率、重传率、延迟分析

### 三、流量特征分析
1. **流量分布**: 上下行帧数/流量/占比统计表，分析流量不对称比例
2. **包大小分析**: 按包大小分类统计(<64B, 64-128B, 128-256B, 256-512B, >512B)并标注业务含义
3. **TCP窗口分析**: TCP初始窗口、窗口增长/衰减、应用消费速率匹配评估

### 四、协议识别与分析
1. **协议分类统计**: 识别所有应用层协议(DNS/HTTP/TLS/SSH等)
2. **协议行为分析**: 各协议的请求/响应模式、数据传输特征
3. **特殊协议识别**: 如ASTERIX(航空监控协议)等专用协议的分析

### 五、异常行为检测
1. **连接异常**: SYN泛洪、连接超时、半开连接、RST异常
2. **流量异常**: 突发流量、异常大包、流量畸形
3. **协议异常**: 协议格式错误、异常端口访问、可疑通信模式
4. **安全风险**: 潜在的扫描行为、数据泄露风险、中间人攻击迹象

### 六、关键问题清单
按严重程度分级列出问题：
- **严重(Critical)**: 影响业务正常运行的问题
- **中等(Medium)**: 影响性能但不阻断业务的问题
- **低(Low)**: 优化建议类问题

每个问题需包含：现象描述、技术根因、业务影响

### 七、优化建议
分优先级给出具体可落地的优化方案：
1. **高优先级**: 立即需要处理的问题
2. **中优先级**: 短期(1-2周)需要处理的问题
3. **低优先级**: 长期优化建议

建议内容包括：业务策略调整、TCP参数优化、连接管理、安全加固等，可附带具体配置命令

### 八、预期收益评估
生成优化前后对比表格，包含指标名称、优化前、优化后、预期收益

### 九、证据链
列出支撑分析结论的关键数据包证据，包含时间戳、数据包摘要、关联分析

## 输出格式要求
**必须使用有效的JSON格式输出**，包含以下字段：

```json
{{
  "summary": "分析报告摘要(150字以内)",
  "basic_info": {{
    "analysis_date": "日期",
    "packet_count": 0,
    "total_bytes": 0,
    "protocols": [{{"name": "TCP", "count": 0, "percentage": 0.0}}]
  }},
  "connection_lifecycle": {{
    "handshake_analysis": "...",
    "connection_states": ["..."]
  }},
  "traffic_features": {{
    "flow_distribution": {{}},
    "packet_size_analysis": []
  }},
  "protocol_analysis": {{
    "identified_protocols": [],
    "protocol_behavior": {{}}
  }},
  "anomaly_detection": {{
    "connection_anomalies": [],
    "traffic_anomalies": [],
    "security_risks": []
  }},
  "key_issues": [{{
    "severity": "critical|medium|low",
    "phenomenon": "...",
    "root_cause": "...",
    "business_impact": "..."
  }}],
  "optimization_suggestions": [{{
    "priority": "high|medium|low",
    "category": "...",
    "suggestion": "...",
    "implementation": "..."
  }}],
  "expected_benefits": [{{
    "metric": "...",
    "before": "...",
    "after": "...",
    "benefit": "..."
  }}],
  "evidence_chain": [{{
    "timestamp": "...",
    "packet_info": "...",
    "relevance": "..."
  }}]
}}
```

## 分析原则
1. **基于证据**: 所有推断必须有数据包证据支撑
2. **专业准确**: 使用正确的网络协议术语
3. **可操作性**: 建议必须具体、可落地
4. **安全视角**: 从网络安全角度评估潜在风险

---

## 抓包数据详情

### 网络流量统计
- 总数据包数: {stats.total_packets}
- 总字节数: {stats.total_bytes:,}
- 协议分布:
  - TCP: {stats.tcp_packets} ({stats.tcp_packets/max(stats.total_packets,1)*100:.1f}%)
  - UDP: {stats.udp_packets} ({stats.udp_packets/max(stats.total_packets,1)*100:.1f}%)
  - ICMP: {stats.icmp_packets}
  - ASTERIX: {stats.asterix_packets} (航空监控协议)

### TCP会话分析
- SYN请求: {stats.tcp_syn_count}
- RST重置: {stats.tcp_rst_count}
- FIN结束: {stats.tcp_fin_count}
- ACK确认: {stats.tcp_ack_count}

### 应用层协议
- HTTP请求: {stats.http_requests}
- DNS查询: {stats.dns_queries}

### 异常统计
- 错误数: {stats.error_count}
- 警告数: {stats.warning_count}

### 唯一IP地址 ({len(stats.unique_ips)}个)
{', '.join(stats.unique_ips[:10])}
{"..." if len(stats.unique_ips) > 10 else ""}

### 唯一端口 ({len(stats.unique_ports)}个)
{', '.join(map(str, stats.unique_ports[:20]))}
{"..." if len(stats.unique_ports) > 20 else ""}

### 错误详情
{chr(10).join(self.errors[:10]) if self.errors else "无"}

### 警告详情
{chr(10).join(self.warnings[:10]) if self.warnings else "无"}

### 数据包样本 (前10条)
{chr(10).join([f"- {p.timestamp} {p.protocol}: {p.src_ip}:{p.src_port or '-'} -> {p.dst_ip}:{p.dst_port or '-'} [{p.info[:80]}]" for p in self.packets[:10]])}

---

请按照上述要求生成专业的PCAP网络流量分析报告，确保JSON格式有效。
"""

        return prompt

    def get_summary_for_report(self) -> Dict[str, Any]:
        """Get summary data for report generation."""
        return {
            'statistics': self.statistics.to_dict(),
            'sample_packets': [p.to_dict() for p in self.packets[:20]],
            'errors': self.errors[:20],
            'warnings': self.warnings[:20]
        }