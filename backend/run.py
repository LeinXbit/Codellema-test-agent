"""
应用启动入口
启动 Flask 开发服务器
"""

import sys
from pathlib import Path

# 将 backend 目录添加到 Python 模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from config.settings import Config
from app.utils.logger import logger


def main():
    """
    主函数：创建应用并启动服务
    """
    try:
        # 创建 Flask 应用
        app = create_app()

        # 获取启动配置
        host = Config.HOST
        port = Config.PORT
        debug = Config.DEBUG

        # 打印启动信息
        logger.info("=" * 60)
        logger.info("AI-Test-Workbench 服务启动中...")
        logger.info(f"访问地址: http://{host}:{port}")
        logger.info(f"调试模式: {'开启' if debug else '关闭'}")
        logger.info(f"默认模型: {Config.DEFAULT_MODEL}")
        logger.info(f"Ollama 地址: {Config.OLLAMA_HOST}")
        logger.info("=" * 60)

        # 启动 Flask 服务器
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False  # 关闭自动重载，避免日志重复
        )

    except KeyboardInterrupt:
        logger.info("服务已手动停止")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()