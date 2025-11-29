"""
Math Plugin - 數學運算
"""
from typing import List
from semantic_kernel.functions import kernel_function
from ..base import BasePlugin


class MathPlugin(BasePlugin):
    """數學運算 Plugin"""

    def __init__(self):
        super().__init__(
            name="MathPlugin",
            description="Basic mathematical operations"
        )

    def get_functions(self) -> List[str]:
        """取得函數列表"""
        return ["add", "subtract", "multiply", "divide", "power"]

    @kernel_function(name="add", description="Add two numbers")
    def add(self, a: float, b: float) -> float:
        """加法"""
        return a + b

    @kernel_function(name="subtract", description="Subtract b from a")
    def subtract(self, a: float, b: float) -> float:
        """減法"""
        return a - b

    @kernel_function(name="multiply", description="Multiply two numbers")
    def multiply(self, a: float, b: float) -> float:
        """乘法"""
        return a * b

    @kernel_function(name="divide", description="Divide a by b")
    def divide(self, a: float, b: float) -> float:
        """除法"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    @kernel_function(name="power", description="Raise a to the power of b")
    def power(self, a: float, b: float) -> float:
        """次方"""
        return a ** b
