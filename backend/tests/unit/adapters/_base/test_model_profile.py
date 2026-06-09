"""
File: backend/tests/unit/adapters/_base/test_model_profile.py
Purpose: Unit tests for the ModelProfile value object (Sprint 57.97 multi-model profile).
Category: Tests / Adapters / _base
Scope: Phase 57 / Sprint 57.97

Created: 2026-06-09
"""

from __future__ import annotations

import dataclasses
from typing import cast

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.model_profile import ModelProfile


def test_model_profile_pairs_action_and_cheap() -> None:
    """ModelProfile stores the two client references verbatim by role."""
    action = cast(ChatClient, object())
    cheap = cast(ChatClient, object())
    profile = ModelProfile(action=action, cheap=cheap)
    assert profile.action is action
    assert profile.cheap is cheap


def test_model_profile_is_frozen() -> None:
    """ModelProfile is a frozen value object — reassigning a tier raises."""
    profile = ModelProfile(action=cast(ChatClient, object()), cheap=cast(ChatClient, object()))
    with pytest.raises(dataclasses.FrozenInstanceError):
        # setattr (not direct assignment) to trigger the runtime frozen guard
        # without a static "cannot assign to frozen" type error.
        setattr(profile, "cheap", cast(ChatClient, object()))


def test_model_profile_same_instance_both_tiers() -> None:
    """The fallback shape (cheap is action) is representable — a single client both roles."""
    single = cast(ChatClient, object())
    profile = ModelProfile(action=single, cheap=single)
    assert profile.cheap is profile.action is single
