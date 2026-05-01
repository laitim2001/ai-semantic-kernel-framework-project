"""
File: backend/src/business_domain/_register_all.py
Purpose: One-call aggregator registering all 5 business domain tools (18 ToolSpec total).
Category: Business domain / aggregator
Scope: Phase 51 / Sprint 51.0 Day 3.5

Description:
    `register_all_business_tools(registry, handlers, *, mock_url)` calls each
    domain's register_<domain>_tools function in sequence. Used by:
    - runtime/workers/agent_loop_worker.py — Day 4 worker startup hook (51.0)
    - api/v1/chat/handler.py — chat dev mode default tools (51.0)
    - tests/integration/test_business_tools_via_registry.py — Day 4 verify

    Design: each domain's register_*_tools mutates the same registry + handlers
    dict. Order doesn't matter (no inter-domain dependencies), but established
    here as patrol -> correlation -> rootcause -> audit -> incident matching
    08b-business-tools-spec.md §Domain 1-5 numbering.

Lifecycle:
    Sprint 55 Phase: when real enterprise integrations replace mock_executors,
    register_all_business_tools function signature stays the same — only
    each domain's mock_executor.py gets swapped.

Created: 2026-04-30 (Sprint 51.0 Day 3)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from agent_harness.observability import Tracer
from agent_harness.tools import (
    ToolExecutorImpl,
    ToolHandler,
    ToolRegistry,
    ToolRegistryImpl,
)
from agent_harness.tools.echo_tool import ECHO_TOOL_SPEC, echo_handler

from .audit_domain.tools import register_audit_tools
from .correlation.tools import register_correlation_tools
from .incident.tools import register_incident_tools
from .patrol.tools import register_patrol_tools
from .rootcause.tools import register_rootcause_tools

# Default mock backend URL (overridable per-call)
DEFAULT_MOCK_URL = "http://localhost:8001"


def register_all_business_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_MOCK_URL,
) -> None:
    """Register all 18 business domain ToolSpecs + 18 handlers.

    Domain breakdown (per 08b-business-tools-spec.md):
      - patrol:        4 tools (08b §Domain 1)
      - correlation:   3 tools (08b §Domain 2)
      - rootcause:     3 tools (08b §Domain 3)
      - audit:         3 tools (08b §Domain 4)
      - incident:      5 tools (08b §Domain 5)
      Total:          18 tools
    """
    register_patrol_tools(registry, handlers, mock_url=mock_url)
    register_correlation_tools(registry, handlers, mock_url=mock_url)
    register_rootcause_tools(registry, handlers, mock_url=mock_url)
    register_audit_tools(registry, handlers, mock_url=mock_url)
    register_incident_tools(registry, handlers, mock_url=mock_url)


def make_default_executor(
    *,
    mock_url: str = DEFAULT_MOCK_URL,
    tracer: Tracer | None = None,
) -> tuple[ToolRegistryImpl, ToolExecutorImpl]:
    """Build a registry+executor pair with echo_tool + 18 business tools (19 total).

    Sprint 51.1 Day 5: switched from InMemoryToolRegistry / InMemoryToolExecutor
    to production Cat 2 implementations (ToolRegistryImpl + ToolExecutorImpl
    with PermissionChecker + JSONSchema validation + concurrency-aware batch).
    Behavior changes:
      - Tool calls now go through PermissionChecker (HIGH-risk + ALWAYS_ASK
        tools surface as approval_required ToolResult error).
      - Bad arguments fail fast with schema mismatch error.
      - Batch executes parallel for read-only / sequential for any
        SEQUENTIAL spec (concurrency policy enforcement).

    Args:
        mock_url: Override for the mock_services backend URL.
        tracer: Optional Tracer (defaults to NoOp via ToolExecutorImpl).

    Returns:
        (registry, executor) — both wired with 19 ToolSpec + handlers.
    """
    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}

    # echo_tool (50.1 built-in for bring-up tests; migrated out of _inmemory in 51.1)
    registry.register(ECHO_TOOL_SPEC)
    handlers["echo_tool"] = echo_handler

    # 18 business tools
    register_all_business_tools(registry, handlers, mock_url=mock_url)

    # ToolExecutorImpl handler signature is `Callable[[ToolCall], Awaitable[str]]`;
    # business handlers return `str | dict` and ToolExecutorImpl coerces to str.
    executor = ToolExecutorImpl(
        registry=registry,
        handlers=handlers,
        tracer=tracer,
    )
    return registry, executor


__all__ = [
    "register_all_business_tools",
    "make_default_executor",
    "DEFAULT_MOCK_URL",
]
