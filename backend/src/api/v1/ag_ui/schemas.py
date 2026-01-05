# =============================================================================
# IPA Platform - AG-UI API Schemas
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
#
# Request/Response schemas for AG-UI protocol API.
# Follows CopilotKit AG-UI protocol specification.
#
# Dependencies:
#   - Pydantic (pydantic)
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AGUIExecutionMode(str, Enum):
    """AG-UI execution mode."""
    WORKFLOW = "workflow"
    CHAT = "chat"
    HYBRID = "hybrid"
    AUTO = "auto"


class AGUIToolDefinition(BaseModel):
    """Tool definition for AG-UI request."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "search",
                "description": "Search for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            }
        }


class AGUIMessage(BaseModel):
    """Message in AG-UI format."""
    id: Optional[str] = Field(None, description="Message ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls in message")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg-123",
                "role": "user",
                "content": "Hello, how can you help me?",
            }
        }


class RunAgentRequest(BaseModel):
    """
    AG-UI Run Agent Request.

    Follows the CopilotKit AG-UI protocol specification for running
    an agent with streaming response.
    """
    thread_id: str = Field(..., description="Thread ID for conversation context")
    run_id: Optional[str] = Field(None, description="Optional run ID (generated if not provided)")
    messages: List[AGUIMessage] = Field(default_factory=list, description="Conversation messages")
    tools: Optional[List[AGUIToolDefinition]] = Field(None, description="Available tools")

    # Execution options
    mode: AGUIExecutionMode = Field(
        AGUIExecutionMode.AUTO,
        description="Execution mode (auto detects best mode)"
    )
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Maximum tokens for response")
    timeout: Optional[float] = Field(None, ge=1, le=600, description="Execution timeout in seconds")

    # Session context
    session_id: Optional[str] = Field(None, description="Optional session ID for persistence")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "messages": [
                    {"role": "user", "content": "Help me analyze this data"},
                ],
                "mode": "auto",
                "max_tokens": 2000,
            }
        }


class RunAgentResponse(BaseModel):
    """
    AG-UI Run Agent Response (for non-streaming mode).

    Only used when streaming is not supported or disabled.
    Normally the response is streamed via SSE.
    """
    thread_id: str
    run_id: str
    status: str = Field(..., description="Execution status (success, error)")
    content: str = Field("", description="Generated content")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "run_id": "run-xyz789",
                "status": "success",
                "content": "Here is my analysis...",
                "tool_calls": [],
                "created_at": "2026-01-05T10:00:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Health check response for AG-UI endpoint."""
    status: str = Field("healthy", description="Service status")
    version: str = Field("1.0.0", description="AG-UI protocol version")
    features: List[str] = Field(
        default_factory=lambda: ["streaming", "tool_calls", "hybrid_mode"],
        description="Supported features"
    )


class ErrorResponse(BaseModel):
    """Error response for AG-UI endpoint."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_REQUEST",
                "message": "thread_id is required",
                "details": {"field": "thread_id"},
            }
        }
