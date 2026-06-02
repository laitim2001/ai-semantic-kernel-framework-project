"""
File: backend/tests/unit/platform_layer/handoff/test_service.py
Purpose: Unit tests for HandoffService.boot_handoff (Sprint 57.68 A-3b)
Category: Tests
Created: 2026-06-02
Modified: 2026-06-02

Mocks SessionRepository + append_audit at the service module so the atomic
boot logic (persona resolve → tenant guard → child create → parent mark →
audit) is verified without a live DB. The multi-tenant 鐵律 (child uses the
parent's tenant_id; foreign/missing parent rejected) and unknown-target
rejection (no boot) are exercised.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

import platform_layer.handoff.service as service_mod
from platform_layer.handoff.service import (
    HandoffError,
    HandoffResult,
    HandoffService,
)


class _FakeTransaction:
    """Async context manager standing in for db.begin() / db.begin_nested()."""

    def __init__(self) -> None:
        self.entered = False
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "_FakeTransaction":
        self.entered = True
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        return False  # do not suppress exceptions


class _FakeSession:
    """Minimal AsyncSession stand-in: only what HandoffService touches."""

    def __init__(self, *, in_tx: bool = False) -> None:
        self._in_tx = in_tx
        self.transaction = _FakeTransaction()

    def in_transaction(self) -> bool:
        return self._in_tx

    def begin(self) -> _FakeTransaction:
        return self.transaction

    def begin_nested(self) -> _FakeTransaction:
        return self.transaction


class _FakeParent:
    def __init__(self, *, id: UUID, tenant_id: UUID) -> None:
        self.id = id
        self.tenant_id = tenant_id


class _FakeRepo:
    """Records calls; parent presence is keyed by (session_id, tenant_id)."""

    def __init__(self, db: Any, *, parents: dict[tuple[UUID, UUID], _FakeParent]) -> None:
        self._db = db
        self._parents = parents
        self.created: dict[str, Any] | None = None
        self.marked: dict[str, Any] | None = None

    async def get_session(self, *, session_id: UUID, tenant_id: UUID) -> Any:
        return self._parents.get((session_id, tenant_id))

    async def create_session(self, **kwargs: Any) -> Any:
        self.created = kwargs
        return _FakeParent(id=kwargs["session_id"], tenant_id=kwargs["tenant_id"])

    async def mark_handed_off(self, *, session_id: UUID, tenant_id: UUID) -> int:
        self.marked = {"session_id": session_id, "tenant_id": tenant_id}
        return 1


@pytest.fixture
def _wire(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install fake repo + audit capture; return a builder for the test setup."""
    audit_calls: list[dict[str, Any]] = []

    async def _fake_append_audit(db: Any, **kwargs: Any) -> Any:
        audit_calls.append(kwargs)
        return object()

    monkeypatch.setattr(service_mod, "append_audit", _fake_append_audit)

    state: dict[str, Any] = {"repo": None, "audit_calls": audit_calls}

    def _build(parents: dict[tuple[UUID, UUID], _FakeParent]) -> _FakeRepo:
        def _repo_factory(db: Any) -> _FakeRepo:
            repo = _FakeRepo(db, parents=parents)
            state["repo"] = repo
            return repo

        monkeypatch.setattr(service_mod, "SessionRepository", _repo_factory)
        return state  # type: ignore[return-value]

    return _build


