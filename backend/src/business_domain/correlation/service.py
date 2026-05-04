"""
File: backend/src/business_domain/correlation/service.py
Purpose: CorrelationService — read-only foundation for correlation (08b §Domain 2).
Category: Business Domain / correlation — service layer
Scope: Sprint 55.1 US-3 / Day 3.1b

Description:
    Sprint 55.1 minimum: get_related(alert_id, depth) returns deterministic
    related-alert list. Production graph traversal deferred to Phase 56+.

Created: 2026-05-04 (Sprint 55.1 Day 3)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 3.1b)
"""

from __future__ import annotations

import hashlib
from typing import Any

from business_domain._base import BusinessServiceBase
from business_domain._obs import business_service_span

_VALID_DEPTHS = (1, 2, 3)


class CorrelationService(BusinessServiceBase):
    """Read-only correlation service; deterministic graph stub."""

    SERVICE_NAME = "correlation"

    async def get_related(self, *, alert_id: str, depth: int = 1) -> list[dict[str, Any]]:
        """Return deterministic related-alert list (depth ∈ {1, 2, 3})."""
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="get_related"
        ):
            if depth not in _VALID_DEPTHS:
                raise ValueError(f"Invalid depth {depth}; must be one of {_VALID_DEPTHS}")

            digest = hashlib.sha256(alert_id.encode()).hexdigest()
            count = depth * 2  # depth=1 → 2 related, depth=2 → 4, depth=3 → 6
            return [
                {
                    "alert_id": f"rel-{digest[i * 4:(i + 1) * 4]}",
                    "tenant_id": str(self.tenant_id),
                    "depth": (i // 2) + 1,
                    "score": int(digest[i * 2 : (i + 1) * 2], 16) / 255.0,
                }
                for i in range(count)
            ]


__all__ = ["CorrelationService"]
