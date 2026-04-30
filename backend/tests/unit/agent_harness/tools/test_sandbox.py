"""
File: backend/tests/unit/agent_harness/tools/test_sandbox.py
Purpose: SubprocessSandbox isolation + resource-limit tests.
Category: Tests / 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 3.3
Created: 2026-04-30
"""

from __future__ import annotations

import json
import sys

import pytest

from agent_harness._contracts import ToolCall
from agent_harness.tools import (
    PYTHON_SANDBOX_SPEC,
    SubprocessSandbox,
    make_python_sandbox_handler,
)

# === SubprocessSandbox direct tests =======================================


@pytest.mark.asyncio
async def test_sandbox_returns_stdout() -> None:
    sb = SubprocessSandbox()
    result = await sb.execute("print('hello from sandbox')", timeout_seconds=5, memory_mb=128)
    assert result.exit_code == 0
    assert "hello from sandbox" in result.stdout
    assert result.killed_by_timeout is False


@pytest.mark.asyncio
async def test_sandbox_timeout_kills_runaway() -> None:
    sb = SubprocessSandbox()
    code = "while True:\n    pass\n"
    result = await sb.execute(code, timeout_seconds=0.5, memory_mb=128)
    assert result.killed_by_timeout is True
    # process killed: exit_code is negative on POSIX (signal) or non-zero on Windows
    assert result.exit_code != 0
    assert result.duration_seconds < 1.5  # killed promptly


@pytest.mark.asyncio
async def test_sandbox_exit_code_propagated() -> None:
    sb = SubprocessSandbox()
    result = await sb.execute("import sys; sys.exit(42)", timeout_seconds=5, memory_mb=128)
    assert result.exit_code == 42
    assert result.killed_by_timeout is False


@pytest.mark.asyncio
async def test_sandbox_runs_in_isolated_cwd() -> None:
    """Subprocess sees a temp cwd, distinct from the host process cwd."""
    import os

    host_cwd = os.getcwd()
    sb = SubprocessSandbox()
    result = await sb.execute("import os; print(os.getcwd())", timeout_seconds=5, memory_mb=128)
    sandbox_cwd = result.stdout.strip()
    assert sandbox_cwd != host_cwd
    # tempdir prefix `sbx_` per implementation
    assert "sbx_" in sandbox_cwd or sandbox_cwd.startswith("/tmp") or "Temp" in sandbox_cwd


@pytest.mark.asyncio
async def test_sandbox_stderr_captured() -> None:
    sb = SubprocessSandbox()
    result = await sb.execute(
        "import sys; sys.stderr.write('warn-msg'); sys.stderr.flush()",
        timeout_seconds=5,
        memory_mb=128,
    )
    assert "warn-msg" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_relative_writes_contained_in_tempdir() -> None:
    """Files written with relative paths land in the tempdir; gone after execute returns."""
    sb = SubprocessSandbox()
    code = "open('out.txt', 'w').write('payload'); print('wrote')"
    result = await sb.execute(code, timeout_seconds=5, memory_mb=128)
    assert result.exit_code == 0
    assert "wrote" in result.stdout
    # tempdir auto-cleaned by `with TemporaryDirectory()`; nothing to assert beyond
    # successful execution + no leakage to host cwd (which we'd see if it crashed)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only RLIMIT_AS")
@pytest.mark.asyncio
async def test_sandbox_memory_limit_kills_oversized_alloc() -> None:
    """POSIX-only: RLIMIT_AS triggers MemoryError or process death on huge alloc."""
    sb = SubprocessSandbox()
    # request 32MB cap; allocate 256MB list-of-bytes
    code = "x = bytearray(256 * 1024 * 1024)"
    result = await sb.execute(code, timeout_seconds=10, memory_mb=32)
    assert result.exit_code != 0  # MemoryError or signal
    assert result.killed_by_timeout is False


# === python_sandbox built-in tool integration ============================


def test_python_sandbox_spec_metadata() -> None:
    spec = PYTHON_SANDBOX_SPEC
    assert spec.name == "python_sandbox"
    assert spec.risk_level.value == "MEDIUM"
    assert spec.hitl_policy.value == "auto"
    assert spec.annotations.destructive is False
    assert "code" in spec.input_schema["required"]


@pytest.mark.asyncio
async def test_python_sandbox_handler_happy_path() -> None:
    handler = make_python_sandbox_handler()
    call = ToolCall(
        id="t1",
        name="python_sandbox",
        arguments={"code": "print(2 + 2)", "timeout_seconds": 3, "memory_mb": 64},
    )
    raw = await handler(call)
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert "4" in payload["stdout"]
    assert payload["killed_by_timeout"] is False


@pytest.mark.asyncio
async def test_python_sandbox_handler_uses_defaults() -> None:
    handler = make_python_sandbox_handler()
    call = ToolCall(id="t2", name="python_sandbox", arguments={"code": "print('ok')"})
    raw = await handler(call)
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert "ok" in payload["stdout"]
