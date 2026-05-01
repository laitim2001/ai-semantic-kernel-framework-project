"""
File: backend/tests/unit/platform_layer/identity/test_jwt.py
Purpose: Unit tests for JWTManager (encode/decode/verify) + JWTClaims parser.
Category: Tests / Unit / Platform layer
Scope: Sprint 52.5 Day 1.2 (P0 #14)

Cases (8+):
    - encode → decode round-trip preserves all claims
    - verify() returns True for valid, False for invalid
    - decode() raises JWTExpiredError on expired token
    - decode() raises JWTInvalidError on bad signature
    - decode() raises JWTInvalidError on malformed token
    - decode() raises JWTInvalidError on missing required claim
    - decode() raises JWTInvalidError on invalid tenant_id UUID
    - extra claims are preserved; reserved claim names rejected at encode

Created: 2026-05-01 (Sprint 52.5 Day 1.2)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from jose import jwt as jose_jwt

from platform_layer.identity.jwt import (
    JWTAuthError,
    JWTClaims,
    JWTExpiredError,
    JWTInvalidError,
    JWTManager,
)


# === Fixtures =====================================================


@pytest.fixture
def secret() -> str:
    return "test-secret-key-do-not-use-in-prod"


@pytest.fixture
def manager(secret: str) -> JWTManager:
    return JWTManager(secret=secret, algorithm="HS256", expires_minutes=60)


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


# === Round-trip ===================================================


def test_encode_decode_round_trip_preserves_all_claims(
    manager: JWTManager, tenant_id: UUID, user_id: UUID
) -> None:
    token = manager.encode(
        sub=str(user_id),
        tenant_id=tenant_id,
        roles=["admin", "auditor"],
    )
    claims = manager.decode(token)

    assert isinstance(claims, JWTClaims)
    assert claims.sub == str(user_id)
    assert claims.tenant_id == tenant_id
    assert claims.roles == ["admin", "auditor"]
    assert claims.iat > 0
    assert claims.exp > claims.iat


def test_verify_returns_true_for_valid_token(
    manager: JWTManager, tenant_id: UUID, user_id: UUID
) -> None:
    token = manager.encode(sub=str(user_id), tenant_id=tenant_id)
    assert manager.verify(token) is True


def test_verify_returns_false_for_invalid_token(manager: JWTManager) -> None:
    assert manager.verify("not.a.valid.jwt.string") is False


# === Expiration ==================================================


def test_decode_raises_expired_error_when_exp_passed(
    secret: str, tenant_id: UUID, user_id: UUID
) -> None:
    # Why: minted with negative expiration so it's pre-expired the moment
    # encode() returns. Exercises the ExpiredSignatureError path.
    manager = JWTManager(secret=secret, algorithm="HS256", expires_minutes=-1)
    token = manager.encode(sub=str(user_id), tenant_id=tenant_id)
    with pytest.raises(JWTExpiredError):
        manager.decode(token)


# === Bad signature / malformed ===================================


def test_decode_raises_invalid_for_bad_signature(
    manager: JWTManager, secret: str, tenant_id: UUID, user_id: UUID
) -> None:
    other = JWTManager(
        secret=secret + "tampered", algorithm="HS256", expires_minutes=60
    )
    token = other.encode(sub=str(user_id), tenant_id=tenant_id)
    with pytest.raises(JWTInvalidError):
        manager.decode(token)


def test_decode_raises_invalid_for_malformed_token(manager: JWTManager) -> None:
    with pytest.raises(JWTInvalidError):
        manager.decode("garbage.but.three.parts")


# === Missing / invalid claims ====================================


def test_decode_raises_invalid_when_tenant_id_missing(
    secret: str, user_id: UUID
) -> None:
    # Construct payload directly (bypassing encode()) to inject a token
    # with valid signature but missing tenant_id claim.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    token = jose_jwt.encode(payload, secret, algorithm="HS256")
    manager = JWTManager(secret=secret, algorithm="HS256", expires_minutes=60)
    with pytest.raises(JWTInvalidError, match="missing required claim"):
        manager.decode(token)


def test_decode_raises_invalid_for_non_uuid_tenant_id(
    secret: str, user_id: UUID
) -> None:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": "not-a-uuid",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    token = jose_jwt.encode(payload, secret, algorithm="HS256")
    manager = JWTManager(secret=secret, algorithm="HS256", expires_minutes=60)
    with pytest.raises(JWTInvalidError, match="not a valid UUID"):
        manager.decode(token)


# === Extra claims =================================================


def test_extra_claims_preserved_in_decode(
    manager: JWTManager, tenant_id: UUID, user_id: UUID
) -> None:
    token = manager.encode(
        sub=str(user_id),
        tenant_id=tenant_id,
        extra={"correlation_id": "abc-123", "issuer": "test-issuer"},
    )
    claims = manager.decode(token)
    assert claims.extra == {
        "correlation_id": "abc-123",
        "issuer": "test-issuer",
    }


def test_encode_rejects_reserved_claim_in_extra(
    manager: JWTManager, tenant_id: UUID, user_id: UUID
) -> None:
    # `exp` collides with managed claim — must raise rather than override.
    with pytest.raises(ValueError, match="reserved standard claim"):
        manager.encode(
            sub=str(user_id),
            tenant_id=tenant_id,
            extra={"exp": 0},
        )


# === Hierarchy ===================================================


def test_expired_error_is_subclass_of_auth_error(
    secret: str, tenant_id: UUID, user_id: UUID
) -> None:
    # Allows callers to except JWTAuthError once for both expired/invalid.
    manager = JWTManager(secret=secret, algorithm="HS256", expires_minutes=-1)
    token = manager.encode(sub=str(user_id), tenant_id=tenant_id)
    with pytest.raises(JWTAuthError):
        manager.decode(token)


def test_invalid_error_is_subclass_of_auth_error(manager: JWTManager) -> None:
    with pytest.raises(JWTAuthError):
        manager.decode("garbage.but.three.parts")
