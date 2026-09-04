"""
Flask 应用工厂
创建和配置 Flask 应用实例
"""

from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config.settings import Config
from app.utils.logger import logger


def create_app():
    """
    应用工厂函数
    创建并配置 Flask 应用实例
    """
    # 获取项目根目录（ai-test-workbench/）
    project_root = Path(__file__).resolve().parent.parent.parent
    frontend_path = project_root / "frontend"

    # 创建 Flask 应用
    app = Flask(
        __name__,
        static_folder=str(frontend_path),
        static_url_path='/static'
    )

    # 加载配置
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['DEBUG'] = Config.DEBUG

    # 启用 CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 注册路由蓝图
    register_blueprints(app)

    # 注册前端路由
    register_frontend_routes(app)

    # 注册错误处理器
    register_error_handlers(app)

    logger.info("Flask 应用创建成功")
    logger.info(f"配置文件加载完成: DEBUG={Config.DEBUG}, HOST={Config.HOST}:{Config.PORT}")
    logger.info(f"前端静态文件目录: {frontend_path}")

    return app


def register_blueprints(app):
    """注册所有路由蓝图"""
    from app.routes.chat import chat_bp
    from app.routes.metrics import metrics_bp

    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(metrics_bp, url_prefix='/api/metrics')

    logger.info("路由蓝图注册完成")

def register_frontend_routes(app):
    """注册前端路由"""
    project_root = Path(__file__).resolve().parent.parent.parent
    frontend_path = project_root / "frontend"

    @app.route('/')
    def index():
        """返回首页"""
        return send_from_directory(str(frontend_path), "index.html")

    @app.route('/<path:path>')
    def static_files(path):
        """返回静态文件（CSS、JS 等）"""
        return send_from_directory(str(frontend_path), path)

    logger.info("前端路由注册完成")


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'success': False,
            'error': '接口不存在，请检查 URL'
        }), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"服务器内部错误: {str(error)}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误，请稍后重试'
        }), 500

    @app.errorhandler(Exception)
    def handle_general_error(error):
        logger.error(f"未捕获的异常: {str(error)}")
        return jsonify({
            'success': False,
            'error': str(error)
        }), 500

    logger.info("错误处理器注册完成")