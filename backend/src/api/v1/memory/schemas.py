# =============================================================================
# IPA Platform - Memory API Schemas
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# Pydantic schemas for Memory API request/response validation.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryMetadataSchema(BaseModel):
    """Schema for memory metadata."""

    source: str = Field("", description="Source of the memory")
    event_id: Optional[str] = Field(None, description="Related event ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    tags: List[str] = Field(default_factory=list, description="Tags")
    custom: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class AddMemoryRequest(BaseModel):
    """Request schema for adding a memory."""

    content: str = Field(..., min_length=1, description="Memory content")
    user_id: str = Field(..., description="User identifier")
    memory_type: str = Field(
        "conversation",
        description="Memory type: event_resolution, user_preference, "
        "system_knowledge, best_practice, conversation, feedback",
    )
    metadata: Optional[MemoryMetadataSchema] = Field(
        None, description="Optional metadata"
    )
    layer: Optional[str] = Field(
        None,
        description="Target layer: working, session, long_term. Auto-selected if not specified.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "User prefers dark mode for the dashboard interface",
                "user_id": "user-123",
                "memory_type": "user_preference",
                "metadata": {
                    "source": "chat",
                    "importance": 0.8,
                    "tags": ["ui", "preference"],
                },
            }
        }


class AddMemoryResponse(BaseModel):
    """Response schema for adding a memory."""

    id: str = Field(..., description="Memory ID")
    user_id: str = Field(..., description="User ID")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Memory type")
    layer: str = Field(..., description="Storage layer")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "mem-abc123",
                "user_id": "user-123",
                "content": "User prefers dark mode for the dashboard interface",
                "memory_type": "user_preference",
                "layer": "long_term",
                "created_at": "2026-01-12T10:00:00Z",
            }
        }


class SearchMemoryRequest(BaseModel):
    """Request schema for searching memories."""

    query: str = Field(..., min_length=1, description="Search query")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    memory_types: Optional[List[str]] = Field(
        None, description="Filter by memory types"
    )
    layers: Optional[List[str]] = Field(None, description="Filter by layers")
    min_importance: float = Field(0.0, ge=0.0, le=1.0, description="Minimum importance")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "user interface preferences",
                "user_id": "user-123",
                "memory_types": ["user_preference"],
                "limit": 10,
            }
        }


class MemorySearchResultSchema(BaseModel):
    """Schema for a single search result."""

    id: str = Field(..., description="Memory ID")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Memory type")
    layer: str = Field(..., description="Storage layer")
    score: float = Field(..., description="Relevance score")
    metadata: MemoryMetadataSchema = Field(..., description="Memory metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class SearchMemoryResponse(BaseModel):
    """Response schema for memory search."""

    results: List[MemorySearchResultSchema] = Field(..., description="Search results")
    total: int = Field(..., description="Total results returned")
    query: str = Field(..., description="Original query")


class MemoryResponse(BaseModel):
    """Response schema for a single memory."""

    id: str = Field(..., description="Memory ID")
    user_id: str = Field(..., description="User ID")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Memory type")
    layer: str = Field(..., description="Storage layer")
    metadata: MemoryMetadataSchema = Field(..., description="Memory metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    access_count: int = Field(0, description="Access count")


class MemoryListResponse(BaseModel):
    """Response schema for listing memories."""

    memories: List[MemoryResponse] = Field(..., description="List of memories")
    total: int = Field(..., description="Total memories")
    user_id: str = Field(..., description="User ID")


class DeleteMemoryResponse(BaseModel):
    """Response schema for deleting a memory."""

    success: bool = Field(..., description="Whether deletion was successful")
    memory_id: str = Field(..., description="Deleted memory ID")
    message: str = Field(..., description="Status message")


class MemoryHealthResponse(BaseModel):
    """Response schema for health check."""

    status: str = Field(..., description="Health status")
    mem0_initialized: bool = Field(..., description="mem0 client status")
    redis_connected: bool = Field(..., description="Redis connection status")
    embedding_service: bool = Field(..., description="Embedding service status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class PromoteMemoryRequest(BaseModel):
    """Request schema for promoting a memory to a higher layer."""

    memory_id: str = Field(..., description="Memory ID to promote")
    user_id: str = Field(..., description="User ID")
    from_layer: str = Field(..., description="Source layer")
    to_layer: str = Field(..., description="Target layer")

    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "mem-abc123",
                "user_id": "user-123",
                "from_layer": "session",
                "to_layer": "long_term",
            }
        }


class ContextRequest(BaseModel):
    """Request schema for getting memory context."""

    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    query: Optional[str] = Field(None, description="Optional query for relevance")
    limit: int = Field(10, ge=1, le=50, description="Maximum memories")
