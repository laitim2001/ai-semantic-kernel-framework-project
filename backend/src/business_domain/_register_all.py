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
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: (Sprint 55.2 Day 3.1) Uniform mode/factory_provider threading
      to all 5 register_*_tools (was incident-only in 55.1; closes
      AD-BusinessDomainPartialSwap-1 at the aggregator layer).
    - 2026-05-04: (Sprint 55.1 Day 3) Added mode + factory_provider kwargs.
    - 2026-04-30: Initial creation (Sprint 51.0 Day 3).
"""

from __future__ import annotations

from collections.abc import Callable

from agent_harness.observability import Tracer
from agent_harness.tools import (
    ToolExecutorImpl,
    ToolHandler,
    ToolRegistry,
    ToolRegistryImpl,
)
from agent_harness.tools.echo_tool import ECHO_TOOL_SPEC, echo_handler

from ._service_factory import BusinessServiceFactory
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
    mode: str = "mock",
    factory_provider: Callable[[], BusinessServiceFactory] | None = None,
) -> None:
    """Register all 18 business domain ToolSpecs + 18 handlers.

    Sprint 55.1 (US-4): added `mode` + `factory_provider` kwargs (incident only).
    Sprint 55.2 (US-2): mode/factory_provider now uniformly threaded to all 5
        register_*_tools. AD-BusinessDomainPartialSwap-1 closed.
        - mode='mock' (default): 51.0 HTTP-backed pathway via mock_executor.
        - mode='service': production pathway. All 5 domains accept `mode='service'`
          + factory_provider. Per-domain handler split (1 real + N sentinel)
          documented in each domain's tools.py module docstring.

    Domain breakdown (per 08b-business-tools-spec.md):
      - patrol:        4 tools (08b §Domain 1) — service-aware (1 real: get_results)
      - correlation:   3 tools (08b §Domain 2) — service-aware (1 real: get_related)
      - rootcause:     3 tools (08b §Domain 3) — service-aware (1 real: diagnose)
      - audit:         3 tools (08b §Domain 4) — service-aware (1 real: query_logs)
      - incident:      5 tools (08b §Domain 5) — fully service-backed
      Total:          18 tools
    """
    if mode not in ("mock", "service"):
        raise ValueError(f"register_all_business_tools: invalid mode {mode!r}")
    if mode == "service" and factory_provider is None:
        raise ValueError("register_all_business_tools(mode='service') requires factory_provider")

    # All 5 domains: mode-aware as of Sprint 55.2.
    register_patrol_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )
    register_correlation_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )
    register_rootcause_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )
    register_audit_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )
    register_incident_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )


def make_default_executor(
    *,
    mock_url: str = DEFAULT_MOCK_URL,
    tracer: Tracer | None = None,
    mode: str | None = None,
    factory_provider: Callable[[], BusinessServiceFactory] | None = None,
) -> tuple[ToolRegistryImpl, ToolExecutorImpl]:
    """Build a registry+executor pair with echo_tool + 18 business tools (19 total).

    Sprint 51.1 Day 5: switched from InMemoryToolRegistry / InMemoryToolExecutor
    to production Cat 2 implementations (ToolRegistryImpl + ToolExecutorImpl
    with PermissionChecker + JSONSchema validation + concurrency-aware batch).

    Sprint 55.1 (US-4): added `mode` + `factory_provider`. When `mode is None`,
    settings.business_domain_mode (env: BUSINESS_DOMAIN_MODE) is read.
    Explicit kwarg wins over env (test override path).

    Args:
        mock_url: Override for the mock_services backend URL.
        tracer: Optional Tracer (defaults to NoOp via ToolExecutorImpl).
        mode: 'mock' / 'service' / None (read settings).
        factory_provider: required when mode resolves to 'service'.

    Returns:
        (registry, executor) — both wired with 19 ToolSpec + handlers.
    """
    if mode is None:
        from core.config import get_settings

        mode = get_settings().business_domain_mode

    registry = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}

    # echo_tool (50.1 built-in for bring-up tests; migrated out of _inmemory in 51.1)
    registry.register(ECHO_TOOL_SPEC)
    handlers["echo_tool"] = echo_handler

    # 18 business tools
    register_all_business_tools(
        registry,
        handlers,
        mock_url=mock_url,
        mode=mode,
        factory_provider=factory_provider,
    )

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
