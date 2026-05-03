"""
File: backend/tests/integration/agent_harness/governance/test_hitl_centralization.py
Purpose: Integration tests for §HITL 中央化 — Cat 2 hitl_tools flows through
         HITLManager (US-3); Teams notifier card-build (US-6).
Category: Tests / Governance / HITL Centralization
Scope: Phase 53 / Sprint 53.4 US-3 + US-6

Created: 2026-05-03 (Sprint 53.4 Day 3)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import ToolCall
from agent_harness._contracts.hitl import ApprovalRequest, RiskLevel
from agent_harness.tools.hitl_tools import (
    make_request_approval_handler,
    request_approval_handler,
)
from infrastructure.db.models.sessions import Session as SessionModel
from platform_layer.governance.hitl.manager import DefaultHITLManager
from platform_layer.governance.hitl.notifier import NoopNotifier
from platform_layer.governance.hitl.teams_webhook import TeamsWebhookNotifier
from tests.conftest import seed_tenant, seed_user

# asyncio_mode = "auto" in pyproject.toml; only mark async tests explicitly
# where needed (we omit pytestmark so sync tests below don't trigger
# pytest-asyncio warnings).


# --------------- Helpers --------------------------------------------------


async def _seed_session(db, tenant, user) -> SessionModel:
    s = SessionModel(
        tenant_id=tenant.id,
        user_id=user.id,
        title="hitl-centralization-test",
        status="active",
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def cat2_setup(db_session: AsyncSession, monkeypatch):
    """Seed tenant + user + session; build HITLManager bound to test session."""
    tenant = await seed_tenant(db_session, code="CAT2_TEST")
    user = await seed_user(db_session, tenant, email="cat2@test.com")
    session_row = await _seed_session(db_session, tenant, user)

    async def _flush_only() -> None:
        await db_session.flush()

    monkeypatch.setattr(db_session, "commit", _flush_only)

    @asynccontextmanager
    async def factory():
        yield db_session

    manager = DefaultHITLManager(session_factory=factory, notifier=NoopNotifier().notify)
    return manager, tenant, user, session_row


# --------------- US-3: hitl_tools.request_approval flows through HITLManager


async def test_request_approval_handler_persists_via_manager(cat2_setup) -> None:
    manager, tenant, _, session_row = cat2_setup

    handler = make_request_approval_handler(
        manager,
        tenant_id_resolver=lambda call: tenant.id,
        session_id_resolver=lambda call: session_row.id,
    )

    call = ToolCall(
        id="tc-1",
        name="request_approval",
        arguments={
            "message": "send password reset email to user@external",
            "severity": "high",
        },
    )
    raw = await handler(call)
    payload = json.loads(raw)

    assert payload["status"] == "pending"
    assert payload["severity"] == "high"

    # Verify it persisted via the manager
    pending = await manager.get_pending(tenant.id)
    assert len(pending) == 1
    assert pending[0].risk_level == RiskLevel.HIGH
    assert pending[0].request_id == UUID(payload["pending_approval_id"])
    assert pending[0].requester == "tools:request_approval"


async def test_severity_low_maps_to_low_risk(cat2_setup) -> None:
    manager, tenant, _, session_row = cat2_setup
    handler = make_request_approval_handler(
        manager,
        tenant_id_resolver=lambda call: tenant.id,
        session_id_resolver=lambda call: session_row.id,
    )
    call = ToolCall(
        id="tc-low",
        name="request_approval",
        arguments={"message": "small action", "severity": "low"},
    )
    await handler(call)
    pending = await manager.get_pending(tenant.id)
    assert pending[0].risk_level == RiskLevel.LOW


async def test_unknown_severity_falls_back_to_medium(cat2_setup) -> None:
    manager, tenant, _, session_row = cat2_setup
    handler = make_request_approval_handler(
        manager,
        tenant_id_resolver=lambda call: tenant.id,
        session_id_resolver=lambda call: session_row.id,
    )
    call = ToolCall(
        id="tc-unknown",
        name="request_approval",
        arguments={"message": "ambiguous", "severity": "unknown_severity"},
    )
    await handler(call)
    pending = await manager.get_pending(tenant.id)
    assert pending[0].risk_level == RiskLevel.MEDIUM


async def test_legacy_handler_returns_placeholder_no_persist(cat2_setup) -> None:
    """Legacy handler is deprecated — does not persist via HITLManager."""
    manager, tenant, _, _ = cat2_setup
    call = ToolCall(
        id="tc-legacy",
        name="request_approval",
        arguments={"message": "legacy", "severity": "medium"},
    )
    raw = await request_approval_handler(call)
    payload = json.loads(raw)
    assert "DEPRECATED" in payload["note"]

    pending = await manager.get_pending(tenant.id)
    assert pending == []  # legacy handler does NOT persist


# --------------- US-6: Teams webhook notifier card payload


def test_teams_notifier_builds_adaptive_card_with_review_link() -> None:
    notifier = TeamsWebhookNotifier(
        default_webhook_url="https://outlook.office.com/webhook/test",
        approval_review_url_template="https://app.example/approvals/{request_id}",
    )
    req = ApprovalRequest(
        request_id=uuid4(),
        tenant_id=uuid4(),
        session_id=uuid4(),
        requester="tools:request_approval",
        risk_level=RiskLevel.HIGH,
        payload={"summary": "send wire transfer"},
        sla_deadline=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        context_snapshot={},
    )
    card = notifier._build_card(req)
    attachments = card["attachments"]
    assert len(attachments) == 1
    content = attachments[0]["content"]
    assert content["type"] == "AdaptiveCard"

    # Find risk fact
    facts = content["body"][1]["facts"]
    risk_fact = next(f for f in facts if f["title"] == "Risk:")
    assert risk_fact["value"] == "HIGH"

    actions = content["actions"]
    assert len(actions) == 1
    assert "approvals" in actions[0]["url"]
    assert str(req.request_id) in actions[0]["url"]


def test_teams_notifier_no_review_link_when_template_missing() -> None:
    notifier = TeamsWebhookNotifier(default_webhook_url="https://outlook.office.com/webhook/test")
    req = ApprovalRequest(
        request_id=uuid4(),
        tenant_id=uuid4(),
        session_id=uuid4(),
        requester="tools:request_approval",
        risk_level=RiskLevel.MEDIUM,
        payload={},
        sla_deadline=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        context_snapshot={},
    )
    card = notifier._build_card(req)
    actions = card["attachments"][0]["content"]["actions"]
    assert actions == []


def test_teams_notifier_per_tenant_override() -> None:
    """When tenant has an override URL, it's used instead of default."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    notifier = TeamsWebhookNotifier(
        default_webhook_url="https://default/webhook",
        tenant_webhook_overrides={tenant_a: "https://tenant-a/webhook"},
    )
    # Use protected access for unit-style test of internal selection
    assert notifier._tenant_overrides.get(tenant_a) == "https://tenant-a/webhook"
    assert notifier._tenant_overrides.get(tenant_b) is None
