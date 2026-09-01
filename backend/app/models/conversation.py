"""
会话管理模型
管理对话会话的状态和消息历史
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime

from app.utils.logger import logger


class Conversation:
    """单个对话会话"""

    def __init__(self, session_id: Optional[str] = None):
        """
        初始化对话会话

        Args:
            session_id: 会话ID，不传则自动生成
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到会话

        Args:
            role: 角色 (user/assistant/system)
            content: 消息内容
        """
        self.messages.append({
            "role": role,
            "content": content
        })
        self.updated_at = datetime.now()

    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages.copy()

    def get_last_n(self, n: int) -> List[Dict[str, str]]:
        """
        获取最近 n 条消息（用于控制上下文长度）

        Args:
            n: 消息数量

        Returns:
            最近 n 条消息列表
        """
        if n <= 0:
            return []
        return self.messages[-n:] if len(self.messages) >= n else self.messages.copy()

    def get_message_count(self) -> int:
        """获取消息总数"""
        return len(self.messages)

    def clear(self) -> None:
        """清空会话"""
        self.messages = []
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_messages": len(self.messages)
        }


class ConversationManager:
    """会话管理器（内存存储）"""

    def __init__(self):
        """初始化会话管理器"""
        self._sessions: Dict[str, Conversation] = {}
        logger.info("会话管理器初始化完成")

    def create_session(self) -> Conversation:
        """
        创建新会话

        Returns:
            新创建的会话对象
        """
        conversation = Conversation()
        self._sessions[conversation.session_id] = conversation
        logger.debug(f"创建新会话: {conversation.session_id}")
        return conversation

    def get_session(self, session_id: str) -> Optional[Conversation]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象，不存在则返回 None
        """
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None) -> Conversation:
        """
        获取或创建会话

        Args:
            session_id: 会话ID，不传则创建新会话

        Returns:
            会话对象
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        # 会话不存在或未传入 session_id，创建新会话
        return self.create_session()

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"删除会话: {session_id}")
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        """
        列出所有会话摘要

        Returns:
            会话摘要列表
        """
        return [
            {
                "session_id": session.session_id,
                "message_count": session.get_message_count(),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            for session in self._sessions.values()
        ]

    def get_session_count(self) -> int:
        """获取会话总数"""
        return len(self._sessions)

    def clear_all(self) -> None:
        """清空所有会话"""
        self._sessions.clear()
        logger.info("所有会话已清空")