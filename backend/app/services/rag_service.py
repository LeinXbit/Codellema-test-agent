"""
RAG 服务
提供文档管理、检索增强生成等核心 RAG 功能
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from app.core.vector_store import vector_store
from app.core.document_loader import document_loader
from app.core.ollama_client import OllamaClient
from app.services.prompt_service import prompt_service
from app.services.post_processor import post_processor
from app.utils.logger import logger
from config.settings import Config


class RAGService:
    """
    RAG 服务类
    提供文档管理、检索增强生成等核心功能
    """

    def __init__(self):
        """初始化 RAG 服务"""
        self.ollama_client = OllamaClient()
        self.default_top_k = 3
        self.default_model = Config.DEFAULT_MODEL

        logger.info("RAG 服务初始化完成")

    # ==================== 文档管理 ====================

    def add_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        添加单个文档到知识库

        Args:
            file_path: 文件路径

        Returns:
            操作结果
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            # 加载并分块
            chunks = document_loader.load_and_split(file_path)

            if not chunks:
                return {
                    "success": False,
                    "error": "文档加载后为空，请检查文件内容"
                }

            # 添加到向量库
            added_count = vector_store.add_documents(chunks)

            logger.info(f"添加文档成功: {file_path.name}, 共 {added_count} 个块")
            return {
                "success": True,
                "data": {
                    "source": file_path.name,
                    "chunks_added": added_count,
                    "total_chunks": len(chunks)
                }
            }

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"添加文档失败: {str(e)}"
            }

    def add_documents_from_dir(
            self,
            directory: Union[str, Path],
            extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量添加目录下所有文档

        Args:
            directory: 目录路径
            extensions: 允许的扩展名列表

        Returns:
            操作结果
        """
        try:
            directory = Path(directory)

            if not directory.exists():
                return {
                    "success": False,
                    "error": f"目录不存在: {directory}"
                }

            # 加载并分块所有文档
            chunks = document_loader.load_and_split(
                directory,
                is_directory=True,
                extensions=extensions
            )

            if not chunks:
                return {
                    "success": False,
                    "error": "目录中未找到可加载的文档"
                }

            # 添加到向量库
            added_count = vector_store.add_documents(chunks)

            # 统计源文件数量
            sources = set()
            for chunk in chunks:
                if chunk.metadata.get('source'):
                    sources.add(chunk.metadata['source'])

            logger.info(f"批量添加文档成功: {directory}, 共 {len(sources)} 个文件, {added_count} 个块")
            return {
                "success": True,
                "data": {
                    "directory": str(directory),
                    "files_processed": len(sources),
                    "chunks_added": added_count,
                    "total_chunks": len(chunks)
                }
            }

        except Exception as e:
            logger.error(f"批量添加文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"批量添加文档失败: {str(e)}"
            }

    def delete_document(self, source: str) -> Dict[str, Any]:
        """
        删除指定源文件的所有文档块

        Args:
            source: 源文件名

        Returns:
            操作结果
        """
        try:
            deleted_count = vector_store.delete_by_source(source)

            if deleted_count > 0:
                logger.info(f"删除文档成功: {source}, 共 {deleted_count} 个块")
                return {
                    "success": True,
                    "data": {
                        "source": source,
                        "chunks_deleted": deleted_count
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"未找到源文件: {source}"
                }

        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除文档失败: {str(e)}"
            }

    def list_documents(self) -> Dict[str, Any]:
        """
        列出知识库中所有文档

        Returns:
            文档列表
        """
        try:
            documents = vector_store.list_documents()
            stats = vector_store.get_stats()

            return {
                "success": True,
                "data": {
                    "total": len(documents),
                    "documents": documents,
                    "stats": stats
                }
            }

        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return {
                "success": False,
                "error": f"列出文档失败: {str(e)}"
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息
        """
        try:
            stats = vector_store.get_stats()
            return {
                "success": True,
                "data": stats
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取统计信息失败: {str(e)}"
            }

    def clear_knowledge_base(self) -> Dict[str, Any]:
        """
        清空知识库

        Returns:
            操作结果
        """
        try:
            success = vector_store.clear_collection()
            if success:
                logger.info("知识库已清空")
                return {
                    "success": True,
                    "message": "知识库已清空"
                }
            else:
                return {
                    "success": False,
                    "error": "清空知识库失败"
                }
        except Exception as e:
            logger.error(f"清空知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"清空知识库失败: {str(e)}"
            }

    # ==================== 检索功能 ====================

    def query(
            self,
            query_text: str,
            top_k: int = 3,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        纯检索（不生成），用于调试和评估

        Args:
            query_text: 查询文本
            top_k: 返回的文档数量
            filter_metadata: 元数据过滤条件

        Returns:
            检索结果
        """
        try:
            if not query_text or not query_text.strip():
                return {
                    "success": False,
                    "error": "查询文本不能为空"
                }

            results = vector_store.query(
                query_text=query_text,
                top_k=top_k,
                filter_metadata=filter_metadata
            )

            logger.debug(f"检索完成: query='{query_text[:50]}...', 结果数={len(results)}")
            return {
                "success": True,
                "data": {
                    "query": query_text,
                    "results": results,
                    "total_results": len(results)
                }
            }

        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return {
                "success": False,
                "error": f"检索失败: {str(e)}"
            }

    # ==================== RAG 增强生成 ====================

    def rag_generate(
            self,
            query: str,
            top_k: int = 3,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            template_name: Optional[str] = None,
            include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        RAG 增强生成

        Args:
            query: 用户查询
            top_k: 检索文档数量
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            template_name: 模板名称（可选，使用指定模板）
            include_sources: 是否在回复中包含来源引用

        Returns:
            包含检索结果和生成回复的字典
        """
        try:
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "查询文本不能为空"
                }

            # 1. 检索相关文档
            logger.info(f"RAG 生成开始: query='{query[:50]}...', top_k={top_k}")
            retrieval_results = vector_store.query(
                query_text=query,
                top_k=top_k
            )

            if not retrieval_results:
                logger.warning("未检索到相关文档，将使用普通生成")
                # 降级为普通生成
                return self._fallback_generate(query, model, temperature, max_tokens)

            # 2. 构建上下文
            context = self._build_context(retrieval_results)
            sources = self._extract_sources(retrieval_results)

            # 3. 构建 Prompt
            if template_name:
                # 使用指定模板
                prompts = self._build_template_prompt(query, context, template_name)
            else:
                # 使用默认 RAG Prompt
                prompts = self._build_default_prompt(query, context)

            # 4. 调用模型生成
            messages = []
            if prompts.get("system"):
                messages.append({
                    "role": "system",
                    "content": prompts["system"]
                })
            messages.append({
                "role": "user",
                "content": prompts["user"]
            })

            response = self.ollama_client.chat(
                messages=messages,
                model=model or self.default_model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            # 5. 后处理（如果指定了模板）
            if template_name:
                response = post_processor.clean_output(response, template_name)

            # 6. 构建返回结果
            result = {
                "success": True,
                "data": {
                    "query": query,
                    "response": response,
                    "sources": sources if include_sources else None,
                    "retrieved_documents": retrieval_results if include_sources else None,
                    "total_retrieved": len(retrieval_results),
                    "template_used": template_name
                }
            }

            logger.info(f"RAG 生成完成: 检索到 {len(retrieval_results)} 个文档")
            return result

        except Exception as e:
            logger.error(f"RAG 生成失败: {str(e)}")
            return {
                "success": False,
                "error": f"RAG 生成失败: {str(e)}"
            }

    def _build_default_prompt(self, query: str, context: str) -> Dict[str, str]:
        """
        构建默认的 RAG Prompt

        Args:
            query: 用户查询
            context: 检索到的文档上下文

        Returns:
            包含 system 和 user prompt 的字典
        """
        system_prompt = """你是一位专业的测试开发工程师，擅长根据业务文档回答测试相关的问题。

请根据提供的文档上下文回答用户的问题。如果上下文中的信息不足以回答问题，请明确告知用户，并基于你的专业知识提供合理的建议。

回答要求：
1. 优先引用文档中的信息，确保回答准确
2. 如果文档信息不足，可以结合专业知识补充，但要明确说明
3. 回答要结构化、清晰、易于理解
4. 涉及技术细节时，提供具体的步骤或示例
"""

        user_prompt = f"""## 文档上下文
{context}

## 用户问题
{query}

请基于以上文档上下文回答问题。如果文档信息不足，请说明并给出建议。"""

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def _build_template_prompt(self, query: str, context: str, template_name: str) -> Dict[str, str]:
        """
        使用指定模板构建 Prompt

        Args:
            query: 用户查询
            context: 检索到的文档上下文
            template_name: 模板名称

        Returns:
            包含 system 和 user prompt 的字典
        """
        # 获取模板
        template = prompt_service.get_template(template_name)
        if not template:
            logger.warning(f"模板不存在: {template_name}, 使用默认 Prompt")
            return self._build_default_prompt(query, context)

        # 获取模板的 system prompt
        system_prompt = template.get_system_prompt()

        # 构建增强的 user prompt（包含上下文）
        user_prompt = f"""## 文档上下文（请参考以下业务文档）
{context}

## 用户需求
{query}

请根据以上文档上下文生成符合业务规范的内容。如果文档信息不足，请结合专业知识补充。"""

        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def _build_context(self, retrieval_results: List[Dict[str, Any]]) -> str:
        """
        构建上下文文本

        Args:
            retrieval_results: 检索结果列表

        Returns:
            拼接的上下文文本
        """
        context_parts = []
        for idx, result in enumerate(retrieval_results, 1):
            source = result.get('metadata', {}).get('source', '未知来源')
            document = result.get('document', '')
            score = result.get('score', 0)

            part = f"【文档 {idx}】来源: {source} (相关度: {score:.2%})\n{document}\n"
            context_parts.append(part)

        return "\n---\n".join(context_parts)

    def _extract_sources(self, retrieval_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取来源信息

        Args:
            retrieval_results: 检索结果列表

        Returns:
            来源信息列表
        """
        sources = []
        seen = set()

        for result in retrieval_results:
            metadata = result.get('metadata', {})
            source = metadata.get('source', '未知来源')

            # 去重
            if source in seen:
                continue
            seen.add(source)

            sources.append({
                "source": source,
                "score": result.get('score', 0),
                "file_type": metadata.get('file_type', 'unknown')
            })

        return sources

    def _fallback_generate(
            self,
            query: str,
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        降级生成（无检索结果时使用）

        Args:
            query: 用户查询
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            生成结果
        """
        logger.info(f"使用降级生成: query='{query[:50]}...'")

        messages = [{
            "role": "user",
            "content": f"请回答以下问题（注意：知识库中未找到相关文档）：\n\n{query}"
        }]

        response = self.ollama_client.chat(
            messages=messages,
            model=model or self.default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        return {
            "success": True,
            "data": {
                "query": query,
                "response": f"[未检索到相关文档]\n\n{response}",
                "sources": [],
                "retrieved_documents": [],
                "total_retrieved": 0,
                "template_used": None,
                "is_fallback": True
            }
        }


# 创建全局单例实例
rag_service = RAGService()