import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# 配置项分类
class Config:
    # 模型配置
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "codeLlama-test")

    # RAG 配置
    CHROMA_PERSIST_DIR = "./data/chroma_db"
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # 生成配置
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2048))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "backend" / "data" / "logs" / "app.log"))

    # 评估配置
    EVAL_SAMPLE_SIZE = 50
    CODE_EXEC_TIMEOUT = 10

    # 应用配置
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    # 会话设置
    MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", 10))