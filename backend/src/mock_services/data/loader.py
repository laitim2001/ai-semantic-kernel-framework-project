"""
File: backend/src/mock_services/data/loader.py
Purpose: Load seed.json into in-memory dict at startup; provide read-only access helpers.
Category: Mock services / data
Scope: Phase 51 / Sprint 51.0 Day 1.4

Description:
    SeedDB holds 7 entity collections (customers / orders / tickets / kb_articles /
    patrols / alerts / incidents / rca_findings / audit_logs) keyed by id where
    applicable. Loaded once at app startup via FastAPI lifespan event.

    No persistence: restart resets state. This is intentional for mock backend
    (Phase 55 真實 integration 不沿用此 loader).

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).parent / "seed.json"


@dataclass
class SeedDB:
    """In-memory store loaded from seed.json. Lookups are O(1) via dict-by-id."""

    customers: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    tickets: dict[str, dict[str, Any]] = field(default_factory=dict)
    kb_articles: dict[str, dict[str, Any]] = field(default_factory=dict)
    patrols: dict[str, dict[str, Any]] = field(default_factory=dict)
    alerts: dict[str, dict[str, Any]] = field(default_factory=dict)
    incidents: dict[str, dict[str, Any]] = field(default_factory=dict)
    rca_findings: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_logs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def stats(self) -> dict[str, int]:
        return {
            "customers": len(self.customers),
            "orders": len(self.orders),
            "tickets": len(self.tickets),
            "kb_articles": len(self.kb_articles),
            "patrols": len(self.patrols),
            "alerts": len(self.alerts),
            "incidents": len(self.incidents),
            "rca_findings": len(self.rca_findings),
            "audit_logs": len(self.audit_logs),
        }


_db: SeedDB | None = None


def load_seed(path: Path | None = None) -> SeedDB:
    """Read seed.json once and populate global SeedDB."""
    global _db
    raw = json.loads((path or SEED_PATH).read_text(encoding="utf-8"))
    db = SeedDB()
    for entity in (
        "customers",
        "orders",
        "tickets",
        "kb_articles",
        "patrols",
        "alerts",
        "incidents",
        "rca_findings",
        "audit_logs",
    ):
        items = raw.get(entity, [])
        getattr(db, entity).update({item["id"]: item for item in items})
    _db = db
    return db


def get_db() -> SeedDB:
    """FastAPI dependency: return the loaded DB or raise if startup not run."""
    if _db is None:
        raise RuntimeError(
            "SeedDB not loaded. Call load_seed() in app lifespan before requests."
        )
    return _db


def reset() -> None:
    """Test helper: clear loaded DB."""
    global _db
    _db = None
