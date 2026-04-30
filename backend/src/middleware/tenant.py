"""
File: backend/src/middleware/tenant.py
Purpose: Tenant context middleware — extracts tenant_id from JWT and propagates.
Category: middleware
Scope: Phase 49 / Sprint 49.1 (stub; Sprint 49.2 implements)

Description:
    Sprint 49.1: stub only — defines the FastAPI dependency signature
    so api/v1/ routers can already declare `Depends(get_current_tenant)`
    without breakage.

    Sprint 49.2 implements: extract from JWT → validate → set in
    `request.state.current_tenant_id` → also `SET LOCAL app.tenant_id`
    for PostgreSQL RLS context.

Per `.claude/rules/multi-tenant-data.md`: every business endpoint MUST
inject this dependency.

Created: 2026-04-29 (Sprint 49.1 Day 3)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request


async def get_current_tenant(request: Request) -> UUID:
    """FastAPI dependency: returns current tenant UUID.

    Sprint 49.1: always raises 501 Not Implemented (Sprint 49.2 will impl).
    """
    raise HTTPException(
        status_code=501,
        detail="Tenant context middleware not implemented; Sprint 49.2",
    )
