"""
E2E Test Fixtures for Orchestration — Sprint 118.

Provides shared fixtures for AD scenario E2E tests:
- Mock LDAP MCP server (success and failure modes)
- Mock ServiceNow MCP server (success and failure modes)
- Webhook authentication fixtures
- FastAPI async test client with singleton overrides
- RITM Intent Mapper with real mappings

These fixtures allow testing the complete AD scenario flow
(Webhook → Mapper → PatternMatcher → Agent → MCP → Close)
without requiring live LDAP or ServiceNow instances.
"""

import os
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# =============================================================================
# Import Application and Components
# =============================================================================

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from main import app
from src.core.auth import require_auth
from src.integrations.orchestration.input.ritm_intent_mapper import (
    IntentMappingResult,
    RITMIntentMapper,
)
from src.integrations.orchestration.input.servicenow_webhook import (
    ServiceNowRITMEvent,
    ServiceNowWebhookReceiver,
    WebhookAuthConfig,
    WebhookValidationError,
)


# =============================================================================
# JWT Auth Override — Bypass protected_router auth for E2E tests
# =============================================================================


async def _mock_require_auth() -> dict:
    """Bypass JWT auth for E2E testing."""
    return {"user_id": "test-user-118", "role": "admin"}


@pytest.fixture(autouse=True)
def override_jwt_auth():
    """Override JWT auth dependency globally for all E2E orchestration tests.

    The webhook endpoints are registered under protected_router which
    requires a valid JWT. This fixture replaces the auth dependency with
    a no-op mock so webhook tests can exercise the ServiceNow-specific
    authentication (X-ServiceNow-Secret header) without needing a JWT.
    """
    app.dependency_overrides[require_auth] = _mock_require_auth
    yield
    app.dependency_overrides.pop(require_auth, None)


# =============================================================================
# Constants
# =============================================================================

WEBHOOK_SECRET = "test-webhook-secret-118"
WEBHOOK_URL = "/api/v1/orchestration/webhooks/servicenow"
HEALTH_URL = "/api/v1/orchestration/webhooks/servicenow/health"


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for orchestration E2E tests.

    Uses ASGI transport for in-process requests without network overhead.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
    ) as ac:
        yield ac


# =============================================================================
# Webhook Auth Fixtures
# =============================================================================


@pytest.fixture
def webhook_auth_config() -> WebhookAuthConfig:
    """Webhook authentication config for tests."""
    return WebhookAuthConfig(
        auth_type="shared_secret",
        shared_secret=WEBHOOK_SECRET,
        allowed_ips=[],  # No IP restriction in tests
        enabled=True,
    )


@pytest.fixture
def webhook_receiver(webhook_auth_config: WebhookAuthConfig) -> ServiceNowWebhookReceiver:
    """Fresh webhook receiver for each test (empty processed cache)."""
    return ServiceNowWebhookReceiver(webhook_auth_config)


@pytest.fixture
def webhook_headers() -> Dict[str, str]:
    """Standard webhook authentication headers."""
    return {
        "X-ServiceNow-Secret": WEBHOOK_SECRET,
        "Content-Type": "application/json",
    }


@pytest.fixture
def webhook_headers_invalid() -> Dict[str, str]:
    """Invalid webhook authentication headers."""
    return {
        "X-ServiceNow-Secret": "wrong-secret",
        "Content-Type": "application/json",
    }


# =============================================================================
# RITM Intent Mapper Fixture
# =============================================================================


@pytest.fixture
def intent_mapper() -> RITMIntentMapper:
    """RITM mapper loaded with real production mappings."""
    return RITMIntentMapper()


# =============================================================================
# LDAP MCP Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_ldap() -> AsyncMock:
    """Mock LDAP MCP server with successful operation responses.

    Mocks the following LDAP operations:
    - search_users: Returns user info
    - get_user_info: Returns detailed user attributes
    - modify_user_attributes: Returns success (unlock, password reset, group change)
    - get_group_members: Returns group member list
    """
    ldap_mock = AsyncMock()

    # search_users
    ldap_mock.search_users.return_value = {
        "success": True,
        "content": [
            {
                "dn": "CN=john.doe,OU=Users,DC=company,DC=com",
                "sAMAccountName": "john.doe",
                "displayName": "John Doe",
                "mail": "john.doe@company.com",
                "department": "Engineering",
                "lockoutTime": "132800000000000000",
            }
        ],
        "metadata": {"result_count": 1},
    }

    # get_user_info
    ldap_mock.get_user_info.return_value = {
        "success": True,
        "content": {
            "dn": "CN=john.doe,OU=Users,DC=company,DC=com",
            "sAMAccountName": "john.doe",
            "displayName": "John Doe",
            "mail": "john.doe@company.com",
            "department": "Engineering",
            "memberOf": ["CN=dev-team,OU=Groups,DC=company,DC=com"],
            "lockoutTime": "0",
            "pwdLastSet": "132800000000000000",
        },
        "metadata": {"tool": "get_user_info"},
    }

    # modify_user_attributes (generic success)
    ldap_mock.modify_user_attributes.return_value = {
        "success": True,
        "content": {"modified": True, "changes_applied": 1},
        "metadata": {"tool": "modify_user_attributes"},
    }

    # get_group_members
    ldap_mock.get_group_members.return_value = {
        "success": True,
        "content": [
            {"sAMAccountName": "alice.wang", "displayName": "Alice Wang"},
            {"sAMAccountName": "bob.chen", "displayName": "Bob Chen"},
        ],
        "metadata": {"result_count": 2},
    }

    return ldap_mock


