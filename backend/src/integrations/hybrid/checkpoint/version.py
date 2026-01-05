# =============================================================================
# IPA Platform - Checkpoint Version Migration
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Version migration utilities for HybridCheckpoint format changes.
# Supports forward migration from older versions to current version.
#
# Version History:
#   - v1: Initial version (Sprint 52-54) - separate MAF and Claude checkpoints
#   - v2: Unified version (Sprint 57) - combined HybridCheckpoint
#
# Dependencies:
#   - HybridCheckpoint models (models)
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from .models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    CompressionAlgorithm,
    HybridCheckpoint,
    MAFCheckpointState,
    RiskSnapshot,
)


# =============================================================================
# Version Constants
# =============================================================================


class CheckpointVersion(int, Enum):
    """
    Checkpoint format versions.

    Attributes:
        V1: Initial version - separate checkpoints
        V2: Current version - unified HybridCheckpoint
    """

    V1 = 1
    V2 = 2


# Current version
CURRENT_VERSION = CheckpointVersion.V2


# =============================================================================
# Migration Result
# =============================================================================


@dataclass
class MigrationResult:
    """
    Result of a version migration operation.

    Attributes:
        success: Whether migration was successful
        original_version: Version before migration
        target_version: Version after migration
        migrated_data: Migrated checkpoint data
        warnings: List of migration warnings
        error: Error message if failed
        migration_time_ms: Time taken for migration
    """

    success: bool
    original_version: int
    target_version: int
    migrated_data: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    migration_time_ms: int = 0

    def has_warnings(self) -> bool:
        """Check if migration has warnings."""
        return len(self.warnings) > 0


# =============================================================================
# Version Migrators
# =============================================================================


