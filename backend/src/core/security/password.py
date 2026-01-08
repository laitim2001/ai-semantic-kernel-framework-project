# =============================================================================
# IPA Platform - Password Hashing
# =============================================================================
# Sprint 70: S70-1 - JWT Utilities
# Phase 18: Authentication System
#
# Secure password hashing using bcrypt.
# Passlib provides a secure, well-tested implementation.
#
# Dependencies:
#   - passlib[bcrypt]
# =============================================================================

from passlib.context import CryptContext

# Configure password hashing context
# - bcrypt: Industry-standard password hashing algorithm
# - deprecated="auto": Automatically upgrade old hashes
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password string

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> # Returns: "$2b$12$..."
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password to check against

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)  # True
        >>> verify_password("wrongpassword", hashed)  # False
    """
    return pwd_context.verify(plain_password, hashed_password)
