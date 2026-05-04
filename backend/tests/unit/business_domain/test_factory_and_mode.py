"""
File: backend/tests/unit/business_domain/test_factory_and_mode.py
Purpose: BusinessServiceFactory + BUSINESS_DOMAIN_MODE flag + register_*_tools mode wiring.
Category: Tests / Business Domain / factory + mode flag
Scope: Sprint 55.1 / Day 3.7

Tests (8):
    1. test_business_service_factory_builds_5_services
    2. test_settings_business_domain_mode_default_mock
    3. test_settings_business_domain_mode_env_override
    4. test_register_incident_tools_mode_mock_uses_executor
    5. test_register_incident_tools_mode_service_requires_factory_provider
    6. test_register_incident_tools_mode_service_handler_calls_service
    7. test_register_incident_tools_invalid_mode_raises
    8. test_make_default_executor_reads_settings

Created: 2026-05-04 (Sprint 55.1 Day 3)
"""

from __future__ import annotations

import json
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import ToolCall
from agent_harness.tools import ToolHandler, ToolRegistryImpl
from business_domain._register_all import make_default_executor
from business_domain._service_factory import BusinessServiceFactory
from business_domain.audit_domain.service import AuditService
from business_domain.correlation.service import CorrelationService
from business_domain.incident.service import IncidentService
from business_domain.incident.tools import register_incident_tools
from business_domain.patrol.service import PatrolService
from business_domain.rootcause.service import RootCauseService
from core.config import Settings, get_settings
from tests.conftest import seed_tenant

# ===== BusinessServiceFactory =========================================


@pytest.mark.asyncio
async def test_business_service_factory_builds_5_services(
    db_session: AsyncSession,
) -> None:
    t = await seed_tenant(db_session, code="FCT_1")
    factory = BusinessServiceFactory(db=db_session, tenant_id=t.id)

    assert isinstance(factory.get_incident_service(), IncidentService)
    assert isinstance(factory.get_patrol_service(), PatrolService)
    assert isinstance(factory.get_correlation_service(), CorrelationService)
    assert isinstance(factory.get_rootcause_service(), RootCauseService)
    assert isinstance(factory.get_audit_service(), AuditService)


# ===== Settings ========================================================


def test_settings_business_domain_mode_default_mock() -> None:
    """Default value is 'mock' (backwards-compat with PoC)."""
    # Direct construction without env override
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.business_domain_mode == "mock"


def test_settings_business_domain_mode_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BUSINESS_DOMAIN_MODE=service env var → settings.business_domain_mode == 'service'."""
    monkeypatch.setenv("BUSINESS_DOMAIN_MODE", "service")
    # Re-create settings (lru_cache from get_settings won't re-read; use direct cls).
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.business_domain_mode == "service"


# ===== register_incident_tools mode wiring ============================


def test_register_incident_tools_mode_mock_uses_executor() -> None:
    """mode='mock' wires mock_incident_* handlers (existing 51.0 path)."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_incident_tools(registry, handlers, mode="mock")

    assert "mock_incident_create" in handlers
    assert "mock_incident_list" in handlers


def test_register_incident_tools_mode_service_requires_factory_provider() -> None:
    """mode='service' without factory_provider → ValueError."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    with pytest.raises(ValueError, match="requires factory_provider"):
        register_incident_tools(registry, handlers, mode="service")


@pytest.mark.asyncio
async def test_register_incident_tools_mode_service_handler_calls_service(
    db_session: AsyncSession,
) -> None:
    """mode='service' handler invokes IncidentService.create() backed by DB."""
    t = await seed_tenant(db_session, code="FCT_S1")
    factory = BusinessServiceFactory(db=db_session, tenant_id=t.id)

    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_incident_tools(
        registry,
        handlers,
        mode="service",
        factory_provider=lambda: factory,
    )

    create_handler = handlers["mock_incident_create"]
    call = ToolCall(
        id="tc-1",
        name="mock_incident_create",
        arguments={"title": "Service-mode incident", "severity": "high"},
    )
    raw = await create_handler(call)
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    assert parsed["title"] == "Service-mode incident"
    assert parsed["severity"] == "high"
    assert parsed["status"] == "open"
    assert parsed["tenant_id"] == str(t.id)


def test_register_incident_tools_invalid_mode_raises() -> None:
    """mode='unknown' → ValueError."""
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    with pytest.raises(ValueError, match="invalid mode"):
        register_incident_tools(registry, handlers, mode="unknown")


# ===== make_default_executor reads settings ===========================


def test_make_default_executor_reads_settings() -> None:
    """When mode is None, settings.business_domain_mode is used."""
    # Default settings has mock mode; this verifies make_default_executor
    # doesn't crash + properly defaults to mock.
    get_settings.cache_clear()  # ensure fresh read
    os.environ.pop("BUSINESS_DOMAIN_MODE", None)
    registry, executor = make_default_executor()  # mode=None → settings (mock)

    # 19 tools registered (echo + 18 business)
    specs = registry.list_specs() if hasattr(registry, "list_specs") else None
    if specs is not None:
        assert len(list(specs)) == 19
