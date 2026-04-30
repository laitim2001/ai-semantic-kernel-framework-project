"""
File: tests/unit/agent_harness/context_mgmt/test_jit_retrieval.py
Purpose: Unit tests for PointerResolver (impl ships Day 3.4).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3 (placeholder created Day 1.8)

Test plan (Day 3.5): 4 tests
  - test_db_pointer_resolves_with_tenant_filter
  - test_unknown_prefix_raises_not_supported
  - test_missing_db_session_raises_config_error
  - test_tenant_id_required_filter_enforced

Multi-tenant safety: tenant_id filter MUST be enforced; cross-tenant pointer must miss.
"""

import pytest


@pytest.mark.skip(reason="Day 3.5 implements PointerResolver + 4 tests with tenant isolation")
def test_placeholder_jit() -> None:
    """Placeholder; replaced by Day 3.5 (4 tests including red-team for tenant filter)."""
