"""
File: backend/src/platform_layer/governance/hitl/teams_webhook.py
Purpose: TeamsWebhookNotifier — Microsoft Teams Incoming Webhook integration.
Category: Platform / Governance / HITL
Scope: Phase 53 / Sprint 53.4 US-6

Description:
    Sends an AdaptiveCard message to a Microsoft Teams channel via Incoming
    Webhook URL. Best-effort — exceptions are logged and swallowed by the
    caller (HITLManager.request_approval) to avoid blocking the HITL flow.

    Per-tenant webhook URL overrides supported via the constructor's
    `tenant_webhook_overrides` mapping (tenant_id → webhook_url). Falls back
    to `default_webhook_url` if no tenant-specific URL.

Created: 2026-05-03 (Sprint 53.4 Day 3)

Modification History:
    - 2026-05-03: Initial creation (Sprint 53.4 Day 3 US-6)

Related:
    - notifier.py (HITLNotifier ABC)
    - manager.py (HITLManager — invokes notifier post-persist)
    - sprint-53-4-plan.md §US-6
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from agent_harness._contracts.hitl import ApprovalRequest
from platform_layer.governance.hitl.notifier import HITLNotifier

logger = logging.getLogger(__name__)


class TeamsWebhookNotifier(HITLNotifier):
    """Posts an AdaptiveCard to Microsoft Teams via Incoming Webhook.

    Args:
        default_webhook_url: fallback URL when no tenant-specific override.
        tenant_webhook_overrides: per-tenant webhook URLs (tenant_id → URL).
        approval_review_url_template: optional template (uses {request_id})
            for a deep-link to the governance approvals page; if None,
            no link is included in the card.
        timeout_s: request timeout (default 5s).
    """

    def __init__(
        self,
        *,
        default_webhook_url: str,
        tenant_webhook_overrides: dict[UUID, str] | None = None,
        approval_review_url_template: str | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        self._default_webhook_url = default_webhook_url
        self._tenant_overrides = tenant_webhook_overrides or {}
        self._review_url_template = approval_review_url_template
        self._timeout_s = timeout_s

    async def notify(self, req: ApprovalRequest) -> None:
        """Send AdaptiveCard for the pending approval (best-effort)."""
        webhook_url = self._tenant_overrides.get(req.tenant_id, self._default_webhook_url)
        card = self._build_card(req)
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(webhook_url, json=card)
                response.raise_for_status()
        except Exception:
            logger.exception("TeamsWebhookNotifier failed for request %s", req.request_id)
            # swallow — manager wraps caller in try/except too, but we don't
            # want even logging failures to escape

    def _build_card(self, req: ApprovalRequest) -> dict[str, Any]:
        """Build a minimal AdaptiveCard JSON payload."""
        review_link = (
            self._review_url_template.format(request_id=req.request_id)
            if self._review_url_template
            else None
        )

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": "🔔 Approval Pending",
                "weight": "Bolder",
                "size": "Medium",
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Tool / Action:", "value": req.requester},
                    {"title": "Risk:", "value": req.risk_level.value},
                    {"title": "Tenant:", "value": str(req.tenant_id)},
                    {
                        "title": "Summary:",
                        "value": str(req.payload.get("summary", "")),
                    },
                ],
            },
        ]

        actions: list[dict[str, Any]] = []
        if review_link:
            actions.append({"type": "Action.OpenUrl", "title": "Review →", "url": review_link})

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                        "actions": actions,
                    },
                }
            ],
        }
