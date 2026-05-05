"""
File: backend/tests/unit/api/v1/chat/test_verification_wire.py
Purpose: Unit tests for AD-Cat10-Wire-1 (chat router 2-mode CHAT_VERIFICATION_MODE wiring).
Category: 範疇 10 (Verification Loops) / Tests
Scope: Sprint 55.5 Day 1 (Option E 2-mode post-D4+D5)

Description:
    Validates the 2-mode dispatch helpers in `api.v1.chat._verifier_factory`
    and the pydantic Literal validation on Settings.chat_verification_mode.
    Per AD-Cat10-Wire-1 acceptance:
        - "disabled" (default) → select_verifier_registry returns None
        - "enabled" → select_verifier_registry returns populated VerifierRegistry
        - factory default contains 1 RulesBasedVerifier with empty rules
        - pydantic rejects unknown modes (e.g. "shadow" — 3-mode legacy)

Created: 2026-05-05 (Sprint 55.5 Day 1)
Last Modified: 2026-05-05

Modification History (newest-first):
    - 2026-05-05: Initial creation (Sprint 55.5 Day 1) — close AD-Cat10-Wire-1 (Option E 2-mode)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_harness.verification import RulesBasedVerifier, VerifierRegistry
from api.v1.chat._verifier_factory import (
    build_default_verifier_registry,
    select_verifier_registry,
)
from core.config import Settings


class TestBuildDefaultVerifierRegistry:
    """AD-Cat10-Wire-1 — factory returns no-op default registry."""

    def test_factory_default_contains_rules_based_no_op(self) -> None:
        """Factory yields VerifierRegistry with one RulesBasedVerifier(rules=[])."""
        registry = build_default_verifier_registry()
        assert isinstance(registry, VerifierRegistry)
        assert len(registry) == 1
        verifier = registry.get_all()[0]
        assert isinstance(verifier, RulesBasedVerifier)


class TestSelectVerifierRegistry:
    """AD-Cat10-Wire-1 — 2-mode dispatch (Option E post-D4+D5)."""

    def test_disabled_mode_injects_none_registry(self) -> None:
        """'disabled' mode → None → wrapper transparently delegates to loop.run()."""
        result = select_verifier_registry("disabled")
        assert result is None

    def test_enabled_mode_injects_populated_registry(self) -> None:
        """'enabled' mode → populated registry → wrapper runs verifiers."""
        result = select_verifier_registry("enabled")
        assert isinstance(result, VerifierRegistry)
        assert len(result) >= 1
        # Default registry contains exactly the no-op RulesBasedVerifier
        assert isinstance(result.get_all()[0], RulesBasedVerifier)


class TestSettingsValidation:
    """AD-Cat10-Wire-1 — pydantic Literal["disabled", "enabled"] rejects 3-mode legacy values."""

    def test_invalid_mode_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """3-mode legacy value 'shadow' rejected by pydantic Literal validation.

        Sprint 55.5 D4+D5 drift response: real run_with_verification supports
        only 2 modes via registry-presence dispatch; no shadow/enforce. Settings
        Literal must enforce this at construction time.
        """
        monkeypatch.setenv("CHAT_VERIFICATION_MODE", "shadow")
        with pytest.raises(ValidationError):
            Settings()
