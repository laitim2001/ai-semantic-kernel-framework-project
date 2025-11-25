"""
n8n Client for Outbound Workflow Triggers

Implements outbound n8n workflow triggering functionality.
Sprint 2 - Story S2-2

Features:
- Trigger n8n workflows via webhook
- Get workflow execution status
- Handle errors and retries with exponential backoff
- Audit logging integration
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.audit.service import AuditService
from src.infrastructure.database.models.audit_log import AuditAction

logger = logging.getLogger(__name__)


class N8nClientError(Exception):
    """Base exception for n8n client errors."""
    pass


class N8nConnectionError(N8nClientError):
    """Connection error when reaching n8n."""
    pass


class N8nAPIError(N8nClientError):
    """API error from n8n."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class N8nClient:
    """
    Client for triggering n8n workflows from IPA platform.

    Supports:
    - Webhook-based workflow triggering
    - API-based execution status queries
    - Retry logic with exponential backoff
    - Comprehensive error handling

    Example:
        ```python
        client = N8nClient(db=session)
        result = await client.trigger_workflow(
            workflow_id="my-workflow",
            data={"key": "value"}
        )
        ```
    """

    # Default configuration
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BASE_DELAY = 1.0
    DEFAULT_RETRY_MAX_DELAY = 30.0

    def __init__(
        self,
        db: AsyncSession,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout: float = None,
        max_retries: int = None,
    ):
        """
        Initialize N8n Client.

        Args:
            db: Database session for audit logging
            base_url: n8n base URL (e.g., http://localhost:5678)
            api_key: n8n API key for authenticated requests
            webhook_secret: Shared secret for webhook signatures
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.db = db
        self.base_url = (base_url or os.getenv("N8N_BASE_URL", "http://ipa-n8n:5678")).rstrip("/")
        self.api_key = api_key or os.getenv("N8N_API_KEY", "")
        self.webhook_secret = webhook_secret or os.getenv("N8N_WEBHOOK_SECRET", "")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES

        self.audit_service = AuditService(db)

        # HTTP client with common settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self._get_default_headers(),
        )

    def _get_default_headers(self) -> dict[str, str]:
        """Get default HTTP headers for n8n requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "IPA-Platform/1.0",
        }
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _make_request(
        self,
        method: str,
        url: str,
        json_data: dict = None,
        retry: bool = True,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            json_data: JSON payload for POST/PUT
            retry: Whether to retry on failure

        Returns:
            httpx.Response object

        Raises:
            N8nConnectionError: On network errors
            N8nAPIError: On API errors
        """
        last_exception = None
        retries = self.max_retries if retry else 0

        for attempt in range(retries + 1):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(url)
                elif method.upper() == "POST":
                    response = await self._client.post(url, json=json_data)
                elif method.upper() == "PUT":
                    response = await self._client.put(url, json=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for success
                if response.status_code < 400:
                    return response

                # Handle error responses
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("message", error_detail)
                except:
                    pass

                raise N8nAPIError(
                    f"n8n API error: {error_detail}",
                    status_code=response.status_code,
                    response={"error": error_detail}
                )

            except httpx.ConnectError as e:
                last_exception = N8nConnectionError(f"Failed to connect to n8n: {e}")
            except httpx.TimeoutException as e:
                last_exception = N8nConnectionError(f"Request to n8n timed out: {e}")
            except N8nAPIError:
                raise  # Don't retry on API errors
            except Exception as e:
                last_exception = N8nClientError(f"Unexpected error: {e}")

            # Wait before retry with exponential backoff
            if attempt < retries:
                delay = min(
                    self.DEFAULT_RETRY_BASE_DELAY * (2 ** attempt),
                    self.DEFAULT_RETRY_MAX_DELAY
                )
                logger.warning(
                    f"n8n request failed, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{retries + 1})"
                )
                await asyncio.sleep(delay)

        raise last_exception

    async def trigger_workflow(
        self,
        workflow_id: str,
        data: dict[str, Any] = None,
        webhook_path: Optional[str] = None,
        ipa_workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Trigger an n8n workflow via webhook.

        Args:
            workflow_id: n8n workflow ID or webhook path identifier
            data: Data to pass to the workflow
            webhook_path: Optional custom webhook path
            ipa_workflow_id: IPA workflow ID that triggered this (for audit)
            user_id: User ID who triggered this (for audit)

        Returns:
            Response dictionary with trigger result

        Example:
            ```python
            result = await client.trigger_workflow(
                workflow_id="process-data",
                data={"source": "ipa", "items": [1, 2, 3]}
            )
            print(result["success"])  # True
            ```
        """
        request_id = str(uuid4())
        start_time = datetime.utcnow()

        # Build webhook URL
        if webhook_path:
            url = f"{self.base_url}/webhook/{webhook_path}"
        else:
            url = f"{self.base_url}/webhook/{workflow_id}"

        # Prepare payload
        payload = {
            "source": "ipa-platform",
            "ipa_workflow_id": ipa_workflow_id,
            "request_id": request_id,
            "timestamp": start_time.isoformat(),
            "data": data or {},
        }

        logger.info(f"Triggering n8n workflow: {workflow_id} at {url}")

        try:
            response = await self._make_request("POST", url, json_data=payload)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw": response.text}

            # Log successful trigger
            await self._log_trigger(
                action=AuditAction.WEBHOOK_PROCESSED,
                workflow_id=workflow_id,
                ipa_workflow_id=ipa_workflow_id,
                request_id=request_id,
                success=True,
                duration_ms=duration_ms,
                response_data=response_data,
            )

            return {
                "success": True,
                "status_code": response.status_code,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "n8n_response": response_data,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except N8nClientError as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Log failed trigger
            await self._log_trigger(
                action=AuditAction.WEBHOOK_FAILED,
                workflow_id=workflow_id,
                ipa_workflow_id=ipa_workflow_id,
                request_id=request_id,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )

            return {
                "success": False,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def trigger_workflow_test(
        self,
        workflow_id: str,
        data: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Trigger n8n workflow in test mode (via test webhook endpoint).

        n8n provides test webhook endpoints that are active during
        workflow editing mode.

        Args:
            workflow_id: n8n workflow ID
            data: Test data to send

        Returns:
            Test trigger result
        """
        url = f"{self.base_url}/webhook-test/{workflow_id}"

        try:
            response = await self._make_request(
                "POST", url, json_data=data or {}, retry=False
            )

            return {
                "success": True,
                "test_mode": True,
                "status_code": response.status_code,
                "workflow_id": workflow_id,
                "response": response.json() if response.text else {},
            }
        except Exception as e:
            return {
                "success": False,
                "test_mode": True,
                "workflow_id": workflow_id,
                "error": str(e),
            }

    async def get_workflow_status(
        self,
        execution_id: str,
    ) -> dict[str, Any]:
        """
        Get the status of an n8n workflow execution.

        Note: Requires n8n API access with appropriate permissions.

        Args:
            execution_id: n8n execution ID

        Returns:
            Execution status information
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key required for execution status queries",
            }

        url = f"{self.base_url}/api/v1/executions/{execution_id}"

        try:
            response = await self._make_request("GET", url)
            return {
                "success": True,
                "execution_id": execution_id,
                "data": response.json(),
            }
        except N8nAPIError as e:
            if e.status_code == 404:
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "error": "Execution not found",
                }
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
            }

    async def list_workflows(self) -> dict[str, Any]:
        """
        List available n8n workflows.

        Note: Requires n8n API access with appropriate permissions.

        Returns:
            List of workflows
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key required for workflow listing",
            }

        url = f"{self.base_url}/api/v1/workflows"

        try:
            response = await self._make_request("GET", url)
            data = response.json()
            return {
                "success": True,
                "workflows": data.get("data", []),
                "total": len(data.get("data", [])),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def health_check(self) -> dict[str, Any]:
        """
        Check n8n server health.

        Returns:
            Health check result
        """
        url = f"{self.base_url}/healthz"

        try:
            response = await self._make_request("GET", url, retry=False)
            return {
                "success": True,
                "status": "healthy",
                "n8n_url": self.base_url,
                "status_code": response.status_code,
            }
        except Exception as e:
            return {
                "success": False,
                "status": "unhealthy",
                "n8n_url": self.base_url,
                "error": str(e),
            }

    async def _log_trigger(
        self,
        action: AuditAction,
        workflow_id: str,
        ipa_workflow_id: Optional[str],
        request_id: str,
        success: bool,
        duration_ms: int,
        response_data: dict = None,
        error: str = None,
    ):
        """Log workflow trigger to audit log."""
        try:
            changes = {
                "n8n_workflow_id": workflow_id,
                "ipa_workflow_id": ipa_workflow_id,
                "request_id": request_id,
                "success": success,
                "duration_ms": duration_ms,
            }

            if response_data:
                changes["response"] = response_data
            if error:
                changes["error"] = error

            await self.audit_service.log(
                action=action,
                resource_type="n8n_trigger",
                resource_name=f"n8n-outbound-{workflow_id}",
                changes=changes,
            )
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")


def get_n8n_client(db: AsyncSession) -> N8nClient:
    """
    Factory function to create N8nClient.

    Args:
        db: Database session

    Returns:
        N8nClient instance
    """
    return N8nClient(db=db)
