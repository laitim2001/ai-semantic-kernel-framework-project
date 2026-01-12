"""
Base Check - 巡檢檢查基類

Sprint 82 - S82-1: 主動巡檢模式
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..types import CheckResult, CheckType, PatrolStatus

logger = logging.getLogger(__name__)


class BaseCheck(ABC):
    """
    巡檢檢查項目基類

    所有檢查項目必須繼承此類並實現 execute() 方法
    """

    check_type: CheckType = CheckType.SERVICE_HEALTH
    check_name: str = "Base Check"
    description: str = "Base check class"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._started_at: Optional[datetime] = None
        self._check_id: str = f"check_{uuid4().hex[:12]}"

    @abstractmethod
    async def execute(self) -> CheckResult:
        """
        執行檢查

        子類必須實現此方法

        Returns:
            CheckResult: 檢查結果
        """
        pass

    def _start_check(self) -> datetime:
        """標記檢查開始"""
        self._started_at = datetime.utcnow()
        logger.debug(f"Starting check: {self.check_name} (ID: {self._check_id})")
        return self._started_at

    def _create_result(
        self,
        status: PatrolStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        """
        創建檢查結果

        Args:
            status: 檢查狀態
            message: 結果消息
            details: 詳細信息
            metrics: 度量指標
            errors: 錯誤列表

        Returns:
            CheckResult: 檢查結果
        """
        started_at = self._started_at or datetime.utcnow()
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        result = CheckResult(
            check_id=self._check_id,
            check_type=self.check_type,
            status=status,
            message=message,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            details=details or {},
            metrics=metrics or {},
            errors=errors or [],
        )

        logger.debug(
            f"Check completed: {self.check_name} "
            f"(Status: {status.value}, Duration: {duration_ms}ms)"
        )

        return result

    def _healthy(
        self,
        message: str = "Check passed",
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> CheckResult:
        """創建健康狀態結果"""
        return self._create_result(
            status=PatrolStatus.HEALTHY,
            message=message,
            details=details,
            metrics=metrics,
        )

    def _warning(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        """創建警告狀態結果"""
        return self._create_result(
            status=PatrolStatus.WARNING,
            message=message,
            details=details,
            metrics=metrics,
            errors=errors,
        )

    def _critical(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        """創建嚴重狀態結果"""
        return self._create_result(
            status=PatrolStatus.CRITICAL,
            message=message,
            details=details,
            metrics=metrics,
            errors=errors,
        )

    def _unknown(
        self,
        message: str = "Unable to determine status",
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
    ) -> CheckResult:
        """創建未知狀態結果"""
        return self._create_result(
            status=PatrolStatus.UNKNOWN,
            message=message,
            details=details,
            errors=errors,
        )

    def get_config_value(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """獲取配置值"""
        return self.config.get(key, default)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(check_type={self.check_type.value})"
