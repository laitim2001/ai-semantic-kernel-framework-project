"""
File: backend/tests/unit/agent_harness/orchestrator_loop/test_handle_tool_error.py
Purpose: Unit tests for AgentLoopImpl._handle_tool_error error_class_str path (AD-Cat8-3).
Category: Tests / 範疇 1 + 範疇 8 boundary
Scope: Phase 55 / Sprint 55.4 Day 1

Description:
    Sprint 55.4 closes AD-Cat8-3 narrow Option C: when soft-failure
    ToolResult arrives, ToolExecutorImpl preserves the tool's original
    exception type as a fully-qualified class name string in
    `ToolResult.error_class` (Sprint 53.3 US-9 mechanism). The
    `_handle_tool_error()` helper now accepts an optional
    `error_class_str` param so the soft-failure path classifies via
    `policy.classify_by_string()` instead of `policy.classify(synthetic)`
    (which would always walk the MRO of a generic `Exception` and
    return FATAL — losing all type-specific policy decisions).

    These tests verify the two classification paths plus an unknown
    string fallback.

Created: 2026-05-05 (Sprint 55.4 Day 1 — AD-Cat8-3 narrow Option C)
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from agent_harness._contracts.observability import TraceContext
from agent_harness.error_handling._abc import ErrorClass
from agent_harness.error_handling.policy import DefaultErrorPolicy
from agent_harness.orchestrator_loop.loop import AgentLoopImpl


@pytest.fixture
def policy() -> DefaultErrorPolicy:
    """Policy with a registered FQ class name for classify_by_string()."""
    p = DefaultErrorPolicy(max_attempts=3)
    p.register_by_string(
        "tests.fake_module.NetworkTimeoutError",
        ErrorClass.TRANSIENT,
    )
    return p


@pytest.fixture
def loop_with_policy(policy: DefaultErrorPolicy) -> AgentLoopImpl:
    """Minimal AgentLoopImpl with only error_policy + tenant_id wired."""
    return AgentLoopImpl(
        chat_client=MagicMock(),
        output_parser=MagicMock(),
        tool_executor=MagicMock(),
        tool_registry=MagicMock(),
        tenant_id=uuid4(),
        error_policy=policy,
    )


@pytest.mark.asyncio
async def test_handle_tool_error_with_error_class_str_uses_classify_by_string(
    loop_with_policy: AgentLoopImpl,
) -> None:
    """When error_class_str provided, classify_by_string() resolves to TRANSIENT.

    AD-Cat8-3 narrow Option C critical path: soft-failure synthetic
    Exception is generic, but error_class_str carries the original tool
    exception's FQ class name (set by ToolExecutorImpl per 53.3 US-9).
    Without this fix, classify(synthetic) walks Exception MRO → FATAL.
    """
    _terminate, cls, _reason, _detail = await loop_with_policy._handle_tool_error(
        error=Exception("synthetic from soft-failure"),
        tool_name="tool_a",
        attempt_num=1,
        state_version=None,
        trace_context=TraceContext.create_root(),
        error_class_str="tests.fake_module.NetworkTimeoutError",
    )
    assert cls == ErrorClass.TRANSIENT


@pytest.mark.asyncio
async def test_handle_tool_error_without_error_class_str_uses_mro_classify(
    loop_with_policy: AgentLoopImpl,
) -> None:
    """Default path (hard-exception caller at loop.py:1033): classify(error) MRO walk.

    Generic Exception is not registered → FATAL. Regression: this is
    the pre-Sprint 55.4 baseline that existing call site (line 1033)
    depends on; default ``error_class_str=None`` must preserve it.
    """
    _terminate, cls, _reason, _detail = await loop_with_policy._handle_tool_error(
        error=Exception("hard error from raise path"),
        tool_name="tool_a",
        attempt_num=1,
        state_version=None,
        trace_context=TraceContext.create_root(),
    )
    assert cls == ErrorClass.FATAL


@pytest.mark.asyncio
async def test_handle_tool_error_unknown_class_str_returns_fatal(
    loop_with_policy: AgentLoopImpl,
) -> None:
    """Unregistered FQ class string → classify_by_string() default = FATAL.

    Per policy.py:176 ``return self._registry_by_str.get(class_str,
    ErrorClass.FATAL)``. This is the safe fallback when adapters / tools
    raise an exception type that has not been registered with the policy.
    """
    _terminate, cls, _reason, _detail = await loop_with_policy._handle_tool_error(
        error=Exception("synthetic from soft-failure"),
        tool_name="tool_a",
        attempt_num=1,
        state_version=None,
        trace_context=TraceContext.create_root(),
        error_class_str="totally.unregistered.NotKnownError",
    )
    assert cls == ErrorClass.FATAL