@pytest.mark.asyncio
async def test_boot_handoff_happy_path(_wire: Any) -> None:
    tenant_id = uuid4()
    parent_id = uuid4()
    user_id = uuid4()
    state = _wire({(parent_id, tenant_id): _FakeParent(id=parent_id, tenant_id=tenant_id)})
    db = _FakeSession()

    result = await HandoffService().boot_handoff(
        parent_session_id=parent_id,
        target_agent="researcher",
        reason="needs deep dive",
        tenant_id=tenant_id,
        user_id=user_id,
        db=db,
    )

    assert isinstance(result, HandoffResult)
    repo = state["repo"]

    # Child created under PARENT's tenant_id, linked, persona in meta_data.
    assert repo.created is not None
    assert repo.created["tenant_id"] == tenant_id
    assert repo.created["user_id"] == user_id
    assert repo.created["handoff_parent_id"] == parent_id
    assert repo.created["meta_data"] == {"agent_role": "researcher"}
    assert repo.created["session_id"] == result.new_session_id

    # Parent marked handed_off (tenant-scoped).
    assert repo.marked == {"session_id": parent_id, "tenant_id": tenant_id}

    # Audit row written with the right kwargs.
    assert len(state["audit_calls"]) == 1
    audit = state["audit_calls"][0]
    assert audit["operation"] == "session.handoff"
    assert audit["resource_type"] == "session"
    assert audit["resource_id"] == str(parent_id)
    assert audit["tenant_id"] == tenant_id
    assert audit["user_id"] == user_id
    assert audit["operation_data"]["target_agent"] == "researcher"
    assert audit["operation_data"]["new_session_id"] == str(result.new_session_id)
    assert audit["operation_data"]["reason"] == "needs deep dive"

    # Transaction committed.
    assert db.transaction.committed is True


@pytest.mark.asyncio
async def test_boot_handoff_unknown_target_raises_no_boot(_wire: Any) -> None:
    tenant_id = uuid4()
    parent_id = uuid4()
    state = _wire({(parent_id, tenant_id): _FakeParent(id=parent_id, tenant_id=tenant_id)})
    db = _FakeSession()

    with pytest.raises(HandoffError, match="unknown handoff target_agent"):
        await HandoffService().boot_handoff(
            parent_session_id=parent_id,
            target_agent="totally-unknown",
            reason="x",
            tenant_id=tenant_id,
            user_id=uuid4(),
            db=db,
        )

    # No session booted, no transaction opened, no audit written.
    assert state["repo"] is None
    assert state["audit_calls"] == []
    assert db.transaction.entered is False


@pytest.mark.asyncio
async def test_boot_handoff_cross_tenant_parent_rejected(_wire: Any) -> None:
    """Multi-tenant 鐵律: a parent in another tenant is not found → reject."""
    parent_tenant = uuid4()
    caller_tenant = uuid4()  # different tenant trying to hand off
    parent_id = uuid4()
    # Parent exists only under parent_tenant; caller_tenant lookup returns None.
    state = _wire({(parent_id, parent_tenant): _FakeParent(id=parent_id, tenant_id=parent_tenant)})
    db = _FakeSession()

    with pytest.raises(HandoffError, match="not found in tenant"):
        await HandoffService().boot_handoff(
            parent_session_id=parent_id,
            target_agent="researcher",
            reason="x",
            tenant_id=caller_tenant,
            user_id=uuid4(),
            db=db,
        )

    repo = state["repo"]
    # Transaction opened (persona resolved) but nothing created / marked / audited.
    assert repo.created is None
    assert repo.marked is None
    assert state["audit_calls"] == []
    assert db.transaction.rolled_back is True


@pytest.mark.asyncio
async def test_boot_handoff_uses_begin_nested_when_in_transaction(_wire: Any) -> None:
    tenant_id = uuid4()
    parent_id = uuid4()
    state = _wire({(parent_id, tenant_id): _FakeParent(id=parent_id, tenant_id=tenant_id)})
    db = _FakeSession(in_tx=True)

    await HandoffService().boot_handoff(
        parent_session_id=parent_id,
        target_agent="reviewer",
        reason="check it",
        tenant_id=tenant_id,
        user_id=uuid4(),
        db=db,
    )
    # Single shared fake transaction object is used for both begin/begin_nested,
    # so we just assert it committed (the in_tx branch was taken without error).
    assert db.transaction.committed is True
    assert state["repo"].created["meta_data"] == {"agent_role": "reviewer"}
