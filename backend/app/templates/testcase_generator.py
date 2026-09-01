"""
测试用例生成模板
根据需求描述生成结构化的测试用例（Markdown 表格格式）
"""

from typing import List
from app.templates.base import BaseTemplate


class TestcaseGeneratorTemplate(BaseTemplate):
    """测试用例生成模板"""

    name = "testcase_generator"
    label = "📋 测试用例生成"
    description = "根据需求描述生成结构化测试用例（Markdown 表格）"
    placeholder = "请输入需求描述，如：用户登录功能需要支持用户名密码登录..."

    def get_system_prompt(self) -> str:
        return """你是一位资深的测试开发工程师，擅长根据需求文档设计全面的测试用例。

                你的任务是根据用户提供的需求描述，生成结构化的测试用例。
                    
                ## 输出规范
                1. 必须使用 Markdown 表格格式输出
                2. 表格必须包含以下列：
                    - **用例编号**：格式为 TC_XXX（XXX 为数字，从 001 开始）
                    - **测试场景**：描述测试的场景/模块
                    - **测试标题**：简洁描述测试点
                    - **前置条件**：执行测试前需要满足的条件
                    - **测试步骤**：详细的操作步骤（用数字序号列出）
                    - **预期结果**：每一步对应的预期结果
                    - **优先级**：P0（核心）/ P1（重要）/ P2（一般）
                    
                3. 用例覆盖范围：
                    - 正常流程（Happy Path）
                    - 异常流程（错误输入、异常情况）
                    - 边界值测试
                    - 权限/安全相关（如适用）
                    
                4. 生成数量：至少 5 条用例，覆盖上述各类场景
                    
                    ## 输出要求
                    - 只输出 Markdown 表格，不要添加额外的解释文字
                    - 确保表格格式正确，列对齐
                    - 用例编号连续递增
                """

    def get_user_prompt(self, **kwargs) -> str:
        requirement = kwargs.get('requirement', '')
        return f"""请根据以下需求描述生成测试用例：

---
{requirement}
---

请按照输出规范生成完整的测试用例表格。"""

    def get_required_params(self) -> List[str]:
        return ['requirement']