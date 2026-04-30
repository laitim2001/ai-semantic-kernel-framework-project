"""
File: backend/src/business_domain/patrol/mock_executor.py
Purpose: HTTP client to mock_services patrol router; wraps endpoints as typed async methods.
Category: Business domain / patrol (mock layer; Phase 55 replaces with real D365/SAP integration)
Scope: Phase 51 / Sprint 51.0 Day 2.2

Description:
    Async HTTP client for the 4 mock_patrol_* endpoints. Each method's signature
    matches what a real enterprise integration would look like (typed args, not
    ToolCall) so Phase 55 swap is mechanical.

    Uses httpx.AsyncClient with 10s timeout; base_url overridable via
    MOCK_SERVICES_URL env (default http://localhost:8001).

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:8001")


class PatrolMockExecutor:
    """HTTP client wrapping mock_services /mock/patrol/* endpoints."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}{path}")
            resp.raise_for_status()
            return resp.json()

    async def check_servers(self, scope: list[str]) -> Any:
        return await self._post("/mock/patrol/check_servers", {"scope": scope})

    async def get_results(self, patrol_id: str) -> Any:
        return await self._get(f"/mock/patrol/results/{patrol_id}")

    async def schedule(self, cron: str, scope: list[str]) -> Any:
        return await self._post("/mock/patrol/schedule", {"cron": cron, "scope": scope})

    async def cancel(self, schedule_id: str) -> Any:
        return await self._post("/mock/patrol/cancel", {"schedule_id": schedule_id})
