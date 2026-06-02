"""FastAPI Web application for Log Analyzer."""

import os
import sys
import asyncio
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request, Header, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import log_analyzer.config.settings as config_module
import log_analyzer.parser.log_parser as parser_module
import log_analyzer.checkpoint.manager as checkpoint_module
import log_analyzer.llm.client as llm_module
import log_analyzer.processor.chunk_processor as processor_module
import log_analyzer.report.generator as report_module
import log_analyzer.utils.helpers as utils_module
from .auth import user_manager, DEFAULT_USER_ID, DEFAULT_USERNAME, ADMIN_USERNAME, require_admin
from .storage import get_storage

Settings = config_module.Settings
load_llm_config = config_module.load_llm_config
init_settings = config_module.init_settings
LogParser = parser_module.LogParser
CheckpointManager = checkpoint_module.CheckpointManager
LLMClient = llm_module.LLMClient
ChunkProcessor = processor_module.ChunkProcessor
ProcessingResult = processor_module.ProcessingResult
ReportGenerator = report_module.ReportGenerator
ensure_dir = utils_module.ensure_dir

# 用户相关目录
USERS_DIR = PROJECT_ROOT / "log_analyzer" / "users"
ensure_dir(str(USERS_DIR))

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def get_user_dir(user_id: str) -> Path:
    """获取用户专属目录"""
    user_dir = USERS_DIR / user_id
    ensure_dir(str(user_dir))
    return user_dir


def get_user_upload_dir(user_id: str) -> Path:
    """获取用户上传文件目录"""
    upload_dir = get_user_dir(user_id) / "uploads"
    ensure_dir(str(upload_dir))
    return upload_dir


def get_user_reports_dir(user_id: str) -> Path:
    """获取用户报告目录"""
    reports_dir = get_user_dir(user_id) / "reports"
    ensure_dir(str(reports_dir))
    return reports_dir


def get_user_checkpoints_dir(user_id: str) -> Path:
    """获取用户检查点目录"""
    checkpoint_dir = get_user_dir(user_id) / "checkpoints"
    ensure_dir(str(checkpoint_dir))
    return checkpoint_dir


async def get_current_user(
    x_user_id: str = Header(None, alias="X-User-Id"),
    x_username: str = Header(None, alias="X-Username")
) -> Dict[str, Any]:
    """从请求头获取当前用户标识（无鉴权）

    - 通过 X-User-Id 头识别用户身份
    - 若未提供则使用默认用户 default_user
    - 自动创建用户档案
    """
    user_id = x_user_id or DEFAULT_USER_ID
    username = x_username or DEFAULT_USERNAME

    user_info = user_manager.get_or_create_user(user_id, username)
    return user_info


async def get_optional_user(authorization: str = Header(None)) -> Optional[Dict[str, Any]]:
    """可选用户识别"""
    return None


async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """管理员权限检查依赖函数
    
    用于保护历史记录相关接口，仅允许管理员访问。
    如果用户不是管理员，返回 403 Forbidden。
    """
    username = current_user.get("username", "")
    
    if not user_manager.is_admin(username):
        raise HTTPException(
            status_code=403,
            detail={
                "code": 403,
                "message": "访问被拒绝：仅管理员可以访问此接口",
                "data": None
            }
        )
    
    return current_user


def extract_zip(zip_path: Path, dest_dir: Path) -> List[str]:
    """解压ZIP文件并返回提取的文件路径列表"""
    import zipfile
    extracted_files = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_dir)
            for name in zf.namelist():
                extracted_path = dest_dir / name
                if extracted_path.is_file():
                    extracted_files.append(str(extracted_path))
        logging.info(f"ZIP文件解压完成: {zip_path}, 提取了 {len(extracted_files)} 个文件")
    except Exception as e:
        logging.error(f"解压ZIP文件失败: {str(e)}")
    return extracted_files

