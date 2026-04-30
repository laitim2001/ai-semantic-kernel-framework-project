# =============================================================================
# IPA Platform - Audit Unit Tests
# =============================================================================
# Sprint 3: 集成 & 可靠性 - 審計日誌系統
#
# Tests for:
#   - AuditEntry
#   - AuditLogger
#   - Query and Export
#   - Statistics
# =============================================================================

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.audit.logger import (
    AuditAction,
    AuditEntry,
    AuditError,
    AuditLogger,
    AuditQueryParams,
    AuditResource,
    AuditSeverity,
)


# =============================================================================
# AuditEntry Tests
# =============================================================================


class TestAuditEntry:
    """Tests for AuditEntry."""

    def test_initialization(self):
        """Test basic initialization."""
        entry = AuditEntry(
            action=AuditAction.WORKFLOW_CREATED,
            resource=AuditResource.WORKFLOW,
            message="Workflow created",
        )

        assert entry.action == AuditAction.WORKFLOW_CREATED
        assert entry.resource == AuditResource.WORKFLOW
        assert entry.message == "Workflow created"
        assert entry.severity == AuditSeverity.INFO
        assert entry.actor_name == "system"

    def test_initialization_with_options(self):
        """Test initialization with all options."""
        workflow_id = uuid4()
        execution_id = uuid4()

        entry = AuditEntry(
            action=AuditAction.WORKFLOW_TRIGGERED,
            resource=AuditResource.WORKFLOW,
            resource_id=str(workflow_id),
            actor_id="user123",
            actor_name="John Doe",
            message="Workflow triggered by user",
            severity=AuditSeverity.WARNING,
            details={"trigger": "manual"},
            workflow_id=workflow_id,
            execution_id=execution_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert entry.actor_id == "user123"
        assert entry.actor_name == "John Doe"
        assert entry.severity == AuditSeverity.WARNING
        assert entry.workflow_id == workflow_id
        assert entry.execution_id == execution_id
        assert entry.ip_address == "192.168.1.1"

    def test_to_dict(self):
        """Test serialization."""
        entry = AuditEntry(
            action=AuditAction.AGENT_EXECUTED,
            resource=AuditResource.AGENT,
            message="Agent executed",
        )

        result = entry.to_dict()

        assert result["action"] == "agent.executed"
        assert result["resource"] == "agent"
        assert result["message"] == "Agent executed"
        assert "id" in result
        assert "timestamp" in result

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "id": str(uuid4()),
            "action": "checkpoint.approved",
            "resource": "checkpoint",
            "message": "Checkpoint approved",
            "actor_name": "admin",
            "severity": "info",
            "timestamp": datetime.utcnow().isoformat(),
        }

        entry = AuditEntry.from_dict(data)

        assert entry.action == AuditAction.CHECKPOINT_APPROVED
        assert entry.resource == AuditResource.CHECKPOINT
        assert entry.actor_name == "admin"