class VersionMigrator(ABC):
    """
    Abstract base class for version migrators.

    Each migrator handles migration from one version to the next.
    """

    @property
    @abstractmethod
    def from_version(self) -> int:
        """Source version."""
        pass

    @property
    @abstractmethod
    def to_version(self) -> int:
        """Target version."""
        pass

    @abstractmethod
    def migrate(self, data: Dict[str, Any]) -> MigrationResult:
        """
        Migrate data from source to target version.

        Args:
            data: Checkpoint data in source version format

        Returns:
            MigrationResult with migrated data
        """
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate data for migration.

        Args:
            data: Data to validate

        Returns:
            List of validation errors (empty if valid)
        """
        pass


class V1ToV2Migrator(VersionMigrator):
    """
    Migrator from v1 to v2 checkpoint format.

    v1 had separate MAF and Claude checkpoints with different structures.
    v2 unifies them into HybridCheckpoint with improved fields.

    Changes in v2:
        - Added checkpoint_type field
        - Added risk_snapshot field
        - Added sync_version and sync_status
        - Unified checkpoint_id format
        - Added mode_history tracking
    """

    @property
    def from_version(self) -> int:
        return 1

    @property
    def to_version(self) -> int:
        return 2

    def migrate(self, data: Dict[str, Any]) -> MigrationResult:
        """
        Migrate v1 checkpoint to v2 format.

        Args:
            data: v1 checkpoint data

        Returns:
            MigrationResult with v2 format data
        """
        start_time = datetime.utcnow()
        warnings: List[str] = []

        try:
            # Validate input
            errors = self.validate(data)
            if errors:
                return MigrationResult(
                    success=False,
                    original_version=1,
                    target_version=2,
                    error=f"Validation failed: {', '.join(errors)}",
                )

            # Create v2 structure
            migrated: Dict[str, Any] = {
                "version": 2,
                "checkpoint_id": data.get("checkpoint_id", data.get("id", "")),
                "session_id": data.get("session_id", ""),
                "status": data.get("status", "active"),
                "checkpoint_type": self._infer_checkpoint_type(data),
            }

            # Migrate MAF state
            if "maf_state" in data:
                migrated["maf_state"] = self._migrate_maf_state(data["maf_state"])
            elif "workflow_state" in data:
                # v1 might use "workflow_state" instead
                migrated["maf_state"] = self._migrate_maf_state(data["workflow_state"])
                warnings.append("Migrated 'workflow_state' to 'maf_state'")

            # Migrate Claude state
            if "claude_state" in data:
                migrated["claude_state"] = self._migrate_claude_state(data["claude_state"])
            elif "session_state" in data:
                # v1 might use "session_state" instead
                migrated["claude_state"] = self._migrate_claude_state(data["session_state"])
                warnings.append("Migrated 'session_state' to 'claude_state'")

            # Migrate execution mode
            migrated["execution_mode"] = data.get("execution_mode", "chat")
            migrated["mode_history"] = data.get("mode_history", [])

            # Add new v2 fields with defaults
            migrated["risk_snapshot"] = data.get("risk_snapshot", None)
            migrated["sync_version"] = data.get("sync_version", 0)
            migrated["sync_status"] = data.get("sync_status", "synced")
            migrated["last_sync_at"] = data.get("last_sync_at", None)

            # Migrate compression info
            migrated["compressed"] = data.get("compressed", False)
            migrated["compression_algorithm"] = data.get("compression_algorithm", "none")
            migrated["checksum"] = data.get("checksum", None)

            # Migrate timestamps
            migrated["created_at"] = data.get("created_at", datetime.utcnow().isoformat())
            migrated["expires_at"] = data.get("expires_at", None)
            migrated["restored_at"] = data.get("restored_at", None)

            # Migrate metadata
            migrated["metadata"] = self._migrate_metadata(data.get("metadata", {}))

            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return MigrationResult(
                success=True,
                original_version=1,
                target_version=2,
                migrated_data=migrated,
                warnings=warnings,
                migration_time_ms=elapsed_ms,
            )

        except Exception as e:
            return MigrationResult(
                success=False,
                original_version=1,
                target_version=2,
                error=str(e),
            )

    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate v1 data for migration."""
        errors = []

        # Check version
        version = data.get("version", 1)
        if version != 1:
            errors.append(f"Expected version 1, got {version}")

        # Check required fields
        if not data.get("session_id") and not data.get("checkpoint_id"):
            errors.append("Missing session_id or checkpoint_id")

        return errors

    def _infer_checkpoint_type(self, data: Dict[str, Any]) -> str:
        """Infer checkpoint type from v1 data."""
        # v1 might have a "type" field
        if "type" in data:
            return data["type"]

        # Infer from context
        if data.get("is_mode_switch"):
            return "mode_switch"
        if data.get("requires_approval") or data.get("pending_approval"):
            return "hitl"
        if data.get("is_recovery"):
            return "recovery"

        return "auto"

    def _migrate_maf_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate MAF state from v1 to v2."""
        return {
            "workflow_id": state.get("workflow_id", ""),
            "workflow_name": state.get("workflow_name", state.get("name", "")),
            "current_step": state.get("current_step", state.get("step", 0)),
            "total_steps": state.get("total_steps", state.get("steps", 0)),
            "agent_states": state.get("agent_states", state.get("agents", {})),
            "variables": state.get("variables", state.get("context", {})),
            "pending_approvals": state.get("pending_approvals", []),
            "execution_log": state.get("execution_log", state.get("log", [])),
            "checkpoint_data": state.get("checkpoint_data", {}),
            "metadata": state.get("metadata", {}),
            "created_at": state.get("created_at", datetime.utcnow().isoformat()),
        }

    def _migrate_claude_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate Claude state from v1 to v2."""
        return {
            "session_id": state.get("session_id", ""),
            "conversation_history": state.get(
                "conversation_history", state.get("messages", [])
            ),
            "tool_call_history": state.get(
                "tool_call_history", state.get("tool_calls", [])
            ),
            "context_variables": state.get(
                "context_variables", state.get("context", {})
            ),
            "system_prompt_hash": state.get("system_prompt_hash", ""),
            "active_hooks": state.get("active_hooks", []),
            "mcp_states": state.get("mcp_states", {}),
            "pending_tool_calls": state.get("pending_tool_calls", []),
            "metadata": state.get("metadata", {}),
            "created_at": state.get("created_at", datetime.utcnow().isoformat()),
        }

    def _migrate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate metadata with version tracking."""
        migrated = metadata.copy()
        migrated["_migration"] = {
            "from_version": 1,
            "to_version": 2,
            "migrated_at": datetime.utcnow().isoformat(),
        }
        return migrated


# =============================================================================
# Checkpoint Version Migrator (Main Class)
# =============================================================================


class CheckpointVersionMigrator:
    """
    Main version migrator for HybridCheckpoint.

    Manages version detection and multi-step migration from any
    supported version to the current version.

    Example:
        >>> migrator = CheckpointVersionMigrator()
        >>> result = migrator.migrate_to_current(old_checkpoint_data)
        >>> if result.success:
        ...     checkpoint = HybridCheckpoint.from_dict(result.migrated_data)
    """

    # Registry of version migrators
    _migrators: Dict[int, VersionMigrator] = {}

    def __init__(self):
        """Initialize migrator with registered version migrators."""
        self._register_migrators()

    def _register_migrators(self) -> None:
        """Register all version migrators."""
        self._migrators = {
            1: V1ToV2Migrator(),
        }

    def get_version(self, data: Dict[str, Any]) -> int:
        """
        Detect version of checkpoint data.

        Args:
            data: Checkpoint data

        Returns:
            Detected version number
        """
        # Explicit version field
        if "version" in data:
            return data["version"]

        # Heuristic detection for v1
        if self._looks_like_v1(data):
            return 1

        # Default to current version
        return CURRENT_VERSION.value

    def _looks_like_v1(self, data: Dict[str, Any]) -> bool:
        """Check if data looks like v1 format."""
        # v1 indicators
        v1_fields = ["workflow_state", "session_state", "is_mode_switch"]
        return any(field in data for field in v1_fields)

    def needs_migration(self, data: Dict[str, Any]) -> bool:
        """
        Check if data needs migration.

        Args:
            data: Checkpoint data

        Returns:
            True if migration is needed
        """
        version = self.get_version(data)
        return version < CURRENT_VERSION.value

    def migrate_to_current(self, data: Dict[str, Any]) -> MigrationResult:
        """
        Migrate checkpoint data to current version.

        Performs multi-step migration if needed (e.g., v1 -> v2 -> v3).

        Args:
            data: Checkpoint data in any supported version

        Returns:
            MigrationResult with current version data

        Example:
            >>> result = migrator.migrate_to_current(v1_data)
            >>> if result.success:
            ...     print(f"Migrated from v{result.original_version}")
        """
        current_version = self.get_version(data)
        target_version = CURRENT_VERSION.value

        if current_version == target_version:
            return MigrationResult(
                success=True,
                original_version=current_version,
                target_version=target_version,
                migrated_data=data,
            )

        if current_version > target_version:
            return MigrationResult(
                success=False,
                original_version=current_version,
                target_version=target_version,
                error=f"Cannot downgrade from version {current_version} to {target_version}",
            )

        # Multi-step migration
        all_warnings: List[str] = []
        current_data = data
        start_version = current_version

        while current_version < target_version:
            migrator = self._migrators.get(current_version)
            if not migrator:
                return MigrationResult(
                    success=False,
                    original_version=start_version,
                    target_version=target_version,
                    error=f"No migrator available for version {current_version}",
                )

            result = migrator.migrate(current_data)
            if not result.success:
                return MigrationResult(
                    success=False,
                    original_version=start_version,
                    target_version=target_version,
                    error=f"Migration from v{current_version} failed: {result.error}",
                )

            all_warnings.extend(result.warnings)
            current_data = result.migrated_data
            current_version = result.target_version

        return MigrationResult(
            success=True,
            original_version=start_version,
            target_version=target_version,
            migrated_data=current_data,
            warnings=all_warnings,
        )

    def migrate_checkpoint(self, checkpoint_data: Dict[str, Any]) -> HybridCheckpoint:
        """
        Migrate and create HybridCheckpoint from data.

        Convenience method that combines migration and deserialization.

        Args:
            checkpoint_data: Checkpoint data in any supported version

        Returns:
            HybridCheckpoint instance in current version

        Raises:
            ValueError: If migration fails
        """
        result = self.migrate_to_current(checkpoint_data)
        if not result.success:
            raise ValueError(f"Migration failed: {result.error}")

        return HybridCheckpoint.from_dict(result.migrated_data)

    def get_supported_versions(self) -> List[int]:
        """
        Get list of supported versions for migration.

        Returns:
            List of version numbers that can be migrated
        """
        versions = list(self._migrators.keys())
        versions.append(CURRENT_VERSION.value)
        return sorted(set(versions))

    def validate_checkpoint_data(
        self, data: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate checkpoint data structure.

        Args:
            data: Checkpoint data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        version = self.get_version(data)

        if version in self._migrators:
            # Validate using version-specific migrator
            migrator = self._migrators[version]
            errors = migrator.validate(data)
        elif version == CURRENT_VERSION.value:
            # Validate current version structure
            errors = self._validate_current_version(data)

        return len(errors) == 0, errors

    def _validate_current_version(self, data: Dict[str, Any]) -> List[str]:
        """Validate current version data structure."""
        errors = []

        # Required fields
        if not data.get("checkpoint_id") and not data.get("session_id"):
            errors.append("Missing checkpoint_id or session_id")

        # Validate status if present
        if "status" in data:
            valid_statuses = [s.value for s in CheckpointStatus]
            if data["status"] not in valid_statuses:
                errors.append(f"Invalid status: {data['status']}")

        # Validate checkpoint_type if present
        if "checkpoint_type" in data:
            valid_types = [t.value for t in CheckpointType]
            if data["checkpoint_type"] not in valid_types:
                errors.append(f"Invalid checkpoint_type: {data['checkpoint_type']}")

        return errors