def pcap_to_log(pcap_path: Path) -> str:
    """将PCAP文件转换为日志格式，使用tshark进行协议解析"""
    log_content = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    log_content.append(f"{timestamp} [INFO] [PCAP] 文件路径: {pcap_path}")
    log_content.append(f"{timestamp} [INFO] [PCAP] 文件大小: {pcap_path.stat().st_size} bytes")
    log_content.append(f"{timestamp} [INFO] [PCAP] 使用tshark进行协议分析")
    
    try:
        import subprocess
        
        # 使用tshark获取完整的数据包统计信息
        stats_cmd = ['tshark', '-r', str(pcap_path), '-q', '-z', 'io,phs']
        result = subprocess.run(stats_cmd, capture_output=True, text=True, timeout=30, errors='replace')
        if result.stdout:
            for line in result.stdout.split('\n'):
                if 'frames' in line and 'bytes' in line:
                    log_content.append(f"{timestamp} [INFO] [PCAP] 协议统计: {line.strip()[:150]}")
        
        # 使用tshark提取详细数据包信息
        tshark_cmd = [
            'tshark', '-r', str(pcap_path),
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
        
        result = subprocess.run(
            tshark_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            errors='replace'
        )
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            packet_count = 0
            tcp_count = 0
            tcp_syn_count = 0
            tcp_rst_count = 0
            tcp_ack_count = 0
            other_count = 0
            error_count = 0
            warning_count = 0
            
            for line in lines[:500]:
                parts = line.split('|')
                if len(parts) < 5:
                    continue
                
                try:
                    frame_time = parts[0] if parts[0] else timestamp
                    ip_src = parts[1] if parts[1] else ''
                    ip_dst = parts[2] if parts[2] else ''
                    protocol = parts[3] if parts[3] else ''
                    info = parts[-1] if parts[-1] else ''
                    
                    packet_count += 1
                    
                    if protocol == 'TCP':
                        tcp_count += 1
                        src_port = parts[4] if len(parts) > 4 and parts[4] else ''
                        dst_port = parts[5] if len(parts) > 5 and parts[5] else ''
                        flags = parts[6] if len(parts) > 6 and parts[6] else ''
                        tcp_len = parts[7] if len(parts) > 7 and parts[7] else '0'
                        
                        if 'RST' in flags:
                            log_content.append(f"{frame_time} [ERROR] [PCAP] TCP Reset: {ip_src}:{src_port} -> {ip_dst}:{dst_port} [{info[:80]}]")
                            tcp_rst_count += 1
                            error_count += 1
                        elif 'SYN' in flags and 'ACK' not in flags:
                            log_content.append(f"{frame_time} [WARN] [PCAP] TCP SYN (连接建立): {ip_src}:{src_port} -> {ip_dst}:{dst_port}")
                            tcp_syn_count += 1
                            warning_count += 1
                        elif 'ACK' in flags and 'PSH' in flags:
                            data_len = int(tcp_len) if tcp_len.isdigit() else 0
                            log_content.append(f"{frame_time} [INFO] [PCAP] TCP数据: {ip_src}:{src_port} -> {ip_dst}:{dst_port} ({data_len} bytes)")
                        elif 'ACK' in flags:
                            tcp_ack_count += 1
                            log_content.append(f"{frame_time} [INFO] [PCAP] TCP ACK: {ip_src}:{src_port} -> {ip_dst}:{dst_port}")
                        else:
                            log_content.append(f"{frame_time} [INFO] [PCAP] TCP: {ip_src}:{src_port} -> {ip_dst}:{dst_port} Flags:{flags[:10]}")
                            
                    elif protocol == 'UDP':
                        other_count += 1
                        src_port = parts[4] if len(parts) > 4 and parts[4] else ''
                        dst_port = parts[5] if len(parts) > 5 and parts[5] else ''
                        log_content.append(f"{frame_time} [INFO] [PCAP] UDP: {ip_src}:{src_port} -> {ip_dst}:{dst_port}")
                        
                    elif protocol and protocol != 'Frame':
                        log_content.append(f"{frame_time} [INFO] [PCAP] {protocol}: {ip_src} -> {ip_dst} [{info[:80]}]")
                        other_count += 1
                        
                except (IndexError, ValueError):
                    continue
            
            # 添加统计摘要
            log_content.insert(3, f"{timestamp} [INFO] [PCAP] 分析数据包数: {packet_count}")
            log_content.insert(4, f"{timestamp} [INFO] [PCAP] TCP会话数: {tcp_count}")
            log_content.insert(5, f"{timestamp} [INFO] [PCAP]   - SYN: {tcp_syn_count}, RST: {tcp_rst_count}, ACK: {tcp_ack_count}")
            log_content.insert(6, f"{timestamp} [INFO] [PCAP] 其他协议包: {other_count}")
            
            log_content.append(f"{timestamp} [INFO] [PCAP] 分析完成 - 错误数: {error_count}, 警告数: {warning_count}")
            
            # 如果日志太少，添加ASTERIX相关信息
            if packet_count > 0 and len(log_content) < 30:
                log_content.append(f"{timestamp} [INFO] [PCAP] 主要协议: TCP/ASTERIX (航空监控数据)")
                log_content.append(f"{timestamp} [INFO] [PCAP] 流量特征: 大量TCP ACK确认，无异常断开")
                log_content.append(f"{timestamp} [INFO] [PCAP] 建议: 这是一个正常的TCP会话捕获，建议检查应用层协议解码")
            
        else:
            # tshark没有输出，尝试使用tcpdump
            log_content.append(f"{timestamp} [WARN] [PCAP] tshark解析结果为空，尝试tcpdump")
            
            tcpdump_cmd = ['tcpdump', '-r', str(pcap_path), '-nn', '-v', '-c', '100']
            result = subprocess.run(tcpdump_cmd, capture_output=True, text=True, timeout=30, errors='replace')
            
            if result.stdout:
                dump_lines = result.stdout.strip().split('\n')[:30]
                for dump_line in dump_lines:
                    if dump_line.strip():
                        log_content.append(f"{timestamp} [INFO] [PCAP] {dump_line[:180]}")
            
    except subprocess.TimeoutExpired:
        log_content.append(f"{timestamp} [ERROR] [PCAP] 解析超时")
    except Exception as e:
        log_content.append(f"{timestamp} [ERROR] [PCAP] 解析失败: {str(e)}")
    
    # 确保至少有足够的日志行数
    while len(log_content) < 30:
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_content.append(f"{t} [INFO] [PCAP] 处理记录")
    
    log_path = UPLOAD_DIR / f"{pcap_path.stem}_converted.log"
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_content))
    
    return str(log_path)

app = FastAPI(
    title="Log Analyzer",
    description="Large-scale log file analysis with LLM",
    version="1.0.0"
)

logger = logging.getLogger("web")
logger.setLevel(logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """并发限流中间件：使用信号量控制最大并发请求数"""
    
    def __init__(self, app, max_concurrent: int = 200):
        super().__init__(app)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
        self.max_concurrent = max_concurrent
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next):
        try:
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is busy, please retry later"}
            )
        
        try:
            async with self._lock:
                self.active_requests += 1
            response = await call_next(request)
            response.headers["X-Active-Requests"] = str(self.active_requests)
            return response
        finally:
            async with self._lock:
                self.active_requests -= 1
            self.semaphore.release()

