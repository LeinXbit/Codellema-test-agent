"""
对话 API 路由
提供 /api/chat 接口，处理对话请求
支持普通对话和模板生成
"""

from flask import Blueprint, request, jsonify

from app.services.llm_service import LLMService
from app.utils.logger import logger

# 创建蓝图
chat_bp = Blueprint('chat', __name__)

# 初始化 LLM 服务（单例）
llm_service = LLMService()


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    对话接口（支持普通对话和模板生成）

    请求体（普通对话）:
        {
            "message": "用户消息内容",      # 必填
            "session_id": "可选会话ID"      # 可选
        }

    请求体（模板生成）:
        {
            "message": "用户消息内容",       # 必填，作为模板的输入参数
            "session_id": "可选会话ID",      # 可选
            "template": "模板名称",          # 必填（指定模板时）
            "template_params": {            # 可选，覆盖/补充模板参数
                "requirement": "..."        # 具体参数因模板而异
            }
        }

    响应（成功）:
        {
            "success": true,
            "data": {
                "session_id": "xxx",
                "response": "AI 回复内容",
                "template": "模板名称"      # 仅模板生成时返回
            }
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
            template_params=template_params
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


@chat_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    获取所有可用模板列表

    响应:
        {
            "success": true,
            "data": [
                {
                    "name": "testcase_generator",
                    "label": "📋 测试用例生成",
                    "description": "根据需求描述生成结构化测试用例（Markdown 表格）",
                    "placeholder": "请输入需求描述...",
                    "required_params": ["requirement"]
                },
                ...
            ]
        }
    """
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
    """
    获取指定模板的详细信息

    响应:
        {
            "success": true,
            "data": {
                "name": "testcase_generator",
                "label": "📋 测试用例生成",
                "description": "...",
                "placeholder": "...",
                "required_params": ["requirement"],
                "system_prompt": "你是一位资深的测试开发工程师..."
            }
        }
    """
    try:
        from app.services.prompt_service import prompt_service

        metadata = prompt_service.get_template_metadata(template_name)
        if not metadata:
            return jsonify({
                'success': False,
                'error': f'模板 "{template_name}" 不存在'
            }), 404

        # 获取模板实例以获取 system_prompt（用于调试/展示）
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


@chat_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    列出所有会话

    响应:
        {
            "success": true,
            "data": {
                "total": 3,
                "sessions": [...]
            }
        }
    """
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
    """
    获取单个会话详情

    响应:
        {
            "success": true,
            "data": {
                "session_id": "xxx",
                "messages": [...],
                "total_messages": 5
            }
        }
    """
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
    """
    删除会话

    响应:
        {
            "success": true,
            "message": "会话 xxx 已删除"
        }
    """
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
    """
    清空会话消息（保留会话 ID）

    响应:
        {
            "success": true,
            "message": "会话 xxx 已清空"
        }
    """
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