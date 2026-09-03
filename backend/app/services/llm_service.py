"""
LLM 服务层
封装对话业务逻辑，编排会话管理和模型调用
支持普通对话、模板生成和 RAG 增强生成
"""

from typing import Optional, Dict, Any

from app.core.ollama_client import OllamaClient
from app.models.conversation import ConversationManager
from app.services.prompt_service import prompt_service
from app.services.post_processor import post_processor
from app.services.rag_service import rag_service
from app.utils.logger import logger
from config.settings import Config


class LLMService:
    """LLM 服务类，处理对话业务逻辑"""

    def __init__(self):
        self.ollama_client = OllamaClient()
        self.conversation_manager = ConversationManager()
        self.max_history = Config.MAX_HISTORY_LENGTH

        logger.info("LLM 服务初始化完成")

    def chat(
            self,
            user_message: str,
            session_id: Optional[str] = None,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            template: Optional[str] = None,
            template_params: Optional[Dict[str, Any]] = None,
            rag: bool = False,
            rag_top_k: int = 3
    ) -> Dict[str, Any]:
        """
        处理对话请求（支持普通对话、模板生成和 RAG 增强生成）

        Args:
            user_message: 用户消息内容
            session_id: 会话ID（可选，不传则创建新会话）
            model: 模型名称（可选，使用默认模型）
            temperature: 温度参数（可选）
            max_tokens: 最大生成 token 数（可选）
            template: 模板名称（可选，指定后使用模板生成）
            template_params: 模板参数（可选，与 template 配合使用）
            rag: 是否启用 RAG 检索增强
            rag_top_k: RAG 检索文档数量

        Returns:
            包含 session_id 和 AI 回复的字典
        """
        try:
            # 1. 获取或创建会话
            conversation = self.conversation_manager.get_or_create_session(session_id)

            # 2. RAG 增强生成（优先级最高）
            if rag:
                return self._handle_rag_chat(
                    conversation=conversation,
                    user_message=user_message,
                    template=template,
                    template_params=template_params or {},
                    rag_top_k=rag_top_k,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            # 3. 模板生成逻辑
            if template:
                return self._handle_template_chat(
                    conversation=conversation,
                    user_message=user_message,
                    template=template,
                    template_params=template_params or {},
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            # 4. 普通对话逻辑
            return self._handle_normal_chat(
                conversation=conversation,
                user_message=user_message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

        except Exception as e:
            logger.error(f"对话处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _handle_normal_chat(
            self,
            conversation,
            user_message: str,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理普通对话
        """
        # 记录用户消息
        conversation.add_message("user", user_message)

        # 获取历史消息（控制上下文长度）
        history_messages = conversation.get_last_n(self.max_history * 2)

        logger.info(f"处理普通对话: session_id={conversation.session_id}, message_len={len(user_message)}")

        # 调用模型生成回复
        response = self.ollama_client.chat(
            messages=history_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        # 记录 AI 回复
        conversation.add_message("assistant", response)

        return {
            "success": True,
            "data": {
                "session_id": conversation.session_id,
                "response": response
            }
        }

    def _handle_template_chat(
            self,
            conversation,
            user_message: str,
            template: str,
            template_params: Dict[str, Any],
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理模板生成
        """
        # 1. 验证模板是否存在
        if not prompt_service.is_valid_template(template):
            logger.warning(f"模板不存在: {template}")
            return {
                "success": False,
                "error": f"模板 '{template}' 不存在"
            }

        # 2. 合并参数
        merged_params = template_params.copy()
        template_meta = prompt_service.get_template_metadata(template)
        if template_meta:
            required_params = template_meta.get('required_params', [])
            if required_params and len(required_params) == 1:
                param_name = required_params[0]
                if param_name not in merged_params or not merged_params[param_name]:
                    merged_params[param_name] = user_message

        logger.info(f"处理模板生成: session_id={conversation.session_id}, template={template}, params={merged_params}")

        # 3. 渲染 Prompt
        try:
            prompts = prompt_service.render_prompt(template, **merged_params)
        except ValueError as e:
            logger.error(f"Prompt 渲染失败: {str(e)}")
            return {
                "success": False,
                "error": f"参数错误: {str(e)}"
            }

        # 4. 记录用户消息
        user_display = f"[{template}] {user_message}"
        conversation.add_message("user", user_display)

        # 5. 构建消息列表
        messages = []
        if prompts.get("system"):
            messages.append({
                "role": "system",
                "content": prompts["system"]
            })

        history_messages = conversation.get_last_n(self.max_history * 2)
        for msg in history_messages:
            if msg["role"] != "system":
                messages.append(msg)

        messages.append({
            "role": "user",
            "content": prompts["user"]
        })

        # 6. 调用模型生成
        response = self.ollama_client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        # 7. 后处理清洗
        cleaned_response = post_processor.clean_output(response, template)
        logger.debug(
            f"模板生成完成: template={template}, original_len={len(response)}, cleaned_len={len(cleaned_response)}")

        # 8. 记录 AI 回复
        conversation.add_message("assistant", cleaned_response)

        return {
            "success": True,
            "data": {
                "session_id": conversation.session_id,
                "response": cleaned_response,
                "template": template,
                "raw_response": response if Config.DEBUG else None
            }
        }

    def _handle_rag_chat(
            self,
            conversation,
            user_message: str,
            template: Optional[str],
            template_params: Dict[str, Any],
            rag_top_k: int,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理 RAG 增强生成
        """
        logger.info(
            f"处理 RAG 增强生成: session_id={conversation.session_id}, template={template}, rag_top_k={rag_top_k}")

        # 1. 记录用户消息（标注 RAG 启用）
        user_display = f"[RAG] {user_message}"
        conversation.add_message("user", user_display)

        # 2. 调用 RAG 服务生成
        rag_result = rag_service.rag_generate(
            query=user_message,
            top_k=rag_top_k,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            template_name=template
        )

        if not rag_result.get('success'):
            error_msg = rag_result.get('error', 'RAG 生成失败')
            logger.error(f"RAG 生成失败: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

        # 3. 获取生成结果
        data = rag_result.get('data', {})
        response = data.get('response', '')
        sources = data.get('sources', [])
        is_fallback = data.get('is_fallback', False)

        # 4. 构建带来源引用的回复
        if sources and not is_fallback:
            # 如果回复中已经包含引用，不再重复添加
            source_text = "\n\n---\n**📎 引用来源：**\n"
            for source in sources:
                source_text += f"- {source.get('source', '未知')} (相关度: {source.get('score', 0):.1%})\n"

            # 如果原始回复已包含引用标注，不重复添加
            if "引用来源" not in response:
                response_with_sources = response + source_text
            else:
                response_with_sources = response
        else:
            response_with_sources = response

        # 5. 记录 AI 回复
        conversation.add_message("assistant", response_with_sources)

        return {
            "success": True,
            "data": {
                "session_id": conversation.session_id,
                "response": response_with_sources,
                "rag": True,
                "sources": sources if sources else [],
                "is_fallback": is_fallback,
                "retrieved_count": data.get('total_retrieved', 0),
                "template": template
            }
        }

    def clear_session(self, session_id: str) -> Dict[str, Any]:
        """清空会话历史"""
        conversation = self.conversation_manager.get_session(session_id)
        if conversation:
            conversation.clear()
            logger.info(f"清空会话: {session_id}")
            return {
                "success": True,
                "message": f"会话 {session_id} 已清空"
            }
        else:
            return {
                "success": False,
                "error": f"会话 {session_id} 不存在"
            }

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话"""
        success = self.conversation_manager.delete_session(session_id)
        if success:
            logger.info(f"删除会话: {session_id}")
            return {
                "success": True,
                "message": f"会话 {session_id} 已删除"
            }
        else:
            return {
                "success": False,
                "error": f"会话 {session_id} 不存在"
            }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        conversation = self.conversation_manager.get_session(session_id)
        if conversation:
            return {
                "success": True,
                "data": conversation.to_dict()
            }
        else:
            return {
                "success": False,
                "error": f"会话 {session_id} 不存在"
            }

    def list_sessions(self) -> Dict[str, Any]:
        """列出所有会话"""
        sessions = self.conversation_manager.list_sessions()
        return {
            "success": True,
            "data": {
                "total": len(sessions),
                "sessions": sessions
            }
        }

    def list_templates(self) -> Dict[str, Any]:
        """列出所有可用模板"""
        templates = prompt_service.list_templates()
        return {
            "success": True,
            "data": templates
        }