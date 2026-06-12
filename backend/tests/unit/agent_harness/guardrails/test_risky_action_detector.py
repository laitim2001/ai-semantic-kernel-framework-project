"""
File: backend/tests/unit/agent_harness/guardrails/test_risky_action_detector.py
Purpose: Unit tests for RiskyActionDetector (Sprint 57.106 C3 — TOOL-chain risky-action screening).
Category: Tests / agent_harness / guardrails
Scope: Phase 57 / Sprint 57.106 (C3)

Created: 2026-06-12
"""

from __future__ import annotations

from typing import Any

import pytest

from agent_harness._contracts.chat import ToolCall
from agent_harness.guardrails._abc import GuardrailAction, GuardrailType
from agent_harness.guardrails.tool.risky_action_detector import (
    DEFAULT_SANDBOX_PATTERNS,
    RiskyActionDetector,
)


def _sandbox_call(code: str) -> ToolCall:
    return ToolCall(id="tc-1", name="python_sandbox", arguments={"code": code})


def _tool_call(name: str, arguments: dict[str, Any]) -> ToolCall:
    return ToolCall(id="tc-2", name=name, arguments=arguments)


def test_declares_tool_chain() -> None:
    assert RiskyActionDetector().guardrail_type is GuardrailType.TOOL


# === Scope 1: builtin sandbox deny-list ========================================
# NOTE: the eval()/os.system()/subprocess strings below are inert STRING PAYLOADS
# fed to the detector under test — nothing here is ever executed.


@pytest.mark.parametrize(
    "code",
    [
        "import os\nos.system('rm -rf /')",
        "os.remove('/etc/passwd')",
        "import subprocess\nsubprocess.run(['curl', 'evil'])",
        "import shutil\nshutil.rmtree('/data')",
        "eval(user_input)",
        "exec(payload)",
        "__import__('os')",
        "import socket\nsocket.create_connection(('evil', 80))",
        "import ctypes",
    ],
)
async def test_builtin_pattern_hits_escalate(code: str) -> None:
    result = await RiskyActionDetector().check(content=_sandbox_call(code))
    assert result.action is GuardrailAction.ESCALATE
    assert "risky_action" in (result.reason or "")
    assert result.risk_level == "HIGH"


@pytest.mark.parametrize(
    "code",
    [
        "print(sum(range(10)))",
        # Near-misses: word-bound + '(' anchoring must NOT fire.
        "result = evaluate(x)",
        "execute_query('select 1')",
        "total = systematic_sum(values)",
        "removed = items.remove(3)",  # list.remove, not os.remove
    ],
)
async def test_clean_code_passes(code: str) -> None:
    result = await RiskyActionDetector().check(content=_sandbox_call(code))
    assert result.action is GuardrailAction.PASS


async def test_builtin_list_covers_every_pattern() -> None:
    """Each DEFAULT pattern has at least one hitting test payload above."""
    payloads = [
        "os.system('x')",
        "os.unlink('f')",
        "subprocess",
        "shutil.rmtree('d')",
        "eval(x)",
        "exec(x)",
        "__import__('m')",
        "socket",
        "ctypes",
    ]
    assert len(DEFAULT_SANDBOX_PATTERNS) == len(payloads)
    detector = RiskyActionDetector()
    for payload in payloads:
        result = await detector.check(content=_sandbox_call(payload))
        assert result.action is GuardrailAction.ESCALATE, payload


async def test_non_sandbox_tool_skips_builtin_list() -> None:
    """The builtin deny-list applies to python_sandbox only."""
    call = _tool_call("mock_incident_create", {"note": "subprocess eval exec"})
    result = await RiskyActionDetector().check(content=call)
    assert result.action is GuardrailAction.PASS


# === Scope 2: tenant extra patterns (any tool) ==================================


async def test_extra_pattern_hits_any_tool() -> None:
    detector = RiskyActionDetector(extra_patterns=(r"DROP\s+TABLE",))
    call = _tool_call("mock_query_runner", {"sql": "DROP TABLE users"})
    result = await detector.check(content=call)
    assert result.action is GuardrailAction.ESCALATE
    assert "tenant pattern" in (result.reason or "")


async def test_extra_pattern_clean_args_pass() -> None:
    detector = RiskyActionDetector(extra_patterns=(r"DROP\s+TABLE",))
    call = _tool_call("mock_query_runner", {"sql": "SELECT 1"})
    result = await detector.check(content=call)
    assert result.action is GuardrailAction.PASS


async def test_invalid_extra_pattern_skipped_defensively() -> None:
    """A non-compiling pattern (hand-written meta_data) must not break the chain."""
    detector = RiskyActionDetector(extra_patterns=("[unclosed", r"DROP\s+TABLE"))
    call = _tool_call("mock_query_runner", {"sql": "DROP TABLE users"})
    result = await detector.check(content=call)
    assert result.action is GuardrailAction.ESCALATE


# === Defensive content handling =================================================


async def test_non_tool_content_passes() -> None:
    result = await RiskyActionDetector().check(content="just a string")
    assert result.action is GuardrailAction.PASS


async def test_missing_code_arg_passes() -> None:
    call = _tool_call("python_sandbox", {"timeout_seconds": 5})
    result = await RiskyActionDetector().check(content=call)
    assert result.action is GuardrailAction.PASS