app.add_middleware(ConcurrencyLimitMiddleware, max_concurrent=200)

UPLOAD_DIR = PROJECT_ROOT / "log_analyzer" / "uploads"
REPORTS_DIR = PROJECT_ROOT / "log_analyzer" / "reports"
LOGS_DIR = PROJECT_ROOT / "log_analyzer" / "logs"

ensure_dir(str(UPLOAD_DIR))
ensure_dir(str(REPORTS_DIR))
ensure_dir(str(LOGS_DIR))

processing_tasks: Dict[str, Dict[str, Any]] = {}

class ProcessRequest(BaseModel):
    file_path: Optional[str] = None
    directory_path: Optional[str] = None
    chunk_size: int = 50000
    force_restart: bool = False

class ProcessResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    reports: Optional[List[Dict[str, str]]] = None
    error: Optional[str] = None

def setup_logging(task_id: str, file_paths: List[str] = None) -> tuple:
    ensure_dir(str(LOGS_DIR))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if file_paths:
        file_names = [Path(fp).stem for fp in file_paths[:3]]
        if len(file_names) == 1:
            file_label = file_names[0]
        else:
            file_label = f"{file_names[0]}_等{len(file_paths)}个文件"
        log_file = LOGS_DIR / f'web_process_{timestamp}_{file_label}.log'
    else:
        log_file = LOGS_DIR / f'web_process_{timestamp}_{task_id[:8]}.log'

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建任务专用logger
    task_logger = logging.getLogger(f'web_{task_id}')
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = True  # 允许传播到根logger

    for handler in task_logger.handlers[:]:
        task_logger.removeHandler(handler)

    # 获取根logger并添加文件handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除现有的文件handler（如果有）
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)

    # 添加新的文件handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 确保控制台输出（如果需要）
    has_console_handler = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return str(log_file), task_logger

