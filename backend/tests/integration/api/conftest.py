"""
File: backend/tests/integration/api/conftest.py
Purpose: Shared fixtures for api/v1 integration tests.
Category: Tests / integration / api
Scope: Phase 53 / Sprint 53.6 (US-5 ServiceFactory test isolation)

Description:
    Resets the module-level ServiceFactory singleton between tests so each
    test gets a fresh factory bound to its own pytest-asyncio event loop.
    Without this, the first test caches a session_factory bound to its loop,
    and subsequent tests in the same process hit "Event loop is closed".

Created: 2026-05-04 (Sprint 53.6 Day 4)
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from platform_layer.governance.service_factory import reset_service_factory


@pytest.fixture(autouse=True)
def _reset_governance_singletons() -> Iterator[None]:
    """Clear ServiceFactory singleton before + after each test."""
    reset_service_factory()
    yield
    reset_service_factory()
