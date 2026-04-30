"""
File: backend/src/business_domain/rootcause/mock_executor.py
Purpose: HTTP client to mock_services rootcause router; apply_fix is HIGH risk.
Category: Business domain / rootcause (mock layer)
Scope: Phase 51 / Sprint 51.0 Day 2.7

Description:
    Async HTTP client for the 3 mock_rootcause_* endpoints. apply_fix defaults
    dry_run=True per 08b spec; live runs require explicit dry_run=false plus
    HITL ALWAYS_ASK approval (Sprint 51.0 stub registers this in tags;
    actual enforcement lands with HITL impl in Phase 53.3).

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:8001")


class RootcauseMockExecutor:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def diagnose(self, incident_id: str) -> Any:
        return await self._post("/mock/rootcause/diagnose", {"incident_id": incident_id})

    async def suggest_fix(self, incident_id: str) -> Any:
        return await self._post("/mock/rootcause/suggest_fix", {"incident_id": incident_id})

    async def apply_fix(self, fix_id: str, dry_run: bool = True) -> Any:
        return await self._post("/mock/rootcause/apply_fix", {"fix_id": fix_id, "dry_run": dry_run})
