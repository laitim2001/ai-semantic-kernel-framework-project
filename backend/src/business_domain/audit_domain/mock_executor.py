"""
File: backend/src/business_domain/audit_domain/mock_executor.py
Purpose: HTTP client to mock_services audit router.
Category: Business domain / audit_domain (mock layer)
Scope: Phase 51 / Sprint 51.0 Day 3.2

Description:
    Async HTTP client for the 3 mock_audit_* endpoints. Phase 55 swap target:
    ServiceNow audit / Splunk SIEM / GRC tooling.

    Note: dir name is `audit_domain` (not `audit`) to avoid clash with
    `governance.audit` per CLAUDE.md scope hierarchy.

Created: 2026-04-30 (Sprint 51.0 Day 3)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:8001")


class AuditMockExecutor:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def query_logs(
        self,
        *,
        time_range_start: str | None = None,
        time_range_end: str | None = None,
        action_filter: str | None = None,
        user_id_filter: str | None = None,
        limit: int = 20,
    ) -> Any:
        payload: dict[str, Any] = {"limit": limit}
        if time_range_start is not None:
            payload["time_range_start"] = time_range_start
        if time_range_end is not None:
            payload["time_range_end"] = time_range_end
        if action_filter is not None:
            payload["action_filter"] = action_filter
        if user_id_filter is not None:
            payload["user_id_filter"] = user_id_filter
        return await self._post("/mock/audit/query_logs", payload)

    async def generate_report(self, template: str, params: dict[str, Any]) -> Any:
        return await self._post(
            "/mock/audit/generate_report", {"template": template, "params": params}
        )

    async def flag_anomaly(self, record_id: str, reason: str) -> Any:
        return await self._post(
            "/mock/audit/flag_anomaly", {"record_id": record_id, "reason": reason}
        )
