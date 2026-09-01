"""
Prompt 服务
管理所有 Prompt 模板的注册、查询和渲染
"""

from typing import Dict, Any, Optional, List
from app.templates import (
    BaseTemplate,
    TestcaseGeneratorTemplate,
    PytestGeneratorTemplate,
    MockGeneratorTemplate,
)
from app.utils.logger import logger


class PromptService:
    """
    Prompt 服务类
    负责管理所有模板，提供模板查询和渲染功能
    """

    def __init__(self):
        """初始化 Prompt 服务，注册所有模板"""
        self._templates: Dict[str, BaseTemplate] = {}
        self._register_templates()
        logger.info(f"Prompt 服务初始化完成，已注册 {len(self._templates)} 个模板")

    def _register_templates(self) -> None:
        """
        注册所有可用模板
        新增模板时，在此处添加注册即可
        """
        templates = [
            TestcaseGeneratorTemplate(),
            PytestGeneratorTemplate(),
            MockGeneratorTemplate(),
        ]

        for template in templates:
            self._templates[template.name] = template
            logger.debug(f"注册模板: {template.name}")

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        获取所有可用模板的元数据列表

        Returns:
            模板元数据列表，每个元素包含 name, label, description, placeholder, required_params
        """
        return [
            template.get_metadata()
            for template in self._templates.values()
        ]

    def get_template(self, name: str) -> Optional[BaseTemplate]:
        """
        根据名称获取模板实例

        Args:
            name: 模板名称

        Returns:
            模板实例，不存在则返回 None
        """
        return self._templates.get(name)

    def get_template_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模板的元数据

        Args:
            name: 模板名称

        Returns:
            模板元数据，不存在则返回 None
        """
        template = self.get_template(name)
        if template:
            return template.get_metadata()
        return None

    def render_prompt(self, name: str, **kwargs) -> Optional[Dict[str, str]]:
        """
        渲染指定模板的 Prompt

        Args:
            name: 模板名称
            **kwargs: 模板所需的参数

        Returns:
            {
                "system": "系统提示词",
                "user": "用户提示词"
            }
            模板不存在或渲染失败返回 None

        Raises:
            ValueError: 缺少必要参数时抛出
        """
        template = self.get_template(name)
        if not template:
            logger.warning(f"模板不存在: {name}")
            return None

        try:
            result = template.render(**kwargs)
            logger.debug(f"渲染模板成功: {name}, params={kwargs}")
            return result
        except ValueError as e:
            logger.error(f"渲染模板失败: {name}, 错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"渲染模板异常: {name}, 错误: {str(e)}")
            raise

    def is_valid_template(self, name: str) -> bool:
        """
        检查模板是否存在

        Args:
            name: 模板名称

        Returns:
            模板是否存在
        """
        return name in self._templates

    def get_template_names(self) -> List[str]:
        """
        获取所有模板名称列表

        Returns:
            模板名称列表
        """
        return list(self._templates.keys())


# 创建全局单例实例
prompt_service = PromptService()