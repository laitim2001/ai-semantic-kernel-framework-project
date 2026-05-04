"""
File: backend/src/business_domain/patrol/service.py
Purpose: PatrolService — read-only foundation for the patrol domain (08b §Domain 1).
Category: Business Domain / patrol — service layer
Scope: Sprint 55.1 US-3 / Day 3.1a

Description:
    Sprint 55.1 introduces minimum read-only service for the patrol domain.
    Phase 55.1 does not build a real patrols/patrol_results DB schema (deferred
    to Phase 56+); instead, get_results() returns deterministic canned data
    keyed by patrol_id hash. This is sufficient to demonstrate the
    BUSINESS_DOMAIN_MODE=service pathway end-to-end without coupling Sprint
    55.1 to additional schema work.

    When mode='mock', PatrolMockExecutor (HTTP to localhost:8001) is used
    instead — handler closure in tools.py branches on mode (Day 3.4).

Created: 2026-05-04 (Sprint 55.1 Day 3)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 3.1a)

Related:
    - 08b-business-tools-spec.md §Domain 1 Patrol
    - business_domain/_base.py — BusinessServiceBase
    - business_domain/_obs.py — business_service_span
"""

from __future__ import annotations

import hashlib
from typing import Any

from business_domain._base import BusinessServiceBase
from business_domain._obs import business_service_span


class PatrolService(BusinessServiceBase):
    """Read-only patrol service. Production schema deferred; deterministic stub."""

    SERVICE_NAME = "patrol"

    async def get_results(self, *, patrol_id: str) -> dict[str, Any]:
        """Return deterministic patrol_results dict keyed by patrol_id hash.

        Phase 56+ will replace this with real DB-backed query against the
        patrol_results table (per 09.md schema). For now, the stub provides
        a stable contract for the rest of Sprint 55.1 wiring.
        """
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="get_results"
        ):
            digest = hashlib.sha256(patrol_id.encode()).hexdigest()[:8]
            # Use first 2 hex chars to derive a deterministic health score.
            score = int(digest[:2], 16)  # 0–255
            health = "healthy" if score < 200 else "degraded"
            return {
                "patrol_id": patrol_id,
                "tenant_id": str(self.tenant_id),
                "health": health,
                "score": score,
                "digest": digest,
                "servers_checked": [
                    {"id": f"srv-{digest[i:i + 2]}", "status": "ok"} for i in range(0, 6, 2)
                ],
            }


__all__ = ["PatrolService"]
