"""Test-only mock adapter package.

Sprint 52.2 Day 3.4: Houses provider-shaped mocks (e.g. MockAnthropicAdapter)
that DO NOT import the corresponding LLM SDK. Used for contract tests that
verify cache_breakpoints → provider-native marker translation without
network access or SDK dependency.

Distinct from `adapters/_testing/`: that dir hosts a generic MockChatClient
shared across categories. `_mock/` hosts provider-shaped mocks for
adapter-level cache marker contract verification.
"""

from adapters._mock.anthropic_adapter import MockAnthropicAdapter

__all__ = ["MockAnthropicAdapter"]
