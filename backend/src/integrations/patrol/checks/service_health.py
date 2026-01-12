"""
Service Health Check - 服務健康檢查

Sprint 82 - S82-1: 主動巡檢模式
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from ..types import CheckResult, CheckType, PatrolStatus
from .base import BaseCheck

logger = logging.getLogger(__name__)


class ServiceHealthCheck(BaseCheck):
    """
    服務健康檢查

    檢查指定服務端點的健康狀態
    """

    check_type = CheckType.SERVICE_HEALTH
    check_name = "Service Health Check"
    description = "Check the health status of specified service endpoints"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 配置項
        self.endpoints: List[Dict[str, Any]] = self.get_config_value("endpoints", [])
        self.timeout_seconds: int = self.get_config_value("timeout_seconds", 30)
        self.expected_status_codes: List[int] = self.get_config_value(
            "expected_status_codes", [200]
        )

        # 默認端點（如果未配置）
        if not self.endpoints:
            self.endpoints = [
                {"name": "Backend API", "url": "http://localhost:8000/health"},
                {"name": "Backend Docs", "url": "http://localhost:8000/docs"},
            ]

    async def execute(self) -> CheckResult:
        """執行服務健康檢查"""
        self._start_check()

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        metrics: Dict[str, float] = {}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
        ) as session:
            tasks = [
                self._check_endpoint(session, endpoint)
                for endpoint in self.endpoints
            ]
            endpoint_results = await asyncio.gather(*tasks, return_exceptions=True)

            for endpoint, result in zip(self.endpoints, endpoint_results):
                if isinstance(result, Exception):
                    results.append({
                        "name": endpoint["name"],
                        "url": endpoint["url"],
                        "status": "error",
                        "error": str(result),
                    })
                    errors.append(f"{endpoint['name']}: {str(result)}")
                else:
                    results.append(result)
                    metrics[f"{endpoint['name']}_response_ms"] = result.get(
                        "response_time_ms", 0
                    )

        # 分析結果
        healthy_count = sum(1 for r in results if r.get("status") == "healthy")
        warning_count = sum(1 for r in results if r.get("status") == "warning")
        error_count = sum(1 for r in results if r.get("status") == "error")
        total = len(results)

        # 計算健康比例
        health_ratio = healthy_count / total if total > 0 else 0
        metrics["health_ratio"] = health_ratio
        metrics["healthy_count"] = float(healthy_count)
        metrics["total_endpoints"] = float(total)

        # 確定整體狀態
        details = {
            "endpoints": results,
            "summary": {
                "healthy": healthy_count,
                "warning": warning_count,
                "error": error_count,
                "total": total,
            },
        }

        if error_count > 0 or health_ratio < 0.5:
            return self._critical(
                message=f"Service health critical: {error_count}/{total} endpoints failed",
                details=details,
                metrics=metrics,
                errors=errors,
            )
        elif warning_count > 0 or health_ratio < 0.8:
            return self._warning(
                message=f"Service health warning: {warning_count} endpoints with issues",
                details=details,
                metrics=metrics,
                errors=errors if errors else None,
            )
        else:
            return self._healthy(
                message=f"All {total} endpoints are healthy",
                details=details,
                metrics=metrics,
            )

    async def _check_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """檢查單個端點"""
        name = endpoint.get("name", "Unknown")
        url = endpoint.get("url", "")
        method = endpoint.get("method", "GET").upper()
        expected_codes = endpoint.get("expected_status_codes", self.expected_status_codes)

        import time
        start_time = time.time()

        try:
            async with session.request(method, url) as response:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = response.status

                result = {
                    "name": name,
                    "url": url,
                    "method": method,
                    "status_code": status_code,
                    "response_time_ms": response_time_ms,
                }

                if status_code in expected_codes:
                    if response_time_ms > 5000:  # 超過 5 秒視為警告
                        result["status"] = "warning"
                        result["message"] = "Response time is slow"
                    else:
                        result["status"] = "healthy"
                        result["message"] = "OK"
                else:
                    result["status"] = "error"
                    result["message"] = f"Unexpected status code: {status_code}"

                return result

        except aiohttp.ClientConnectorError as e:
            return {
                "name": name,
                "url": url,
                "method": method,
                "status": "error",
                "error": f"Connection failed: {str(e)}",
                "response_time_ms": (time.time() - start_time) * 1000,
            }
        except asyncio.TimeoutError:
            return {
                "name": name,
                "url": url,
                "method": method,
                "status": "error",
                "error": "Request timed out",
                "response_time_ms": self.timeout_seconds * 1000,
            }
        except Exception as e:
            return {
                "name": name,
                "url": url,
                "method": method,
                "status": "error",
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
            }
