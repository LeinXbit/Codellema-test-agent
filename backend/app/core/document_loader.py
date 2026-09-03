"""
文档加载器
负责加载多种格式的文档（MD/TXT），并进行分块处理
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.utils.logger import logger
from config.settings import Config


class DocumentLoader:
    """
    文档加载器类
    负责加载、解析和分块各种格式的文档
    """

    # 支持的文档格式
    SUPPORTED_EXTENSIONS = {
        '.txt': 'text',
        '.md': 'markdown',
        '.markdown': 'markdown',
    }

    def __init__(
            self,
            chunk_size: Optional[int] = None,
            chunk_overlap: Optional[int] = None
    ):
        """
        初始化文档加载器

        Args:
            chunk_size: 分块大小（字符数），默认从配置读取
            chunk_overlap: 分块重叠大小，默认从配置读取
        """
        self.chunk_size = chunk_size or (
            Config.CHUNK_SIZE if hasattr(Config, 'CHUNK_SIZE') else 512
        )
        self.chunk_overlap = chunk_overlap or (
            Config.CHUNK_OVERLAP if hasattr(Config, 'CHUNK_OVERLAP') else 50
        )

        # 初始化文本分块器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            length_function=len,
            keep_separator=False,
        )

        logger.info(f"文档加载器初始化完成: chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap}")

    def load_document(self, file_path: Union[str, Path]) -> List[Document]:
        """
        加载单个文档

        Args:
            file_path: 文件路径

        Returns:
            Document 对象列表（每个文档可能被分成多个 Document）
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 获取文件扩展名
        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"不支持的文件格式: {extension}，将尝试作为纯文本加载")
            extension = '.txt'

        try:
            file_type = self.SUPPORTED_EXTENSIONS.get(extension, 'text')
            logger.info(f"加载文档: {file_path.name} (类型: {file_type})")

            # 根据文件类型选择加载器
            if file_type == 'markdown':
                loader = UnstructuredMarkdownLoader(
                    str(file_path),
                    mode="single",
                    strategy="fast"
                )
            else:
                # 纯文本或未知格式，使用 TextLoader 并指定编码
                loader = TextLoader(
                    str(file_path),
                    encoding='utf-8',
                    autodetect_encoding=True
                )

            documents = loader.load()

            # 为每个文档添加元数据
            for doc in documents:
                doc.metadata['source'] = file_path.name
                doc.metadata['file_path'] = str(file_path)
                doc.metadata['file_type'] = file_type

            logger.info(f"文档加载成功: {file_path.name}, 共 {len(documents)} 个片段")
            return documents

        except Exception as e:
            logger.error(f"加载文档失败 {file_path.name}: {str(e)}")
            raise Exception(f"加载文档失败: {str(e)}")

    def load_documents_from_dir(
            self,
            directory: Union[str, Path],
            extensions: Optional[List[str]] = None
    ) -> List[Document]:
        """
        从目录加载所有支持的文档

        Args:
            directory: 目录路径
            extensions: 允许的扩展名列表，默认使用所有支持的格式

        Returns:
            所有 Document 对象列表
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        if not directory.is_dir():
            raise NotADirectoryError(f"路径不是目录: {directory}")

        # 确定要加载的扩展名
        if extensions is None:
            extensions = list(self.SUPPORTED_EXTENSIONS.keys())
        else:
            extensions = [ext.lower() for ext in extensions]
            # 过滤不支持的扩展名
            extensions = [ext for ext in extensions if ext in self.SUPPORTED_EXTENSIONS]

        # 查找所有匹配的文件
        all_documents = []
        for ext in extensions:
            pattern = f"*{ext}"
            for file_path in directory.glob(pattern):
                try:
                    docs = self.load_document(file_path)
                    all_documents.extend(docs)
                except Exception as e:
                    logger.error(f"跳过文件 {file_path.name}: {str(e)}")

        logger.info(f"从目录加载完成: {directory}, 共 {len(all_documents)} 个文档片段")
        return all_documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档切分为块

        Args:
            documents: Document 对象列表

        Returns:
            分块后的 Document 对象列表
        """
        if not documents:
            logger.warning("文档列表为空，无需分块")
            return []

        try:
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"文档分块完成: {len(documents)} 个文档 -> {len(chunks)} 个块")

            # 为每个块添加块索引元数据
            for idx, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = idx
                chunk.metadata['chunk_total'] = len(chunks)

            return chunks

        except Exception as e:
            logger.error(f"文档分块失败: {str(e)}")
            raise Exception(f"文档分块失败: {str(e)}")

    def load_and_split(
            self,
            file_path_or_dir: Union[str, Path],
            is_directory: bool = False,
            extensions: Optional[List[str]] = None
    ) -> List[Document]:
        """
        一站式加载和分块

        Args:
            file_path_or_dir: 文件或目录路径
            is_directory: 是否为目录
            extensions: 目录模式下的扩展名过滤

        Returns:
            分块后的 Document 对象列表
        """
        if is_directory:
            documents = self.load_documents_from_dir(file_path_or_dir, extensions)
        else:
            documents = self.load_document(file_path_or_dir)

        return self.split_documents(documents)

    def get_chunk_info(self, chunks: List[Document]) -> Dict[str, Any]:
        """
        获取分块信息统计

        Args:
            chunks: 分块后的 Document 列表

        Returns:
            统计信息字典
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "total_characters": 0
            }

        sizes = [len(chunk.page_content) for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(sizes) / len(sizes),
            "min_chunk_size": min(sizes),
            "max_chunk_size": max(sizes),
            "total_characters": sum(sizes)
        }


# 创建全局单例实例
document_loader = DocumentLoader()