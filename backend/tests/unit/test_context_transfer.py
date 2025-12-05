# =============================================================================
# IPA Platform - Context Transfer Manager Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for the context transfer manager including:
#   - TransferContext data structure
#   - TransformationRule data structure
#   - Context extraction
#   - Context transformation
#   - Context validation
#   - Context injection
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.orchestration.handoff.context_transfer import (
    ContextTransferManager,
    TransferContext,
    TransferValidationError,
    TransformationRule,
)


# =============================================================================
# TransferContext Tests
# =============================================================================


class TestTransferContext:
    """Tests for TransferContext dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        context = TransferContext(
            task_id="task-001",
        )

        assert context.task_id == "task-001"
        assert context.task_state == {}
        assert context.conversation_history == []
        assert context.metadata == {}
        assert context.source_agent_id is None
        assert context.target_agent_id is None
        assert context.handoff_reason == ""
        assert isinstance(context.timestamp, datetime)
        assert context.checksum is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        context = TransferContext(
            task_id="task-002",
            task_state={"step": 1},
            conversation_history=[{"role": "user", "content": "test"}],
            metadata={"priority": "high"},
            source_agent_id="agent-1",
            target_agent_id="agent-2",
            handoff_reason="capacity",
            checksum="abc123",
        )

        assert context.task_id == "task-002"
        assert context.task_state == {"step": 1}
        assert len(context.conversation_history) == 1
        assert context.metadata == {"priority": "high"}
        assert context.source_agent_id == "agent-1"
        assert context.target_agent_id == "agent-2"
        assert context.handoff_reason == "capacity"
        assert context.checksum == "abc123"


# =============================================================================
# TransformationRule Tests
# =============================================================================


class TestTransformationRule:
    """Tests for TransformationRule dataclass."""

    def test_basic_rule(self):
        """Test basic rule creation."""
        rule = TransformationRule(
            source_field="old_name",
            target_field="new_name",
        )

        assert rule.source_field == "old_name"
        assert rule.target_field == "new_name"
        assert rule.transformer is None
        assert rule.required is False

    def test_rule_with_transformer(self):
        """Test rule with transformer function."""
        transformer = lambda x: x.upper()
        rule = TransformationRule(
            source_field="name",
            target_field="name",
            transformer=transformer,
            required=True,
        )

        assert rule.transformer is not None
        assert rule.required is True
        assert rule.transformer("test") == "TEST"


# =============================================================================
# TransferValidationError Tests
# =============================================================================


class TestTransferValidationError:
    """Tests for TransferValidationError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = TransferValidationError("Validation failed")

        assert str(error) == "Validation failed"
        assert error.field is None
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with field and details."""
        error = TransferValidationError(
            "Field missing",
            field="task_id",
            details={"expected": "string"},
        )

        assert error.field == "task_id"
        assert error.details == {"expected": "string"}


# =============================================================================
# ContextTransferManager Tests
# =============================================================================


class TestContextTransferManager:
    """Tests for ContextTransferManager class."""

    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return ContextTransferManager()

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        service = AsyncMock()
        service.get_agent_state = AsyncMock(return_value={"step": 1, "data": "test"})
        service.get_conversation_history = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        )
        service.get_agent_metadata = AsyncMock(return_value={"type": "support"})
        service.inject_context = AsyncMock()
        return service

    @pytest.fixture
    def sample_context(self):
        """Create sample transfer context."""
        return TransferContext(
            task_id="task-001",
            task_state={"step": 1, "variables": {"x": 10}},
            conversation_history=[{"role": "user", "content": "Test"}],
            metadata={"source": "api"},
        )

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_default_initialization(self):
        """Test default initialization."""
        manager = ContextTransferManager()

        assert manager._required_fields == {"task_id", "task_state"}
        assert manager._max_history_length == 100
        assert manager._max_context_size == 10 * 1024 * 1024

    def test_custom_initialization(self):
        """Test custom initialization."""
        manager = ContextTransferManager(
            required_fields={"task_id", "metadata"},
            max_history_length=50,
            max_context_size=1024 * 1024,
        )

        assert "metadata" in manager._required_fields
        assert manager._max_history_length == 50
        assert manager._max_context_size == 1024 * 1024

    # -------------------------------------------------------------------------
    # Extract Context Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_extract_context_full(self, manager, mock_agent_service):
        """Test full context extraction."""
        agent_id = uuid4()

        context = await manager.extract_context(
            agent_service=mock_agent_service,
            source_agent_id=agent_id,
            task_id="task-001",
        )

        assert context.task_id == "task-001"
        assert context.task_state == {"step": 1, "data": "test"}
        assert len(context.conversation_history) == 2
        assert context.metadata == {"type": "support"}
        assert context.source_agent_id == str(agent_id)
        assert context.checksum is not None

    @pytest.mark.asyncio
    async def test_extract_context_without_history(self, manager, mock_agent_service):
        """Test extraction without conversation history."""
        context = await manager.extract_context(
            agent_service=mock_agent_service,
            source_agent_id=uuid4(),
            task_id="task-002",
            include_history=False,
        )

        assert context.conversation_history == []

    @pytest.mark.asyncio
    async def test_extract_context_without_metadata(self, manager, mock_agent_service):
        """Test extraction without metadata."""
        context = await manager.extract_context(
            agent_service=mock_agent_service,
            source_agent_id=uuid4(),
            task_id="task-003",
            include_metadata=False,
        )

        assert context.metadata == {}

    @pytest.mark.asyncio
    async def test_extract_context_without_service(self, manager):
        """Test extraction without agent service."""
        context = await manager.extract_context(
            agent_service=None,
            source_agent_id=uuid4(),
            task_id="task-004",
        )

        assert context.task_id == "task-004"
        assert context.task_state == {}

    # -------------------------------------------------------------------------
    # Transform Context Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_transform_context_basic(self, manager, sample_context):
        """Test basic context transformation."""
        transformed = await manager.transform_context(sample_context)

        assert transformed.task_id == sample_context.task_id
        assert transformed.checksum is not None

    @pytest.mark.asyncio
    async def test_transform_context_with_rule(self, manager, sample_context):
        """Test transformation with rule."""
        rules = [
            TransformationRule(
                source_field="step",
                target_field="current_step",
            )
        ]

        transformed = await manager.transform_context(sample_context, rules=rules)

        assert "current_step" in transformed.task_state
        assert "step" not in transformed.task_state

    @pytest.mark.asyncio
    async def test_transform_context_with_transformer(self, manager, sample_context):
        """Test transformation with transformer function."""
        rules = [
            TransformationRule(
                source_field="step",
                target_field="step",
                transformer=lambda x: x * 2,
            )
        ]

        transformed = await manager.transform_context(sample_context, rules=rules)

        assert transformed.task_state["step"] == 2

    @pytest.mark.asyncio
    async def test_transform_trims_history(self, manager):
        """Test that transformation trims long history."""
        manager._max_history_length = 5

        context = TransferContext(
            task_id="task-001",
            task_state={},
            conversation_history=[{"role": "user", "content": f"msg-{i}"} for i in range(10)],
        )

        transformed = await manager.transform_context(context)

        assert len(transformed.conversation_history) == 5

    @pytest.mark.asyncio
    async def test_transform_updates_timestamp(self, manager, sample_context):
        """Test that transformation updates timestamp."""
        original_timestamp = sample_context.timestamp

        transformed = await manager.transform_context(sample_context)

        assert transformed.timestamp >= original_timestamp

    @pytest.mark.asyncio
    async def test_transform_does_not_modify_original(self, manager, sample_context):
        """Test that transformation does not modify original."""
        original_step = sample_context.task_state["step"]

        rules = [
            TransformationRule(
                source_field="step",
                target_field="step",
                transformer=lambda x: x * 10,
            )
        ]

        await manager.transform_context(sample_context, rules=rules)

        assert sample_context.task_state["step"] == original_step

    # -------------------------------------------------------------------------
    # Validate Context Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_validate_context_success(self, manager, sample_context):
        """Test successful validation."""
        result = await manager.validate_context(sample_context)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_context_missing_task_id(self, manager):
        """Test validation fails for missing task_id."""
        context = TransferContext(
            task_id="",
            task_state={"key": "value"},
        )

        with pytest.raises(TransferValidationError):
            await manager.validate_context(context, strict=True)

    @pytest.mark.asyncio
    async def test_validate_context_invalid_task_state(self, manager):
        """Test validation with invalid task_state type."""
        context = TransferContext(
            task_id="task-001",
            task_state={},  # Empty is OK but we'll test with custom validator
        )

        # Create custom validator
        def check_non_empty(ctx):
            if not ctx.task_state:
                raise TransferValidationError("task_state cannot be empty")

        manager.register_validator(check_non_empty)

        with pytest.raises(TransferValidationError):
            await manager.validate_context(context, strict=True)

    @pytest.mark.asyncio
    async def test_validate_context_non_strict(self, manager):
        """Test non-strict validation returns False."""
        context = TransferContext(
            task_id="",
            task_state={},
        )

        result = await manager.validate_context(context, strict=False)

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_context_size_limit(self, manager):
        """Test validation fails for oversized context."""
        manager._max_context_size = 100  # Very small limit

        context = TransferContext(
            task_id="task-001",
            task_state={"large_data": "x" * 200},
        )

        with pytest.raises(TransferValidationError):
            await manager.validate_context(context, strict=True)

    @pytest.mark.asyncio
    async def test_custom_validator_called(self, manager, sample_context):
        """Test that custom validators are called."""
        validator_called = []

        def custom_validator(ctx):
            validator_called.append(True)

        manager.register_validator(custom_validator)

        await manager.validate_context(sample_context)

        assert len(validator_called) == 1

    # -------------------------------------------------------------------------
    # Inject Context Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_inject_context_success(self, manager, sample_context, mock_agent_service):
        """Test successful context injection."""
        target_id = uuid4()

        result = await manager.inject_context(
            agent_service=mock_agent_service,
            target_agent_id=target_id,
            context=sample_context,
        )

        assert result is True
        assert sample_context.target_agent_id == str(target_id)
        mock_agent_service.inject_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_inject_context_validates(self, manager, mock_agent_service):
        """Test that injection validates by default."""
        invalid_context = TransferContext(
            task_id="",
            task_state={},
        )

        with pytest.raises(TransferValidationError):
            await manager.inject_context(
                agent_service=mock_agent_service,
                target_agent_id=uuid4(),
                context=invalid_context,
                validate=True,
            )

    @pytest.mark.asyncio
    async def test_inject_context_skip_validation(self, manager, mock_agent_service):
        """Test injection with validation skipped."""
        context = TransferContext(
            task_id="",  # Invalid but skipping validation
            task_state={},
        )

        result = await manager.inject_context(
            agent_service=mock_agent_service,
            target_agent_id=uuid4(),
            context=context,
            validate=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_inject_without_service(self, manager, sample_context):
        """Test injection without agent service."""
        result = await manager.inject_context(
            agent_service=None,
            target_agent_id=uuid4(),
            context=sample_context,
            validate=False,
        )

        assert result is True

    # -------------------------------------------------------------------------
    # Transfer Shortcut Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_transfer_shortcut(self, manager):
        """Test simple transfer method."""
        target_id = uuid4()
        context_data = {
            "task_id": "task-001",
            "task_state": {"step": 1},
            "conversation_history": [],
            "metadata": {},
            "source_agent_id": "agent-1",
            "handoff_reason": "test",
        }

        result = await manager.transfer(target_id, context_data)

        assert result is True

    # -------------------------------------------------------------------------
    # Custom Transformer Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_custom_transformer_called(self, manager, sample_context):
        """Test that custom transformers are called."""
        def custom_transformer(ctx):
            ctx.metadata["transformed"] = True
            return ctx

        manager.register_transformer(custom_transformer)

        transformed = await manager.transform_context(sample_context)

        assert transformed.metadata.get("transformed") is True

    @pytest.mark.asyncio
    async def test_multiple_transformers(self, manager, sample_context):
        """Test multiple transformers in sequence."""
        def add_flag1(ctx):
            ctx.metadata["flag1"] = True
            return ctx

        def add_flag2(ctx):
            ctx.metadata["flag2"] = True
            return ctx

        manager.register_transformer(add_flag1)
        manager.register_transformer(add_flag2)

        transformed = await manager.transform_context(sample_context)

        assert transformed.metadata.get("flag1") is True
        assert transformed.metadata.get("flag2") is True

    # -------------------------------------------------------------------------
    # Checksum Tests
    # -------------------------------------------------------------------------

    def test_checksum_calculation(self, manager):
        """Test checksum calculation is consistent."""
        context1 = TransferContext(
            task_id="task-001",
            task_state={"key": "value"},
        )
        context2 = TransferContext(
            task_id="task-001",
            task_state={"key": "value"},
        )

        checksum1 = manager._calculate_checksum(context1)
        checksum2 = manager._calculate_checksum(context2)

        assert checksum1 == checksum2

    def test_checksum_changes_with_content(self, manager):
        """Test checksum changes when content changes."""
        context1 = TransferContext(
            task_id="task-001",
            task_state={"key": "value1"},
        )
        context2 = TransferContext(
            task_id="task-001",
            task_state={"key": "value2"},
        )

        checksum1 = manager._calculate_checksum(context1)
        checksum2 = manager._calculate_checksum(context2)

        assert checksum1 != checksum2

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_context_validation(self, manager):
        """Test validation of minimal valid context."""
        context = TransferContext(
            task_id="task-001",
            task_state={"minimal": True},
        )

        result = await manager.validate_context(context)

        assert result is True

    @pytest.mark.asyncio
    async def test_rule_with_required_missing_field(self, manager, sample_context):
        """Test transformation rule with missing required field."""
        rules = [
            TransformationRule(
                source_field="nonexistent",
                target_field="new_field",
                required=True,
            )
        ]

        with pytest.raises(TransferValidationError):
            await manager.transform_context(sample_context, rules=rules)
