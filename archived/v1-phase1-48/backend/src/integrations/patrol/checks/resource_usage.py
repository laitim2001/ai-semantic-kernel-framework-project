"""
Resource Usage Check - 資源使用檢查

Sprint 82 - S82-1: 主動巡檢模式
"""

import logging
import os
from typing import Any, Dict, Optional

from ..types import CheckResult, CheckType, PatrolStatus
from .base import BaseCheck

logger = logging.getLogger(__name__)


class ResourceUsageCheck(BaseCheck):
    """
    資源使用檢查

    檢查 CPU、記憶體、磁盤使用情況
    """

    check_type = CheckType.RESOURCE_USAGE
    check_name = "Resource Usage Check"
    description = "Check CPU, memory, and disk usage"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # CPU 閾值
        self.cpu_warning_threshold: float = self.get_config_value("cpu_warning_threshold", 70.0)
        self.cpu_critical_threshold: float = self.get_config_value("cpu_critical_threshold", 90.0)

        # 記憶體閾值
        self.memory_warning_threshold: float = self.get_config_value("memory_warning_threshold", 75.0)
        self.memory_critical_threshold: float = self.get_config_value("memory_critical_threshold", 95.0)

        # 磁盤閾值
        self.disk_warning_threshold: float = self.get_config_value("disk_warning_threshold", 80.0)
        self.disk_critical_threshold: float = self.get_config_value("disk_critical_threshold", 95.0)

        # 檢查路徑
        self.disk_paths: list = self.get_config_value("disk_paths", ["/", "C:\\"])

    async def execute(self) -> CheckResult:
        """執行資源使用檢查"""
        self._start_check()

        try:
            import psutil
        except ImportError:
            return self._warning(
                message="psutil not installed, using mock data",
                details={"error": "psutil module not available"},
            )

        issues: list = []
        warnings: list = []
        metrics: Dict[str, float] = {}

        # CPU 檢查
        cpu_result = self._check_cpu(psutil)
        metrics.update(cpu_result["metrics"])
        if cpu_result["status"] == "critical":
            issues.append(cpu_result["message"])
        elif cpu_result["status"] == "warning":
            warnings.append(cpu_result["message"])

        # 記憶體檢查
        memory_result = self._check_memory(psutil)
        metrics.update(memory_result["metrics"])
        if memory_result["status"] == "critical":
            issues.append(memory_result["message"])
        elif memory_result["status"] == "warning":
            warnings.append(memory_result["message"])

        # 磁盤檢查
        disk_result = self._check_disk(psutil)
        metrics.update(disk_result["metrics"])
        if disk_result["status"] == "critical":
            issues.extend(disk_result.get("issues", []))
        elif disk_result["status"] == "warning":
            warnings.extend(disk_result.get("warnings", []))

        # 彙總結果
        details = {
            "cpu": cpu_result["details"],
            "memory": memory_result["details"],
            "disk": disk_result["details"],
            "thresholds": {
                "cpu_warning": self.cpu_warning_threshold,
                "cpu_critical": self.cpu_critical_threshold,
                "memory_warning": self.memory_warning_threshold,
                "memory_critical": self.memory_critical_threshold,
                "disk_warning": self.disk_warning_threshold,
                "disk_critical": self.disk_critical_threshold,
            },
        }

        if issues:
            return self._critical(
                message=f"Resource critical: {'; '.join(issues)}",
                details=details,
                metrics=metrics,
                errors=issues,
            )
        elif warnings:
            return self._warning(
                message=f"Resource warning: {'; '.join(warnings)}",
                details=details,
                metrics=metrics,
            )
        else:
            return self._healthy(
                message="All resources within normal range",
                details=details,
                metrics=metrics,
            )

    def _check_cpu(self, psutil) -> Dict[str, Any]:
        """檢查 CPU 使用情況"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)

        result = {
            "metrics": {
                "cpu_percent": cpu_percent,
                "cpu_count": float(cpu_count or 0),
                "cpu_count_logical": float(cpu_count_logical or 0),
            },
            "details": {
                "usage_percent": cpu_percent,
                "cores": cpu_count,
                "logical_cores": cpu_count_logical,
            },
        }

        if cpu_percent >= self.cpu_critical_threshold:
            result["status"] = "critical"
            result["message"] = f"CPU usage at {cpu_percent:.1f}%"
        elif cpu_percent >= self.cpu_warning_threshold:
            result["status"] = "warning"
            result["message"] = f"CPU usage at {cpu_percent:.1f}%"
        else:
            result["status"] = "healthy"
            result["message"] = f"CPU usage normal at {cpu_percent:.1f}%"

        return result

    def _check_memory(self, psutil) -> Dict[str, Any]:
        """檢查記憶體使用情況"""
        memory = psutil.virtual_memory()

        result = {
            "metrics": {
                "memory_percent": memory.percent,
                "memory_total_gb": memory.total / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
            },
            "details": {
                "usage_percent": memory.percent,
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
            },
        }

        if memory.percent >= self.memory_critical_threshold:
            result["status"] = "critical"
            result["message"] = f"Memory usage at {memory.percent:.1f}%"
        elif memory.percent >= self.memory_warning_threshold:
            result["status"] = "warning"
            result["message"] = f"Memory usage at {memory.percent:.1f}%"
        else:
            result["status"] = "healthy"
            result["message"] = f"Memory usage normal at {memory.percent:.1f}%"

        return result

    def _check_disk(self, psutil) -> Dict[str, Any]:
        """檢查磁盤使用情況"""
        disk_info: list = []
        issues: list = []
        warnings: list = []
        metrics: Dict[str, float] = {}

        for path in self.disk_paths:
            if not os.path.exists(path):
                continue

            try:
                usage = psutil.disk_usage(path)
                percent = usage.percent

                disk_data = {
                    "path": path,
                    "usage_percent": percent,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                }
                disk_info.append(disk_data)

                safe_path = path.replace("/", "_").replace("\\", "_").replace(":", "")
                metrics[f"disk_{safe_path}_percent"] = percent
                metrics[f"disk_{safe_path}_free_gb"] = usage.free / (1024**3)

                if percent >= self.disk_critical_threshold:
                    issues.append(f"Disk {path} at {percent:.1f}%")
                elif percent >= self.disk_warning_threshold:
                    warnings.append(f"Disk {path} at {percent:.1f}%")

            except Exception as e:
                logger.error(f"Failed to check disk {path}: {e}")

        result = {
            "metrics": metrics,
            "details": {"disks": disk_info},
        }

        if issues:
            result["status"] = "critical"
            result["issues"] = issues
        elif warnings:
            result["status"] = "warning"
            result["warnings"] = warnings
        else:
            result["status"] = "healthy"

        return result
