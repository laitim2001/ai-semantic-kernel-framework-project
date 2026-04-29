"""
File: backend/tests/unit/platform_layer/observability/test_logger.py
Purpose: Verify PIIRedactor + JSON logger configuration.
Category: Tests / Platform / Observability
Scope: Phase 49 / Sprint 49.4 Day 3
"""

from __future__ import annotations

import io
import json
import logging

import pytest

from platform_layer.observability.logger import (
    PIIRedactor,
    _RedactingJsonFormatter,
)


class TestPIIRedactor:
    @pytest.mark.parametrize(
        "raw,expected_substring,redaction",
        [
            ("Contact me at alice@example.com", "[email]", "@"),
            ("Phone +1 415-555-0100 please", "[phone]", "415"),
            ("SSN 123-45-6789 leaked", "[ssn]", "123-45"),
            ("From IP 192.168.1.55 this morning", "[ipv4]", "192.168"),
        ],
    )
    def test_redacts_pii_patterns(self, raw: str, expected_substring: str, redaction: str) -> None:
        out = PIIRedactor.redact(raw)
        assert expected_substring in out
        assert redaction not in out

    def test_empty_input_returns_empty(self) -> None:
        assert PIIRedactor.redact("") == ""

    def test_no_pii_passes_through(self) -> None:
        msg = "Tenant 7e1c-4b2 created session"
        assert PIIRedactor.redact(msg) == msg


def test_json_formatter_redacts_message_and_emits_valid_json() -> None:
    """_RedactingJsonFormatter outputs JSON with PII redacted in message."""
    formatter = _RedactingJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="user alice@example.com login from 192.168.1.55",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)

    parsed = json.loads(output)
    assert "[email]" in parsed["message"]
    assert "[ipv4]" in parsed["message"]
    assert "alice@example.com" not in parsed["message"]
    assert parsed["level"] == "INFO"
    assert parsed["name"] == "test"


def test_logger_with_extra_fields_serializes_correctly() -> None:
    """logger.info(..., extra={...}) values appear in JSON output."""
    formatter = _RedactingJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    log = logging.getLogger("test.extra")
    log.handlers.clear()
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

    log.info("op done", extra={"tenant_id": "t-42", "duration_ms": 123})

    line = buf.getvalue().strip()
    parsed = json.loads(line)
    assert parsed["tenant_id"] == "t-42"
    assert parsed["duration_ms"] == 123
    assert parsed["message"] == "op done"
