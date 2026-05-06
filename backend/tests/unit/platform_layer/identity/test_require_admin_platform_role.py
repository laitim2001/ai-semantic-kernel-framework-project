"""
File: backend/tests/unit/platform_layer/identity/test_require_admin_platform_role.py
Purpose: Unit tests for require_admin_platform_role JWT-claim-based RBAC dep.
Category: Tests / Platform / Identity
Scope: Sprint 56.2 / Day 1 / US-4 (closes AD-AdminAuth-1)
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from platform_layer.identity.auth import require_admin_platform_role


def _make_request(*, user_id: object, roles: object) -> SimpleNamespace:
    """Build a minimal Request stub with .state.user_id + .state.roles."""
    state = SimpleNamespace(user_id=user_id, roles=roles)
    return SimpleNamespace(state=state)


class TestRequireAdminPlatformRole:
    @pytest.mark.asyncio
    async def test_admin_role_passes(self) -> None:
        """Generic 'admin' role grants platform-admin access."""
        user_id = uuid4()
        request = _make_request(user_id=user_id, roles=["admin"])
        result = await require_admin_platform_role(request)  # type: ignore[arg-type]
        assert result == user_id

    @pytest.mark.asyncio
    async def test_platform_admin_role_passes(self) -> None:
        """Explicit 'platform_admin' role grants platform-admin access."""
        user_id = uuid4()
        request = _make_request(user_id=user_id, roles=["platform_admin"])
        result = await require_admin_platform_role(request)  # type: ignore[arg-type]
        assert result == user_id

    @pytest.mark.asyncio
    async def test_tenant_admin_role_rejected_403(self) -> None:
        """Tenant-scoped admins cannot create / suspend / archive other tenants."""
        user_id = uuid4()
        request = _make_request(user_id=user_id, roles=["tenant_admin"])
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_platform_role(request)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 403
        assert "Platform admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_no_roles_in_state_500(self) -> None:
        """Middleware contract violated → 500 (not 403; signals system bug)."""
        user_id = uuid4()
        request = _make_request(user_id=user_id, roles=None)
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_platform_role(request)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 500
        assert "roles middleware contract violated" in exc_info.value.detail
