"""
File: backend/src/business_domain/incident/mock_executor.py
Purpose: HTTP client to mock_services incident router.
Category: Business domain / incident (mock layer)
Scope: Phase 51 / Sprint 51.0 Day 3.4

Description:
    Async HTTP client for the 5 mock_incident_* endpoints. Phase 55 swap target:
    PagerDuty / Opsgenie / ServiceNow incident mgmt.

Created: 2026-04-30 (Sprint 51.0 Day 3)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = os.environ.get("MOCK_SERVICES_URL", "http://localhost:8001")


class IncidentMockExecutor:
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

    async def create(
        self,
        *,
        title: str,
        severity: str = "high",
        alert_ids: list[str] | None = None,
    ) -> Any:
        return await self._post(
            "/mock/incident/create",
            {"title": title, "severity": severity, "alert_ids": alert_ids or []},
        )

    async def update_status(self, incident_id: str, status: str) -> Any:
        return await self._post(
            "/mock/incident/update_status",
            {"incident_id": incident_id, "status": status},
        )

    async def close(self, incident_id: str, resolution: str) -> Any:
        return await self._post(
            "/mock/incident/close",
            {"incident_id": incident_id, "resolution": resolution},
        )

    async def get(self, incident_id: str) -> Any:
        return await self._get(f"/mock/incident/{incident_id}")

    async def list(
        self,
        *,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> Any:
        payload: dict[str, Any] = {"limit": limit}
        if severity is not None:
            payload["severity"] = severity
        if status is not None:
            payload["status"] = status
        return await self._post("/mock/incident/list", payload)
