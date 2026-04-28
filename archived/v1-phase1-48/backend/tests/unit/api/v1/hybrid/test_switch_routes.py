# =============================================================================
# IPA Platform - Mode Switch API Unit Tests
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# Unit tests for mode switch API routes:
#   - POST /hybrid/switch - Manual trigger mode switch
#   - GET /hybrid/switch/status/{session_id} - Query switch status
#   - POST /hybrid/switch/rollback - Rollback switch
#   - GET /hybrid/switch/history/{session_id} - Get switch history
#   - GET /hybrid/switch/checkpoints/{session_id} - List checkpoints
#   - DELETE /hybrid/switch/checkpoints/{session_id}/{checkpoint_id} - Delete checkpoint
#   - DELETE /hybrid/switch/history/{session_id} - Clear history
# =============================================================================

import pytest
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.switching import (
    ExecutionState,
    InMemoryCheckpointStorage,
    MigrationStatus,
    ModeTransition,
    ModeSwitcher,
    SwitchCheckpoint,
    SwitchConfig,
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
)
from src.integrations.hybrid.switching.migration.state_migrator import (
    MigratedState,
    MigrationContext,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_switch_trigger() -> SwitchTrigger:
    """Create a mock switch trigger."""
    return SwitchTrigger(
        trigger_type=SwitchTriggerType.MANUAL,
        reason="Manual switch request",
        confidence=1.0,
        source_mode=ExecutionMode.WORKFLOW_MODE,
        target_mode=ExecutionMode.CHAT_MODE,
        detected_at=datetime.utcnow(),
        metadata={"user_id": "test-user"},
    )


@pytest.fixture
def mock_migrated_state() -> MigratedState:
    """Create a mock migrated state."""
    return MigratedState(
        source_mode=ExecutionMode.WORKFLOW_MODE,
        target_mode=ExecutionMode.CHAT_MODE,
        status=MigrationStatus.COMPLETED,
        migrated_at=datetime.utcnow(),
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
        tool_call_records=[
            {"tool": "Bash", "result": "OK"},
        ],
        context_summary="Executed 3 workflow steps",
        warnings=[],
    )


@pytest.fixture
def mock_execution_state_for_checkpoint() -> Dict[str, Any]:
    """Create a mock execution state dict for checkpoint."""
    return {
        "session_id": "sess-123",
        "current_mode": "workflow",
        "step": 3,
        "total": 5,
        "variables": {"key": "value"},
    }


@pytest.fixture
def mock_execution_state() -> ExecutionState:
    """Create a mock execution state."""
    return ExecutionState(
        session_id="sess-123",
        current_mode=ExecutionMode.WORKFLOW_MODE.value,
        consecutive_failures=0,
        has_pending_steps=False,
        step_count=3,
        message_count=2,
        tool_call_count=1,
        resource_usage={"cpu": 0.5, "memory": 0.3},
        metadata={"key": "value"},
    )


@pytest.fixture
def mock_checkpoint(
    mock_execution_state_for_checkpoint: Dict[str, Any],
) -> SwitchCheckpoint:
    """Create a mock checkpoint."""
    return SwitchCheckpoint(
        checkpoint_id="cp-123",
        switch_id="switch-456",
        context_snapshot=mock_execution_state_for_checkpoint,
        mode_before=ExecutionMode.WORKFLOW_MODE.value,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_switch_result(
    mock_switch_trigger: SwitchTrigger,
    mock_migrated_state: MigratedState,
) -> SwitchResult:
    """Create a mock switch result."""
    now = datetime.utcnow()
    return SwitchResult(
        success=True,
        status=SwitchStatus.COMPLETED,
        trigger=mock_switch_trigger,
        new_mode=ExecutionMode.CHAT_MODE.value,
        migrated_state=mock_migrated_state,
        checkpoint_id="cp-123",
        switch_time_ms=150,
        started_at=now,
        completed_at=now,
    )


@pytest.fixture
def mock_mode_transition(
    mock_switch_trigger: SwitchTrigger,
    mock_switch_result: SwitchResult,
) -> ModeTransition:
    """Create a mock mode transition."""
    return ModeTransition(
        transition_id="trans-123",
        session_id="sess-123",
        source_mode=ExecutionMode.WORKFLOW_MODE.value,
        target_mode=ExecutionMode.CHAT_MODE.value,
        trigger=mock_switch_trigger,
        result=mock_switch_result,
        rollback_of=None,
        created_at=datetime.utcnow(),
        metadata={"checkpoint_id": "cp-123"},
    )


# =============================================================================
# Schema Tests
# =============================================================================


class TestSwitchSchemas:
    """Test switch API schemas."""

    def test_switch_request_schema(self) -> None:
        """Test SwitchRequest schema validation."""
        from src.api.v1.hybrid.switch_schemas import SwitchRequest

        request = SwitchRequest(
            session_id="sess-123",
            target_mode="chat",
            reason="Test switch",
            preserve_state=True,
            create_checkpoint=True,
        )

        assert request.session_id == "sess-123"
        assert request.target_mode == "chat"
        assert request.preserve_state is True
        assert request.force is False  # default

    def test_switch_request_invalid_mode(self) -> None:
        """Test SwitchRequest rejects invalid mode."""
        from pydantic import ValidationError
        from src.api.v1.hybrid.switch_schemas import SwitchRequest

        with pytest.raises(ValidationError):
            SwitchRequest(
                session_id="sess-123",
                target_mode="invalid_mode",  # Invalid
            )

    def test_rollback_request_schema(self) -> None:
        """Test RollbackRequest schema validation."""
        from src.api.v1.hybrid.switch_schemas import RollbackRequest

        request = RollbackRequest(
            session_id="sess-123",
            checkpoint_id="cp-456",
            reason="Test rollback",
        )

        assert request.session_id == "sess-123"
        assert request.checkpoint_id == "cp-456"
        assert request.reason == "Test rollback"

    def test_rollback_request_optional_checkpoint(self) -> None:
        """Test RollbackRequest allows optional checkpoint_id."""
        from src.api.v1.hybrid.switch_schemas import RollbackRequest

        request = RollbackRequest(
            session_id="sess-123",
        )

        assert request.session_id == "sess-123"
        assert request.checkpoint_id is None

    def test_switch_result_response_schema(self) -> None:
        """Test SwitchResultResponse schema."""
        from src.api.v1.hybrid.switch_schemas import (
            SwitchResultResponse,
            SwitchTriggerResponse,
        )

        trigger = SwitchTriggerResponse(
            trigger_type="manual",
            reason="Test",
            confidence=1.0,
            source_mode="workflow",
            target_mode="chat",
            detected_at=datetime.utcnow(),
        )

        response = SwitchResultResponse(
            success=True,
            session_id="sess-123",
            source_mode="workflow",
            target_mode="chat",
            status="completed",
            trigger=trigger,
            started_at=datetime.utcnow(),
            can_rollback=True,
        )

        assert response.success is True
        assert response.status == "completed"

    def test_switch_status_response_schema(self) -> None:
        """Test SwitchStatusResponse schema."""
        from src.api.v1.hybrid.switch_schemas import SwitchStatusResponse

        response = SwitchStatusResponse(
            session_id="sess-123",
            current_mode="workflow",
            can_switch=True,
            available_checkpoints=3,
        )

        assert response.session_id == "sess-123"
        assert response.current_mode == "workflow"
        assert response.can_switch is True
        assert response.available_checkpoints == 3


class TestSwitchTriggerResponse:
    """Test SwitchTriggerResponse schema."""

    def test_full_trigger_response(self) -> None:
        """Test full trigger response with all fields."""
        from src.api.v1.hybrid.switch_schemas import SwitchTriggerResponse

        response = SwitchTriggerResponse(
            trigger_type="complexity",
            reason="Task complexity exceeded threshold",
            confidence=0.85,
            source_mode="workflow",
            target_mode="chat",
            detected_at=datetime.utcnow(),
            metadata={"complexity_score": 0.9},
        )

        assert response.trigger_type == "complexity"
        assert response.confidence == 0.85
        assert response.metadata["complexity_score"] == 0.9

    def test_confidence_bounds(self) -> None:
        """Test confidence must be between 0 and 1."""
        from pydantic import ValidationError
        from src.api.v1.hybrid.switch_schemas import SwitchTriggerResponse

        with pytest.raises(ValidationError):
            SwitchTriggerResponse(
                trigger_type="manual",
                reason="Test",
                confidence=1.5,  # Invalid, > 1
                source_mode="workflow",
                target_mode="chat",
                detected_at=datetime.utcnow(),
            )


class TestMigratedStateResponse:
    """Test MigratedStateResponse schema."""

    def test_migrated_state_response(self) -> None:
        """Test migrated state response."""
        from src.api.v1.hybrid.switch_schemas import MigratedStateResponse

        response = MigratedStateResponse(
            source_mode="workflow",
            target_mode="chat",
            status="completed",
            migrated_at=datetime.utcnow(),
            conversation_history_count=5,
            tool_call_count=3,
            context_summary="Migrated 5 messages and 3 tool calls",
            warnings=["Some history was truncated"],
        )

        assert response.conversation_history_count == 5
        assert len(response.warnings) == 1

    def test_partial_status(self) -> None:
        """Test partial migration status."""
        from src.api.v1.hybrid.switch_schemas import MigratedStateResponse

        response = MigratedStateResponse(
            source_mode="chat",
            target_mode="workflow",
            status="partial",
            migrated_at=datetime.utcnow(),
            warnings=["Lost conversation context"],
        )

        assert response.status == "partial"


# =============================================================================
# Route Helper Function Tests
# =============================================================================


class TestRouteHelpers:
    """Test route helper functions."""

    def test_parse_execution_mode_workflow(self) -> None:
        """Test parsing workflow mode."""
        from src.api.v1.hybrid.switch_routes import _parse_execution_mode

        mode = _parse_execution_mode("workflow")
        assert mode == ExecutionMode.WORKFLOW_MODE

    def test_parse_execution_mode_chat(self) -> None:
        """Test parsing chat mode."""
        from src.api.v1.hybrid.switch_routes import _parse_execution_mode

        mode = _parse_execution_mode("chat")
        assert mode == ExecutionMode.CHAT_MODE

    def test_parse_execution_mode_hybrid(self) -> None:
        """Test parsing hybrid mode."""
        from src.api.v1.hybrid.switch_routes import _parse_execution_mode

        mode = _parse_execution_mode("hybrid")
        assert mode == ExecutionMode.HYBRID_MODE

    def test_parse_execution_mode_invalid(self) -> None:
        """Test parsing invalid mode raises error."""
        from src.api.v1.hybrid.switch_routes import _parse_execution_mode

        with pytest.raises(ValueError):
            _parse_execution_mode("invalid")

    def test_mode_to_str(self) -> None:
        """Test mode to string conversion."""
        from src.api.v1.hybrid.switch_routes import _mode_to_str

        assert _mode_to_str(ExecutionMode.WORKFLOW_MODE) == "workflow"
        assert _mode_to_str(ExecutionMode.CHAT_MODE) == "chat"
        assert _mode_to_str(ExecutionMode.HYBRID_MODE) == "hybrid"

    def test_trigger_to_response(
        self, mock_switch_trigger: SwitchTrigger
    ) -> None:
        """Test trigger to response conversion."""
        from src.api.v1.hybrid.switch_routes import _trigger_to_response

        response = _trigger_to_response(mock_switch_trigger)

        assert response.trigger_type == "manual"
        assert response.confidence == 1.0
        assert response.source_mode == "workflow"
        assert response.target_mode == "chat"


class TestSessionModeTracking:
    """Test session mode tracking functions."""

    def test_get_session_mode_default(self) -> None:
        """Test default session mode is workflow."""
        from src.api.v1.hybrid.switch_routes import get_session_mode

        mode = get_session_mode("new-session-xyz")
        assert mode == ExecutionMode.WORKFLOW_MODE

    def test_set_and_get_session_mode(self) -> None:
        """Test setting and getting session mode."""
        from src.api.v1.hybrid.switch_routes import (
            get_session_mode,
            set_session_mode,
        )

        set_session_mode("test-session", ExecutionMode.CHAT_MODE)
        mode = get_session_mode("test-session")
        assert mode == ExecutionMode.CHAT_MODE

    def test_add_and_get_transitions(
        self, mock_mode_transition: ModeTransition
    ) -> None:
        """Test adding and getting transitions."""
        from src.api.v1.hybrid.switch_routes import (
            add_transition,
            get_transitions,
        )

        session_id = "test-trans-session"
        add_transition(session_id, mock_mode_transition)
        transitions = get_transitions(session_id)

        assert len(transitions) == 1
        assert transitions[0].transition_id == mock_mode_transition.transition_id


# =============================================================================
# Route Tests (Unit Level)
# =============================================================================


class TestTriggerSwitchRoute:
    """Test trigger_switch route."""

    @pytest.mark.asyncio
    async def test_trigger_switch_success(
        self,
        mock_switch_result: SwitchResult,
    ) -> None:
        """Test successful mode switch."""
        from src.api.v1.hybrid.switch_routes import (
            trigger_switch,
            set_session_mode,
        )
        from src.api.v1.hybrid.switch_schemas import SwitchRequest

        # Set initial mode
        set_session_mode("sess-test-1", ExecutionMode.WORKFLOW_MODE)

        request = SwitchRequest(
            session_id="sess-test-1",
            target_mode="chat",
            reason="Test switch",
        )

        with patch(
            "src.api.v1.hybrid.switch_routes.get_mode_switcher"
        ) as mock_get_switcher:
            mock_switcher = MagicMock()
            mock_switcher.switch = AsyncMock(return_value=mock_switch_result)
            mock_get_switcher.return_value = mock_switcher

            response = await trigger_switch(request)

            assert response.success is True
            assert response.session_id == "sess-test-1"
            assert response.source_mode == "workflow"
            assert response.target_mode == "chat"

    @pytest.mark.asyncio
    async def test_trigger_switch_same_mode_error(self) -> None:
        """Test switch to same mode raises error."""
        from fastapi import HTTPException
        from src.api.v1.hybrid.switch_routes import (
            trigger_switch,
            set_session_mode,
        )
        from src.api.v1.hybrid.switch_schemas import SwitchRequest

        set_session_mode("sess-test-2", ExecutionMode.CHAT_MODE)

        request = SwitchRequest(
            session_id="sess-test-2",
            target_mode="chat",  # Same as current
        )

        with pytest.raises(HTTPException) as exc_info:
            await trigger_switch(request)

        assert exc_info.value.status_code == 400
        assert "already in chat mode" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_trigger_switch_force_same_mode(
        self,
        mock_switch_result: SwitchResult,
    ) -> None:
        """Test force switch to same mode works."""
        from src.api.v1.hybrid.switch_routes import (
            trigger_switch,
            set_session_mode,
        )
        from src.api.v1.hybrid.switch_schemas import SwitchRequest

        set_session_mode("sess-test-3", ExecutionMode.CHAT_MODE)

        # Adjust mock result for chat to chat
        mock_switch_result.trigger.source_mode = ExecutionMode.CHAT_MODE
        mock_switch_result.trigger.target_mode = ExecutionMode.CHAT_MODE

        request = SwitchRequest(
            session_id="sess-test-3",
            target_mode="chat",
            force=True,  # Force even though same mode
        )

        with patch(
            "src.api.v1.hybrid.switch_routes.get_mode_switcher"
        ) as mock_get_switcher:
            mock_switcher = MagicMock()
            mock_switcher.switch = AsyncMock(return_value=mock_switch_result)
            mock_get_switcher.return_value = mock_switcher

            response = await trigger_switch(request)

            assert response.success is True


class TestGetSwitchStatusRoute:
    """Test get_switch_status route."""

    @pytest.mark.asyncio
    async def test_get_switch_status(self) -> None:
        """Test getting switch status."""
        from src.api.v1.hybrid.switch_routes import (
            get_switch_status,
            set_session_mode,
        )

        set_session_mode("sess-status-1", ExecutionMode.WORKFLOW_MODE)

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.list_checkpoints = AsyncMock(return_value=[])
            mock_get_storage.return_value = mock_storage

            response = await get_switch_status(
                session_id="sess-status-1",
                include_history=True,
                history_limit=10,
            )

            assert response.session_id == "sess-status-1"
            assert response.current_mode == "workflow"
            assert response.can_switch is True

    @pytest.mark.asyncio
    async def test_get_switch_status_with_checkpoints(
        self, mock_checkpoint: SwitchCheckpoint
    ) -> None:
        """Test status includes checkpoint count."""
        from src.api.v1.hybrid.switch_routes import get_switch_status

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.list_checkpoints = AsyncMock(
                return_value=[mock_checkpoint, mock_checkpoint]
            )
            mock_get_storage.return_value = mock_storage

            response = await get_switch_status(
                session_id="sess-status-2",
                include_history=False,
                history_limit=10,
            )

            assert response.available_checkpoints == 2


class TestRollbackSwitchRoute:
    """Test rollback_switch route."""

    @pytest.mark.asyncio
    async def test_rollback_with_checkpoint_id(
        self,
        mock_checkpoint: SwitchCheckpoint,
        mock_switch_result: SwitchResult,
    ) -> None:
        """Test rollback with specific checkpoint ID."""
        from src.api.v1.hybrid.switch_routes import (
            rollback_switch,
            set_session_mode,
        )
        from src.api.v1.hybrid.switch_schemas import RollbackRequest

        set_session_mode("sess-rollback-1", ExecutionMode.CHAT_MODE)

        request = RollbackRequest(
            session_id="sess-rollback-1",
            checkpoint_id="cp-123",
        )

        with patch(
            "src.api.v1.hybrid.switch_routes.get_mode_switcher"
        ) as mock_get_switcher, patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_checkpoint = AsyncMock(return_value=mock_checkpoint)
            mock_get_storage.return_value = mock_storage

            mock_switcher = MagicMock()
            mock_switcher.rollback = AsyncMock(return_value=mock_switch_result)
            mock_get_switcher.return_value = mock_switcher

            response = await rollback_switch(request)

            assert response.success is True
            assert response.checkpoint_id == "cp-123"

    @pytest.mark.asyncio
    async def test_rollback_checkpoint_not_found(self) -> None:
        """Test rollback with non-existent checkpoint."""
        from fastapi import HTTPException
        from src.api.v1.hybrid.switch_routes import rollback_switch
        from src.api.v1.hybrid.switch_schemas import RollbackRequest

        request = RollbackRequest(
            session_id="sess-rollback-2",
            checkpoint_id="non-existent",
        )

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_checkpoint = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            with pytest.raises(HTTPException) as exc_info:
                await rollback_switch(request)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_uses_latest_checkpoint(
        self,
        mock_checkpoint: SwitchCheckpoint,
        mock_switch_result: SwitchResult,
    ) -> None:
        """Test rollback uses latest checkpoint when none specified."""
        from src.api.v1.hybrid.switch_routes import rollback_switch
        from src.api.v1.hybrid.switch_schemas import RollbackRequest

        request = RollbackRequest(
            session_id="sess-rollback-3",
            # No checkpoint_id - use latest
        )

        with patch(
            "src.api.v1.hybrid.switch_routes.get_mode_switcher"
        ) as mock_get_switcher, patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_latest_checkpoint = AsyncMock(
                return_value=mock_checkpoint
            )
            mock_get_storage.return_value = mock_storage

            mock_switcher = MagicMock()
            mock_switcher.rollback = AsyncMock(return_value=mock_switch_result)
            mock_get_switcher.return_value = mock_switcher

            response = await rollback_switch(request)

            assert response.success is True
            mock_storage.get_latest_checkpoint.assert_called_once()


class TestSwitchHistoryRoute:
    """Test get_switch_history route."""

    @pytest.mark.asyncio
    async def test_get_empty_history(self) -> None:
        """Test getting empty switch history."""
        from src.api.v1.hybrid.switch_routes import get_switch_history

        response = await get_switch_history(
            session_id="new-session",
            skip=0,
            limit=20,
        )

        assert response.session_id == "new-session"
        assert len(response.transitions) == 0
        assert response.total == 0

    @pytest.mark.asyncio
    async def test_get_history_with_transitions(
        self, mock_mode_transition: ModeTransition
    ) -> None:
        """Test getting history with transitions."""
        from src.api.v1.hybrid.switch_routes import (
            add_transition,
            get_switch_history,
        )

        session_id = "sess-history-1"
        add_transition(session_id, mock_mode_transition)

        response = await get_switch_history(
            session_id=session_id,
            skip=0,
            limit=20,
        )

        assert len(response.transitions) == 1
        assert response.total == 1


class TestCheckpointsRoute:
    """Test checkpoint listing route."""

    @pytest.mark.asyncio
    async def test_list_checkpoints(
        self, mock_checkpoint: SwitchCheckpoint
    ) -> None:
        """Test listing checkpoints."""
        from src.api.v1.hybrid.switch_routes import list_checkpoints

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.list_checkpoints = AsyncMock(
                return_value=[mock_checkpoint]
            )
            mock_get_storage.return_value = mock_storage

            response = await list_checkpoints(
                session_id="sess-cp-1",
                skip=0,
                limit=10,
            )

            assert response["total"] == 1
            assert len(response["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty(self) -> None:
        """Test listing checkpoints when none exist."""
        from src.api.v1.hybrid.switch_routes import list_checkpoints

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.list_checkpoints = AsyncMock(return_value=[])
            mock_get_storage.return_value = mock_storage

            response = await list_checkpoints(
                session_id="sess-no-cp",
                skip=0,
                limit=10,
            )

            assert response["total"] == 0
            assert len(response["data"]) == 0


class TestDeleteCheckpointRoute:
    """Test delete checkpoint route."""

    @pytest.mark.asyncio
    async def test_delete_checkpoint_success(
        self, mock_checkpoint: SwitchCheckpoint
    ) -> None:
        """Test successful checkpoint deletion."""
        from src.api.v1.hybrid.switch_routes import delete_checkpoint

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_checkpoint = AsyncMock(return_value=mock_checkpoint)
            mock_storage.delete_checkpoint = AsyncMock()
            mock_get_storage.return_value = mock_storage

            # Should not raise
            await delete_checkpoint(
                session_id="sess-123",
                checkpoint_id="cp-123",
            )

            mock_storage.delete_checkpoint.assert_called_once_with("cp-123")

    @pytest.mark.asyncio
    async def test_delete_checkpoint_not_found(self) -> None:
        """Test deleting non-existent checkpoint."""
        from fastapi import HTTPException
        from src.api.v1.hybrid.switch_routes import delete_checkpoint

        with patch(
            "src.api.v1.hybrid.switch_routes.get_checkpoint_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_checkpoint = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            with pytest.raises(HTTPException) as exc_info:
                await delete_checkpoint(
                    session_id="sess-123",
                    checkpoint_id="non-existent",
                )

            assert exc_info.value.status_code == 404


class TestClearHistoryRoute:
    """Test clear switch history route."""

    @pytest.mark.asyncio
    async def test_clear_history(
        self, mock_mode_transition: ModeTransition
    ) -> None:
        """Test clearing switch history."""
        from src.api.v1.hybrid.switch_routes import (
            add_transition,
            clear_switch_history,
            get_switch_history,
        )

        session_id = "sess-clear-history"
        add_transition(session_id, mock_mode_transition)

        # Verify history exists
        history = await get_switch_history(session_id, 0, 10)
        assert history.total == 1

        # Clear history
        await clear_switch_history(session_id)

        # Verify history is cleared
        history = await get_switch_history(session_id, 0, 10)
        assert history.total == 0
