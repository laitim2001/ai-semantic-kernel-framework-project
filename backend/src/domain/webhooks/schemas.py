"""
Webhook Schemas (Pydantic Models)

Sprint 2 - Story S2-1
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class WebhookPayload(BaseModel):
    """Schema for incoming webhook payload."""
    workflow_id: Optional[str] = Field(None, description="Target workflow ID to trigger")
    action: Optional[str] = Field(None, description="Action to perform")
    data: Optional[dict[str, Any]] = Field(None, description="Webhook payload data")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "my-workflow",
                "action": "trigger",
                "data": {"key": "value"},
                "metadata": {"source": "n8n"}
            }
        }
    )


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    success: bool = Field(..., description="Whether the webhook was processed successfully")
    execution_id: Optional[str] = Field(None, description="ID of the triggered execution")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Unique request ID for tracking")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "execution_id": "exec-12345",
                "message": "Workflow execution triggered successfully",
                "timestamp": "2025-01-01T00:00:00Z",
                "request_id": "req-12345"
            }
        }
    )


class WebhookTestRequest(BaseModel):
    """Schema for webhook test request."""
    payload: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Test payload to send"
    )
    include_signature: bool = Field(
        default=True,
        description="Whether to include signature validation info in response"
    )


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""
    success: bool = Field(..., description="Test result")
    message: str = Field(..., description="Test result message")
    received_payload: dict[str, Any] = Field(..., description="Received payload")
    headers_received: dict[str, str] = Field(..., description="Headers received")
    signature_info: Optional[dict[str, Any]] = Field(
        None,
        description="Signature validation information"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Test timestamp")


class N8nWebhookPayload(BaseModel):
    """Schema for n8n specific webhook payload."""
    workflow_id: str = Field(..., description="n8n workflow ID")
    execution_id: Optional[str] = Field(None, description="n8n execution ID")
    node_name: Optional[str] = Field(None, description="Name of the node that triggered")
    data: dict[str, Any] = Field(default_factory=dict, description="Webhook data")
    timestamp: Optional[datetime] = Field(None, description="n8n execution timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "n8n-workflow-123",
                "execution_id": "exec-456",
                "node_name": "HTTP Request",
                "data": {"key": "value"},
                "timestamp": "2025-01-01T00:00:00Z"
            }
        }
    )


class WebhookAuditEntry(BaseModel):
    """Schema for webhook audit log entry."""
    source: str = Field(..., description="Webhook source (n8n, teams, etc.)")
    workflow_id: Optional[str] = Field(None, description="Target workflow ID")
    execution_id: Optional[str] = Field(None, description="Triggered execution ID")
    ip_address: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    signature_valid: Optional[bool] = Field(None, description="Signature validation result")
    response_status: int = Field(..., description="HTTP response status code")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Processing duration in ms")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# S2-2: n8n Workflow Trigger (Outbound)
# ============================================

class N8nTriggerRequest(BaseModel):
    """Schema for triggering an n8n workflow."""
    n8n_workflow_id: str = Field(..., description="n8n workflow ID or webhook path")
    data: dict[str, Any] = Field(default_factory=dict, description="Data to pass to n8n workflow")
    webhook_path: Optional[str] = Field(None, description="Custom webhook path (overrides workflow_id)")
    test_mode: bool = Field(False, description="Use n8n test webhook endpoint")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "n8n_workflow_id": "process-data",
                "data": {"items": [1, 2, 3], "action": "process"},
                "test_mode": False
            }
        }
    )


class N8nTriggerResponse(BaseModel):
    """Schema for n8n trigger response."""
    success: bool = Field(..., description="Whether the trigger was successful")
    workflow_id: str = Field(..., description="n8n workflow ID that was triggered")
    request_id: str = Field(..., description="Unique request ID")
    n8n_response: Optional[dict[str, Any]] = Field(None, description="Response from n8n")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_type: Optional[str] = Field(None, description="Error type classification")
    duration_ms: Optional[int] = Field(None, description="Request duration in ms")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "workflow_id": "process-data",
                "request_id": "req-abc123",
                "n8n_response": {"received": True},
                "duration_ms": 150,
                "timestamp": "2025-01-01T00:00:00Z"
            }
        }
    )


class N8nHealthResponse(BaseModel):
    """Schema for n8n health check response."""
    success: bool = Field(..., description="Whether n8n is healthy")
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    n8n_url: str = Field(..., description="n8n URL that was checked")
    error: Optional[str] = Field(None, description="Error if unhealthy")


class N8nWorkflowInfo(BaseModel):
    """Schema for n8n workflow information."""
    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    active: bool = Field(..., description="Whether workflow is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class N8nWorkflowListResponse(BaseModel):
    """Schema for n8n workflow list response."""
    success: bool = Field(..., description="Whether the request was successful")
    workflows: list[N8nWorkflowInfo] = Field(default_factory=list, description="List of workflows")
    total: int = Field(0, description="Total number of workflows")
    error: Optional[str] = Field(None, description="Error message if failed")


class N8nExecutionStatusResponse(BaseModel):
    """Schema for n8n execution status response."""
    success: bool = Field(..., description="Whether the query was successful")
    execution_id: str = Field(..., description="n8n execution ID")
    data: Optional[dict[str, Any]] = Field(None, description="Execution data from n8n")
    error: Optional[str] = Field(None, description="Error message if failed")
