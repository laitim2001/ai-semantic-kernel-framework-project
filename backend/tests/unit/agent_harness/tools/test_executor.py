"""
File: backend/tests/unit/agent_harness/tools/test_executor.py
Purpose: Unit tests for ToolExecutorImpl — permission gate / JSONSchema / concurrency.
Category: Tests / 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 2.4 + 2.5

Created: 2026-04-30
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from agent_harness._contracts import (
    ConcurrencyPolicy,
    ExecutionContext,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)
from agent_harness.tools import (
    PermissionDecision,
    ToolExecutorImpl,
    ToolRegistryImpl,
)

# === Fixtures =============================================================


def _spec(
    name: str,
    *,
    hitl: ToolHITLPolicy = ToolHITLPolicy.AUTO,
    risk: RiskLevel = RiskLevel.LOW,
    destructive: bool = False,
    concurrency: ConcurrencyPolicy = ConcurrencyPolicy.READ_ONLY_PARALLEL,
    schema: dict[str, Any] | None = None,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"test spec {name}",
        input_schema=schema
        or {
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
        annotations=ToolAnnotations(read_only=not destructive, destructive=destructive),
        concurrency_policy=concurrency,
        hitl_policy=hitl,
        risk_level=risk,
    )


def _call(name: str, args: dict[str, Any] | None = None, call_id: str = "c1") -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=args or {"q": "hi"})


async def _ok_handler(call: ToolCall) -> str:
    return f"echoed:{call.arguments.get('q')}"


async def _slow_handler(call: ToolCall) -> str:
    await asyncio.sleep(0.1)  # 100ms
    return "slow_done"


async def _explode_handler(call: ToolCall) -> str:
    raise RuntimeError("boom")


# === Permission tests (Day 2.4) ===========================================


@pytest.mark.asyncio
async def test_allow_simple_read_only() -> None:
    reg = ToolRegistryImpl()
    spec = _spec("ok_read")
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"ok_read": _ok_handler})

    result = await exe.execute(_call("ok_read"))
    assert result.success is True
    assert result.content == "echoed:hi"


@pytest.mark.asyncio
async def test_require_approval_always_ask() -> None:
    reg = ToolRegistryImpl()
    spec = _spec("sensitive", hitl=ToolHITLPolicy.ALWAYS_ASK)
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"sensitive": _ok_handler})

    result = await exe.execute(_call("sensitive"))
    assert result.success is False
    assert result.error is not None
    assert "approval required" in result.error
    assert "always_ask" in result.error


@pytest.mark.asyncio
async def test_require_approval_ask_once() -> None:
    reg = ToolRegistryImpl()
    spec = _spec("first_call", hitl=ToolHITLPolicy.ASK_ONCE)
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"first_call": _ok_handler})

    result = await exe.execute(_call("first_call"))
    assert result.success is False
    assert "approval required" in (result.error or "")


@pytest.mark.asyncio
async def test_require_approval_high_risk_overrides_auto_hitl() -> None:
    reg = ToolRegistryImpl()
    # AUTO hitl_policy but HIGH risk → still REQUIRE_APPROVAL
    spec = _spec("dangerous", hitl=ToolHITLPolicy.AUTO, risk=RiskLevel.HIGH)
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"dangerous": _ok_handler})

    result = await exe.execute(_call("dangerous"))
    assert result.success is False
    assert "approval required" in (result.error or "")
    assert "HIGH" in (result.error or "")


@pytest.mark.asyncio
async def test_deny_destructive_without_explicit_approval() -> None:
    reg = ToolRegistryImpl()
    spec = _spec("delete_db", destructive=True, concurrency=ConcurrencyPolicy.SEQUENTIAL)
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"delete_db": _ok_handler})

    result = await exe.execute(_call("delete_db"))
    assert result.success is False
    assert "permission denied" in (result.error or "")


@pytest.mark.asyncio
async def test_allow_destructive_with_explicit_approval() -> None:
    reg = ToolRegistryImpl()
    spec = _spec("delete_db", destructive=True, concurrency=ConcurrencyPolicy.SEQUENTIAL)
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"delete_db": _ok_handler})

    ctx = ExecutionContext(explicit_approval=True)
    result = await exe.execute(_call("delete_db"), context=ctx)
    assert result.success is True


@pytest.mark.asyncio
async def test_deny_beats_require_approval() -> None:
    """Resolution order: DENY > REQUIRE_APPROVAL. Destructive + ALWAYS_ASK → DENY (not approval)."""
    reg = ToolRegistryImpl()
    spec = _spec(
        "wipe",
        destructive=True,
        hitl=ToolHITLPolicy.ALWAYS_ASK,
        risk=RiskLevel.HIGH,
        concurrency=ConcurrencyPolicy.SEQUENTIAL,
    )
    reg.register(spec)
    exe = ToolExecutorImpl(registry=reg, handlers={"wipe": _ok_handler})

    result = await exe.execute(_call("wipe"))
    assert result.success is False
    assert "permission denied" in (result.error or "")


# === JSONSchema validation tests (Day 2.3) ================================


@pytest.mark.asyncio
async def test_schema_valid_arguments() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("schema_ok"))
    exe = ToolExecutorImpl(registry=reg, handlers={"schema_ok": _ok_handler})

    result = await exe.execute(_call("schema_ok", {"q": "valid"}))
    assert result.success is True


@pytest.mark.asyncio
async def test_schema_invalid_missing_required_field() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("strict"))
    exe = ToolExecutorImpl(registry=reg, handlers={"strict": _ok_handler})

    # missing required 'q'
    result = await exe.execute(_call("strict", {"wrong_key": "x"}))
    assert result.success is False
    assert "schema mismatch" in (result.error or "")


@pytest.mark.asyncio
async def test_schema_invalid_wrong_type() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("strict_type"))
    exe = ToolExecutorImpl(registry=reg, handlers={"strict_type": _ok_handler})

    # q must be string, supplying int
    result = await exe.execute(_call("strict_type", {"q": 42}))
    assert result.success is False
    assert "schema mismatch" in (result.error or "")


@pytest.mark.asyncio
async def test_schema_validator_cached_per_spec() -> None:
    """Validator is built once per spec.name and reused across calls."""
    reg = ToolRegistryImpl()
    reg.register(_spec("cached"))
    exe = ToolExecutorImpl(registry=reg, handlers={"cached": _ok_handler})

    await exe.execute(_call("cached", {"q": "first"}))
    await exe.execute(_call("cached", {"q": "second"}))

    assert "cached" in exe._validator_cache  # noqa: SLF001 — verifying internal cache
    assert len(exe._validator_cache) == 1


# === Concurrency tests (Day 2.5) ==========================================


@pytest.mark.asyncio
async def test_batch_empty_returns_empty() -> None:
    reg = ToolRegistryImpl()
    exe = ToolExecutorImpl(registry=reg, handlers={})
    assert await exe.execute_batch([]) == []


@pytest.mark.asyncio
async def test_batch_read_only_parallel_runs_concurrently() -> None:
    """3 read-only-parallel calls × 100ms slow handler should finish in ~100ms (parallel), not ~300ms."""
    reg = ToolRegistryImpl()
    reg.register(_spec("ro_a", concurrency=ConcurrencyPolicy.READ_ONLY_PARALLEL))
    reg.register(_spec("ro_b", concurrency=ConcurrencyPolicy.READ_ONLY_PARALLEL))
    reg.register(_spec("ro_c", concurrency=ConcurrencyPolicy.READ_ONLY_PARALLEL))
    exe = ToolExecutorImpl(
        registry=reg,
        handlers={"ro_a": _slow_handler, "ro_b": _slow_handler, "ro_c": _slow_handler},
    )

    calls = [_call("ro_a", call_id="a"), _call("ro_b", call_id="b"), _call("ro_c", call_id="c")]
    t0 = time.monotonic()
    results = await exe.execute_batch(calls)
    elapsed = time.monotonic() - t0

    assert len(results) == 3
    assert all(r.success for r in results)
    # parallel: ~100ms; sequential would be ~300ms. Threshold 250ms allows OS jitter.
    assert elapsed < 0.25, f"expected parallel (<250ms), got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_batch_with_sequential_runs_serial() -> None:
    """Any SEQUENTIAL spec in batch forces full-batch sequential execution."""
    reg = ToolRegistryImpl()
    reg.register(_spec("seq_a", concurrency=ConcurrencyPolicy.SEQUENTIAL))
    reg.register(_spec("ro_b", concurrency=ConcurrencyPolicy.READ_ONLY_PARALLEL))
    reg.register(_spec("ro_c", concurrency=ConcurrencyPolicy.READ_ONLY_PARALLEL))
    exe = ToolExecutorImpl(
        registry=reg,
        handlers={"seq_a": _slow_handler, "ro_b": _slow_handler, "ro_c": _slow_handler},
    )

    calls = [_call("seq_a", call_id="a"), _call("ro_b", call_id="b"), _call("ro_c", call_id="c")]
    t0 = time.monotonic()
    results = await exe.execute_batch(calls)
    elapsed = time.monotonic() - t0

    assert len(results) == 3
    # serial: ~300ms; parallel would be ~100ms. Threshold 280ms guards against false-pass parallel.
    assert elapsed > 0.28, f"expected serial (>280ms), got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_batch_all_parallel_runs_concurrently() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("p_a", concurrency=ConcurrencyPolicy.ALL_PARALLEL))
    reg.register(_spec("p_b", concurrency=ConcurrencyPolicy.ALL_PARALLEL))
    exe = ToolExecutorImpl(
        registry=reg,
        handlers={"p_a": _slow_handler, "p_b": _slow_handler},
    )

    t0 = time.monotonic()
    results = await exe.execute_batch([_call("p_a", call_id="a"), _call("p_b", call_id="b")])
    elapsed = time.monotonic() - t0

    assert len(results) == 2
    assert all(r.success for r in results)
    assert elapsed < 0.18, f"expected parallel, got {elapsed:.3f}s"


# === Edge case tests ======================================================


@pytest.mark.asyncio
async def test_unknown_tool_returns_error() -> None:
    reg = ToolRegistryImpl()
    exe = ToolExecutorImpl(registry=reg, handlers={})
    result = await exe.execute(_call("nonexistent"))
    assert result.success is False
    assert "unknown tool" in (result.error or "")


@pytest.mark.asyncio
async def test_handler_exception_propagated_via_result_error() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("explodes"))
    exe = ToolExecutorImpl(registry=reg, handlers={"explodes": _explode_handler})

    result = await exe.execute(_call("explodes"))
    assert result.success is False
    assert "boom" in (result.error or "")


@pytest.mark.asyncio
async def test_no_handler_registered_returns_error() -> None:
    reg = ToolRegistryImpl()
    reg.register(_spec("orphan"))  # spec registered but no handler
    exe = ToolExecutorImpl(registry=reg, handlers={})

    result = await exe.execute(_call("orphan"))
    assert result.success is False
    assert "no handler" in (result.error or "")


# === PermissionChecker direct tests =======================================


def test_permission_decision_enum_values() -> None:
    assert PermissionDecision.ALLOW.value == "allow"
    assert PermissionDecision.REQUIRE_APPROVAL.value == "require_approval"
    assert PermissionDecision.DENY.value == "deny"
