"""
嵌入客户端
管理嵌入模型的加载、缓存和文本向量化
"""
from typing import List, Union, Optional


from sentence_transformers import SentenceTransformer
import numpy as np

from app.utils.logger import logger
from config.settings import Config


class EmbeddingClient:
    """
    嵌入客户端类
    负责加载嵌入模型，将文本转换为向量
    """

    # 默认模型名称（与方案书一致）
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    # 向量维度
    EMBEDDING_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        """
        初始化嵌入客户端

        Args:
            model_name: 模型名称，默认使用 all-MiniLM-L6-v2
        """
        self.model_name = model_name or Config.EMBEDDING_MODEL if hasattr(Config,
                                                                          'EMBEDDING_MODEL') else self.DEFAULT_MODEL
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """
        加载嵌入模型
        """
        try:
            logger.info(f"正在加载嵌入模型: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"嵌入模型加载成功: {self.model_name}, 向量维度: {self.get_embedding_dim()}")
        except Exception as e:
            logger.error(f"嵌入模型加载失败: {str(e)}")
            raise Exception(f"加载嵌入模型失败: {str(e)}")

    def get_embedding_dim(self) -> int:
        """
        获取向量维度

        Returns:
            向量维度
        """
        return self.EMBEDDING_DIM

    def embed(self, text: Union[str, List[str]]) -> List[List[float]]:
        """
        将文本转换为向量

        Args:
            text: 单个文本或文本列表

        Returns:
            向量列表，每个向量为浮点数列表
        """
        if not text:
            logger.warning("输入文本为空")
            return []

        if self._model is None:
            raise RuntimeError("嵌入模型未加载")

        try:
            # 统一转为列表处理
            texts = [text] if isinstance(text, str) else text
            # 过滤空字符串
            texts = [t for t in texts if t and t.strip()]

            if not texts:
                logger.warning("过滤后无有效文本")
                return []

            # 调用模型生成向量
            embeddings = self._model.encode(texts, convert_to_numpy=True)

            # 转为 Python list 格式
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()

            # 如果输入是单个字符串，返回单个向量而非列表
            if isinstance(text, str):
                return embeddings[0] if embeddings else []

            return embeddings

        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise Exception(f"文本向量化失败: {str(e)}")

    def embed_query(self, query: str) -> List[float]:
        """
        将查询文本转换为向量（便于与 embed() 区分）

        Args:
            query: 查询文本

        Returns:
            查询向量
        """
        return self.embed(query)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        将文档列表批量向量化

        Args:
            documents: 文档文本列表

        Returns:
            向量列表
        """
        return self.embed(documents)

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            包含模型名称和向量维度的字典
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.get_embedding_dim(),
            "is_loaded": self._model is not None
        }


# 创建全局单例实例
embedding_client = EmbeddingClient()