"""Unit tests for ServiceNow Client — Sprint 117.

Tests ServiceNow Table API client with mocked HTTP responses.

50 tests covering:
- ServiceNowConfig (10 tests)
- ServiceNowClient.create_incident (5 tests)
- ServiceNowClient.update_incident (4 tests)
- ServiceNowClient.get_incident (5 tests)
- ServiceNowClient.create_ritm (4 tests)
- ServiceNowClient.get_ritm_status (4 tests)
- ServiceNowClient.add_attachment (3 tests)
- ServiceNowClient.add_work_notes (2 tests)
- Error handling (8 tests)
- Retry mechanism (5 tests)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.servicenow_config import (
    AuthMethod,
    ServiceNowConfig,
)
from src.integrations.mcp.servicenow_client import (
    ServiceNowAuthError,
    ServiceNowClient,
    ServiceNowError,
    ServiceNowNotFoundError,
    ServiceNowPermissionError,
    ServiceNowServerError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config() -> ServiceNowConfig:
    """Basic auth configuration for testing."""
    return ServiceNowConfig(
        instance_url="https://test.service-now.com",
        username="admin",
        password="secret123",
        auth_method=AuthMethod.BASIC,
        api_version="v2",
        timeout=10,
        max_retries=2,
        retry_base_delay=0.01,
    )


@pytest.fixture
def oauth_config() -> ServiceNowConfig:
    """OAuth2 configuration for testing."""
    return ServiceNowConfig(
        instance_url="https://test.service-now.com",
        oauth_token="Bearer-Token-12345",
        auth_method=AuthMethod.OAUTH2,
        api_version="v2",
        timeout=10,
        max_retries=1,
    )


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock httpx Response."""

    def create(
        status_code: int = 200,
        json_data: dict = None,
        text: str = "",
        headers: dict = None,
    ) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text or ""
        resp.headers = headers or {}
        resp.json.return_value = json_data or {}
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            import httpx

            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=MagicMock(),
                response=resp,
            )
        return resp

    return create


# =============================================================================
# ServiceNowConfig Tests
# =============================================================================


class TestServiceNowConfig:
    """Tests for ServiceNowConfig dataclass."""

    def test_basic_config_creation(self) -> None:
        """Config with basic auth fields."""
        config = ServiceNowConfig(
            instance_url="https://example.service-now.com",
            username="admin",
            password="pass",
        )
        assert config.instance_url == "https://example.service-now.com"
        assert config.auth_method == AuthMethod.BASIC

    def test_base_url_property(self, config: ServiceNowConfig) -> None:
        """base_url combines instance_url with API version."""
        assert config.base_url == "https://test.service-now.com/api/now/v2"

    def test_base_url_strips_trailing_slash(self) -> None:
        """Trailing slash in instance_url is removed."""
        config = ServiceNowConfig(
            instance_url="https://test.service-now.com/",
        )
        assert config.base_url == "https://test.service-now.com/api/now/v2"

    def test_attachment_url_property(self, config: ServiceNowConfig) -> None:
        """attachment_url points to attachment API."""
        assert config.attachment_url == "https://test.service-now.com/api/now/attachment"

    def test_auth_tuple_basic(self, config: ServiceNowConfig) -> None:
        """Basic auth returns (username, password) tuple."""
        assert config.auth_tuple == ("admin", "secret123")

    def test_auth_tuple_oauth_returns_none(self, oauth_config: ServiceNowConfig) -> None:
        """OAuth config returns None for auth_tuple."""
        assert oauth_config.auth_tuple is None

    def test_auth_headers_oauth(self, oauth_config: ServiceNowConfig) -> None:
        """OAuth config returns Authorization header."""
        assert oauth_config.auth_headers == {
            "Authorization": "Bearer Bearer-Token-12345"
        }

    def test_validate_valid_config(self, config: ServiceNowConfig) -> None:
        """Valid config returns empty error list."""
        errors = config.validate()
        assert errors == []

    def test_validate_missing_url(self) -> None:
        """Missing instance_url produces error."""
        config = ServiceNowConfig(instance_url="")
        errors = config.validate()
        assert any("instance_url" in e for e in errors)

    @patch.dict(
        os.environ,
        {
            "SERVICENOW_INSTANCE_URL": "https://env.service-now.com",
            "SERVICENOW_USERNAME": "env_user",
            "SERVICENOW_PASSWORD": "env_pass",
            "SERVICENOW_API_VERSION": "v1",
            "SERVICENOW_TIMEOUT": "60",
        },
    )
    def test_from_env(self) -> None:
        """from_env reads all environment variables."""
        config = ServiceNowConfig.from_env()
        assert config.instance_url == "https://env.service-now.com"
        assert config.username == "env_user"
        assert config.password == "env_pass"
        assert config.api_version == "v1"
        assert config.timeout == 60


