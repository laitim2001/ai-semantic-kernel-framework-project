"""
File: backend/src/agent_harness/tools/search_tools.py
Purpose: web_search built-in tool (Bing Search v7 via httpx).
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 4.1

Description:
    `web_search` queries Microsoft Bing Search v7 API and returns top-K
    snippets as JSON. Real Bing API key smoke test is CARRY-024 (operator
    runs manually with env BING_SEARCH_API_KEY); CI uses mocked httpx
    responses.

    Falls back to env-var-driven endpoint override for self-hosted /
    sandboxed environments (BING_SEARCH_ENDPOINT). 51.1 ships only Bing;
    DuckDuckGo / Google CSE adapters land later if needed.

Key Components:
    - WEB_SEARCH_SPEC: ToolSpec for web_search
    - make_web_search_handler(client): factory bound to an httpx.AsyncClient
      (or None to use a fresh per-call client)

Owner: 01-eleven-categories-spec.md §範疇 2
Created: 2026-04-30 (Sprint 51.1 Day 4.1)
"""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable

import httpx

from agent_harness._contracts import (
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)

ToolHandler = Callable[[ToolCall], Awaitable[str]]

WEB_SEARCH_SPEC: ToolSpec = ToolSpec(
    name="web_search",
    description=(
        "Search the public web via Bing Search v7. Returns top-K result "
        "snippets (title / url / snippet) as a JSON array. Use for fresh "
        "facts, news, documentation lookups."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string.",
                "minLength": 1,
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5).",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
            },
        },
        "required": ["query"],
    },
    annotations=ToolAnnotations(
        read_only=True,
        destructive=False,
        idempotent=False,  # web changes; not strictly idempotent
        open_world=True,
    ),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("builtin", "search"),
)

_DEFAULT_BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"


class WebSearchConfigError(RuntimeError):
    """Raised when BING_SEARCH_API_KEY is missing at handler invocation time."""


def make_web_search_handler(
    client: httpx.AsyncClient | None = None,
    *,
    endpoint: str | None = None,
    api_key_env: str = "BING_SEARCH_API_KEY",
) -> ToolHandler:
    """Build an async handler bound to an httpx client and Bing endpoint.

    `client=None` → creates a fresh `httpx.AsyncClient` per call (simple
    but high overhead). Pass a long-lived client for production.
    """
    target = endpoint or os.environ.get("BING_SEARCH_ENDPOINT", _DEFAULT_BING_ENDPOINT)

    async def _handler(call: ToolCall) -> str:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise WebSearchConfigError(f"missing env {api_key_env}; cannot call Bing Search API")
        query = str(call.arguments["query"])
        top_k = int(call.arguments.get("top_k", 5))
        params: dict[str, str | int] = {
            "q": query,
            "count": top_k,
            "responseFilter": "Webpages",
        }
        headers = {"Ocp-Apim-Subscription-Key": api_key}

        if client is None:
            async with httpx.AsyncClient(timeout=10) as fresh:
                resp = await fresh.get(target, params=params, headers=headers)
        else:
            resp = await client.get(target, params=params, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        web_pages = body.get("webPages", {}).get("value", []) if isinstance(body, dict) else []
        results = [
            {
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in web_pages[:top_k]
        ]
        return json.dumps({"query": query, "results": results})

    return _handler
