"""
对话存储模块 - 支持用户数据隔离
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("web-langchain.conversation_store")


class ConversationStore:
    """对话存储管理器"""

    def __init__(self, user_id: str = "hanmeimei"):
        self.user_id = user_id
        self.data_dir = Path(__file__).parent.parent.parent / "log_analyzer" / "users" / user_id / "conversations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.data_dir / "_index.json"
        self._conversations = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """加载对话索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载对话索引失败: {e}")
                return {}
        return {}

    def _save_index(self):
        """保存对话索引"""
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(self._conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存对话索引失败: {e}")

    def _get_messages_file(self, conversation_id: str) -> Path:
        """获取对话消息文件路径"""
        return self.data_dir / f"{conversation_id}_messages.json"

    def save_conversation(self, conversation: Dict[str, Any]):
        """保存对话"""
        conversation_id = conversation["conversation_id"]
        self._conversations[conversation_id] = conversation
        self._save_index()

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话"""
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话（按时间倒序）"""
        conversations = list(self._conversations.values())
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        return conversations

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._save_index()

            messages_file = self._get_messages_file(conversation_id)
            if messages_file.exists():
                try:
                    messages_file.unlink()
                except Exception as e:
                    logger.warning(f"删除对话消息文件失败: {e}")

            return True
        return False

    def add_message(self, conversation_id: str, message: Dict[str, Any]):
        """添加消息"""
        messages_file = self._get_messages_file(conversation_id)
        messages = []

        if messages_file.exists():
            try:
                with open(messages_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            except Exception as e:
                logger.warning(f"加载对话消息失败: {e}")

        messages.append(message)

        try:
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存对话消息失败: {e}")

        if conversation_id in self._conversations:
            self._conversations[conversation_id]["message_count"] = len(messages)
            self._conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
            self._save_index()

    def get_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取对话消息"""
        messages_file = self._get_messages_file(conversation_id)

        if not messages_file.exists():
            return []

        try:
            with open(messages_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except Exception as e:
            logger.warning(f"加载对话消息失败: {e}")
            return []

        if offset > 0:
            messages = messages[offset:]

        if limit > 0 and limit < len(messages):
            messages = messages[-limit:]

        return messages

    def clear_messages(self, conversation_id: str):
        """清空对话消息"""
        messages_file = self._get_messages_file(conversation_id)
        if messages_file.exists():
            try:
                messages_file.unlink()
            except Exception as e:
                logger.warning(f"删除对话消息文件失败: {e}")

        if conversation_id in self._conversations:
            self._conversations[conversation_id]["message_count"] = 0
            self._conversations[conversation_id]["updated_at"] = datetime.now().isoformat()
            self._save_index()


_conversation_stores: Dict[str, ConversationStore] = {}


def get_conversation_store(user_id: str = "hanmeimei") -> ConversationStore:
    """获取对话存储实例"""
    if user_id not in _conversation_stores:
        _conversation_stores[user_id] = ConversationStore(user_id=user_id)
    return _conversation_stores[user_id]
