"""
后处理器
对模型输出进行清洗、提取和格式化
"""

import re
import json
from typing import Optional, Dict, Any
from app.utils.logger import logger


class PostProcessor:
    """
    后处理器类
    提供多种输出清洗和提取方法
    """

    @staticmethod
    def extract_markdown_table(text: str) -> str:
        """
        从文本中提取 Markdown 表格

        Args:
            text: 模型输出的原始文本

        Returns:
            提取的 Markdown 表格，如果未找到则返回原始文本
        """
        if not text:
            return text

        # 查找 Markdown 表格模式
        # 表格由包含 | 的行组成，至少有一行分隔符（|---|---|）
        lines = text.strip().split('\n')
        table_lines = []
        in_table = False

        for line in lines:
            # 检查是否是表格行（包含 | 且不是代码块）
            if '|' in line and not line.strip().startswith('```'):
                # 检查是否是表格分隔符行（如 |---|---|）
                if re.match(r'^\s*\|?\s*[-:]+\s*\|', line):
                    in_table = True
                elif in_table and '|' in line:
                    table_lines.append(line)
                elif in_table and not line.strip():
                    # 空行，表格可能结束
                    if table_lines:
                        break
                elif in_table and '|' not in line:
                    # 非表格行，表格结束
                    break

        # 如果找到了表格行，组装返回
        if table_lines:
            # 确保包含表头分隔符
            result = '\n'.join(table_lines)
            logger.debug(f"提取 Markdown 表格成功，共 {len(table_lines)} 行")
            return result

        # 如果没有找到表格，尝试更宽松的匹配：提取所有包含 | 的行
        all_table_lines = [line for line in text.split('\n') if '|' in line and not line.strip().startswith('```')]
        if all_table_lines:
            logger.debug(f"提取 Markdown 表格（宽松模式），共 {len(all_table_lines)} 行")
            return '\n'.join(all_table_lines)

        logger.warning("未找到 Markdown 表格，返回原始文本")
        return text

    @staticmethod
    def extract_code_block(text: str, language: Optional[str] = None) -> str:
        """
        从文本中提取代码块

        Args:
            text: 模型输出的原始文本
            language: 代码块语言标识（如 'python', 'json'），不指定则提取任意代码块

        Returns:
            提取的代码内容，如果未找到则返回原始文本
        """
        if not text:
            return text

        # 构建正则模式
        if language:
            pattern = rf'```{language}\s*\n(.*?)\n```'
        else:
            pattern = r'```(?:\w+)?\s*\n(.*?)\n```'

        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            # 取第一个匹配的代码块
            code = matches[0].strip()
            logger.debug(f"提取代码块成功，语言: {language or '未指定'}, 长度: {len(code)}")
            return code

        # 如果没有代码块标记，尝试返回原始文本（可能是纯代码）
        if language == 'python' and ('import ' in text or 'def ' in text or 'class ' in text):
            logger.debug("未找到代码块标记，但文本包含 Python 关键字，返回原始文本")
            return text.strip()

        if language == 'json' and text.strip().startswith('{') and text.strip().endswith('}'):
            logger.debug("未找到代码块标记，但文本符合 JSON 格式，返回原始文本")
            return text.strip()

        logger.warning(f"未找到代码块，语言: {language or '未指定'}，返回原始文本")
        return text.strip()

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取并解析 JSON

        Args:
            text: 模型输出的原始文本

        Returns:
            解析后的 JSON 字典，解析失败返回 None
        """
        if not text:
            return None

        # 尝试提取代码块中的 JSON
        code = PostProcessor.extract_code_block(text, 'json')
        if code:
            try:
                return json.loads(code)
            except json.JSONDecodeError:
                pass

        # 尝试从文本中直接提取 JSON 对象
        # 查找 { ... } 结构
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                result = json.loads(match)
                logger.debug("从文本中提取 JSON 成功")
                return result
            except json.JSONDecodeError:
                continue

        logger.warning("未找到有效的 JSON 数据")
        return None

    @staticmethod
    def remove_duplicate_lines(text: str) -> str:
        """
        去除文本中的重复行

        Args:
            text: 原始文本

        Returns:
            去重后的文本
        """
        if not text:
            return text

        lines = text.strip().split('\n')
        seen = set()
        result = []

        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                result.append(line)
            elif not stripped:
                # 保留空行（但不多保留）
                if result and result[-1] != '':
                    result.append(line)

        return '\n'.join(result)

    @staticmethod
    def clean_output(text: str, template_name: str) -> str:
        """
        根据模板类型清洗输出

        Args:
            text: 模型输出的原始文本
            template_name: 模板名称

        Returns:
            清洗后的文本
        """
        if not text:
            return text

        # 移除首尾的空白和多余换行
        text = text.strip()

        # 根据模板类型进行特定清洗
        if template_name == 'testcase_generator':
            # 提取 Markdown 表格
            text = PostProcessor.extract_markdown_table(text)
            # 去重（删除重复的表格行）
            text = PostProcessor.remove_duplicate_lines(text)

        elif template_name == 'pytest_generator':
            # 提取 Python 代码块
            text = PostProcessor.extract_code_block(text, 'python')

        elif template_name == 'mock_generator':
            # 提取 JSON
            json_data = PostProcessor.extract_json(text)
            if json_data:
                text = json.dumps(json_data, ensure_ascii=False, indent=2)
            else:
                # 如果提取失败，尝试提取代码块
                text = PostProcessor.extract_code_block(text, 'json')

        logger.debug(f"清洗输出完成: template={template_name}, output_len={len(text)}")
        return text

    @staticmethod
    def is_valid_pytest_code(code: str) -> bool:
        """
        检查代码是否包含有效的 Pytest 测试函数

        Args:
            code: Python 代码字符串

        Returns:
            是否包含有效的测试函数
        """
        if not code:
            return False

        # 检查是否包含 test_ 函数定义
        has_test_function = bool(re.search(r'def\s+test_\w+\s*\(', code))
        has_import = bool(re.search(r'^import\s+|from\s+\w+\s+import', code, re.MULTILINE))
        has_assert = bool(re.search(r'\bassert\b', code))

        result = has_test_function and has_assert
        logger.debug(
            f"Pytest 代码验证: has_test={has_test_function}, has_import={has_import}, has_assert={has_assert}, result={result}")
        return result

    @staticmethod
    def is_valid_json_structure(text: str) -> bool:
        """
        检查文本是否为有效的 JSON 结构

        Args:
            text: 文本字符串

        Returns:
            是否为有效 JSON
        """
        if not text:
            return False

        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False


# 创建全局单例实例
post_processor = PostProcessor()