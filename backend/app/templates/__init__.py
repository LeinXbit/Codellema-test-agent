"""
Prompt 模板包
提供各种测试开发场景的 Prompt 模板
"""

from app.templates.base import BaseTemplate
from app.templates.testcase_generator import TestcaseGeneratorTemplate
from app.templates.pytest_generator import PytestGeneratorTemplate
from app.templates.mock_generator import MockGeneratorTemplate

__all__ = [
    'BaseTemplate',
    'TestcaseGeneratorTemplate',
    'PytestGeneratorTemplate',
    'MockGeneratorTemplate',
]