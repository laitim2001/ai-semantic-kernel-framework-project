"""
File: backend/src/platform_layer/identity/oidc.py
Purpose: WorkOS OIDC PKCE flow wrapper — initiate login + exchange callback + signout.
Category: 範疇 Platform Layer / Identity (Sprint 57.7 US-A2)
Scope: Phase 57 / Sprint 57.7 (IAM Foundation Tier 0 spike)
Owner: Platform Layer Identity team

Description:
    Hosted IAM vendor wrapper for WorkOS (chosen per US-A1 4-vendor matrix —
    see iam-vendor-matrix.md). Provides:

    1. initiate_login(redirect_uri) → vendor authorize URL + state stored in
       Redis (TTL 10 min) keyed by state for CSRF protection
    2. exchange_callback(code, state) → vendor SDK code exchange + extract
       subject + return profile (caller does V2 user upsert)
    3. signout(token) → vendor logout redirect URL

    Path 1 per Day 0 D2 verify: V2 internal JWT stays HS256 via JWTManager;
    vendor SDK handles JWKS validation of WorkOS-issued tokens internally.
    NO direct JWKS fetching needed in V2 code.

    Skeleton (Sprint 57.7 Day 1 PM) — full integration tests Day 2 once
    WorkOS B2B account approved (signup approval ~1-2 business days per
    Risk Class A).

Key Components:
    - WorkOSOIDCFlow: main flow class with 3 async methods
    - OIDCConfigError: raised when workos_api_key blank (production safety)
    - OIDCStateError: raised on state mismatch (CSRF protection)

Created: 2026-05-09 (Sprint 57.7 Day 1 PM)
Last Modified: 2026-05-09

Modification History (newest-first):
    - 2026-05-09: Initial skeleton creation (Sprint 57.7 US-A2 Day 1 PM)

Related:
    - iam-vendor-matrix.md (Sprint 57.7 US-A1 vendor decision)
    - core/config/__init__.py (workos_api_key + workos_client_id + oidc_redirect_uri)
    - api/v1/auth.py (3 endpoints consume this flow)
    - .claude/rules/llm-provider-neutrality.md (workos is auth SDK; LLM SDK rule N/A)
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.config import get_settings

if TYPE_CHECKING:
    # Defer workos import to runtime methods so module imports cleanly even
    # when WorkOS SDK not yet pip-installed (Day 1 PM skeleton phase before
    # Day 2 vendor account + pip install -r requirements.txt).
    pass

logger = logging.getLogger(__name__)


class OIDCConfigError(RuntimeError):
    """Raised when WorkOS configuration is missing (workos_api_key blank)."""


class OIDCStateError(ValueError):
    """Raised when callback state does not match initiate_login state (CSRF)."""


@dataclass(frozen=True)
class OIDCProfile:
    """Subset of vendor profile used by V2 user upsert pathway."""

    external_id: str  # WorkOS user_id (subject) → users.external_id lookup
    email: str
    first_name: str | None
    last_name: str | None
    raw_id_token: str  # opaque vendor JWT (V2 does not decode; SDK validates)


class WorkOSOIDCFlow:
    """OIDC PKCE flow via WorkOS Hosted IAM.

    Stateless wrapper (no Redis dependency in skeleton; state replay
    protection deferred to Day 2 with proper Redis-backed state store).

    Production usage:

        flow = WorkOSOIDCFlow()
        authorize_url, state = flow.initiate_login(redirect_uri="...")
        # browser → WorkOS → IdP login → callback
        profile = flow.exchange_callback(code=..., state=...)
        # caller upserts users row via profile.external_id + profile.email
    """

    def __init__(self) -> None:
        s = get_settings()
        self._api_key = s.workos_api_key
        self._client_id = s.workos_client_id
        self._default_redirect_uri = s.oidc_redirect_uri

    def _require_configured(self) -> None:
        """Raise OIDCConfigError if WorkOS not configured."""
        if not self._api_key or not self._client_id:
            raise OIDCConfigError(
                "WorkOS not configured: set WORKOS_API_KEY + WORKOS_CLIENT_ID env vars"
            )

    def initiate_login(self, *, redirect_uri: str | None = None) -> tuple[str, str]:
        """Generate vendor authorize URL + state for CSRF protection.

        Args:
            redirect_uri: Override default oidc_redirect_uri Setting.

        Returns:
            Tuple of (authorize_url, state). Caller stores state in
            session/cookie for callback validation.

        Raises:
            OIDCConfigError: WorkOS not configured.
        """
        self._require_configured()
        # SKELETON: Day 2 will replace with real workos.SSO.get_authorization_url
        # call. State generation logic stays in V2 (CSRF token).
        state = secrets.token_urlsafe(32)
        target_redirect = redirect_uri or self._default_redirect_uri
        # Day 2 real impl:
        #   from workos import WorkOSClient
        #   client = WorkOSClient(api_key=self._api_key, client_id=self._client_id)
        #   authorize_url = client.sso.get_authorization_url(
        #       redirect_uri=target_redirect, state=state, ...)
        authorize_url = (
            f"https://api.workos.com/sso/authorize"
            f"?client_id={self._client_id}"
            f"&redirect_uri={target_redirect}"
            f"&response_type=code"
            f"&state={state}"
        )
        logger.info(
            "oidc.initiate_login",
            extra={"redirect_uri": target_redirect, "state_len": len(state)},
        )
        return authorize_url, state

    def exchange_callback(self, *, code: str, state: str, expected_state: str) -> OIDCProfile:
        """Exchange authorization code for vendor profile.

        Args:
            code: Authorization code from vendor callback query param.
            state: State value returned by vendor callback.
            expected_state: State previously stored at initiate_login (caller
                retrieves from session/cookie/Redis).

        Returns:
            OIDCProfile with external_id (WorkOS user_id), email, name,
            raw_id_token.

        Raises:
            OIDCConfigError: WorkOS not configured.
            OIDCStateError: state mismatch (CSRF / replay).
        """
        self._require_configured()
        if state != expected_state:
            raise OIDCStateError("state mismatch — possible CSRF or replay attack")
        # SKELETON: Day 2 replace with real workos SDK call:
        #   profile_and_token = client.sso.get_profile_and_token(code=code)
        #   profile = profile_and_token.profile
        #   id_token = profile_and_token.access_token
        # Returning placeholder for skeleton structural verify.
        logger.info("oidc.exchange_callback", extra={"code_len": len(code)})
        return OIDCProfile(
            external_id="placeholder-workos-user-id",
            email="placeholder@example.com",
            first_name=None,
            last_name=None,
            raw_id_token="placeholder-jwt",
        )

    def signout_url(self, *, return_to: str) -> str:
        """Vendor signout URL — caller redirects browser to this URL.

        Args:
            return_to: URL to redirect to after vendor logout.

        Returns:
            Vendor logout URL.

        Raises:
            OIDCConfigError: WorkOS not configured.
        """
        self._require_configured()
        # SKELETON: Day 2 vendor SDK provides logout_url helper; for now
        # construct manually per WorkOS SSO docs.
        return f"https://api.workos.com/sso/logout?return_to={return_to}"


__all__ = ["WorkOSOIDCFlow", "OIDCProfile", "OIDCConfigError", "OIDCStateError"]
