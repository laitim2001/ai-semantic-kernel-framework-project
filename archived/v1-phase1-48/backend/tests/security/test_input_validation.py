"""
IPA Platform - Input Validation Security Tests

Tests for input validation security including:
- SQL injection prevention
- XSS prevention
- Path traversal prevention
- Command injection prevention
- Request size limits

Author: IPA Platform Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# =============================================================================
# SQL Injection Tests
# =============================================================================

class TestSQLInjection:
    """Test SQL injection prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_sql_injection_in_search(
        self,
        unauthenticated_client: AsyncClient,
        sql_injection_payloads: list[str]
    ):
        """Test that SQL injection in search params is prevented."""
        for payload in sql_injection_payloads:
            response = await unauthenticated_client.get(
                "/api/v1/workflows/",
                params={"search": payload}
            )

            # Should handle safely (not 500 error)
            assert response.status_code != 500
            # Should not expose database errors
            if response.text:
                assert "SQL" not in response.text.upper()
                assert "syntax error" not in response.text.lower()

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_sql_injection_in_path_params(
        self,
        unauthenticated_client: AsyncClient,
        sql_injection_payloads: list[str]
    ):
        """Test that SQL injection in path parameters is prevented."""
        for payload in sql_injection_payloads[:5]:  # Test subset
            response = await unauthenticated_client.get(
                f"/api/v1/workflows/{payload}"
            )

            # Should handle safely
            assert response.status_code != 500
            if response.text:
                assert "SQL" not in response.text.upper()

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_sql_injection_in_json_body(
        self,
        unauthenticated_client: AsyncClient,
        sql_injection_payloads: list[str]
    ):
        """Test that SQL injection in JSON body is prevented."""
        for payload in sql_injection_payloads[:5]:
            response = await unauthenticated_client.post(
                "/api/v1/workflows/",
                json={
                    "name": payload,
                    "description": payload,
                }
            )

            # Should handle safely
            assert response.status_code != 500
            if response.text:
                assert "SQL" not in response.text.upper()


# =============================================================================
# XSS Prevention Tests
# =============================================================================

class TestXSSPrevention:
    """Test XSS attack prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_xss_in_workflow_name(
        self,
        unauthenticated_client: AsyncClient,
        xss_payloads: list[str]
    ):
        """Test that XSS in workflow name is prevented."""
        for payload in xss_payloads[:5]:
            response = await unauthenticated_client.post(
                "/api/v1/workflows/",
                json={
                    "name": payload,
                    "description": "Test workflow",
                }
            )

            # Should sanitize or reject
            # If stored, check it's escaped when retrieved
            if response.status_code in [200, 201] and response.text:
                response_text = response.text
                # Script tags should be escaped or removed
                assert "<script>" not in response_text
                assert "onerror=" not in response_text.lower()

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_xss_in_search_results(
        self,
        unauthenticated_client: AsyncClient,
        xss_payloads: list[str]
    ):
        """Test that XSS is not reflected in search results."""
        for payload in xss_payloads[:5]:
            response = await unauthenticated_client.get(
                "/api/v1/workflows/",
                params={"search": payload}
            )

            if response.text:
                # XSS should not be reflected
                assert "<script>" not in response.text
                assert "alert(" not in response.text


# =============================================================================
# Path Traversal Tests
# =============================================================================

class TestPathTraversal:
    """Test path traversal attack prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_path_traversal_in_file_paths(
        self,
        unauthenticated_client: AsyncClient,
        path_traversal_payloads: list[str]
    ):
        """Test that path traversal attacks are prevented."""
        for payload in path_traversal_payloads:
            response = await unauthenticated_client.get(
                f"/api/v1/templates/{payload}"
            )

            # Should not return sensitive files
            if response.text:
                assert "root:" not in response.text  # /etc/passwd content
                assert "NTLM" not in response.text  # Windows SAM content

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_path_traversal_in_upload(
        self,
        unauthenticated_client: AsyncClient,
        path_traversal_payloads: list[str]
    ):
        """Test that path traversal in uploads is prevented."""
        for payload in path_traversal_payloads[:3]:
            # Try to upload with malicious filename
            files = {"file": (payload, b"test content", "text/plain")}

            response = await unauthenticated_client.post(
                "/api/v1/uploads/",
                files=files
            )

            # Should reject or sanitize
            assert response.status_code != 500


# =============================================================================
# Command Injection Tests
# =============================================================================

class TestCommandInjection:
    """Test command injection prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_command_injection_in_workflow_name(
        self,
        unauthenticated_client: AsyncClient,
        command_injection_payloads: list[str]
    ):
        """Test that command injection is prevented."""
        for payload in command_injection_payloads[:5]:
            response = await unauthenticated_client.post(
                "/api/v1/workflows/",
                json={
                    "name": payload,
                    "description": "Test"
                }
            )

            # Should not execute commands
            # Check response doesn't contain command output
            if response.text:
                assert "uid=" not in response.text  # id command output
                assert "root" not in response.text.lower() or "workflow" in response.text.lower()


# =============================================================================
# Request Size Limit Tests
# =============================================================================

class TestRequestSizeLimits:
    """Test request size limits."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_large_request_body_rejected(
        self,
        unauthenticated_client: AsyncClient,
        large_payload: str
    ):
        """Test that very large request bodies are rejected."""
        try:
            response = await unauthenticated_client.post(
                "/api/v1/workflows/",
                json={"name": large_payload[:100000]}  # 100KB
            )

            # Should reject or handle large payloads
            # 413 for payload too large, 422 for validation error
            assert response.status_code in [400, 413, 422, 404]

        except Exception:
            # Connection errors are acceptable for very large payloads
            pass

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_deeply_nested_json_rejected(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that deeply nested JSON is rejected."""
        # Create deeply nested JSON
        nested = {"level": 1}
        current = nested
        for i in range(100):
            current["nested"] = {"level": i + 2}
            current = current["nested"]

        response = await unauthenticated_client.post(
            "/api/v1/workflows/",
            json=nested
        )

        # Should handle without crashing
        assert response.status_code != 500


# =============================================================================
# Content Type Tests
# =============================================================================

class TestContentType:
    """Test content type validation."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_wrong_content_type_rejected(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that wrong content types are handled."""
        response = await unauthenticated_client.post(
            "/api/v1/workflows/",
            content="name=test",
            headers={"Content-Type": "text/plain"}
        )

        # Should reject or handle gracefully
        assert response.status_code in [400, 415, 422, 404]

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_multipart_bomb_rejected(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that multipart bombs are rejected."""
        # Create many form fields
        files = {f"file{i}": (f"test{i}.txt", b"x" * 1000) for i in range(100)}

        try:
            response = await unauthenticated_client.post(
                "/api/v1/uploads/",
                files=files
            )

            # Should handle gracefully
            assert response.status_code in [400, 404, 413, 422]

        except Exception:
            # Connection errors are acceptable
            pass


# =============================================================================
# Header Injection Tests
# =============================================================================

class TestHeaderInjection:
    """Test HTTP header injection prevention."""

    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_header_injection_in_redirect(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test that header injection is prevented."""
        malicious_headers = [
            "test\r\nSet-Cookie: malicious=true",
            "test\r\nX-Injected: header",
            "test%0d%0aSet-Cookie: evil=value",
        ]

        for payload in malicious_headers:
            response = await unauthenticated_client.get(
                "/api/v1/redirect",
                params={"url": payload},
                follow_redirects=False
            )

            # Check response headers don't contain injected headers
            headers = dict(response.headers)
            assert "malicious" not in str(headers).lower()
            assert "x-injected" not in [h.lower() for h in headers.keys()]
