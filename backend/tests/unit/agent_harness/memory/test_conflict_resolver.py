"""
File: backend/tests/unit/agent_harness/memory/test_conflict_resolver.py
Purpose: Unit tests for 4-rule conflict resolver.
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 3.4

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agent_harness._contracts import MemoryHint
from agent_harness.memory.conflict_resolver import (
    RequiresHumanReviewError,
    resolve,
)


def _hint(
    *,
    layer: str = "user",
    confidence: float = 0.5,
    last_verified_at: datetime | None = None,
    relevance: float = 0.5,
) -> MemoryHint:
    return MemoryHint(
        hint_id=uuid4(),
        layer=layer,  # type: ignore[arg-type]
        time_scale="long_term",
        summary="x",
        confidence=confidence,
        relevance_score=relevance,
        full_content_pointer="p",
        timestamp=datetime.now(timezone.utc),
        last_verified_at=last_verified_at,
    )


def test_empty_raises_value_error() -> None:
    with pytest.raises(ValueError):
        resolve([])


def test_single_hint_returns_immediately() -> None:
    h = _hint()
    assert resolve([h]) is h


def test_rule1_high_confidence_wins() -> None:
    """Rule 1: exactly one hint with confidence >= 0.8 wins."""
    a = _hint(confidence=0.95)
    b = _hint(confidence=0.5)
    c = _hint(confidence=0.6)
    assert resolve([a, b, c]) is a


def test_rule1_skipped_when_two_high_confidence() -> None:
    """Rule 1 only fires when EXACTLY one is >=0.8; falls through otherwise."""
    a = _hint(layer="user", confidence=0.9)
    b = _hint(layer="tenant", confidence=0.9)
    # No fresh verifications + layer specificity decides: user > tenant
    chosen = resolve([a, b])
    assert chosen is a  # Rule 3 picks user


def test_rule2_freshly_verified_wins() -> None:
    """Rule 2: hints verified within 7 days; latest verified wins."""
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    stale = _hint(confidence=0.7, last_verified_at=now - timedelta(days=10))
    fresh_old = _hint(confidence=0.7, last_verified_at=now - timedelta(days=6, hours=12))
    fresh_new = _hint(confidence=0.7, last_verified_at=now - timedelta(days=1))
    assert resolve([stale, fresh_old, fresh_new], now=now) is fresh_new


def test_rule3_layer_specificity_user_over_tenant() -> None:
    """Rule 3: user > role > tenant > system; session takes top precedence."""
    user_hint = _hint(layer="user", confidence=0.6)
    tenant_hint = _hint(layer="tenant", confidence=0.6)
    system_hint = _hint(layer="system", confidence=0.6)
    assert resolve([user_hint, tenant_hint, system_hint]) is user_hint


def test_rule3_session_top_priority() -> None:
    session_hint = _hint(layer="session", confidence=0.5)
    user_hint = _hint(layer="user", confidence=0.5)
    assert resolve([session_hint, user_hint]) is session_hint


def test_rule4_fallback_raises_human_review() -> None:
    """Rule 4: same-layer + same-confidence + no fresh verification -> HITL."""
    a = _hint(layer="user", confidence=0.5)
    b = _hint(layer="user", confidence=0.5)
    with pytest.raises(RequiresHumanReviewError):
        resolve([a, b])
