"""
File: backend/tests/integration/business_domain/test_business_tools_via_registry.py
Purpose: Execute all 18 business ToolSpecs through ToolRegistryImpl; httpx routed in-process via ASGI.  # noqa: E501
Category: Tests / Integration / business_domain
Scope: Phase 51 / Sprint 51.0 Day 4.2; updated Sprint 51.1 Day 5 (CARRY-017)

Description:
    Verifies the full registration -> execution chain WITHOUT a running
    mock_services subprocess. Uses httpx ASGI transport to route HTTP
    requests in-process directly to the mock_services FastAPI app.

    Flow per tool:
      1. ToolCall constructed with realistic arguments
      2. ToolExecutorImpl.execute() runs the registered handler (after the
         permission gate — see permissive checker note below)
      3. Handler calls <Domain>MockExecutor.<method>() via httpx
      4. ASGI transport routes httpx to mock_services FastAPI app
      5. Response JSON serialized as ToolResult.content

    Sprint 51.1 Day 5 migration: switched from InMemoryToolRegistry /
    InMemoryToolExecutor (deleted) to production ToolRegistryImpl /
    ToolExecutorImpl. Several tests exercise HIGH-risk + ALWAYS_ASK tools
    (e.g. mock_rootcause_apply_fix, mock_incident_close) whose permission
    gate would normally short-circuit handler execution. To preserve the
    original "handler-routing" test focus, an `_AllowAllPermissionChecker`
    is injected — permission semantics are independently covered in
    tests/unit/agent_harness/tools/test_executor.py.

Created: 2026-04-30 (Sprint 51.0 Day 4)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest

from agent_harness._contracts import (
    ExecutionContext,
    RiskLevel,
    ToolCall,
    ToolHITLPolicy,
)
from agent_harness.tools import (
    PermissionChecker,
    PermissionDecision,
    ToolExecutorImpl,
    ToolRegistryImpl,
)
from business_domain._register_all import register_all_business_tools
from mock_services.data.loader import load_seed
from mock_services.main import app


class _AllowAllPermissionChecker(PermissionChecker):
    """Test-only checker that always returns ALLOW.

    Used to keep this suite focused on handler routing through the ASGI
    transport. Production permission semantics are covered in
    tests/unit/agent_harness/tools/test_executor.py.
    """

    def check(
        self,
        spec: Any,  # noqa: ANN401 — relax for test
        call: ToolCall,
        context: ExecutionContext,
    ) -> PermissionDecision:
        return PermissionDecision.ALLOW


@pytest.fixture(scope="module", autouse=True)
def _load_seed() -> None:
    """ASGI transport bypasses lifespan; load seed manually once per module."""
    load_seed()


@pytest.fixture(autouse=True)
def patched_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route every httpx.AsyncClient request to the mock_services ASGI app in-process."""
    transport = httpx.ASGITransport(app=app)
    OriginalClient = httpx.AsyncClient

    class ASGIClient(OriginalClient):  # type: ignore[misc]
        def __init__(self, **kwargs: Any) -> None:
            kwargs.pop("timeout", None)
            super().__init__(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", ASGIClient)


@pytest.fixture
def registry_and_executor() -> tuple[ToolRegistryImpl, ToolExecutorImpl]:
    registry = ToolRegistryImpl()
    handlers: dict[str, Any] = {}
    register_all_business_tools(registry, handlers)
    executor = ToolExecutorImpl(
        registry=registry,
        handlers=handlers,
        permission_checker=_AllowAllPermissionChecker(),
    )
    return registry, executor


def _call(name: str, args: dict[str, Any]) -> ToolCall:
    return ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=args)


@pytest.mark.asyncio
async def test_registry_has_18_business_tools(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    registry, _ = registry_and_executor
    specs = registry.list()
    assert len(specs) == 18
    names = {s.name for s in specs}
    # 5 domains, prefixed
    assert sum(1 for n in names if n.startswith("mock_patrol_")) == 4
    assert sum(1 for n in names if n.startswith("mock_correlation_")) == 3
    assert sum(1 for n in names if n.startswith("mock_rootcause_")) == 3
    assert sum(1 for n in names if n.startswith("mock_audit_")) == 3
    assert sum(1 for n in names if n.startswith("mock_incident_")) == 5


@pytest.mark.asyncio
async def test_high_risk_tools_use_first_class_fields() -> None:
    """Sprint 51.1 CARRY-021: HIGH-risk tools use first-class hitl_policy /
    risk_level fields, not tags-encoded `risk:high` / `hitl_policy:always_ask`.
    """
    registry = ToolRegistryImpl()
    handlers: dict[str, Any] = {}
    register_all_business_tools(registry, handlers)

    high_risk = [s for s in registry.list() if s.risk_level is RiskLevel.HIGH]
    assert {s.name for s in high_risk} == {
        "mock_rootcause_apply_fix",
        "mock_incident_close",
    }
    for spec in high_risk:
        assert spec.hitl_policy is ToolHITLPolicy.ALWAYS_ASK
        assert spec.annotations.destructive is True
        # tags must NOT contain legacy encoding
        for tag in spec.tags:
            assert not tag.startswith("hitl_policy:")
            assert not tag.startswith("risk:")


@pytest.mark.asyncio
async def test_patrol_check_servers(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(
        _call("mock_patrol_check_servers", {"scope": ["web-01", "web-02"]})
    )
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert all("health" in r for r in payload)


@pytest.mark.asyncio
async def test_patrol_get_results(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(_call("mock_patrol_get_results", {"patrol_id": "pat_001"}))
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert payload["server_id"] == "web-01"


@pytest.mark.asyncio
async def test_correlation_find_root_cause(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(
        _call("mock_correlation_find_root_cause", {"incident_id": "inc_002"})
    )
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert payload[0]["confidence"] >= payload[-1]["confidence"]  # sorted desc


@pytest.mark.asyncio
async def test_rootcause_diagnose(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(_call("mock_rootcause_diagnose", {"incident_id": "inc_001"}))
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert payload["incident_id"] == "inc_001"
    assert "hypothesis" in payload


@pytest.mark.asyncio
async def test_rootcause_apply_fix_dry_run(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(
        _call(
            "mock_rootcause_apply_fix",
            {"fix_id": "fix_test_001", "dry_run": True},
        )
    )
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert payload["dry_run"] is True
    assert payload["status"] == "dry_run_ok"


@pytest.mark.asyncio
async def test_audit_query_logs(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(_call("mock_audit_query_logs", {"limit": 5}))
    assert result.success is True
    payload = json.loads(result.content) if isinstance(result.content, str) else result.content
    assert isinstance(payload, list)


@pytest.mark.asyncio
async def test_incident_create_then_close(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor

    create_result = await executor.execute(
        _call(
            "mock_incident_create",
            {"title": "Integration test incident", "severity": "medium"},
        )
    )
    assert create_result.success is True
    created = (
        json.loads(create_result.content)
        if isinstance(create_result.content, str)
        else create_result.content
    )
    assert created["id"].startswith("inc_live_")

    close_result = await executor.execute(
        _call(
            "mock_incident_close",
            {"incident_id": created["id"], "resolution": "test resolution"},
        )
    )
    assert close_result.success is True
    closed = (
        json.loads(close_result.content)
        if isinstance(close_result.content, str)
        else close_result.content
    )
    assert closed["status"] == "closed_pending_review"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error_result(
    registry_and_executor: tuple[ToolRegistryImpl, ToolExecutorImpl],
) -> None:
    _, executor = registry_and_executor
    result = await executor.execute(_call("nonexistent_tool", {}))
    assert result.success is False
    assert "unknown tool" in (result.error or "")
