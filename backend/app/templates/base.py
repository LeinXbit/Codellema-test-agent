"""
模板基类
定义所有 Prompt 模板的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTemplate(ABC):
    """
    Prompt 模板抽象基类

    所有具体模板必须继承此类并实现所有抽象方法
    """

    # 模板元数据（子类必须重写）
    name: str = ""  # 模板唯一标识
    label: str = ""  # 显示名称（含图标）
    description: str = ""  # 模板描述
    placeholder: str = ""  # 输入框占位提示

    def __init__(self):
        """初始化模板"""
        self._validate_metadata()

    def _validate_metadata(self):
        """验证模板元数据是否完整"""
        required = ['name', 'label', 'description', 'placeholder']
        for attr in required:
            if not getattr(self, attr, None):
                raise ValueError(f"模板 {self.__class__.__name__} 缺少 {attr} 属性")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        获取系统提示词（System Prompt）

        定义 AI 的角色、任务目标和输出规范
        """
        pass

    @abstractmethod
    def get_user_prompt(self, **kwargs) -> str:
        """
        获取用户提示词（User Prompt）

        根据输入参数渲染具体的用户指令

        Args:
            **kwargs: 模板所需的参数（如 requirement, function_desc 等）

        Returns:
            渲染后的用户提示词字符串
        """
        pass

    @abstractmethod
    def get_required_params(self) -> list:
        """
        获取模板所需的参数列表

        Returns:
            参数名称列表，如 ['requirement'] 或 ['function_desc']
        """
        pass

    def render(self, **kwargs) -> Dict[str, str]:
        """
        渲染完整的 Prompt

        返回 System Prompt 和 User Prompt 的组合

        Args:
            **kwargs: 模板所需的参数

        Returns:
            {
                "system": "系统提示词",
                "user": "用户提示词"
            }

        Raises:
            ValueError: 缺少必要参数时抛出
        """
        # 验证必要参数
        required = self.get_required_params()
        missing = [p for p in required if p not in kwargs or not kwargs[p]]
        if missing:
            raise ValueError(f"缺少必要参数: {', '.join(missing)}")

        return {
            "system": self.get_system_prompt(),
            "user": self.get_user_prompt(**kwargs)
        }

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取模板元数据

        Returns:
            包含模板名称、标签、描述、占位符的字典
        """
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "placeholder": self.placeholder,
            "required_params": self.get_required_params()
        }