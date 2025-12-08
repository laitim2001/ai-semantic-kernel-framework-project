# =============================================================================
# IPA Platform - WorkflowContext Adapter
# =============================================================================
# Phase 5: MVP Core Official API Migration
# Sprint 26, Story S26-4: WorkflowContextAdapter (5 pts)
#
# This module adapts the existing WorkflowContext to be compatible with
# the official Microsoft Agent Framework context interface.
#
# Official context interface (from workflows-api.md):
#   context.get(key) - Retrieve shared state
#   context.set(key, value) - Store shared state
#   context.run_id - Current execution run ID
#
# Key Features:
#   - Wraps existing WorkflowContext
#   - Provides official context interface
#   - Supports bidirectional state transfer
#   - Maintains execution history
#
# IMPORTANT: Compatible with official Agent Framework context interface
# =============================================================================

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import logging
import copy

# Import existing domain model
from src.domain.workflows.models import WorkflowContext


logger = logging.getLogger(__name__)


# =============================================================================
# WorkflowContextAdapter - Official Context Interface
# =============================================================================

class WorkflowContextAdapter:
    """
    Adapter that provides official Agent Framework context interface.

    This adapter wraps the existing WorkflowContext and provides the
    get/set interface expected by the official Workflow executors.

    Example:
        >>> from src.domain.workflows.models import WorkflowContext
        >>> domain_ctx = WorkflowContext(execution_id=uuid4(), workflow_id=uuid4())
        >>> adapter = WorkflowContextAdapter(domain_ctx)
        >>> adapter.set("key", "value")
        >>> print(adapter.get("key"))  # "value"

    IMPORTANT: Provides interface compatible with official context
    """

    def __init__(
        self,
        context: Optional[WorkflowContext] = None,
        execution_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        initial_variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the context adapter.

        Args:
            context: Existing WorkflowContext to wrap (optional)
            execution_id: Execution ID if creating new context
            workflow_id: Workflow ID if creating new context
            initial_variables: Initial variables for new context
        """
        if context:
            self._context = context
        else:
            # Create a new WorkflowContext
            self._context = WorkflowContext(
                execution_id=execution_id or uuid4(),
                workflow_id=workflow_id or uuid4(),
                variables=initial_variables or {},
            )

        # Track modifications
        self._modifications: List[Dict[str, Any]] = []
        self._created_at = datetime.utcnow()

    @property
    def run_id(self) -> str:
        """
        Get the current run/execution ID.

        This property is required by the official context interface.

        Returns:
            String representation of the execution ID
        """
        return str(self._context.execution_id)

    @property
    def execution_id(self) -> UUID:
        """Get the execution ID as UUID."""
        return self._context.execution_id

    @property
    def workflow_id(self) -> UUID:
        """Get the workflow ID."""
        return self._context.workflow_id

    @property
    def current_node(self) -> Optional[str]:
        """Get the current executing node."""
        return self._context.current_node

    @current_node.setter
    def current_node(self, node_id: str) -> None:
        """Set the current executing node."""
        self._context.current_node = node_id

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context.

        This is the primary method for retrieving shared state
        between workflow executors.

        Args:
            key: The key to retrieve
            default: Default value if key not found

        Returns:
            The stored value or default
        """
        # Check variables first
        value = self._context.variables.get(key)
        if value is not None:
            return value

        # Check input_data as fallback
        value = self._context.input_data.get(key)
        if value is not None:
            return value

        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context.

        This is the primary method for storing shared state
        between workflow executors.

        Args:
            key: The key to store
            value: The value to store
        """
        self._context.variables[key] = value

        # Track modification
        self._modifications.append({
            "action": "set",
            "key": key,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def delete(self, key: str) -> bool:
        """
        Delete a value from the context.

        Args:
            key: The key to delete

        Returns:
            True if key was deleted, False if not found
        """
        if key in self._context.variables:
            del self._context.variables[key]

            self._modifications.append({
                "action": "delete",
                "key": key,
                "timestamp": datetime.utcnow().isoformat(),
            })
            return True

        return False

    def has(self, key: str) -> bool:
        """
        Check if a key exists in the context.

        Args:
            key: The key to check

        Returns:
            True if key exists
        """
        return key in self._context.variables or key in self._context.input_data

    def keys(self) -> List[str]:
        """
        Get all keys in the context.

        Returns:
            List of all keys (variables + input_data)
        """
        all_keys = set(self._context.variables.keys())
        all_keys.update(self._context.input_data.keys())
        return list(all_keys)

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update multiple values at once.

        Args:
            data: Dictionary of key-value pairs to update
        """
        for key, value in data.items():
            self.set(key, value)

    def clear(self) -> None:
        """Clear all variables (but not input_data)."""
        self._context.variables.clear()

        self._modifications.append({
            "action": "clear",
            "timestamp": datetime.utcnow().isoformat(),
        })

    # =========================================================================
    # History and Tracking
    # =========================================================================

    def add_history(
        self,
        node_id: str,
        action: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Add an entry to execution history.

        Args:
            node_id: The node that was executed
            action: What action was performed
            result: Result summary
            error: Error message if failed
        """
        self._context.add_history(
            node_id=node_id,
            action=action,
            result=result,
            error=error,
        )

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get the execution history."""
        return self._context.history

    @property
    def modifications(self) -> List[Dict[str, Any]]:
        """Get the list of context modifications."""
        return self._modifications

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary.

        Returns:
            Dictionary representation of the context
        """
        return {
            "execution_id": str(self._context.execution_id),
            "workflow_id": str(self._context.workflow_id),
            "variables": copy.deepcopy(self._context.variables),
            "input_data": copy.deepcopy(self._context.input_data),
            "current_node": self._context.current_node,
            "history": self._context.history,
            "created_at": self._created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContextAdapter":
        """
        Create context adapter from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            WorkflowContextAdapter instance
        """
        context = WorkflowContext(
            execution_id=UUID(data["execution_id"]),
            workflow_id=UUID(data["workflow_id"]),
            variables=data.get("variables", {}),
            input_data=data.get("input_data", {}),
            current_node=data.get("current_node"),
            history=data.get("history", []),
        )
        return cls(context=context)

    def snapshot(self) -> Dict[str, Any]:
        """
        Create a snapshot of the current context state.

        Useful for checkpointing and recovery.

        Returns:
            Snapshot dictionary
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_id": str(self._context.execution_id),
            "variables": copy.deepcopy(self._context.variables),
            "current_node": self._context.current_node,
            "history_count": len(self._context.history),
        }

    # =========================================================================
    # Domain Context Access
    # =========================================================================

    @property
    def domain_context(self) -> WorkflowContext:
        """
        Get the underlying domain WorkflowContext.

        Use this when you need access to the original domain model.

        Returns:
            The wrapped WorkflowContext
        """
        return self._context

    def sync_from_domain(self) -> None:
        """
        Sync state from the domain context.

        Call this if domain context was modified externally.
        """
        # Already using the same object, no sync needed
        pass

    def sync_to_domain(self) -> None:
        """
        Sync state to the domain context.

        Call this before saving the domain context.
        """
        # Already using the same object, no sync needed
        pass

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorkflowContextAdapter("
            f"run_id={self.run_id[:8]}..., "
            f"keys={len(self.keys())}, "
            f"history={len(self.history)})"
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_context(
    execution_id: Optional[UUID] = None,
    workflow_id: Optional[UUID] = None,
    input_data: Optional[Dict[str, Any]] = None,
    initial_variables: Optional[Dict[str, Any]] = None,
) -> WorkflowContextAdapter:
    """
    Factory function to create a new context adapter.

    Args:
        execution_id: Optional execution identifier
        workflow_id: Optional workflow identifier
        input_data: Initial input data
        initial_variables: Initial context variables

    Returns:
        WorkflowContextAdapter instance
    """
    context = WorkflowContext(
        execution_id=execution_id or uuid4(),
        workflow_id=workflow_id or uuid4(),
        variables=initial_variables or {},
        input_data=input_data or {},
    )
    return WorkflowContextAdapter(context=context)


def adapt_context(context: WorkflowContext) -> WorkflowContextAdapter:
    """
    Adapt an existing domain context to the official interface.

    Args:
        context: The domain WorkflowContext to adapt

    Returns:
        WorkflowContextAdapter wrapping the context
    """
    return WorkflowContextAdapter(context=context)


def merge_contexts(
    primary: WorkflowContextAdapter,
    secondary: WorkflowContextAdapter,
) -> WorkflowContextAdapter:
    """
    Merge two context adapters.

    Variables from secondary are added to primary if not already present.
    History from both is combined.

    Args:
        primary: The primary context (takes precedence)
        secondary: The secondary context to merge

    Returns:
        New merged WorkflowContextAdapter
    """
    # Create new context based on primary
    merged = create_context(
        execution_id=primary.execution_id,
        workflow_id=primary.workflow_id,
        initial_variables=copy.deepcopy(primary._context.variables),
    )

    # Merge input_data
    merged._context.input_data = copy.deepcopy(primary._context.input_data)
    for key, value in secondary._context.input_data.items():
        if key not in merged._context.input_data:
            merged._context.input_data[key] = value

    # Merge variables (primary takes precedence)
    for key, value in secondary._context.variables.items():
        if key not in merged._context.variables:
            merged._context.variables[key] = value

    # Combine history
    merged._context.history = (
        primary._context.history + secondary._context.history
    )

    return merged
