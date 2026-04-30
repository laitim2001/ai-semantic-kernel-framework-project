# =============================================================================
# IPA Platform - State Migrator Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL - S56-3 State Migration
#
# Unit tests for StateMigrator, MigratedState, MigrationValidator.
#
# Dependencies:
#   - pytest, pytest-asyncio
#   - StateMigrator (src.integrations.hybrid.switching.migration)
# =============================================================================

import pytest
from datetime import datetime

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.switching.migration import (
    MigratedState,
    MigrationConfig,
    MigrationError,
    MigrationValidator,
    StateMigrator,
)
from src.integrations.hybrid.switching.migration.state_migrator import (
    MigrationContext,
    MigrationStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def default_config() -> MigrationConfig:
    """Create default migration config."""
    return MigrationConfig()


@pytest.fixture
def migrator(default_config: MigrationConfig) -> StateMigrator:
    """Create StateMigrator with default config."""
    return StateMigrator(config=default_config)


@pytest.fixture
def workflow_context() -> MigrationContext:
    """Create sample workflow mode context."""
    return MigrationContext(
        session_id="sess-123",
        current_mode=ExecutionMode.WORKFLOW_MODE,
        conversation_history=[
            {"role": "user", "content": "Start workflow"},
            {"role": "assistant", "content": "Workflow started"},
        ],
        workflow_steps=[
            {"step": 1, "action": "fetch_data", "status": "completed"},
            {"step": 2, "action": "process_data", "status": "completed"},
            {"step": 3, "action": "send_report", "status": "pending"},
        ],
        tool_calls=[
            {"tool": "http_request", "result": "data fetched"},
            {"tool": "data_transform", "result": "processed"},
        ],
        variables={"output_format": "json", "batch_size": 100},
        agent_states={"agent_1": {"status": "active"}},
        metadata={"workflow_id": "wf-456"},
    )


@pytest.fixture
def chat_context() -> MigrationContext:
    """Create sample chat mode context."""
    return MigrationContext(
        session_id="sess-789",
        current_mode=ExecutionMode.CHAT_MODE,
        conversation_history=[
            {"role": "user", "content": "What is the status?"},
            {"role": "assistant", "content": "All systems operational."},
            {"role": "user", "content": "Run the daily report"},
            {"role": "assistant", "content": "I'll prepare that for you."},
        ],
        workflow_steps=[],
        tool_calls=[
            {"tool": "status_check", "result": "ok"},
        ],
        variables={"user_preference": "detailed"},
        agent_states={},
        metadata={"chat_session_id": "chat-abc"},
    )


@pytest.fixture
def empty_context() -> MigrationContext:
    """Create empty context."""
    return MigrationContext(
        session_id="sess-empty",
        current_mode=ExecutionMode.CHAT_MODE,
        conversation_history=[],
        workflow_steps=[],
        tool_calls=[],
        variables={},
        agent_states={},
        metadata={},
    )


# =============================================================================
# MigrationConfig Tests
# =============================================================================


class TestMigrationConfig:
    """Tests for MigrationConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MigrationConfig()

        assert config.preserve_history is True
        assert config.max_history_items == 100
        assert config.include_tool_calls is True
        assert config.include_metadata is True
        assert config.validate_before_migrate is True
        assert config.validate_after_migrate is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = MigrationConfig(
            preserve_history=False,
            max_history_items=50,
            include_tool_calls=False,
            include_metadata=False,
            validate_before_migrate=False,
            validate_after_migrate=False,
        )

        assert config.preserve_history is False
        assert config.max_history_items == 50
        assert config.include_tool_calls is False
        assert config.include_metadata is False
        assert config.validate_before_migrate is False
        assert config.validate_after_migrate is False


# =============================================================================
# MigratedState Tests
# =============================================================================


class TestMigratedState:
    """Tests for MigratedState dataclass."""

    def test_default_creation(self) -> None:
        """Test creating MigratedState with defaults."""
        state = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert state.source_mode == ExecutionMode.WORKFLOW_MODE
        assert state.target_mode == ExecutionMode.CHAT_MODE
        assert state.status == MigrationStatus.COMPLETED
        assert isinstance(state.migrated_at, datetime)
        assert state.conversation_history == []
        assert state.workflow_state == {}
        assert state.tool_call_records == []
        assert state.context_summary == ""
        assert state.preserved_data == {}
        assert state.warnings == []

    def test_is_successful_completed(self) -> None:
        """Test is_successful returns True for COMPLETED."""
        state = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.COMPLETED,
        )
        assert state.is_successful() is True

    def test_is_successful_partial(self) -> None:
        """Test is_successful returns True for PARTIAL."""
        state = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.PARTIAL,
        )
        assert state.is_successful() is True

    def test_is_successful_failed(self) -> None:
        """Test is_successful returns False for FAILED."""
        state = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.FAILED,
        )
        assert state.is_successful() is False

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        state = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.COMPLETED,
            conversation_history=[{"role": "user", "content": "test"}],
            context_summary="Test summary",
            warnings=["Warning 1"],
        )

        result = state.to_dict()

        assert result["source_mode"] == "workflow"
        assert result["target_mode"] == "chat"
        assert result["status"] == "completed"
        assert "migrated_at" in result
        assert result["conversation_history"] == [{"role": "user", "content": "test"}]
        assert result["context_summary"] == "Test summary"
        assert result["warnings"] == ["Warning 1"]


# =============================================================================
# MigrationContext Tests
# =============================================================================


class TestMigrationContext:
    """Tests for MigrationContext dataclass."""

    def test_creation(self, workflow_context: MigrationContext) -> None:
        """Test MigrationContext creation."""
        assert workflow_context.session_id == "sess-123"
        assert workflow_context.current_mode == ExecutionMode.WORKFLOW_MODE
        assert len(workflow_context.conversation_history) == 2
        assert len(workflow_context.workflow_steps) == 3
        assert len(workflow_context.tool_calls) == 2
        assert workflow_context.variables["output_format"] == "json"

    def test_empty_context(self, empty_context: MigrationContext) -> None:
        """Test empty MigrationContext."""
        assert empty_context.session_id == "sess-empty"
        assert empty_context.conversation_history == []
        assert empty_context.workflow_steps == []
        assert empty_context.tool_calls == []


# =============================================================================
# MigrationValidator Tests
# =============================================================================


class TestMigrationValidator:
    """Tests for MigrationValidator."""

    def test_validate_source_valid_workflow(
        self, workflow_context: MigrationContext
    ) -> None:
        """Test source validation for valid workflow context."""
        validator = MigrationValidator()

        is_valid, issues = validator.validate_source(
            workflow_context, ExecutionMode.CHAT_MODE
        )

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_source_valid_chat(
        self, chat_context: MigrationContext
    ) -> None:
        """Test source validation for valid chat context."""
        validator = MigrationValidator()

        is_valid, issues = validator.validate_source(
            chat_context, ExecutionMode.WORKFLOW_MODE
        )

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_source_missing_session_id(self) -> None:
        """Test validation fails for missing session ID."""
        validator = MigrationValidator()
        context = MigrationContext(
            session_id="",
            current_mode=ExecutionMode.CHAT_MODE,
        )

        is_valid, issues = validator.validate_source(
            context, ExecutionMode.WORKFLOW_MODE
        )

        assert is_valid is False
        assert "Missing session ID" in issues

    def test_validate_source_same_mode(
        self, chat_context: MigrationContext
    ) -> None:
        """Test validation warns for same source and target mode."""
        validator = MigrationValidator()

        is_valid, issues = validator.validate_source(
            chat_context, ExecutionMode.CHAT_MODE
        )

        # Same mode is valid but generates warning
        assert is_valid is True
        assert any("same" in issue.lower() for issue in issues)

    def test_validate_source_empty_workflow(self) -> None:
        """Test validation warns for workflow mode without data."""
        validator = MigrationValidator()
        context = MigrationContext(
            session_id="sess-123",
            current_mode=ExecutionMode.WORKFLOW_MODE,
            workflow_steps=[],
            tool_calls=[],
        )

        is_valid, issues = validator.validate_source(
            context, ExecutionMode.CHAT_MODE
        )

        assert is_valid is False
        assert any("no execution data" in issue.lower() for issue in issues)

    def test_validate_source_empty_chat(self, empty_context: MigrationContext) -> None:
        """Test validation warns for chat mode without history."""
        validator = MigrationValidator()

        is_valid, issues = validator.validate_source(
            empty_context, ExecutionMode.WORKFLOW_MODE
        )

        assert is_valid is False
        assert any("no conversation history" in issue.lower() for issue in issues)

    def test_validate_result_success(
        self, workflow_context: MigrationContext
    ) -> None:
        """Test result validation for successful migration."""
        validator = MigrationValidator()
        result = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.COMPLETED,
            conversation_history=[{"role": "user", "content": "test"}],
            tool_call_records=[{"tool": "test"}],
            context_summary="Test summary",
        )

        is_valid, issues = validator.validate_result(result, workflow_context)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_result_failed_status(
        self, workflow_context: MigrationContext
    ) -> None:
        """Test result validation for failed migration."""
        validator = MigrationValidator()
        result = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.FAILED,
        )

        is_valid, issues = validator.validate_result(result, workflow_context)

        assert is_valid is False
        assert "Migration failed" in issues

    def test_validate_result_lost_history(
        self, workflow_context: MigrationContext
    ) -> None:
        """Test result validation detects lost conversation history."""
        validator = MigrationValidator()
        result = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.COMPLETED,
            conversation_history=[],  # Lost history
            tool_call_records=[{"tool": "test"}],
            context_summary="Test summary",
        )

        is_valid, issues = validator.validate_result(result, workflow_context)

        assert is_valid is False
        assert any("history was lost" in issue.lower() for issue in issues)

    def test_validate_result_missing_context_summary(
        self, workflow_context: MigrationContext
    ) -> None:
        """Test result validation detects missing context summary."""
        validator = MigrationValidator()
        result = MigratedState(
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
            status=MigrationStatus.COMPLETED,
            conversation_history=[{"role": "user", "content": "test"}],
            context_summary="",  # Missing summary
        )

        is_valid, issues = validator.validate_result(result, workflow_context)

        assert is_valid is False
        assert any("context summary" in issue.lower() for issue in issues)


# =============================================================================
# StateMigrator Tests
# =============================================================================


class TestStateMigratorInit:
    """Tests for StateMigrator initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        migrator = StateMigrator()

        assert migrator.config is not None
        assert migrator.validator is not None
        assert migrator.get_migration_count() == 0

    def test_custom_config_init(self) -> None:
        """Test initialization with custom config."""
        config = MigrationConfig(max_history_items=50)
        migrator = StateMigrator(config=config)

        assert migrator.config.max_history_items == 50

    def test_repr(self) -> None:
        """Test string representation."""
        migrator = StateMigrator()
        assert "StateMigrator" in repr(migrator)
        assert "migrations=0" in repr(migrator)


class TestStateMigratorWorkflowToChat:
    """Tests for Workflow → Chat migration."""

    @pytest.mark.asyncio
    async def test_basic_migration(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test basic workflow to chat migration."""
        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert result.is_successful()
        assert result.source_mode == ExecutionMode.WORKFLOW_MODE
        assert result.target_mode == ExecutionMode.CHAT_MODE
        assert len(result.conversation_history) > 0
        assert result.context_summary != ""

    @pytest.mark.asyncio
    async def test_workflow_steps_converted(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test workflow steps are converted to conversation history."""
        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        # Should have workflow steps converted
        step_messages = [
            msg for msg in result.conversation_history
            if msg.get("metadata", {}).get("type") == "workflow_step"
        ]
        assert len(step_messages) == 3  # 3 workflow steps

    @pytest.mark.asyncio
    async def test_tool_calls_preserved(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test tool calls are preserved during migration."""
        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert len(result.tool_call_records) == 2

    @pytest.mark.asyncio
    async def test_context_summary_generated(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test context summary is generated."""
        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert "workflow steps" in result.context_summary.lower()
        assert "tool calls" in result.context_summary.lower()

    @pytest.mark.asyncio
    async def test_variables_preserved(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test variables are preserved in preserved_data."""
        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert "original_variables" in result.preserved_data
        assert result.preserved_data["original_variables"]["output_format"] == "json"

    @pytest.mark.asyncio
    async def test_without_tool_calls(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test migration without tool calls config."""
        config = MigrationConfig(include_tool_calls=False)
        migrator = StateMigrator(config=config)

        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert result.tool_call_records == []

    @pytest.mark.asyncio
    async def test_without_metadata(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test migration without metadata config."""
        config = MigrationConfig(include_metadata=False)
        migrator = StateMigrator(config=config)

        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert result.preserved_data == {}


class TestStateMigratorChatToWorkflow:
    """Tests for Chat → Workflow migration."""

    @pytest.mark.asyncio
    async def test_basic_migration(
        self, migrator: StateMigrator, chat_context: MigrationContext
    ) -> None:
        """Test basic chat to workflow migration."""
        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.is_successful()
        assert result.source_mode == ExecutionMode.CHAT_MODE
        assert result.target_mode == ExecutionMode.WORKFLOW_MODE

    @pytest.mark.asyncio
    async def test_workflow_state_created(
        self, migrator: StateMigrator, chat_context: MigrationContext
    ) -> None:
        """Test workflow state is created from conversation."""
        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert "initial_context" in result.workflow_state
        assert "variables" in result.workflow_state
        assert "conversation_summary" in result.workflow_state

    @pytest.mark.asyncio
    async def test_intent_extracted(
        self, migrator: StateMigrator, chat_context: MigrationContext
    ) -> None:
        """Test user intent is extracted from conversation."""
        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        # Should extract last user message as intent
        assert "daily report" in result.workflow_state["initial_context"].lower()

    @pytest.mark.asyncio
    async def test_conversation_summary_created(
        self, migrator: StateMigrator, chat_context: MigrationContext
    ) -> None:
        """Test conversation summary is created."""
        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        summary = result.workflow_state["conversation_summary"]
        assert "messages" in summary.lower()

    @pytest.mark.asyncio
    async def test_history_preserved(
        self, migrator: StateMigrator, chat_context: MigrationContext
    ) -> None:
        """Test conversation history is preserved."""
        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert len(result.conversation_history) == 4

    @pytest.mark.asyncio
    async def test_without_history_preservation(
        self, chat_context: MigrationContext
    ) -> None:
        """Test migration without history preservation."""
        config = MigrationConfig(preserve_history=False)
        migrator = StateMigrator(config=config)

        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.conversation_history == []


class TestStateMigratorHybridMode:
    """Tests for Hybrid mode migration."""

    @pytest.mark.asyncio
    async def test_hybrid_migration(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test hybrid mode migration preserves everything."""
        # Set to hybrid mode
        workflow_context.current_mode = ExecutionMode.HYBRID_MODE

        result = await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.HYBRID_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert result.is_successful()
        assert len(result.conversation_history) > 0
        assert result.workflow_state != {}
        assert len(result.tool_call_records) > 0
        assert result.context_summary != ""


class TestStateMigratorValidation:
    """Tests for validation during migration."""

    @pytest.mark.asyncio
    async def test_validation_error_on_invalid_source(
        self, migrator: StateMigrator
    ) -> None:
        """Test migration raises error on invalid source."""
        invalid_context = MigrationContext(
            session_id="",  # Invalid: empty session ID
            current_mode=ExecutionMode.CHAT_MODE,
        )

        with pytest.raises(MigrationError) as exc_info:
            await migrator.migrate(
                invalid_context,
                source_mode=ExecutionMode.CHAT_MODE,
                target_mode=ExecutionMode.WORKFLOW_MODE,
            )

        assert "validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_skip_validation(
        self, empty_context: MigrationContext
    ) -> None:
        """Test migration without validation."""
        config = MigrationConfig(
            validate_before_migrate=False,
            validate_after_migrate=False,
        )
        migrator = StateMigrator(config=config)

        # Should not raise even with empty context
        result = await migrator.migrate(
            empty_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert result.status == MigrationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_partial_status_on_validation_issues(
        self, chat_context: MigrationContext
    ) -> None:
        """Test migration returns PARTIAL status on validation issues."""
        # Use preserve_history=False so conversation history is lost
        # Validator will detect source had history but result doesn't
        config = MigrationConfig(preserve_history=False)
        migrator = StateMigrator(config=config)

        result = await migrator.migrate(
            chat_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        # Should complete but with warnings (history was lost)
        assert result.is_successful()
        assert result.status == MigrationStatus.PARTIAL
        assert len(result.warnings) > 0


class TestStateMigratorMigrationCount:
    """Tests for migration count tracking."""

    @pytest.mark.asyncio
    async def test_migration_count_increments(
        self, migrator: StateMigrator, workflow_context: MigrationContext
    ) -> None:
        """Test migration count increments after each migration."""
        assert migrator.get_migration_count() == 0

        await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert migrator.get_migration_count() == 1

        # Migrate back
        workflow_context.current_mode = ExecutionMode.CHAT_MODE
        await migrator.migrate(
            workflow_context,
            source_mode=ExecutionMode.CHAT_MODE,
            target_mode=ExecutionMode.WORKFLOW_MODE,
        )

        assert migrator.get_migration_count() == 2


class TestStateMigratorHistoryLimits:
    """Tests for history item limits."""

    @pytest.mark.asyncio
    async def test_max_history_items(self) -> None:
        """Test max_history_items limits conversation history."""
        config = MigrationConfig(max_history_items=2)
        migrator = StateMigrator(config=config)

        context = MigrationContext(
            session_id="sess-123",
            current_mode=ExecutionMode.WORKFLOW_MODE,
            workflow_steps=[
                {"step": i, "action": f"action_{i}"} for i in range(10)
            ],
            tool_calls=[
                {"tool": f"tool_{i}"} for i in range(10)
            ],
        )

        result = await migrator.migrate(
            context,
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        # Should only have 2 workflow steps converted
        step_messages = [
            msg for msg in result.conversation_history
            if msg.get("metadata", {}).get("type") == "workflow_step"
        ]
        assert len(step_messages) == 2

        # Should only have 2 tool calls
        assert len(result.tool_call_records) == 2


# =============================================================================
# MigrationError Tests
# =============================================================================


class TestMigrationError:
    """Tests for MigrationError exception."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = MigrationError("Migration failed")

        assert str(error) == "Migration failed"
        assert error.source_mode is None
        assert error.target_mode is None
        assert error.details == {}

    def test_error_with_modes(self) -> None:
        """Test error with mode information."""
        error = MigrationError(
            "Migration failed",
            source_mode=ExecutionMode.WORKFLOW_MODE,
            target_mode=ExecutionMode.CHAT_MODE,
        )

        assert error.source_mode == ExecutionMode.WORKFLOW_MODE
        assert error.target_mode == ExecutionMode.CHAT_MODE

    def test_error_with_details(self) -> None:
        """Test error with details."""
        error = MigrationError(
            "Migration failed",
            details={"reason": "validation_error", "field": "session_id"},
        )

        assert error.details["reason"] == "validation_error"
        assert error.details["field"] == "session_id"
