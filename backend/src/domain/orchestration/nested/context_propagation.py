# =============================================================================
# IPA Platform - Context Propagation
# =============================================================================
# Sprint 11: S11-6 Context Propagation
#
# Handles context and variable propagation across nested workflows:
# - PropagationType: COPY, REFERENCE, MERGE, FILTER
# - ContextPropagator: Manages context flow between parent/child workflows
# - VariableScope: Tracks variable visibility and lifecycle
# - DataFlowTracker: Monitors data flow through workflow hierarchy
# =============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable, Union
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import copy
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class PropagationType(str, Enum):
    """
    上下文傳播類型

    Context propagation strategies:
    - COPY: Deep copy context to child (isolated)
    - REFERENCE: Share reference (shared state)
    - MERGE: Merge parent into child context
    - FILTER: Only propagate selected keys
    """
    COPY = "copy"
    REFERENCE = "reference"
    MERGE = "merge"
    FILTER = "filter"


class VariableScopeType(str, Enum):
    """
    變量作用域類型

    Variable scope types:
    - LOCAL: Only visible in current workflow
    - PARENT: Visible in parent workflow
    - GLOBAL: Visible across all workflows
    - INHERITED: Inherited from parent, read-only
    """
    LOCAL = "local"
    PARENT = "parent"
    GLOBAL = "global"
    INHERITED = "inherited"


class DataFlowDirection(str, Enum):
    """
    數據流向

    Data flow directions:
    - DOWNSTREAM: Parent to child
    - UPSTREAM: Child to parent
    - BIDIRECTIONAL: Both directions
    """
    DOWNSTREAM = "downstream"
    UPSTREAM = "upstream"
    BIDIRECTIONAL = "bidirectional"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VariableDescriptor:
    """
    變量描述符

    Describes a variable's metadata and scope.
    """
    name: str
    scope: VariableScopeType
    value: Any = None
    source_workflow_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: Optional[datetime] = None
    read_only: bool = False
    propagate_down: bool = True
    propagate_up: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "scope": self.scope.value,
            "value": self.value,
            "source_workflow_id": str(self.source_workflow_id) if self.source_workflow_id else None,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "read_only": self.read_only,
            "propagate_down": self.propagate_down,
            "propagate_up": self.propagate_up,
            "metadata": self.metadata,
        }


@dataclass
class PropagationRule:
    """
    傳播規則

    Defines how context is propagated between workflows.
    """
    rule_id: UUID = field(default_factory=uuid4)
    source_key: str = ""
    target_key: Optional[str] = None  # None means same as source
    propagation_type: PropagationType = PropagationType.COPY
    direction: DataFlowDirection = DataFlowDirection.DOWNSTREAM
    transform: Optional[Callable[[Any], Any]] = None
    condition: Optional[Callable[[Any], bool]] = None
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": str(self.rule_id),
            "source_key": self.source_key,
            "target_key": self.target_key or self.source_key,
            "propagation_type": self.propagation_type.value,
            "direction": self.direction.value,
            "priority": self.priority,
            "has_transform": self.transform is not None,
            "has_condition": self.condition is not None,
        }


@dataclass
class DataFlowEvent:
    """
    數據流事件

    Records a data flow event for tracking.
    """
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_workflow_id: UUID = field(default_factory=uuid4)
    target_workflow_id: UUID = field(default_factory=uuid4)
    variable_name: str = ""
    old_value: Any = None
    new_value: Any = None
    direction: DataFlowDirection = DataFlowDirection.DOWNSTREAM
    propagation_type: PropagationType = PropagationType.COPY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "source_workflow_id": str(self.source_workflow_id),
            "target_workflow_id": str(self.target_workflow_id),
            "variable_name": self.variable_name,
            "direction": self.direction.value,
            "propagation_type": self.propagation_type.value,
        }


# =============================================================================
# Variable Scope
# =============================================================================


