
"""
任务处理模块 - 后台任务处理逻辑
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


async def process_files_from_path(
    task_id: str,
    file_paths: List[str],
    user_id: str,
    task_info: Dict[str, Any]
):
    """
    后台处理从路径读取的文件列表
    
    这与 process_files 函数的逻辑基本相同，
    区别在于文件已经存在于服务器上，无需上传步骤
    """
    from .app import (
        TASKS_DIR,
        LOGS_DIR,
        Settings,
        init_settings,
        load_llm_config,
        LLMClient,
        LogParser,
        ChunkProcessor,
        ReportGenerator,
        CheckpointManager,
        get_user_reports_dir,
        get_user_checkpoints_dir,
        setup_logging,
        get_storage
    )
    
    # 初始化组件
    log_file, logger = setup_logging(task_id, LOGS_DIR, file_paths)
    settings = init_settings()
    llm_config = load_llm_config()
    
    try:
        llm_client = LLMClient(config=llm_config, max_retries=3, retry_delay=1.0)
        parser = LogParser(chunk_size=50000)
        user_checkpoints_dir = get_user_checkpoints_dir(user_id)
        checkpoint_manager = CheckpointManager(checkpoint_dir=str(user_checkpoints_dir))
        processor = ChunkProcessor(
            parser=parser,
            llm_client=llm_client,
            checkpoint_manager=checkpoint_manager,
            chunk_size=50000,
            enable_checkpoint=False
        )
        user_reports_dir = get_user_reports_dir(user_id)
        report_generator = ReportGenerator(output_dir=str(user_reports_dir))
        
        # 更新任务状态
        task_info["status"] = "running"
        task_info["message"] = "开始处理文件..."
        task_info["progress"] = 5.0
        
        with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
            json.dump(task_info, f, indent=2)
        
        all_results = []
        all_reports = []
        processed_files = 0
        
        for idx, file_path in enumerate(file_paths):
            try:
                # 更新进度
                progress = 10.0 + (idx / len(file_paths)) * 80.0
                task_info["progress"] = progress
                task_info["message"] = f"正在处理: {Path(file_path).name} ({idx + 1}/{len(file_paths)})"
                
                with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
                    json.dump(task_info, f, indent=2)
                
                logger.info(f"[Task {task_id}] 开始处理文件: {file_path}")
                
                # 文件类型处理
                if file_path.lower().endswith('.pcap'):
                    logger.info(f"[Task {task_id}] PCAP文件检测")
                    # 这里可以添加PCAP处理逻辑
                    # 为简化，继续使用通用处理
                
                # 通用处理
                result = await processor.process_file_async(
                    file_path=file_path,
                    resume=True,
                    force_restart=True
                )
                all_results.append(result)
                
                logger.info(f"[Task {task_id}] 文件处理完成: {Path(file_path).name}, 状态: {result.status}")
                
                if result.status == "completed":
                    # 生成报告
                    report = report_generator.generate_report(result)
                    saved_files = report_generator.save_report(report, format="html+md+pdf+word")
                    
                    logger.info(f"[Task {task_id}] 报告已保存: {saved_files}")
                    
                    for saved_file in saved_files:
                        file_type = "html" if saved_file.endswith(".html") else \
                                    "pdf" if saved_file.endswith(".pdf") else \
                                    "word" if saved_file.endswith(".docx") else \
                                    "markdown" if saved_file.endswith(".md") else "json"
                        all_reports.append({
                            "name": Path(saved_file).name,
                            "path": saved_file,
                            "type": file_type
                        })
                    processed_files += 1
                
            except Exception as e:
                import traceback
                logger.error(f"[Task {task_id}] 处理文件 {file_path} 时出错: {str(e)}")
                logger.error(traceback.format_exc())
                continue
        
        # 生成综合报告（如果有多个文件）
        if len(all_results) > 1:
            task_info["message"] = "正在生成综合报告..."
            task_info["progress"] = 95.0
            with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
                json.dump(task_info, f, indent=2)
            
            try:
                combined_report = report_generator.generate_combined_report(all_results)
                combined_files = report_generator.save_report(combined_report, format="html+md+pdf+word", prefix="combined")
                logger.info(f"[Task {task_id}] 综合报告已保存: {combined_files}")
                for saved_file in combined_files:
                    file_type = "html" if saved_file.endswith(".html") else \
                                "pdf" if saved_file.endswith(".pdf") else \
                                "word" if saved_file.endswith(".docx") else \
                                "markdown" if saved_file.endswith(".md") else "json"
                    all_reports.append({
                        "name": Path(saved_file).name,
                        "path": saved_file,
                        "type": file_type
                    })
            except Exception as e:
                logger.error(f"[Task {task_id}] 生成综合报告失败: {str(e)}")
        
        # 完成处理
        task_info["progress"] = 100.0
        task_info["status"] = "completed"
        task_info["message"] = f"处理完成！共处理 {processed_files} 个文件"
        task_info["reports"] = all_reports
        
        # 保存历史记录
        if all_results and user_id:
            try:
                storage = get_storage()
                stats_summary = {
                    "total_files": len(file_paths),
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
                            "source": "process_from_path_endpoint"
                        }
                    }
                    storage.create(user_id, history_record)
                logger.info(f"[Task {task_id}] 已持久化 {len(all_results)} 条历史报告")
            except Exception as e:
                logger.error(f"[Task {task_id}] 持久化历史报告失败: {e}")
        
        # 保存最终状态
        with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
            json.dump(task_info, f, indent=2)
        
    except Exception as e:
        import traceback
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["message"] = f"处理失败: {str(e)}"
        with open(TASKS_DIR / f"{task_id}.json", 'w') as f:
            json.dump(task_info, f, indent=2)
        logger.error(f"处理任务 {task_id} 失败: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        if "llm_client" in locals():
            try:
                await llm_client.close()
            except Exception as e:
                logger.warning(f"关闭 LLM 客户端时出错: {str(e)}")