# =============================================================================
# AuditLogger Tests
# =============================================================================


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.fixture
    def logger(self):
        """Create logger instance."""
        return AuditLogger()

    # -------------------------------------------------------------------------
    # Logging Tests
    # -------------------------------------------------------------------------

    def test_log_basic(self, logger):
        """Test basic logging."""
        entry = logger.log(
            action=AuditAction.WORKFLOW_CREATED,
            resource=AuditResource.WORKFLOW,
            message="Created new workflow",
        )

        assert entry is not None
        assert entry.action == AuditAction.WORKFLOW_CREATED
        assert logger.get_entry_count() == 1

    def test_log_with_details(self, logger):
        """Test logging with details."""
        entry = logger.log(
            action=AuditAction.AGENT_EXECUTED,
            resource=AuditResource.AGENT,
            message="Agent executed",
            actor_id="user123",
            details={"duration_ms": 150},
        )

        assert entry.actor_id == "user123"
        assert entry.details["duration_ms"] == 150

    def test_log_workflow_event(self, logger):
        """Test workflow event logging."""
        workflow_id = uuid4()
        execution_id = uuid4()

        entry = logger.log_workflow_event(
            action=AuditAction.WORKFLOW_TRIGGERED,
            workflow_id=workflow_id,
            message="Triggered by webhook",
            execution_id=execution_id,
        )

        assert entry.resource == AuditResource.WORKFLOW
        assert entry.workflow_id == workflow_id
        assert entry.execution_id == execution_id

    def test_log_agent_event(self, logger):
        """Test agent event logging."""
        agent_id = uuid4()

        entry = logger.log_agent_event(
            action=AuditAction.AGENT_EXECUTED,
            agent_id=agent_id,
            message="Agent completed task",
        )

        assert entry.resource == AuditResource.AGENT
        assert entry.resource_id == str(agent_id)

    def test_log_checkpoint_event(self, logger):
        """Test checkpoint event logging."""
        checkpoint_id = uuid4()
        workflow_id = uuid4()

        entry = logger.log_checkpoint_event(
            action=AuditAction.CHECKPOINT_APPROVED,
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            message="Checkpoint approved by admin",
            actor_name="admin",
        )

        assert entry.resource == AuditResource.CHECKPOINT
        assert entry.workflow_id == workflow_id

    def test_log_user_event(self, logger):
        """Test user event logging."""
        entry = logger.log_user_event(
            action=AuditAction.USER_LOGIN,
            user_id="user123",
            message="User logged in",
            ip_address="10.0.0.1",
            user_agent="Chrome/100",
        )

        assert entry.resource == AuditResource.USER
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "Chrome/100"

    def test_log_system_event(self, logger):
        """Test system event logging."""
        entry = logger.log_system_event(
            action=AuditAction.SYSTEM_ERROR,
            message="Database connection failed",
            severity=AuditSeverity.CRITICAL,
        )

        assert entry.resource == AuditResource.SYSTEM
        assert entry.severity == AuditSeverity.CRITICAL

    def test_log_error(self, logger):
        """Test error logging."""
        error = ValueError("Invalid input")

        entry = logger.log_error(
            resource=AuditResource.WORKFLOW,
            message="Workflow validation failed",
            error=error,
        )

        assert entry.severity == AuditSeverity.ERROR
        assert entry.details["error_type"] == "ValueError"
        assert "Invalid input" in entry.details["error_message"]

    # -------------------------------------------------------------------------
    # Query Tests
    # -------------------------------------------------------------------------

    def test_query_all(self, logger):
        """Test querying all entries."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)
        logger.log(AuditAction.CHECKPOINT_APPROVED, AuditResource.CHECKPOINT)

        results = logger.query()

        assert len(results) == 3

    def test_query_by_action(self, logger):
        """Test querying by action."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)

        params = AuditQueryParams(actions=[AuditAction.WORKFLOW_CREATED])
        results = logger.query(params)

        assert len(results) == 1
        assert results[0].action == AuditAction.WORKFLOW_CREATED

    def test_query_by_resource(self, logger):
        """Test querying by resource."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)
        logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW)

        params = AuditQueryParams(resources=[AuditResource.WORKFLOW])
        results = logger.query(params)

        assert len(results) == 2
        assert all(r.resource == AuditResource.WORKFLOW for r in results)

    def test_query_by_actor(self, logger):
        """Test querying by actor."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW, actor_id="user1")
        logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW, actor_id="user2")

        params = AuditQueryParams(actor_id="user1")
        results = logger.query(params)

        assert len(results) == 1
        assert results[0].actor_id == "user1"

    def test_query_by_time_range(self, logger):
        """Test querying by time range."""
        # 創建不同時間的條目
        old_entry = logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        old_entry.timestamp = datetime.utcnow() - timedelta(hours=2)

        new_entry = logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW)

        params = AuditQueryParams(
            start_time=datetime.utcnow() - timedelta(hours=1)
        )
        results = logger.query(params)

        assert len(results) == 1
        assert results[0].action == AuditAction.WORKFLOW_UPDATED

    def test_query_pagination(self, logger):
        """Test query pagination."""
        for i in range(10):
            logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)

        params = AuditQueryParams(limit=5, offset=0)
        page1 = logger.query(params)

        params = AuditQueryParams(limit=5, offset=5)
        page2 = logger.query(params)

        assert len(page1) == 5
        assert len(page2) == 5

    def test_get_entry(self, logger):
        """Test getting single entry."""
        entry = logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)

        result = logger.get_entry(entry.id)

        assert result is not None
        assert result.id == entry.id

    def test_get_entry_not_found(self, logger):
        """Test getting non-existent entry."""
        result = logger.get_entry(uuid4())
        assert result is None

    # -------------------------------------------------------------------------
    # Execution Trail Tests
    # -------------------------------------------------------------------------

    def test_get_execution_trail(self, logger):
        """Test getting execution trail."""
        execution_id = uuid4()
        workflow_id = uuid4()

        logger.log(
            AuditAction.EXECUTION_STARTED,
            AuditResource.EXECUTION,
            execution_id=execution_id,
            workflow_id=workflow_id,
        )
        logger.log(
            AuditAction.AGENT_EXECUTED,
            AuditResource.AGENT,
            execution_id=execution_id,
        )
        logger.log(
            AuditAction.EXECUTION_COMPLETED,
            AuditResource.EXECUTION,
            execution_id=execution_id,
        )

        trail = logger.get_execution_trail(execution_id)

        assert len(trail) == 3
        # 應該按時間順序排列
        assert trail[0].action == AuditAction.EXECUTION_STARTED
        assert trail[-1].action == AuditAction.EXECUTION_COMPLETED

    def test_get_execution_trail_with_related(self, logger):
        """Test execution trail including related events."""
        execution_id = uuid4()
        workflow_id = uuid4()

        # 執行事件
        logger.log(
            AuditAction.EXECUTION_STARTED,
            AuditResource.EXECUTION,
            execution_id=execution_id,
            workflow_id=workflow_id,
        )

        # 相關工作流事件 (不同 execution_id)
        logger.log(
            AuditAction.WORKFLOW_UPDATED,
            AuditResource.WORKFLOW,
            workflow_id=workflow_id,
        )

        trail = logger.get_execution_trail(execution_id, include_related=True)

        assert len(trail) >= 1

    def test_count(self, logger):
        """Test counting entries."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)

        assert logger.count() == 2

    def test_count_with_filter(self, logger):
        """Test counting with filter."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)

        params = AuditQueryParams(resources=[AuditResource.WORKFLOW])
        count = logger.count(params)

        assert count == 2

    # -------------------------------------------------------------------------
    # Export Tests
    # -------------------------------------------------------------------------

    def test_export_csv(self, logger):
        """Test CSV export."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW, message="Test")

        csv = logger.export_csv()

        assert "id" in csv
        assert "workflow.created" in csv
        assert "Test" in csv

    def test_export_json(self, logger):
        """Test JSON export."""
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT, message="Test")

        json_data = logger.export_json()

        assert len(json_data) == 1
        assert json_data[0]["action"] == "agent.executed"

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    def test_get_statistics(self, logger):
        """Test getting statistics."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.WORKFLOW_UPDATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)
        logger.log_error(AuditResource.SYSTEM, "Error occurred")

        stats = logger.get_statistics()

        assert stats["total_entries"] == 4
        assert stats["by_action"]["workflow.created"] == 1
        assert stats["by_resource"]["workflow"] == 2
        assert stats["by_severity"]["error"] == 1

    # -------------------------------------------------------------------------
    # Subscription Tests
    # -------------------------------------------------------------------------

    def test_subscribe(self, logger):
        """Test subscribing to events."""
        received_entries = []

        def callback(entry):
            received_entries.append(entry)

        logger.subscribe(callback)
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)

        assert len(received_entries) == 1

    def test_unsubscribe(self, logger):
        """Test unsubscribing from events."""
        received_entries = []

        def callback(entry):
            received_entries.append(entry)

        logger.subscribe(callback)
        logger.unsubscribe(callback)
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)

        assert len(received_entries) == 0

    # -------------------------------------------------------------------------
    # Utility Tests
    # -------------------------------------------------------------------------

    def test_clear(self, logger):
        """Test clearing entries."""
        logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)
        logger.log(AuditAction.AGENT_EXECUTED, AuditResource.AGENT)

        logger.clear()

        assert logger.get_entry_count() == 0

    def test_max_entries_limit(self):
        """Test max entries limit."""
        logger = AuditLogger(max_memory_entries=5)

        for i in range(10):
            logger.log(AuditAction.WORKFLOW_CREATED, AuditResource.WORKFLOW)

        assert logger.get_entry_count() == 5


# =============================================================================
# Enum Tests
# =============================================================================


class TestAuditEnums:
    """Tests for audit enums."""

    def test_audit_action_values(self):
        """Test action values."""
        assert AuditAction.WORKFLOW_CREATED.value == "workflow.created"
        assert AuditAction.AGENT_EXECUTED.value == "agent.executed"
        assert AuditAction.CHECKPOINT_APPROVED.value == "checkpoint.approved"
        assert AuditAction.USER_LOGIN.value == "user.login"

    def test_audit_resource_values(self):
        """Test resource values."""
        assert AuditResource.WORKFLOW.value == "workflow"
        assert AuditResource.AGENT.value == "agent"
        assert AuditResource.USER.value == "user"

    def test_audit_severity_values(self):
        """Test severity values."""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


# =============================================================================
# Exception Tests
# =============================================================================


class TestAuditExceptions:
    """Tests for audit exceptions."""

    def test_audit_error(self):
        """Test audit error."""
        error = AuditError("Test error", code="TEST_CODE")

        assert str(error) == "Test error"
        assert error.code == "TEST_CODE"
