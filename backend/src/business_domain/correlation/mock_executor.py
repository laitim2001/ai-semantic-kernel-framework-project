"""
File: backend/src/business_domain/correlation/mock_executor.py
Purpose: HTTP client to mock_services correlation router.
Category: Business domain / correlation (mock layer)
Scope: Phase 51 / Sprint 51.0 Day 2.5

Description:
    Async HTTP client for the 3 mock_correlation_* endpoints. Phase 55 swap
    target: Splunk / DataDog correlation engine.

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:8001")


class CorrelationMockExecutor:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()

    async def analyze(self, alert_ids: list[str]) -> Any:
        return await self._post("/mock/correlation/analyze", {"alert_ids": alert_ids})

    async def find_root_cause(self, incident_id: str) -> Any:
        return await self._post("/mock/correlation/find_root_cause", {"incident_id": incident_id})

    async def get_related(self, alert_id: str, depth: int = 1) -> Any:
        return await self._get(f"/mock/correlation/related/{alert_id}", params={"depth": depth})