class VariableScope:
    """
    變量作用域管理

    Manages variable visibility and lifecycle across workflow hierarchy.
    Supports local, parent, global, and inherited scopes.
    """

    def __init__(
        self,
        workflow_id: UUID,
        parent_scope: Optional["VariableScope"] = None
    ):
        """
        Initialize VariableScope.

        Args:
            workflow_id: Current workflow ID
            parent_scope: Parent workflow's scope (if any)
        """
        self.workflow_id = workflow_id
        self.parent_scope = parent_scope

        # Variable storage by scope type
        self._local: Dict[str, VariableDescriptor] = {}
        self._inherited: Dict[str, VariableDescriptor] = {}

        # Global scope (shared reference)
        self._global_store: Dict[str, VariableDescriptor] = {}

    def set(
        self,
        name: str,
        value: Any,
        scope: VariableScopeType = VariableScopeType.LOCAL,
        propagate_down: bool = True,
        propagate_up: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        設置變量

        Set a variable in the specified scope.

        Args:
            name: Variable name
            value: Variable value
            scope: Scope type
            propagate_down: Whether to propagate to child workflows
            propagate_up: Whether to propagate to parent workflow
            metadata: Additional metadata
        """
        descriptor = VariableDescriptor(
            name=name,
            scope=scope,
            value=value,
            source_workflow_id=self.workflow_id,
            propagate_down=propagate_down,
            propagate_up=propagate_up,
            metadata=metadata or {},
        )

        if scope == VariableScopeType.LOCAL:
            self._local[name] = descriptor
        elif scope == VariableScopeType.GLOBAL:
            self._global_store[name] = descriptor
        elif scope == VariableScopeType.PARENT and self.parent_scope:
            # Set in parent scope
            self.parent_scope.set(name, value, VariableScopeType.LOCAL, metadata=metadata)
        elif scope == VariableScopeType.INHERITED:
            # Inherited variables are read-only from child perspective
            descriptor.read_only = True
            self._inherited[name] = descriptor

        logger.debug(f"Variable '{name}' set in {scope.value} scope for workflow {self.workflow_id}")

    def get(
        self,
        name: str,
        default: Any = None,
        search_parent: bool = True
    ) -> Any:
        """
        獲取變量

        Get a variable, searching through scope hierarchy.

        Args:
            name: Variable name
            default: Default value if not found
            search_parent: Whether to search parent scopes

        Returns:
            Variable value or default
        """
        # Check local first
        if name in self._local:
            return self._local[name].value

        # Check inherited
        if name in self._inherited:
            return self._inherited[name].value

        # Check global
        if name in self._global_store:
            return self._global_store[name].value

        # Search parent scope
        if search_parent and self.parent_scope:
            return self.parent_scope.get(name, default, search_parent=True)

        return default

    def get_descriptor(self, name: str) -> Optional[VariableDescriptor]:
        """
        獲取變量描述符

        Get the full descriptor for a variable.
        """
        if name in self._local:
            return self._local[name]
        if name in self._inherited:
            return self._inherited[name]
        if name in self._global_store:
            return self._global_store[name]
        if self.parent_scope:
            return self.parent_scope.get_descriptor(name)
        return None

    def delete(self, name: str) -> bool:
        """
        刪除變量

        Delete a variable from local scope.
        """
        if name in self._local:
            del self._local[name]
            return True
        return False

    def exists(self, name: str, search_parent: bool = True) -> bool:
        """
        檢查變量是否存在

        Check if a variable exists.
        """
        if name in self._local or name in self._inherited or name in self._global_store:
            return True
        if search_parent and self.parent_scope:
            return self.parent_scope.exists(name, search_parent=True)
        return False

    def list_variables(
        self,
        scope_filter: Optional[VariableScopeType] = None,
        include_parent: bool = False
    ) -> List[VariableDescriptor]:
        """
        列出變量

        List all variables, optionally filtered by scope.
        """
        variables: List[VariableDescriptor] = []

        if scope_filter is None or scope_filter == VariableScopeType.LOCAL:
            variables.extend(self._local.values())
        if scope_filter is None or scope_filter == VariableScopeType.INHERITED:
            variables.extend(self._inherited.values())
        if scope_filter is None or scope_filter == VariableScopeType.GLOBAL:
            variables.extend(self._global_store.values())

        if include_parent and self.parent_scope:
            parent_vars = self.parent_scope.list_variables(scope_filter, include_parent=True)
            # Filter out duplicates (local takes precedence)
            local_names = {v.name for v in variables}
            variables.extend([v for v in parent_vars if v.name not in local_names])

        return variables

    def create_child_scope(self, child_workflow_id: UUID) -> "VariableScope":
        """
        創建子作用域

        Create a child scope with proper inheritance.
        """
        child = VariableScope(child_workflow_id, parent_scope=self)

        # Copy propagatable variables as inherited
        for name, descriptor in self._local.items():
            if descriptor.propagate_down:
                child._inherited[name] = VariableDescriptor(
                    name=name,
                    scope=VariableScopeType.INHERITED,
                    value=copy.deepcopy(descriptor.value),
                    source_workflow_id=descriptor.source_workflow_id,
                    read_only=True,
                    propagate_down=descriptor.propagate_down,
                    metadata=descriptor.metadata.copy(),
                )

        # Share global store reference
        child._global_store = self._global_store

        return child

    def to_dict(self) -> Dict[str, Any]:
        """Convert scope to dictionary."""
        return {
            "workflow_id": str(self.workflow_id),
            "local_count": len(self._local),
            "inherited_count": len(self._inherited),
            "global_count": len(self._global_store),
            "has_parent": self.parent_scope is not None,
            "variables": {
                "local": [v.to_dict() for v in self._local.values()],
                "inherited": [v.to_dict() for v in self._inherited.values()],
                "global": [v.to_dict() for v in self._global_store.values()],
            },
        }


# =============================================================================
# Context Propagator
# =============================================================================


class ContextPropagator:
    """
    上下文傳播器

    Manages context propagation between parent and child workflows.
    Supports multiple propagation strategies and transformation rules.
    """

    def __init__(self):
        """Initialize ContextPropagator."""
        self._rules: List[PropagationRule] = []
        self._default_type = PropagationType.COPY
        self._blocked_keys: Set[str] = set()
        self._key_mappings: Dict[str, str] = {}

    def add_rule(self, rule: PropagationRule) -> None:
        """
        添加傳播規則

        Add a propagation rule.
        """
        self._rules.append(rule)
        # Sort by priority
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def block_key(self, key: str) -> None:
        """
        阻止鍵傳播

        Block a key from being propagated.
        """
        self._blocked_keys.add(key)

    def map_key(self, source_key: str, target_key: str) -> None:
        """
        映射鍵名

        Map a source key to a different target key.
        """
        self._key_mappings[source_key] = target_key

    def propagate_downstream(
        self,
        parent_context: Dict[str, Any],
        child_context: Optional[Dict[str, Any]] = None,
        propagation_type: Optional[PropagationType] = None,
        filter_keys: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        向下傳播上下文

        Propagate context from parent to child.

        Args:
            parent_context: Parent workflow context
            child_context: Existing child context (optional)
            propagation_type: Override propagation type
            filter_keys: Only propagate these keys (for FILTER type)

        Returns:
            Propagated child context
        """
        prop_type = propagation_type or self._default_type
        result = child_context.copy() if child_context else {}

        for key, value in parent_context.items():
            # Skip blocked keys
            if key in self._blocked_keys:
                continue

            # Apply key mapping
            target_key = self._key_mappings.get(key, key)

            # Check filter
            if prop_type == PropagationType.FILTER and filter_keys:
                if key not in filter_keys:
                    continue

            # Find applicable rule
            rule = self._find_rule(key, DataFlowDirection.DOWNSTREAM)

            if rule:
                # Apply rule
                value = self._apply_rule(rule, value)
                if value is None:  # Rule filtered out the value
                    continue
                prop_type = rule.propagation_type

            # Propagate based on type
            if prop_type == PropagationType.COPY:
                result[target_key] = copy.deepcopy(value)
            elif prop_type == PropagationType.REFERENCE:
                result[target_key] = value
            elif prop_type == PropagationType.MERGE:
                if target_key in result and isinstance(result[target_key], dict) and isinstance(value, dict):
                    result[target_key] = {**result[target_key], **value}
                else:
                    result[target_key] = copy.deepcopy(value)
            elif prop_type == PropagationType.FILTER:
                result[target_key] = copy.deepcopy(value)

        return result

    def propagate_upstream(
        self,
        child_context: Dict[str, Any],
        parent_context: Dict[str, Any],
        merge_strategy: str = "update"  # "update", "merge", "replace"
    ) -> Dict[str, Any]:
        """
        向上傳播上下文

        Propagate context from child to parent.

        Args:
            child_context: Child workflow context
            parent_context: Parent workflow context
            merge_strategy: How to merge into parent

        Returns:
            Updated parent context
        """
        result = parent_context.copy()

        for key, value in child_context.items():
            # Skip blocked keys
            if key in self._blocked_keys:
                continue

            # Find applicable rule
            rule = self._find_rule(key, DataFlowDirection.UPSTREAM)

            if rule:
                # Only propagate if rule allows upstream
                if rule.direction not in [DataFlowDirection.UPSTREAM, DataFlowDirection.BIDIRECTIONAL]:
                    continue
                value = self._apply_rule(rule, value)
                if value is None:
                    continue

            # Apply key mapping (reverse)
            target_key = key
            for src, tgt in self._key_mappings.items():
                if tgt == key:
                    target_key = src
                    break

            # Apply merge strategy
            if merge_strategy == "update":
                result[target_key] = copy.deepcopy(value)
            elif merge_strategy == "merge":
                if target_key in result and isinstance(result[target_key], dict) and isinstance(value, dict):
                    result[target_key] = {**result[target_key], **value}
                else:
                    result[target_key] = copy.deepcopy(value)
            elif merge_strategy == "replace":
                result = child_context.copy()
                break

        return result

    def _find_rule(
        self,
        key: str,
        direction: DataFlowDirection
    ) -> Optional[PropagationRule]:
        """Find applicable rule for key and direction."""
        for rule in self._rules:
            if rule.source_key == key or rule.source_key == "*":
                if rule.direction == direction or rule.direction == DataFlowDirection.BIDIRECTIONAL:
                    return rule
        return None

    def _apply_rule(self, rule: PropagationRule, value: Any) -> Any:
        """Apply rule transformation and condition."""
        # Check condition
        if rule.condition and not rule.condition(value):
            return None

        # Apply transform
        if rule.transform:
            return rule.transform(value)

        return value

    def create_child_context(
        self,
        parent_context: Dict[str, Any],
        child_inputs: Optional[Dict[str, Any]] = None,
        propagation_type: PropagationType = PropagationType.COPY
    ) -> Dict[str, Any]:
        """
        創建子上下文

        Create a new child context from parent context.

        Args:
            parent_context: Parent workflow context
            child_inputs: Additional inputs for child
            propagation_type: Propagation strategy

        Returns:
            New child context
        """
        # Start with propagated parent context
        child = self.propagate_downstream(
            parent_context,
            propagation_type=propagation_type
        )

        # Override with child-specific inputs
        if child_inputs:
            child.update(child_inputs)

        return child

    def merge_child_results(
        self,
        parent_context: Dict[str, Any],
        child_results: List[Dict[str, Any]],
        merge_keys: Optional[Set[str]] = None,
        conflict_strategy: str = "last_wins"  # "last_wins", "first_wins", "merge_all"
    ) -> Dict[str, Any]:
        """
        合併子結果

        Merge results from multiple child workflows into parent context.

        Args:
            parent_context: Parent workflow context
            child_results: List of child workflow results
            merge_keys: Keys to merge (None = all)
            conflict_strategy: How to handle conflicts

        Returns:
            Merged context
        """
        result = parent_context.copy()

        for child_ctx in child_results:
            for key, value in child_ctx.items():
                if merge_keys and key not in merge_keys:
                    continue

                if key in result:
                    if conflict_strategy == "first_wins":
                        continue  # Keep existing
                    elif conflict_strategy == "last_wins":
                        result[key] = copy.deepcopy(value)
                    elif conflict_strategy == "merge_all":
                        if isinstance(result[key], list):
                            if isinstance(value, list):
                                result[key].extend(value)
                            else:
                                result[key].append(value)
                        elif isinstance(result[key], dict) and isinstance(value, dict):
                            result[key] = {**result[key], **value}
                        else:
                            result[key] = [result[key], value]
                else:
                    result[key] = copy.deepcopy(value)

        return result


# =============================================================================
# Data Flow Tracker
# =============================================================================


class DataFlowTracker:
    """
    數據流追蹤器

    Monitors and records data flow through workflow hierarchy.
    Useful for debugging and audit trails.
    """

    def __init__(self, max_events: int = 10000):
        """
        Initialize DataFlowTracker.

        Args:
            max_events: Maximum events to retain
        """
        self.max_events = max_events
        self._events: List[DataFlowEvent] = []
        self._workflow_graph: Dict[UUID, Set[UUID]] = {}  # parent -> children
        self._variable_sources: Dict[str, List[UUID]] = {}  # variable -> workflows that modified it

    def record_flow(
        self,
        source_workflow_id: UUID,
        target_workflow_id: UUID,
        variable_name: str,
        old_value: Any,
        new_value: Any,
        direction: DataFlowDirection,
        propagation_type: PropagationType
    ) -> DataFlowEvent:
        """
        記錄數據流

        Record a data flow event.
        """
        event = DataFlowEvent(
            source_workflow_id=source_workflow_id,
            target_workflow_id=target_workflow_id,
            variable_name=variable_name,
            old_value=old_value,
            new_value=new_value,
            direction=direction,
            propagation_type=propagation_type,
        )

        self._events.append(event)

        # Trim if needed
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

        # Update graph
        if source_workflow_id not in self._workflow_graph:
            self._workflow_graph[source_workflow_id] = set()
        if direction == DataFlowDirection.DOWNSTREAM:
            self._workflow_graph[source_workflow_id].add(target_workflow_id)

        # Update variable sources
        if variable_name not in self._variable_sources:
            self._variable_sources[variable_name] = []
        if source_workflow_id not in self._variable_sources[variable_name]:
            self._variable_sources[variable_name].append(source_workflow_id)

        logger.debug(f"Data flow recorded: {variable_name} from {source_workflow_id} to {target_workflow_id}")

        return event

    def get_events(
        self,
        workflow_id: Optional[UUID] = None,
        variable_name: Optional[str] = None,
        direction: Optional[DataFlowDirection] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DataFlowEvent]:
        """
        獲取事件

        Get data flow events with optional filtering.
        """
        events = self._events

        if workflow_id:
            events = [
                e for e in events
                if e.source_workflow_id == workflow_id or e.target_workflow_id == workflow_id
            ]

        if variable_name:
            events = [e for e in events if e.variable_name == variable_name]

        if direction:
            events = [e for e in events if e.direction == direction]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def get_variable_history(
        self,
        variable_name: str,
        limit: int = 50
    ) -> List[DataFlowEvent]:
        """
        獲取變量歷史

        Get history of a specific variable.
        """
        return [
            e for e in self._events
            if e.variable_name == variable_name
        ][-limit:]

    def get_workflow_flow(
        self,
        workflow_id: UUID,
        direction: DataFlowDirection = DataFlowDirection.DOWNSTREAM
    ) -> List[DataFlowEvent]:
        """
        獲取工作流流向

        Get all data flow for a workflow.
        """
        if direction == DataFlowDirection.DOWNSTREAM:
            return [e for e in self._events if e.source_workflow_id == workflow_id]
        elif direction == DataFlowDirection.UPSTREAM:
            return [e for e in self._events if e.target_workflow_id == workflow_id]
        else:
            return [
                e for e in self._events
                if e.source_workflow_id == workflow_id or e.target_workflow_id == workflow_id
            ]

    def get_workflow_children(self, workflow_id: UUID) -> Set[UUID]:
        """
        獲取子工作流

        Get all child workflows.
        """
        return self._workflow_graph.get(workflow_id, set())

    def get_variable_sources(self, variable_name: str) -> List[UUID]:
        """
        獲取變量來源

        Get all workflows that have modified a variable.
        """
        return self._variable_sources.get(variable_name, [])

    def build_dependency_graph(self) -> Dict[str, Any]:
        """
        構建依賴圖

        Build a dependency graph from tracked flows.
        """
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        for event in self._events:
            src_id = str(event.source_workflow_id)
            tgt_id = str(event.target_workflow_id)

            if src_id not in nodes:
                nodes[src_id] = {"id": src_id, "variables_out": set()}
            if tgt_id not in nodes:
                nodes[tgt_id] = {"id": tgt_id, "variables_in": set()}

            nodes[src_id]["variables_out"].add(event.variable_name)
            nodes[tgt_id].setdefault("variables_in", set()).add(event.variable_name)

            edges.append({
                "source": src_id,
                "target": tgt_id,
                "variable": event.variable_name,
                "type": event.propagation_type.value,
            })

        # Convert sets to lists for serialization
        for node in nodes.values():
            for key in ["variables_out", "variables_in"]:
                if key in node:
                    node[key] = list(node[key])

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Get tracker statistics.
        """
        by_direction = {}
        by_type = {}
        by_variable = {}

        for event in self._events:
            # By direction
            dir_val = event.direction.value
            by_direction[dir_val] = by_direction.get(dir_val, 0) + 1

            # By type
            type_val = event.propagation_type.value
            by_type[type_val] = by_type.get(type_val, 0) + 1

            # By variable
            by_variable[event.variable_name] = by_variable.get(event.variable_name, 0) + 1

        return {
            "total_events": len(self._events),
            "unique_workflows": len(self._workflow_graph),
            "unique_variables": len(self._variable_sources),
            "by_direction": by_direction,
            "by_propagation_type": by_type,
            "top_variables": sorted(
                by_variable.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "max_events": self.max_events,
        }

    def clear(self) -> None:
        """
        清空追蹤

        Clear all tracked events.
        """
        self._events.clear()
        self._workflow_graph.clear()
        self._variable_sources.clear()
        logger.info("Data flow tracker cleared")


# =============================================================================
# Utility Functions
# =============================================================================


def create_isolated_context(
    source_context: Dict[str, Any],
    keys_to_copy: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    創建隔離上下文

    Create an isolated copy of context.

    Args:
        source_context: Source context to copy
        keys_to_copy: Specific keys to copy (None = all)

    Returns:
        Isolated context copy
    """
    if keys_to_copy:
        return {
            k: copy.deepcopy(v)
            for k, v in source_context.items()
            if k in keys_to_copy
        }
    return copy.deepcopy(source_context)


def merge_contexts(
    contexts: List[Dict[str, Any]],
    conflict_resolution: str = "last_wins"
) -> Dict[str, Any]:
    """
    合併多個上下文

    Merge multiple contexts into one.

    Args:
        contexts: List of contexts to merge
        conflict_resolution: "first_wins", "last_wins", "collect_all"

    Returns:
        Merged context
    """
    result: Dict[str, Any] = {}

    for ctx in contexts:
        for key, value in ctx.items():
            if key not in result:
                result[key] = copy.deepcopy(value)
            elif conflict_resolution == "last_wins":
                result[key] = copy.deepcopy(value)
            elif conflict_resolution == "first_wins":
                pass  # Keep existing
            elif conflict_resolution == "collect_all":
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(copy.deepcopy(value))

    return result


def filter_context_by_prefix(
    context: Dict[str, Any],
    prefix: str,
    remove_prefix: bool = False
) -> Dict[str, Any]:
    """
    按前綴過濾上下文

    Filter context keys by prefix.

    Args:
        context: Source context
        prefix: Key prefix to filter
        remove_prefix: Whether to remove prefix from keys

    Returns:
        Filtered context
    """
    result = {}
    for key, value in context.items():
        if key.startswith(prefix):
            new_key = key[len(prefix):] if remove_prefix else key
            result[new_key] = value
    return result

