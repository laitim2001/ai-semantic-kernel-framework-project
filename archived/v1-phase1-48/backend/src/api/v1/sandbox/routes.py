"""
Sandbox API Routes - Phase 21 Sandbox Security

Provides sandbox management endpoints for secure code execution.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional

from src.api.v1.sandbox.schemas import (
    CreateSandboxRequest,
    SandboxResponse,
    IPCMessageRequest,
    IPCMessageResponse,
    PoolStatusResponse,
    PoolCleanupResponse,
)
from src.domain.sandbox import SandboxService, SandboxStatus

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

# Global service instance
_sandbox_service: Optional[SandboxService] = None


def get_sandbox_service() -> SandboxService:
    """Get or create sandbox service instance"""
    global _sandbox_service
    if _sandbox_service is None:
        _sandbox_service = SandboxService()
    return _sandbox_service


# Static routes first (before dynamic routes)
@router.get("/pool/status", response_model=PoolStatusResponse)
async def get_pool_status():
    """Get process pool status"""
    service = get_sandbox_service()
    status_data = service.get_pool_status()
    return PoolStatusResponse(**status_data)


@router.post("/pool/cleanup", response_model=PoolCleanupResponse)
async def cleanup_pool():
    """Cleanup idle processes in the pool"""
    service = get_sandbox_service()
    result = service.cleanup_pool()
    return PoolCleanupResponse(**result)


# Main sandbox routes
@router.post("", response_model=SandboxResponse, status_code=status.HTTP_201_CREATED)
async def create_sandbox(request: CreateSandboxRequest):
    """Create a new sandbox process"""
    service = get_sandbox_service()
    sandbox = service.create_sandbox(
        user_id=request.user_id,
        environment=request.environment,
        timeout_seconds=request.timeout_seconds,
        max_memory_mb=request.max_memory_mb,
    )
    return _to_sandbox_response(sandbox)


@router.get("/{sandbox_id}", response_model=SandboxResponse)
async def get_sandbox(sandbox_id: str):
    """Get sandbox status by ID"""
    service = get_sandbox_service()
    sandbox = service.get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found",
        )
    return _to_sandbox_response(sandbox)


@router.delete("/{sandbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sandbox(sandbox_id: str):
    """Terminate and delete a sandbox"""
    service = get_sandbox_service()
    # First terminate, then delete
    service.terminate_sandbox(sandbox_id)
    deleted = service.delete_sandbox(sandbox_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found",
        )
    return None


@router.post("/{sandbox_id}/ipc", response_model=IPCMessageResponse)
async def send_ipc_message(sandbox_id: str, request: IPCMessageRequest):
    """Send IPC message to sandbox"""
    service = get_sandbox_service()

    # Check sandbox exists
    sandbox = service.get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found",
        )

    response = service.send_ipc_message(
        sandbox_id=sandbox_id,
        message_type=request.type,
        payload=request.payload,
        request_id=request.request_id,
    )

    return IPCMessageResponse(
        request_id=response.request_id,
        response_type=response.response_type,
        result=response.result,
        latency_ms=response.latency_ms,
        success=response.success,
        error=response.error,
    )


def _to_sandbox_response(sandbox) -> SandboxResponse:
    """Convert domain model to response"""
    return SandboxResponse(
        sandbox_id=sandbox.sandbox_id,
        user_id=sandbox.user_id,
        status=sandbox.status.value,
        environment=sandbox.environment,
        timeout_seconds=sandbox.timeout_seconds,
        max_memory_mb=sandbox.max_memory_mb,
        memory_usage_mb=sandbox.memory_usage_mb,
        uptime_seconds=sandbox.uptime_seconds,
        creation_time_ms=sandbox.creation_time_ms,
        created_at=sandbox.created_at,
    )
