"""
API Response Check - API 響應檢查

Sprint 82 - S82-1: 主動巡檢模式
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp

from ..types import CheckResult, CheckType, PatrolStatus
from .base import BaseCheck

logger = logging.getLogger(__name__)


class APIResponseCheck(BaseCheck):
    """
    API 響應檢查

    檢查 API 端點的響應時間和正確性
    """

    check_type = CheckType.API_RESPONSE
    check_name = "API Response Check"
    description = "Check API response times and correctness"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 配置項
        self.api_endpoints: List[Dict[str, Any]] = self.get_config_value("api_endpoints", [])
        self.timeout_seconds: int = self.get_config_value("timeout_seconds", 60)
        self.max_response_time_ms: int = self.get_config_value("max_response_time_ms", 5000)
        self.warning_response_time_ms: int = self.get_config_value("warning_response_time_ms", 2000)

        # 默認端點
        if not self.api_endpoints:
            self.api_endpoints = [
                {
                    "name": "Health Check",
                    "url": "http://localhost:8000/health",
                    "method": "GET",
                    "expected_status": 200,
                },
                {
                    "name": "API Version",
                    "url": "http://localhost:8000/api/v1/",
                    "method": "GET",
                    "expected_status": 200,
                },
            ]

    async def execute(self) -> CheckResult:
        """執行 API 響應檢查"""
        self._start_check()

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        metrics: Dict[str, float] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0,
            "max_response_time_ms": 0,
            "min_response_time_ms": float("inf"),
        }

        response_times: List[float] = []

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
        ) as session:
            tasks = [
                self._check_api(session, endpoint)
                for endpoint in self.api_endpoints
            ]
            api_results = await asyncio.gather(*tasks, return_exceptions=True)

            for endpoint, result in zip(self.api_endpoints, api_results):
                metrics["total_requests"] += 1

                if isinstance(result, Exception):
                    results.append({
                        "name": endpoint["name"],
                        "url": endpoint["url"],
                        "status": "error",
                        "error": str(result),
                    })
                    errors.append(f"{endpoint['name']}: {str(result)}")
                    metrics["failed_requests"] += 1
                else:
                    results.append(result)
                    if result.get("status") == "healthy":
                        metrics["successful_requests"] += 1
                    else:
                        metrics["failed_requests"] += 1
                        if result.get("error"):
                            errors.append(f"{endpoint['name']}: {result.get('error')}")

                    response_time = result.get("response_time_ms", 0)
                    response_times.append(response_time)
                    metrics["max_response_time_ms"] = max(
                        metrics["max_response_time_ms"],
                        response_time
                    )
                    metrics["min_response_time_ms"] = min(
                        metrics["min_response_time_ms"],
                        response_time
                    )

        # 計算平均響應時間
        if response_times:
            metrics["avg_response_time_ms"] = sum(response_times) / len(response_times)
        if metrics["min_response_time_ms"] == float("inf"):
            metrics["min_response_time_ms"] = 0

        # 計算成功率
        success_rate = (
            metrics["successful_requests"] / metrics["total_requests"]
            if metrics["total_requests"] > 0
            else 0
        )
        metrics["success_rate"] = success_rate

        # 分析結果
        details = {
            "api_results": results,
            "summary": {
                "total": int(metrics["total_requests"]),
                "successful": int(metrics["successful_requests"]),
                "failed": int(metrics["failed_requests"]),
                "success_rate": f"{success_rate * 100:.1f}%",
            },
            "response_times": {
                "avg_ms": metrics["avg_response_time_ms"],
                "max_ms": metrics["max_response_time_ms"],
                "min_ms": metrics["min_response_time_ms"],
            },
        }

        # 確定整體狀態
        if success_rate < 0.5 or metrics["failed_requests"] > 0:
            return self._critical(
                message=f"API check critical: {int(metrics['failed_requests'])} requests failed",
                details=details,
                metrics=metrics,
                errors=errors,
            )
        elif (
            success_rate < 0.9 or
            metrics["avg_response_time_ms"] > self.max_response_time_ms
        ):
            return self._warning(
                message=f"API check warning: Avg response time {metrics['avg_response_time_ms']:.0f}ms",
                details=details,
                metrics=metrics,
                errors=errors if errors else None,
            )
        else:
            return self._healthy(
                message=f"All {int(metrics['total_requests'])} API calls successful",
                details=details,
                metrics=metrics,
            )

    async def _check_api(
        self,
        session: aiohttp.ClientSession,
        endpoint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """檢查單個 API"""
        name = endpoint.get("name", "Unknown")
        url = endpoint.get("url", "")
        method = endpoint.get("method", "GET").upper()
        expected_status = endpoint.get("expected_status", 200)
        body = endpoint.get("body")
        headers = endpoint.get("headers", {})

        start_time = time.time()

        try:
            kwargs: Dict[str, Any] = {"headers": headers}
            if body and method in ["POST", "PUT", "PATCH"]:
                kwargs["json"] = body

            async with session.request(method, url, **kwargs) as response:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = response.status

                # 嘗試獲取響應體大小
                content = await response.read()
                response_size = len(content)

                result = {
                    "name": name,
                    "url": url,
                    "method": method,
                    "status_code": status_code,
                    "expected_status": expected_status,
                    "response_time_ms": response_time_ms,
                    "response_size_bytes": response_size,
                }

                if status_code == expected_status:
                    if response_time_ms > self.max_response_time_ms:
                        result["status"] = "warning"
                        result["message"] = f"Response time {response_time_ms:.0f}ms exceeds maximum"
                    elif response_time_ms > self.warning_response_time_ms:
                        result["status"] = "warning"
                        result["message"] = f"Response time {response_time_ms:.0f}ms is slow"
                    else:
                        result["status"] = "healthy"
                        result["message"] = "OK"
                else:
                    result["status"] = "error"
                    result["error"] = f"Expected {expected_status}, got {status_code}"

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
