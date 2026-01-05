# =============================================================================
# IPA Platform - Mode Switcher
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 56: Mode Switcher & HITL
#
# Core ModeSwitcher class for dynamic mode switching between
# Workflow Mode (MAF) and Chat Mode (Claude SDK).
#
# Key Features:
#   - Trigger-based mode switching detection
#   - State migration between modes
#   - Rollback support for failed switches
#   - Checkpoint management for recovery
#
# Dependencies:
#   - SwitchTrigger, SwitchResult (src.integrations.hybrid.switching.models)
#   - HybridContext (src.integrations.hybrid.context.models)
#   - ContextBridge (src.integrations.hybrid.context.bridge)
# =============================================================================

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Union
from uuid import uuid4

from src.integrations.hybrid.intent.models import ExecutionMode

from .models import (
    ExecutionState,
    MigratedState,
    MigrationDirection,
    ModeTransition,
    SwitchCheckpoint,
    SwitchConfig,
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
    SwitchValidation,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols
# =============================================================================


class TriggerDetectorProtocol(Protocol):
    """Protocol for trigger detectors."""

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """Detect if mode switch is needed."""
        ...


class StateMigratorProtocol(Protocol):
    """Protocol for state migrator."""

    async def migrate(
        self,
        context: Any,  # HybridContext
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """Migrate state between modes."""
        ...


class CheckpointStorageProtocol(Protocol):
    """Protocol for checkpoint storage."""

    async def save_checkpoint(self, checkpoint: SwitchCheckpoint) -> str:
        """Save a checkpoint."""
        ...

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[SwitchCheckpoint]:
        """Get a checkpoint by ID."""
        ...

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        ...


class ContextBridgeProtocol(Protocol):
    """Protocol for context bridge."""

    async def get_context(self, session_id: str) -> Optional[Any]:
        """Get hybrid context for session."""
        ...

    async def update_context(self, session_id: str, context: Any) -> bool:
        """Update hybrid context."""
        ...


# =============================================================================
# Metrics
# =============================================================================


@dataclass
class SwitcherMetrics:
    """Metrics for ModeSwitcher performance tracking."""

    total_switches: int = 0
    successful_switches: int = 0
    failed_switches: int = 0
    rollbacks: int = 0
    switches_by_trigger: Dict[str, int] = field(default_factory=dict)
    switches_by_direction: Dict[str, int] = field(default_factory=dict)
    average_switch_time_ms: float = 0.0
    last_switch_at: Optional[datetime] = None

    def record_switch(
        self,
        success: bool,
        trigger_type: str,
        direction: str,
        time_ms: int,
    ) -> None:
        """Record a switch operation."""
        self.total_switches += 1
        if success:
            self.successful_switches += 1
        else:
            self.failed_switches += 1

        self.switches_by_trigger[trigger_type] = (
            self.switches_by_trigger.get(trigger_type, 0) + 1
        )
        self.switches_by_direction[direction] = (
            self.switches_by_direction.get(direction, 0) + 1
        )

        # Update average
        total_time = self.average_switch_time_ms * (self.total_switches - 1)
        self.average_switch_time_ms = (total_time + time_ms) / self.total_switches
        self.last_switch_at = datetime.utcnow()

    def record_rollback(self) -> None:
        """Record a rollback operation."""
        self.rollbacks += 1

    def get_success_rate(self) -> float:
        """Get switch success rate."""
        if self.total_switches == 0:
            return 0.0
        return self.successful_switches / self.total_switches

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_switches": self.total_switches,
            "successful_switches": self.successful_switches,
            "failed_switches": self.failed_switches,
            "rollbacks": self.rollbacks,
            "switches_by_trigger": self.switches_by_trigger,
            "switches_by_direction": self.switches_by_direction,
            "average_switch_time_ms": self.average_switch_time_ms,
            "success_rate": self.get_success_rate(),
            "last_switch_at": self.last_switch_at.isoformat() if self.last_switch_at else None,
        }


# =============================================================================
# In-Memory Checkpoint Storage (Default Implementation)
# =============================================================================


class InMemoryCheckpointStorage:
    """In-memory checkpoint storage for development/testing."""

    def __init__(self) -> None:
        self._checkpoints: Dict[str, SwitchCheckpoint] = {}

    async def save_checkpoint(self, checkpoint: SwitchCheckpoint) -> str:
        """Save a checkpoint."""
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint.checkpoint_id

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[SwitchCheckpoint]:
        """Get a checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all checkpoints."""
        self._checkpoints.clear()

    async def list_checkpoints(self, session_id: str) -> List[SwitchCheckpoint]:
        """List all checkpoints for a session."""
        return [
            cp for cp in self._checkpoints.values()
            if cp.context_snapshot.get("session_id") == session_id
        ]

    async def get_latest_checkpoint(self, session_id: str) -> Optional[SwitchCheckpoint]:
        """Get the most recent checkpoint for a session."""
        session_checkpoints = await self.list_checkpoints(session_id)
        if not session_checkpoints:
            return None
        return max(session_checkpoints, key=lambda cp: cp.created_at)


# =============================================================================
# ModeSwitcher Main Class
# =============================================================================


class ModeSwitcher:
    """
    Core ModeSwitcher for dynamic mode switching.

    Manages the transition between Workflow Mode (MAF) and Chat Mode (Claude SDK),
    including trigger detection, state migration, and rollback support.

    Attributes:
        config: Switch configuration
        trigger_detectors: List of trigger detectors
        state_migrator: State migrator for mode transitions
        checkpoint_storage: Storage for rollback checkpoints
        context_bridge: Bridge for context management
        metrics: Switcher performance metrics

    Example:
        >>> switcher = ModeSwitcher(
        ...     config=SwitchConfig(),
        ...     trigger_detectors=[ComplexityTriggerDetector()],
        ...     state_migrator=StateMigrator(),
        ... )
        >>> trigger = await switcher.should_switch(mode, state, input)
        >>> if trigger:
        ...     result = await switcher.execute_switch(trigger, context)
    """

    def __init__(
        self,
        config: Optional[SwitchConfig] = None,
        trigger_detectors: Optional[List[TriggerDetectorProtocol]] = None,
        state_migrator: Optional[StateMigratorProtocol] = None,
        checkpoint_storage: Optional[CheckpointStorageProtocol] = None,
        context_bridge: Optional[ContextBridgeProtocol] = None,
    ) -> None:
        """
        Initialize ModeSwitcher.

        Args:
            config: Switch configuration
            trigger_detectors: List of trigger detectors
            state_migrator: State migrator
            checkpoint_storage: Checkpoint storage
            context_bridge: Context bridge
        """
        self.config = config or SwitchConfig()
        self.trigger_detectors = trigger_detectors or []
        self.state_migrator = state_migrator
        self.checkpoint_storage = checkpoint_storage or InMemoryCheckpointStorage()
        self.context_bridge = context_bridge
        self.metrics = SwitcherMetrics()
        self._transition_history: List[ModeTransition] = []

        logger.info(
            f"ModeSwitcher initialized with {len(self.trigger_detectors)} detectors"
        )

    # =========================================================================
    # Trigger Detection
    # =========================================================================

    async def should_switch(
        self,
        current_mode: ExecutionMode,
        current_state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        """
        Check if mode switch is needed.

        Evaluates all trigger detectors in order:
        1. User explicit request
        2. Failure recovery
        3. Resource constraints
        4. Complexity change

        Args:
            current_mode: Current execution mode
            current_state: Current execution state
            new_input: New user input

        Returns:
            SwitchTrigger if switch is needed, None otherwise
        """
        if not self.config.enable_auto_switch:
            logger.debug("Auto-switch disabled")
            return None

        for detector in self.trigger_detectors:
            try:
                trigger = await detector.detect(current_mode, current_state, new_input)
                if trigger and trigger.is_high_confidence(self.config.complexity_threshold):
                    logger.info(
                        f"Switch trigger detected: {trigger.trigger_type.value} "
                        f"({trigger.source_mode} -> {trigger.target_mode})"
                    )
                    return trigger
            except Exception as e:
                logger.warning(f"Trigger detector failed: {e}")
                continue

        return None

    # =========================================================================
    # Switch Execution
    # =========================================================================

    async def execute_switch(
        self,
        trigger: SwitchTrigger,
        context: Any,  # HybridContext
        session_id: Optional[str] = None,
    ) -> SwitchResult:
        """
        Execute mode switch.

        Steps:
        1. Create pre-switch checkpoint
        2. Migrate state to target mode
        3. Initialize target mode
        4. Validate switch
        5. Update context

        Args:
            trigger: Switch trigger
            context: Current hybrid context
            session_id: Optional session ID

        Returns:
            SwitchResult with switch outcome
        """
        start_time = time.time()
        switch_id = str(uuid4())

        logger.info(
            f"Executing switch {switch_id}: "
            f"{trigger.source_mode} -> {trigger.target_mode}"
        )

        try:
            # 1. Create checkpoint for rollback
            checkpoint = await self._create_switch_checkpoint(
                switch_id=switch_id,
                context=context,
                trigger=trigger,
            )

            # 2. Migrate state
            source_mode = ExecutionMode(trigger.source_mode)
            target_mode = ExecutionMode(trigger.target_mode)

            if self.state_migrator:
                migrated_state = await self.state_migrator.migrate(
                    context,
                    source_mode,
                    target_mode,
                )
            else:
                # Default migration with minimal state
                migrated_state = self._create_default_migrated_state(
                    source_mode, target_mode
                )

            # 3. Initialize target mode
            new_context = await self._initialize_target_mode(
                target_mode=target_mode,
                migrated_state=migrated_state,
                original_context=context,
            )

            # 4. Validate switch
            validation = await self._validate_switch(new_context, target_mode)
            if not validation.success:
                logger.warning(f"Switch validation failed: {validation.error}")
                await self.rollback_switch(checkpoint.checkpoint_id)
                return SwitchResult(
                    success=False,
                    switch_id=switch_id,
                    status=SwitchStatus.FAILED,
                    trigger=trigger,
                    validation=validation,
                    error=validation.error,
                    checkpoint_id=checkpoint.checkpoint_id,
                )

            # 5. Update context bridge
            if self.context_bridge and session_id:
                await self.context_bridge.update_context(session_id, new_context)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Record metrics
            direction = f"{trigger.source_mode}_to_{trigger.target_mode}"
            self.metrics.record_switch(
                success=True,
                trigger_type=trigger.trigger_type.value,
                direction=direction,
                time_ms=duration_ms,
            )

            # Record transition
            transition = ModeTransition(
                session_id=session_id or "",
                source_mode=trigger.source_mode,
                target_mode=trigger.target_mode,
                trigger=trigger,
            )

            result = SwitchResult(
                success=True,
                switch_id=switch_id,
                status=SwitchStatus.COMPLETED,
                trigger=trigger,
                new_mode=trigger.target_mode,
                migrated_state=migrated_state,
                checkpoint_id=checkpoint.checkpoint_id,
                validation=validation,
                switch_time_ms=duration_ms,
                completed_at=datetime.utcnow(),
            )

            transition.result = result
            self._transition_history.append(transition)

            logger.info(f"Switch {switch_id} completed in {duration_ms}ms")
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Switch {switch_id} failed: {e}", exc_info=True)

            # Record failed metrics
            direction = f"{trigger.source_mode}_to_{trigger.target_mode}"
            self.metrics.record_switch(
                success=False,
                trigger_type=trigger.trigger_type.value,
                direction=direction,
                time_ms=duration_ms,
            )

            return SwitchResult(
                success=False,
                switch_id=switch_id,
                status=SwitchStatus.FAILED,
                trigger=trigger,
                error=str(e),
                switch_time_ms=duration_ms,
                completed_at=datetime.utcnow(),
            )

    # =========================================================================
    # Rollback
    # =========================================================================

    async def rollback_switch(
        self,
        checkpoint_id_or_checkpoint: Union[str, SwitchCheckpoint],
    ) -> bool:
        """
        Rollback a failed mode switch.

        Restores the context to the state saved in the checkpoint.

        Args:
            checkpoint_id_or_checkpoint: Checkpoint ID or checkpoint object

        Returns:
            True if rollback succeeded, False otherwise
        """
        try:
            if isinstance(checkpoint_id_or_checkpoint, str):
                checkpoint = await self.checkpoint_storage.get_checkpoint(
                    checkpoint_id_or_checkpoint
                )
                if not checkpoint:
                    logger.error(f"Checkpoint not found: {checkpoint_id_or_checkpoint}")
                    return False
            else:
                checkpoint = checkpoint_id_or_checkpoint

            logger.info(f"Rolling back to checkpoint {checkpoint.checkpoint_id}")

            # Restore context from snapshot
            if self.context_bridge and checkpoint.context_snapshot:
                session_id = checkpoint.context_snapshot.get("session_id")
                if session_id:
                    await self.context_bridge.update_context(
                        session_id,
                        checkpoint.context_snapshot,
                    )

            # Record rollback
            self.metrics.record_rollback()

            # Record rollback transition
            transition = ModeTransition(
                session_id=checkpoint.context_snapshot.get("session_id", ""),
                source_mode=checkpoint.context_snapshot.get("current_mode", ""),
                target_mode=checkpoint.mode_before,
                rollback_of=checkpoint.switch_id,
                result=SwitchResult(
                    success=True,
                    status=SwitchStatus.ROLLED_BACK,
                ),
            )
            self._transition_history.append(transition)

            logger.info(f"Rollback completed for checkpoint {checkpoint.checkpoint_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return False

    # =========================================================================
    # Manual Switch
    # =========================================================================

    async def manual_switch(
        self,
        session_id: str,
        target_mode: ExecutionMode,
        reason: str = "Manual switch request",
        context: Optional[Any] = None,
    ) -> SwitchResult:
        """
        Manually trigger mode switch.

        Args:
            session_id: Session identifier
            target_mode: Target execution mode
            reason: Reason for manual switch
            context: Optional context (will be fetched if not provided)

        Returns:
            SwitchResult with switch outcome
        """
        # Get current context if not provided
        if context is None and self.context_bridge:
            context = await self.context_bridge.get_context(session_id)

        # Determine current mode
        current_mode = self._get_current_mode(context)

        # Create manual trigger
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.MANUAL,
            source_mode=current_mode.value,
            target_mode=target_mode.value,
            reason=reason,
            confidence=1.0,  # Manual triggers have full confidence
        )

        return await self.execute_switch(trigger, context, session_id)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _create_switch_checkpoint(
        self,
        switch_id: str,
        context: Any,
        trigger: SwitchTrigger,
    ) -> SwitchCheckpoint:
        """Create a checkpoint before switch for rollback support."""
        # Serialize context to snapshot
        if hasattr(context, "to_dict"):
            snapshot = context.to_dict()
        elif isinstance(context, dict):
            snapshot = context.copy()
        else:
            snapshot = {}

        checkpoint = SwitchCheckpoint(
            switch_id=switch_id,
            context_snapshot=snapshot,
            mode_before=trigger.source_mode,
        )

        await self.checkpoint_storage.save_checkpoint(checkpoint)
        logger.debug(f"Created checkpoint {checkpoint.checkpoint_id} for switch {switch_id}")

        return checkpoint

    async def _initialize_target_mode(
        self,
        target_mode: ExecutionMode,
        migrated_state: MigratedState,
        original_context: Any,
    ) -> Any:
        """Initialize the target mode with migrated state."""
        # This is a placeholder - actual implementation would
        # initialize MAF workflow or Claude session based on target mode
        logger.debug(f"Initializing target mode: {target_mode.value}")

        # Return modified context with new mode
        if hasattr(original_context, "to_dict"):
            new_context = original_context.to_dict()
        elif isinstance(original_context, dict):
            new_context = original_context.copy()
        else:
            new_context = {}

        new_context["current_mode"] = target_mode.value
        new_context["migrated_state"] = migrated_state.to_dict()

        return new_context

    async def _validate_switch(
        self,
        new_context: Any,
        target_mode: ExecutionMode,
    ) -> SwitchValidation:
        """Validate the mode switch."""
        checks_passed = []
        checks_failed = []
        warnings = []

        # Check context exists
        if new_context is not None:
            checks_passed.append("context_exists")
        else:
            checks_failed.append("context_exists")

        # Check mode is set
        if isinstance(new_context, dict):
            if new_context.get("current_mode") == target_mode.value:
                checks_passed.append("mode_set")
            else:
                checks_failed.append("mode_set")

            # Check migrated state
            if new_context.get("migrated_state"):
                checks_passed.append("state_migrated")
            else:
                warnings.append("No migrated state found")

        success = len(checks_failed) == 0
        status = ValidationStatus.VALID if success else ValidationStatus.INVALID
        if success and warnings:
            status = ValidationStatus.WARNING

        return SwitchValidation(
            status=status,
            success=success,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            error="; ".join(checks_failed) if checks_failed else None,
        )

    def _create_default_migrated_state(
        self,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """Create default migrated state when no migrator is available."""
        direction = self._get_migration_direction(source_mode, target_mode)
        return MigratedState(
            direction=direction,
            preserved_history=self.config.preserve_history,
            preserved_tool_results=self.config.preserve_tool_results,
            context_summary="Default migration (no custom migrator)",
        )

    def _get_migration_direction(
        self,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigrationDirection:
        """Get migration direction from source to target mode."""
        if source_mode == ExecutionMode.WORKFLOW_MODE:
            if target_mode == ExecutionMode.CHAT_MODE:
                return MigrationDirection.WORKFLOW_TO_CHAT
            elif target_mode == ExecutionMode.HYBRID_MODE:
                return MigrationDirection.WORKFLOW_TO_HYBRID
        elif source_mode == ExecutionMode.CHAT_MODE:
            if target_mode == ExecutionMode.WORKFLOW_MODE:
                return MigrationDirection.CHAT_TO_WORKFLOW
            elif target_mode == ExecutionMode.HYBRID_MODE:
                return MigrationDirection.CHAT_TO_HYBRID
        elif source_mode == ExecutionMode.HYBRID_MODE:
            if target_mode == ExecutionMode.WORKFLOW_MODE:
                return MigrationDirection.HYBRID_TO_WORKFLOW
            elif target_mode == ExecutionMode.CHAT_MODE:
                return MigrationDirection.HYBRID_TO_CHAT

        # Default
        return MigrationDirection.CHAT_TO_WORKFLOW

    def _get_current_mode(self, context: Any) -> ExecutionMode:
        """Get current execution mode from context."""
        if hasattr(context, "current_mode"):
            return ExecutionMode(context.current_mode)
        elif isinstance(context, dict) and "current_mode" in context:
            return ExecutionMode(context["current_mode"])
        return ExecutionMode.CHAT_MODE  # Default

    # =========================================================================
    # Detector Management
    # =========================================================================

    def register_detector(self, detector: TriggerDetectorProtocol) -> None:
        """Register a trigger detector."""
        self.trigger_detectors.append(detector)
        logger.info(f"Registered trigger detector: {type(detector).__name__}")

    def unregister_detector(self, detector: TriggerDetectorProtocol) -> None:
        """Unregister a trigger detector."""
        if detector in self.trigger_detectors:
            self.trigger_detectors.remove(detector)
            logger.info(f"Unregistered trigger detector: {type(detector).__name__}")

    # =========================================================================
    # Metrics and History
    # =========================================================================

    def get_metrics(self) -> SwitcherMetrics:
        """Get switcher metrics."""
        return self.metrics

    def get_transition_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ModeTransition]:
        """
        Get transition history.

        Args:
            session_id: Optional filter by session
            limit: Maximum number of transitions to return

        Returns:
            List of mode transitions
        """
        history = self._transition_history
        if session_id:
            history = [t for t in history if t.session_id == session_id]
        return history[-limit:]

    def clear_transition_history(self, session_id: Optional[str] = None) -> int:
        """
        Clear transition history.

        Args:
            session_id: Optional filter by session

        Returns:
            Number of transitions cleared
        """
        if session_id:
            before_count = len(self._transition_history)
            self._transition_history = [
                t for t in self._transition_history if t.session_id != session_id
            ]
            return before_count - len(self._transition_history)
        else:
            count = len(self._transition_history)
            self._transition_history = []
            return count

    def reset_metrics(self) -> None:
        """Reset switcher metrics."""
        self.metrics = SwitcherMetrics()
        logger.info("Switcher metrics reset")


# =============================================================================
# Factory Function
# =============================================================================


def create_mode_switcher(
    config: Optional[SwitchConfig] = None,
    trigger_detectors: Optional[List[TriggerDetectorProtocol]] = None,
    state_migrator: Optional[StateMigratorProtocol] = None,
    checkpoint_storage: Optional[CheckpointStorageProtocol] = None,
    context_bridge: Optional[ContextBridgeProtocol] = None,
) -> ModeSwitcher:
    """
    Factory function to create ModeSwitcher.

    Args:
        config: Switch configuration
        trigger_detectors: List of trigger detectors
        state_migrator: State migrator
        checkpoint_storage: Checkpoint storage
        context_bridge: Context bridge

    Returns:
        Configured ModeSwitcher instance
    """
    return ModeSwitcher(
        config=config,
        trigger_detectors=trigger_detectors,
        state_migrator=state_migrator,
        checkpoint_storage=checkpoint_storage,
        context_bridge=context_bridge,
    )
