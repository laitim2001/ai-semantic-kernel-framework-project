# =============================================================================
# IPA Platform - Password Hashing Tests
# =============================================================================
# Sprint 123: S123-2 - Auth Module Tests
# Phase 33: Comprehensive Testing
#
# Unit tests for src.core.security.password module.
# Tests bcrypt hashing and password verification.
#
# Dependencies:
#   - pytest
#   - passlib[bcrypt]
# =============================================================================

import pytest

from src.core.security.password import hash_password, verify_password


# ---------------------------------------------------------------------------
# TestHashPassword
# ---------------------------------------------------------------------------


class TestHashPassword:
    """Tests for hash_password function."""

    def test_returns_bcrypt_hash(self) -> None:
        """Hashed output must start with '$2b$' (bcrypt identifier)."""
        hashed = hash_password("my-secure-password")

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_different_passwords_different_hashes(self) -> None:
        """Two distinct passwords must produce different hashes."""
        hash_a = hash_password("password-alpha")
        hash_b = hash_password("password-beta")

        assert hash_a != hash_b

    def test_same_password_different_salts(self) -> None:
        """Hashing the same password twice must yield different hashes (unique salt)."""
        password = "identical-password"
        hash_first = hash_password(password)
        hash_second = hash_password(password)

        assert hash_first != hash_second


# ---------------------------------------------------------------------------
# TestVerifyPassword
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    """Tests for verify_password function."""

    def test_correct_password_returns_true(self) -> None:
        """Verifying with the original password must return True."""
        password = "correct-horse-battery-staple"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_wrong_password_returns_false(self) -> None:
        """Verifying with a wrong password must return False."""
        hashed = hash_password("real-password")

        assert verify_password("wrong-password", hashed) is False

    def test_empty_password_verification(self) -> None:
        """An empty string is a valid password input; verify against its own hash."""
        hashed = hash_password("")

        assert verify_password("", hashed) is True
        assert verify_password("non-empty", hashed) is False
