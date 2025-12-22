"""
Unit tests for Code Interpreter API routes.

Sprint 37: Phase 8 - Code Interpreter Integration
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.code_interpreter.routes import router
from src.api.v1.code_interpreter import schemas


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for /code-interpreter/health endpoint."""

    @patch('src.api.v1.code_interpreter.routes.get_settings')
    def test_health_check_configured(self, mock_get_settings):
        """Test health check when Azure OpenAI is configured."""
        mock_settings = MagicMock()
        mock_settings.azure_openai_endpoint = "https://test.openai.azure.com/"
        mock_settings.azure_openai_api_key = "test-key"
        mock_settings.azure_openai_deployment_name = "gpt-4o"
        mock_get_settings.return_value = mock_settings

        response = client.get("/code-interpreter/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["azure_openai_configured"] is True

    @patch('src.api.v1.code_interpreter.routes.get_settings')
    def test_health_check_not_configured(self, mock_get_settings):
        """Test health check when Azure OpenAI is not configured."""
        mock_settings = MagicMock()
        mock_settings.azure_openai_endpoint = None
        mock_settings.azure_openai_api_key = None
        mock_settings.azure_openai_deployment_name = None
        mock_get_settings.return_value = mock_settings

        response = client.get("/code-interpreter/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["azure_openai_configured"] is False


class TestExecuteEndpoint:
    """Tests for /code-interpreter/execute endpoint."""

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_execute_code_success(self, mock_adapter_class):
        """Test successful code execution."""
        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = MagicMock(
            success=True,
            output="42",
            execution_time=1.0,
            files=[],
            error=None,
            metadata={"status": "success", "code_outputs": []},
        )
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/execute",
            json={"code": "print(42)", "timeout": 60}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["output"] == "42"

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_execute_code_with_session(self, mock_adapter_class):
        """Test code execution with existing session."""
        # First create a session
        mock_adapter = MagicMock()
        mock_adapter.execute.return_value = MagicMock(
            success=True,
            output="Hello",
            execution_time=0.5,
            files=[],
            error=None,
            metadata={"status": "success", "code_outputs": []},
        )
        mock_adapter_class.return_value = mock_adapter

        # Create session
        create_response = client.post(
            "/code-interpreter/sessions",
            json={"name": "Test Session"}
        )
        session_id = create_response.json()["session"]["session_id"]

        # Execute with session (mock the session lookup)
        from src.api.v1.code_interpreter import routes
        routes._sessions[session_id] = mock_adapter

        response = client.post(
            "/code-interpreter/execute",
            json={"code": "print('hello')", "session_id": session_id}
        )

        assert response.status_code == 200
        # Cleanup
        routes._sessions.clear()

    def test_execute_code_session_not_found(self):
        """Test code execution with non-existent session."""
        response = client.post(
            "/code-interpreter/execute",
            json={"code": "print(1)", "session_id": "sess_nonexistent"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_execute_code_validation_error(self):
        """Test code execution with invalid input."""
        response = client.post(
            "/code-interpreter/execute",
            json={"code": "", "timeout": 60}  # Empty code
        )

        assert response.status_code == 422  # Validation error


class TestAnalyzeEndpoint:
    """Tests for /code-interpreter/analyze endpoint."""

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_analyze_task_success(self, mock_adapter_class):
        """Test successful task analysis."""
        mock_adapter = MagicMock()
        mock_adapter.analyze_task.return_value = MagicMock(
            success=True,
            output="The factorial of 10 is 3628800",
            execution_time=2.0,
            files=[],
            error=None,
        )
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/analyze",
            json={"task": "Calculate the factorial of 10"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "3628800" in data["output"]

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_analyze_task_with_context(self, mock_adapter_class):
        """Test task analysis with context."""
        mock_adapter = MagicMock()
        mock_adapter.analyze_task.return_value = MagicMock(
            success=True,
            output="Sum is 15",
            execution_time=1.0,
            files=[],
            error=None,
        )
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/analyze",
            json={
                "task": "Calculate the sum",
                "context": {"data": [1, 2, 3, 4, 5]}
            }
        )

        assert response.status_code == 200
        mock_adapter.analyze_task.assert_called_once()


class TestSessionEndpoints:
    """Tests for session management endpoints."""

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_create_session(self, mock_adapter_class):
        """Test creating a new session."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/sessions",
            json={"name": "Data Analysis Session", "timeout": 120}
        )

        assert response.status_code == 201
        data = response.json()
        assert "session" in data
        assert data["session"]["name"] == "Data Analysis Session"
        assert data["session"]["session_id"].startswith("sess_")

        # Cleanup
        from src.api.v1.code_interpreter import routes
        routes._sessions.clear()

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_create_session_default_name(self, mock_adapter_class):
        """Test creating a session with default name."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/sessions",
            json={}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session"]["name"] == "IPA-CodeInterpreter"

        # Cleanup
        from src.api.v1.code_interpreter import routes
        routes._sessions.clear()

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_delete_session(self, mock_adapter_class):
        """Test deleting a session."""
        mock_adapter = MagicMock()
        mock_adapter.cleanup.return_value = True
        mock_adapter_class.return_value = mock_adapter

        # Create session first
        create_response = client.post(
            "/code-interpreter/sessions",
            json={"name": "Temp Session"}
        )
        session_id = create_response.json()["session"]["session_id"]

        # Delete session
        response = client.delete(f"/code-interpreter/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert session_id in data["message"]

    def test_delete_session_not_found(self):
        """Test deleting non-existent session."""
        response = client.delete("/code-interpreter/sessions/sess_nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('src.api.v1.code_interpreter.routes.CodeInterpreterAdapter')
    def test_get_session(self, mock_adapter_class):
        """Test getting session info."""
        mock_adapter = MagicMock()
        mock_adapter.assistant_id = "asst_test123"
        mock_adapter.is_initialized = True
        mock_adapter.config = MagicMock()
        mock_adapter.config.assistant_name = "Test Session"
        mock_adapter_class.return_value = mock_adapter

        # Create session first
        create_response = client.post(
            "/code-interpreter/sessions",
            json={"name": "Test Session"}
        )
        session_id = create_response.json()["session"]["session_id"]

        # Get session
        response = client.get(f"/code-interpreter/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

        # Cleanup
        from src.api.v1.code_interpreter import routes
        routes._sessions.clear()

    def test_get_session_not_found(self):
        """Test getting non-existent session."""
        response = client.get("/code-interpreter/sessions/sess_nonexistent")

        assert response.status_code == 404


class TestSchemas:
    """Tests for request/response schemas."""

    def test_code_execute_request_schema(self):
        """Test CodeExecuteRequest schema validation."""
        # Valid request
        request = schemas.CodeExecuteRequest(
            code="print(1)",
            timeout=60,
        )
        assert request.code == "print(1)"
        assert request.timeout == 60

        # Test timeout bounds
        with pytest.raises(ValueError):
            schemas.CodeExecuteRequest(code="x", timeout=0)  # Below minimum

        with pytest.raises(ValueError):
            schemas.CodeExecuteRequest(code="x", timeout=301)  # Above maximum

    def test_task_analyze_request_schema(self):
        """Test TaskAnalyzeRequest schema validation."""
        request = schemas.TaskAnalyzeRequest(
            task="Calculate factorial",
            context={"n": 10},
        )
        assert request.task == "Calculate factorial"
        assert request.context == {"n": 10}

    def test_session_create_request_schema(self):
        """Test SessionCreateRequest schema validation."""
        request = schemas.SessionCreateRequest(
            name="Custom Session",
            instructions="Be helpful",
            timeout=90,
        )
        assert request.name == "Custom Session"
        assert request.instructions == "Be helpful"
        assert request.timeout == 90

    def test_code_execute_response_schema(self):
        """Test CodeExecuteResponse schema."""
        response = schemas.CodeExecuteResponse(
            success=True,
            output="Hello World",
            execution_time=1.5,
            files=[],
            error=None,
        )
        assert response.success is True
        assert response.output == "Hello World"
        assert response.execution_time == 1.5

    def test_file_output_schema(self):
        """Test FileOutput schema."""
        file_output = schemas.FileOutput(
            type="image",
            file_id="file-123",
            filename="plot.png",
        )
        assert file_output.type == "image"
        assert file_output.file_id == "file-123"
        assert file_output.filename == "plot.png"

    def test_session_info_schema(self):
        """Test SessionInfo schema."""
        from datetime import datetime

        session = schemas.SessionInfo(
            session_id="sess_abc123",
            assistant_id="asst_xyz789",
            name="Test Session",
            created_at=datetime.utcnow(),
            is_active=True,
        )
        assert session.session_id == "sess_abc123"
        assert session.is_active is True
