"""
Mock 数据生成模板
根据字段描述生成 JSON 格式的测试数据
"""

from typing import List
from .base import BaseTemplate


class MockGeneratorTemplate(BaseTemplate):
    """Mock 数据生成模板"""

    name = "mock_generator"
    label = "🎭 Mock 数据生成"
    description = "根据字段描述生成 JSON 格式测试数据"
    placeholder = "请输入字段描述，如：username(string), password(string), email(string), age(int)..."

    def get_system_prompt(self) -> str:
        return """你是一位资深的测试开发工程师，擅长构造仿真测试数据。

                你的任务是根据用户提供的字段描述，生成 JSON 格式的 Mock 测试数据。
                
                ## 输出规范
                1. 使用 JSON 格式输出
                2. 每个字段生成多种类型的值：
                   - 有效值（正常数据）
                   - 边界值（最大/最小值）
                   - 特殊值（空值、特殊字符等）
                3. 数据应包含以下分类：
                   - valid_data: 有效的测试数据
                   - boundary_data: 边界值测试数据
                   - invalid_data: 异常/无效测试数据
                
                ## 字段类型参考
                - string: 生成有意义的字符串（用户名、邮箱、地址等）
                - int: 生成整数（年龄、ID、数量等）
                - float: 生成浮点数（价格、评分等）
                - boolean: true/false
                - array: 生成数组数据
                - object: 生成嵌套对象
                
                ## 输出格式
                ```json
                {
                    "valid_data": {
                        "field1": "正常值",
                        "field2": 123
                    },
                    "boundary_data": {
                        "field1": "最大值测试",
                        "field2": 999999
                    },
                    "invalid_data": {
                        "field1": "",
                        "field2": -1
                    }
                }
                    
                # 输出要求
                1.只输出JSON数据,不要添加额外的解释文字
                2.确保JSON格式合法
                3.使用```json代码块包裹
                """

    def get_user_prompt(self, **kwargs) -> str:
        fields = kwargs.get('fields','')
        return  f"""请根据以下字段描述生成Mock测试数据
        
---
{fields}
---

请按照输出规范生成完整的JSON测试数据"""

    def get_required_params(self) -> list:
        return ['fields']