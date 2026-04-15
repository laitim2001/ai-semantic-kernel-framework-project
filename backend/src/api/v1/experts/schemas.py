"""Pydantic schemas for the Expert Management API.

Sprint 162 — Phase 46 Agent Expert Registry.
Sprint 163 — CRUD schemas added.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExpertResponse(BaseModel):
    """Single expert definition response."""

    name: str = Field(..., description="Expert unique name")
    display_name: str = Field(..., description="English display name")
    display_name_zh: str = Field(..., description="Chinese display name")
    description: str = Field("", description="Expert description")
    domain: str = Field(..., description="Expert domain")
    capabilities: list[str] = Field(default_factory=list, description="Expert capabilities")
    model: str | None = Field(None, description="LLM model override (null = default)")
    max_iterations: int = Field(5, description="Max tool-call iterations")
    tools: list[str] = Field(default_factory=list, description="Allowed tool names")
    enabled: bool = Field(True, description="Whether the expert is active")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class ExpertDetailResponse(ExpertResponse):
    """Extended response with DB fields."""

    id: str = Field(..., description="Expert UUID")
    is_builtin: bool = Field(False, description="Whether seeded from YAML")
    version: int = Field(1, description="Version number")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ExpertListResponse(BaseModel):
    """Response for listing experts."""

    experts: list[ExpertDetailResponse] = Field(..., description="Expert list")
    total: int = Field(..., description="Total expert count")


class ExpertCreateRequest(BaseModel):
    """Request body for creating a new expert."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique expert name (slug)")
    display_name: str = Field(..., min_length=1, max_length=255, description="English display name")
    display_name_zh: str = Field(..., min_length=1, max_length=255, description="Chinese display name")
    description: str = Field("", description="Expert description")
    domain: str = Field(..., description="Expert domain")
    capabilities: list[str] = Field(default_factory=list, description="Capability tags")
    model: str | None = Field(None, description="LLM model override")
    max_iterations: int = Field(5, ge=1, le=20, description="Max iterations")
    system_prompt: str = Field(..., min_length=1, description="System prompt")
    tools: list[str] = Field(default_factory=list, description="Allowed tool names")
    enabled: bool = Field(True, description="Whether active")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class ExpertUpdateRequest(BaseModel):
    """Request body for updating an expert. All fields optional."""

    display_name: Optional[str] = Field(None, max_length=255)
    display_name_zh: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = None
    capabilities: Optional[list[str]] = None
    model: Optional[str] = None
    max_iterations: Optional[int] = Field(None, ge=1, le=20)
    system_prompt: Optional[str] = None
    tools: Optional[list[str]] = None
    enabled: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class ReloadResponse(BaseModel):
    """Response after hot-reloading the registry."""

    status: str = Field("ok", description="Reload status")
    experts_loaded: int = Field(..., description="Number of experts loaded")
    expert_names: list[str] = Field(..., description="Loaded expert names")
