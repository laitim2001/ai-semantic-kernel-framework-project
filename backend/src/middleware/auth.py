"""
File: backend/src/middleware/auth.py
Purpose: Auth context middleware — JWT validation, user_id extraction.
Category: middleware
Scope: Phase 49 / Sprint 49.1 (stub; Sprint 49.3 implements)

Description:
    Sprint 49.1: stub only. Sprint 49.3 implements: parse Authorization
    header → validate JWT → set `request.state.current_user_id` +
    `request.state.user_roles` for RBAC checks.

Created: 2026-04-29 (Sprint 49.1 Day 3)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request


async def get_current_user(request: Request) -> UUID:
    """FastAPI dependency: returns current user UUID.

    Sprint 49.1: always raises 501; Sprint 49.3 will impl.
    """
    raise HTTPException(
        status_code=501,
        detail="Auth middleware not implemented; Sprint 49.3",
    )
