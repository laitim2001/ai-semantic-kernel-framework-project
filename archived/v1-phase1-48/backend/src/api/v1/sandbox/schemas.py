"""
Sandbox API Schemas - Phase 21 Sandbox Security
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateSandboxRequest(BaseModel):
    """Request to create a new sandbox"""
    user_id: str = Field(..., description="User ID for the sandbox")
    environment: str = Field(default="test", description="Environment type")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Timeout in seconds")
    max_memory_mb: int = Field(default=512, ge=64, le=4096, description="Max memory in MB")


class SandboxResponse(BaseModel):
    """Sandbox information response"""
    sandbox_id: str
    user_id: str
    status: str
    environment: str
    timeout_seconds: int
    max_memory_mb: int
    memory_usage_mb: int
    uptime_seconds: int
    creation_time_ms: float
    created_at: datetime

    class Config:
        from_attributes = True


class IPCMessageRequest(BaseModel):
    """IPC message request"""
    type: str = Field(..., description="Message type: EXECUTE, ENV_CHECK, FS_CHECK, NET_CHECK")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    request_id: Optional[str] = Field(default=None, description="Optional request ID")


class IPCMessageResponse(BaseModel):
    """IPC message response"""
    request_id: str
    response_type: str
    result: Any
    latency_ms: float
    success: bool
    error: Optional[str] = None


class PoolStatusResponse(BaseModel):
    """Process pool status response"""
    active_count: int
    idle_count: int
    max_pool_size: int
    reuse_count: int


class PoolCleanupResponse(BaseModel):
    """Pool cleanup response"""
    cleaned_count: int
    remaining_active: int


class SandboxListResponse(BaseModel):
    """List of sandboxes response"""
    sandboxes: List[SandboxResponse]
    total: int
