"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""
import pytest


# =============================================================================
# Pytest Markers Configuration (Phase 7)
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end tests (may require real API)")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line("markers", "integration: Integration tests")


@pytest.fixture
def client():
    """Create a test client for the FastAPI application.

    Uses lazy import to avoid initialization issues during test collection.
    """
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
def api_prefix() -> str:
    """API version prefix."""
    return "/api/v1"


# =============================================================================
# Database Fixtures (Sprint 1)
# =============================================================================

# @pytest.fixture
# async def db_session():
#     """Create a database session for testing."""
#     # TODO: Implement database session fixture
#     pass


# @pytest.fixture
# def sample_user():
#     """Create a sample user for testing."""
#     return {
#         "email": "test@example.com",
#         "name": "Test User",
#         "role": "user",
#     }


# =============================================================================
# Agent Framework Fixtures (Sprint 1)
# =============================================================================

# @pytest.fixture
# def mock_agent_executor():
#     """Create a mock agent executor for testing."""
#     pass


# @pytest.fixture
# def mock_workflow():
#     """Create a mock workflow for testing."""
#     pass


# =============================================================================
# Redis Fixtures (Sprint 2)
# =============================================================================

# @pytest.fixture
# async def redis_client():
#     """Create a Redis client for testing."""
#     pass
