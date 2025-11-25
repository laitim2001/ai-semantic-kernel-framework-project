"""
Input Validators and Sanitizers

Sprint 3 - Story S3-2: API Security Hardening

Provides input validation and sanitization utilities.
"""
import html
import logging
import re
from typing import Annotated, Any, List, Optional, Pattern
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field, ValidationError, field_validator

from .config import SecurityConfig, security_config

logger = logging.getLogger(__name__)

# Regex patterns for validation
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)
URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})(?::\d+)?(?:/[^\s]*)?$"
)
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Characters that should be escaped or removed
DANGEROUS_CHARS = re.compile(r"[<>\"';&|`$(){}]")
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE)\b)",
    re.IGNORECASE
)
XSS_PATTERN = re.compile(
    r"(<script|javascript:|on\w+\s*=|data:text/html)",
    re.IGNORECASE
)


def sanitize_string(
    value: str,
    max_length: Optional[int] = None,
    allow_html: bool = False,
    strip_dangerous: bool = True,
) -> str:
    """Sanitize a string input.

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags
        strip_dangerous: Whether to remove dangerous characters

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value) if value is not None else ""

    # Strip whitespace
    value = value.strip()

    # Truncate if needed
    if max_length and len(value) > max_length:
        value = value[:max_length]
        logger.debug(f"String truncated to {max_length} characters")

    # HTML escape if not allowing HTML
    if not allow_html:
        value = html.escape(value)

    # Remove dangerous characters
    if strip_dangerous:
        value = DANGEROUS_CHARS.sub("", value)

    return value


def validate_uuid(value: str) -> UUID:
    """Validate and parse a UUID string.

    Args:
        value: UUID string

    Returns:
        UUID object

    Raises:
        ValueError: If invalid UUID
    """
    if isinstance(value, UUID):
        return value

    if not UUID_PATTERN.match(str(value)):
        raise ValueError(f"Invalid UUID format: {value}")

    return UUID(str(value))


def validate_email(value: str) -> str:
    """Validate an email address.

    Args:
        value: Email string

    Returns:
        Validated email (lowercase)

    Raises:
        ValueError: If invalid email
    """
    value = value.strip().lower()

    if not EMAIL_PATTERN.match(value):
        raise ValueError(f"Invalid email format: {value}")

    if len(value) > 254:
        raise ValueError("Email too long (max 254 characters)")

    return value


def validate_url(value: str, require_https: bool = False) -> str:
    """Validate a URL.

    Args:
        value: URL string
        require_https: Whether to require HTTPS

    Returns:
        Validated URL

    Raises:
        ValueError: If invalid URL
    """
    value = value.strip()

    if require_https and not value.startswith("https://"):
        raise ValueError("URL must use HTTPS")

    if not URL_PATTERN.match(value):
        raise ValueError(f"Invalid URL format: {value}")

    if len(value) > 2048:
        raise ValueError("URL too long (max 2048 characters)")

    return value


def check_sql_injection(value: str) -> bool:
    """Check if string contains potential SQL injection.

    Args:
        value: String to check

    Returns:
        True if potential SQL injection detected
    """
    return bool(SQL_INJECTION_PATTERN.search(value))


def check_xss(value: str) -> bool:
    """Check if string contains potential XSS.

    Args:
        value: String to check

    Returns:
        True if potential XSS detected
    """
    return bool(XSS_PATTERN.search(value))


def _sanitize_validator(value: str) -> str:
    """Pydantic validator for sanitizing strings."""
    if not isinstance(value, str):
        return value
    return sanitize_string(value, max_length=security_config.max_string_length)


def _check_injection_validator(value: str) -> str:
    """Pydantic validator to check for injection attacks."""
    if not isinstance(value, str):
        return value

    if check_sql_injection(value):
        logger.warning(f"Potential SQL injection detected: {value[:50]}...")
        raise ValueError("Invalid input: potential SQL injection detected")

    if check_xss(value):
        logger.warning(f"Potential XSS detected: {value[:50]}...")
        raise ValueError("Invalid input: potential XSS detected")

    return value


# Annotated types for Pydantic models
SafeString = Annotated[
    str,
    BeforeValidator(_sanitize_validator),
    AfterValidator(_check_injection_validator),
]

SafeEmail = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().lower() if isinstance(v, str) else v),
    AfterValidator(validate_email),
]

SafeUUID = Annotated[
    str,
    AfterValidator(validate_uuid),
]

SafeURL = Annotated[
    str,
    BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v),
    AfterValidator(validate_url),
]


class InputValidator:
    """Utility class for input validation.

    Provides static methods for validating various input types.

    Example:
        if InputValidator.is_safe_string(user_input):
            process(user_input)
    """

    @staticmethod
    def is_safe_string(value: str, max_length: int = 10000) -> bool:
        """Check if string is safe (no injection patterns).

        Args:
            value: String to check
            max_length: Maximum allowed length

        Returns:
            True if safe
        """
        if not isinstance(value, str):
            return False

        if len(value) > max_length:
            return False

        if check_sql_injection(value):
            return False

        if check_xss(value):
            return False

        return True

    @staticmethod
    def is_valid_email(value: str) -> bool:
        """Check if value is a valid email.

        Args:
            value: Email to check

        Returns:
            True if valid
        """
        try:
            validate_email(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Check if value is a valid UUID.

        Args:
            value: UUID to check

        Returns:
            True if valid
        """
        try:
            validate_uuid(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_url(value: str, require_https: bool = False) -> bool:
        """Check if value is a valid URL.

        Args:
            value: URL to check
            require_https: Whether to require HTTPS

        Returns:
            True if valid
        """
        try:
            validate_url(value, require_https=require_https)
            return True
        except ValueError:
            return False

    @staticmethod
    def sanitize_for_log(value: str, max_length: int = 200) -> str:
        """Sanitize a value for safe logging.

        Args:
            value: Value to sanitize
            max_length: Maximum length in log

        Returns:
            Sanitized string safe for logging
        """
        if not isinstance(value, str):
            value = str(value)

        # Remove newlines and control characters
        value = re.sub(r"[\n\r\t\x00-\x1f]", " ", value)

        # Truncate
        if len(value) > max_length:
            value = value[:max_length] + "..."

        return value

    @staticmethod
    def validate_json_structure(
        data: dict,
        required_fields: List[str],
        max_depth: int = 10,
    ) -> bool:
        """Validate JSON structure.

        Args:
            data: Dictionary to validate
            required_fields: List of required field names
            max_depth: Maximum nesting depth

        Returns:
            True if valid
        """
        if not isinstance(data, dict):
            return False

        # Check required fields
        for field in required_fields:
            if field not in data:
                return False

        # Check depth
        def check_depth(obj: Any, current_depth: int) -> bool:
            if current_depth > max_depth:
                return False

            if isinstance(obj, dict):
                return all(
                    check_depth(v, current_depth + 1)
                    for v in obj.values()
                )
            elif isinstance(obj, list):
                return all(
                    check_depth(item, current_depth + 1)
                    for item in obj
                )
            return True

        return check_depth(data, 0)
