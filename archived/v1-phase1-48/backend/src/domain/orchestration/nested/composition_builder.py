# =============================================================================
# IPA Platform - Workflow Composition Builder
# =============================================================================
# Sprint 11: S11-4 WorkflowCompositionBuilder
#
# Provides a fluent API for composing workflows with:
# - Sequential composition
# - Parallel composition
# - Conditional branching
# - Loop structures
# - Switch/case patterns
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from uuid import UUID, uuid4
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class CompositionType(str, Enum):
    """
    組合類型

    Types of workflow composition:
    - SEQUENCE: Execute workflows in order
    - PARALLEL: Execute workflows concurrently
    - CONDITIONAL: Execute based on condition
    - LOOP: Execute repeatedly
    - SWITCH: Execute based on matching value
    """
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    SWITCH = "switch"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WorkflowNode:
    """
    工作流節點

    Represents a single workflow in a composition,
    either as a reference or inline definition.
    """
    id: UUID
    workflow_id: Optional[UUID]  # Reference to existing workflow
    inline_definition: Optional[Dict[str, Any]]  # Inline workflow definition
    name: str
    inputs_mapping: Dict[str, str] = field(default_factory=dict)
    outputs_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None  # For conditional execution
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "inline_definition": self.inline_definition,
            "inputs_mapping": self.inputs_mapping,
            "outputs_mapping": self.outputs_mapping,
            "condition": self.condition,
            "metadata": self.metadata,
        }


@dataclass
class CompositionBlock:
    """
    組合塊

    A block containing multiple nodes or nested blocks
    with a specific composition type.
    """
    id: UUID
    composition_type: CompositionType
    nodes: List[Union[WorkflowNode, "CompositionBlock"]] = field(default_factory=list)
    condition: Optional[str] = None  # Condition expression
    loop_config: Optional[Dict[str, Any]] = None  # Loop configuration
    switch_cases: Optional[Dict[str, Any]] = None  # Switch cases
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        serialized = {
            "id": str(self.id),
            "type": self.composition_type.value,
            "name": self.name,
            "nodes": [],
            "metadata": self.metadata,
        }

        for node in self.nodes:
            if isinstance(node, CompositionBlock):
                serialized["nodes"].append(node.to_dict())
            else:
                serialized["nodes"].append(node.to_dict())

        if self.condition:
            serialized["condition"] = self.condition

        if self.loop_config:
            serialized["loop_config"] = self.loop_config

        if self.switch_cases:
            serialized["switch"] = self.switch_cases

        return serialized


# =============================================================================
# Workflow Composition Builder
# =============================================================================


