"""
Pytest 代码生成模板
根据函数描述生成可执行的 Pytest 测试代码
"""

from typing import List
from .base import BaseTemplate


class PytestGeneratorTemplate(BaseTemplate):
    """Pytest 代码生成模板"""

    name = "pytest_generator"
    label = "🧪 Pytest 代码生成"
    description = "根据函数描述生成可执行的 Pytest 测试代码"
    placeholder = "请输入函数描述，如：测试用户登录接口，验证正确用户名密码返回 token..."

    def get_system_prompt(self) -> str:
        return """你是一位资深的测试开发工程师，擅长使用 Pytest 编写高质量的自动化测试代码。

                你的任务是根据用户提供的函数描述，生成可执行的 Pytest 测试代码。
                
                ## 代码规范
                1. 使用 pytest 框架
                2. 测试函数命名：test_<功能描述>
                3. 使用 fixture 管理测试前置条件
                4. 使用 requests 库进行 API 测试（如涉及 HTTP）
                5. 使用 assert 进行断言验证
                6. 包含必要的 import 语句
                7. 添加清晰的注释说明
                
                ## 代码结构
                ```python
                import pytest
                import requests
                
                # Fixture 定义（如需要）
                @pytest.fixture
                def ...:
                    ...
                
                # 测试函数
                def test_...():
                    # 准备测试数据
                    # 执行操作
                    # 断言验证
                    
                # 输出要求
                1.只输出Python代码，不要添加额外的解释文字
                2.代码必须包含完整的import语句
                3.代码必须可直接执行(pytest可收集)
                4.使用```python代码块包裹
                """

    def get_user_prompt(self, **kwargs) -> str:
        function_desc = kwargs.get('function_desc','')
        return f"""请根据一下描述生成Pytest测试代码
        
---
{function_desc}
---

请按照代码规范生成完整的Pytest测试代码"""

    def get_required_params(self) -> List[str]:
        return ['function_desc']
