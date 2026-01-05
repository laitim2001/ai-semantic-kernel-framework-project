# =============================================================================
# IPA Platform - Human-in-the-Loop Handler Tests
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-3: Human-in-the-Loop Tests
#
# Unit tests for HITLHandler, ApprovalStorage, and related components.
#
# Test Coverage:
#   - ApprovalStatus enum
#   - ToolCallInfo dataclass
#   - ApprovalRequest dataclass
#   - ApprovalStorage class
#   - HITLHandler class
#   - Factory functions
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.ag_ui.features.human_in_loop import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStorage,
    DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    HITLHandler,
    ToolCallInfo,
    create_hitl_handler,
    get_approval_storage,
    get_hitl_handler,
)
from src.integrations.ag_ui.events import AGUIEventType, CustomEvent
from src.integrations.hybrid.risk import RiskLevel


# =============================================================================
# ApprovalStatus Tests
# =============================================================================


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_pending_value(self):
        """Test PENDING status has correct value."""
        assert ApprovalStatus.PENDING.value == "pending"

    def test_approved_value(self):
        """Test APPROVED status has correct value."""
        assert ApprovalStatus.APPROVED.value == "approved"

    def test_rejected_value(self):
        """Test REJECTED status has correct value."""
        assert ApprovalStatus.REJECTED.value == "rejected"

    def test_timeout_value(self):
        """Test TIMEOUT status has correct value."""
        assert ApprovalStatus.TIMEOUT.value == "timeout"

    def test_cancelled_value(self):
        """Test CANCELLED status has correct value."""
        assert ApprovalStatus.CANCELLED.value == "cancelled"

    def test_status_is_string_enum(self):
        """Test ApprovalStatus is a string enum."""
        assert isinstance(ApprovalStatus.PENDING, str)
        assert ApprovalStatus.PENDING == "pending"


# =============================================================================
# ToolCallInfo Tests
# =============================================================================


class TestToolCallInfo:
    """Tests for ToolCallInfo dataclass."""

    def test_create_with_required_fields(self):
        """Test creating ToolCallInfo with required fields."""
        info = ToolCallInfo(id="tc-123", name="Bash")

        assert info.id == "tc-123"
        assert info.name == "Bash"
        assert info.arguments == {}

    def test_create_with_all_fields(self):
        """Test creating ToolCallInfo with all fields."""
        args = {"command": "ls -la"}
        info = ToolCallInfo(id="tc-456", name="Bash", arguments=args)

        assert info.id == "tc-456"
        assert info.name == "Bash"
        assert info.arguments == args

    def test_arguments_default_factory(self):
        """Test that arguments uses a default factory."""
        info1 = ToolCallInfo(id="tc-1", name="Tool1")
        info2 = ToolCallInfo(id="tc-2", name="Tool2")

        info1.arguments["key"] = "value"
        assert "key" not in info2.arguments


