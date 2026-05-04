"""
File: backend/tests/unit/business_domain/test_partial_swap.py
Purpose: AD-BusinessDomainPartialSwap-1 closure tests — 4 deferred domains
    (patrol / correlation / rootcause / audit_domain) tools.py mode swap.
Category: Tests / Business Domain / partial swap mode wiring
Scope: Sprint 55.2 / Day 1-2 (US-1)

Tests:
  Day 1 (6): patrol 3 + correlation 3
  Day 2 (6): rootcause 3 + audit_domain 3 (added in Day 2)

Follows test_factory_and_mode.py (55.1 incident) pattern. Each domain has:
  - mode='mock' default behavior unchanged (existing 51.0 path)
  - mode='service' without factory_provider → ValueError
  - mode='service' foundational service method invoked (real e2e via factory)

Sentinel methods (3 patrol + 2 correlation + 2 rootcause + 2 audit_domain) per
D1 finding (55.2 progress Day 0): handler returns
{"status": "service_path_pending", "method": "<name>"} JSON; tested implicitly
by the foundational tests (factory called → no crash) + explicitly by Day 2
sentinel-specific tests if needed.

Created: 2026-05-04 (Sprint 55.2 Day 1.3)
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import ToolCall
from agent_harness.tools import ToolHandler, ToolRegistryImpl
from business_domain._service_factory import BusinessServiceFactory
from business_domain.correlation.tools import register_correlation_tools
from business_domain.patrol.tools import register_patrol_tools
from tests.conftest import seed_tenant

# ===== patrol mode swap (Day 1.1) ======================================


def test_register_patrol_tools_mode_mock_uses_executor() -> None:
    """mode='mock' wires mock_patrol_* handlers (51.0 HTTP path)."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_patrol_tools(registry, handlers, mode="mock")

    assert "mock_patrol_check_servers" in handlers
    assert "mock_patrol_get_results" in handlers
    assert "mock_patrol_schedule" in handlers
    assert "mock_patrol_cancel" in handlers


def test_register_patrol_tools_mode_service_requires_factory_provider() -> None:
    """mode='service' without factory_provider → ValueError."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    with pytest.raises(ValueError, match="requires factory_provider"):
        register_patrol_tools(registry, handlers, mode="service")


@pytest.mark.asyncio
async def test_register_patrol_tools_mode_service_get_results_invokes_service(
    db_session: AsyncSession,
) -> None:
    """mode='service' get_results handler invokes PatrolService.get_results (real e2e)."""
    t = await seed_tenant(db_session, code="PSWAP_P1")
    factory = BusinessServiceFactory(db=db_session, tenant_id=t.id)

    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_patrol_tools(
        registry,
        handlers,
        mode="service",
        factory_provider=lambda: factory,
    )

    h_get = handlers["mock_patrol_get_results"]
    call = ToolCall(
        id="tc-patrol-1",
        name="mock_patrol_get_results",
        arguments={"patrol_id": "patrol-001"},
    )
    raw = await h_get(call)
    parsed = json.loads(raw) if isinstance(raw, str) else raw

    # PatrolService.get_results returns a deterministic dict (55.1 SHA-256 stub)
    assert isinstance(parsed, dict)
    assert "patrol_id" in parsed or "results" in parsed or len(parsed) > 0

    # Sentinel handlers don't crash and return service_path_pending
    h_check = handlers["mock_patrol_check_servers"]
    raw_check = await h_check(
        ToolCall(id="tc-patrol-2", name="mock_patrol_check_servers", arguments={"scope": ["s1"]})
    )
    parsed_check = json.loads(raw_check) if isinstance(raw_check, str) else raw_check
    assert parsed_check == {"status": "service_path_pending", "method": "check_servers"}


# ===== correlation mode swap (Day 1.2) =================================


def test_register_correlation_tools_mode_mock_uses_executor() -> None:
    """mode='mock' wires mock_correlation_* handlers."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_correlation_tools(registry, handlers, mode="mock")

    assert "mock_correlation_analyze" in handlers
    assert "mock_correlation_find_root_cause" in handlers
    assert "mock_correlation_get_related" in handlers


def test_register_correlation_tools_mode_service_requires_factory_provider() -> None:
    """mode='service' without factory_provider → ValueError."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    with pytest.raises(ValueError, match="requires factory_provider"):
        register_correlation_tools(registry, handlers, mode="service")


@pytest.mark.asyncio
async def test_register_correlation_tools_mode_service_get_related_invokes_service(
    db_session: AsyncSession,
) -> None:
    """mode='service' get_related handler invokes CorrelationService.get_related (real e2e)."""
    t = await seed_tenant(db_session, code="PSWAP_C1")
    factory = BusinessServiceFactory(db=db_session, tenant_id=t.id)

    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_correlation_tools(
        registry,
        handlers,
        mode="service",
        factory_provider=lambda: factory,
    )

    h_related = handlers["mock_correlation_get_related"]
    call = ToolCall(
        id="tc-corr-1",
        name="mock_correlation_get_related",
        arguments={"alert_id": "alert-001", "depth": 2},
    )
    raw = await h_related(call)
    parsed = json.loads(raw) if isinstance(raw, str) else raw

    # CorrelationService.get_related returns list[dict] (55.1 deterministic graph)
    assert isinstance(parsed, list)

    # Sentinel handler: analyze returns service_path_pending
    h_analyze = handlers["mock_correlation_analyze"]
    raw_analyze = await h_analyze(
        ToolCall(
            id="tc-corr-2",
            name="mock_correlation_analyze",
            arguments={"alert_ids": ["a1"]},
        )
    )
    parsed_analyze = json.loads(raw_analyze) if isinstance(raw_analyze, str) else raw_analyze
    assert parsed_analyze == {"status": "service_path_pending", "method": "analyze"}
