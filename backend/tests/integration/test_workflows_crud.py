"""
Integration tests for Workflows CRUD API
Tests all 5 endpoints with authentication
"""
import pytest
import asyncio
from httpx import AsyncClient
from uuid import UUID

from main import app
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.workflow import Workflow
from src.infrastructure.auth.jwt_manager import JWTManager
from src.infrastructure.auth.password import PasswordManager


# Test fixtures

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_user():
    """Create a test user for authentication"""
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create test user
            password_manager = PasswordManager()
            hashed_password = password_manager.hash_password("testpass123")

            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password=hashed_password,
                full_name="Test User",
                is_active=True
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)

        yield user


@pytest.fixture(scope="module")
async def auth_token(test_user):
    """Get authentication token for test user"""
    jwt_manager = JWTManager()
    access_token = jwt_manager.create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )
    return access_token


@pytest.fixture
async def client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def cleanup_workflows():
    """Clean up test workflows after each test"""
    yield
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        await session.execute(delete(Workflow).where(Workflow.name.like("Test Workflow%")))
        await session.commit()


# Tests

@pytest.mark.asyncio
class TestWorkflowsCRUD:
    """Test Workflows CRUD operations"""

    async def test_01_create_workflow_success(self, client, auth_token):
        """Test creating a new workflow"""
        response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow 1",
                "description": "Test workflow description",
                "trigger_type": "manual",
                "trigger_config": {},
                "status": "draft",
                "tags": ["test", "crud"]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Test Workflow 1"
        assert data["description"] == "Test workflow description"
        assert data["status"] == "draft"
        assert "test" in data["tags"]
        assert "id" in data
        assert UUID(data["id"])  # Valid UUID

    async def test_02_create_workflow_duplicate_name(self, client, auth_token):
        """Test creating workflow with duplicate name"""
        # Create first workflow
        await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Duplicate",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Duplicate",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_03_create_workflow_invalid_trigger_config(self, client, auth_token):
        """Test creating workflow with invalid trigger config"""
        response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Invalid",
                "trigger_type": "scheduled",
                "trigger_config": {}  # Missing cron_expression
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422
        assert "cron_expression" in str(response.json())

    async def test_04_list_workflows(self, client, auth_token):
        """Test listing workflows with pagination"""
        # Create multiple workflows
        for i in range(5):
            await client.post(
                "/api/v1/workflows/",
                json={
                    "name": f"Test Workflow List {i}",
                    "trigger_type": "manual",
                    "trigger_config": {},
                    "tags": ["list", "test"]
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )

        # List workflows
        response = await client.get(
            "/api/v1/workflows/?page=1&page_size=3",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        assert data["page"] == 1
        assert data["page_size"] == 3
        assert len(data["items"]) <= 3

    async def test_05_list_workflows_with_filters(self, client, auth_token):
        """Test listing workflows with filters"""
        # Create workflow with specific status and tags
        await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Active",
                "trigger_type": "webhook",
                "trigger_config": {"webhook_secret": "test"},
                "status": "active",
                "tags": ["production", "active"]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Filter by status
        response = await client.get(
            "/api/v1/workflows/?status=active",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "active" for item in data["items"])

        # Filter by trigger type
        response = await client.get(
            "/api/v1/workflows/?trigger_type=webhook",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        # Note: trigger_type is in metadata, so we can't verify from response

        # Search by name
        response = await client.get(
            "/api/v1/workflows/?search=Active",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert any("Active" in item["name"] for item in data["items"])

    async def test_06_get_workflow_by_id(self, client, auth_token):
        """Test getting workflow by ID"""
        # Create workflow
        create_response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Get",
                "description": "Get by ID test",
                "trigger_type": "event",
                "trigger_config": {"event_type": "customer.created"}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        workflow_id = create_response.json()["id"]

        # Get workflow
        response = await client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == workflow_id
        assert data["name"] == "Test Workflow Get"
        assert data["description"] == "Get by ID test"

    async def test_07_get_workflow_not_found(self, client, auth_token):
        """Test getting non-existent workflow"""
        fake_uuid = "123e4567-e89b-12d3-a456-426614174000"

        response = await client.get(
            f"/api/v1/workflows/{fake_uuid}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_08_update_workflow(self, client, auth_token):
        """Test updating workflow"""
        # Create workflow
        create_response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Update",
                "status": "draft",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        workflow_id = create_response.json()["id"]

        # Update workflow
        response = await client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "name": "Test Workflow Updated",
                "description": "Updated description",
                "status": "active",
                "tags": ["updated"]
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Test Workflow Updated"
        assert data["description"] == "Updated description"
        assert data["status"] == "active"
        assert "updated" in data["tags"]

    async def test_09_update_workflow_duplicate_name(self, client, auth_token):
        """Test updating workflow to duplicate name"""
        # Create two workflows
        await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Original",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        create_response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow ToUpdate",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        workflow_id = create_response.json()["id"]

        # Try to update to duplicate name
        response = await client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"name": "Test Workflow Original"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_10_delete_workflow(self, client, auth_token):
        """Test deleting workflow"""
        # Create workflow
        create_response = await client.post(
            "/api/v1/workflows/",
            json={
                "name": "Test Workflow Delete",
                "trigger_type": "manual",
                "trigger_config": {}
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        workflow_id = create_response.json()["id"]

        # Delete workflow
        response = await client.delete(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert get_response.status_code == 404

    async def test_11_delete_workflow_not_found(self, client, auth_token):
        """Test deleting non-existent workflow"""
        fake_uuid = "123e4567-e89b-12d3-a456-426614174000"

        response = await client.delete(
            f"/api/v1/workflows/{fake_uuid}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404

    async def test_12_unauthorized_access(self, client):
        """Test accessing endpoints without authentication"""
        # Create without auth
        response = await client.post(
            "/api/v1/workflows/",
            json={"name": "Test", "trigger_type": "manual", "trigger_config": {}}
        )
        assert response.status_code == 401

        # List without auth
        response = await client.get("/api/v1/workflows/")
        assert response.status_code == 401

        # Get without auth
        response = await client.get("/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 401
