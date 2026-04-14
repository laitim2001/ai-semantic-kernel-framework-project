"""Pydantic schemas for the Expert Management API.

Sprint 162 — Phase 46 Agent Expert Registry.
"""

from __future__ import annotations

from typing import Any

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


class ExpertListResponse(BaseModel):
    """Response for listing experts."""

    experts: list[ExpertResponse] = Field(..., description="Expert list")
    total: int = Field(..., description="Total expert count")


class ReloadResponse(BaseModel):
    """Response after hot-reloading the registry."""

    status: str = Field("ok", description="Reload status")
    experts_loaded: int = Field(..., description="Number of experts loaded")
    expert_names: list[str] = Field(..., description="Loaded expert names")
