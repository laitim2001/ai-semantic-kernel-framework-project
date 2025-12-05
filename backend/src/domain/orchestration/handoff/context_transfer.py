# =============================================================================
# IPA Platform - Context Transfer Manager
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Manages context extraction, transformation, and injection during handoff.
# Ensures complete and validated context transfer between agents.
#
# Features:
#   - Context extraction from source agent
#   - Context transformation for compatibility
#   - Context validation before injection
#   - Context injection to target agent
# =============================================================================

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class TransferValidationError(Exception):
    """Exception raised when context validation fails."""

    def __init__(
        self,
        message: str,
        field: str = None,
        details: Dict[str, Any] = None,
    ):
        super().__init__(message)
        self.field = field
        self.details = details or {}


@dataclass
class TransferContext:
    """
    Represents context data being transferred.

    Attributes:
        task_id: Identifier of the task
        task_state: Current task state dictionary
        conversation_history: List of conversation messages
        metadata: Additional metadata
        source_agent_id: ID of source agent
        target_agent_id: ID of target agent
        handoff_reason: Reason for the handoff
        timestamp: When context was extracted
        checksum: Optional checksum for validation
    """
    task_id: str
    task_state: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_agent_id: Optional[str] = None
    target_agent_id: Optional[str] = None
    handoff_reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    checksum: Optional[str] = None


@dataclass
class TransformationRule:
    """
    Rule for transforming context fields.

    Attributes:
        source_field: Field to transform from
        target_field: Field to transform to
        transformer: Function to transform the value
        required: Whether the field is required
    """
    source_field: str
    target_field: str
    transformer: Optional[Callable[[Any], Any]] = None
    required: bool = False


