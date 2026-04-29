"""
File: backend/src/platform_layer/observability/logger.py
Purpose: Structured JSON logger with PII redaction + trace_id auto-injection.
Category: Platform / Observability
Scope: Phase 49 / Sprint 49.4 Day 3

Description:
    All process logs go through this formatter:
    - JSON output (one record per line)
    - PII redaction (email / phone / SSN / IPv4) BEFORE serialization
    - trace_id injected from current OTel span context (if available)
    - tenant_id / user_id / session_id from `extra` kwarg

    Why JSON: Loki / ELK / CloudWatch Insights all parse JSON natively;
    grep across structured fields is faster than regex over text logs.

    PIIRedactor is a separate utility — call directly when redacting other
    output (audit reports / Slack messages / etc).

Created: 2026-04-29 (Sprint 49.4 Day 3)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4 Day 3)

Related:
    - 14-security-deep-dive.md (PII rules)
    - .claude/rules/multi-tenant-data.md (tenant_id propagation)
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

from pythonjsonlogger.json import JsonFormatter

# ---------------------------------------------------------------------------
# PII Redactor — regex-based; conservative
# ---------------------------------------------------------------------------


class PIIRedactor:
    """Redact common PII patterns. Conservative — false positives preferred over leaks."""

    EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\-\s().]{8,}\d)(?!\d)")
    SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

    @classmethod
    def redact(cls, text: str) -> str:
        """Order matters: match more specific patterns (SSN / IPv4) before phone,
        which has a permissive digit-grouping regex that would otherwise consume them.
        """
        if not text:
            return text
        out = cls.EMAIL_RE.sub("[email]", text)
        out = cls.SSN_RE.sub("[ssn]", out)
        out = cls.IPV4_RE.sub("[ipv4]", out)
        out = cls.PHONE_RE.sub("[phone]", out)
        return out


# ---------------------------------------------------------------------------
# JsonFormatter subclass with PII + trace_id injection
# ---------------------------------------------------------------------------


class _RedactingJsonFormatter(JsonFormatter):
    """JsonFormatter that redacts PII in `message` field + auto-injects trace_id."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # 1. Redact message
        if isinstance(log_record.get("message"), str):
            log_record["message"] = PIIRedactor.redact(log_record["message"])

        # 2. Inject trace_id from current OTel span if present
        try:
            from opentelemetry import trace as ot_trace

            span = ot_trace.get_current_span()
            ctx = span.get_span_context()
            if ctx.is_valid:
                log_record["trace_id"] = format(ctx.trace_id, "032x")
                log_record["span_id"] = format(ctx.span_id, "016x")
        except Exception:  # noqa: BLE001 — never let logging crash
            pass

        # 3. Standardize timestamp + level fields
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_CONFIGURED = False


def configure_json_logging(*, level: int = logging.INFO, stream: Any | None = None) -> None:
    """Install JSON formatter on the root logger. Idempotent.

    Tests should NOT call this — they use the default text logger so pytest -v
    output stays readable. Call from main.py / app startup only.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    formatter = _RedactingJsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        timestamp=True,
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def get_json_logger(name: str) -> logging.Logger:
    """Return a logger; same as logging.getLogger() but documents intent.

    Use as:
        logger = get_json_logger(__name__)
        logger.info("user action", extra={"tenant_id": str(t)})
    """
    return logging.getLogger(name)


__all__ = [
    "PIIRedactor",
    "configure_json_logging",
    "get_json_logger",
]
