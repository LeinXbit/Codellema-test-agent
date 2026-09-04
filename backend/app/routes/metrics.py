"""
监控路由
提供质量指标的查询、看板数据和报告导出接口
"""
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file

from app.services.evaluation_service import evaluation_service
from app.services.sampling_service import sampling_service
from app.core.metric_store import metric_store
from app.utils.logger import logger

# 创建蓝图
metrics_bp = Blueprint('metrics', __name__)


# ==================== 看板接口 ====================

@metrics_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    获取监控看板数据

    响应:
        {
            "success": true,
            "data": {
                "latest_metrics": {...},
                "trends": {...},
                "metrics_stats": {...},
                "feedback_stats": {...},
                "sampling_stats": {...},
                "rag_stats": {...},
                "template_stats": [...],
                "updated_at": "2026-09-03T10:00:00"
            }
        }
    """
    try:
        result = evaluation_service.get_dashboard_data()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"获取看板数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 指标查询接口 ====================

@metrics_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    获取指标历史数据

    Query 参数:
        metric_type: 指标类型（可选）
        limit: 返回数量（默认 100）
        days: 最近 N 天（可选）

    响应:
        {
            "success": true,
            "data": {
                "metrics": [...],
                "total": 50
            }
        }
    """
    try:
        metric_type = request.args.get('metric_type')
        limit = int(request.args.get('limit', 100))
        days = int(request.args.get('days')) if request.args.get('days') else None

        metrics = metric_store.get_metrics(
            metric_type=metric_type,
            limit=limit,
            days=days
        )

        return jsonify({
            'success': True,
            'data': {
                'metrics': metrics,
                'total': len(metrics)
            }
        }), 200
    except Exception as e:
        logger.error(f"获取指标失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/metrics/latest', methods=['GET'])
def get_latest_metrics():
    """
    获取所有类型的最新指标

    响应:
        {
            "success": true,
            "data": {
                "retrieval_recall_rate": {...},
                "case_usability_rate": {...},
                "code_executable_rate": {...},
                "hallucination_rate": {...}
            }
        }
    """
    try:
        metrics = metric_store.get_latest_metrics()
        return jsonify({
            'success': True,
            'data': metrics
        }), 200
    except Exception as e:
        logger.error(f"获取最新指标失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/metrics/trend', methods=['GET'])
def get_trend():
    """
    获取指标趋势数据

    Query 参数:
        metric_type: 指标类型（必填）
        days: 天数（默认 30）

    响应:
        {
            "success": true,
            "data": {
                "trend": [
                    {"date": "2026-09-01", "value": 78.5},
                    {"date": "2026-09-02", "value": 82.3}
                ],
                "metric_type": "code_executable_rate",
                "days": 30
            }
        }
    """
    try:
        metric_type = request.args.get('metric_type')
        days = int(request.args.get('days', 30))

        if not metric_type:
            return jsonify({
                'success': False,
                'error': '缺少 metric_type 参数'
            }), 400

        trend = metric_store.get_trend(metric_type, days=days)

        return jsonify({
            'success': True,
            'data': {
                'trend': trend,
                'metric_type': metric_type,
                'days': days
            }
        }), 200
    except Exception as e:
        logger.error(f"获取趋势数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/metrics/stats', methods=['GET'])
def get_metrics_stats():
    """
    获取所有指标的统计信息

    响应:
        {
            "success": true,
            "data": {
                "retrieval_recall_rate": {
                    "latest": 82.5,
                    "average": 78.3,
                    "min": 65.0,
                    "max": 85.0,
                    "count": 15
                },
                ...
            }
        }
    """
    try:
        stats = metric_store.get_all_metrics_stats()
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    except Exception as e:
        logger.error(f"获取指标统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 人工反馈接口 ====================

@metrics_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    提交人工反馈

    请求体:
        {
            "generation_id": "gen_001",      # 必填
            "scores": {                      # 必填
                "usability": 4,
                "accuracy": 5,
                "completeness": 3
            },
            "comment": "边界值覆盖不够全面",  # 可选
            "annotator": "tester_01"         # 可选
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400

        generation_id = data.get('generation_id')
        scores = data.get('scores')
        comment = data.get('comment')
        annotator = data.get('annotator')

        if not generation_id:
            return jsonify({
                'success': False,
                'error': '缺少 generation_id'
            }), 400

        if not scores or not isinstance(scores, dict):
            return jsonify({
                'success': False,
                'error': '缺少 scores 或格式不正确'
            }), 400

        result = evaluation_service.record_feedback(
            generation_id=generation_id,
            scores=scores,
            comment=comment,
            annotator=annotator
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"提交反馈失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/feedback', methods=['GET'])
def get_feedbacks():
    """
    获取反馈列表

    Query 参数:
        generation_id: 生成记录 ID（可选）
        limit: 返回数量（默认 100）
    """
    try:
        generation_id = request.args.get('generation_id')
        limit = int(request.args.get('limit', 100))

        feedbacks = metric_store.get_feedbacks(
            generation_id=generation_id,
            limit=limit
        )

        return jsonify({
            'success': True,
            'data': {
                'feedbacks': feedbacks,
                'total': len(feedbacks)
            }
        }), 200
    except Exception as e:
        logger.error(f"获取反馈失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """
    获取反馈统计信息

    响应:
        {
            "success": true,
            "data": {
                "total_feedbacks": 25,
                "avg_usability": 4.2,
                "avg_accuracy": 4.5,
                "avg_completeness": 3.8
            }
        }
    """
    try:
        stats = metric_store.get_feedback_stats()
        return jsonify({
            'success': True,
            'data': stats
        }), 200
    except Exception as e:
        logger.error(f"获取反馈统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 采样管理接口 ====================

@metrics_bp.route('/samples', methods=['GET'])
def get_samples():
    """
    获取待标注样本

    Query 参数:
        sample_type: 样本类型（可选）
        limit: 返回数量（默认 20）
    """
    try:
        sample_type = request.args.get('sample_type')
        limit = int(request.args.get('limit', 20))

        result = sampling_service.get_samples_for_review(
            sample_type=sample_type,
            limit=limit
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"获取样本失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/samples', methods=['POST'])
def submit_sample_review():
    """
    提交样本标注

    请求体:
        {
            "sample_id": "sample_xxx",      # 必填
            "scores": {                     # 必填
                "relevance": 4,
                "usability": 3
            },
            "comment": "相关度较高",          # 可选
            "annotator": "tester_01"         # 可选
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400

        sample_id = data.get('sample_id')
        scores = data.get('scores')
        comment = data.get('comment')
        annotator = data.get('annotator')

        if not sample_id:
            return jsonify({
                'success': False,
                'error': '缺少 sample_id'
            }), 400

        if not scores or not isinstance(scores, dict):
            return jsonify({
                'success': False,
                'error': '缺少 scores 或格式不正确'
            }), 400

        result = sampling_service.submit_sample_review(
            sample_id=sample_id,
            scores=scores,
            comment=comment,
            annotator=annotator
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"提交样本标注失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/samples/stats', methods=['GET'])
def get_sample_stats():
    """
    获取采样统计信息
    """
    try:
        result = sampling_service.get_sampling_stats()
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"获取采样统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 自动评估接口 ====================

@metrics_bp.route('/evaluate/run', methods=['POST'])
def run_evaluation():
    """
    触发自动评估

    请求体（可选）:
        {
            "code_samples": [...],      # 可选，代码样本列表
            "format_samples": [...]     # 可选，格式样本列表
        }
    """
    try:
        data = request.get_json() or {}

        code_samples = data.get('code_samples')
        format_samples = data.get('format_samples')

        result = evaluation_service.run_auto_evaluation(
            code_samples=code_samples,
            format_samples=format_samples
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"运行自动评估失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 报告导出接口 ====================

@metrics_bp.route('/report/export', methods=['GET'])
def export_report():
    """
    导出评估报告

    Query 参数:
        days: 覆盖天数（默认 30）
        format: 导出格式（json/csv），默认 json
    """
    try:
        days = int(request.args.get('days', 30))
        fmt = request.args.get('format', 'json')

        result = evaluation_service.export_report(days=days)

        if not result['success']:
            return jsonify(result), 500

        if fmt == 'csv':
            # 简易 CSV 导出
            import csv
            import io

            report_data = result.get('data', {})
            metrics = report_data.get('metrics', {})

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(['指标类型', '时间', '值'])

            # 写入数据
            for metric_type, records in metrics.items():
                for record in records:
                    writer.writerow([
                        metric_type,
                        record.get('timestamp', ''),
                        record.get('value', '')
                    ])

            # 返回 CSV 文件
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'evaluation_report_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        else:
            # 返回 JSON
            return jsonify(result), 200

    except Exception as e:
        logger.error(f"导出报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
