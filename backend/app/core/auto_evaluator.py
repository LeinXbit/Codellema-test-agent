"""
自动评估器
提供对 AI 输出质量的自动化检查功能
"""

import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


from app.utils.logger import logger


class AutoEvaluator:
    """
    自动评估器类
    提供代码可执行性检查、格式检查、相关性检查等功能
    """

    # 评估类型常量
    EVAL_CODE_EXECUTABLE = "code_executable"
    EVAL_FORMAT_VALID = "format_valid"
    EVAL_RAG_RELEVANCE = "rag_relevance"

    def __init__(self):
        """初始化自动评估器"""
        logger.info("自动评估器初始化完成")

    # ==================== 代码可执行性检查 ====================

    def check_pytest_executable(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        检查 pytest 代码是否可被 pytest 收集

        Args:
            code: Python 代码字符串
            timeout: 超时时间（秒）

        Returns:
            检查结果:
                - passed: 是否可执行
                - error: 错误信息（如果失败）
                - collected: 收集到的测试数量（如果成功）
                - details: 详细信息
        """
        if not code or not code.strip():
            return {
                "passed": False,
                "error": "代码为空",
                "collected": 0,
                "details": {}
            }

        # 先做快速语法检查（正则匹配）
        syntax_check = self._quick_syntax_check(code)
        if not syntax_check.get('passed', False):
            return {
                "passed": False,
                "error": syntax_check.get('error', '语法检查失败'),
                "collected": 0,
                "details": {"syntax_check": syntax_check}
            }

        # 尝试使用 pytest --collect-only 检查
        return self._run_pytest_collect(code, timeout)

    def _quick_syntax_check(self, code: str) -> Dict[str, Any]:
        """
        快速语法检查（正则匹配）

        Args:
            code: Python 代码字符串

        Returns:
            检查结果
        """
        issues = []

        # 检查是否有测试函数
        test_functions = re.findall(r'def\s+test_\w+\s*\(', code)
        if not test_functions:
            issues.append("未找到 test_ 开头的测试函数")

        # 检查是否有 assert
        has_assert = bool(re.search(r'\bassert\b', code))
        if not has_assert:
            issues.append("未找到 assert 断言语句")

        # 检查 import 语句
        has_import = bool(re.search(r'^(import|from)\s+', code, re.MULTILINE))
        if not has_import:
            issues.append("未找到 import 语句")

        # 检查括号匹配（简单检查）
        if code.count('(') != code.count(')'):
            issues.append("括号不匹配")
        if code.count('[') != code.count(']'):
            issues.append("方括号不匹配")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "test_count": len(test_functions),
            "has_assert": has_assert,
            "has_import": has_import
        }

    def _run_pytest_collect(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        使用 pytest --collect-only 检查代码

        Args:
            code: Python 代码字符串
            timeout: 超时时间

        Returns:
            检查结果
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name

            try:
                # 执行 pytest --collect-only
                result = subprocess.run(
                    ['pytest', temp_file, '--collect-only', '-q', '--disable-warnings'],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                # 解析输出
                output = result.stdout + result.stderr

                # 检查是否成功
                if result.returncode == 0:
                    # 提取测试数量
                    collected_match = re.search(r'collected\s+(\d+)\s+items?', output)
                    collected = int(collected_match.group(1)) if collected_match else 0

                    return {
                        "passed": True,
                        "error": None,
                        "collected": collected,
                        "details": {
                            "return_code": result.returncode,
                            "output": output[:500]  # 截断输出
                        }
                    }
                else:
                    # 提取错误信息
                    error_lines = [line for line in output.split('\n') if line.strip()]
                    error_msg = error_lines[-1] if error_lines else "未知错误"

                    return {
                        "passed": False,
                        "error": error_msg,
                        "collected": 0,
                        "details": {
                            "return_code": result.returncode,
                            "output": output[:500]
                        }
                    }

            finally:
                # 清理临时文件
                try:
                    Path(temp_file).unlink()
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            logger.warning(f"pytest 执行超时: timeout={timeout}s")
            return {
                "passed": False,
                "error": f"执行超时（{timeout}秒）",
                "collected": 0,
                "details": {}
            }
        except FileNotFoundError:
            logger.warning("pytest 未安装，使用快速检查模式")
            # 降级到快速检查
            return self._quick_syntax_check(code)
        except Exception as e:
            logger.error(f"pytest 检查失败: {str(e)}")
            return {
                "passed": False,
                "error": str(e),
                "collected": 0,
                "details": {}
            }

    # ==================== 格式检查 ====================

    def check_output_format(self, output: str, template_name: str) -> Dict[str, Any]:
        """
        检查输出是否符合模板格式要求

        Args:
            output: 模型输出文本
            template_name: 模板名称

        Returns:
            检查结果
        """
        if not output or not output.strip():
            return {
                "passed": False,
                "error": "输出为空",
                "format_type": template_name,
                "details": {}
            }

        if template_name == "testcase_generator":
            return self._check_markdown_table(output)
        elif template_name == "pytest_generator":
            return self._check_pytest_code(output)
        elif template_name == "mock_generator":
            return self._check_json_format(output)
        else:
            return {
                "passed": True,
                "message": "未知模板类型，跳过格式检查",
                "format_type": template_name,
                "details": {}
            }

    def _check_markdown_table(self, output: str) -> Dict[str, Any]:
        """检查 Markdown 表格格式"""
        lines = output.strip().split('\n')

        # 检查是否包含表格行（包含 |）
        table_lines = [line for line in lines if '|' in line]

        if not table_lines:
            return {
                "passed": False,
                "error": "未找到 Markdown 表格（缺少 | 分隔符）",
                "format_type": "markdown_table",
                "details": {"total_lines": len(lines)}
            }

        # 检查是否有表头分隔符
        has_separator = any(
            re.match(r'^\s*\|?\s*[-:]+\s*\|', line) for line in lines
        )

        # 检查用例编号格式
        has_testcase_ids = any(
            re.search(r'TC_\d{3}', line) for line in table_lines
        )

        return {
            "passed": has_separator and has_testcase_ids,
            "error": None if (has_separator and has_testcase_ids) else "表格格式不完整",
            "format_type": "markdown_table",
            "details": {
                "table_rows": len(table_lines),
                "has_separator": has_separator,
                "has_testcase_ids": has_testcase_ids,
                "total_lines": len(lines)
            }
        }

    def _check_pytest_code(self, output: str) -> Dict[str, Any]:
        """检查 Pytest 代码格式"""
        # 使用快速语法检查
        syntax_result = self._quick_syntax_check(output)

        # 检查是否包含代码块标记
        has_code_block = bool(re.search(r'```python', output))

        return {
            "passed": syntax_result.get('passed', False),
            "error": None if syntax_result.get('passed', False) else "代码格式检查失败",
            "format_type": "pytest_code",
            "details": {
                "syntax_check": syntax_result,
                "has_code_block": has_code_block
            }
        }

    def _check_json_format(self, output: str) -> Dict[str, Any]:
        """检查 JSON 格式"""
        # 尝试提取 JSON
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, output, re.DOTALL)

        if not matches:
            return {
                "passed": False,
                "error": "未找到 JSON 数据",
                "format_type": "json",
                "details": {}
            }

        # 尝试解析
        for match in matches:
            try:
                json.loads(match)
                return {
                    "passed": True,
                    "error": None,
                    "format_type": "json",
                    "details": {
                        "json_found": True,
                        "json_length": len(match)
                    }
                }
            except json.JSONDecodeError:
                continue

        return {
            "passed": False,
            "error": "JSON 格式无效",
            "format_type": "json",
            "details": {
                "candidates": len(matches)
            }
        }

    # ==================== RAG 相关性检查 ====================

    def check_rag_relevance(
            self,
            query: str,
            retrieved_docs: List[Dict[str, Any]],
            relevance_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        检查 RAG 检索结果的相关性（需要人工标注验证）

        此方法提供自动化辅助检查，但最终相关性判断仍需人工标注

        Args:
            query: 查询文本
            retrieved_docs: 检索到的文档列表
            relevance_threshold: 相关性阈值（分数低于此值视为不相关）

        Returns:
            检查结果
        """
        if not retrieved_docs:
            return {
                "passed": False,
                "error": "未检索到任何文档",
                "total_retrieved": 0,
                "relevant_count": 0,
                "relevance_rate": 0,
                "details": {}
            }

        # 统计分数高于阈值的文档
        relevant_count = sum(
            1 for doc in retrieved_docs
            if doc.get('score', 0) >= relevance_threshold
        )

        total = len(retrieved_docs)
        relevance_rate = (relevant_count / total * 100) if total > 0 else 0

        # 检查文档来源是否与查询相关（基于关键词匹配，辅助判断）
        keyword_match_rate = self._calculate_keyword_match(query, retrieved_docs)

        return {
            "passed": relevance_rate >= 80,  # 至少 80% 的相关率
            "error": None if relevance_rate >= 80 else f"相关率 {relevance_rate:.1f}% 低于阈值 80%",
            "total_retrieved": total,
            "relevant_count": relevant_count,
            "relevance_rate": round(relevance_rate, 2),
            "keyword_match_rate": round(keyword_match_rate, 2),
            "details": {
                "threshold": relevance_threshold,
                "docs": [
                    {
                        "source": doc.get('metadata', {}).get('source', 'unknown'),
                        "score": doc.get('score', 0),
                        "relevant": doc.get('score', 0) >= relevance_threshold
                    }
                    for doc in retrieved_docs
                ]
            }
        }

    def _calculate_keyword_match(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> float:
        """
        计算查询与检索文档的关键词匹配率

        Args:
            query: 查询文本
            retrieved_docs: 检索到的文档列表

        Returns:
            匹配率（百分比）
        """
        # 提取查询关键词（简单分词）
        query_words = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', query.lower()))
        if not query_words:
            return 0

        # 统计匹配的文档数量
        matched_count = 0
        for doc in retrieved_docs:
            content = doc.get('document', '').lower()
            # 检查是否有任何关键词匹配
            if any(word in content for word in query_words):
                matched_count += 1

        return (matched_count / len(retrieved_docs) * 100) if retrieved_docs else 0

    # ==================== 综合评估 ====================

    def evaluate_code_executable_batch(
            self,
            code_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量评估代码可执行性

        Args:
            code_samples: 代码样本列表，每个包含:
                - code: 代码字符串
                - metadata: 元数据（可选）

        Returns:
            批量评估结果
        """
        total = len(code_samples)
        passed = 0
        failed = 0
        results = []

        for sample in code_samples:
            code = sample.get('code', '')
            result = self.check_pytest_executable(code)

            if result.get('passed', False):
                passed += 1
            else:
                failed += 1

            results.append({
                "sample": sample.get('metadata', {}),
                "result": result
            })

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "results": results
        }

    def evaluate_format_batch(
            self,
            outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量评估输出格式

        Args:
            outputs: 输出样本列表，每个包含:
                - output: 输出文本
                - template: 模板名称
                - metadata: 元数据（可选）

        Returns:
            批量评估结果
        """
        total = len(outputs)
        passed = 0
        failed = 0
        results = []

        for sample in outputs:
            output = sample.get('output', '')
            template = sample.get('template', '')
            result = self.check_output_format(output, template)

            if result.get('passed', False):
                passed += 1
            else:
                failed += 1

            results.append({
                "sample": sample.get('metadata', {}),
                "result": result
            })

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "results": results
        }


# 创建全局单例实例
auto_evaluator = AutoEvaluator()