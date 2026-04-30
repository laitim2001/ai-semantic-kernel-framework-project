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

from collections.abc import Awaitable, Callable
from typing import Any

from agent_harness._contracts import ToolCall
from agent_harness.tools._inmemory import InMemoryToolRegistry

from .audit_domain.tools import register_audit_tools
from .correlation.tools import register_correlation_tools
from .incident.tools import register_incident_tools
from .patrol.tools import register_patrol_tools
from .rootcause.tools import register_rootcause_tools

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]

# Default mock backend URL (overridable per-call)
DEFAULT_MOCK_URL = "http://localhost:8001"


def register_all_business_tools(
    registry: InMemoryToolRegistry,
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


__all__ = ["register_all_business_tools", "DEFAULT_MOCK_URL"]
