"""
File: backend/src/api/v1/auth.py
Purpose: OIDC PKCE auth endpoints — login redirect + callback exchange + logout.
Category: api/v1 (Sprint 57.7 US-A2)
Scope: Phase 57 / Sprint 57.7 (IAM Foundation Tier 0 spike)

Description:
    Three endpoints implementing OIDC PKCE flow via WorkOS Hosted IAM:

    - GET /api/v1/auth/login    — generate vendor authorize URL + 302 redirect
    - GET /api/v1/auth/callback — exchange code + V2 user upsert + V2 JWT issue
    - POST /api/v1/auth/logout  — vendor signout redirect

    State CSRF protection via httpOnly secure cookie set by /login + read by
    /callback. Day 1 skeleton uses cookie; Day 2 may upgrade to Redis-backed
    state store for distributed deployment.

    V2 internal JWT remains HS256 per Day 0 D2 verify (Path 1) — vendor SDK
    handles vendor JWT (RS256) validation internally. Callback issues V2
    HS256 JWT via JWTManager.encode() and returns to caller as cookie.

Created: 2026-05-09 (Sprint 57.7 Day 1 PM)
Last Modified: 2026-05-09

Modification History (newest-first):
    - 2026-05-09: Initial skeleton creation (Sprint 57.7 US-A2 Day 1 PM)

Related:
    - platform_layer/identity/oidc.py (WorkOSOIDCFlow consumer)
    - platform_layer/identity/jwt.py (JWTManager.encode for V2 JWT issue)
    - infrastructure/db/models/identity.py (User upsert via external_id)
    - api/main.py (router include)
    - iam-vendor-matrix.md (Sprint 57.7 US-A1 vendor decision)
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from platform_layer.identity.jwt import JWTManager
from platform_layer.identity.oidc import (
    OIDCConfigError,
    OIDCStateError,
    WorkOSOIDCFlow,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ---- Cookie names + TTL --------------------------------------------------
# Why httpOnly secure cookie: prevents JS access (XSS mitigation) + browser
# auto-sends to /callback for state validation. SameSite=Lax allows the
# vendor redirect (cross-site) to deliver the cookie back.
_STATE_COOKIE = "oidc_state"
_REDIRECT_COOKIE = "oidc_redirect_to"
_JWT_COOKIE = "v2_jwt"
_STATE_TTL_SECONDS = 600  # 10 min


class LogoutResponse(BaseModel):
    redirect_to: str


@router.get("/login")
async def login(
    redirect_to: str = Query(default="/cost-dashboard"),
) -> RedirectResponse:
    """Initiate OIDC login — 302 redirect to vendor authorize URL.

    Sets oidc_state + oidc_redirect_to cookies so /callback can validate
    state (CSRF) and know where to redirect the user post-login.
    """
    try:
        flow = WorkOSOIDCFlow()
        authorize_url, state = flow.initiate_login()
    except OIDCConfigError as exc:
        logger.error("auth.login: WorkOS not configured", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    response = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=False,  # Day 2: True in prod (set via Settings.cookie_secure)
        samesite="lax",
    )
    response.set_cookie(
        key=_REDIRECT_COOKIE,
        value=redirect_to,
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    oidc_state: str | None = Cookie(default=None),
    oidc_redirect_to: str | None = Cookie(default=None),
) -> RedirectResponse:
    """Exchange OIDC callback code → vendor profile → V2 user upsert + V2 JWT.

    Day 1 skeleton: state validation + skeleton profile return + V2 JWT
    issue. User upsert via SQL deferred to Day 2 (needs DB session DI +
    Multi-tenant 鐵律 #2 tenant_id resolution path TBD).
    """
    if oidc_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing oidc_state cookie",
        )

    try:
        flow = WorkOSOIDCFlow()
        profile = flow.exchange_callback(
            code=code,
            state=state,
            expected_state=oidc_state,
        )
    except OIDCStateError as exc:
        logger.warning("auth.callback: state mismatch")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OIDCConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # SKELETON Day 1: V2 user upsert deferred to Day 2.
    # Day 2 implementation:
    #   async with get_session_factory()() as session:
    #       user = await session.execute(
    #           select(User).where(User.external_id == profile.external_id)
    #       )
    #       if not user:
    #           user = User(email=profile.email, external_id=profile.external_id, ...)
    #           session.add(user)
    #           await session.commit()
    #   tenant_id = user.tenant_id  # from User.tenant_id FK
    placeholder_user_id = uuid4()
    placeholder_tenant_id = UUID("00000000-0000-0000-0000-000000000000")  # default tenant

    jwt_manager = JWTManager()
    v2_jwt = jwt_manager.encode(
        sub=str(placeholder_user_id),
        tenant_id=placeholder_tenant_id,
        roles=["user"],  # Day 2 will look up via RBACManager (US-A3)
        extra={"email": profile.email, "external_id": profile.external_id},
    )

    final_redirect = oidc_redirect_to or "/cost-dashboard"
    response = RedirectResponse(
        url=final_redirect,
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key=_JWT_COOKIE,
        value=v2_jwt,
        max_age=3600,  # 1 hour matches jwt_expires_minutes default
        httponly=True,
        secure=False,
        samesite="lax",
    )
    # Clear ephemeral state cookies
    response.delete_cookie(_STATE_COOKIE)
    response.delete_cookie(_REDIRECT_COOKIE)
    return response


@router.post("/logout")
async def logout(
    return_to: str = Query(default="/auth/login"),
) -> JSONResponse:
    """Vendor signout + clear V2 JWT cookie.

    Returns JSON with vendor logout URL so frontend can redirect browser
    (POST → 302 chain not ideal; let frontend handle redirect explicitly).
    """
    try:
        flow = WorkOSOIDCFlow()
        # Encode return_to for safety even if vendor SDK does it (defense in depth)
        signout_url = flow.signout_url(return_to=quote_plus(return_to))
    except OIDCConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    body = LogoutResponse(redirect_to=signout_url).model_dump()
    response = JSONResponse(content=body)
    response.delete_cookie(_JWT_COOKIE)
    return response
