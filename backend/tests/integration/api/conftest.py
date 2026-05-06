"""
File: backend/tests/integration/api/conftest.py
Purpose: Shared fixtures for api/v1 integration tests.
Category: Tests / integration / api
Scope: Phase 53 / Sprint 53.6 (US-5 ServiceFactory test isolation)

Description:
    Resets module-level singletons between tests so each test gets a fresh
    instance bound to its own pytest-asyncio event loop. Without this, the
    first test caches resources bound to its loop, and subsequent tests in
    the same process hit "Event loop is closed".

    Singletons reset (per testing.md §Module-level Singleton Reset Pattern):
    - ServiceFactory (53.6) — governance HITL/Risk/AuditQuery
    - SLAMetricRecorder (56.3 US-1) — Cat 12 SLA recording

Modification History:
    - 2026-05-06: Sprint 56.3 Day 1 — add reset_sla_recorder (US-1)
    - 2026-05-04: Initial (Sprint 53.6 Day 4)
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from platform_layer.governance.service_factory import reset_service_factory
from platform_layer.observability import reset_sla_recorder


@pytest.fixture(autouse=True)
def _reset_module_singletons() -> Iterator[None]:
    """Clear module-level singletons before + after each test."""
    reset_service_factory()
    reset_sla_recorder()
    yield
    reset_service_factory()
    reset_sla_recorder()
