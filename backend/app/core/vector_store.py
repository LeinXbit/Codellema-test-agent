"""
向量存储
封装 ChromaDB 的增删改查操作，支持文档的向量化存储和检索
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document

from app.core.embedding_client import embedding_client
from app.core.document_loader import document_loader
from app.utils.logger import logger
from config.settings import Config


class VectorStore:
    """
    向量存储类
    封装 ChromaDB，提供文档的增删改查功能
    """

    # 默认集合名称
    DEFAULT_COLLECTION_NAME = "rag_documents"

    def __init__(
            self,
            persist_dir: Optional[str] = None,
            collection_name: Optional[str] = None
    ):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化目录，默认从配置读取
            collection_name: 集合名称，默认使用 DEFAULT_COLLECTION_NAME
        """
        # 设置持久化目录
        self.persist_dir = persist_dir or (
            Config.CHROMA_PERSIST_DIR if hasattr(Config, 'CHROMA_PERSIST_DIR')
            else str(BACKEND_DIR / "data" / "chroma_db")
        )

        # 确保持久化目录存在
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME

        # 初始化 ChromaDB 客户端（持久化模式）
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(
                anonymized_telemetry=False,  # 禁用匿名数据收集
                allow_reset=True  # 允许重置集合
            )
        )

        # 获取或创建集合
        self.collection = self._get_or_create_collection()

        logger.info(f"向量存储初始化完成: persist_dir={self.persist_dir}, collection={self.collection_name}")
        logger.info(f"当前文档数: {self.collection.count()}")

    def _get_or_create_collection(self) -> chromadb.Collection:
        """
        获取或创建 ChromaDB 集合

        Returns:
            ChromaDB 集合对象
        """
        try:
            # 尝试获取已存在的集合
            collection = self.client.get_collection(self.collection_name)
            logger.info(f"获取已有集合: {self.collection_name}, 文档数: {collection.count()}")
            return collection
        except Exception:
            # 集合不存在，创建新集合
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            logger.info(f"创建新集合: {self.collection_name}")
            return collection

    def add_documents(
            self,
            documents: List[Document],
            batch_size: int = 100
    ) -> int:
        """
        批量添加文档到向量库

        Args:
            documents: Document 对象列表
            batch_size: 批量添加的大小

        Returns:
            成功添加的文档数量
        """
        if not documents:
            logger.warning("文档列表为空，跳过添加")
            return 0

        logger.info(f"开始添加文档: {len(documents)} 个文档")

        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                added = self._add_batch(batch)
                total_added += added
                logger.debug(f"批次 {i // batch_size + 1} 添加成功: {added} 个文档")
            except Exception as e:
                logger.error(f"批次 {i // batch_size + 1} 添加失败: {str(e)}")
                # 继续处理下一批

        logger.info(f"文档添加完成: {total_added} 个文档")
        return total_added

    def _add_batch(self, documents: List[Document]) -> int:
        """
        添加一批文档到向量库

        Args:
            documents: Document 对象列表

        Returns:
            成功添加的文档数量
        """
        if not documents:
            return 0

        # 提取文档内容、元数据和生成 ID
        ids = []
        texts = []
        metadatas = []

        for idx, doc in enumerate(documents):
            # 生成唯一 ID：文件名_块索引_时间戳
            doc_id = f"{doc.metadata.get('source', 'doc')}_{idx}_{hash(doc.page_content) % 1000000}"
            ids.append(doc_id)
            texts.append(doc.page_content)

            # 复制元数据，确保包含 source
            metadata = doc.metadata.copy()
            metadata['doc_id'] = doc_id
            metadatas.append(metadata)

        # 生成向量
        embeddings = embedding_client.embed_documents(texts)

        # 添加到 ChromaDB
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return len(documents)

    def query(
            self,
            query_text: str,
            top_k: int = 3,
            filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相似文档

        Args:
            query_text: 查询文本
            top_k: 返回的文档数量
            filter_metadata: 元数据过滤条件（可选）

        Returns:
            检索结果列表，每个结果包含:
                - id: 文档ID
                - document: 文档内容
                - metadata: 元数据
                - distance: 距离值
                - score: 相似度分数 (0-1, 越高越相似)
        """
        if not query_text or not query_text.strip():
            logger.warning("查询文本为空")
            return []

        try:
            # 生成查询向量
            query_embedding = embedding_client.embed_query(query_text)

            # 执行检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )

            # 格式化结果
            formatted_results = []
            if results and results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # 计算相似度分数（距离转分数，余弦距离范围 0-2）
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    # 余弦相似度：1 - distance/2，范围 0-1
                    score = 1 - (distance / 2) if distance <= 2 else 0

                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i] if results.get('documents') else '',
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                        'distance': distance,
                        'score': round(score, 4)
                    })

            logger.debug(f"检索完成: query='{query_text[:50]}...', 结果数={len(formatted_results)}")
            return formatted_results

        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            raise Exception(f"向量检索失败: {str(e)}")

    def delete_document(self, doc_id: str) -> bool:
        """
        删除指定文档

        Args:
            doc_id: 文档ID

        Returns:
            是否删除成功
        """
        try:
            # 先检查文档是否存在
            existing = self.collection.get(ids=[doc_id])
            if not existing or not existing['ids']:
                logger.warning(f"文档不存在: {doc_id}")
                return False

            self.collection.delete(ids=[doc_id])
            logger.info(f"删除文档: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False

    def delete_by_source(self, source: str) -> int:
        """
        删除指定源文件的所有文档

        Args:
            source: 源文件名

        Returns:
            删除的文档数量
        """
        try:
            # 查询所有匹配的文档
            existing = self.collection.get(where={"source": source})
            if not existing or not existing['ids']:
                logger.warning(f"未找到源文件: {source}")
                return 0

            ids = existing['ids']
            self.collection.delete(ids=ids)
            logger.info(f"删除源文件: {source}, 共 {len(ids)} 个文档")
            return len(ids)

        except Exception as e:
            logger.error(f"删除源文件失败: {str(e)}")
            return 0

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        列出所有文档

        Returns:
            文档摘要列表
        """
        try:
            # 获取所有文档
            all_docs = self.collection.get()
            if not all_docs or not all_docs['ids']:
                return []

            # 按源文件分组去重
            seen_sources = set()
            result = []

            for i, doc_id in enumerate(all_docs['ids']):
                metadata = all_docs['metadatas'][i] if all_docs.get('metadatas') else {}
                source = metadata.get('source', 'unknown')

                if source not in seen_sources:
                    seen_sources.add(source)
                    result.append({
                        'doc_id': doc_id,
                        'source': source,
                        'file_type': metadata.get('file_type', 'unknown'),
                        'chunk_count': all_docs['ids'].count(doc_id),  # 简化统计
                        'metadata': metadata
                    })

            return result

        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息

        Returns:
            统计信息字典
        """
        try:
            count = self.collection.count()

            # 获取部分文档用于统计
            if count > 0:
                sample = self.collection.get(limit=min(100, count))
                sources = set()
                file_types = set()

                if sample and sample.get('metadatas'):
                    for metadata in sample['metadatas']:
                        if metadata.get('source'):
                            sources.add(metadata['source'])
                        if metadata.get('file_type'):
                            file_types.add(metadata['file_type'])

                return {
                    "total_documents": count,
                    "unique_sources": len(sources),
                    "file_types": list(file_types),
                    "persist_dir": self.persist_dir,
                    "collection_name": self.collection_name
                }
            else:
                return {
                    "total_documents": 0,
                    "unique_sources": 0,
                    "file_types": [],
                    "persist_dir": self.persist_dir,
                    "collection_name": self.collection_name
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "total_documents": -1,
                "error": str(e)
            }

    def clear_collection(self) -> bool:
        """
        清空集合

        Returns:
            是否清空成功
        """
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info(f"清空集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return False


# 创建全局单例实例
vector_store = VectorStore()