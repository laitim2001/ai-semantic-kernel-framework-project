"""Knowledge Management API — CRUD + search + ingest endpoints.

Provides REST endpoints for managing the enterprise knowledge base:
  - Document ingestion (text upload)
  - Knowledge search
  - Collection management
  - Agent Skills listing

Sprint 119 — Phase 38 E2E Assembly C.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_rag_pipeline = None
_skills_provider = None


def _get_rag_pipeline():
    global _rag_pipeline
    if _rag_pipeline is None:
        from src.integrations.knowledge.rag_pipeline import RAGPipeline
        _rag_pipeline = RAGPipeline()
        logger.info("Knowledge API: RAGPipeline initialized")
    return _rag_pipeline


def _get_skills_provider():
    global _skills_provider
    if _skills_provider is None:
        from src.integrations.knowledge.agent_skills import AgentSkillsProvider
        _skills_provider = AgentSkillsProvider()
        logger.info("Knowledge API: AgentSkillsProvider initialized")
    return _skills_provider


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class IngestTextRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    collection: Optional[str] = None


class IngestResponse(BaseModel):
    success: bool
    title: str = ""
    chunks: int = 0
    indexed: int = 0
    error: Optional[str] = None


class SearchResultItem(BaseModel):
    content: str
    score: float
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    count: int
    query: str


class SkillItem(BaseModel):
    skill_id: str
    name: str
    category: str
    description: str
    tags: List[str]


# =============================================================================
# Knowledge Base Endpoints
# =============================================================================

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_text(body: IngestTextRequest) -> IngestResponse:
    """Ingest text content into the knowledge base."""
    pipeline = _get_rag_pipeline()
    result = await pipeline.ingest_text(
        text=body.content,
        title=body.title,
        metadata=body.metadata,
    )
    return IngestResponse(**result)


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(body: SearchRequest) -> SearchResponse:
    """Search the knowledge base."""
    pipeline = _get_rag_pipeline()
    results = await pipeline.retrieve(
        query=body.query,
        limit=body.limit,
        collection=body.collection,
    )
    return SearchResponse(
        results=[
            SearchResultItem(
                content=r.content[:500],
                score=r.score,
                source=r.source,
                metadata=r.metadata or {},
            )
            for r in results
        ],
        count=len(results),
        query=body.query,
    )


@router.get("/collections", response_model=Dict[str, Any])
async def get_collection_info() -> Dict[str, Any]:
    """Get knowledge base collection statistics."""
    pipeline = _get_rag_pipeline()
    return await pipeline.get_collection_info()


@router.delete("/collections", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection() -> None:
    """Delete the entire knowledge collection."""
    pipeline = _get_rag_pipeline()
    await pipeline.delete_collection()


# =============================================================================
# Agent Skills Endpoints
# =============================================================================

@router.get("/skills", response_model=List[SkillItem])
async def list_skills(
    category: Optional[str] = Query(None),
) -> List[SkillItem]:
    """List available agent skills."""
    provider = _get_skills_provider()
    from src.integrations.knowledge.agent_skills import SkillCategory
    cat = None
    if category:
        try:
            cat = SkillCategory(category)
        except ValueError:
            pass
    skills = provider.list_skills(category=cat)
    return [
        SkillItem(
            skill_id=s.skill_id,
            name=s.name,
            category=s.category.value,
            description=s.description,
            tags=s.tags,
        )
        for s in skills
    ]


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> Dict[str, Any]:
    """Get a specific skill with full content."""
    provider = _get_skills_provider()
    skill = provider.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return {
        "skill_id": skill.skill_id,
        "name": skill.name,
        "category": skill.category.value,
        "description": skill.description,
        "content": skill.content,
        "tags": skill.tags,
        "version": skill.version,
    }


@router.get("/skills/search/query")
async def search_skills(
    q: str = Query(..., description="Search query"),
    limit: int = Query(3, ge=1, le=10),
) -> List[SkillItem]:
    """Search agent skills by keyword."""
    provider = _get_skills_provider()
    results = provider.search_skills(q, limit=limit)
    return [
        SkillItem(
            skill_id=s.skill_id,
            name=s.name,
            category=s.category.value,
            description=s.description,
            tags=s.tags,
        )
        for s in results
    ]