# =============================================================================
# ApprovalRequest Tests
# =============================================================================


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_create_with_required_fields(self):
        """Test creating ApprovalRequest with required fields."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={"command": "rm -rf /tmp"},
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            reasoning="High-risk shell command",
            run_id="run-789",
        )

        assert request.approval_id == "approval-123"
        assert request.tool_call_id == "tc-456"
        assert request.tool_name == "Bash"
        assert request.risk_level == RiskLevel.HIGH
        assert request.risk_score == 0.85
        assert request.status == ApprovalStatus.PENDING
        assert request.session_id is None
        assert request.resolved_at is None

    def test_create_with_all_fields(self):
        """Test creating ApprovalRequest with all fields."""
        created = datetime.utcnow()
        expires = created + timedelta(seconds=300)
        metadata = {"source": "test"}

        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Edit",
            arguments={"file_path": "/etc/passwd"},
            risk_level=RiskLevel.CRITICAL,
            risk_score=0.95,
            reasoning="Critical file operation",
            run_id="run-789",
            session_id="sess-abc",
            status=ApprovalStatus.PENDING,
            created_at=created,
            expires_at=expires,
            metadata=metadata,
        )

        assert request.session_id == "sess-abc"
        assert request.created_at == created
        assert request.expires_at == expires
        assert request.metadata == metadata

    def test_is_expired_false(self):
        """Test is_expired returns False for non-expired request."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            expires_at=datetime.utcnow() + timedelta(seconds=300),
        )

        assert request.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for expired request."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            expires_at=datetime.utcnow() - timedelta(seconds=10),
        )

        assert request.is_expired() is True

    def test_is_pending_true(self):
        """Test is_pending returns True for pending non-expired request."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            status=ApprovalStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(seconds=300),
        )

        assert request.is_pending() is True

    def test_is_pending_false_when_approved(self):
        """Test is_pending returns False for approved request."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            status=ApprovalStatus.APPROVED,
            expires_at=datetime.utcnow() + timedelta(seconds=300),
        )

        assert request.is_pending() is False

    def test_is_pending_false_when_expired(self):
        """Test is_pending returns False for expired request."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            status=ApprovalStatus.PENDING,
            expires_at=datetime.utcnow() - timedelta(seconds=10),
        )

        assert request.is_pending() is False

    def test_to_dict(self):
        """Test to_dict serialization."""
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={"command": "ls"},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test reason",
            run_id="run-789",
            session_id="sess-abc",
        )

        result = request.to_dict()

        assert result["approval_id"] == "approval-123"
        assert result["tool_call_id"] == "tc-456"
        assert result["tool_name"] == "Bash"
        assert result["arguments"] == {"command": "ls"}
        assert result["risk_level"] == "high"
        assert result["risk_score"] == 0.8
        assert result["reasoning"] == "Test reason"
        assert result["run_id"] == "run-789"
        assert result["session_id"] == "sess-abc"
        assert result["status"] == "pending"
        assert "created_at" in result
        assert "expires_at" in result

    def test_to_dict_with_resolved_at(self):
        """Test to_dict includes resolved_at when present."""
        resolved = datetime.utcnow()
        request = ApprovalRequest(
            approval_id="approval-123",
            tool_call_id="tc-456",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-789",
            status=ApprovalStatus.APPROVED,
            resolved_at=resolved,
        )

        result = request.to_dict()

        assert result["resolved_at"] is not None
        assert "Z" in result["resolved_at"]


# =============================================================================
# ApprovalStorage Tests
# =============================================================================


class TestApprovalStorage:
    """Tests for ApprovalStorage class."""

    @pytest.fixture
    def storage(self):
        """Create ApprovalStorage instance."""
        return ApprovalStorage(default_timeout_seconds=300)

    @pytest.mark.asyncio
    async def test_create_pending(self, storage):
        """Test creating a pending approval request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={"command": "rm -rf /tmp"},
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            reasoning="High-risk command",
            run_id="run-456",
        )

        assert approval_id.startswith("approval-")

        request = await storage.get(approval_id)
        assert request is not None
        assert request.tool_call_id == "tc-123"
        assert request.tool_name == "Bash"
        assert request.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_pending_with_session(self, storage):
        """Test creating pending request with session ID."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
            session_id="sess-789",
        )

        request = await storage.get(approval_id)
        assert request.session_id == "sess-789"

    @pytest.mark.asyncio
    async def test_create_pending_with_custom_timeout(self, storage):
        """Test creating pending request with custom timeout."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
            timeout_seconds=60,
        )

        request = await storage.get(approval_id)
        # Check that expires_at is roughly 60 seconds from now
        time_diff = (request.expires_at - datetime.utcnow()).total_seconds()
        assert 55 < time_diff < 65

    @pytest.mark.asyncio
    async def test_get_not_found(self, storage):
        """Test getting a non-existent request."""
        result = await storage.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_updates_expired_status(self, storage):
        """Test that get() updates status for expired requests."""
        # Create a request that's already expired
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
            timeout_seconds=0,  # Immediate expiry
        )

        # Wait a moment for expiry
        await asyncio.sleep(0.1)

        request = await storage.get(approval_id)
        assert request.status == ApprovalStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_update_status_approve(self, storage):
        """Test approving a request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        result = await storage.update_status(approval_id, approved=True)
        assert result is True

        request = await storage.get(approval_id)
        assert request.status == ApprovalStatus.APPROVED
        assert request.resolved_at is not None

    @pytest.mark.asyncio
    async def test_update_status_reject(self, storage):
        """Test rejecting a request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        result = await storage.update_status(
            approval_id, approved=False, user_comment="Too risky"
        )
        assert result is True

        request = await storage.get(approval_id)
        assert request.status == ApprovalStatus.REJECTED
        assert request.user_comment == "Too risky"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, storage):
        """Test updating non-existent request."""
        result = await storage.update_status("nonexistent", approved=True)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_status_already_resolved(self, storage):
        """Test updating already resolved request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        # First update
        await storage.update_status(approval_id, approved=True)

        # Second update should fail
        result = await storage.update_status(approval_id, approved=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_pending_empty(self, storage):
        """Test getting pending requests when none exist."""
        pending = await storage.get_pending()
        assert pending == []

    @pytest.mark.asyncio
    async def test_get_pending_returns_only_pending(self, storage):
        """Test that get_pending returns only pending requests."""
        # Create multiple requests
        id1 = await storage.create_pending(
            tool_call_id="tc-1",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test 1",
            run_id="run-1",
        )

        id2 = await storage.create_pending(
            tool_call_id="tc-2",
            tool_name="Edit",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            reasoning="Test 2",
            run_id="run-2",
        )

        # Approve one
        await storage.update_status(id1, approved=True)

        pending = await storage.get_pending()
        assert len(pending) == 1
        assert pending[0].approval_id == id2

    @pytest.mark.asyncio
    async def test_get_pending_filter_by_session(self, storage):
        """Test filtering pending by session ID."""
        await storage.create_pending(
            tool_call_id="tc-1",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test 1",
            run_id="run-1",
            session_id="sess-A",
        )

        await storage.create_pending(
            tool_call_id="tc-2",
            tool_name="Edit",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            reasoning="Test 2",
            run_id="run-2",
            session_id="sess-B",
        )

        pending = await storage.get_pending(session_id="sess-A")
        assert len(pending) == 1
        assert pending[0].session_id == "sess-A"

    @pytest.mark.asyncio
    async def test_get_pending_filter_by_run(self, storage):
        """Test filtering pending by run ID."""
        await storage.create_pending(
            tool_call_id="tc-1",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test 1",
            run_id="run-1",
        )

        await storage.create_pending(
            tool_call_id="tc-2",
            tool_name="Edit",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            reasoning="Test 2",
            run_id="run-2",
        )

        pending = await storage.get_pending(run_id="run-2")
        assert len(pending) == 1
        assert pending[0].run_id == "run-2"

    @pytest.mark.asyncio
    async def test_cancel_pending(self, storage):
        """Test cancelling a pending request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        result = await storage.cancel(approval_id)
        assert result is True

        request = await storage.get(approval_id)
        assert request.status == ApprovalStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, storage):
        """Test cancelling non-existent request."""
        result = await storage.cancel("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_already_resolved(self, storage):
        """Test cancelling already resolved request."""
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        await storage.update_status(approval_id, approved=True)

        result = await storage.cancel(approval_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, storage):
        """Test cleaning up expired requests."""
        # Create and resolve a request
        approval_id = await storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        await storage.update_status(approval_id, approved=True)

        # Cleanup with 0 max age should remove it
        removed = await storage.cleanup_expired(max_age_seconds=0)
        assert removed == 1

    def test_get_stats_empty(self, storage):
        """Test get_stats on empty storage."""
        stats = storage.get_stats()

        assert stats["total"] == 0
        assert stats["pending"] == 0
        assert stats["approved"] == 0
        assert stats["rejected"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_requests(self, storage):
        """Test get_stats with various request statuses."""
        # Create multiple requests
        id1 = await storage.create_pending(
            tool_call_id="tc-1",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-1",
        )

        await storage.create_pending(
            tool_call_id="tc-2",
            tool_name="Edit",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-2",
        )

        id3 = await storage.create_pending(
            tool_call_id="tc-3",
            tool_name="Write",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-3",
        )

        # Approve one, reject another
        await storage.update_status(id1, approved=True)
        await storage.update_status(id3, approved=False)

        stats = storage.get_stats()

        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 1


# =============================================================================
# HITLHandler Tests
# =============================================================================


class TestHITLHandler:
    """Tests for HITLHandler class."""

    @pytest.fixture
    def mock_risk_engine(self):
        """Create mock RiskAssessmentEngine."""
        engine = MagicMock()
        return engine

    @pytest.fixture
    def approval_storage(self):
        """Create ApprovalStorage instance."""
        return ApprovalStorage()

    @pytest.fixture
    def handler(self, mock_risk_engine, approval_storage):
        """Create HITLHandler instance."""
        return HITLHandler(
            risk_engine=mock_risk_engine,
            approval_storage=approval_storage,
        )

    def test_init(self, mock_risk_engine, approval_storage):
        """Test handler initialization."""
        handler = HITLHandler(
            risk_engine=mock_risk_engine,
            approval_storage=approval_storage,
            default_timeout_seconds=600,
        )

        assert handler.risk_engine is mock_risk_engine
        assert handler.approval_storage is approval_storage
        assert handler.default_timeout == 600

    @pytest.mark.asyncio
    async def test_check_approval_needed_true(self, handler, mock_risk_engine):
        """Test check_approval_needed returns True for high-risk."""
        mock_assessment = MagicMock()
        mock_assessment.overall_level = RiskLevel.HIGH
        mock_assessment.overall_score = 0.85
        mock_assessment.requires_approval = True
        mock_risk_engine.assess.return_value = mock_assessment

        tool_call = ToolCallInfo(
            id="tc-123",
            name="Bash",
            arguments={"command": "rm -rf /tmp"},
        )

        needs_approval, assessment = await handler.check_approval_needed(tool_call)

        assert needs_approval is True
        assert assessment is mock_assessment

    @pytest.mark.asyncio
    async def test_check_approval_needed_false(self, handler, mock_risk_engine):
        """Test check_approval_needed returns False for low-risk."""
        mock_assessment = MagicMock()
        mock_assessment.overall_level = RiskLevel.LOW
        mock_assessment.overall_score = 0.2
        mock_assessment.requires_approval = False
        mock_risk_engine.assess.return_value = mock_assessment

        tool_call = ToolCallInfo(
            id="tc-123",
            name="Read",
            arguments={"file_path": "/tmp/test.txt"},
        )

        needs_approval, assessment = await handler.check_approval_needed(tool_call)

        assert needs_approval is False
        assert assessment is mock_assessment

    @pytest.mark.asyncio
    async def test_create_approval_event(self, handler, mock_risk_engine):
        """Test creating approval event."""
        mock_assessment = MagicMock()
        mock_assessment.overall_level = RiskLevel.HIGH
        mock_assessment.overall_score = 0.85
        mock_assessment.approval_reason = "High-risk shell command"
        mock_assessment.factors = []

        tool_call = ToolCallInfo(
            id="tc-123",
            name="Bash",
            arguments={"command": "rm -rf /tmp"},
        )

        event = await handler.create_approval_event(
            tool_call=tool_call,
            assessment=mock_assessment,
            run_id="run-456",
            session_id="sess-789",
        )

        assert isinstance(event, CustomEvent)
        assert event.type == AGUIEventType.CUSTOM
        assert event.event_name == "approval_required"
        assert event.payload["tool_call_id"] == "tc-123"
        assert event.payload["tool_name"] == "Bash"
        assert event.payload["risk_level"] == "high"
        assert "approval_id" in event.payload

    @pytest.mark.asyncio
    async def test_create_approval_event_stores_in_storage(
        self, handler, mock_risk_engine, approval_storage
    ):
        """Test that creating approval event stores it in storage."""
        mock_assessment = MagicMock()
        mock_assessment.overall_level = RiskLevel.HIGH
        mock_assessment.overall_score = 0.85
        mock_assessment.approval_reason = "Test reason"
        mock_assessment.factors = []

        tool_call = ToolCallInfo(
            id="tc-123",
            name="Bash",
            arguments={"command": "test"},
        )

        event = await handler.create_approval_event(
            tool_call=tool_call,
            assessment=mock_assessment,
            run_id="run-456",
        )

        approval_id = event.payload["approval_id"]
        request = await approval_storage.get(approval_id)

        assert request is not None
        assert request.tool_call_id == "tc-123"
        assert request.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_handle_approval_response_approve(
        self, handler, mock_risk_engine, approval_storage
    ):
        """Test handling approval response."""
        # Create a pending request
        approval_id = await approval_storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        success, request = await handler.handle_approval_response(
            approval_id=approval_id,
            approved=True,
            user_comment="Approved by admin",
        )

        assert success is True
        assert request.status == ApprovalStatus.APPROVED
        assert request.user_comment == "Approved by admin"

    @pytest.mark.asyncio
    async def test_handle_approval_response_reject(
        self, handler, mock_risk_engine, approval_storage
    ):
        """Test handling rejection response."""
        approval_id = await approval_storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        success, request = await handler.handle_approval_response(
            approval_id=approval_id,
            approved=False,
            user_comment="Too dangerous",
        )

        assert success is True
        assert request.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_wait_for_approval(self, handler, approval_storage):
        """Test waiting for approval."""
        approval_id = await approval_storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        # Approve in background
        async def approve_later():
            await asyncio.sleep(0.1)
            await approval_storage.update_status(approval_id, approved=True)

        asyncio.create_task(approve_later())

        request = await handler.wait_for_approval(
            approval_id=approval_id,
            poll_interval_seconds=0.05,
        )

        assert request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_wait_for_approval_not_found(self, handler):
        """Test waiting for non-existent approval."""
        with pytest.raises(ValueError, match="not found"):
            await handler.wait_for_approval(
                approval_id="nonexistent",
                poll_interval_seconds=0.05,
            )

    @pytest.mark.asyncio
    async def test_create_approval_resolved_event(self, handler, approval_storage):
        """Test creating approval resolved event."""
        approval_id = await approval_storage.create_pending(
            tool_call_id="tc-123",
            tool_name="Bash",
            arguments={},
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            reasoning="Test",
            run_id="run-456",
        )

        await approval_storage.update_status(approval_id, approved=True)
        request = await approval_storage.get(approval_id)

        event = await handler.create_approval_resolved_event(request)

        assert isinstance(event, CustomEvent)
        assert event.event_name == "approval_resolved"
        assert event.payload["approval_id"] == approval_id
        assert event.payload["status"] == "approved"
        assert event.payload["approved"] is True


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_hitl_handler_defaults(self):
        """Test creating handler with defaults."""
        handler = create_hitl_handler()

        assert handler.risk_engine is not None
        assert handler.approval_storage is not None
        assert handler.default_timeout == DEFAULT_APPROVAL_TIMEOUT_SECONDS

    def test_create_hitl_handler_custom(self):
        """Test creating handler with custom components."""
        risk_engine = MagicMock()
        storage = ApprovalStorage()

        handler = create_hitl_handler(
            risk_engine=risk_engine,
            approval_storage=storage,
            default_timeout_seconds=600,
        )

        assert handler.risk_engine is risk_engine
        assert handler.approval_storage is storage
        assert handler.default_timeout == 600

    def test_get_approval_storage_singleton(self):
        """Test get_approval_storage returns singleton."""
        # Reset global
        import src.integrations.ag_ui.features.human_in_loop as module

        module._default_storage = None

        storage1 = get_approval_storage()
        storage2 = get_approval_storage()

        assert storage1 is storage2

    def test_get_hitl_handler_singleton(self):
        """Test get_hitl_handler returns singleton."""
        # Reset global
        import src.integrations.ag_ui.features.human_in_loop as module

        module._default_handler = None
        module._default_storage = None

        handler1 = get_hitl_handler()
        handler2 = get_hitl_handler()

        assert handler1 is handler2
