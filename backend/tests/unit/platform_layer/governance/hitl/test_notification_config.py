"""
File: backend/tests/unit/platform_layer/governance/hitl/test_notification_config.py
Purpose: Unit tests for load_notifier_from_config (Sprint 53.5 US-4).
Category: Tests / Unit / Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.5 US-4

Cases:
    - YAML missing → NoopNotifier (with WARNING)
    - teams.enabled=false → NoopNotifier
    - empty webhook + no overrides → NoopNotifier
    - default webhook resolves → TeamsWebhookNotifier
    - per-tenant override resolves (default empty) → TeamsWebhookNotifier
    - env var interpolation with set var → resolved
    - env var interpolation with unset var → falls back to empty → NoopNotifier
    - per-tenant override with invalid UUID key → ValueError
    - per-tenant override with non-mapping → ValueError

Created: 2026-05-04 (Sprint 53.5 Day 1)
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from platform_layer.governance.hitl.notifier import (
    NoopNotifier,
    load_notifier_from_config,
)
from platform_layer.governance.hitl.teams_webhook import TeamsWebhookNotifier


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "notification.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_missing_file_returns_noop(tmp_path: Path) -> None:
    notifier = load_notifier_from_config(tmp_path / "does-not-exist.yaml")
    assert isinstance(notifier, NoopNotifier)


def test_teams_disabled_returns_noop(tmp_path: Path) -> None:
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: false
  default_webhook: https://example.com/hook
""",
    )
    notifier = load_notifier_from_config(cfg)
    assert isinstance(notifier, NoopNotifier)


def test_empty_webhook_no_overrides_returns_noop(tmp_path: Path) -> None:
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: ""
  per_tenant_overrides: {}
""",
    )
    notifier = load_notifier_from_config(cfg)
    assert isinstance(notifier, NoopNotifier)


def test_default_webhook_returns_teams_notifier(tmp_path: Path) -> None:
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: https://teams.example.com/hook/abc
  timeout_s: 7.5
""",
    )
    notifier = load_notifier_from_config(cfg)
    assert isinstance(notifier, TeamsWebhookNotifier)


def test_per_tenant_override_resolves(tmp_path: Path) -> None:
    """Override-only (default empty) still returns Teams notifier."""
    tid = uuid4()
    cfg = _write_yaml(
        tmp_path,
        f"""
version: "1.0"
teams:
  enabled: true
  default_webhook: ""
  per_tenant_overrides:
    {tid}: https://teams.example.com/tenant/{tid}/hook
""",
    )
    notifier = load_notifier_from_config(cfg)
    assert isinstance(notifier, TeamsWebhookNotifier)


def test_env_var_set_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_TEAMS_WEBHOOK", "https://teams.example.com/from-env")
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: ${TEST_TEAMS_WEBHOOK}
""",
    )
    notifier = load_notifier_from_config(cfg)
    assert isinstance(notifier, TeamsWebhookNotifier)


def test_env_var_unset_falls_back_to_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_MISSING_WEBHOOK_VAR", raising=False)
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: ${TEST_MISSING_WEBHOOK_VAR}
""",
    )
    notifier = load_notifier_from_config(cfg)
    # Empty resolved URL + no overrides → NoopNotifier.
    assert isinstance(notifier, NoopNotifier)


def test_invalid_tenant_uuid_raises(tmp_path: Path) -> None:
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: https://teams.example.com/default
  per_tenant_overrides:
    not-a-uuid: https://teams.example.com/x
""",
    )
    with pytest.raises(ValueError, match="not a valid UUID"):
        load_notifier_from_config(cfg)


def test_per_tenant_override_non_mapping_raises(tmp_path: Path) -> None:
    cfg = _write_yaml(
        tmp_path,
        """
version: "1.0"
teams:
  enabled: true
  default_webhook: https://teams.example.com/default
  per_tenant_overrides:
    - "wrong"
    - "structure"
""",
    )
    with pytest.raises(ValueError, match="must be a mapping"):
        load_notifier_from_config(cfg)


def test_real_repo_config_loads(tmp_path: Path) -> None:
    """Smoke: backend/config/notification.yaml parses without error.

    Without env vars set, falls back to NoopNotifier (default webhook empty).
    """
    repo_config = Path(__file__).resolve().parents[5] / "config" / "notification.yaml"
    if not repo_config.exists():
        pytest.skip("config/notification.yaml not present")
    # Don't pollute test env: ensure TEAMS_WEBHOOK_URL unset for this test.
    os.environ.pop("TEAMS_WEBHOOK_URL", None)
    notifier = load_notifier_from_config(repo_config)
    # Repo default has env-driven webhook; without env → NoopNotifier.
    assert isinstance(notifier, NoopNotifier)
