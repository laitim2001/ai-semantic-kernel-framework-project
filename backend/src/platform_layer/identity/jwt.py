"""
File: backend/src/platform_layer/identity/jwt.py
Purpose: JWT encode/decode/verify for V2 tenant + user identity propagation.
Category: Platform layer / Identity (cross-cutting; supports multi-tenant 鐵律 3)
Scope: Sprint 52.5 Day 1.2 (P0 #14 — replaces V1 X-Tenant-Id header)
Owner: platform_layer/identity owner

Description:
    JWTManager wraps `python-jose` to produce/validate signed JWT tokens
    carrying `tenant_id` + `sub` (user_id) + `roles` claims. Tokens are
    issued by the auth service (out of scope here) and validated by
    `TenantContextMiddleware` to populate `request.state` for FastAPI
    dependencies in `auth.py`.

    Settings (jwt_secret / jwt_algorithm / jwt_expires_minutes) come from
    `core.config.get_settings()` by default but the constructor accepts
    overrides for testability.

    Rationale: V1 read tenant_id from `X-Tenant-Id` header — trivially
    spoofable. V2 makes tenant_id JWT-claim only. See
    .claude/rules/multi-tenant-data.md 鐵律 1-3 + audit W1-2 P0 #14.

Key Components:
    - JWTManager.encode(...) -> str
    - JWTManager.decode(token) -> JWTClaims
    - JWTManager.verify(token) -> bool (non-raising)
    - JWTClaims: frozen dataclass mirroring decoded payload

Created: 2026-05-01 (Sprint 52.5 Day 1.2)
Last Modified: 2026-05-01

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.5 Day 1.2) — P0 #14 JWT module

Related:
    - core/config/__init__.py — Settings.jwt_* fields (49.3 reserved 49.4+ wires)
    - platform_layer/middleware/tenant_context.py — middleware that calls decode()
    - platform_layer/identity/auth.py — FastAPI deps reading request.state
    - .claude/rules/multi-tenant-data.md — auth header rule
    - claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md — issue #14
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import jwt as jose_jwt  # type: ignore[import-untyped, unused-ignore]
from jose.exceptions import (  # type: ignore[import-untyped, unused-ignore]
    ExpiredSignatureError,
    JWTError,
)

from core.config import get_settings

# === Custom exceptions ============================================
# Why: callers (middleware, tests) need to distinguish "expired" from
# "malformed/bad signature" to return appropriate 401 messages and to
# avoid leaking signature details. Wrapping jose exceptions keeps the
# adapter layer hidden behind our own types.


class JWTAuthError(Exception):
    """Base class for JWT validation failures (401 territory)."""


class JWTExpiredError(JWTAuthError):
    """Token signature was valid but `exp` claim has passed."""


class JWTInvalidError(JWTAuthError):
    """Token failed validation (bad signature / malformed / missing claim)."""


# === JWTClaims ====================================================


@dataclass(frozen=True)
class JWTClaims:
    """Decoded JWT payload. `extra` holds any non-standard claims.

    Standard claims:
        sub: str — opaque user identifier (commonly UUID stringified)
        tenant_id: UUID — the only authoritative tenant_id source
        roles: list[str] — RBAC roles (empty if user has none)
        iat: int — issued-at UNIX timestamp (seconds)
        exp: int — expiration UNIX timestamp (seconds)
    """

    sub: str
    tenant_id: UUID
    roles: list[str]
    iat: int
    exp: int
    extra: dict[str, Any] = field(default_factory=dict)


# === JWTManager ===================================================


class JWTManager:
    """Encode + decode + verify JWT tokens.

    Default constructor reads from `core.config.Settings`. Tests pass
    explicit `secret` / `algorithm` / `expires_minutes` for isolation.
    """

    # Reserved standard claim names — disallowed in `extra` to prevent
    # accidental override of structural fields like `exp` or `tenant_id`.
    _RESERVED_CLAIMS = frozenset({"sub", "tenant_id", "roles", "iat", "exp"})

    def __init__(
        self,
        *,
        secret: str | None = None,
        algorithm: str | None = None,
        expires_minutes: int | None = None,
    ) -> None:
        if secret is None or algorithm is None or expires_minutes is None:
            s = get_settings()
            self.secret = secret if secret is not None else s.jwt_secret
            self.algorithm = algorithm if algorithm is not None else s.jwt_algorithm
            self.expires_minutes = (
                expires_minutes if expires_minutes is not None else s.jwt_expires_minutes
            )
        else:
            self.secret = secret
            self.algorithm = algorithm
            self.expires_minutes = expires_minutes

    def encode(
        self,
        *,
        sub: str,
        tenant_id: UUID,
        roles: list[str] | tuple[str, ...] = (),
        expires_minutes: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Produce a signed JWT.

        Args:
            sub: User identifier (claim `sub`).
            tenant_id: Tenant UUID (claim `tenant_id`).
            roles: RBAC roles list.
            expires_minutes: Override default expiration window.
            extra: Additional non-standard claims; reserved names raise.

        Returns:
            Compact JWS serialisation (header.payload.signature).
        """
        now = datetime.now(timezone.utc)
        exp_minutes = expires_minutes if expires_minutes is not None else self.expires_minutes
        exp_at = now + timedelta(minutes=exp_minutes)
        payload: dict[str, Any] = {
            "sub": sub,
            "tenant_id": str(tenant_id),
            "roles": list(roles),
            "iat": int(now.timestamp()),
            "exp": int(exp_at.timestamp()),
        }
        if extra:
            for key in extra:
                if key in self._RESERVED_CLAIMS:
                    raise ValueError(f"extra claim '{key}' overlaps a reserved standard claim")
            payload.update(extra)
        encoded: str = jose_jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return encoded

    def decode(self, token: str) -> JWTClaims:
        """Validate signature + expiration and return parsed claims.

        Raises:
            JWTExpiredError: token expired (signature was valid).
            JWTInvalidError: signature mismatch / malformed / missing claim.
        """
        try:
            raw = jose_jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
        except ExpiredSignatureError as e:
            raise JWTExpiredError("token expired") from e
        except JWTError as e:
            raise JWTInvalidError(f"token invalid: {e}") from e
        return self._parse_claims(raw)

    def verify(self, token: str) -> bool:
        """Return True if `decode()` succeeds, False otherwise.

        Use this only when you don't need the claims; callers that need
        tenant_id should call `decode()` and handle exceptions.
        """
        try:
            self.decode(token)
            return True
        except JWTAuthError:
            return False

    @classmethod
    def _parse_claims(cls, raw: dict[str, Any]) -> JWTClaims:
        # Why: raw is the verified payload; we still validate structural
        # fields (presence + types) here because jose only checks signature
        # and exp — missing tenant_id / sub would otherwise crash later.
        try:
            sub = raw["sub"]
            tenant_id_str = raw["tenant_id"]
            iat = int(raw["iat"])
            exp = int(raw["exp"])
        except KeyError as e:
            raise JWTInvalidError(f"missing required claim: {e.args[0]}") from e
        except (TypeError, ValueError) as e:
            raise JWTInvalidError(f"invalid claim type: {e}") from e

        if not isinstance(sub, str):
            raise JWTInvalidError("'sub' must be a string")
        try:
            tenant_id = UUID(tenant_id_str)
        except (ValueError, TypeError) as e:
            raise JWTInvalidError(f"'tenant_id' is not a valid UUID: {e}") from e

        roles_raw = raw.get("roles", [])
        if not isinstance(roles_raw, list) or not all(isinstance(r, str) for r in roles_raw):
            raise JWTInvalidError("'roles' must be a list of strings")

        extra = {k: v for k, v in raw.items() if k not in cls._RESERVED_CLAIMS}
        return JWTClaims(
            sub=sub,
            tenant_id=tenant_id,
            roles=list(roles_raw),
            iat=iat,
            exp=exp,
            extra=extra,
        )


__all__ = [
    "JWTAuthError",
    "JWTClaims",
    "JWTExpiredError",
    "JWTInvalidError",
    "JWTManager",
]