@pytest.fixture
def mock_ldap_fail() -> AsyncMock:
    """Mock LDAP MCP server that fails all operations.

    Simulates LDAP server connectivity issues or permission denied.
    """
    ldap_mock = AsyncMock()

    error_response = {
        "success": False,
        "error": "LDAP connection failed: server unreachable",
        "metadata": {
            "error_type": "LDAPConnectionError",
            "retry_attempted": True,
        },
    }

    ldap_mock.search_users.return_value = error_response
    ldap_mock.get_user_info.return_value = error_response
    ldap_mock.modify_user_attributes.return_value = error_response
    ldap_mock.get_group_members.return_value = error_response

    return ldap_mock


# =============================================================================
# ServiceNow MCP Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_servicenow() -> AsyncMock:
    """Mock ServiceNow MCP server with successful operation responses.

    Mocks RITM status update and closure operations.
    """
    sn_mock = AsyncMock()

    # get_ritm_status
    sn_mock.get_ritm_status.return_value = {
        "success": True,
        "content": {
            "sys_id": "ritm-unlock-001",
            "number": "RITM0012345",
            "stage": "fulfillment",
            "state": "2",
            "approval": "approved",
        },
        "metadata": {"tool": "get_ritm_status"},
    }

    # update_incident (used for RITM work notes)
    sn_mock.update_incident.return_value = {
        "success": True,
        "content": {
            "sys_id": "ritm-unlock-001",
            "state": "3",
            "work_notes": "AD operation completed successfully",
        },
        "metadata": {"tool": "update_incident", "updated_fields": ["state", "work_notes"]},
    }

    # create_incident (for error reporting)
    sn_mock.create_incident.return_value = {
        "success": True,
        "content": {
            "sys_id": "inc-error-001",
            "number": "INC0099001",
            "short_description": "AD operation error",
            "state": "1",
        },
        "metadata": {"tool": "create_incident"},
    }

    return sn_mock


@pytest.fixture
def mock_sn_fail() -> AsyncMock:
    """Mock ServiceNow MCP server that fails all operations.

    Simulates ServiceNow API downtime or authentication failure.
    """
    sn_mock = AsyncMock()

    error_response = {
        "success": False,
        "error": "ServiceNow API unavailable: Connection timeout",
        "metadata": {
            "error_type": "ServiceNowError",
            "status_code": 503,
        },
    }

    sn_mock.get_ritm_status.return_value = error_response
    sn_mock.update_incident.return_value = error_response
    sn_mock.create_incident.return_value = error_response

    return sn_mock


# =============================================================================
# Webhook Receiver Override Fixtures
# =============================================================================


@pytest.fixture
def override_webhook_receiver(
    webhook_receiver: ServiceNowWebhookReceiver,
) -> ServiceNowWebhookReceiver:
    """Override the global webhook receiver singleton for testing.

    Patches the module-level singleton in webhook_routes to use
    our test-configured receiver.
    """
    import src.api.v1.orchestration.webhook_routes as webhook_module

    original = webhook_module._webhook_receiver
    webhook_module._webhook_receiver = webhook_receiver

    yield webhook_receiver

    # Restore original
    webhook_module._webhook_receiver = original


@pytest.fixture
def override_intent_mapper(
    intent_mapper: RITMIntentMapper,
) -> RITMIntentMapper:
    """Override the global intent mapper singleton for testing."""
    import src.api.v1.orchestration.webhook_routes as webhook_module

    original = webhook_module._intent_mapper
    webhook_module._intent_mapper = intent_mapper

    yield intent_mapper

    webhook_module._intent_mapper = original


# =============================================================================
# Composite Fixtures
# =============================================================================


@pytest.fixture
def ad_scenario_setup(
    override_webhook_receiver,
    override_intent_mapper,
    mock_ldap,
    mock_servicenow,
):
    """Composite fixture that sets up all components for AD E2E testing.

    Returns a dict with all mocks for assertion access.
    """
    return {
        "webhook_receiver": override_webhook_receiver,
        "intent_mapper": override_intent_mapper,
        "ldap": mock_ldap,
        "servicenow": mock_servicenow,
    }