# =============================================================================
# Incident Operations
# =============================================================================


class TestCreateIncident:
    """Tests for ServiceNowClient.create_incident."""

    @pytest.mark.asyncio
    async def test_create_incident_success(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Successful incident creation returns record."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "abc123", "number": "INC0010001"}},
        )

        with patch("httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            mock_http.is_closed = False
            mock_http.request = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_http
            client._client = mock_http

            result = await client.create_incident(
                short_description="Server down",
                description="Web server not responding",
                category="software",
                urgency="1",
            )

        assert result["sys_id"] == "abc123"
        assert result["number"] == "INC0010001"

    @pytest.mark.asyncio
    async def test_create_incident_with_optional_fields(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Incident creation with assignment_group and caller_id."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "abc123", "number": "INC0010002"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.create_incident(
            short_description="Test",
            description="Test desc",
            assignment_group="grp-001",
            caller_id="user-001",
        )

        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["assignment_group"] == "grp-001"
        assert payload["caller_id"] == "user-001"

    @pytest.mark.asyncio
    async def test_create_incident_defaults(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Default category and urgency applied."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {"sys_id": "abc123"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.create_incident(
            short_description="Test",
            description="Test desc",
        )

        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["category"] == "inquiry"
        assert payload["urgency"] == "3"

    @pytest.mark.asyncio
    async def test_create_incident_url(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """POST request targets correct URL."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.create_incident(
            short_description="Test",
            description="Test desc",
        )

        call_args = mock_http.request.call_args
        assert call_args[0][0] == "POST"
        url = call_args.kwargs.get("url") or call_args[0][1]
        assert "/table/incident" in url

    @pytest.mark.asyncio
    async def test_create_incident_auth_error(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """401 raises ServiceNowAuthError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            401,
            {"error": {"message": "Invalid credentials"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowAuthError):
            await client.create_incident(
                short_description="Test",
                description="Test desc",
            )


class TestUpdateIncident:
    """Tests for ServiceNowClient.update_incident."""

    @pytest.mark.asyncio
    async def test_update_incident_success(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Successful update returns updated record."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "abc123", "state": "2"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.update_incident(
            "abc123",
            {"state": "2", "work_notes": "Investigating"},
        )

        assert result["state"] == "2"

    @pytest.mark.asyncio
    async def test_update_incident_uses_patch(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Update uses PATCH method."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.update_incident("abc123", {"state": "2"})

        call_args = mock_http.request.call_args
        assert call_args[0][0] == "PATCH"

    @pytest.mark.asyncio
    async def test_update_incident_url_contains_sys_id(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """PATCH URL includes sys_id."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.update_incident("sys-id-xyz", {"state": "2"})

        call_args = mock_http.request.call_args
        url = call_args.kwargs.get("url") or call_args[0][1]
        assert "sys-id-xyz" in url

    @pytest.mark.asyncio
    async def test_update_incident_not_found(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """404 raises ServiceNowNotFoundError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            404,
            {"error": {"message": "Record not found"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowNotFoundError):
            await client.update_incident("nonexistent", {"state": "2"})


class TestGetIncident:
    """Tests for ServiceNowClient.get_incident."""

    @pytest.mark.asyncio
    async def test_get_incident_by_number(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query by number returns matching record."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": [{"sys_id": "abc123", "number": "INC0010001"}]},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_incident(number="INC0010001")

        assert result is not None
        assert result["number"] == "INC0010001"

    @pytest.mark.asyncio
    async def test_get_incident_by_sys_id(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query by sys_id returns record."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "abc123", "number": "INC0010001"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_incident(sys_id="abc123")

        assert result is not None
        assert result["sys_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_incident_not_found_by_number(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query returns None when no match found."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": []})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_incident(number="INC9999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_incident_not_found_by_sys_id(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query by sys_id returns None on 404."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            404,
            {"error": {"message": "Record not found"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_incident(sys_id="nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_incident_requires_identifier(
        self, config: ServiceNowConfig
    ) -> None:
        """ValueError raised when neither number nor sys_id provided."""
        client = ServiceNowClient(config)
        with pytest.raises(ValueError, match="Either number or sys_id"):
            await client.get_incident()


# =============================================================================
# RITM Operations
# =============================================================================


class TestCreateRITM:
    """Tests for ServiceNowClient.create_ritm."""

    @pytest.mark.asyncio
    async def test_create_ritm_success(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Successful RITM creation."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "ritm-001", "number": "RITM0010001"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.create_ritm(
            cat_item="cat-item-001",
            variables={"target_user": "john.doe"},
            requested_for="user-001",
            short_description="AD Account Creation",
        )

        assert result["number"] == "RITM0010001"

    @pytest.mark.asyncio
    async def test_create_ritm_url(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """POST targets sc_req_item table."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.create_ritm(
            cat_item="cat-001",
            variables={},
            requested_for="user-001",
            short_description="Test",
        )

        call_args = mock_http.request.call_args
        url = call_args.kwargs.get("url") or call_args[0][1]
        assert "/table/sc_req_item" in url

    @pytest.mark.asyncio
    async def test_create_ritm_payload_structure(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """RITM payload includes all required fields."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.create_ritm(
            cat_item="cat-001",
            variables={"key": "val"},
            requested_for="user-001",
            short_description="Test RITM",
        )

        call_args = mock_http.request.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["cat_item"] == "cat-001"
        assert payload["variables"] == {"key": "val"}
        assert payload["requested_for"] == "user-001"
        assert payload["short_description"] == "Test RITM"

    @pytest.mark.asyncio
    async def test_create_ritm_permission_denied(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """403 raises ServiceNowPermissionError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            403,
            {"error": {"message": "Insufficient privileges"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowPermissionError):
            await client.create_ritm(
                cat_item="cat-001",
                variables={},
                requested_for="user-001",
                short_description="Test",
            )


class TestGetRITMStatus:
    """Tests for ServiceNowClient.get_ritm_status."""

    @pytest.mark.asyncio
    async def test_get_ritm_by_number(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query RITM by number."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": [{"sys_id": "ritm-001", "number": "RITM0010001", "stage": "fulfillment"}]},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_ritm_status(number="RITM0010001")
        assert result is not None
        assert result["stage"] == "fulfillment"

    @pytest.mark.asyncio
    async def test_get_ritm_by_sys_id(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Query RITM by sys_id."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "ritm-001", "stage": "approval"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_ritm_status(sys_id="ritm-001")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_ritm_not_found(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Returns None when RITM not found."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": []})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.get_ritm_status(number="RITM9999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_ritm_requires_identifier(
        self, config: ServiceNowConfig
    ) -> None:
        """ValueError when neither number nor sys_id given."""
        client = ServiceNowClient(config)
        with pytest.raises(ValueError, match="Either number or sys_id"):
            await client.get_ritm_status()


# =============================================================================
# Attachment and Work Notes
# =============================================================================


class TestAddAttachment:
    """Tests for ServiceNowClient.add_attachment."""

    @pytest.mark.asyncio
    async def test_add_attachment_success(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Successful attachment upload."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "att-001", "file_name": "log.txt"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="log.txt",
            content=b"Error log content",
            content_type="text/plain",
        )

        assert result["file_name"] == "log.txt"

    @pytest.mark.asyncio
    async def test_add_attachment_url_format(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Attachment URL includes table_name and table_sys_id params."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="report.pdf",
            content=b"pdf content",
            content_type="application/pdf",
        )

        call_args = mock_http.request.call_args
        url = call_args.kwargs.get("url") or call_args[0][1]
        assert "attachment/file" in url
        assert "table_name=incident" in url
        assert "table_sys_id=inc-001" in url

    @pytest.mark.asyncio
    async def test_add_attachment_content_type_header(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Content-Type header matches specified type."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.add_attachment(
            table="incident",
            sys_id="inc-001",
            file_name="image.png",
            content=b"\x89PNG",
            content_type="image/png",
        )

        call_args = mock_http.request.call_args
        headers = call_args.kwargs.get("headers")
        assert headers["Content-Type"] == "image/png"


class TestAddWorkNotes:
    """Tests for ServiceNowClient.add_work_notes."""

    @pytest.mark.asyncio
    async def test_add_work_notes_success(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Successful work notes addition."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            200,
            {"result": {"sys_id": "inc-001", "work_notes": "Investigation started"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        result = await client.add_work_notes(
            table="incident",
            sys_id="inc-001",
            work_notes="Investigation started",
        )

        assert result["work_notes"] == "Investigation started"

    @pytest.mark.asyncio
    async def test_add_work_notes_uses_patch(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Work notes use PATCH method."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(200, {"result": {}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        await client.add_work_notes(
            table="incident",
            sys_id="inc-001",
            work_notes="Test note",
        )

        call_args = mock_http.request.call_args
        assert call_args[0][0] == "PATCH"


# =============================================================================
# Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for comprehensive error handling."""

    @pytest.mark.asyncio
    async def test_auth_error_401(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """401 raises ServiceNowAuthError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(401, {"error": {"message": "Invalid credentials"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowAuthError) as exc_info:
            await client.create_incident("Test", "Test")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_permission_error_403(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """403 raises ServiceNowPermissionError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(403, {"error": {"message": "Forbidden"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowPermissionError) as exc_info:
            await client.update_incident("abc", {"state": "2"})
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found_error_404(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """404 raises ServiceNowNotFoundError."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(404, {"error": {"message": "Not found"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowNotFoundError) as exc_info:
            await client.update_incident("nonexistent", {"state": "2"})
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_server_error_500(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """500 raises ServiceNowServerError after retries."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(500, {"error": {"message": "Internal error"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowServerError) as exc_info:
            await client.create_incident("Test", "Test")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_error_detail_preserved(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Error detail message is preserved in exception."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(
            401,
            {"error": {"message": "User account locked"}},
        )

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowAuthError) as exc_info:
            await client.create_incident("Test", "Test")
        assert "User account locked" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error(self, config: ServiceNowConfig) -> None:
        """Connection errors raise ServiceNowError after retries."""
        import httpx

        client = ServiceNowClient(config)

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        client._client = mock_http

        with pytest.raises(ServiceNowError, match="Connection failed"):
            await client.create_incident("Test", "Test")

    @pytest.mark.asyncio
    async def test_timeout_error(self, config: ServiceNowConfig) -> None:
        """Timeout errors raise ServiceNowError after retries."""
        import httpx

        client = ServiceNowClient(config)

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        client._client = mock_http

        with pytest.raises(ServiceNowError, match="timed out"):
            await client.create_incident("Test", "Test")

    @pytest.mark.asyncio
    async def test_error_without_json_body(
        self, config: ServiceNowConfig
    ) -> None:
        """Non-JSON error response handled gracefully."""
        client = ServiceNowClient(config)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_resp.json.side_effect = Exception("Not JSON")
        mock_resp.headers = {}

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowAuthError):
            await client.create_incident("Test", "Test")


# =============================================================================
# Retry Mechanism
# =============================================================================


class TestRetryMechanism:
    """Tests for exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_server_error(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Retries on 500 server errors."""
        client = ServiceNowClient(config)

        fail_resp = mock_response(500, {"error": {"message": "Server error"}})
        success_resp = mock_response(200, {"result": {"sys_id": "abc123"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            side_effect=[fail_resp, success_resp]
        )
        client._client = mock_http

        result = await client.create_incident("Test", "Test")
        assert result["sys_id"] == "abc123"
        assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """No retry on 401 authentication errors."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(401, {"error": {"message": "Unauthorized"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowAuthError):
            await client.create_incident("Test", "Test")
        assert mock_http.request.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_permission_error(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """No retry on 403 permission errors."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(403, {"error": {"message": "Forbidden"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowPermissionError):
            await client.update_incident("abc", {"state": "2"})
        assert mock_http.request.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_not_found(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """No retry on 404 not found errors."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(404, {"error": {"message": "Not found"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowNotFoundError):
            await client.update_incident("nonexist", {"state": "2"})
        assert mock_http.request.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(
        self, config: ServiceNowConfig, mock_response
    ) -> None:
        """Raises after max retries exhausted."""
        client = ServiceNowClient(config)
        mock_resp = mock_response(500, {"error": {"message": "Server error"}})

        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=mock_resp)
        client._client = mock_http

        with pytest.raises(ServiceNowServerError):
            await client.create_incident("Test", "Test")
        # max_retries=2, so 3 total attempts (initial + 2 retries)
        assert mock_http.request.call_count == 3