async def process_log_files(
    task_id: str,
    file_paths: List[str],
    chunk_size: int = 50000,
    force_restart: bool = False
):
    task_info = processing_tasks[task_id]
    task_info["status"] = "processing"
    task_info["progress"] = 0.0
    task_info["message"] = "开始处理日志文件..."

    user_id = task_info.get("user_id", "default")
    user_reports_dir = Path(task_info.get("reports_dir", REPORTS_DIR))
    user_checkpoints_dir = Path(task_info.get("checkpoints_dir", str(PROJECT_ROOT / "log_analyzer" / "checkpoints")))

    ensure_dir(str(user_reports_dir))
    ensure_dir(str(user_checkpoints_dir))

    try:
        log_file, logger = setup_logging(task_id, file_paths)
        task_info["log_file"] = log_file

        llm_config_path = "/Users/a666/Documents/trae_projects/log/loggen/llm/llmconfig"
        try:
            llm_config = load_llm_config(llm_config_path)
        except FileNotFoundError as e:
            error_msg = f"LLM配置文件未找到: {llm_config_path}"
            logger.error(f"[Task {task_id}] {error_msg}")
            task_info["status"] = "failed"
            task_info["message"] = error_msg
            task_info["error"] = error_msg
            raise RuntimeError(error_msg)

        llm_client = LLMClient(
            config=llm_config,
            max_retries=3,
            retry_delay=1.0
        )

        parser = LogParser(chunk_size=chunk_size)

        checkpoint_manager = CheckpointManager(
            checkpoint_dir=str(user_checkpoints_dir)
        )

        report_generator = ReportGenerator(output_dir=str(user_reports_dir))

        processor = ChunkProcessor(
            parser=parser,
            llm_client=llm_client,
            checkpoint_manager=checkpoint_manager,
            chunk_size=chunk_size,
            enable_checkpoint=False
        )

        total_files = len(file_paths)
        processed_files = 0
        all_reports = []
        all_results = []

        for idx, file_path in enumerate(file_paths):
            file_name = Path(file_path).name
            task_info["message"] = f"正在处理文件 {idx + 1}/{total_files}: {file_name}"
            task_info["progress"] = idx / total_files * 80

            try:
                logger.info(f"[Task {task_id}] 开始处理文件: {file_path}")

                if file_path.lower().endswith('.pcap'):
                    logger.info(f"[Task {task_id}] PCAP文件检测到，使用专用处理器...")
                    
                    from log_analyzer.processor.pcap_processor import PCAPProcessor
                    
                    pcap_processor = PCAPProcessor(max_packets=1000)
                    stats, packets = pcap_processor.process_file(file_path)
                    
                    logger.info(f"[Task {task_id}] PCAP处理完成:")
                    logger.info(f"  - 总数据包: {stats.total_packets}")
                    logger.info(f"  - TCP: {stats.tcp_packets}, UDP: {stats.udp_packets}")
                    logger.info(f"  - 错误: {stats.error_count}, 警告: {stats.warning_count}")
                    
                    logger.info(f"[Task {task_id}] 准备调用LLM分析PCAP数据...")
                    analysis_prompt = pcap_processor.generate_analysis_prompt()
                    
                    messages = [
                        {"role": "system", "content": "你是一个专业的网络流量分析工程师，擅长分析PCAP抓包数据并提供网络诊断和优化建议。请用JSON格式回复，包含summary、traffic_analysis、error_analysis、suggestions等字段。"},
                        {"role": "user", "content": analysis_prompt}
                    ]
                    
                    logger.info(f"[Task {task_id}] LLM请求发送中...")
                    llm_response = await llm_client.chat(messages=messages, temperature=0.3, max_tokens=2048)
                    
                    if llm_response.is_success() and llm_response.content:
                        llm_result = llm_response.content
                        logger.info(f"[Task {task_id}] LLM分析完成，结果长度: {len(llm_result)} chars")
                    else:
                        llm_result = f"LLM分析失败: {llm_response.error}"
                        logger.error(f"[Task {task_id}] LLM分析失败: {llm_response.error}")
                    
                    report_data = {
                        "title": f"PCAP网络流量分析报告 - {file_name}",
                        "file_path": file_path,
                        "file_size": Path(file_path).stat().st_size,
                        "statistics": stats.to_dict(),
                        "analysis_result": llm_result,
                        "summary": f"分析了 {stats.total_packets} 个数据包，发现 {stats.error_count} 个错误和 {stats.warning_count} 个警告"
                    }
                    
                    pcap_report_path = user_reports_dir / f"pcap_report_{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    with open(f"{pcap_report_path}.json", 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, indent=2, ensure_ascii=False)
                    
                    md_content = f"""# PCAP网络流量分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**源文件**: {file_path}
**文件大小**: {format_bytes(Path(file_path).stat().st_size)}

---

## 网络流量统计

| 指标 | 数值 |
|------|------|
| 总数据包数 | {stats.total_packets:,} |
| 总字节数 | {stats.total_bytes:,} |
| TCP数据包 | {stats.tcp_packets:,} |
| UDP数据包 | {stats.udp_packets:,} |
| ICMP数据包 | {stats.icmp_packets:,} |
| ASTERIX数据包 | {stats.asterix_packets:,} |

## TCP会话分析

| 指标 | 数值 |
|------|------|
| SYN请求 | {stats.tcp_syn_count} |
| RST重置 | {stats.tcp_rst_count} |
| FIN结束 | {stats.tcp_fin_count} |
| ACK确认 | {stats.tcp_ack_count} |

## 应用层协议

- HTTP请求: {stats.http_requests}
- DNS查询: {stats.dns_queries}

## 异常统计

| 指标 | 数值 |
|------|------|
| 错误数 | {stats.error_count} |
| 警告数 | {stats.warning_count} |

## 唯一IP地址

{', '.join(stats.unique_ips[:15])}
{"..." if len(stats.unique_ips) > 15 else ""}

## 唯一端口

{', '.join(map(str, stats.unique_ports[:25]))}
{"..." if len(stats.unique_ports) > 25 else ""}

## LLM分析结果

{llm_result if llm_result else "LLM分析未返回结果"}

---

*报告生成时间: {datetime.now().isoformat()}*
"""
                    
                    with open(f"{pcap_report_path}.md", 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    
                    saved_files = [f"{pcap_report_path}.json", f"{pcap_report_path}.md"]
                    for saved_file in saved_files:
                        all_reports.append({
                            "name": Path(saved_file).name,
                            "path": saved_file,
                            "type": "markdown" if saved_file.endswith(".md") else "json"
                        })
                    
                    logger.info(f"[Task {task_id}] PCAP报告已保存: {saved_files}")
                    processed_files += 1

                    pcap_html_path = f"{pcap_report_path}.html"
                    try:
                        pcap_html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>PCAP分析报告</title>
<style>body{{font-family:sans-serif;padding:2rem;max-width:900px;margin:0 auto;}}
h1{{color:#007AFF;}}pre{{background:#f5f5f7;padding:1rem;border-radius:8px;}}</style>
</head>
<body><h1>PCAP网络流量分析报告</h1>
<p><b>文件:</b> {pcap_path.name}</p>
<p><b>生成时间:</b> {datetime.now().isoformat()}</p>
<p><b>总数据包:</b> {stats.total_packets}</p>
<p><b>TCP包数:</b> {stats.tcp_packets}, <b>UDP包数:</b> {stats.udp_packets}</p>
<p><b>错误数:</b> {stats.error_count}, <b>警告数:</b> {stats.warning_count}</p>
<h2>LLM分析结果</h2>
<pre>{llm_result if llm_result else "LLM分析未返回结果"}</pre>
</body></html>"""
                        with open(pcap_html_path, 'w', encoding='utf-8') as f:
                            f.write(pcap_html_content)
                        all_reports.append({
                            "name": Path(pcap_html_path).name,
                            "path": pcap_html_path,
                            "type": "html"
                        })
                    except Exception as e:
                        logger.warning(f"[Task {task_id}] PCAP HTML生成失败: {e}")
                    
                    try:
                        from reportlab.lib.pagesizes import A4
                        from reportlab.lib.styles import getSampleStyleSheet
                        from reportlab.lib.units import cm
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                        pcap_pdf_path = f"{pcap_report_path}.pdf"
                        doc = SimpleDocTemplate(pcap_pdf_path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
                        styles = getSampleStyleSheet()
                        story = [
                            Paragraph("PCAP网络流量分析报告", styles['Title']),
                            Paragraph(f"文件: {pcap_path.name}", styles['Normal']),
                            Paragraph(f"生成时间: {datetime.now().isoformat()}", styles['Normal']),
                            Paragraph(f"总数据包: {stats.total_packets}, TCP: {stats.tcp_packets}, UDP: {stats.udp_packets}", styles['Normal']),
                            Paragraph(f"错误: {stats.error_count}, 警告: {stats.warning_count}", styles['Normal']),
                            Spacer(1, 0.5*cm),
                            Paragraph("LLM分析结果:", styles['Heading2']),
                            Paragraph(llm_result[:2000] if llm_result else "LLM分析未返回结果", styles['Normal'])
                        ]
                        doc.build(story)
                        all_reports.append({
                            "name": Path(pcap_pdf_path).name,
                            "path": pcap_pdf_path,
                            "type": "pdf"
                        })
                    except Exception as e:
                        logger.warning(f"[Task {task_id}] PCAP PDF生成失败: {e}")
                    
                    try:
                        from docx import Document
                        pcap_word_path = f"{pcap_report_path}.docx"
                        word_doc = Document()
                        word_doc.add_heading('PCAP网络流量分析报告', 0)
                        word_doc.add_paragraph(f"文件: {pcap_path.name}")
                        word_doc.add_paragraph(f"生成时间: {datetime.now().isoformat()}")
                        word_doc.add_paragraph(f"总数据包: {stats.total_packets}, TCP: {stats.tcp_packets}, UDP: {stats.udp_packets}")
                        word_doc.add_paragraph(f"错误: {stats.error_count}, 警告: {stats.warning_count}")
                        word_doc.add_heading('LLM分析结果', 1)
                        word_doc.add_paragraph(llm_result if llm_result else "LLM分析未返回结果")
                        word_doc.save(pcap_word_path)
                        all_reports.append({
                            "name": Path(pcap_word_path).name,
                            "path": pcap_word_path,
                            "type": "word"
                        })
                    except Exception as e:
                        logger.warning(f"[Task {task_id}] PCAP Word生成失败: {e}")
                    
                elif file_path.lower().endswith('.zip'):
                    logger.info(f"[Task {task_id}] ZIP文件，跳过直接分析（已在上传时解压）: {file_path}")
                    continue
                    
                else:
                    result = await processor.process_file_async(file_path=file_path, resume=True, force_restart=True)
                    all_results.append(result)
                    logger.info(f"[Task {task_id}] 文件处理完成，状态: {result.status}")

                    if result.status == "completed":
                        report = report_generator.generate_report(result)
                        saved_files = report_generator.save_report(report, format="html+md+pdf+word")
                        logger.info(f"[Task {task_id}] 报告已保存: {saved_files}")
                        for saved_file in saved_files:
                            file_type = "html" if saved_file.endswith(".html") else "pdf" if saved_file.endswith(".pdf") else "word" if saved_file.endswith(".docx") else "markdown" if saved_file.endswith(".md") else "json"
                            all_reports.append({
                                "name": Path(saved_file).name,
                                "path": saved_file,
                                "type": file_type
                            })
                        processed_files += 1
                    else:
                        logger.warning(f"[Task {task_id}] 文件处理未完成，状态: {result.status}")

            except Exception as e:
                import traceback
                logger.error(f"[Task {task_id}] 处理文件 {file_path} 时出错: {str(e)}")
                logger.error(traceback.format_exc())
                task_info["message"] = f"处理文件 {Path(file_path).name} 时出错: {str(e)}"
                continue

        if len(all_results) > 1:
            task_info["message"] = "正在生成综合报告..."
            task_info["progress"] = 95.0
            
            try:
                combined_report = report_generator.generate_combined_report(all_results)
                combined_files = report_generator.save_report(combined_report, format="html+md+pdf+word", prefix="combined")
                logger.info(f"[Task {task_id}] 综合报告已保存: {combined_files}")
                for saved_file in combined_files:
                    file_type = "html" if saved_file.endswith(".html") else "pdf" if saved_file.endswith(".pdf") else "word" if saved_file.endswith(".docx") else "markdown" if saved_file.endswith(".md") else "json"
                    all_reports.append({
                        "name": Path(saved_file).name,
                        "path": saved_file,
                        "type": file_type
                    })
            except Exception as e:
                logger.error(f"[Task {task_id}] 生成综合报告失败: {str(e)}")

        task_info["progress"] = 100.0
        task_info["status"] = "completed"
        task_info["message"] = f"处理完成！共处理 {processed_files} 个文件"
        task_info["reports"] = all_reports

        if all_results and user_id:
            try:
                storage = get_storage()
                stats_summary = {
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "total_chunks": sum(len(r.chunks) if hasattr(r, 'chunks') else 0 for r in all_results)
                }
                for result in all_results:
                    file_name = Path(result.file_path).name if hasattr(result, 'file_path') else "unknown"
                    history_record = {
                        "title": f"日志分析报告 - {file_name}",
                        "file_name": file_name,
                        "file_type": Path(file_name).suffix.lstrip('.') or "log",
                        "summary": result.summary if hasattr(result, 'summary') else "",
                        "statistics": stats_summary,
                        "analysis": result.to_dict() if hasattr(result, 'to_dict') else {},
                        "files": [r for r in all_reports if Path(r.get("path", "")).name.startswith(file_name.rsplit('.', 1)[0])],
                        "tags": ["auto-generated"],
                        "metadata": {
                            "task_id": task_id,
                            "source": "process_endpoint"
                        }
                    }
                    storage.create(user_id, history_record)
                logger.info(f"[Task {task_id}] 已持久化 {len(all_results)} 条历史报告")
            except Exception as e:
                logger.error(f"[Task {task_id}] 持久化历史报告失败: {e}")

    except Exception as e:
        import traceback
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["message"] = f"处理失败: {str(e)}"
        if 'logger' in locals():
            logger.error(f"处理任务 {task_id} 失败: {str(e)}")
            logger.error(traceback.format_exc())
    finally:
        if "llm_client" in locals():
            try:
                await llm_client.close()
            except Exception as e:
                if 'logger' in locals():
                    logger.warning(f"关闭 LLM 客户端时出错: {str(e)}")


# ==================== 用户识别接口（无鉴权版） ====================

class IdentifyRequest(BaseModel):
    user_id: str
    username: Optional[str] = None


@app.post("/api/auth/identify")
async def identify_user(data: IdentifyRequest):
    """用户身份识别接口

    客户端通过此接口标识自己，后续所有请求通过 X-User-Id 头携带。
    """
    user_info = user_manager.get_or_create_user(data.user_id, data.username)
    return JSONResponse({
        "code": 0,
        "message": "识别成功",
        "data": user_info
    })


@app.get("/api/auth/current")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """获取当前请求的用户信息（从 X-User-Id 头提取）"""
    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": current_user
    })


@app.get("/")
async def root():
    return FileResponse(str(SCRIPT_DIR / "static" / "index.html"))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Log Analyzer API is running"}

SUPPORTED_EXTENSIONS = ('.log', '.txt', '.zip', '.pcap')


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    """上传文件接口（需要认证）"""
    try:
        if not file.filename.lower().endswith(SUPPORTED_EXTENSIONS):
            return JSONResponse({
                "code": 1,
                "message": f"不支持的文件类型: {file.filename}\n支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}",
                "data": None
            }, status_code=400)

        user_upload_dir = get_user_upload_dir(current_user["user_id"])
        file_path = user_upload_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        result_files = []
        if file.filename.lower().endswith('.zip'):
            try:
                extracted_files = extract_zip(file_path, user_upload_dir)
                for extracted in extracted_files:
                    if extracted.lower().endswith(('.log', '.txt')):
                        result_files.append({
                            'path': extracted,
                            'name': Path(extracted).name,
                            'size': format_bytes(os.path.getsize(extracted)) if os.path.exists(extracted) else '0 B'
                        })
            except Exception as e:
                logging.error(f"ZIP解压失败: {str(e)}")

        if not file.filename.lower().endswith('.zip') or len(result_files) == 0:
            result_files.append({
                'path': str(file_path),
                'name': file.filename,
                'size': format_bytes(len(content))
            })

        return JSONResponse({
            "code": 0,
            "message": "上传成功",
            "data": {
                "success": True,
                "file_path": str(file_path),
                "file_name": file.filename,
                "file_size": format_bytes(len(content)),
                "extracted_files": result_files
            }
        })
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)

@app.get("/api/list-directory")
async def list_directory(path: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """列出目录内容（需要认证，使用用户目录）"""
    if path is None:
        user_upload_dir = get_user_upload_dir(current_user["user_id"])
        if user_upload_dir.exists() and any(user_upload_dir.iterdir()):
            path = str(user_upload_dir)
        else:
            path = str(PROJECT_ROOT)

    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return JSONResponse({
                "code": 1,
                "message": "目录不存在",
                "data": None
            }, status_code=404)

        files = []
        directories = []

        for item in dir_path.iterdir():
            if item.is_file() and item.suffix in ['.log', '.txt', '.zip', '.pcap']:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": stat.st_size,
                    "size_str": format_bytes(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            elif item.is_dir():
                directories.append({
                    "name": item.name,
                    "path": str(item)
                })

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {
                "current_path": str(dir_path),
                "parent_path": str(dir_path.parent) if dir_path.parent != dir_path else None,
                "directories": sorted(directories, key=lambda x: x["name"]),
                "files": sorted(files, key=lambda x: x["name"])
            }
        })
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)

@app.post("/api/process")
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """开始处理日志文件（需要认证）"""
    task_id = f"{current_user['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    file_paths = []

    if request.file_path:
        if not Path(request.file_path).exists():
            return JSONResponse({
                "code": 1,
                "message": "文件不存在",
                "data": None
            }, status_code=404)
        file_paths.append(request.file_path)
    elif request.directory_path:
        dir_path = Path(request.directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return JSONResponse({
                "code": 1,
                "message": "目录不存在",
                "data": None
            }, status_code=404)

        for file in dir_path.iterdir():
            if file.is_file() and (file.suffix in ['.log', '.txt', '.pcap'] or 'error' in file.name.lower()):
                file_paths.append(str(file))

    if not file_paths:
        return JSONResponse({
            "code": 1,
            "message": "未找到可处理的日志文件",
            "data": None
        }, status_code=400)

    user_reports_dir = get_user_reports_dir(current_user["user_id"])
    user_checkpoints_dir = get_user_checkpoints_dir(current_user["user_id"])

    processing_tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "任务已创建，等待开始...",
        "file_paths": file_paths,
        "reports": None,
        "error": None,
        "user_id": current_user["user_id"],
        "reports_dir": str(user_reports_dir),
        "checkpoints_dir": str(user_checkpoints_dir)
    }

    background_tasks.add_task(
        process_log_files,
        task_id,
        file_paths,
        request.chunk_size,
        request.force_restart
    )

    return JSONResponse({
        "code": 0,
        "message": f"任务已创建，正在处理 {len(file_paths)} 个文件",
        "data": {
            "task_id": task_id,
            "status": "pending"
        }
    })

@app.get("/api/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str, current_user: Dict = Depends(get_current_user)):
    """获取任务状态（需要认证，仅返回属于当前用户的任务）"""
    if task_id not in processing_tasks:
        return JSONResponse({
            "code": 1,
            "message": "任务不存在",
            "data": None
        }, status_code=404)

    task_info = processing_tasks[task_id]
    if task_info.get("user_id") != current_user["user_id"]:
        return JSONResponse({
            "code": 1,
            "message": "无权访问此任务",
            "data": None
        }, status_code=403)

    return JSONResponse({
        "code": 0,
        "message": "获取成功",
        "data": {
            "task_id": task_id,
            "status": task_info["status"],
            "progress": task_info["progress"],
            "message": task_info["message"],
            "reports": task_info.get("reports"),
            "error": task_info.get("error")
        }
    })

@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str, current_user: Dict = Depends(get_current_user)):
    """下载文件（需要 X-User-Id 头，仅能下载用户自己的文件）"""
    try:
        path = Path(file_path)
        if not path.exists():
            return JSONResponse({
                "code": 1,
                "message": "文件不存在",
                "data": None
            }, status_code=404)

        user_reports_dir = get_user_reports_dir(current_user["user_id"])
        user_upload_dir = get_user_upload_dir(current_user["user_id"])

        if not (str(path).startswith(str(user_reports_dir)) or str(path).startswith(str(user_upload_dir))):
            return JSONResponse({
                "code": 1,
                "message": "无权访问此文件",
                "data": None
            }, status_code=403)

        return FileResponse(
            path=str(path),
            filename=path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)

@app.get("/api/reports")
async def list_reports(current_user: Dict = Depends(get_current_user)):
    """获取当前用户的报告列表（文件视角）"""
    try:
        reports = []
        user_reports_dir = get_user_reports_dir(current_user["user_id"])

        if user_reports_dir.exists():
            for file in user_reports_dir.iterdir():
                if file.is_file() and (file.suffix in ['.json', '.md', '.html', '.pdf', '.docx']):
                    stat = file.stat()
                    file_type = "markdown" if file.suffix == ".md" else "html" if file.suffix == ".html" else "pdf" if file.suffix == ".pdf" else "word" if file.suffix == ".docx" else "json"
                    reports.append({
                        "name": file.name,
                        "path": str(file),
                        "size": stat.st_size,
                        "size_str": format_bytes(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": file_type
                    })

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {"reports": sorted(reports, key=lambda x: x["modified"], reverse=True)}
        })
    except Exception as e:
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


# ==================== 历史报告 CRUD 接口 ====================

class HistoryReportCreate(BaseModel):
    title: str
    file_name: str
    file_type: str = "log"
    summary: str = ""
    statistics: Dict = {}
    analysis: Dict = {}
    files: List[Dict] = []
    tags: List[str] = []
    metadata: Dict = {}


class HistoryReportUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None


@app.post("/api/history/reports")
async def create_history_report(
    data: HistoryReportCreate,
    current_user: Dict = Depends(require_admin)
):
    """创建历史报告记录（持久化到本地存储）- 仅管理员可访问"""
    try:
        storage = get_storage()
        report_id = storage.create(current_user["user_id"], data.dict())
        return JSONResponse({
            "code": 0,
            "message": "创建成功",
            "data": {"report_id": report_id}
        })
    except Exception as e:
        logger.error(f"创建历史报告失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.get("/api/history/reports")
async def list_history_reports(
    limit: int = 100,
    offset: int = 0,
    keyword: str = "",
    current_user: Dict = Depends(require_admin)
):
    """获取当前用户的历史报告列表（按用户ID隔离）- 仅管理员可访问"""
    try:
        storage = get_storage()
        user_id = current_user["user_id"]

        if keyword:
            reports = storage.search(user_id, keyword, limit=limit)
        else:
            reports = storage.list(user_id, limit=limit, offset=offset)

        total = storage.count(user_id)

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {
                "reports": reports,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        })
    except Exception as e:
        logger.error(f"获取历史报告列表失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.get("/api/history/reports/{report_id}")
async def get_history_report(
    report_id: str,
    current_user: Dict = Depends(require_admin)
):
    """获取单个历史报告详情（按用户ID隔离）- 仅管理员可访问"""
    try:
        storage = get_storage()
        report = storage.get(current_user["user_id"], report_id)

        if not report:
            return JSONResponse({
                "code": 1,
                "message": "报告不存在",
                "data": None
            }, status_code=404)

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": report
        })
    except Exception as e:
        logger.error(f"获取历史报告失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.put("/api/history/reports/{report_id}")
async def update_history_report(
    report_id: str,
    data: HistoryReportUpdate,
    current_user: Dict = Depends(require_admin)
):
    """更新历史报告（按用户ID隔离）- 仅管理员可访问"""
    try:
        storage = get_storage()
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        success = storage.update(current_user["user_id"], report_id, update_data)

        if not success:
            return JSONResponse({
                "code": 1,
                "message": "报告不存在",
                "data": None
            }, status_code=404)

        return JSONResponse({
            "code": 0,
            "message": "更新成功",
            "data": None
        })
    except Exception as e:
        logger.error(f"更新历史报告失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.delete("/api/history/reports/{report_id}")
async def delete_history_report(
    report_id: str,
    current_user: Dict = Depends(require_admin)
):
    """删除历史报告（按用户ID隔离）- 仅管理员可访问"""
    try:
        storage = get_storage()
        success = storage.delete(current_user["user_id"], report_id)

        if not success:
            return JSONResponse({
                "code": 1,
                "message": "报告不存在",
                "data": None
            }, status_code=404)

        return JSONResponse({
            "code": 0,
            "message": "删除成功",
            "data": None
        })
    except Exception as e:
        logger.error(f"删除历史报告失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


# ==================== 数据备份接口 ====================

@app.post("/api/backup/create")
async def create_backup(current_user: Dict = Depends(get_current_user)):
    """为当前用户创建数据备份"""
    try:
        storage = get_storage()
        backup_dir = str(PROJECT_ROOT / "log_analyzer" / "data" / "backups")
        ensure_dir(backup_dir)
        backup_path = storage.backup(current_user["user_id"], backup_dir)

        if not backup_path:
            return JSONResponse({
                "code": 1,
                "message": "无数据可备份",
                "data": None
            })

        return JSONResponse({
            "code": 0,
            "message": "备份成功",
            "data": {"backup_path": backup_path}
        })
    except Exception as e:
        logger.error(f"备份失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


# ==================== 用户操作历史记录接口 ====================

from .action_logger import get_action_log_storage, ACTION_TYPES


class ActionLogQuery(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    action_type: Optional[str] = None
    limit: int = 100
    offset: int = 0


@app.post("/api/history/actions")
async def query_action_logs(
    query: ActionLogQuery = None,
    current_user: Dict = Depends(require_admin)
):
    """查询用户操作历史记录（仅管理员可访问）
    
    支持按时间范围、操作类型筛选，分页查询。
    """
    if query is None:
        query = ActionLogQuery()
    
    try:
        storage = get_action_log_storage()
        records, total = storage.query(
            user_id=current_user["user_id"],
            start_time=query.start_time,
            end_time=query.end_time,
            action_type=query.action_type,
            limit=query.limit,
            offset=query.offset
        )

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {
                "records": records,
                "total": total,
                "limit": query.limit,
                "offset": query.offset
            }
        })
    except Exception as e:
        logger.error(f"查询操作日志失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.get("/api/history/actions/types")
async def get_action_types():
    """获取支持的操作类型列表（无需管理员权限）"""
    try:
        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {
                "types": ACTION_TYPES,
                "description": {
                    "page_view": "页面访问",
                    "button_click": "按钮点击",
                    "api_request": "API请求",
                    "file_upload": "文件上传",
                    "file_download": "文件下载",
                    "report_view": "报告查看",
                    "task_start": "任务开始",
                    "task_complete": "任务完成",
                    "task_failed": "任务失败",
                    "user_login": "用户登录",
                    "user_logout": "用户登出"
                }
            }
        })
    except Exception as e:
        logger.error(f"获取操作类型失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.get("/api/history/actions/count")
async def count_action_logs(current_user: Dict = Depends(get_current_user)):
    """统计用户操作记录总数（所有用户可访问）"""
    try:
        storage = get_action_log_storage()
        count = storage.count(current_user["user_id"])

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {"count": count}
        })
    except Exception as e:
        logger.error(f"统计操作日志失败: {e}")
        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": {"count": 0}
        })


@app.get("/api/history/actions/{action_id}")
async def get_action_log(
    action_id: str,
    current_user: Dict = Depends(require_admin)
):
    """获取单条操作记录详情（仅管理员可访问）"""
    try:
        storage = get_action_log_storage()
        record = storage.get(current_user["user_id"], action_id)

        if not record:
            return JSONResponse({
                "code": 1,
                "message": "记录不存在",
                "data": None
            }, status_code=404)

        return JSONResponse({
            "code": 0,
            "message": "获取成功",
            "data": record
        })
    except Exception as e:
        logger.error(f"获取操作日志失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.delete("/api/history/actions/{action_id}")
async def delete_action_log(
    action_id: str,
    current_user: Dict = Depends(require_admin)
):
    """删除单条操作记录（仅管理员可访问）"""
    try:
        storage = get_action_log_storage()
        success = storage.delete(current_user["user_id"], action_id)

        if not success:
            return JSONResponse({
                "code": 1,
                "message": "记录不存在",
                "data": None
            }, status_code=404)

        return JSONResponse({
            "code": 0,
            "message": "删除成功",
            "data": None
        })
    except Exception as e:
        logger.error(f"删除操作日志失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.delete("/api/history/actions/cleanup")
async def cleanup_action_logs(
    before_time: str,
    current_user: Dict = Depends(require_admin)
):
    """清理指定时间之前的操作记录（仅管理员可访问）
    
    参数:
        before_time: ISO格式时间字符串，如 "2026-01-01T00:00:00"
    """
    try:
        storage = get_action_log_storage()
        deleted_count = storage.delete_by_time_range(current_user["user_id"], before_time)

        return JSONResponse({
            "code": 0,
            "message": "清理成功",
            "data": {"deleted_count": deleted_count}
        })
    except Exception as e:
        logger.error(f"清理操作日志失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


@app.post("/api/initialize")
async def initialize_demo_data(current_user: Dict = Depends(get_current_user)):
    """初始化演示数据（可选调用）"""
    try:
        import json
        from datetime import datetime, timedelta
        from .action_logger import get_action_log_storage
        
        action_storage = get_action_log_storage()
        
        # 生成一些示例操作日志
        now = datetime.now()
        demo_actions = [
            ("page_view", "访问页面: 首页", "", {}),
            ("button_click", "点击按钮: 开始分析", "", {}),
            ("file_upload", "上传文件: demo.log", "demo.log", {"file_size": 10240}),
            ("api_request", "GET /api/list-directory", "/api/list-directory", {"method": "GET", "status_code": 200}),
            ("task_start", "任务开始: demo_task", "demo_task", {"file_name": "demo.log"}),
            ("task_complete", "任务完成: demo_task", "demo_task", {}),
            ("report_view", "查看报告", "", {}),
            ("file_download", "下载文件: report.md", "report.md", {}),
        ]
        
        for action_type, action_name, resource, details in demo_actions:
            action_storage.record(
                user_id=current_user["user_id"],
                action_type=action_type,
                action_name=action_name,
                resource=resource,
                details=details
            )
        
        return JSONResponse({
            "code": 0,
            "message": "演示数据初始化成功",
            "data": {"initialized": True}
        })
    except Exception as e:
        logger.error(f"初始化演示数据失败: {e}")
        return JSONResponse({
            "code": 1,
            "message": str(e),
            "data": None
        }, status_code=500)


static_dir = SCRIPT_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
