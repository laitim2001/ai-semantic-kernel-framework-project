# =============================================================================
# IPA Platform - Coordination Context Manager
# =============================================================================
# Sprint 81: S81-1 - Claude 主導的多 Agent 協調 (10 pts)
#
# This module manages context transfer and result merging across agents.
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    CoordinationContext,
    Subtask,
    SubtaskResult,
    SubtaskStatus,
)


logger = logging.getLogger(__name__)


@dataclass
class ContextTransfer:
    """Represents a context transfer between agents."""

    from_subtask_id: str
    to_subtask_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_subtask_id": self.from_subtask_id,
            "to_subtask_id": self.to_subtask_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class ContextManager:
    """
    Manages context transfer and result merging for multi-agent coordination.

    Responsibilities:
    - Transfer context between dependent subtasks
    - Merge results from multiple agents
    - Maintain shared state across coordination
    """

    def __init__(self):
        """Initialize context manager."""
        self._transfers: List[ContextTransfer] = []
        self._shared_context: Dict[str, Any] = {}

    def transfer_context(
        self,
        from_subtask: Subtask,
        to_subtask: Subtask,
        result: SubtaskResult,
    ) -> Dict[str, Any]:
        """
        Transfer context from completed subtask to dependent subtask.

        Args:
            from_subtask: The completed subtask.
            to_subtask: The dependent subtask.
            result: Result from the completed subtask.

        Returns:
            The transferred context data.
        """
        # Build transfer data
        transfer_data = {
            "source_subtask_id": from_subtask.subtask_id,
            "source_output": result.output,
            "source_metadata": result.metadata,
        }

        # Add relevant input data from source
        if from_subtask.input_data:
            transfer_data["source_input"] = from_subtask.input_data

        # Create transfer record
        transfer = ContextTransfer(
            from_subtask_id=from_subtask.subtask_id,
            to_subtask_id=to_subtask.subtask_id,
            data=transfer_data,
        )
        self._transfers.append(transfer)

        # Update target subtask input
        if "dependencies_output" not in to_subtask.input_data:
            to_subtask.input_data["dependencies_output"] = {}

        to_subtask.input_data["dependencies_output"][from_subtask.subtask_id] = (
            result.output
        )

        logger.debug(
            f"Transferred context from {from_subtask.subtask_id} "
            f"to {to_subtask.subtask_id}"
        )

        return transfer_data

    def merge_results(
        self,
        results: List[SubtaskResult],
        merge_strategy: str = "combine",
    ) -> Any:
        """
        Merge results from multiple subtasks.

        Args:
            results: List of subtask results.
            merge_strategy: How to merge results:
                - "combine": Combine into a list
                - "dict": Merge into a dictionary
                - "first_success": Return first successful result
                - "last": Return last result

        Returns:
            Merged result.
        """
        if not results:
            return None

        successful_results = [r for r in results if r.success]

        if merge_strategy == "combine":
            return self._merge_combine(results)

        elif merge_strategy == "dict":
            return self._merge_dict(results)

        elif merge_strategy == "first_success":
            return successful_results[0].output if successful_results else None

        elif merge_strategy == "last":
            return results[-1].output

        else:
            logger.warning(f"Unknown merge strategy: {merge_strategy}, using combine")
            return self._merge_combine(results)

    def _merge_combine(self, results: List[SubtaskResult]) -> List[Dict[str, Any]]:
        """Merge results by combining into a list."""
        return [
            {
                "subtask_id": r.subtask_id,
                "agent_id": r.agent_id,
                "success": r.success,
                "output": r.output,
            }
            for r in results
        ]

    def _merge_dict(self, results: List[SubtaskResult]) -> Dict[str, Any]:
        """Merge results into a dictionary keyed by subtask ID."""
        merged = {}
        for r in results:
            merged[r.subtask_id] = {
                "agent_id": r.agent_id,
                "success": r.success,
                "output": r.output,
            }
        return merged

    def update_shared_context(self, key: str, value: Any) -> None:
        """
        Update shared context accessible by all subtasks.

        Args:
            key: Context key.
            value: Context value.
        """
        self._shared_context[key] = value
        logger.debug(f"Updated shared context: {key}")

    def get_shared_context(self, key: str, default: Any = None) -> Any:
        """
        Get value from shared context.

        Args:
            key: Context key.
            default: Default value if key not found.

        Returns:
            Context value or default.
        """
        return self._shared_context.get(key, default)

    def get_all_shared_context(self) -> Dict[str, Any]:
        """Get all shared context."""
        return self._shared_context.copy()

    def prepare_subtask_context(
        self,
        subtask: Subtask,
        completed_subtasks: Dict[str, Subtask],
        results: Dict[str, SubtaskResult],
    ) -> Dict[str, Any]:
        """
        Prepare context for a subtask based on its dependencies.

        Args:
            subtask: The subtask to prepare context for.
            completed_subtasks: Dict of completed subtasks by ID.
            results: Dict of results by subtask ID.

        Returns:
            Prepared context dictionary.
        """
        context = {
            "shared": self._shared_context.copy(),
            "dependencies": {},
        }

        # Add dependency outputs
        for dep_id in subtask.depends_on:
            if dep_id in results:
                dep_result = results[dep_id]
                context["dependencies"][dep_id] = {
                    "output": dep_result.output,
                    "success": dep_result.success,
                    "metadata": dep_result.metadata,
                }

        # Add to subtask input data
        subtask.input_data["context"] = context

        return context

    def aggregate_final_result(
        self,
        context: CoordinationContext,
        aggregation_type: str = "summary",
    ) -> Any:
        """
        Aggregate all results into a final output.

        Args:
            context: The coordination context.
            aggregation_type: Type of aggregation:
                - "summary": Create a summary of all results
                - "detailed": Include all details
                - "outputs_only": Only include outputs

        Returns:
            Aggregated result.
        """
        if aggregation_type == "summary":
            return self._aggregate_summary(context)

        elif aggregation_type == "detailed":
            return self._aggregate_detailed(context)

        elif aggregation_type == "outputs_only":
            return self._aggregate_outputs_only(context)

        else:
            return self._aggregate_summary(context)

    def _aggregate_summary(self, context: CoordinationContext) -> Dict[str, Any]:
        """Create summary aggregation."""
        total = len(context.results)
        successful = sum(1 for r in context.results if r.success)

        return {
            "task_id": context.task.task_id,
            "total_subtasks": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "outputs": [
                {"subtask_id": r.subtask_id, "output": r.output}
                for r in context.results
                if r.success
            ],
            "errors": [
                {"subtask_id": r.subtask_id, "error": r.error}
                for r in context.results
                if not r.success
            ],
        }

    def _aggregate_detailed(self, context: CoordinationContext) -> Dict[str, Any]:
        """Create detailed aggregation."""
        return {
            "task": context.task.to_dict(),
            "analysis": context.analysis.to_dict() if context.analysis else None,
            "subtasks": [s.to_dict() for s in context.subtasks],
            "results": [r.to_dict() for r in context.results],
            "shared_context": self._shared_context,
            "transfers": [t.to_dict() for t in self._transfers],
        }

    def _aggregate_outputs_only(self, context: CoordinationContext) -> List[Any]:
        """Create outputs-only aggregation."""
        return [r.output for r in context.results if r.success]

    def get_transfers(self) -> List[ContextTransfer]:
        """Get all context transfers."""
        return self._transfers.copy()

    def clear(self) -> None:
        """Clear all context state."""
        self._transfers.clear()
        self._shared_context.clear()
        logger.debug("Context manager cleared")
