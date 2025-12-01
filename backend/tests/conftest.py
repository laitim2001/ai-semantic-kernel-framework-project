"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
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
