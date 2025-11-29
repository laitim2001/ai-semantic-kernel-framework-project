"""
Time Plugin - 日期時間處理
"""
from typing import List
from datetime import datetime, timezone
from semantic_kernel.functions import kernel_function
from ..base import BasePlugin


class TimePlugin(BasePlugin):
    """日期時間處理 Plugin"""

    def __init__(self):
        super().__init__(
            name="TimePlugin",
            description="Date and time utilities"
        )

    def get_functions(self) -> List[str]:
        """取得函數列表"""
        return ["get_current_time", "format_datetime", "get_timestamp"]

    @kernel_function(
        name="get_current_time",
        description="Get current UTC time in ISO format"
    )
    def get_current_time(self) -> str:
        """取得當前 UTC 時間"""
        return datetime.now(timezone.utc).isoformat()

    @kernel_function(
        name="format_datetime",
        description="Format datetime string to specified format"
    )
    def format_datetime(self, dt_string: str, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        格式化日期時間

        Args:
            dt_string: ISO format datetime string
            format_string: Python datetime format string

        Returns:
            Formatted datetime string
        """
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        return dt.strftime(format_string)

    @kernel_function(
        name="get_timestamp",
        description="Get current Unix timestamp"
    )
    def get_timestamp(self) -> int:
        """取得當前 Unix timestamp"""
        return int(datetime.now(timezone.utc).timestamp())
