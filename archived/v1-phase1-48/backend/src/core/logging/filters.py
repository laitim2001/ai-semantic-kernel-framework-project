"""Sensitive information filter for structured logging.

Sprint 122, Story 122-3: Implements a structlog processor that detects
and masks sensitive fields in log event dictionaries. Prevents accidental
leakage of passwords, tokens, API keys, and other credentials.

Masked Fields (case-insensitive, partial match):
    password, secret, token, api_key, apikey, authorization,
    credential, private_key, access_key

Usage:
    import structlog
    from src.core.logging.filters import SensitiveInfoFilter

    structlog.configure(
        processors=[
            SensitiveInfoFilter(),
            structlog.processors.JSONRenderer(),
        ]
    )
"""

import re
from typing import Any

# Patterns that indicate a field contains sensitive data.
# Matched case-insensitively against field names.
_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"access[_-]?key", re.IGNORECASE),
    re.compile(r"connection[_-]?string", re.IGNORECASE),
]

# Replacement value for masked fields
_MASK = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    """Check if a field name matches any sensitive pattern.

    Args:
        key: The field name to check.

    Returns:
        True if the field name matches a sensitive pattern.
    """
    return any(pattern.search(key) for pattern in _SENSITIVE_PATTERNS)


def _mask_value(value: Any) -> Any:
    """Mask a sensitive value.

    For strings, returns the mask. For other types, returns the mask
    string as well (to avoid type errors in JSON serialization).

    Args:
        value: The value to mask.

    Returns:
        The masked replacement value.
    """
    if value is None or value == "":
        return value
    return _MASK


def _mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive fields in a dictionary.

    Args:
        data: Dictionary to scan for sensitive fields.

    Returns:
        A new dictionary with sensitive values replaced by _MASK.
    """
    result = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            result[key] = _mask_value(value)
        elif isinstance(value, dict):
            result[key] = _mask_dict(value)
        elif isinstance(value, list):
            result[key] = _mask_list(value)
        else:
            result[key] = value
    return result


def _mask_list(data: list[Any]) -> list[Any]:
    """Recursively mask sensitive fields in list elements.

    Args:
        data: List to scan for dictionaries with sensitive fields.

    Returns:
        A new list with sensitive values in nested dicts masked.
    """
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(_mask_dict(item))
        elif isinstance(item, list):
            result.append(_mask_list(item))
        else:
            result.append(item)
    return result


class SensitiveInfoFilter:
    """Structlog processor that masks sensitive fields in log events.

    Scans all top-level and nested dictionary fields in the event_dict
    for keys matching sensitive patterns (password, secret, token, etc.)
    and replaces their values with '***REDACTED***'.

    This processor should be placed before the JSON renderer in the
    structlog processor chain.

    Example:
        Input:  {"event": "login", "password": "abc123", "user": "admin"}
        Output: {"event": "login", "password": "***REDACTED***", "user": "admin"}
    """

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a log event dictionary, masking sensitive fields.

        Args:
            logger: The wrapped logger object.
            method_name: The name of the log method called.
            event_dict: The event dictionary being processed.

        Returns:
            The event dictionary with sensitive values masked.
        """
        return _mask_dict(event_dict)
