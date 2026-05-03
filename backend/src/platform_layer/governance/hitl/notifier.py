"""
File: backend/src/platform_layer/governance/hitl/notifier.py
Purpose: HITLNotifier ABC + load_notifier_from_config factory.
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-6 / Sprint 53.5 US-4

Description:
    Notifiers are invoked by HITLManager.request_approval() AFTER the request
    is persisted. Failures must NOT block the HITL flow — caller wraps in
    try/except.

    Production deployments wire `TeamsWebhookNotifier` (default). Tests use
    `NoopNotifier` or a list-collector fake.

    Sprint 53.5 US-4 adds `load_notifier_from_config(config_path)` which
    parses backend/config/notification.yaml + env var interpolation +
    per-tenant overrides; returns a HITLNotifier instance. Falls back to
    NoopNotifier when the YAML is missing or the default webhook URL is
    unresolved.

Created: 2026-05-03 (Sprint 53.4 Day 3)

Modification History:
    - 2026-05-04: Add load_notifier_from_config + ENV interpolation (Sprint 53.5 US-4)
    - 2026-05-03: Initial creation (Sprint 53.4 Day 3 US-6)

Related:
    - platform_layer/governance/hitl/manager.py
    - platform_layer/governance/hitl/teams_webhook.py
    - backend/config/notification.yaml
    - 17-cross-category-interfaces.md §5 (HITL centralization)
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml  # type: ignore[import-untyped, unused-ignore]

from agent_harness._contracts.hitl import ApprovalRequest

logger = logging.getLogger(__name__)


class HITLNotifier(ABC):
    """ABC for HITL pending-request notification channels."""

    @abstractmethod
    async def notify(self, req: ApprovalRequest) -> None:
        """Best-effort notification; failures do not block HITL flow."""
        ...


class NoopNotifier(HITLNotifier):
    """No-op notifier (default for tests; production should wire a real one)."""

    async def notify(self, req: ApprovalRequest) -> None:
        return None


# ---------------------------------------------------------------------------
# Config loader (Sprint 53.5 US-4)
# ---------------------------------------------------------------------------

# ${VAR} matcher; ${VAR:-default} not supported (keep loader simple — env
# expansion is just a convenience; missing values return empty string).
_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    """Recursively expand ${VAR} in strings; preserve other types as-is."""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_notifier_from_config(config_path: str | Path) -> HITLNotifier:
    """Build a HITLNotifier from notification.yaml.

    Returns NoopNotifier (with WARNING log) when:
      - file missing
      - teams.enabled = false
      - default_webhook empty AND no per-tenant override resolves

    Otherwise returns TeamsWebhookNotifier wired with the config.

    Args:
        config_path: absolute or repo-relative path to notification.yaml.

    Raises:
        ValueError: malformed YAML structure (typed validation, not env miss).
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning("notification.yaml not found at %s; falling back to NoopNotifier", path)
        return NoopNotifier()

    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = _expand_env(raw)

    teams_cfg: dict[str, Any] = cfg.get("teams", {})
    if not teams_cfg.get("enabled", True):
        logger.info("notification.yaml teams.enabled=false; using NoopNotifier")
        return NoopNotifier()

    default_webhook = (teams_cfg.get("default_webhook") or "").strip()
    overrides_raw = teams_cfg.get("per_tenant_overrides") or {}
    if not isinstance(overrides_raw, dict):
        raise ValueError(
            f"notification.yaml teams.per_tenant_overrides must be a mapping, "
            f"got {type(overrides_raw).__name__}"
        )

    # Build the UUID-keyed override map; skip entries with empty resolved URL.
    overrides: dict[UUID, str] = {}
    for tenant_str, url in overrides_raw.items():
        url_clean = (url or "").strip()
        if not url_clean:
            continue
        try:
            overrides[UUID(str(tenant_str))] = url_clean
        except ValueError:
            raise ValueError(
                f"notification.yaml teams.per_tenant_overrides key {tenant_str!r} "
                "is not a valid UUID"
            ) from None

    if not default_webhook and not overrides:
        logger.warning("notification.yaml has no resolved webhook URL; using NoopNotifier")
        return NoopNotifier()

    # Lazy import to avoid circular (teams_webhook imports HITLNotifier from here).
    from platform_layer.governance.hitl.teams_webhook import TeamsWebhookNotifier

    return TeamsWebhookNotifier(
        default_webhook_url=default_webhook,
        tenant_webhook_overrides=overrides if overrides else None,
        approval_review_url_template=teams_cfg.get("approval_review_url_template"),
        timeout_s=float(teams_cfg.get("timeout_s", 5.0)),
    )


__all__ = [
    "HITLNotifier",
    "NoopNotifier",
    "load_notifier_from_config",
]
