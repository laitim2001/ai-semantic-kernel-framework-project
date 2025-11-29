"""
HTTP Tool for making HTTP requests to external APIs

Supports GET, POST, PUT, PATCH, DELETE methods with headers, query params, and body.
"""
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import httpx

from ..base import ITool, ToolExecutionResult

logger = logging.getLogger(__name__)


class HttpTool(ITool):
    """
    HTTP Tool 實作

    用於調用外部 HTTP APIs,支援所有標準 HTTP 方法
    """

    def __init__(self, timeout: float = 30.0, max_redirects: int = 5):
        """
        初始化 HTTP Tool

        Args:
            timeout: 請求超時時間 (秒)
            max_redirects: 最大重定向次數
        """
        self.timeout = timeout
        self.max_redirects = max_redirects

    @property
    def name(self) -> str:
        return "http"

    @property
    def description(self) -> str:
        return "Make HTTP requests to external APIs (GET, POST, PUT, PATCH, DELETE)"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["method", "url"],
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                    "description": "HTTP method",
                },
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Target URL (must be valid HTTP/HTTPS URL)",
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers (optional)",
                    "additionalProperties": {"type": "string"},
                },
                "query_params": {
                    "type": "object",
                    "description": "URL query parameters (optional)",
                    "additionalProperties": {"type": "string"},
                },
                "body": {
                    "type": "object",
                    "description": "Request body for POST/PUT/PATCH (optional)",
                },
                "json_response": {
                    "type": "boolean",
                    "description": "Parse response as JSON (default: auto-detect)",
                    "default": None,
                },
            },
        }

    async def execute(self, **kwargs) -> ToolExecutionResult:
        """
        執行 HTTP 請求

        Args:
            method: HTTP 方法 (GET, POST, PUT, PATCH, DELETE)
            url: 目標 URL
            headers: HTTP headers (optional)
            query_params: URL query parameters (optional)
            body: Request body (optional)
            json_response: 是否解析 JSON 回應 (optional)

        Returns:
            ToolExecutionResult 包含 HTTP 回應資料
        """
        start_time = datetime.now(timezone.utc)

        method = kwargs.get("method", "GET").upper()
        url = kwargs.get("url")
        headers = kwargs.get("headers", {})
        query_params = kwargs.get("query_params", {})
        body = kwargs.get("body")
        json_response = kwargs.get("json_response")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                max_redirects=self.max_redirects,
                follow_redirects=True,
            ) as client:
                # Make HTTP request
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=body if body else None,
                )

                # Calculate execution time
                execution_time_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )

                # Parse response
                content_type = response.headers.get("content-type", "")
                is_json = "application/json" in content_type

                # Auto-detect JSON or use explicit flag
                if json_response is None:
                    json_response = is_json

                if json_response:
                    try:
                        response_body = response.json()
                    except Exception:
                        response_body = response.text
                else:
                    response_body = response.text

                # Build output
                output = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body,
                    "elapsed_ms": response.elapsed.total_seconds() * 1000,
                }

                logger.info(
                    f"HTTP {method} request to {url} completed with status {response.status_code}"
                )

                return ToolExecutionResult(
                    success=True,
                    output=output,
                    execution_time_ms=execution_time_ms,
                    metadata={
                        "method": method,
                        "url": url,
                        "status_code": response.status_code,
                        "content_type": content_type,
                    },
                )

        except httpx.TimeoutException as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"HTTP request timeout: {url}")

            return ToolExecutionResult(
                success=False,
                output=None,
                error_message=f"Request timeout after {self.timeout}s",
                execution_time_ms=execution_time_ms,
                metadata={"method": method, "url": url, "error_type": "timeout"},
            )

        except httpx.HTTPStatusError as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"HTTP status error: {e.response.status_code} for {url}")

            return ToolExecutionResult(
                success=False,
                output={
                    "status_code": e.response.status_code,
                    "body": e.response.text,
                },
                error_message=f"HTTP {e.response.status_code} error",
                execution_time_ms=execution_time_ms,
                metadata={
                    "method": method,
                    "url": url,
                    "status_code": e.response.status_code,
                    "error_type": "http_error",
                },
            )

        except Exception as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"HTTP request failed: {e}")

            return ToolExecutionResult(
                success=False,
                output=None,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                metadata={"method": method, "url": url, "error_type": "exception"},
            )
