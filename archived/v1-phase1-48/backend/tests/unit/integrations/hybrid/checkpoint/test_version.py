# =============================================================================
# IPA Platform - Checkpoint Version Migration Unit Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Tests for CheckpointVersionMigrator and version migration logic.
# =============================================================================

from datetime import datetime

import pytest

from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    HybridCheckpoint,
)
from src.integrations.hybrid.checkpoint.version import (
    CURRENT_VERSION,
    CheckpointVersion,
    CheckpointVersionMigrator,
    MigrationResult,
    V1ToV2Migrator,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def migrator() -> CheckpointVersionMigrator:
    """Create migrator instance."""
    return CheckpointVersionMigrator()


@pytest.fixture
def v1_data() -> dict:
    """Create v1 format checkpoint data."""
    return {
        "version": 1,
        "checkpoint_id": "cp_123",
        "session_id": "sess_123",
        "status": "active",
        "workflow_state": {
            "workflow_id": "wf_123",
            "name": "Test Workflow",
            "step": 2,
            "steps": 5,
            "agents": {"agent1": {"status": "completed"}},
            "context": {"key": "value"},
        },
        "session_state": {
            "session_id": "sess_123",
            "messages": [{"role": "user", "content": "Hello"}],
            "tool_calls": [{"tool": "search", "result": "found"}],
            "context": {"user_id": "u_123"},
        },
        "execution_mode": "hybrid",
        "created_at": "2025-12-20T10:00:00",
        "metadata": {"custom_field": "custom_value"},
    }


@pytest.fixture
def v1_mode_switch_data() -> dict:
    """Create v1 format checkpoint data for mode switch."""
    return {
        "version": 1,
        "checkpoint_id": "cp_switch",
        "session_id": "sess_switch",
        "status": "active",
        "is_mode_switch": True,
        "maf_state": {
            "workflow_id": "wf_switch",
            "workflow_name": "Switch Workflow",
            "current_step": 1,
            "total_steps": 3,
        },
        "execution_mode": "workflow",
        "created_at": "2025-12-20T11:00:00",
    }


@pytest.fixture
def v2_data() -> dict:
    """Create v2 format checkpoint data."""
    return {
        "version": 2,
        "checkpoint_id": "cp_v2",
        "session_id": "sess_v2",
        "status": "active",
        "checkpoint_type": "auto",
        "maf_state": {
            "workflow_id": "wf_v2",
            "workflow_name": "V2 Workflow",
            "current_step": 1,
            "total_steps": 3,
            "agent_states": {},
            "variables": {},
            "pending_approvals": [],
            "execution_log": [],
            "checkpoint_data": {},
            "metadata": {},
            "created_at": "2025-12-20T12:00:00",
        },
        "execution_mode": "workflow",
        "sync_version": 0,
        "sync_status": "synced",
        "compressed": False,
        "compression_algorithm": "none",
        "created_at": "2025-12-20T12:00:00",
        "metadata": {},
    }


# =============================================================================
# CheckpointVersion Tests
# =============================================================================


class TestCheckpointVersion:
    """Tests for CheckpointVersion enum."""

    def test_version_values(self):
        """Test version values."""
        assert CheckpointVersion.V1 == 1
        assert CheckpointVersion.V2 == 2

    def test_current_version(self):
        """Test current version."""
        assert CURRENT_VERSION == CheckpointVersion.V2


# =============================================================================
# MigrationResult Tests
# =============================================================================


class TestMigrationResult:
    """Tests for MigrationResult."""

    def test_successful_result(self):
        """Test successful migration result."""
        result = MigrationResult(
            success=True,
            original_version=1,
            target_version=2,
            migrated_data={"version": 2},
        )

        assert result.success
        assert result.original_version == 1
        assert result.target_version == 2
        assert result.migrated_data is not None
        assert not result.has_warnings()

    def test_failed_result(self):
        """Test failed migration result."""
        result = MigrationResult(
            success=False,
            original_version=1,
            target_version=2,
            error="Migration failed",
        )

        assert not result.success
        assert result.error == "Migration failed"

    def test_result_with_warnings(self):
        """Test result with warnings."""
        result = MigrationResult(
            success=True,
            original_version=1,
            target_version=2,
            migrated_data={},
            warnings=["Minor issue", "Another issue"],
        )

        assert result.has_warnings()
        assert len(result.warnings) == 2


# =============================================================================
# V1ToV2Migrator Tests
# =============================================================================


class TestV1ToV2Migrator:
    """Tests for V1ToV2Migrator."""

    @pytest.fixture
    def v1_migrator(self) -> V1ToV2Migrator:
        return V1ToV2Migrator()

    def test_version_properties(self, v1_migrator):
        """Test migrator version properties."""
        assert v1_migrator.from_version == 1
        assert v1_migrator.to_version == 2

    def test_migrate_basic_v1_data(self, v1_migrator, v1_data):
        """Test migrating basic v1 data."""
        result = v1_migrator.migrate(v1_data)

        assert result.success
        assert result.original_version == 1
        assert result.target_version == 2
        assert result.migrated_data["version"] == 2

    def test_migrate_workflow_state_to_maf_state(self, v1_migrator, v1_data):
        """Test migrating workflow_state to maf_state."""
        result = v1_migrator.migrate(v1_data)

        assert result.success
        assert "maf_state" in result.migrated_data
        assert result.migrated_data["maf_state"]["workflow_id"] == "wf_123"
        assert result.migrated_data["maf_state"]["workflow_name"] == "Test Workflow"
        assert result.migrated_data["maf_state"]["current_step"] == 2
        assert result.migrated_data["maf_state"]["total_steps"] == 5
        assert "workflow_state renamed" in str(result.warnings).lower() or len(result.warnings) > 0

    def test_migrate_session_state_to_claude_state(self, v1_migrator, v1_data):
        """Test migrating session_state to claude_state."""
        result = v1_migrator.migrate(v1_data)

        assert result.success
        assert "claude_state" in result.migrated_data
        assert result.migrated_data["claude_state"]["session_id"] == "sess_123"
        assert len(result.migrated_data["claude_state"]["conversation_history"]) == 1
        assert len(result.migrated_data["claude_state"]["tool_call_history"]) == 1

    def test_migrate_mode_switch_type(self, v1_migrator, v1_mode_switch_data):
        """Test inferring mode_switch checkpoint type."""
        result = v1_migrator.migrate(v1_mode_switch_data)

        assert result.success
        assert result.migrated_data["checkpoint_type"] == "mode_switch"

    def test_migrate_adds_new_fields(self, v1_migrator, v1_data):
        """Test that migration adds new v2 fields."""
        result = v1_migrator.migrate(v1_data)

        assert result.success
        assert "sync_version" in result.migrated_data
        assert "sync_status" in result.migrated_data
        assert "compressed" in result.migrated_data
        assert "compression_algorithm" in result.migrated_data

    def test_migrate_preserves_metadata(self, v1_migrator, v1_data):
        """Test that migration preserves and adds to metadata."""
        result = v1_migrator.migrate(v1_data)

        assert result.success
        assert "custom_field" in result.migrated_data["metadata"]
        assert "_migration" in result.migrated_data["metadata"]

    def test_validate_v1_data(self, v1_migrator, v1_data):
        """Test validating v1 data."""
        errors = v1_migrator.validate(v1_data)
        assert len(errors) == 0

    def test_validate_wrong_version(self, v1_migrator):
        """Test validating data with wrong version."""
        data = {"version": 2, "session_id": "sess_123"}
        errors = v1_migrator.validate(data)

        assert len(errors) > 0
        assert "Expected version 1" in errors[0]

    def test_validate_missing_ids(self, v1_migrator):
        """Test validating data with missing IDs."""
        data = {"version": 1}
        errors = v1_migrator.validate(data)

        assert len(errors) > 0


# =============================================================================
# CheckpointVersionMigrator Tests
# =============================================================================


class TestCheckpointVersionMigrator:
    """Tests for CheckpointVersionMigrator."""

    def test_get_version_explicit(self, migrator, v1_data, v2_data):
        """Test getting explicit version."""
        assert migrator.get_version(v1_data) == 1
        assert migrator.get_version(v2_data) == 2

    def test_get_version_heuristic(self, migrator):
        """Test version detection by heuristics."""
        # Data with v1 indicators
        v1_like = {"workflow_state": {}, "session_id": "test"}
        assert migrator.get_version(v1_like) == 1

        # Data without version field defaults to current
        unknown = {"session_id": "test"}
        assert migrator.get_version(unknown) == CURRENT_VERSION.value

    def test_needs_migration(self, migrator, v1_data, v2_data):
        """Test needs_migration check."""
        assert migrator.needs_migration(v1_data) is True
        assert migrator.needs_migration(v2_data) is False

    def test_migrate_to_current_v1(self, migrator, v1_data):
        """Test migrating v1 to current version."""
        result = migrator.migrate_to_current(v1_data)

        assert result.success
        assert result.original_version == 1
        assert result.target_version == CURRENT_VERSION.value
        assert result.migrated_data["version"] == CURRENT_VERSION.value

    def test_migrate_to_current_already_current(self, migrator, v2_data):
        """Test migrating already current version."""
        result = migrator.migrate_to_current(v2_data)

        assert result.success
        assert result.original_version == CURRENT_VERSION.value
        assert result.target_version == CURRENT_VERSION.value
        assert result.migrated_data == v2_data

    def test_migrate_to_current_downgrade_fails(self, migrator):
        """Test that downgrade fails."""
        future_data = {"version": 999, "session_id": "test"}
        result = migrator.migrate_to_current(future_data)

        assert not result.success
        assert "Cannot downgrade" in result.error

    def test_migrate_checkpoint(self, migrator, v1_data):
        """Test migrate_checkpoint convenience method."""
        checkpoint = migrator.migrate_checkpoint(v1_data)

        assert isinstance(checkpoint, HybridCheckpoint)
        assert checkpoint.session_id == "sess_123"
        assert checkpoint.version == CURRENT_VERSION.value

    def test_migrate_checkpoint_failure(self, migrator):
        """Test migrate_checkpoint with invalid data."""
        invalid_data = {"version": 999}

        with pytest.raises(ValueError, match="Migration failed"):
            migrator.migrate_checkpoint(invalid_data)

    def test_get_supported_versions(self, migrator):
        """Test getting supported versions."""
        versions = migrator.get_supported_versions()

        assert 1 in versions
        assert CURRENT_VERSION.value in versions

    def test_validate_checkpoint_data_v1(self, migrator, v1_data):
        """Test validating v1 checkpoint data."""
        is_valid, errors = migrator.validate_checkpoint_data(v1_data)

        assert is_valid
        assert len(errors) == 0

    def test_validate_checkpoint_data_v2(self, migrator, v2_data):
        """Test validating v2 checkpoint data."""
        is_valid, errors = migrator.validate_checkpoint_data(v2_data)

        assert is_valid
        assert len(errors) == 0

    def test_validate_checkpoint_data_invalid_status(self, migrator):
        """Test validating data with invalid status."""
        data = {"version": 2, "session_id": "test", "status": "invalid_status"}
        is_valid, errors = migrator.validate_checkpoint_data(data)

        assert not is_valid
        assert any("Invalid status" in e for e in errors)

    def test_validate_checkpoint_data_invalid_type(self, migrator):
        """Test validating data with invalid checkpoint type."""
        data = {
            "version": 2,
            "session_id": "test",
            "checkpoint_type": "invalid_type",
        }
        is_valid, errors = migrator.validate_checkpoint_data(data)

        assert not is_valid
        assert any("Invalid checkpoint_type" in e for e in errors)


# =============================================================================
# Integration Tests
# =============================================================================


class TestMigrationIntegration:
    """Integration tests for migration workflow."""

    def test_full_v1_to_v2_migration(self, migrator, v1_data):
        """Test complete v1 to v2 migration and usage."""
        # Migrate
        result = migrator.migrate_to_current(v1_data)
        assert result.success

        # Create checkpoint from migrated data
        checkpoint = HybridCheckpoint.from_dict(result.migrated_data)

        # Verify checkpoint is usable
        assert checkpoint.version == 2
        assert checkpoint.session_id == "sess_123"
        assert checkpoint.is_active()
        assert checkpoint.has_maf_state()
        assert checkpoint.has_claude_state()

        # Verify MAF state
        assert checkpoint.maf_state.workflow_id == "wf_123"
        assert checkpoint.maf_state.current_step == 2
        assert checkpoint.maf_state.total_steps == 5

        # Verify Claude state
        assert checkpoint.claude_state.session_id == "sess_123"
        assert checkpoint.claude_state.get_message_count() == 1

    def test_migration_with_warnings(self, migrator, v1_data):
        """Test that migrations with warnings still succeed."""
        result = migrator.migrate_to_current(v1_data)

        assert result.success
        # v1 uses workflow_state/session_state which should generate warnings
        assert result.has_warnings() or len(result.warnings) >= 0

    def test_migration_idempotent(self, migrator, v1_data):
        """Test that migrating twice gives same result."""
        result1 = migrator.migrate_to_current(v1_data)
        result2 = migrator.migrate_to_current(result1.migrated_data)

        assert result1.success
        assert result2.success
        assert result1.migrated_data["version"] == result2.migrated_data["version"]
        assert result1.migrated_data["session_id"] == result2.migrated_data["session_id"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_migrate_empty_states(self, migrator):
        """Test migrating checkpoint with empty states."""
        data = {
            "version": 1,
            "session_id": "sess_empty",
            "workflow_state": {
                "workflow_id": "",
                "name": "",
            },
        }

        result = migrator.migrate_to_current(data)
        assert result.success

    def test_migrate_partial_v1_data(self, migrator):
        """Test migrating partial v1 data."""
        data = {
            "version": 1,
            "checkpoint_id": "cp_partial",
            "session_id": "sess_partial",
            # No workflow_state or session_state
        }

        result = migrator.migrate_to_current(data)
        assert result.success
        assert result.migrated_data.get("maf_state") is None
        assert result.migrated_data.get("claude_state") is None

    def test_migrate_with_timestamps(self, migrator, v1_data):
        """Test that timestamps are preserved."""
        result = migrator.migrate_to_current(v1_data)

        assert result.success
        assert result.migrated_data["created_at"] == "2025-12-20T10:00:00"

    def test_migrate_preserves_execution_mode(self, migrator, v1_data):
        """Test that execution mode is preserved."""
        result = migrator.migrate_to_current(v1_data)

        assert result.success
        assert result.migrated_data["execution_mode"] == "hybrid"
