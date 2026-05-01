"""
File: tests/unit/agent_harness/context_mgmt/test_jit_retrieval.py
Purpose: Unit tests for PointerResolver (impl: jit_retrieval.py).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3.5

4 tests:
  - test_db_pointer_resolves_with_tenant_filter
  - test_unknown_prefix_raises_not_supported
  - test_missing_db_session_raises_config_error
  - test_tenant_id_required_filter_enforced  (red-team for tenant isolation)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from agent_harness.context_mgmt.jit_retrieval import (
    JITRetrievalConfigError,
    JITRetrievalNotSupportedError,
    PointerResolver,
    PointerTenantMismatchError,
)


class _MockDBSession:
    """Mock async DB session that records the (table, row_id, tenant_id) it was called with."""

    def __init__(self, *, return_content: str | None = "row content") -> None:
        self.return_content = return_content
        self.last_call: dict[str, object] | None = None

    async def fetch_content(
        self,
        *,
        table: str,
        row_id: UUID,
        tenant_id: UUID,
    ) -> str | None:
        self.last_call = {"table": table, "row_id": row_id, "tenant_id": tenant_id}
        return self.return_content


@pytest.mark.asyncio
async def test_db_pointer_resolves_with_tenant_filter() -> None:
    """db:// pointer resolves through the mock; tenant_id is forwarded to fetch_content."""
    db = _MockDBSession(return_content="hello memory row")
    resolver = PointerResolver(db_session=db)
    tenant = uuid4()
    row = uuid4()
    pointer = f"db://memory_user/{row}?tenant_id={tenant}"

    result = await resolver.resolve(pointer, tenant_id=tenant)

    assert result == "hello memory row"
    assert db.last_call == {
        "table": "memory_user",
        "row_id": row,
        "tenant_id": tenant,
    }


@pytest.mark.asyncio
async def test_unknown_prefix_raises_not_supported() -> None:
    """memory:// / tool:// / kb:// + unknown schemes raise JITRetrievalNotSupportedError."""
    resolver = PointerResolver(db_session=_MockDBSession())
    tenant = uuid4()

    for pointer in (
        "memory://session/abc",
        "tool://artefact/x",
        "kb://doc/y",
        "weird://something",
    ):
        with pytest.raises(JITRetrievalNotSupportedError):
            await resolver.resolve(pointer, tenant_id=tenant)


@pytest.mark.asyncio
async def test_missing_db_session_raises_config_error() -> None:
    """db:// pointer without db_session injection raises JITRetrievalConfigError."""
    resolver = PointerResolver(db_session=None)
    tenant = uuid4()
    pointer = f"db://memory_user/{uuid4()}?tenant_id={tenant}"

    with pytest.raises(JITRetrievalConfigError):
        await resolver.resolve(pointer, tenant_id=tenant)


@pytest.mark.asyncio
async def test_tenant_id_required_filter_enforced() -> None:
    """Red-team: missing tenant_id query OR mismatched tenant must raise PointerTenantMismatchError."""
    db = _MockDBSession()
    resolver = PointerResolver(db_session=db)
    runtime_tenant = uuid4()
    other_tenant = uuid4()

    # Case A: missing query
    with pytest.raises(PointerTenantMismatchError):
        await resolver.resolve(
            f"db://memory_user/{uuid4()}",
            tenant_id=runtime_tenant,
        )

    # Case B: query present but does not match runtime tenant_id (cross-tenant attempt)
    with pytest.raises(PointerTenantMismatchError):
        await resolver.resolve(
            f"db://memory_user/{uuid4()}?tenant_id={other_tenant}",
            tenant_id=runtime_tenant,
        )

    # Case C: malformed UUID in query
    with pytest.raises(PointerTenantMismatchError):
        await resolver.resolve(
            f"db://memory_user/{uuid4()}?tenant_id=not-a-uuid",
            tenant_id=runtime_tenant,
        )

    # No DB call should have been made for any of the above
    assert db.last_call is None
