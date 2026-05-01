"""
File: backend/src/agent_harness/context_mgmt/jit_retrieval.py
Purpose: PointerResolver — JIT (Just-In-Time) retrieval of large blobs by URI pointer.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    PointerResolver lets prompts reference large blobs (memory rows, tool
    artefacts, KB documents) by a short URI pointer instead of inlining
    them. The Compactor or PromptBuilder may emit a tombstone like
    `[POINTER db://memory_user/<uuid>?tenant_id=<tid>]` and call resolve()
    only when the agent actually needs the body.

    Schemes (52.1):
      - db://<table>/<uuid>?tenant_id=<tid>      Cat 3 memory tables (active)
      - memory://...                              raises JITRetrievalNotSupportedError
      - tool://...                                raises JITRetrievalNotSupportedError
      - kb://...                                  raises JITRetrievalNotSupportedError

Multi-tenant safety (per 10-server-side-philosophy.md §原則 1):
    Every db:// pointer MUST include a tenant_id query parameter, AND the
    runtime call also receives tenant_id explicitly. The two MUST match;
    a mismatch is treated as a security violation and raises
    PointerTenantMismatchError. The DB query enforces tenant_id at the
    storage layer too (RLS-style WHERE clause).

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (JITRetrieval row)

Related:
    - _abc.py JITRetrieval ABC
    - 09-db-schema-design.md (memory_* tables)
    - multi-tenant-data.md (.claude/rules/) — tenant_id strict filter rule

Created: 2026-05-01 (Sprint 52.1 Day 3.4)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.4) — PointerResolver with db:// scheme
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from agent_harness.context_mgmt._abc import JITRetrieval


class JITRetrievalNotSupportedError(RuntimeError):
    """Raised when a pointer scheme has no resolver bound (memory:// / tool:// / kb://)."""


class JITRetrievalConfigError(RuntimeError):
    """Raised when the resolver lacks a required dependency (e.g. db_session for db://)."""


class PointerTenantMismatchError(RuntimeError):
    """Raised when the pointer's tenant_id query parameter conflicts with the runtime tenant_id."""


# Whitelist of memory_* tables a db:// pointer may target. Day 3.4 narrow scope —
# Cat 3 owns these; Phase 53.1+ may extend to other tables via explicit allow-list.
_ALLOWED_DB_TABLES: frozenset[str] = frozenset(
    {
        "memory_user",
        "memory_session",
        "memory_role",
        "memory_tenant",
        "memory_system",
    }
)


class PointerResolver(JITRetrieval):
    """Default JITRetrieval impl. db:// active; other schemes raise NotSupported."""

    def __init__(self, *, db_session: Any | None = None) -> None:
        self._db_session = db_session

    async def resolve(
        self,
        pointer: str,
        *,
        tenant_id: UUID,
    ) -> str:
        parsed = urlparse(pointer)
        scheme = parsed.scheme.lower()

        if scheme == "db":
            return await self._resolve_db(parsed, tenant_id=tenant_id)

        if scheme in ("memory", "tool", "kb"):
            raise JITRetrievalNotSupportedError(
                f"Pointer scheme '{scheme}://' is reserved but not implemented in Sprint 52.1; "
                f"caller must inline the content directly."
            )

        raise JITRetrievalNotSupportedError(
            f"Unknown pointer scheme '{scheme}://' in pointer={pointer!r}"
        )

    async def _resolve_db(
        self,
        parsed: Any,
        *,
        tenant_id: UUID,
    ) -> str:
        if self._db_session is None:
            raise JITRetrievalConfigError(
                "PointerResolver was constructed without a db_session; "
                "db:// pointers cannot be resolved. Pass db_session=... at construction."
            )

        # parsed.netloc == table; parsed.path == "/<uuid>"
        table = parsed.netloc
        if table not in _ALLOWED_DB_TABLES:
            raise JITRetrievalNotSupportedError(
                f"db:// table '{table}' is not in the Sprint 52.1 allow-list "
                f"({sorted(_ALLOWED_DB_TABLES)})."
            )

        path = (parsed.path or "").lstrip("/")
        if not path:
            raise JITRetrievalConfigError(
                f"db:// pointer is missing the row id segment (parsed={parsed.geturl()!r})"
            )
        try:
            row_uuid = UUID(path)
        except (ValueError, AttributeError) as err:
            raise JITRetrievalConfigError(
                f"db:// pointer row id is not a valid UUID: {path!r}"
            ) from err

        # tenant_id MUST come from the query string AND match runtime tenant
        qs = parse_qs(parsed.query)
        tenant_qs = qs.get("tenant_id", [None])[0]
        if tenant_qs is None:
            raise PointerTenantMismatchError(
                "db:// pointer is missing required query parameter ?tenant_id=<uuid>"
            )
        try:
            pointer_tenant = UUID(tenant_qs)
        except (ValueError, AttributeError) as err:
            raise PointerTenantMismatchError(
                f"db:// pointer tenant_id query parameter is not a valid UUID: {tenant_qs!r}"
            ) from err

        if pointer_tenant != tenant_id:
            raise PointerTenantMismatchError(
                f"db:// pointer tenant_id ({pointer_tenant}) does not match runtime tenant_id "
                f"({tenant_id}). Cross-tenant resolution is forbidden."
            )

        # Storage-layer enforcement: WHERE id=:row_uuid AND tenant_id=:tenant_id
        # (Real binding deferred to Day 3 wiring with SQLAlchemy AsyncSession;
        # Day 3.4 unit tests use a mock session.)
        result = await self._db_session.fetch_content(
            table=table,
            row_id=row_uuid,
            tenant_id=tenant_id,
        )
        if result is None:
            raise JITRetrievalConfigError(
                f"db:// pointer resolved to no row (table={table}, id={row_uuid}, tenant={tenant_id})"
            )
        return str(result)
