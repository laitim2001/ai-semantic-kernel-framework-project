"""n8n Webhook API Schemas.

Pydantic models for n8n webhook request/response validation.

Models:
    - N8nWebhookPayload: Incoming webhook data from n8n
    - N8nWebhookResponse: Response sent back to n8n
    - N8nStatusResponse: Connection status check
    - N8nConfigResponse: n8n configuration
    - N8nConfigUpdate: Configuration update request
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class WebhookAction(str, Enum):
    """Supported webhook actions from n8n."""

    ANALYZE = "analyze"
    CLASSIFY = "classify"
    EXECUTE = "execute"
    QUERY = "query"
    NOTIFY = "notify"


class N8nWebhookPayload(BaseModel):
    """Incoming webhook payload from n8n.

    This is the data structure that n8n sends when triggering
    IPA via HTTP Request node or Webhook node.

    Attributes:
        workflow_id: Source n8n workflow ID
        execution_id: n8n execution ID that triggered this webhook
        action: Requested action type
        data: Business data payload
        callback_url: Optional URL for async result callback
        metadata: Additional metadata from n8n

    Example:
        {
            "workflow_id": "wf-123",
            "execution_id": "exec-456",
            "action": "analyze",
            "data": {"incident_id": "INC001", "description": "Server down"},
            "callback_url": "http://n8n:5678/webhook/ipa-callback"
        }
    """

    workflow_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Source n8n workflow ID",
    )
    execution_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="n8n execution ID",
    )
    action: WebhookAction = Field(
        ...,
        description="Requested action type",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Business data payload",
    )
    callback_url: Optional[str] = Field(
        None,
        description="URL for async result callback to n8n",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from n8n",
    )


class N8nWebhookResponse(BaseModel):
    """Response returned to n8n after processing webhook.

    Attributes:
        success: Whether the request was processed successfully
        request_id: Unique IPA request tracking ID
        action: The action that was performed
        result: Processing result data
        error: Error message if processing failed
        timestamp: Processing timestamp
    """

    success: bool
    request_id: str = Field(..., description="IPA request tracking ID")
    action: str = Field(..., description="Action that was performed")
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Processing result",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing timestamp",
    )


class N8nConnectionStatus(str, Enum):
    """n8n connection status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class N8nStatusResponse(BaseModel):
    """n8n connection status response.

    Attributes:
        status: Current connection status
        base_url: Configured n8n base URL
        healthy: Whether n8n is reachable
        last_check: Timestamp of last health check
        tools_count: Number of registered MCP tools
        error: Error message if unhealthy
    """

    status: N8nConnectionStatus
    base_url: str
    healthy: bool
    last_check: Optional[datetime] = None
    tools_count: int = 0
    error: Optional[str] = None


class N8nConfigResponse(BaseModel):
    """n8n configuration response (safe — no secrets).

    Attributes:
        base_url: n8n instance base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        api_key_configured: Whether API key is set (no actual key)
        webhook_hmac_configured: Whether HMAC secret is set
    """

    base_url: str
    timeout: int
    max_retries: int
    api_key_configured: bool
    webhook_hmac_configured: bool


class N8nConfigUpdate(BaseModel):
    """n8n configuration update request.

    Only non-secret settings can be updated via API.
    API key and HMAC secret must be set via environment variables.

    Attributes:
        base_url: New n8n base URL
        timeout: New timeout in seconds
        max_retries: New max retry count
    """

    base_url: Optional[str] = Field(
        None,
        min_length=1,
        description="n8n instance base URL",
    )
    timeout: Optional[int] = Field(
        None,
        ge=5,
        le=300,
        description="Request timeout in seconds (5-300)",
    )
    max_retries: Optional[int] = Field(
        None,
        ge=0,
        le=10,
        description="Maximum retry attempts (0-10)",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize base URL."""
        if v is not None:
            v = v.rstrip("/")
            if not v.startswith(("http://", "https://")):
                raise ValueError("base_url must start with http:// or https://")
        return v


class WebhookVerificationError(BaseModel):
    """Error response for webhook verification failures.

    Attributes:
        error: Error code
        message: Human-readable error message
        details: Additional error details
    """

    error: str = "WEBHOOK_VERIFICATION_FAILED"
    message: str
    details: Optional[Dict[str, Any]] = None
