"""
聊天管理器 - 处理消息发送和流式响应，完整集成原有日志分析系统
包含：真实LLM调用、指代消解、上下文压缩等功能
"""
import json
import logging
import asyncio
import uuid
import re
from typing import Dict, Any, List, AsyncGenerator, Optional
from datetime import datetime

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_analyzer.config.settings import load_llm_config
from log_analyzer.llm.client import LLMClient
from .conversation_store import get_conversation_store
from .tool_executor import get_tool_executor

logger = logging.getLogger("web-langchain.chat_manager")


class ContextCompressor:
    """上下文压缩器 - 智能压缩对话历史"""
    
    def __init__(self, max_messages: int = 10, compression_threshold: int = 15):
        self.max_messages = max_messages
        self.compression_threshold = compression_threshold
    
    def compress_context(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩对话上下文"""
        if len(messages) <= self.compression_threshold:
            return messages[-self.max_messages:] if len(messages) > self.max_messages else messages
        
        recent_messages = messages[-5:]
        
        summary = self._generate_summary(messages[:-5])
        
        summary_message = {
            "message_id": f"summary_{datetime.now().timestamp()}",
            "role": "system",
            "content": f"[对话历史摘要] 之前有 {len(messages) - 5} 条消息的对话已压缩为摘要：{summary}",
            "timestamp": datetime.now().isoformat(),
            "metadata": {"type": "summary"}
        }
        
        return [summary_message] + recent_messages
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        summary_parts = []
        if user_messages:
            first_query = user_messages[0].get("content", "")[:50]
            summary_parts.append(f"首问: {first_query}...")
        
        summary_parts.append(f"共 {len(user_messages)} 次用户提问")
        summary_parts.append(f"生成了 {len(assistant_messages)} 次回复")
        
        return "；".join(summary_parts)


class PronounResolver:
    """指代消解器 - 解析代词和上下文引用"""
    
    PRONOUN_PATTERNS = {
        "这": ["这个", "这儿", "这里"],
        "那": ["那个", "那儿", "那里"],
        "它": ["它们", "它的"],
        "他": ["他们", "他的"],
        "她": ["她们", "她的"],
        "我": ["我的"],
        "你": ["你的"],
        "这些": [],
        "那些": [],
        "此": ["此次", "此时"],
        "该": ["该文件", "该日志"],
        "以上": ["以上内容", "以上分析"],
        "以下": ["以下内容", "以下分析"],
        "刚才": ["刚才的", "刚才说"],
        "之前": ["之前说的", "之前分析"],
        "现在": ["现在的", "现在分析"],
        "刚才": []
    }
    
    CONTEXT_KEYWORDS = ["文件", "日志", "报告", "分析", "错误", "问题", "结果"]
    
    def resolve_pronouns(self, user_input: str, context: Dict[str, Any]) -> str:
        """解析并替换代词"""
        resolved = user_input
        
        uploaded_files = context.get("uploaded_files", [])
        recent_files = context.get("recent_files", [])
        recent_analysis = context.get("recent_analysis", {})
        
        resolved = self._resolve_file_pronouns(resolved, uploaded_files, recent_files)
        resolved = self._resolve_analysis_pronouns(resolved, recent_analysis)
        resolved = self._resolve_action_pronouns(resolved, context)
        
        return resolved
    
    def _resolve_file_pronouns(self, text: str, uploaded_files: List, recent_files: List) -> str:
        """解析文件相关的代词"""
        all_files = uploaded_files + recent_files
        
        if not all_files:
            return text
        
        last_file = all_files[0] if all_files else None
        if not last_file:
            return text
        
        file_name = last_file.get("name", "") if isinstance(last_file, dict) else str(last_file)
        
        pronouns_to_resolve = ["这个", "那个", "它", "该文件", "该日志"]
        
        for pronoun in pronouns_to_resolve:
            if pronoun in text:
                text = text.replace(pronoun, f"文件 {file_name}")
        
        return text
    
    def _resolve_analysis_pronouns(self, text: str, recent_analysis: Dict) -> str:
        """解析分析相关的代词"""
        if "刚才" in text or "之前的" in text or "以上" in text:
            analysis_type = recent_analysis.get("type", "")
            if analysis_type:
                text = text.replace("刚才", f"{analysis_type}结果")
                text = text.replace("之前的", "")
                text = text.replace("以上", f"{analysis_type}结果")
        
        return text
    
    def _resolve_action_pronouns(self, text: str, context: Dict) -> str:
        """解析动作相关的代词"""
        last_action = context.get("last_action", "")
        
        if "再" in text and last_action:
            if "分析" in last_action:
                text = text.replace("再", f"重新{last_action}")
            elif "生成" in last_action:
                text = text.replace("再", f"重新{last_action}")
        
        return text
    
    def detect_ambiguous_reference(self, text: str) -> bool:
        """检测是否有歧义的引用"""
        ambiguous_patterns = [
            r"这些", r"那些", r"它们",
            r"上面的", r"下面的",
            r"刚才的", r"之前的"
        ]
        
        for pattern in ambiguous_patterns:
            if re.search(pattern, text):
                return True
        
        return False


class ChatManager:
    """聊天管理器 - 集成真实LLM、指代消解、上下文压缩"""
    
    def __init__(self, user_id: str = "hanmeimei"):
        self.user_id = user_id
        
        try:
            llm_config = load_llm_config()
            self.llm_client = LLMClient(config=llm_config)
            logger.info("LLM 客户端初始化成功")
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")
            self.llm_client = None
        
        self.conversation_store = get_conversation_store(user_id=user_id)
        self.tool_executor = get_tool_executor(user_id=user_id)
        
        self.context_compressor = ContextCompressor()
        self.pronoun_resolver = PronounResolver()
        self.user_contexts = {}

    def _get_user_context(self, conversation_id: str) -> Dict[str, Any]:
        """获取用户上下文信息"""
        if conversation_id not in self.user_contexts:
            self.user_contexts[conversation_id] = {
                "uploaded_files": [],
                "recent_files": [],
                "recent_analysis": {},
                "last_action": ""
            }
        
        try:
            files_result = self.tool_executor._handle_list_uploaded_files()
            if files_result.get("success"):
                self.user_contexts[conversation_id]["uploaded_files"] = files_result.get("files", [])[:5]
        except Exception as e:
            logger.warning(f"获取上传文件失败: {e}")
        
        return self.user_contexts[conversation_id]

    def _update_user_context(self, conversation_id: str, action: str, data: Any):
        """更新用户上下文"""
        context = self._get_user_context(conversation_id)
        context["last_action"] = action
        
        if action == "analyze":
            context["recent_analysis"] = {"type": "分析", "data": data}
            if isinstance(data, dict) and "file" in data:
                context["recent_files"].insert(0, {"name": data["file"]})
                context["recent_files"] = context["recent_files"][:5]
        elif action == "upload":
            if isinstance(data, dict):
                context["recent_files"].insert(0, data)
                context["recent_files"] = context["recent_files"][:5]

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送消息并获取响应"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        context = self._get_user_context(conversation_id)
        resolved_content = self.pronoun_resolver.resolve_pronouns(content, context)
        
        user_message = {
            "message_id": message_id,
            "role": "user",
            "content": resolved_content,
            "original_content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        self.conversation_store.add_message(conversation_id, user_message)
        
        response = await self._generate_response(conversation_id, resolved_content)
        
        assistant_message_id = str(uuid.uuid4())
        assistant_message = {
            "message_id": assistant_message_id,
            "role": "assistant",
            "content": response.get("content", ""),
            "timestamp": datetime.now().isoformat(),
            "metadata": response.get("metadata", {})
        }
        
        self.conversation_store.add_message(conversation_id, assistant_message)
        
        if response.get("metadata", {}).get("tool_used"):
            self._update_user_context(conversation_id, response["metadata"]["tool_used"], response)
        
        return {
            "success": True,
            "user_message": user_message,
            "assistant_message": assistant_message
        }

    async def stream_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
        files: Dict[str, Any] = None  # 新增：暂存文件信息
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式发送消息"""
        logger.info("=" * 60)
        logger.info(f"📨 收到新消息请求 - 对话ID: {conversation_id}")
        logger.info(f"📝 用户内容: {content}")
        if files:
            uploaded_files = files.get("uploaded", [])
            server_files = files.get("server", [])
            logger.info(f"📁 暂存文件信息:")
            if uploaded_files:
                logger.info(f"  📄 上传文件: {uploaded_files}")
            if server_files:
                logger.info(f"  📂 服务器文件: {server_files}")
        logger.info("=" * 60)
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        context = self._get_user_context(conversation_id)
        
        # 如果有暂存文件，更新上下文
        if files:
            uploaded_files = files.get("uploaded", [])
            server_files = files.get("server", [])
            for filename in uploaded_files:
                context["recent_files"].insert(0, {"name": filename, "type": "uploaded"})
            for file_info in server_files:
                context["recent_files"].insert(0, {"name": file_info.get("name", ""), "type": "server", "path": file_info.get("path", "")})
            context["recent_files"] = context["recent_files"][:10]  # 保留最近10个文件
        
        resolved_content = self.pronoun_resolver.resolve_pronouns(content, context)
        
        if resolved_content != content:
            yield {
                "type": "pronoun_resolved",
                "original": content,
                "resolved": resolved_content,
                "timestamp": datetime.now().isoformat()
            }
        
        user_message = {
            "message_id": message_id,
            "role": "user",
            "content": resolved_content,
            "original_content": content,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        self.conversation_store.add_message(conversation_id, user_message)
        
        yield {
            "type": "user_message",
            "message": user_message
        }
        
        assistant_message_id = str(uuid.uuid4())
        full_content = ""
        tool_calls = []
        
        # 关键：把 files 传递给生成响应的方法！
        async for chunk in self._generate_stream_response(conversation_id, resolved_content, files):
            yield chunk
            
            if chunk.get("type") == "content":
                full_content += chunk.get("content", "")
            elif chunk.get("type") == "tool_call":
                tool_calls.append(chunk.get("tool", {}))
        
        assistant_message = {
            "message_id": assistant_message_id,
            "role": "assistant",
            "content": full_content,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "tool_calls": tool_calls,
                "tokens_used": len(full_content)
            }
        }
        
        self.conversation_store.add_message(conversation_id, assistant_message)
        
        if tool_calls:
            tool_result = tool_calls[0] if tool_calls else None
            if tool_result and isinstance(tool_result, dict):
                tool_name = tool_result.get("name", tool_result.get("tool", ""))
                self._update_user_context(conversation_id, tool_name, tool_result)
        
        yield {
            "type": "assistant_message",
            "message": assistant_message
        }

    async def _generate_response(self, conversation_id: str, user_content: str, files: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成响应"""
        conversation = self.conversation_store.get_conversation(conversation_id)
        if not conversation:
            return {"content": "对话不存在", "metadata": {}}
        
        messages = self.conversation_store.get_messages(conversation_id, limit=20)
        compressed_messages = self.context_compressor.compress_context(messages)
        
        context = self._build_context(compressed_messages)
        
        tool_result = await self._try_execute_tools(user_content, files)
        if tool_result and tool_result.get("success"):
            response_content = self._format_tool_response(tool_result)
            return {
                "content": response_content,
                "metadata": {
                    "tool_used": tool_result.get("tool", ""),
                    "tools_used": [tool_result.get("tool", "")]
                }
            }
        
        if self.llm_client:
            llm_response = await self._call_llm(user_content, context)
            if llm_response:
                return {
                    "content": llm_response,
                    "metadata": {"intent": "llm_response"}
                }
        
        fallback_response = self._generate_fallback_response(user_content)
        return {
            "content": fallback_response,
            "metadata": {"intent": "fallback"}
        }

    async def _generate_stream_response(
        self,
        conversation_id: str,
        user_content: str,
        files: Dict[str, Any] = None  # 新增：接收文件信息
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """生成流式响应"""
        yield {
            "type": "thinking",
            "content": "正在分析您的请求...",
            "timestamp": datetime.now().isoformat()
        }
        
        intent = self._detect_intent(user_content)
        yield {
            "type": "intent",
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }
        
        # 关键：把 files 传递给工具执行方法！
        tool_result = await self._try_execute_tools(user_content, files)
        if tool_result and tool_result.get("success"):
            yield {
                "type": "tool_call",
                "tool": tool_result.get("tool", ""),
                "tool_name": tool_result.get("tool", ""),
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
            
            await asyncio.sleep(0.3)
            
            yield {
                "type": "tool_result",
                "tool": tool_result.get("tool", ""),
                "tool_name": tool_result.get("tool", ""),
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            response_content = self._format_tool_response(tool_result)
            
            if self.llm_client and tool_result.get("tool") in ["list_uploaded_files", "list_reports"]:
                try:
                    messages = self.conversation_store.get_messages(conversation_id, limit=5)
                    context = self._build_context(messages)
                    enhanced_response = await self._call_llm(
                        f"基于以下工具执行结果，用友好的方式回复用户：\n\n{response_content}\n\n用户的问题是关于日志分析的。",
                        context
                    )
                    if enhanced_response:
                        response_content = enhanced_response
                except Exception as e:
                    logger.warning(f"LLM增强响应失败: {e}")
            
            for i in range(0, len(response_content), 30):
                chunk = response_content[i:i + 30]
                yield {
                    "type": "content",
                    "content": chunk,
                    "timestamp": datetime.now().isoformat()
                }
                await asyncio.sleep(0.02)
        else:
            if self.llm_client:
                try:
                    messages = self.conversation_store.get_messages(conversation_id, limit=10)
                    compressed_messages = self.context_compressor.compress_context(messages)
                    context = self._build_context(compressed_messages)
                    
                    full_response = await self._call_llm(user_content, context)
                    
                    if full_response:
                        for i in range(0, len(full_response), 30):
                            chunk = full_response[i:i + 30]
                            yield {
                                "type": "content",
                                "content": chunk,
                                "timestamp": datetime.now().isoformat()
                            }
                            await asyncio.sleep(0.02)
                    else:
                        fallback_response = self._generate_fallback_response(user_content)
                        for i in range(0, len(fallback_response), 30):
                            chunk = fallback_response[i:i + 30]
                            yield {
                                "type": "content",
                                "content": chunk,
                                "timestamp": datetime.now().isoformat()
                            }
                            await asyncio.sleep(0.02)
                except Exception as e:
                    logger.error(f"LLM调用失败: {e}")
                    fallback_response = self._generate_fallback_response(user_content)
                    for i in range(0, len(fallback_response), 30):
                        chunk = fallback_response[i:i + 30]
                        yield {
                            "type": "content",
                            "content": chunk,
                            "timestamp": datetime.now().isoformat()
                        }
                        await asyncio.sleep(0.02)
            else:
                fallback_response = self._generate_fallback_response(user_content)
                for i in range(0, len(fallback_response), 30):
                    chunk = fallback_response[i:i + 30]
                    yield {
                        "type": "content",
                        "content": chunk,
                        "timestamp": datetime.now().isoformat()
                    }
                    await asyncio.sleep(0.02)
        
        yield {
            "type": "finish",
            "timestamp": datetime.now().isoformat()
        }

    async def _call_llm(self, user_content: str, context: str = "") -> Optional[str]:
        """调用真实LLM"""
        if not self.llm_client:
            return None
        
        try:
            system_prompt = """你是一个专业的日志分析助手。请根据用户的问题和上下文信息，提供准确、专业的回答。

你可以帮助用户：
1. 分析日志文件中的错误和警告
2. 搜索日志中的特定内容
3. 生成详细的分析报告
4. 解释错误信息的含义和可能的解决方案
5. 提供性能优化建议

请用简洁、专业的语言回答。"""
            
            messages = []
            if context:
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "system", "content": f"上下文信息：\n{context}"})
            else:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": user_content})
            
            response = await self.llm_client.chat(messages)
            
            if response and response.get("content"):
                return response["content"]
            
            return None
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return None

    async def _try_execute_tools(self, user_content: str, files: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """尝试执行工具 - 优先处理暂存文件"""
        logger.info("🔧 开始工具执行尝试...")
        user_content_lower = user_content.lower()
        
        # 1. 优先处理：如果有暂存文件，立即分析！
        if files:
            uploaded_files = files.get("uploaded", [])
            server_files = files.get("server", [])
            
            if uploaded_files or server_files:
                logger.info("✅ 检测到暂存文件，优先执行分析！")
                # 先处理上传的文件
                for filename in uploaded_files:
                    try:
                        logger.info(f"  📄 开始处理上传文件: {filename}")
                        logger.info(f"  🛠️  调用工具: analyze_errors (参数: file_path={filename}, mode=llm)")
                        result = await self.tool_executor.execute_tool(
                            "analyze_errors",
                            {"file_path": filename, "mode": "llm", "deep_analysis": True}
                        )
                        if result.get("success"):
                            logger.info(f"  ✅ 工具调用成功! 分析完成: {filename}")
                            result["tool"] = "analyze_errors"
                            return result
                        else:
                            logger.warning(f"  ⚠️ 工具调用返回失败: {result.get('error', '未知错误')}")
                    except Exception as e:
                        logger.error(f"  ❌ 分析文件 {filename} 异常: {e}")
                        continue
                
                # 再处理服务器文件
                for file_info in server_files:
                    try:
                        file_path = file_info.get("path", "")
                        filename = file_info.get("name", "")
                        logger.info(f"  📂 开始处理服务器文件: {filename} (路径: {file_path})")
                        logger.info(f"  🛠️  调用工具: analyze_from_server_path (参数: path={file_path}, file_pattern={filename})")
                        # 服务器文件需要特殊处理
                        result = await self.tool_executor.execute_tool(
                            "analyze_from_server_path",
                            {"path": file_path, "file_pattern": filename}
                        )
                        if result.get("success"):
                            logger.info(f"  ✅ 工具调用成功! 分析完成: {filename}")
                            result["tool"] = "analyze_from_server_path"
                            return result
                        else:
                            logger.warning(f"  ⚠️ 工具调用返回失败: {result.get('error', '未知错误')}")
                    except Exception as e:
                        logger.error(f"  ❌ 分析服务器文件 {filename} 异常: {e}")
                        continue
        
        # 2. 常规关键词匹配（没有暂存文件时）
        file_patterns = [
            ("上传文件", "upload"),
            ("上传了", "upload"),
            ("已上传", "list_uploaded_files"),
            ("上传的文件", "list_uploaded_files"),
            ("列出文件", "list_uploaded_files"),
            ("历史报告", "list_reports"),
            ("报告列表", "list_reports"),
            ("列出报告", "list_reports"),
            ("统计", "get_statistics"),
            ("统计信息", "get_statistics"),
            ("日志统计", "get_statistics"),
            ("服务器目录", "list_server_directories"),
            ("服务器文件", "list_server_directories"),
            ("浏览服务器", "list_server_directories"),
            ("pcap", "analyze_pcap"),
            ("PCAP", "analyze_pcap"),
            ("nginx", "analyze_nginx"),
            ("Nginx", "analyze_nginx"),
            ("分析错误", "analyze_errors"),
            ("错误分析", "analyze_errors")
        ]
        
        for keyword, tool_name in file_patterns:
            if keyword in user_content_lower:
                result = await self.tool_executor.execute_tool(tool_name, {})
                result["tool"] = tool_name
                return result
        
        log_search_patterns = ["搜索", "查找", "找"]
        for pattern in log_search_patterns:
            if pattern in user_content_lower:
                match = re.search(rf'{pattern}\s+(.+)', user_content)
                if match:
                    query = match.group(1).strip()
                    result = await self.tool_executor.execute_tool("search_logs", {"query": query})
                    result["tool"] = "search_logs"
                    return result
        
        return None

    def _detect_intent(self, content: str) -> str:
        """检测用户意图"""
        content_lower = content.lower()
        
        intent_scores = {
            "search": 0,
            "analyze": 0,
            "report": 0,
            "statistics": 0,
            "upload": 0,
            "chat": 0
        }
        
        intent_keywords = {
            "search": ["搜索", "查找", "找", "查询"],
            "analyze": ["分析", "分析错误", "错误分析", "检查"],
            "report": ["报告", "生成报告", "导出", "下载"],
            "statistics": ["统计", "数据", "数量", "分布"],
            "upload": ["上传", "文件", "导入"],
            "chat": ["帮助", "怎么用", "是什么"]
        }
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    intent_scores[intent] += 1
        
        max_intent = max(intent_scores, key=intent_scores.get)
        return max_intent if intent_scores[max_intent] > 0 else "chat"

    def _build_context(self, messages: List[Dict[str, Any]]) -> str:
        """构建上下文"""
        context_parts = []
        
        for msg in messages[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if msg.get("metadata", {}).get("type") == "summary":
                context_parts.append(f"[摘要] {content}")
            else:
                context_parts.append(f"{role}: {content[:100]}")
        
        return "\n".join(context_parts)

    def _format_tool_response(self, tool_result: Dict[str, Any]) -> str:
        """格式化工具响应"""
        tool = tool_result.get("tool", "")
        
        if tool == "list_uploaded_files":
            files = tool_result.get("files", [])
            if not files:
                return "您还没有上传任何文件。请先上传日志文件，然后我可以帮您分析。"
            
            response = f"您已上传 {len(files)} 个文件：\n\n"
            for f in files:
                response += f"📄 {f['name']} ({f['size_formatted']})\n"
            
            response += "\n您可以：\n"
            response += "• 让我分析某个文件：\"分析 app.log\"\n"
            response += "• 搜索日志内容：\"搜索 ERROR\"\n"
            response += "• 生成报告：\"为 app.log 生成报告\""
            return response
        
        elif tool == "list_reports":
            reports = tool_result.get("reports", [])
            if not reports:
                return "您还没有生成过报告。分析日志后即可生成多格式报告。"
            
            response = f"您共有 {len(reports)} 份历史报告：\n\n"
            for report in reports[:5]:
                response += f"📊 {report['datetime']}\n"
                for f in report.get('files', []):
                    response += f"   • {f['name']} ({f['size_formatted']})\n"
                response += "\n"
            
            if len(reports) > 5:
                response += f"... 还有 {len(reports) - 5} 份报告\n"
            
            return response
        
        elif tool == "get_statistics":
            stats = tool_result.get("statistics", {})
            response = "📈 日志统计信息：\n\n"
            response += f"总文件数：{stats.get('total_files', 0)}\n"
            response += f"总日志数：{stats.get('total_logs', 0)}\n"
            response += f"错误数：{stats.get('error_count', 0)} 🔴\n"
            response += f"警告数：{stats.get('warn_count', 0)} 🟡\n"
            response += f"信息数：{stats.get('info_count', 0)} 🟢\n"
            response += f"调试数：{stats.get('debug_count', 0)} ⚪\n"
            
            files = stats.get('files', [])
            if files:
                response += "\n各文件详情：\n"
                for f in files:
                    response += f"\n📄 {f['filename']}:\n"
                    response += f"   总行数：{f['total']}\n"
                    response += f"   错误：{f['error']} 🔴\n"
                    response += f"   警告：{f['warn']} 🟡\n"
            
            return response
        
        elif tool == "search_logs":
            results = tool_result.get("results", [])
            total = tool_result.get("total", 0)
            
            if not results:
                return "未找到匹配的日志记录。"
            
            response = f"🔍 找到 {total} 条匹配的日志：\n\n"
            for i, result in enumerate(results[:10], 1):
                log = result.get("log", {})
                response += f"{i}. [{log.get('level', 'INFO')}] {log.get('message', '')[:100]}\n"
                if log.get('timestamp'):
                    response += f"   时间：{log.get('timestamp')}\n"
                response += "\n"
            
            if total > 10:
                response += f"... 还有 {total - 10} 条结果\n"
            
            return response
        
        elif tool == "list_server_directories":
            if tool_result.get("is_root"):
                dirs = tool_result.get("directories", [])
                response = "📁 服务器可访问目录：\n\n"
                for d in dirs:
                    response += f"• {d}\n"
                response += "\n请告诉我要浏览哪个目录。"
            else:
                contents = tool_result.get("contents", [])
                response = f"📁 {tool_result.get('path', '')}：\n\n"
                
                dirs = [c for c in contents if c.get('is_directory')]
                files = [c for c in contents if c.get('is_file')]
                
                if dirs:
                    response += "📂 目录：\n"
                    for d in dirs:
                        response += f"• {d['name']}/\n"
                
                if files:
                    response += "\n📄 文件：\n"
                    for f in files[:10]:
                        response += f"• {f['name']} ({f.get('size_formatted', '')})\n"
                    
                    if len(files) > 10:
                        response += f"... 还有 {len(files) - 10} 个文件\n"
            
            return response
        
        else:
            return json.dumps(tool_result, ensure_ascii=False, indent=2)

    def _generate_fallback_response(self, user_content: str) -> str:
        """生成降级响应"""
        content_lower = user_content.lower()
        
        if any(keyword in content_lower for keyword in ["你好", "您好", "hi", "hello"]):
            return "您好！我是日志分析助手。我可以帮您：\n\n" \
                   "• 上传并分析日志文件\n" \
                   "• 搜索错误和警告\n" \
                   "• 生成多格式分析报告\n" \
                   "• 分析服务器上的日志\n\n" \
                   "请上传文件或告诉我您需要什么帮助！"
        
        elif any(keyword in content_lower for keyword in ["帮助", "help", "怎么用"]):
            return "使用指南：\n\n" \
                   "1️⃣ 上传日志文件 → 点击上传按钮\n" \
                   "2️⃣ 分析日志 → \"分析 app.log\"\n" \
                   "3️⃣ 搜索内容 → \"搜索 ERROR\"\n" \
                   "4️⃣ 生成报告 → \"生成报告\"\n" \
                   "5️⃣ 查看统计 → \"显示统计\"\n\n" \
                   "或使用快捷操作按钮！"
        
        elif any(keyword in content_lower for keyword in ["谢谢", "感谢"]):
            return "不客气！如果还有其他需要帮助的，请随时告诉我。"
        
        else:
            return "我理解您的需求。您可以：\n\n" \
                   "• 上传日志文件让我分析\n" \
                   "• 说出文件名来让我分析\n" \
                   "• 或使用快捷操作按钮\n\n" \
                   "请问您需要什么帮助？"


_chat_managers: Dict[str, ChatManager] = {}


def get_chat_manager(user_id: str = "hanmeimei") -> ChatManager:
    """获取用户的聊天管理器实例"""
    if user_id not in _chat_managers:
        _chat_managers[user_id] = ChatManager(user_id=user_id)
    return _chat_managers[user_id]