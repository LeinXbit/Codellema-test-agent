"""
日志配置模块
使用 loguru 统一管理应用日志
"""

import sys
from pathlib import Path
from loguru import logger

from config.settings import Config


# 确保日志目录存在
log_file_path = Path(Config.LOG_FILE)
log_file_path.parent.mkdir(parents=True, exist_ok=True)


# 移除默认的 logger 配置
logger.remove()


# 配置控制台输出（带颜色）
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=Config.LOG_LEVEL,
    colorize=True,
)


# 配置文件输出（按天轮转）
logger.add(
    log_file_path,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=Config.LOG_LEVEL,
    rotation="1 day",      # 每天轮转
    retention="30 days",   # 保留30天
    compression="zip",     # 压缩旧日志
    encoding="utf-8",
)


# 导出 logger 实例
__all__ = ["logger"]