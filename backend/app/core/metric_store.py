"""
指标存储
负责质量指标的持久化存储、查询和趋势分析
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

from app.utils.logger import logger
from config.settings import Config


class MetricStore:
    """
    指标存储类
    使用 JSON 文件持久化存储指标数据
    """

    # 指标类型常量
    METRIC_RETRIEVAL_RATE = "retrieval_recall_rate"
    METRIC_CASE_USABILITY = "case_usability_rate"
    METRIC_CODE_EXECUTABLE = "code_executable_rate"
    METRIC_HALLUCINATION = "hallucination_rate"

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化指标存储

        Args:
            data_dir: 数据存储目录，默认使用 backend/data/metrics
        """
        if data_dir is None:
            self.data_dir = Path(BACKEND_DIR) / "data" / "metrics"
        else:
            self.data_dir = Path(data_dir)

        # 确保持久化目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据文件路径
        self.metrics_file = self.data_dir / "metrics.json"
        self.feedback_file = self.data_dir / "feedback.json"
        self.samples_file = self.data_dir / "samples.json"

        # 初始化数据文件
        self._init_files()

        logger.info(f"指标存储初始化完成: data_dir={self.data_dir}")

    def _init_files(self):
        """初始化数据文件（如果不存在）"""
        for file_path in [self.metrics_file, self.feedback_file, self.samples_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

    def _load_data(self, file_path: Path) -> List[Dict]:
        """从 JSON 文件加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_data(self, file_path: Path, data: List[Dict]):
        """保存数据到 JSON 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 指标管理 ====================

    def save_metric(
            self,
            metric_type: str,
            value: float,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存单个指标

        Args:
            metric_type: 指标类型
            value: 指标值（百分比或分数）
            metadata: 附加元数据（样本数、模板名称等）

        Returns:
            保存的指标记录
        """
        metrics = self._load_data(self.metrics_file)

        record = {
            "id": f"metric_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now().isoformat(),
            "metric_type": metric_type,
            "value": value,
            "metadata": metadata or {}
        }

        metrics.append(record)
        self._save_data(self.metrics_file, metrics)

        logger.info(f"保存指标: {metric_type}={value}, metadata={metadata}")
        return record

    def save_evaluation_result(
            self,
            metric_type: str,
            total: int,
            passed: int,
            failed: int,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存评估结果（自动计算通过率）

        Args:
            metric_type: 指标类型
            total: 总样本数
            passed: 通过数
            failed: 失败数
            metadata: 附加元数据

        Returns:
            保存的指标记录
        """
        rate = (passed / total * 100) if total > 0 else 0

        metadata = metadata or {}
        metadata.update({
            "total_samples": total,
            "passed": passed,
            "failed": failed
        })

        return self.save_metric(metric_type, rate, metadata)

    def get_metrics(
            self,
            metric_type: Optional[str] = None,
            limit: int = 100,
            days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        查询指标

        Args:
            metric_type: 指标类型，不传则返回所有类型
            limit: 返回数量限制
            days: 只返回最近 N 天的数据

        Returns:
            指标记录列表
        """
        metrics = self._load_data(self.metrics_file)

        # 按时间过滤
        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            metrics = [
                m for m in metrics
                if datetime.fromisoformat(m['timestamp']) >= cutoff
            ]

        # 按类型过滤
        if metric_type:
            metrics = [m for m in metrics if m['metric_type'] == metric_type]

        # 按时间倒序排序，取最近的数据
        metrics.sort(key=lambda x: x['timestamp'], reverse=True)
        return metrics[:limit]

    def get_latest_metric(self, metric_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定类型的最新指标

        Args:
            metric_type: 指标类型

        Returns:
            最新的指标记录，不存在则返回 None
        """
        metrics = self.get_metrics(metric_type=metric_type, limit=1)
        return metrics[0] if metrics else None

    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        获取所有类型的最新指标

        Returns:
            各类型最新指标的字典
        """
        metric_types = [
            self.METRIC_RETRIEVAL_RATE,
            self.METRIC_CASE_USABILITY,
            self.METRIC_CODE_EXECUTABLE,
            self.METRIC_HALLUCINATION
        ]

        result = {}
        for metric_type in metric_types:
            latest = self.get_latest_metric(metric_type)
            if latest:
                result[metric_type] = latest
            else:
                result[metric_type] = None

        return result

    def get_trend(
            self,
            metric_type: str,
            days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取指标趋势数据（按天聚合）

        Args:
            metric_type: 指标类型
            days: 天数

        Returns:
            趋势数据列表，每个元素包含 date 和 value
        """
        metrics = self.get_metrics(
            metric_type=metric_type,
            days=days,
            limit=1000
        )

        if not metrics:
            return []

        # 按天聚合
        daily_data = {}
        for m in metrics:
            date_key = datetime.fromisoformat(m['timestamp']).date().isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(m['value'])

        # 计算每天的平均值
        trend = []
        for date_key in sorted(daily_data.keys()):
            values = daily_data[date_key]
            avg_value = sum(values) / len(values)
            trend.append({
                "date": date_key,
                "value": round(avg_value, 2),
                "count": len(values)
            })

        return trend

    def get_all_metrics_stats(self) -> Dict[str, Any]:
        """
        获取所有指标的统计信息

        Returns:
            包含各指标统计信息的字典
        """
        metric_types = [
            self.METRIC_RETRIEVAL_RATE,
            self.METRIC_CASE_USABILITY,
            self.METRIC_CODE_EXECUTABLE,
            self.METRIC_HALLUCINATION
        ]

        stats = {}
        for metric_type in metric_types:
            metrics = self.get_metrics(metric_type=metric_type, limit=100)
            if metrics:
                values = [m['value'] for m in metrics]
                stats[metric_type] = {
                    "latest": metrics[0]['value'],
                    "average": round(sum(values) / len(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "count": len(values)
                }
            else:
                stats[metric_type] = None

        return stats

    # ==================== 反馈管理 ====================

    def save_feedback(
            self,
            generation_id: str,
            scores: Dict[str, int],
            comment: Optional[str] = None,
            annotator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存人工反馈

        Args:
            generation_id: 生成记录 ID
            scores: 评分字典，如 {"usability": 4, "accuracy": 5}
            comment: 评论文本
            annotator: 标注人

        Returns:
            保存的反馈记录
        """
        feedbacks = self._load_data(self.feedback_file)

        record = {
            "id": f"feedback_{uuid.uuid4().hex[:8]}",
            "generation_id": generation_id,
            "timestamp": datetime.now().isoformat(),
            "scores": scores,
            "comment": comment or "",
            "annotator": annotator or "anonymous"
        }

        feedbacks.append(record)
        self._save_data(self.feedback_file, feedbacks)

        logger.info(f"保存反馈: generation_id={generation_id}, scores={scores}")
        return record

    def get_feedbacks(
            self,
            generation_id: Optional[str] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取反馈列表

        Args:
            generation_id: 生成记录 ID，不传则返回所有
            limit: 返回数量限制

        Returns:
            反馈记录列表
        """
        feedbacks = self._load_data(self.feedback_file)

        if generation_id:
            feedbacks = [f for f in feedbacks if f['generation_id'] == generation_id]

        feedbacks.sort(key=lambda x: x['timestamp'], reverse=True)
        return feedbacks[:limit]

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        获取反馈统计信息

        Returns:
            反馈统计
        """
        feedbacks = self._load_data(self.feedback_file)

        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "avg_usability": None,
                "avg_accuracy": None,
                "avg_completeness": None
            }

        # 计算各维度平均分
        usability_scores = [f['scores'].get('usability', 0) for f in feedbacks]
        accuracy_scores = [f['scores'].get('accuracy', 0) for f in feedbacks]
        completeness_scores = [f['scores'].get('completeness', 0) for f in feedbacks]

        return {
            "total_feedbacks": len(feedbacks),
            "avg_usability": round(sum(usability_scores) / len(usability_scores), 2) if usability_scores else None,
            "avg_accuracy": round(sum(accuracy_scores) / len(accuracy_scores), 2) if accuracy_scores else None,
            "avg_completeness": round(sum(completeness_scores) / len(completeness_scores),
                                      2) if completeness_scores else None
        }

    # ==================== 样本管理 ====================

    def save_sample(
            self,
            sample_type: str,
            data: Dict[str, Any],
            label: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存评估样本

        Args:
            sample_type: 样本类型（rag_relevance, case_usability 等）
            data: 样本数据（查询、生成结果等）
            label: 人工标注结果

        Returns:
            保存的样本记录
        """
        samples = self._load_data(self.samples_file)

        record = {
            "id": f"sample_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now().isoformat(),
            "sample_type": sample_type,
            "data": data,
            "label": label,
            "is_labeled": label is not None
        }

        samples.append(record)
        self._save_data(self.samples_file, samples)

        logger.info(f"保存样本: sample_type={sample_type}, is_labeled={label is not None}")
        return record

    def get_unlabeled_samples(
            self,
            sample_type: Optional[str] = None,
            limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取未标注的样本

        Args:
            sample_type: 样本类型，不传则返回所有类型
            limit: 返回数量限制

        Returns:
            未标注样本列表
        """
        samples = self._load_data(self.samples_file)

        # 过滤已标注
        samples = [s for s in samples if not s.get('is_labeled', False)]

        # 按类型过滤
        if sample_type:
            samples = [s for s in samples if s['sample_type'] == sample_type]

        # 按时间排序（先提交的先标注）
        samples.sort(key=lambda x: x['timestamp'])
        return samples[:limit]

    def label_sample(
            self,
            sample_id: str,
            label: Dict[str, Any],
            annotator: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        标注样本

        Args:
            sample_id: 样本 ID
            label: 标注结果
            annotator: 标注人

        Returns:
            更新后的样本记录，不存在则返回 None
        """
        samples = self._load_data(self.samples_file)

        for idx, sample in enumerate(samples):
            if sample['id'] == sample_id:
                samples[idx]['label'] = label
                samples[idx]['is_labeled'] = True
                samples[idx]['annotator'] = annotator or "anonymous"
                samples[idx]['labeled_at'] = datetime.now().isoformat()
                self._save_data(self.samples_file, samples)
                logger.info(f"标注样本: sample_id={sample_id}")
                return samples[idx]

        logger.warning(f"样本不存在: sample_id={sample_id}")
        return None

    def get_sample_stats(self) -> Dict[str, Any]:
        """
        获取样本统计信息

        Returns:
            样本统计
        """
        samples = self._load_data(self.samples_file)

        total = len(samples)
        labeled = len([s for s in samples if s.get('is_labeled', False)])
        unlabeled = total - labeled

        # 按类型统计
        type_stats = {}
        for sample in samples:
            sample_type = sample.get('sample_type', 'unknown')
            if sample_type not in type_stats:
                type_stats[sample_type] = {"total": 0, "labeled": 0}
            type_stats[sample_type]["total"] += 1
            if sample.get('is_labeled', False):
                type_stats[sample_type]["labeled"] += 1

        return {
            "total_samples": total,
            "labeled_samples": labeled,
            "unlabeled_samples": unlabeled,
            "by_type": type_stats
        }


# 创建全局单例实例
metric_store = MetricStore()