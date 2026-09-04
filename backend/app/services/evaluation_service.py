"""
评估服务
负责质量评估的流程编排、指标计算和看板数据汇总
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

from app.core.metric_store import metric_store
from app.core.auto_evaluator import auto_evaluator
from app.services.sampling_service import sampling_service
from app.services.rag_service import rag_service
from app.utils.logger import logger


class EvaluationService:
    """
    评估服务类
    负责质量评估的流程编排、指标计算和看板数据汇总
    """

    def __init__(self):
        """初始化评估服务"""
        logger.info("评估服务初始化完成")

    # ==================== 自动评估 ====================

    def run_auto_evaluation(
            self,
            code_samples: Optional[List[Dict[str, Any]]] = None,
            format_samples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        运行自动评估

        Args:
            code_samples: 代码样本列表（用于代码可执行率评估）
            format_samples: 格式样本列表（用于格式检查）

        Returns:
            评估结果
        """
        results = {}

        # 1. 代码可执行率评估
        if code_samples:
            code_result = auto_evaluator.evaluate_code_executable_batch(code_samples)
            results['code_executable'] = code_result

            # 保存指标
            if code_result['total'] > 0:
                metric_store.save_evaluation_result(
                    metric_type=metric_store.METRIC_CODE_EXECUTABLE,
                    total=code_result['total'],
                    passed=code_result['passed'],
                    failed=code_result['failed'],
                    metadata={
                        "evaluation_time": datetime.now().isoformat(),
                        "auto": True
                    }
                )
                logger.info(f"代码可执行率评估完成: {code_result['pass_rate']:.1f}%")

        # 2. 格式检查（可用于用例可用率的参考）
        if format_samples:
            format_result = auto_evaluator.evaluate_format_batch(format_samples)
            results['format_check'] = format_result

            # 保存为格式检查指标（作为可用率参考）
            if format_result['total'] > 0:
                metric_store.save_evaluation_result(
                    metric_type="format_pass_rate",
                    total=format_result['total'],
                    passed=format_result['passed'],
                    failed=format_result['failed'],
                    metadata={
                        "evaluation_time": datetime.now().isoformat(),
                        "auto": True,
                        "note": "格式检查（用例可用率参考）"
                    }
                )
                logger.info(f"格式检查完成: {format_result['pass_rate']:.1f}%")

        # 3. RAG 检索相关性评估（需人工标注数据）
        # 从已标注样本中计算
        rag_relevance_result = self._calculate_rag_relevance_from_samples()
        if rag_relevance_result:
            results['rag_relevance'] = rag_relevance_result

        # 4. 幻觉率评估（需人工标注数据）
        hallucination_result = self._calculate_hallucination_from_samples()
        if hallucination_result:
            results['hallucination'] = hallucination_result

        return {
            "success": True,
            "data": results,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_rag_relevance_from_samples(self) -> Optional[Dict[str, Any]]:
        """
        从已标注样本计算 RAG 检索相关性

        Returns:
            相关性统计结果
        """
        # 获取已标注的 RAG 样本
        samples_file = Path(BACKEND_DIR) / "data" / "metrics" / "samples.json"
        if not samples_file.exists():
            return None

        import json
        with open(samples_file, 'r', encoding='utf-8') as f:
            all_samples = json.load(f)

        rag_samples = [
            s for s in all_samples
            if s.get('sample_type') == 'rag_relevance'
               and s.get('is_labeled', False)
        ]

        if not rag_samples:
            logger.info("暂无已标注的 RAG 样本")
            return None

        # 统计相关性
        relevant_count = 0
        partially_count = 0
        irrelevant_count = 0

        for sample in rag_samples:
            label = sample.get('label', {})
            scores = label.get('scores', {})
            relevance = scores.get('relevance', 0)

            if relevance >= 4:
                relevant_count += 1
            elif relevance >= 2:
                partially_count += 1
            else:
                irrelevant_count += 1

        total = len(rag_samples)
        relevance_rate = (relevant_count / total * 100) if total > 0 else 0

        # 保存指标
        metric_store.save_metric(
            metric_type=metric_store.METRIC_RETRIEVAL_RATE,
            value=relevance_rate,
            metadata={
                "total_samples": total,
                "relevant": relevant_count,
                "partially_relevant": partially_count,
                "irrelevant": irrelevant_count,
                "evaluation_time": datetime.now().isoformat()
            }
        )

        logger.info(f"RAG 检索相关性计算完成: {relevance_rate:.1f}%")

        return {
            "total": total,
            "relevant": relevant_count,
            "partially_relevant": partially_count,
            "irrelevant": irrelevant_count,
            "relevance_rate": relevance_rate
        }

    def _calculate_hallucination_from_samples(self) -> Optional[Dict[str, Any]]:
        """
        从已标注样本计算幻觉率

        Returns:
            幻觉统计结果
        """
        samples_file = Path(BACKEND_DIR) / "data" / "metrics" / "samples.json"
        if not samples_file.exists():
            return None

        import json
        with open(samples_file, 'r', encoding='utf-8') as f:
            all_samples = json.load(f)

        hallucination_samples = [
            s for s in all_samples
            if s.get('sample_type') == 'hallucination'
               and s.get('is_labeled', False)
        ]

        if not hallucination_samples:
            logger.info("暂无已标注的幻觉检测样本")
            return None

        # 统计幻觉程度
        none_count = 0  # 无幻觉
        mild_count = 0  # 轻微幻觉
        severe_count = 0  # 严重幻觉

        for sample in hallucination_samples:
            label = sample.get('label', {})
            scores = label.get('scores', {})
            hallucination_score = scores.get('hallucination_score', 0)

            if hallucination_score >= 4:
                none_count += 1
            elif hallucination_score >= 2:
                mild_count += 1
            else:
                severe_count += 1

        total = len(hallucination_samples)
        hallucination_rate = ((mild_count + severe_count) / total * 100) if total > 0 else 0

        # 保存指标（幻觉率越低越好）
        metric_store.save_metric(
            metric_type=metric_store.METRIC_HALLUCINATION,
            value=hallucination_rate,
            metadata={
                "total_samples": total,
                "none": none_count,
                "mild": mild_count,
                "severe": severe_count,
                "evaluation_time": datetime.now().isoformat(),
                "note": "幻觉率越低越好"
            }
        )

        logger.info(f"幻觉率计算完成: {hallucination_rate:.1f}%")

        return {
            "total": total,
            "none": none_count,
            "mild": mild_count,
            "severe": severe_count,
            "hallucination_rate": hallucination_rate
        }

    # ==================== 人工反馈 ====================

    def record_feedback(
            self,
            generation_id: str,
            scores: Dict[str, int],
            comment: Optional[str] = None,
            annotator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录人工反馈

        Args:
            generation_id: 生成记录 ID
            scores: 评分字典
            comment: 评论文本
            annotator: 标注人

        Returns:
            保存结果
        """
        # 保存反馈
        feedback = metric_store.save_feedback(
            generation_id=generation_id,
            scores=scores,
            comment=comment,
            annotator=annotator
        )

        # 更新用例可用率指标（如果反馈来自用例生成）
        # 这里简化处理，实际可根据 generation_id 查询关联模板
        metric_store.save_metric(
            metric_type=metric_store.METRIC_CASE_USABILITY,
            value=(sum(scores.values()) / len(scores) / 5 * 100) if scores else 0,
            metadata={
                "generation_id": generation_id,
                "scores": scores,
                "comment": comment,
                "annotator": annotator or "anonymous"
            }
        )

        logger.info(f"记录反馈: generation_id={generation_id}")

        return {
            "success": True,
            "data": feedback
        }

    # ==================== 看板数据 ====================

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取监控看板数据（所有指标 + 趋势 + 统计）

        Returns:
            看板数据
        """
        # 1. 获取最新指标
        latest_metrics = metric_store.get_latest_metrics()

        # 2. 获取趋势数据（最近 30 天）
        trends = {}
        for metric_type in [
            metric_store.METRIC_RETRIEVAL_RATE,
            metric_store.METRIC_CASE_USABILITY,
            metric_store.METRIC_CODE_EXECUTABLE,
            metric_store.METRIC_HALLUCINATION
        ]:
            trends[metric_type] = metric_store.get_trend(metric_type, days=30)

        # 3. 获取所有指标统计
        metrics_stats = metric_store.get_all_metrics_stats()

        # 4. 获取反馈统计
        feedback_stats = metric_store.get_feedback_stats()

        # 5. 获取采样统计
        sampling_stats = sampling_service.get_sampling_stats()

        # 6. 获取知识库统计
        rag_stats = rag_service.get_stats()

        # 7. 获取模板列表
        template_list = self._get_template_stats()

        return {
            "success": True,
            "data": {
                "latest_metrics": latest_metrics,
                "trends": trends,
                "metrics_stats": metrics_stats,
                "feedback_stats": feedback_stats,
                "sampling_stats": sampling_stats.get('data', {}),
                "rag_stats": rag_stats.get('data', {}),
                "template_stats": template_list,
                "updated_at": datetime.now().isoformat()
            }
        }

    def _get_template_stats(self) -> List[Dict[str, Any]]:
        """
        获取模板使用统计（从生成记录中提取，简化版）

        Returns:
            模板统计列表
        """
        # 从 metric_store 中获取相关指标
        code_metrics = metric_store.get_metrics(
            metric_type=metric_store.METRIC_CODE_EXECUTABLE,
            limit=10
        )

        usability_metrics = metric_store.get_metrics(
            metric_type=metric_store.METRIC_CASE_USABILITY,
            limit=10
        )

        # 构建模板统计（简化版）
        templates = [
            {
                "name": "testcase_generator",
                "label": "📋 测试用例生成",
                "usage_count": len(usability_metrics),
                "latest_rate": usability_metrics[0]['value'] if usability_metrics else None
            },
            {
                "name": "pytest_generator",
                "label": "🧪 Pytest 代码生成",
                "usage_count": len(code_metrics),
                "latest_rate": code_metrics[0]['value'] if code_metrics else None
            },
            {
                "name": "mock_generator",
                "label": "🎭 Mock 数据生成",
                "usage_count": 0,
                "latest_rate": None
            }
        ]

        return templates

    # ==================== 报告导出 ====================

    def export_report(self, days: int = 30) -> Dict[str, Any]:
        """
        导出评估报告

        Args:
            days: 报告覆盖天数

        Returns:
            报告数据
        """
        # 获取指标数据
        metrics = {}
        for metric_type in [
            metric_store.METRIC_RETRIEVAL_RATE,
            metric_store.METRIC_CASE_USABILITY,
            metric_store.METRIC_CODE_EXECUTABLE,
            metric_store.METRIC_HALLUCINATION
        ]:
            metrics[metric_type] = metric_store.get_metrics(
                metric_type=metric_type,
                days=days,
                limit=100
            )

        # 获取反馈
        feedbacks = metric_store.get_feedbacks(limit=100)

        # 获取采样统计
        sampling_stats = sampling_service.get_sampling_stats()

        # 构建报告
        report = {
            "title": "AI-Test-Workbench 质量评估报告",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "days": days,
                "start": (datetime.now() - timedelta(days=days)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "metrics": metrics,
            "feedback": {
                "total": len(feedbacks),
                "latest": feedbacks[:5] if feedbacks else []
            },
            "sampling": sampling_stats.get('data', {}),
            "summary": self._generate_summary(metrics)
        }

        return {
            "success": True,
            "data": report
        }

    def _generate_summary(self, metrics: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        生成报告摘要

        Args:
            metrics: 指标数据

        Returns:
            摘要信息
        """
        summary = {}

        for metric_type, data in metrics.items():
            if not data:
                summary[metric_type] = {
                    "status": "no_data",
                    "latest": None,
                    "trend": "unknown"
                }
                continue

            # 计算趋势（最近 5 条 vs 之前 5 条）
            values = [m['value'] for m in data]
            latest = values[0] if values else 0
            avg = sum(values) / len(values) if values else 0

            # 判断趋势
            if len(values) >= 10:
                recent_avg = sum(values[:5]) / 5
                older_avg = sum(values[5:10]) / 5
                if recent_avg > older_avg * 1.05:
                    trend = "improving"
                elif recent_avg < older_avg * 0.95:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            # 判断状态（基于目标值）
            targets = {
                metric_store.METRIC_RETRIEVAL_RATE: 80,
                metric_store.METRIC_CASE_USABILITY: 70,
                metric_store.METRIC_CODE_EXECUTABLE: 75,
                metric_store.METRIC_HALLUCINATION: 20  # 越低越好
            }
            target = targets.get(metric_type, 70)

            if metric_type == metric_store.METRIC_HALLUCINATION:
                # 幻觉率越低越好
                status = "good" if latest <= target else "needs_improvement"
            else:
                status = "good" if latest >= target else "needs_improvement"

            summary[metric_type] = {
                "latest": latest,
                "average": round(avg, 2),
                "count": len(values),
                "target": target,
                "status": status,
                "trend": trend
            }

        return summary


# 创建全局单例实例
evaluation_service = EvaluationService()