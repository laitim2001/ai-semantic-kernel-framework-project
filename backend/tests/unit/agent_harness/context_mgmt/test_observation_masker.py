"""
File: tests/unit/agent_harness/context_mgmt/test_observation_masker.py
Purpose: Unit tests for DefaultObservationMasker (impl ships Day 3.1).
Category: Tests / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 3 (placeholder created Day 1.8)

Test plan (Day 3.2): 6 tests
  - test_12turn_keep_recent_5_redacts_1to7_intact_8to12  (core case)
  - test_preserves_tool_calls_field
  - test_handles_empty_messages
  - test_handles_single_turn
  - test_honors_keep_recent_override
  - test_skips_non_tool_messages
"""

import pytest


@pytest.mark.skip(reason="Day 3.2 implements DefaultObservationMasker + 6 tests")
def test_placeholder_masker() -> None:
    """Placeholder; replaced by Day 3.2 (6 tests covering masker behaviour)."""