class WorkflowCompositionBuilder:
    """
    工作流組合建構器

    Provides a fluent API for building complex workflow compositions
    with nested structures and various execution patterns.

    Example usage:
        composition = (
            WorkflowCompositionBuilder()
            .sequence()
                .add_workflow(wf_id_1, name="prepare")
                .parallel()
                    .add_workflow(wf_id_2, name="process_a")
                    .add_workflow(wf_id_3, name="process_b")
                .end()
                .conditional("result.success == true")
                    .add_workflow(wf_id_4, name="success_handler")
                .end()
            .end()
            .build()
        )
    """

    def __init__(self, name: Optional[str] = None):
        """
        Initialize WorkflowCompositionBuilder.

        Args:
            name: Optional name for the composition
        """
        self._name = name
        self._root: Optional[CompositionBlock] = None
        self._current_block: Optional[CompositionBlock] = None
        self._block_stack: List[CompositionBlock] = []
        self._current_case: Optional[str] = None

    # =========================================================================
    # Composition Type Starters
    # =========================================================================

    def sequence(self, name: Optional[str] = None) -> "WorkflowCompositionBuilder":
        """
        開始順序組合

        Start a sequential composition block.

        Args:
            name: Optional name for this block

        Returns:
            Self for chaining
        """
        block = CompositionBlock(
            id=uuid4(),
            composition_type=CompositionType.SEQUENCE,
            name=name,
        )
        self._push_block(block)
        return self

    def parallel(self, name: Optional[str] = None) -> "WorkflowCompositionBuilder":
        """
        開始並行組合

        Start a parallel composition block.

        Args:
            name: Optional name for this block

        Returns:
            Self for chaining
        """
        block = CompositionBlock(
            id=uuid4(),
            composition_type=CompositionType.PARALLEL,
            name=name,
        )
        self._push_block(block)
        return self

    def conditional(
        self,
        condition: str,
        name: Optional[str] = None
    ) -> "WorkflowCompositionBuilder":
        """
        開始條件組合

        Start a conditional composition block.

        Args:
            condition: Condition expression (e.g., "result.success == true")
            name: Optional name for this block

        Returns:
            Self for chaining
        """
        block = CompositionBlock(
            id=uuid4(),
            composition_type=CompositionType.CONDITIONAL,
            condition=condition,
            name=name,
        )
        self._push_block(block)
        return self

    def loop(
        self,
        max_iterations: int = 10,
        condition: Optional[str] = None,
        name: Optional[str] = None
    ) -> "WorkflowCompositionBuilder":
        """
        開始迴圈組合

        Start a loop composition block.

        Args:
            max_iterations: Maximum iterations
            condition: Continue condition (e.g., "not converged")
            name: Optional name for this block

        Returns:
            Self for chaining
        """
        block = CompositionBlock(
            id=uuid4(),
            composition_type=CompositionType.LOOP,
            loop_config={
                "max_iterations": max_iterations,
                "condition": condition,
            },
            name=name,
        )
        self._push_block(block)
        return self

    def switch(
        self,
        expression: str,
        name: Optional[str] = None
    ) -> "WorkflowCompositionBuilder":
        """
        開始分支組合

        Start a switch/case composition block.

        Args:
            expression: Expression to evaluate for case matching
            name: Optional name for this block

        Returns:
            Self for chaining
        """
        block = CompositionBlock(
            id=uuid4(),
            composition_type=CompositionType.SWITCH,
            switch_cases={
                "expression": expression,
                "cases": {},
                "default": None,
            },
            name=name,
        )
        self._push_block(block)
        return self

    def case(self, value: Any) -> "WorkflowCompositionBuilder":
        """
        添加 switch case

        Add a case to a switch block.

        Args:
            value: Value to match

        Returns:
            Self for chaining

        Raises:
            ValueError: If not in a switch block
        """
        if not self._current_block or self._current_block.composition_type != CompositionType.SWITCH:
            raise ValueError("case() must be called within switch()")

        case_key = str(value)
        self._current_block.switch_cases["cases"][case_key] = []
        self._current_case = case_key
        return self

    def default(self) -> "WorkflowCompositionBuilder":
        """
        添加 switch default case

        Add a default case to a switch block.

        Returns:
            Self for chaining
        """
        if not self._current_block or self._current_block.composition_type != CompositionType.SWITCH:
            raise ValueError("default() must be called within switch()")

        self._current_block.switch_cases["default"] = []
        self._current_case = "_default"
        return self

    # =========================================================================
    # Node Addition
    # =========================================================================

    def add_workflow(
        self,
        workflow_id: UUID,
        name: Optional[str] = None,
        inputs_mapping: Optional[Dict[str, str]] = None,
        outputs_mapping: Optional[Dict[str, str]] = None,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowCompositionBuilder":
        """
        添加工作流引用

        Add a workflow reference node.

        Args:
            workflow_id: ID of workflow to reference
            name: Display name
            inputs_mapping: Map parent context to workflow inputs
            outputs_mapping: Map workflow outputs to parent context
            condition: Optional execution condition
            metadata: Additional metadata

        Returns:
            Self for chaining
        """
        node = WorkflowNode(
            id=uuid4(),
            workflow_id=workflow_id,
            inline_definition=None,
            name=name or f"workflow_{workflow_id}",
            inputs_mapping=inputs_mapping or {},
            outputs_mapping=outputs_mapping or {},
            condition=condition,
            metadata=metadata or {},
        )
        self._add_node(node)
        return self

    def add_inline(
        self,
        definition: Dict[str, Any],
        name: Optional[str] = None,
        inputs_mapping: Optional[Dict[str, str]] = None,
        outputs_mapping: Optional[Dict[str, str]] = None,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "WorkflowCompositionBuilder":
        """
        添加內聯工作流定義

        Add an inline workflow definition node.

        Args:
            definition: Inline workflow definition
            name: Display name
            inputs_mapping: Map parent context to workflow inputs
            outputs_mapping: Map workflow outputs to parent context
            condition: Optional execution condition
            metadata: Additional metadata

        Returns:
            Self for chaining
        """
        node = WorkflowNode(
            id=uuid4(),
            workflow_id=None,
            inline_definition=definition,
            name=name or f"inline_{uuid4().hex[:8]}",
            inputs_mapping=inputs_mapping or {},
            outputs_mapping=outputs_mapping or {},
            condition=condition,
            metadata=metadata or {},
        )
        self._add_node(node)
        return self

    def add_task(
        self,
        task_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None,
        inputs_mapping: Optional[Dict[str, str]] = None,
        outputs_mapping: Optional[Dict[str, str]] = None
    ) -> "WorkflowCompositionBuilder":
        """
        添加任務節點

        Add a simple task node (shorthand for inline definition).

        Args:
            task_type: Type of task
            config: Task configuration
            name: Display name
            inputs_mapping: Input mappings
            outputs_mapping: Output mappings

        Returns:
            Self for chaining
        """
        definition = {
            "type": task_type,
            "config": config,
        }
        return self.add_inline(
            definition=definition,
            name=name or f"task_{task_type}",
            inputs_mapping=inputs_mapping,
            outputs_mapping=outputs_mapping,
        )

    # =========================================================================
    # Block Management
    # =========================================================================

    def end(self) -> "WorkflowCompositionBuilder":
        """
        結束當前組合塊

        End the current composition block.

        Returns:
            Self for chaining
        """
        self._current_case = None
        self._pop_block()
        return self

    def _push_block(self, block: CompositionBlock) -> None:
        """Push a new block onto the stack."""
        if self._current_block:
            self._current_block.nodes.append(block)
            self._block_stack.append(self._current_block)
        else:
            self._root = block

        self._current_block = block

    def _pop_block(self) -> None:
        """Pop the current block from the stack."""
        if self._block_stack:
            self._current_block = self._block_stack.pop()
        else:
            self._current_block = None

    def _add_node(self, node: WorkflowNode) -> None:
        """Add a node to the current block."""
        if not self._current_block:
            raise ValueError("No active composition block. Start with sequence(), parallel(), etc.")

        if self._current_block.composition_type == CompositionType.SWITCH:
            # Add to current case
            if self._current_case == "_default":
                if self._current_block.switch_cases["default"] is None:
                    self._current_block.switch_cases["default"] = []
                self._current_block.switch_cases["default"].append(node.to_dict())
            elif self._current_case:
                self._current_block.switch_cases["cases"][self._current_case].append(node.to_dict())
            else:
                raise ValueError("Must call case() or default() before adding workflows in switch")
        else:
            self._current_block.nodes.append(node)

    # =========================================================================
    # Building
    # =========================================================================

    def build(self) -> Dict[str, Any]:
        """
        構建最終的組合定義

        Build and return the final composition definition.

        Returns:
            Composition definition as dictionary

        Raises:
            ValueError: If no composition defined
        """
        if not self._root:
            raise ValueError("No composition defined. Start with sequence(), parallel(), etc.")

        return {
            "name": self._name,
            "composition": self._root.to_dict(),
            "version": "1.0",
        }

    def validate(self) -> List[str]:
        """
        驗證組合

        Validate the composition for errors.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self._root:
            errors.append("No composition defined")
            return errors

        # Check for unclosed blocks
        if self._block_stack:
            errors.append(f"{len(self._block_stack)} unclosed block(s)")

        # Validate recursively
        errors.extend(self._validate_block(self._root))

        return errors

    def _validate_block(self, block: CompositionBlock) -> List[str]:
        """Validate a composition block recursively."""
        errors = []

        # Check for empty blocks
        if not block.nodes and block.composition_type != CompositionType.SWITCH:
            errors.append(f"Empty {block.composition_type.value} block")

        # Validate switch cases
        if block.composition_type == CompositionType.SWITCH:
            if not block.switch_cases or not block.switch_cases.get("cases"):
                errors.append("Switch block has no cases")

        # Validate loop config
        if block.composition_type == CompositionType.LOOP:
            if not block.loop_config:
                errors.append("Loop block missing configuration")

        # Validate conditional
        if block.composition_type == CompositionType.CONDITIONAL:
            if not block.condition:
                errors.append("Conditional block missing condition")

        # Validate nested blocks
        for node in block.nodes:
            if isinstance(node, CompositionBlock):
                errors.extend(self._validate_block(node))

        return errors

    def reset(self) -> "WorkflowCompositionBuilder":
        """
        重置建構器

        Reset the builder to initial state.

        Returns:
            Self for chaining
        """
        self._root = None
        self._current_block = None
        self._block_stack = []
        self._current_case = None
        return self

    # =========================================================================
    # Templates
    # =========================================================================

    @classmethod
    def create_map_reduce(
        cls,
        mapper_workflow_id: UUID,
        reducer_workflow_id: UUID,
        items_key: str = "items",
        result_key: str = "results"
    ) -> "WorkflowCompositionBuilder":
        """
        建立 Map-Reduce 模板

        Create a map-reduce composition template.

        Args:
            mapper_workflow_id: Workflow ID for mapping
            reducer_workflow_id: Workflow ID for reducing
            items_key: Key for input items
            result_key: Key for output results

        Returns:
            Configured builder
        """
        builder = cls(name="map_reduce")
        return (
            builder
            .sequence()
                .parallel()
                    .add_workflow(
                        mapper_workflow_id,
                        name="mapper",
                        inputs_mapping={items_key: "item"}
                    )
                .end()
                .add_workflow(
                    reducer_workflow_id,
                    name="reducer",
                    inputs_mapping={"mapper_results": result_key}
                )
            .end()
        )

    @classmethod
    def create_pipeline(
        cls,
        workflow_ids: List[UUID],
        pass_through_key: str = "data"
    ) -> "WorkflowCompositionBuilder":
        """
        建立 Pipeline 模板

        Create a pipeline composition template.

        Args:
            workflow_ids: List of workflow IDs in order
            pass_through_key: Key to pass between stages

        Returns:
            Configured builder
        """
        builder = cls(name="pipeline")
        builder.sequence()

        for i, wf_id in enumerate(workflow_ids):
            builder.add_workflow(
                wf_id,
                name=f"stage_{i+1}",
                inputs_mapping={pass_through_key: "input"},
                outputs_mapping={"output": pass_through_key},
            )

        return builder.end()

    @classmethod
    def create_scatter_gather(
        cls,
        scatter_workflow_id: UUID,
        worker_workflow_ids: List[UUID],
        gather_workflow_id: UUID
    ) -> "WorkflowCompositionBuilder":
        """
        建立 Scatter-Gather 模板

        Create a scatter-gather composition template.

        Args:
            scatter_workflow_id: Workflow to scatter work
            worker_workflow_ids: Worker workflow IDs
            gather_workflow_id: Workflow to gather results

        Returns:
            Configured builder
        """
        builder = cls(name="scatter_gather")
        builder.sequence()

        # Scatter
        builder.add_workflow(scatter_workflow_id, name="scatter")

        # Parallel workers
        builder.parallel()
        for i, wf_id in enumerate(worker_workflow_ids):
            builder.add_workflow(wf_id, name=f"worker_{i+1}")
        builder.end()

        # Gather
        builder.add_workflow(gather_workflow_id, name="gather")

        return builder.end()

    @classmethod
    def create_retry_pattern(
        cls,
        workflow_id: UUID,
        max_retries: int = 3,
        backoff_seconds: int = 5
    ) -> "WorkflowCompositionBuilder":
        """
        建立重試模板

        Create a retry pattern composition template.

        Args:
            workflow_id: Workflow to retry
            max_retries: Maximum retry attempts
            backoff_seconds: Seconds between retries

        Returns:
            Configured builder
        """
        builder = cls(name="retry_pattern")
        return (
            builder
            .loop(max_iterations=max_retries, condition="not result.success")
                .add_workflow(
                    workflow_id,
                    name="main_task",
                    metadata={"backoff_seconds": backoff_seconds}
                )
            .end()
        )

    @classmethod
    def create_saga(
        cls,
        steps: List[Dict[str, UUID]],
    ) -> "WorkflowCompositionBuilder":
        """
        建立 Saga 模板

        Create a saga pattern composition template with compensations.

        Args:
            steps: List of {"forward": UUID, "compensate": UUID}

        Returns:
            Configured builder
        """
        builder = cls(name="saga")
        builder.sequence()

        for i, step in enumerate(steps):
            # Each step with conditional compensation
            builder.add_workflow(
                step["forward"],
                name=f"step_{i+1}",
                metadata={"compensation": str(step.get("compensate"))}
            )

        return builder.end()
