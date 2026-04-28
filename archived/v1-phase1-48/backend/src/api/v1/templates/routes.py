# =============================================================================
# IPA Platform - Templates API Routes
# =============================================================================
# Sprint 4: Developer Experience - Agent Template Marketplace
#
# REST API endpoints for Agent template management:
#   - GET /templates/ - List templates with filtering
#   - GET /templates/health - Health check (MUST be before /{id})
#   - GET /templates/categories/list - List categories
#   - GET /templates/popular/list - Get popular templates
#   - GET /templates/top-rated/list - Get top rated templates
#   - GET /templates/statistics/summary - Get statistics
#   - POST /templates/search - Search templates
#   - GET /templates/{id} - Get template details
#   - POST /templates/{id}/instantiate - Instantiate template
#   - POST /templates/{id}/rate - Rate a template
#   - GET /templates/similar/{id} - Get similar templates
#
# IMPORTANT: Static routes MUST be defined before dynamic routes (/{id})
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.templates.schemas import (
    CategoryListResponse,
    CategoryResponse,
    HealthCheckResponse,
    InstantiateRequest,
    InstantiateResponse,
    RateRequest,
    RateResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    TemplateDetailResponse,
    TemplateExampleResponse,
    TemplateListResponse,
    TemplateListResult,
    TemplateParameterResponse,
    TemplateStatisticsResponse,
)
from src.domain.templates import (
    TemplateCategory,
    TemplateError,
    TemplateService,
    TemplateStatus,
)


router = APIRouter(prefix="/templates", tags=["templates"])


# =============================================================================
# Service Instance Management
# =============================================================================

_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """Get or create template service instance."""
    global _template_service
    if _template_service is None:
        # Default templates directory
        templates_dir = Path(__file__).parent.parent.parent.parent.parent / "templates"
        _template_service = TemplateService(templates_dir=templates_dir)
        _template_service.load_templates()
    return _template_service


def set_template_service(service: TemplateService) -> None:
    """Set template service instance (for testing)."""
    global _template_service
    _template_service = service


# =============================================================================
# Helper Functions
# =============================================================================


def _to_list_response(template) -> TemplateListResponse:
    """Convert template to list response."""
    return TemplateListResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        status=template.status.value,
        version=template.version,
        author=template.author,
        usage_count=template.usage_count,
        rating=template.rating,
        rating_count=template.rating_count,
        tags=template.tags,
    )


def _to_detail_response(template) -> TemplateDetailResponse:
    """Convert template to detail response."""
    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        status=template.status.value,
        version=template.version,
        author=template.author,
        created_at=template.created_at,
        updated_at=template.updated_at,
        instructions=template.instructions,
        tools=template.tools,
        model=template.model,
        temperature=template.temperature,
        max_tokens=template.max_tokens,
        parameters=[
            TemplateParameterResponse(
                name=p.name,
                type=p.type.value,
                description=p.description,
                required=p.required,
                default=p.default,
                options=p.options,
                min_value=p.min_value,
                max_value=p.max_value,
                pattern=p.pattern,
            )
            for p in template.parameters
        ],
        usage_count=template.usage_count,
        rating=template.rating,
        rating_count=template.rating_count,
        tags=template.tags,
        examples=[
            TemplateExampleResponse(
                input=e.input,
                output=e.output,
                description=e.description,
            )
            for e in template.examples
        ],
    )


# =============================================================================
# Static Routes (MUST be defined before dynamic routes)
# =============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check template service health."""
    service = get_template_service()
    stats = service.get_statistics()

    return HealthCheckResponse(
        service="templates",
        status="healthy",
        total_templates=stats["total_templates"],
        templates_loaded=stats["total_templates"] > 0,
    )


@router.get("/statistics/summary", response_model=TemplateStatisticsResponse)
async def get_statistics():
    """Get template service statistics."""
    service = get_template_service()
    stats = service.get_statistics()

    return TemplateStatisticsResponse(
        total_templates=stats["total_templates"],
        builtin_templates=stats["builtin_templates"],
        custom_templates=stats["custom_templates"],
        total_usage=stats["total_usage"],
        by_category=stats["by_category"],
        by_status=stats["by_status"],
    )


