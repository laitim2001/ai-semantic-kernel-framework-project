"""
File: backend/src/business_domain/knowledge/tools.py
Purpose: knowledge_search ToolSpec + register_knowledge_tools — wraps the REAL LocalDocsConnector.
Category: Business domain / knowledge / tool layer (REAL — NOT mock)
Scope: Phase 57 / Sprint 57.145

Description:
    Exposes the first real external data-source connector to the agent as a
    Cat 2 tool. `knowledge_search` is read-only (LOW risk, AUTO hitl) so the
    registry-derived permission matrix auto-passes it — the agent searches the
    company docs folder freely and grounds answers in real snippets with source
    paths. Dual-arity handler (ToolCall, ExecutionContext) so it reads the
    server-authoritative tenant_id for per-tenant vector isolation (Sprint 57.147;
    mirrors memory_search), with an LLM-forged-scope guard.

Key Components:
    - KNOWLEDGE_SEARCH_SPEC: the ToolSpec (mirrors MEMORY_SEARCH_SPEC shape)
    - make_knowledge_search_handler(): builds a (ToolCall, ExecutionContext) -> str handler
    - register_knowledge_tools(): registers spec + handler over a docs root

Created: 2026-06-26 (Sprint 57.145)
Last Modified: 2026-06-27

Modification History (newest-first):
    - 2026-06-27: Sprint 57.147 — dual-arity handler + forgery guard + thread context.tenant_id
      to per-tenant vector search (AD-Knowledge-Connector-RBAC-Citation-Slice3 isolation half)
    - 2026-06-27: Sprint 57.146 — opt-in vector_index (semantic-primary, keyword fail-soft fallback)
    - 2026-06-26: Initial creation (Sprint 57.145) — first real connector tool
      (AD-Knowledge-Connector-First-Real-Source)

Related:
    - 01-eleven-categories-spec.md §範疇 2 (Tools)
    - agent_harness/tools/memory_tools.py (MEMORY_SEARCH_SPEC — read-only query template)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from agent_harness._contracts import (
    ConcurrencyPolicy,
    ExecutionContext,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)
from agent_harness.tools import ToolHandler, ToolRegistry

from .connector import KnowledgeHit, LocalDocsConnector

if TYPE_CHECKING:
    from .vector_index import KnowledgeVectorIndex

logger = logging.getLogger(__name__)

# Reserved scope arg names the LLM is NOT allowed to set — they come from the
# server-authoritative ExecutionContext (JWT-derived), never the tool call.
_RESERVED_SCOPE_KEYS = ("tenant_id", "user_id", "session_id")


def _reject_forged_scope(args: dict[str, Any], context: ExecutionContext) -> str | None:
    """Return an error string if any reserved scope arg disagrees with the context, else None.

    Mirrors memory_tools._detect_forged_scope_args (Sprint 52.5 W4P-4): tenant_id /
    user_id / session_id are server-authoritative. The knowledge_search schema does
    not declare these properties, but JSONSchema additionalProperties is permissive,
    so an LLM could still smuggle a tenant_id into arguments — this guard refuses a
    supplied value that disagrees with (or is supplied when absent from) the context.
    Tolerant: omitted keys / empty values / a value EQUAL to the context are allowed.
    """
    ctx_view = {
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
        "session_id": context.session_id,
    }
    for key in _RESERVED_SCOPE_KEYS:
        if key not in args:
            continue
        raw = args[key]
        if raw is None or raw == "":
            continue
        try:
            supplied = UUID(str(raw))
        except (ValueError, AttributeError):
            return (
                f"argument '{key}' is not a valid scope id; scope comes from "
                "ExecutionContext, not the tool call"
            )
        expected = ctx_view[key]
        if expected is None or supplied != expected:
            return (
                f"argument '{key}' disagrees with ExecutionContext "
                "(refusing potentially forged tenant scope)"
            )
    return None


KNOWLEDGE_SEARCH_SPEC: ToolSpec = ToolSpec(
    name="knowledge_search",
    description=(
        "Search the company knowledge base / internal documents folder for "
        "passages relevant to a query. Returns up to top_k snippets, each with "
        "its source file path, so the answer can cite real sources. Read-only."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "description": "Natural-language or keyword query to search the documents for.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "Max number of ranked document snippets to return (1-20).",
            },
        },
        "required": ["query"],
    },
    # open_world=True: this tool reaches a real external data source (the file system).
    annotations=ToolAnnotations(read_only=True, idempotent=True, open_world=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("knowledge", "read-only"),
)


def make_knowledge_search_handler(
    connector: LocalDocsConnector,
    vector_index: "KnowledgeVectorIndex | None" = None,
) -> ToolHandler:
    """Build a dual-arity (ToolCall, ExecutionContext) -> str handler over a real docs connector.

    Sprint 57.147: the handler is dual-arity so it reads the server-authoritative
    tenant_id from the ExecutionContext (JWT-derived, threaded by the loop) and
    passes it into the per-tenant vector search — each tenant's agent retrieves
    ONLY its own collection. An LLM-supplied tenant scope arg that disagrees with
    the context is refused (forgery guard). The keyword fail-soft path stays shared
    (tenant_id is not applied there — documented limitation; keyword is the degraded
    fallback).

    Sprint 57.146: when a vector_index is supplied the handler retrieves by semantic
    similarity (embedding + Qdrant); on ANY embedding/Qdrant error it fails soft to
    the keyword connector so the tool never goes dark. vector_index None → keyword
    behavior (shared root).
    """

    async def handler(call: ToolCall, context: ExecutionContext) -> str:
        args = dict(call.arguments)
        forge = _reject_forged_scope(args, context)
        if forge is not None:
            return json.dumps({"hits": [], "count": 0, "error": forge})
        query = str(args.get("query", "")).strip()
        top_k_raw = args.get("top_k", 5)
        try:
            top_k = int(top_k_raw)
        except (TypeError, ValueError):
            top_k = 5
        if not query:
            return json.dumps({"hits": [], "count": 0, "note": "empty query"})
        hits: list[KnowledgeHit]
        if vector_index is not None:
            try:
                hits = await vector_index.search(query, top_k=top_k, tenant_id=context.tenant_id)
            except Exception:  # noqa: BLE001 — fail-soft to keyword on embedding/Qdrant error
                logger.warning(
                    "knowledge_search vector path failed; falling back to keyword",
                    exc_info=True,
                )
                hits = connector.search(query, top_k=top_k)
        else:
            hits = connector.search(query, top_k=top_k)
        return json.dumps(
            {
                "hits": [
                    {"source": h.source, "snippet": h.snippet, "score": round(h.score, 3)}
                    for h in hits
                ],
                "count": len(hits),
            }
        )

    return handler


def register_knowledge_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    docs_root: Path | str,
    vector_index: "KnowledgeVectorIndex | None" = None,
) -> None:
    """Register the REAL knowledge_search tool backed by a LocalDocsConnector(docs_root).

    Mirrors the per-domain register_*_tools shape: mutates the shared (registry,
    handlers). The connector is built once here; a missing root raises clearly so
    the caller (make_default_executor opt-in) can decide to skip registration.
    Sprint 57.146: an optional vector_index makes the handler semantic-primary
    (keyword fail-soft fallback).
    """
    connector = LocalDocsConnector(docs_root)
    registry.register(KNOWLEDGE_SEARCH_SPEC)
    handlers["knowledge_search"] = make_knowledge_search_handler(connector, vector_index)