class ContextTransferManager:
    """
    Manages context transfer between agents during handoff.

    Responsibilities:
        - Extract context from source agent
        - Transform context for target agent compatibility
        - Validate context before injection
        - Inject context to target agent

    Usage:
        manager = ContextTransferManager()

        # Extract context
        context = await manager.extract_context(
            agent_service,
            source_agent_id,
            task_id,
        )

        # Transform if needed
        transformed = await manager.transform_context(
            context,
            transformation_rules,
        )

        # Validate
        await manager.validate_context(transformed)

        # Inject
        await manager.inject_context(
            agent_service,
            target_agent_id,
            transformed,
        )
    """

    # Default required fields for validation
    DEFAULT_REQUIRED_FIELDS = {"task_id", "task_state"}

    # Maximum conversation history length
    MAX_HISTORY_LENGTH = 100

    # Maximum context size in bytes (10 MB)
    MAX_CONTEXT_SIZE = 10 * 1024 * 1024

    def __init__(
        self,
        required_fields: Set[str] = None,
        max_history_length: int = None,
        max_context_size: int = None,
    ):
        """
        Initialize ContextTransferManager.

        Args:
            required_fields: Set of required field names
            max_history_length: Maximum conversation history entries
            max_context_size: Maximum context size in bytes
        """
        self._required_fields = required_fields or self.DEFAULT_REQUIRED_FIELDS
        self._max_history_length = max_history_length or self.MAX_HISTORY_LENGTH
        self._max_context_size = max_context_size or self.MAX_CONTEXT_SIZE

        # Custom validators
        self._validators: List[Callable[[TransferContext], None]] = []

        # Custom transformers
        self._transformers: List[Callable[[TransferContext], TransferContext]] = []

        logger.info("ContextTransferManager initialized")

    def register_validator(
        self,
        validator: Callable[[TransferContext], None],
    ) -> None:
        """
        Register a custom validator function.

        Args:
            validator: Function that raises TransferValidationError if invalid
        """
        self._validators.append(validator)

    def register_transformer(
        self,
        transformer: Callable[[TransferContext], TransferContext],
    ) -> None:
        """
        Register a custom transformer function.

        Args:
            transformer: Function that transforms and returns context
        """
        self._transformers.append(transformer)

    async def extract_context(
        self,
        agent_service: Any,
        source_agent_id: UUID,
        task_id: str,
        include_history: bool = True,
        include_metadata: bool = True,
    ) -> TransferContext:
        """
        Extract context from source agent.

        Args:
            agent_service: Agent service for retrieving agent state
            source_agent_id: ID of the source agent
            task_id: ID of the task being transferred
            include_history: Whether to include conversation history
            include_metadata: Whether to include metadata

        Returns:
            TransferContext with extracted data
        """
        logger.debug(f"Extracting context from agent {source_agent_id}")

        task_state = {}
        conversation_history = []
        metadata = {}

        if agent_service:
            # Get task state
            task_state = await agent_service.get_agent_state(
                source_agent_id,
                task_id,
            ) or {}

            # Get conversation history
            if include_history:
                history = await agent_service.get_conversation_history(
                    source_agent_id,
                    task_id,
                )
                conversation_history = list(history or [])

            # Get metadata
            if include_metadata:
                metadata = await agent_service.get_agent_metadata(
                    source_agent_id,
                ) or {}

        context = TransferContext(
            task_id=task_id,
            task_state=task_state,
            conversation_history=conversation_history,
            metadata=metadata,
            source_agent_id=str(source_agent_id),
        )

        # Calculate checksum
        context.checksum = self._calculate_checksum(context)

        logger.info(
            f"Context extracted: task_id={task_id}, "
            f"state_keys={len(task_state)}, "
            f"history_length={len(conversation_history)}"
        )

        return context

    async def transform_context(
        self,
        context: TransferContext,
        rules: List[TransformationRule] = None,
        target_agent_type: str = None,
    ) -> TransferContext:
        """
        Transform context for target agent compatibility.

        Args:
            context: Context to transform
            rules: List of transformation rules
            target_agent_type: Type of target agent for auto-transformation

        Returns:
            Transformed TransferContext
        """
        logger.debug(f"Transforming context for task {context.task_id}")

        # Deep copy to avoid modifying original
        transformed = copy.deepcopy(context)

        # Apply explicit rules
        if rules:
            for rule in rules:
                transformed = self._apply_rule(transformed, rule)

        # Apply registered transformers
        for transformer in self._transformers:
            transformed = transformer(transformed)

        # Trim conversation history if too long
        if len(transformed.conversation_history) > self._max_history_length:
            transformed.conversation_history = transformed.conversation_history[
                -self._max_history_length:
            ]
            logger.debug(
                f"Trimmed conversation history to {self._max_history_length} entries"
            )

        # Update timestamp
        transformed.timestamp = datetime.utcnow()

        # Recalculate checksum
        transformed.checksum = self._calculate_checksum(transformed)

        return transformed

    async def validate_context(
        self,
        context: TransferContext,
        strict: bool = True,
    ) -> bool:
        """
        Validate context before injection.

        Args:
            context: Context to validate
            strict: If True, raise exception on validation failure

        Returns:
            True if valid

        Raises:
            TransferValidationError: If validation fails and strict=True
        """
        logger.debug(f"Validating context for task {context.task_id}")

        errors = []

        # Check required fields
        for field_name in self._required_fields:
            value = getattr(context, field_name, None)
            if value is None or (isinstance(value, dict) and not value):
                errors.append(f"Required field '{field_name}' is missing or empty")

        # Check task_id
        if not context.task_id or not isinstance(context.task_id, str):
            errors.append("task_id must be a non-empty string")

        # Check task_state
        if not isinstance(context.task_state, dict):
            errors.append("task_state must be a dictionary")

        # Check conversation_history
        if not isinstance(context.conversation_history, list):
            errors.append("conversation_history must be a list")

        # Check size
        try:
            size = len(json.dumps(self._to_dict(context)))
            if size > self._max_context_size:
                errors.append(
                    f"Context size ({size} bytes) exceeds maximum "
                    f"({self._max_context_size} bytes)"
                )
        except Exception as e:
            errors.append(f"Context is not JSON serializable: {e}")

        # Run custom validators
        for validator in self._validators:
            try:
                validator(context)
            except TransferValidationError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Validator failed: {e}")

        if errors:
            logger.warning(f"Context validation failed: {errors}")
            if strict:
                raise TransferValidationError(
                    f"Context validation failed with {len(errors)} error(s)",
                    details={"errors": errors},
                )
            return False

        logger.debug("Context validation passed")
        return True

    async def inject_context(
        self,
        agent_service: Any,
        target_agent_id: UUID,
        context: TransferContext,
        validate: bool = True,
    ) -> bool:
        """
        Inject context to target agent.

        Args:
            agent_service: Agent service for context injection
            target_agent_id: ID of the target agent
            context: Context to inject
            validate: Whether to validate before injection

        Returns:
            True if injection succeeded
        """
        logger.debug(f"Injecting context to agent {target_agent_id}")

        # Validate first
        if validate:
            await self.validate_context(context, strict=True)

        # Update target agent ID
        context.target_agent_id = str(target_agent_id)

        # Convert to dictionary for injection
        context_dict = self._to_dict(context)

        if agent_service:
            await agent_service.inject_context(
                target_agent_id,
                context_dict,
            )

        logger.info(
            f"Context injected to agent {target_agent_id}: "
            f"task_id={context.task_id}"
        )

        return True

    async def transfer(
        self,
        target_agent_id: UUID,
        context_data: Dict[str, Any],
    ) -> bool:
        """
        Simple transfer method for direct context injection.

        Args:
            target_agent_id: ID of the target agent
            context_data: Dictionary of context data

        Returns:
            True if transfer succeeded
        """
        context = TransferContext(
            task_id=context_data.get("task_id", ""),
            task_state=context_data.get("task_state", {}),
            conversation_history=context_data.get("conversation_history", []),
            metadata=context_data.get("metadata", {}),
            source_agent_id=context_data.get("source_agent_id"),
            handoff_reason=context_data.get("handoff_reason", ""),
        )

        return await self.inject_context(None, target_agent_id, context, validate=False)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _apply_rule(
        self,
        context: TransferContext,
        rule: TransformationRule,
    ) -> TransferContext:
        """Apply a transformation rule to context."""
        # Get source value from task_state
        source_value = context.task_state.get(rule.source_field)

        if source_value is None and rule.required:
            raise TransferValidationError(
                f"Required field '{rule.source_field}' not found in task_state",
                field=rule.source_field,
            )

        if source_value is not None:
            # Transform value
            if rule.transformer:
                try:
                    transformed_value = rule.transformer(source_value)
                except Exception as e:
                    raise TransferValidationError(
                        f"Transformation failed for field '{rule.source_field}': {e}",
                        field=rule.source_field,
                    )
            else:
                transformed_value = source_value

            # Set target value
            context.task_state[rule.target_field] = transformed_value

            # Remove source if different from target
            if rule.source_field != rule.target_field:
                del context.task_state[rule.source_field]

        return context

    def _calculate_checksum(self, context: TransferContext) -> str:
        """Calculate checksum for context validation."""
        import hashlib

        content = json.dumps(
            {
                "task_id": context.task_id,
                "task_state": context.task_state,
                "conversation_history": context.conversation_history,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _to_dict(self, context: TransferContext) -> Dict[str, Any]:
        """Convert TransferContext to dictionary."""
        return {
            "task_id": context.task_id,
            "task_state": context.task_state,
            "conversation_history": context.conversation_history,
            "metadata": context.metadata,
            "source_agent_id": context.source_agent_id,
            "target_agent_id": context.target_agent_id,
            "handoff_reason": context.handoff_reason,
            "timestamp": context.timestamp.isoformat() if context.timestamp else None,
            "checksum": context.checksum,
        }
