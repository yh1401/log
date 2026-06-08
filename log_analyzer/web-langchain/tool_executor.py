"""
工具执行器 - 管理和执行LangChain工具，完整集成原有日志分析系统
"""
import os
import sys
import json
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_analyzer.config.settings import load_llm_config, get_settings
from log_analyzer.llm.client import LLMClient
from log_analyzer.parser.log_parser import LogParser
from log_analyzer.processor.chunk_processor import ChunkProcessor, ProcessingResult
from log_analyzer.report.generator import ReportGenerator
from log_analyzer.report.rule_based_analyzer import RuleBasedAnalyzer
from log_analyzer.checkpoint.manager import CheckpointManager, Checkpoint
from log_analyzer.utils.helpers import ensure_dir

logger = logging.getLogger("web-langchain.tool_executor")


class ToolExecutor:
    """工具执行器 - 完整集成原有日志分析系统"""
    
    def __init__(self, user_id: str = "hanmeimei"):
        self.user_id = user_id
        self.user_dir = PROJECT_ROOT / "log_analyzer" / "users" / user_id
        self.upload_dir = self.user_dir / "uploads"
        self.reports_dir = self.user_dir / "reports"
        self.checkpoints_dir = self.user_dir / "checkpoints"
        self.tasks_dir = PROJECT_ROOT / "log_analyzer" / "tasks"
        
        ensure_dir(str(self.user_dir))
        ensure_dir(str(self.upload_dir))
        ensure_dir(str(self.reports_dir))
        ensure_dir(str(self.checkpoints_dir))
        ensure_dir(str(self.tasks_dir))
        
        try:
            llm_config = load_llm_config()
            self.llm_client = LLMClient(config=llm_config)
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")
            self.llm_client = None
        
        self.log_parser = LogParser()
        self.checkpoint_manager = CheckpointManager(str(self.checkpoints_dir))
        
        self.tools = self._register_tools()
        self.active_tasks = {}
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """注册所有可用工具"""
        return {
            "search_logs": {
                "name": "search_logs",
                "description": "搜索日志文件中的内容，支持关键词、错误级别过滤",
                "parameters": {
                    "query": {"type": "string", "description": "搜索关键词", "required": False},
                    "file_path": {"type": "string", "description": "日志文件路径（用户上传目录中的文件）", "required": False},
                    "log_level": {"type": "string", "description": "日志级别：ERROR, WARN, INFO, DEBUG", "required": False},
                    "limit": {"type": "integer", "description": "返回结果数量限制，默认100", "required": False}
                },
                "handler": self._handle_search_logs
            },
            "analyze_errors": {
                "name": "analyze_errors",
                "description": "分析日志中的错误，进行智能识别、语义合并、根因推断",
                "parameters": {
                    "file_path": {"type": "string", "description": "日志文件路径", "required": True},
                    "mode": {"type": "string", "description": "分析模式：llm（智能模式）或 rule（规则模式）", "required": False},
                    "deep_analysis": {"type": "boolean", "description": "是否进行深度根因分析", "required": False}
                },
                "handler": self._handle_analyze_errors
            },
            "get_statistics": {
                "name": "get_statistics",
                "description": "获取日志统计信息，包括错误数、警告数、日志分布等",
                "parameters": {
                    "file_path": {"type": "string", "description": "日志文件路径，不指定则统计所有文件", "required": False}
                },
                "handler": self._handle_get_statistics
            },
            "generate_report": {
                "name": "generate_report",
                "description": "生成多格式分析报告（PDF、Word、Markdown、HTML）",
                "parameters": {
                    "file_path": {"type": "string", "description": "日志文件路径", "required": True},
                    "report_format": {"type": "string", "description": "报告格式：all, pdf, word, markdown, html", "required": False},
                    "mode": {"type": "string", "description": "分析模式：llm 或 rule", "required": False}
                },
                "handler": self._handle_generate_report
            },
            "list_uploaded_files": {
                "name": "list_uploaded_files",
                "description": "列出用户已上传的所有文件",
                "parameters": {},
                "handler": self._handle_list_uploaded_files
            },
            "list_reports": {
                "name": "list_reports",
                "description": "列出用户所有历史报告",
                "parameters": {},
                "handler": self._handle_list_reports
            },
            "list_server_directories": {
                "name": "list_server_directories",
                "description": "列出服务器上允许访问的目录结构",
                "parameters": {
                    "path": {"type": "string", "description": "要浏览的目录路径，不指定则从根目录开始", "required": False}
                },
                "handler": self._handle_list_server_directories
            },
            "analyze_from_server_path": {
                "name": "analyze_from_server_path",
                "description": "从服务器指定目录分析日志文件，支持多文件",
                "parameters": {
                    "path": {"type": "string", "description": "服务器目录路径", "required": True},
                    "file_pattern": {"type": "string", "description": "文件匹配模式，如*.log", "required": False},
                    "mode": {"type": "string", "description": "分析模式：llm 或 rule", "required": False}
                },
                "handler": self._handle_analyze_from_server_path
            },
            "get_task_status": {
                "name": "get_task_status",
                "description": "获取分析任务的执行状态",
                "parameters": {
                    "task_id": {"type": "string", "description": "任务ID", "required": True}
                },
                "handler": self._handle_get_task_status
            },
            "stop_task": {
                "name": "stop_task",
                "description": "终止正在执行的分析任务",
                "parameters": {
                    "task_id": {"type": "string", "description": "任务ID", "required": True}
                },
                "handler": self._handle_stop_task
            },
            "resume_task": {
                "name": "resume_task",
                "description": "从断点恢复执行分析任务",
                "parameters": {
                    "checkpoint_id": {"type": "string", "description": "检查点ID", "required": True}
                },
                "handler": self._handle_resume_task
            },
            "analyze_pcap": {
                "name": "analyze_pcap",
                "description": "分析PCAP网络抓包文件",
                "parameters": {
                    "file_path": {"type": "string", "description": "PCAP文件路径", "required": True}
                },
                "handler": self._handle_analyze_pcap
            },
            "analyze_nginx": {
                "name": "analyze_nginx",
                "description": "分析Nginx访问日志",
                "parameters": {
                    "file_path": {"type": "string", "description": "Nginx日志文件路径", "required": True}
                },
                "handler": self._handle_analyze_nginx
            }
        }
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定的工具"""
        logger.info("-" * 60)
        logger.info(f"🛠️  开始执行工具: {tool_name}")
        logger.info(f"📋 工具参数: {json.dumps(parameters, ensure_ascii=False, indent=2)}")
        logger.info(f"👤 用户ID: {self.user_id}")
        logger.info("-" * 60)
        
        if tool_name not in self.tools:
            error_msg = f"工具不存在: {tool_name}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        start_time = time.time()
        try:
            tool = self.tools[tool_name]
            handler = tool["handler"]
            
            logger.info(f"✅ 找到工具: {tool_name}, 开始执行处理函数...")
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                result = handler(**parameters)
            
            elapsed_time = time.time() - start_time
            
            if result.get("success"):
                logger.info(f"✅ 工具执行成功! 耗时: {elapsed_time:.2f}s")
                logger.info(f"📦 返回结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
            else:
                logger.warning(f"⚠️ 工具执行返回失败: {result.get('error', '未知错误')}")
            
            logger.info("-" * 60)
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 执行工具 {tool_name} 异常! 耗时: {elapsed_time:.2f}s, 错误: {e}", exc_info=True)
            logger.info("-" * 60)
            return {
                "success": False,
                "error": f"执行失败: {str(e)}"
            }
    
    def _handle_search_logs(self, query: str = "", file_path: str = "", log_level: str = "", limit: int = 100) -> Dict[str, Any]:
        """搜索日志"""
        try:
            if file_path:
                search_dir = self.upload_dir / file_path
            else:
                search_dir = self.upload_dir
            
            results = []
            if search_dir.is_file():
                files_to_search = [search_dir]
            elif search_dir.is_dir():
                files_to_search = list(search_dir.iterdir())
            else:
                return {"success": False, "error": "文件或目录不存在"}
            
            for log_file in files_to_search:
                if not log_file.is_file():
                    continue
                
                try:
                    parsed_logs = self.log_parser.parse_log(str(log_file))
                    
                    for log in parsed_logs:
                        if query and query.lower() not in str(log).lower():
                            continue
                        if log_level and log.get("level", "").upper() != log_level.upper():
                            continue
                        
                        results.append({
                            "file": log_file.name,
                            "log": log,
                            "timestamp": log.get("timestamp", "")
                        })
                        
                        if len(results) >= limit:
                            break
                    
                    if len(results) >= limit:
                        break
                except Exception as e:
                    logger.warning(f"解析文件 {log_file.name} 失败: {e}")
                    continue
            
            results.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "success": True,
                "total": len(results),
                "results": results[:limit]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_analyze_errors(self, file_path: str, mode: str = "llm", deep_analysis: bool = True) -> Dict[str, Any]:
        """分析错误"""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            if mode == "rule":
                analyzer = RuleBasedAnalyzer()
                analysis_result = analyzer.analyze(str(full_path))
            else:
                processor = ChunkProcessor(
                    llm_client=self.llm_client,
                    checkpoint_manager=self.checkpoint_manager
                )
                analysis_result = processor.process_file(str(full_path))
            
            return {
                "success": True,
                "file": file_path,
                "mode": mode,
                "analysis": analysis_result.to_dict() if hasattr(analysis_result, 'to_dict') else str(analysis_result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_get_statistics(self, file_path: str = "") -> Dict[str, Any]:
        """获取统计信息"""
        try:
            stats = {
                "total_files": 0,
                "total_logs": 0,
                "error_count": 0,
                "warn_count": 0,
                "info_count": 0,
                "debug_count": 0,
                "files": []
            }
            
            if file_path:
                target_files = [self.upload_dir / file_path]
            else:
                target_files = list(self.upload_dir.iterdir())
            
            for log_file in target_files:
                if not log_file.is_file():
                    continue
                
                try:
                    parsed_logs = self.log_parser.parse_log(str(log_file))
                    
                    file_stats = {
                        "filename": log_file.name,
                        "total": len(parsed_logs),
                        "error": 0,
                        "warn": 0,
                        "info": 0,
                        "debug": 0
                    }
                    
                    for log in parsed_logs:
                        level = log.get("level", "").upper()
                        if level == "ERROR":
                            file_stats["error"] += 1
                        elif level == "WARN" or level == "WARNING":
                            file_stats["warn"] += 1
                        elif level == "INFO":
                            file_stats["info"] += 1
                        elif level == "DEBUG":
                            file_stats["debug"] += 1
                    
                    stats["total_files"] += 1
                    stats["total_logs"] += file_stats["total"]
                    stats["error_count"] += file_stats["error"]
                    stats["warn_count"] += file_stats["warn"]
                    stats["info_count"] += file_stats["info"]
                    stats["debug_count"] += file_stats["debug"]
                    stats["files"].append(file_stats)
                except Exception as e:
                    logger.warning(f"统计文件 {log_file.name} 失败: {e}")
                    continue
            
            return {
                "success": True,
                "statistics": stats
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_generate_report(self, file_path: str, report_format: str = "all", mode: str = "llm") -> Dict[str, Any]:
        """生成报告"""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            processor = ChunkProcessor(
                llm_client=self.llm_client,
                checkpoint_manager=self.checkpoint_manager
            )
            result = processor.process_file(str(full_path))
            
            generator = ReportGenerator()
            report_files = {}
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"report_chat_{full_path.stem}_{timestamp}"
            
            if report_format == "all" or "markdown" in report_format:
                md_path = self.reports_dir / f"{base_name}.md"
                generator.generate_markdown(result, str(md_path))
                report_files["markdown"] = str(md_path.name)
            
            if report_format == "all" or "html" in report_format:
                html_path = self.reports_dir / f"{base_name}.html"
                generator.generate_html(result, str(html_path))
                report_files["html"] = str(html_path.name)
            
            if report_format == "all" or "pdf" in report_format:
                pdf_path = self.reports_dir / f"{base_name}.pdf"
                try:
                    generator.generate_pdf(result, str(pdf_path))
                    report_files["pdf"] = str(pdf_path.name)
                except Exception as e:
                    logger.warning(f"PDF生成失败: {e}")
            
            if report_format == "all" or "word" in report_format:
                docx_path = self.reports_dir / f"{base_name}.docx"
                try:
                    generator.generate_word(result, str(docx_path))
                    report_files["word"] = str(docx_path.name)
                except Exception as e:
                    logger.warning(f"Word生成失败: {e}")
            
            return {
                "success": True,
                "file": file_path,
                "mode": mode,
                "report_files": report_files
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_list_uploaded_files(self) -> Dict[str, Any]:
        """列出已上传文件"""
        try:
            files = []
            if self.upload_dir.exists():
                for f in self.upload_dir.iterdir():
                    if f.is_file():
                        stat = f.stat()
                        files.append({
                            "name": f.name,
                            "size": stat.st_size,
                            "size_formatted": self._format_bytes(stat.st_size),
                            "upload_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            
            files.sort(key=lambda x: x["upload_time"], reverse=True)
            
            return {
                "success": True,
                "files": files,
                "total": len(files)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_list_reports(self) -> Dict[str, Any]:
        """列出历史报告"""
        try:
            reports = []
            if self.reports_dir.exists():
                report_groups = {}
                for f in self.reports_dir.iterdir():
                    if f.is_file():
                        name = f.name
                        import re
                        match = re.search(r'_(\d{8}_\d{6})', name)
                        if match:
                            key = match.group(1)
                            if key not in report_groups:
                                report_groups[key] = {
                                    "timestamp": key,
                                    "datetime": datetime.strptime(key, "%Y%m%d_%H%M%S").isoformat(),
                                    "files": []
                                }
                            report_groups[key]["files"].append({
                                "name": name,
                                "type": f.suffix[1:],
                                "size": f.stat().st_size,
                                "size_formatted": self._format_bytes(f.stat().st_size)
                            })
                
                reports = list(report_groups.values())
                reports.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "success": True,
                "reports": reports,
                "total": len(reports)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_list_server_directories(self, path: str = "") -> Dict[str, Any]:
        """列出服务器目录"""
        try:
            if not path:
                settings = get_settings()
                allowed_dirs = settings.server_path.allowed_directories
                return {
                    "success": True,
                    "path": "/",
                    "is_root": True,
                    "directories": allowed_dirs if allowed_dirs else ["/"]
                }
            
            target_path = Path(path)
            if not self._is_path_allowed(target_path):
                return {"success": False, "error": "路径不在允许访问范围内"}
            
            if not target_path.exists() or not target_path.is_dir():
                return {"success": False, "error": "目录不存在"}
            
            contents = []
            for item in target_path.iterdir():
                try:
                    contents.append({
                        "name": item.name,
                        "path": str(item),
                        "is_directory": item.is_dir(),
                        "is_file": item.is_file(),
                        "size": item.stat().st_size if item.is_file() else 0,
                        "size_formatted": self._format_bytes(item.stat().st_size) if item.is_file() else ""
                    })
                except Exception:
                    continue
            
            contents.sort(key=lambda x: (not x["is_directory"], x["name"]))
            
            return {
                "success": True,
                "path": str(target_path),
                "parent": str(target_path.parent) if target_path.parent != target_path else None,
                "contents": contents
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_analyze_from_server_path(self, path: str, file_pattern: str = "*.log", mode: str = "llm") -> Dict[str, Any]:
        """从服务器路径分析"""
        try:
            target_path = Path(path)
            if not self._is_path_allowed(target_path):
                return {"success": False, "error": "路径不在允许访问范围内"}
            
            if not target_path.exists():
                return {"success": False, "error": "路径不存在"}
            
            log_files = []
            if target_path.is_file():
                log_files = [target_path]
            else:
                import glob
                pattern = str(target_path / file_pattern)
                log_files = [Path(f) for f in glob.glob(pattern)]
            
            if not log_files:
                return {"success": False, "error": "未找到匹配的日志文件"}
            
            processor = ChunkProcessor(
                llm_client=self.llm_client,
                checkpoint_manager=self.checkpoint_manager
            )
            
            results = []
            for log_file in log_files[:5]:
                try:
                    result = processor.process_file(str(log_file))
                    results.append({
                        "file": log_file.name,
                        "result": result.to_dict() if hasattr(result, 'to_dict') else str(result)
                    })
                except Exception as e:
                    logger.warning(f"处理文件 {log_file.name} 失败: {e}")
                    continue
            
            return {
                "success": True,
                "path": path,
                "total_files": len(log_files),
                "processed": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_analyze_pcap(self, file_path: str) -> Dict[str, Any]:
        """分析PCAP文件"""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            from log_analyzer.processor.pcap_processor import PcapProcessor
            processor = PcapProcessor()
            result = processor.analyze_pcap(str(full_path))
            
            return {
                "success": True,
                "file": file_path,
                "analysis": result.to_dict() if hasattr(result, 'to_dict') else str(result)
            }
        except ImportError:
            return {"success": False, "error": "PCAP分析功能未安装，请安装pcap相关依赖"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_analyze_nginx(self, file_path: str) -> Dict[str, Any]:
        """分析Nginx日志"""
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return {"success": False, "error": f"文件不存在: {file_path}"}
            
            from log_analyzer.parser.nginx_parser import NginxParser
            parser = NginxParser()
            logs = parser.parse(str(full_path))
            
            stats = {
                "total_requests": len(logs),
                "status_codes": {},
                "top_paths": [],
                "top_ips": []
            }
            
            path_count = {}
            ip_count = {}
            for log in logs:
                status = str(log.get("status", ""))
                stats["status_codes"][status] = stats["status_codes"].get(status, 0) + 1
                
                path = log.get("path", "")
                path_count[path] = path_count.get(path, 0) + 1
                
                ip = log.get("ip", "")
                ip_count[ip] = ip_count.get(ip, 0) + 1
            
            stats["top_paths"] = sorted(path_count.items(), key=lambda x: x[1], reverse=True)[:10]
            stats["top_ips"] = sorted(ip_count.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "success": True,
                "file": file_path,
                "statistics": stats,
                "sample_logs": logs[:20]
            }
        except ImportError:
            return {"success": False, "error": "Nginx分析功能未实现"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            task_file = self.tasks_dir / f"{task_id}.json"
            if not task_file.exists():
                return {"success": False, "error": "任务不存在"}
            
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            return {
                "success": True,
                "task": task_data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_stop_task(self, task_id: str) -> Dict[str, Any]:
        """停止任务"""
        try:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["stopped"] = True
            
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                task_data["status"] = "stopped"
                task_data["stopped_at"] = datetime.now().isoformat()
                
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "任务已停止",
                "task_id": task_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_resume_task(self, checkpoint_id: str) -> Dict[str, Any]:
        """恢复任务"""
        try:
            checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            if not checkpoint:
                return {"success": False, "error": "检查点不存在"}
            
            return {
                "success": True,
                "message": "任务恢复功能准备就绪",
                "checkpoint_id": checkpoint_id,
                "checkpoint_data": checkpoint.to_dict() if hasattr(checkpoint, 'to_dict') else checkpoint
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _is_path_allowed(self, path: Path) -> bool:
        """检查路径是否允许访问"""
        try:
            settings = get_settings()
            allowed_dirs = settings.server_path.allowed_directories
            
            if not allowed_dirs or len(allowed_dirs) == 0:
                return True
            
            abs_path = path.resolve()
            for allowed_dir in allowed_dirs:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    if abs_path.is_relative_to(allowed_path):
                        return True
                except Exception:
                    if str(abs_path).startswith(str(allowed_path)):
                        return True
            
            return False
        except Exception:
            return True
    
    def _format_bytes(self, size: int) -> str:
        """格式化字节大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


# 全局工具执行器实例缓存
_tool_executors: Dict[str, ToolExecutor] = {}


def get_tool_executor(user_id: str = "hanmeimei") -> ToolExecutor:
    """获取用户的工具执行器实例"""
    if user_id not in _tool_executors:
        _tool_executors[user_id] = ToolExecutor(user_id=user_id)
    return _tool_executors[user_id]
