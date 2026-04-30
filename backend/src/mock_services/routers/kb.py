"""
File: backend/src/mock_services/routers/kb.py
Purpose: Mock knowledge base — simple substring search returning ranked KB articles.
Category: Mock services / routers
Scope: Phase 51 / Sprint 51.0 Day 1.6

Description:
    POST /mock/kb/search accepts {query: str, top_k: int} and returns up to top_k
    KBSearchResult sorted by naive substring score:
        - Title contains query (case-insensitive): score 1.0
        - Tag contains query: score 0.7
        - Content contains query: score 0.5
        - Otherwise: score 0.0 (excluded)

    Production replacement (Phase 55) will use Qdrant + embedding similarity.
    The naive scoring is sufficient for demo material in 51-54.

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from mock_services.data.loader import SeedDB, get_db
from mock_services.schemas import KBArticle, KBSearchResult

router = APIRouter(prefix="/mock/kb", tags=["mock-kb"])


class KBSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    top_k: int = Field(default=5, ge=1, le=20)


def _score(article: dict[str, Any], query: str) -> float:
    q = query.casefold()
    if q in article["title"].casefold():
        return 1.0
    for tag in article.get("tags", []):
        if q in tag.casefold():
            return 0.7
    if q in article["content"].casefold():
        return 0.5
    return 0.0


@router.post("/search", response_model=list[KBSearchResult])
async def search(
    request: KBSearchRequest, db: SeedDB = Depends(get_db)
) -> list[KBSearchResult]:
    scored = [
        (_score(article, request.query), article) for article in db.kb_articles.values()
    ]
    scored = [(s, a) for s, a in scored if s > 0.0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        KBSearchResult(article=KBArticle(**article), score=score)
        for score, article in scored[: request.top_k]
    ]
