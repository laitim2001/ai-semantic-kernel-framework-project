"""
Base Plugin Architecture
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from semantic_kernel.functions import kernel_function


class BasePlugin(ABC):
    """
    Plugin 基礎類別

    所有 Plugin 必須繼承此類別並實作必要方法
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_functions(self) -> List[str]:
        """
        取得 Plugin 提供的函數列表

        Returns:
            函數名稱列表
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        取得 Plugin 元資料

        Returns:
            元資料字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "functions": self.get_functions()
        }
