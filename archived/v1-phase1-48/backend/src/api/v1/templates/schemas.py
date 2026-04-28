# =============================================================================
# IPA Platform - Templates API Schemas
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# Pydantic schemas for template API request/response validation.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Parameter Schemas
# =============================================================================


class TemplateParameterResponse(BaseModel):
    """Template parameter response."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None


class TemplateExampleResponse(BaseModel):
    """Template example response."""

    input: str
    output: Dict[str, Any]
    description: Optional[str] = None


# =============================================================================
# Template Schemas
# =============================================================================


class TemplateListResponse(BaseModel):
    """Template list item response."""

    id: str
    name: str
    description: str
    category: str
    status: str
    version: str
    author: str
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = Field(default_factory=list)


class TemplateDetailResponse(BaseModel):
    """Template detail response."""

    id: str
    name: str
    description: str
    category: str
    status: str
    version: str
    author: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    instructions: str
    tools: List[str] = Field(default_factory=list)
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    parameters: List[TemplateParameterResponse] = Field(default_factory=list)
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = Field(default_factory=list)
    examples: List[TemplateExampleResponse] = Field(default_factory=list)


class TemplateListResult(BaseModel):
    """Template list result with pagination."""

    templates: List[TemplateListResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# Instantiation Schemas
# =============================================================================


class InstantiateRequest(BaseModel):
    """Template instantiation request."""

    name: str = Field(..., min_length=1, max_length=100, description="Name for the new agent")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameter values")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional agent metadata")


class InstantiateResponse(BaseModel):
    """Template instantiation response."""

    agent_id: UUID
    template_id: str
    template_version: str
    name: str
    created_at: datetime


# =============================================================================
# Search Schemas
# =============================================================================


class SearchRequest(BaseModel):
    """Template search request."""

    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(10, ge=1, le=50)


class SearchResultItem(BaseModel):
    """Search result item."""

    template: TemplateListResponse
    score: float


class SearchResponse(BaseModel):
    """Template search response."""

    results: List[SearchResultItem]
    query: str
    total: int


# =============================================================================
# Rating Schemas
# =============================================================================


class RateRequest(BaseModel):
    """Template rating request."""

    rating: float = Field(..., ge=1, le=5, description="Rating from 1 to 5")


class RateResponse(BaseModel):
    """Template rating response."""

    template_id: str
    new_rating: float
    rating_count: int


# =============================================================================
# Category Schemas
# =============================================================================


class CategoryResponse(BaseModel):
    """Category with template count."""

    category: str
    name: str
    count: int


class CategoryListResponse(BaseModel):
    """Category list response."""

    categories: List[CategoryResponse]


# =============================================================================
# Statistics Schemas
# =============================================================================


class TemplateStatisticsResponse(BaseModel):
    """Template service statistics."""

    total_templates: int
    builtin_templates: int
    custom_templates: int
    total_usage: int
    by_category: Dict[str, int]
    by_status: Dict[str, int]


# =============================================================================
# Health Check Schema
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    service: str = "templates"
    status: str
    total_templates: int
    templates_loaded: bool
