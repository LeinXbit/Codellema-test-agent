"""
对话 API 路由
提供 /api/chat 接口，处理对话请求
支持普通对话、模板生成和 RAG 增强生成
"""

import sys
from pathlib import Path

from flask import Blueprint, request, jsonify

from app.services.llm_service import LLMService
from app.services.rag_service import rag_service
from app.utils.logger import logger

# 创建蓝图
chat_bp = Blueprint('chat', __name__)

# 初始化 LLM 服务（单例）
llm_service = LLMService()


# ==================== 对话接口 ====================

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    对话接口（支持普通对话、模板生成和 RAG 增强生成）

    请求体（普通对话）:
        {
            "message": "用户消息内容",      # 必填
            "session_id": "可选会话ID"      # 可选
        }

    请求体（模板生成）:
        {
            "message": "用户消息内容",       # 必填
            "session_id": "可选会话ID",      # 可选
            "template": "模板名称",          # 必填
            "template_params": {}            # 可选
        }

    请求体（RAG 增强生成）:
        {
            "message": "用户消息内容",       # 必填
            "session_id": "可选会话ID",      # 可选
            "rag": true,                     # 必填，启用 RAG
            "rag_top_k": 3,                  # 可选，默认 3
            "template": "可选模板名称"       # 可选，RAG + 模板组合
        }
    """
    try:
        # 1. 解析请求体
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400

        # 2. 获取参数
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        template = data.get('template')
        template_params = data.get('template_params', {})
        rag = data.get('rag', False)
        rag_top_k = data.get('rag_top_k', 3)

        # 3. 验证参数
        if not user_message:
            return jsonify({
                'success': False,
                'error': '消息内容不能为空'
            }), 400

        # 4. 调用服务层处理
        result = llm_service.chat(
            user_message=user_message,
            session_id=session_id,
            template=template,
            template_params=template_params,
            rag=rag,
            rag_top_k=rag_top_k
        )

        # 5. 返回响应
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"对话接口异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500


# ==================== 模板管理接口 ====================

@chat_bp.route('/templates', methods=['GET'])
def list_templates():
    """获取所有可用模板列表"""
    try:
        result = llm_service.list_templates()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/templates/<template_name>', methods=['GET'])
def get_template(template_name):
    """获取指定模板的详细信息"""
    try:
        from app.services.prompt_service import prompt_service

        metadata = prompt_service.get_template_metadata(template_name)
        if not metadata:
            return jsonify({
                'success': False,
                'error': f'模板 "{template_name}" 不存在'
            }), 404

        template = prompt_service.get_template(template_name)
        if template:
            metadata['system_prompt'] = template.get_system_prompt()

        return jsonify({
            'success': True,
            'data': metadata
        }), 200
    except Exception as e:
        logger.error(f"获取模板详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== RAG 管理接口 ====================

@chat_bp.route('/rag/documents', methods=['GET'])
def list_rag_documents():
    """
    列出知识库中所有文档

    响应:
        {
            "success": true,
            "data": {
                "total": 3,
                "documents": [...],
                "stats": {...}
            }
        }
    """
    try:
        result = rag_service.list_documents()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/rag/documents', methods=['POST'])
def upload_rag_document():
    """
    上传文档到知识库

    请求体 (multipart/form-data):
        file: 文档文件
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '请选择要上传的文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400

        # 保存临时文件
        import tempfile
        import os

        # 获取文件扩展名
        ext = os.path.splitext(file.filename)[1].lower()
        supported_exts = ['.txt', '.md', '.markdown']
        if ext not in supported_exts:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {ext}，请使用 {", ".join(supported_exts)}'
            }), 400

        # 保存到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name

        try:
            # 调用 RAG 服务添加文档
            result = rag_service.add_document(tmp_path)

            # 清理临时文件
            os.unlink(tmp_path)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 500

        except Exception as e:
            # 确保清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e

    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'上传文档失败: {str(e)}'
        }), 500


@chat_bp.route('/rag/documents/<source>', methods=['DELETE'])
def delete_rag_document(source):
    """
    删除知识库中的文档

    Args:
        source: 源文件名
    """
    try:
        result = rag_service.delete_document(source)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/rag/stats', methods=['GET'])
def get_rag_stats():
    """
    获取知识库统计信息

    响应:
        {
            "success": true,
            "data": {
                "total_documents": 150,
                "unique_sources": 5,
                "file_types": ["markdown", "text"],
                "persist_dir": "/path/to/chroma_db",
                "collection_name": "rag_documents"
            }
        }
    """
    try:
        result = rag_service.get_stats()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/rag/clear', methods=['POST'])
def clear_rag_knowledge_base():
    """
    清空知识库（危险操作）
    """
    try:
        # 可添加确认机制，这里简化处理
        result = rag_service.clear_knowledge_base()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"清空知识库失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/rag/query', methods=['POST'])
def rag_query():
    """
    纯检索接口（调试用）

    请求体:
        {
            "query": "查询文本",
            "top_k": 3
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400

        query = data.get('query', '').strip()
        top_k = data.get('top_k', 3)

        if not query:
            return jsonify({
                'success': False,
                'error': '查询文本不能为空'
            }), 400

        result = rag_service.query(query, top_k)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"检索接口异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 会话管理接口 ====================

@chat_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """列出所有会话"""
    try:
        result = llm_service.list_sessions()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取单个会话详情"""
    try:
        result = llm_service.get_session_info(session_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"获取会话详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    try:
        result = llm_service.delete_session(session_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/sessions/<session_id>/clear', methods=['POST'])
def clear_session(session_id):
    """清空会话消息（保留会话 ID）"""
    try:
        result = llm_service.clear_session(session_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"清空会话失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500