@router.get("/categories/list", response_model=CategoryListResponse)
async def list_categories():
    """List all template categories with counts."""
    service = get_template_service()

    categories = service.get_categories()

    return CategoryListResponse(
        categories=[
            CategoryResponse(
                category=c["category"],
                name=c["name"],
                count=c["count"],
            )
            for c in categories
        ]
    )


@router.get("/popular/list", response_model=TemplateListResult)
async def get_popular_templates(
    limit: int = Query(5, ge=1, le=20, description="Number of templates"),
):
    """Get most popular templates by usage count."""
    service = get_template_service()

    templates = service.get_popular_templates(limit=limit)

    return TemplateListResult(
        templates=[_to_list_response(t) for t in templates],
        total=len(templates),
        page=1,
        page_size=limit,
    )


@router.get("/top-rated/list", response_model=TemplateListResult)
async def get_top_rated_templates(
    limit: int = Query(5, ge=1, le=20, description="Number of templates"),
):
    """Get top rated templates."""
    service = get_template_service()

    templates = service.get_top_rated_templates(limit=limit)

    return TemplateListResult(
        templates=[_to_list_response(t) for t in templates],
        total=len(templates),
        page=1,
        page_size=limit,
    )


@router.post("/search", response_model=SearchResponse)
async def search_templates(request: SearchRequest):
    """
    Search templates with relevance scoring.

    Returns templates sorted by relevance to the search query.
    """
    service = get_template_service()

    results = service.search_templates(
        query=request.query,
        limit=request.limit,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                template=_to_list_response(r["template"]),
                score=r["score"],
            )
            for r in results
        ],
        query=request.query,
        total=len(results),
    )


# =============================================================================
# Template List (before dynamic routes but after specific static routes)
# =============================================================================


@router.get("/", response_model=TemplateListResult)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name/description/tags"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    sort_by: str = Query("usage_count", description="Sort field"),
    ascending: bool = Query(False, description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
):
    """
    List all templates with optional filtering and pagination.

    Supports filtering by category, status, search text, and tags.
    Results are paginated and can be sorted by various fields.
    """
    service = get_template_service()

    # Parse category
    cat = None
    if category:
        try:
            cat = TemplateCategory(category.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    # Parse status
    stat = None
    if status:
        try:
            stat = TemplateStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # Get templates
    templates = service.list_templates(
        category=cat,
        status=stat,
        search=search,
        tags=tag_list,
        sort_by=sort_by,
        ascending=ascending,
    )

    # Paginate
    total = len(templates)
    start = (page - 1) * page_size
    end = start + page_size
    page_templates = templates[start:end]

    return TemplateListResult(
        templates=[_to_list_response(t) for t in page_templates],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Dynamic Routes (with path parameters - MUST be after static routes)
# =============================================================================


@router.get("/similar/{template_id}", response_model=TemplateListResult)
async def get_similar_templates(
    template_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of templates"),
):
    """Find templates similar to a given template."""
    service = get_template_service()

    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    similar = service.find_similar_templates(template_id=template_id, limit=limit)

    return TemplateListResult(
        templates=[_to_list_response(t) for t in similar],
        total=len(similar),
        page=1,
        page_size=limit,
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str):
    """
    Get template details by ID.

    Returns complete template information including parameters,
    examples, and usage statistics.
    """
    service = get_template_service()

    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    return _to_detail_response(template)


@router.post("/{template_id}/instantiate", response_model=InstantiateResponse)
async def instantiate_template(template_id: str, request: InstantiateRequest):
    """
    Instantiate a template to create a new Agent.

    Validates parameters against template definition and creates
    a new Agent with the configured settings.
    """
    service = get_template_service()

    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    try:
        agent_id = await service.instantiate(
            template_id=template_id,
            name=request.name,
            parameters=request.parameters,
            metadata=request.metadata,
        )

        return InstantiateResponse(
            agent_id=agent_id,
            template_id=template_id,
            template_version=template.version,
            name=request.name,
            created_at=datetime.utcnow(),
        )

    except TemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/rate", response_model=RateResponse)
async def rate_template(template_id: str, request: RateRequest):
    """Rate a template (1-5 scale)."""
    service = get_template_service()

    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    try:
        new_rating = service.rate_template(
            template_id=template_id,
            rating=request.rating,
        )

        return RateResponse(
            template_id=template_id,
            new_rating=new_rating,
            rating_count=template.rating_count,
        )

    except TemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))
