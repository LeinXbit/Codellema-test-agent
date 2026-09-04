"""
采样服务
管理人工标注样本的生成、获取和标注流程
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

from app.core.metric_store import metric_store
from app.core.auto_evaluator import auto_evaluator
from app.services.rag_service import rag_service
from app.services.prompt_service import prompt_service
from app.utils.logger import logger


class SamplingService:
    """
    采样服务类
    负责管理评估样本的生成、获取和标注
    """

    # 样本类型常量
    SAMPLE_TYPE_RAG_RELEVANCE = "rag_relevance"
    SAMPLE_TYPE_CASE_USABILITY = "case_usability"
    SAMPLE_TYPE_CODE_EXECUTABLE = "code_executable"
    SAMPLE_TYPE_HALLUCINATION = "hallucination"

    def __init__(self):
        """初始化采样服务"""
        self.sample_types = {
            self.SAMPLE_TYPE_RAG_RELEVANCE: {
                "name": "RAG 检索相关性",
                "description": "评估检索到的文档与查询的相关性",
                "score_labels": ["相关", "部分相关", "不相关"],
                "dimensions": ["relevance"]
            },
            self.SAMPLE_TYPE_CASE_USABILITY: {
                "name": "用例可用性",
                "description": "评估生成的测试用例是否可直接使用",
                "score_labels": ["可用", "需修改", "不可用"],
                "dimensions": ["usability", "completeness", "accuracy"]
            },
            self.SAMPLE_TYPE_CODE_EXECUTABLE: {
                "name": "代码可执行性",
                "description": "评估生成的代码是否可执行",
                "score_labels": ["可执行", "不可执行"],
                "dimensions": ["executable"]
            },
            self.SAMPLE_TYPE_HALLUCINATION: {
                "name": "幻觉检测",
                "description": "检测生成内容是否包含与业务规则矛盾的错误信息",
                "score_labels": ["无幻觉", "轻微幻觉", "严重幻觉"],
                "dimensions": ["hallucination_score"]
            }
        }

        logger.info("采样服务初始化完成")

    # ==================== 样本生成 ====================

    def generate_samples_from_rag_queries(
            self,
            queries: List[str],
            top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        从 RAG 查询生成样本

        Args:
            queries: 查询列表
            top_k: 检索文档数量

        Returns:
            生成的样本列表
        """
        samples = []

        for query in queries:
            # 执行检索
            result = rag_service.query(query, top_k=top_k)

            if not result.get('success'):
                logger.warning(f"RAG 查询失败: {query}")
                continue

            data = result.get('data', {})
            results = data.get('results', [])

            # 创建样本
            sample = metric_store.save_sample(
                sample_type=self.SAMPLE_TYPE_RAG_RELEVANCE,
                data={
                    "query": query,
                    "retrieved_docs": [
                        {
                            "source": r.get('metadata', {}).get('source', 'unknown'),
                            "content_preview": r.get('document', '')[:200] + "...",
                            "score": r.get('score', 0)
                        }
                        for r in results
                    ],
                    "total_retrieved": len(results)
                },
                label=None
            )

            samples.append(sample)
            logger.debug(f"生成 RAG 样本: query='{query[:30]}...'")

        logger.info(f"生成 RAG 样本完成: {len(samples)} 个")
        return samples

    def generate_samples_from_generations(
            self,
            generations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        从历史生成记录生成样本

        Args:
            generations: 生成记录列表，每个包含:
                - output: 生成内容
                - template: 使用的模板
                - user_message: 用户消息
                - session_id: 会话 ID（可选）

        Returns:
            生成的样本列表
        """
        samples = []

        for gen in generations:
            output = gen.get('output', '')
            template = gen.get('template', '')
            user_message = gen.get('user_message', '')

            # 确定样本类型
            if template == "testcase_generator":
                sample_type = self.SAMPLE_TYPE_CASE_USABILITY
                # 自动执行格式检查，预填充信息
                format_result = auto_evaluator.check_output_format(output, template)
            elif template == "pytest_generator":
                sample_type = self.SAMPLE_TYPE_CODE_EXECUTABLE
                # 自动执行可执行性检查，预填充信息
                executable_result = auto_evaluator.check_pytest_executable(output)
            elif template == "mock_generator":
                # Mock 生成暂不纳入自动标注体系，可手动标注
                sample_type = self.SAMPLE_TYPE_CASE_USABILITY
                format_result = auto_evaluator.check_output_format(output, template)
            else:
                # 普通对话，暂不采样
                continue

            # 创建样本
            sample = metric_store.save_sample(
                sample_type=sample_type,
                data={
                    "user_message": user_message,
                    "template": template,
                    "output": output,
                    "auto_check": locals().get('format_result', {}) or locals().get('executable_result', {}),
                    "metadata": gen.get('metadata', {})
                },
                label=None
            )

            samples.append(sample)
            logger.debug(f"生成生成样本: template={template}")

        logger.info(f"生成生成样本完成: {len(samples)} 个")
        return samples

    def generate_samples_from_conversations(
            self,
            conversations: List[Dict[str, Any]],
            sample_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        从对话记录生成幻觉检测样本

        Args:
            conversations: 对话记录列表
            sample_count: 采样数量

        Returns:
            生成的样本列表
        """
        samples = []

        # 筛选包含 AI 回复的对话
        for conv in conversations[:sample_count]:
            messages = conv.get('messages', [])
            if not messages:
                continue

            # 获取最后一条 AI 回复
            ai_messages = [m for m in messages if m.get('role') == 'assistant']
            if not ai_messages:
                continue

            last_ai = ai_messages[-1]

            # 获取对应的用户消息
            user_messages = [m for m in messages if m.get('role') == 'user']
            last_user = user_messages[-1] if user_messages else None

            sample = metric_store.save_sample(
                sample_type=self.SAMPLE_TYPE_HALLUCINATION,
                data={
                    "user_message": last_user.get('content', '') if last_user else '',
                    "ai_response": last_ai.get('content', ''),
                    "session_id": conv.get('session_id', ''),
                    "context": messages[-5:] if len(messages) > 5 else messages
                },
                label=None
            )

            samples.append(sample)

        logger.info(f"生成幻觉检测样本完成: {len(samples)} 个")
        return samples

    # ==================== 样本获取 ====================

    def get_samples_for_review(
            self,
            sample_type: Optional[str] = None,
            limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取待标注样本

        Args:
            sample_type: 样本类型，不传则返回所有类型
            limit: 返回数量限制

        Returns:
            包含样本列表和元数据的字典
        """
        samples = metric_store.get_unlabeled_samples(
            sample_type=sample_type,
            limit=limit
        )

        # 为每个样本添加类型元数据
        enriched_samples = []
        for sample in samples:
            sample_type_info = self.sample_types.get(
                sample.get('sample_type', ''),
                {
                    "name": "未知类型",
                    "description": "",
                    "score_labels": [],
                    "dimensions": []
                }
            )

            enriched_samples.append({
                **sample,
                "_type_info": sample_type_info
            })

        return {
            "success": True,
            "data": {
                "total": len(enriched_samples),
                "samples": enriched_samples,
                "available_types": self.get_available_sample_types()
            }
        }

    def get_sample_by_id(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定样本

        Args:
            sample_id: 样本 ID

        Returns:
            样本数据，不存在则返回 None
        """
        # 从存储中获取（目前直接从文件加载，后续可优化）
        import json
        samples_file = Path(BACKEND_DIR) / "data" / "metrics" / "samples.json"
        if not samples_file.exists():
            return None

        with open(samples_file, 'r', encoding='utf-8') as f:
            samples = json.load(f)

        for sample in samples:
            if sample.get('id') == sample_id:
                return sample

        return None

    def get_available_sample_types(self) -> List[Dict[str, Any]]:
        """
        获取可用的样本类型列表

        Returns:
            样本类型信息列表
        """
        return [
            {
                "key": key,
                **info
            }
            for key, info in self.sample_types.items()
        ]

    def get_sampling_stats(self) -> Dict[str, Any]:
        """
        获取采样统计信息

        Returns:
            采样统计
        """
        stats = metric_store.get_sample_stats()

        # 获取反馈统计
        feedback_stats = metric_store.get_feedback_stats()

        return {
            "success": True,
            "data": {
                "sample_stats": stats,
                "feedback_stats": feedback_stats,
                "available_types": self.get_available_sample_types()
            }
        }

    # ==================== 样本标注 ====================

    def submit_sample_review(
            self,
            sample_id: str,
            scores: Dict[str, int],
            comment: Optional[str] = None,
            annotator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交样本标注

        Args:
            sample_id: 样本 ID
            scores: 评分字典
            comment: 评论文本
            annotator: 标注人

        Returns:
            标注结果
        """
        # 获取样本信息
        sample = self.get_sample_by_id(sample_id)
        if not sample:
            return {
                "success": False,
                "error": f"样本不存在: {sample_id}"
            }

        # 验证评分维度
        sample_type = sample.get('sample_type', '')
        type_info = self.sample_types.get(sample_type, {})
        valid_dimensions = type_info.get('dimensions', [])

        # 检查评分维度是否匹配
        for key in scores.keys():
            if key not in valid_dimensions and valid_dimensions:
                logger.warning(f"评分维度 '{key}' 不在样本类型 '{sample_type}' 的维度列表中")

        # 保存标注
        label_result = metric_store.label_sample(
            sample_id=sample_id,
            label={
                "scores": scores,
                "comment": comment or "",
                "annotator": annotator or "anonymous",
                "submitted_at": datetime.now().isoformat()
            }
        )

        if not label_result:
            return {
                "success": False,
                "error": f"标注样本失败: {sample_id}"
            }

        logger.info(f"提交标注: sample_id={sample_id}, scores={scores}")
        return {
            "success": True,
            "data": label_result
        }

    def submit_batch_review(
            self,
            reviews: List[Dict[str, Any]],
            annotator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量提交标注

        Args:
            reviews: 标注列表，每个包含 sample_id, scores, comment
            annotator: 标注人

        Returns:
            批量标注结果
        """
        results = []
        success_count = 0
        failed_count = 0

        for review in reviews:
            sample_id = review.get('sample_id')
            scores = review.get('scores', {})
            comment = review.get('comment')

            if not sample_id or not scores:
                failed_count += 1
                results.append({
                    "sample_id": sample_id,
                    "success": False,
                    "error": "缺少 sample_id 或 scores"
                })
                continue

            result = self.submit_sample_review(
                sample_id=sample_id,
                scores=scores,
                comment=comment,
                annotator=annotator
            )

            if result.get('success'):
                success_count += 1
            else:
                failed_count += 1

            results.append({
                "sample_id": sample_id,
                "success": result.get('success', False),
                "error": result.get('error')
            })

        return {
            "success": True,
            "data": {
                "total": len(reviews),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            }
        }

    # ==================== 样本统计与导出 ====================

    def get_sample_type_stats(self, sample_type: str) -> Dict[str, Any]:
        """
        获取特定类型的样本统计

        Args:
            sample_type: 样本类型

        Returns:
            样本统计
        """
        # 获取该类型的所有样本（包括已标注）
        samples_file = Path(BACKEND_DIR) / "data" / "metrics" / "samples.json"
        if not samples_file.exists():
            return {"total": 0, "labeled": 0, "unlabeled": 0}

        import json
        with open(samples_file, 'r', encoding='utf-8') as f:
            all_samples = json.load(f)

        type_samples = [s for s in all_samples if s.get('sample_type') == sample_type]

        total = len(type_samples)
        labeled = len([s for s in type_samples if s.get('is_labeled', False)])
        unlabeled = total - labeled

        # 计算标注统计
        if labeled > 0:
            # 统计各维度平均分
            score_stats = {}
            for sample in type_samples:
                if sample.get('is_labeled'):
                    label = sample.get('label', {})
                    scores = label.get('scores', {})
                    for key, value in scores.items():
                        if key not in score_stats:
                            score_stats[key] = []
                        score_stats[key].append(value)

            avg_scores = {
                key: round(sum(values) / len(values), 2)
                for key, values in score_stats.items()
            }
        else:
            avg_scores = {}

        return {
            "total": total,
            "labeled": labeled,
            "unlabeled": unlabeled,
            "avg_scores": avg_scores
        }

    def export_samples(
            self,
            sample_type: Optional[str] = None,
            labeled_only: bool = False,
            limit: int = 1000
    ) -> Dict[str, Any]:
        """
        导出样本数据

        Args:
            sample_type: 样本类型
            labeled_only: 是否只导出已标注样本
            limit: 导出数量限制

        Returns:
            导出数据
        """
        samples_file = Path(BACKEND_DIR) / "data" / "metrics" / "samples.json"
        if not samples_file.exists():
            return {
                "success": False,
                "error": "样本数据不存在"
            }

        import json
        with open(samples_file, 'r', encoding='utf-8') as f:
            all_samples = json.load(f)

        # 过滤
        if sample_type:
            all_samples = [s for s in all_samples if s.get('sample_type') == sample_type]

        if labeled_only:
            all_samples = [s for s in all_samples if s.get('is_labeled', False)]

        # 限制数量
        all_samples = all_samples[:limit]

        return {
            "success": True,
            "data": {
                "total": len(all_samples),
                "samples": all_samples,
                "exported_at": datetime.now().isoformat()
            }
        }


# 创建全局单例实例
sampling_service = SamplingService()