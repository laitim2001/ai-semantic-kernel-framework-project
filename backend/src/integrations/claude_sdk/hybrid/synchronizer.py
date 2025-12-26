"""Context Synchronizer for Hybrid Orchestrator.

Sprint 50: S50-4 - Context Synchronizer (8 pts)

This module provides context synchronization between Microsoft Agent Framework
and Claude Agent SDK, ensuring consistent state management across frameworks.

Key Features:
- Format conversion between frameworks
- Context state tracking and diffing
- Snapshot/restore capabilities
- Message history synchronization
- Metadata and tool state synchronization
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .types import HybridSessionConfig, ToolCall


class ContextFormat(Enum):
    """Context format types for different frameworks."""

    CLAUDE_SDK = "claude_sdk"
    MICROSOFT_AGENT = "microsoft_agent"
    UNIFIED = "unified"


class SyncDirection(Enum):
    """Direction of context synchronization."""

    CLAUDE_TO_MS = "claude_to_ms"
    MS_TO_CLAUDE = "ms_to_claude"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    """Strategy for resolving context conflicts."""

    LATEST_WINS = "latest_wins"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class Message:
    """A message in the conversation history."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[ToolCall] = field(default_factory=list)
    framework_source: str = "claude_sdk"

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata,
            "tool_calls": [
                {"name": tc.name, "arguments": tc.arguments, "result": tc.result}
                for tc in self.tool_calls
            ],
            "framework_source": self.framework_source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        tool_calls = [
            ToolCall(
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
                result=tc.get("result"),
            )
            for tc in data.get("tool_calls", [])
        ]
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {}),
            tool_calls=tool_calls,
            framework_source=data.get("framework_source", "claude_sdk"),
        )


@dataclass
class ContextState:
    """Represents the current context state.

    Contains all information needed to synchronize context
    between frameworks including messages, metadata, and tool state.
    """

    # Unique context identifier
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Conversation history
    messages: List[Message] = field(default_factory=list)

    # System prompt
    system_prompt: Optional[str] = None

    # Context metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Active tool definitions
    tools: List[Dict[str, Any]] = field(default_factory=list)

    # Current framework
    current_framework: str = "claude_sdk"

    # Last update timestamp
    last_updated: float = field(default_factory=time.time)

    # Version for conflict detection
    version: int = 1

    # Hash for change detection
    _content_hash: str = ""

    def compute_hash(self) -> str:
        """Compute hash of context state for change detection."""
        content = json.dumps(
            {
                "messages": [m.to_dict() for m in self.messages],
                "system_prompt": self.system_prompt,
                "metadata": self.metadata,
                "tools": self.tools,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def has_changed(self) -> bool:
        """Check if context has changed since last hash computation."""
        current_hash = self.compute_hash()
        return current_hash != self._content_hash

    def update_hash(self) -> None:
        """Update the stored content hash."""
        self._content_hash = self.compute_hash()
        self.last_updated = time.time()
        self.version += 1

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[ToolCall]] = None,
    ) -> Message:
        """Add a message to the context."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            tool_calls=tool_calls or [],
            framework_source=self.current_framework,
        )
        self.messages.append(message)
        self.update_hash()
        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert context state to dictionary."""
        return {
            "context_id": self.context_id,
            "messages": [m.to_dict() for m in self.messages],
            "system_prompt": self.system_prompt,
            "metadata": dict(self.metadata),  # Copy to avoid reference sharing
            "tools": [dict(t) for t in self.tools],  # Copy tools list
            "current_framework": self.current_framework,
            "last_updated": self.last_updated,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextState":
        """Create context state from dictionary."""
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        state = cls(
            context_id=data.get("context_id", str(uuid.uuid4())),
            messages=messages,
            system_prompt=data.get("system_prompt"),
            metadata=data.get("metadata", {}),
            tools=data.get("tools", []),
            current_framework=data.get("current_framework", "claude_sdk"),
            last_updated=data.get("last_updated", time.time()),
            version=data.get("version", 1),
        )
        state.update_hash()
        return state


@dataclass
class ContextDiff:
    """Represents differences between two context states."""

    # Added messages
    added_messages: List[Message] = field(default_factory=list)

    # Removed messages
    removed_messages: List[Message] = field(default_factory=list)

    # Changed metadata keys
    metadata_changes: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)

    # Tool changes
    tool_changes: Dict[str, Any] = field(default_factory=dict)

    # System prompt changed
    system_prompt_changed: bool = False

    # Old and new system prompts
    old_system_prompt: Optional[str] = None
    new_system_prompt: Optional[str] = None

    def is_empty(self) -> bool:
        """Check if diff contains no changes."""
        return (
            not self.added_messages
            and not self.removed_messages
            and not self.metadata_changes
            and not self.tool_changes
            and not self.system_prompt_changed
        )

    def summary(self) -> str:
        """Generate summary of changes."""
        parts = []
        if self.added_messages:
            parts.append(f"+{len(self.added_messages)} messages")
        if self.removed_messages:
            parts.append(f"-{len(self.removed_messages)} messages")
        if self.metadata_changes:
            parts.append(f"~{len(self.metadata_changes)} metadata")
        if self.tool_changes:
            parts.append(f"~{len(self.tool_changes)} tools")
        if self.system_prompt_changed:
            parts.append("system prompt changed")
        return ", ".join(parts) if parts else "no changes"


@dataclass
class ContextSnapshot:
    """Snapshot of context state at a point in time."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str = ""
    state: Optional[ContextState] = None
    created_at: float = field(default_factory=time.time)
    label: str = ""

    def restore(self) -> ContextState:
        """Restore context from snapshot."""
        if self.state is None:
            raise ValueError("Snapshot has no state to restore")
        # Deep copy state
        return ContextState.from_dict(self.state.to_dict())


class ContextSynchronizer:
    """Synchronizes context between frameworks.

    Handles conversion, diffing, and merging of context state
    between Microsoft Agent Framework and Claude Agent SDK.
    """

    def __init__(
        self,
        config: Optional[HybridSessionConfig] = None,
        conflict_resolution: ConflictResolution = ConflictResolution.LATEST_WINS,
    ):
        """Initialize context synchronizer.

        Args:
            config: Hybrid session configuration
            conflict_resolution: Strategy for resolving conflicts
        """
        self._config = config or HybridSessionConfig()
        self._conflict_resolution = conflict_resolution
        self._contexts: Dict[str, ContextState] = {}
        self._snapshots: Dict[str, List[ContextSnapshot]] = {}
        self._sync_listeners: List[Callable[[ContextState, SyncDirection], None]] = []
        self._sync_count = 0
        self._last_sync_time: Optional[float] = None

    @property
    def config(self) -> HybridSessionConfig:
        """Get current configuration."""
        return self._config

    @property
    def sync_count(self) -> int:
        """Get number of syncs performed."""
        return self._sync_count

    @property
    def context_count(self) -> int:
        """Get number of active contexts."""
        return len(self._contexts)

    def create_context(
        self,
        context_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextState:
        """Create a new context.

        Args:
            context_id: Optional context ID (auto-generated if not provided)
            system_prompt: Optional system prompt
            metadata: Optional initial metadata

        Returns:
            Created context state
        """
        context = ContextState(
            context_id=context_id or str(uuid.uuid4()),
            system_prompt=system_prompt,
            metadata=metadata or {},
        )
        context.update_hash()
        self._contexts[context.context_id] = context
        self._snapshots[context.context_id] = []
        return context

    def get_context(self, context_id: str) -> Optional[ContextState]:
        """Get context by ID."""
        return self._contexts.get(context_id)

    def remove_context(self, context_id: str) -> bool:
        """Remove a context.

        Args:
            context_id: Context ID to remove

        Returns:
            True if removed, False if not found
        """
        if context_id in self._contexts:
            del self._contexts[context_id]
            if context_id in self._snapshots:
                del self._snapshots[context_id]
            return True
        return False

    def convert_to_claude(
        self, context: ContextState
    ) -> Dict[str, Any]:
        """Convert context to Claude SDK format.

        Args:
            context: Context state to convert

        Returns:
            Context in Claude SDK format
        """
        messages = []

        # Add system prompt as first message
        if context.system_prompt:
            messages.append({
                "role": "user",
                "content": f"<system>{context.system_prompt}</system>",
            })

        # Convert messages
        for msg in context.messages:
            claude_msg = {"role": msg.role, "content": msg.content}

            # Handle tool results
            if msg.role == "tool":
                claude_msg["role"] = "user"
                tool_results = []
                for tc in msg.tool_calls:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.name,
                        "content": str(tc.result) if tc.result else "",
                    })
                if tool_results:
                    claude_msg["content"] = tool_results

            # Handle assistant tool calls
            elif msg.role == "assistant" and msg.tool_calls:
                tool_use = []
                for tc in msg.tool_calls:
                    tool_use.append({
                        "type": "tool_use",
                        "id": tc.name,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                claude_msg["content"] = [
                    {"type": "text", "text": msg.content},
                    *tool_use,
                ]

            messages.append(claude_msg)

        return {
            "messages": messages[-self._config.max_sync_messages:],
            "tools": self._convert_tools_to_claude(context.tools),
            "metadata": context.metadata,
        }

    def convert_to_ms_agent(
        self, context: ContextState
    ) -> Dict[str, Any]:
        """Convert context to Microsoft Agent Framework format.

        Args:
            context: Context state to convert

        Returns:
            Context in MS Agent Framework format
        """
        chat_history = []

        for msg in context.messages:
            ms_msg = {
                "role": msg.role,
                "content": msg.content,
                "name": msg.metadata.get("name"),
            }

            # Convert tool calls
            if msg.tool_calls:
                ms_msg["function_call"] = {
                    "name": msg.tool_calls[0].name,
                    "arguments": json.dumps(msg.tool_calls[0].arguments),
                }

            chat_history.append(ms_msg)

        return {
            "chat_history": chat_history[-self._config.max_sync_messages:],
            "system_message": context.system_prompt,
            "functions": self._convert_tools_to_ms_agent(context.tools),
            "context": context.metadata,
        }

    def convert_from_claude(
        self, claude_data: Dict[str, Any], context_id: Optional[str] = None
    ) -> ContextState:
        """Convert Claude SDK format to context state.

        Args:
            claude_data: Data in Claude SDK format
            context_id: Optional context ID

        Returns:
            Context state
        """
        context = ContextState(
            context_id=context_id or str(uuid.uuid4()),
            current_framework="claude_sdk",
            metadata=claude_data.get("metadata", {}),
        )

        # Parse messages
        for msg_data in claude_data.get("messages", []):
            role = msg_data.get("role", "user")
            content = msg_data.get("content", "")

            # Handle system prompt in first message
            if isinstance(content, str) and content.startswith("<system>"):
                context.system_prompt = content[8:-9]  # Remove tags
                continue

            # Handle structured content
            if isinstance(content, list):
                text_parts = []
                tool_calls = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif part.get("type") == "tool_use":
                            tool_calls.append(ToolCall(
                                name=part.get("name", ""),
                                arguments=part.get("input", {}),
                                framework="claude_sdk",
                            ))
                content = " ".join(text_parts)
                context.add_message(role, content, tool_calls=tool_calls)
            else:
                context.add_message(role, content)

        # Convert tools
        context.tools = self._convert_tools_from_claude(
            claude_data.get("tools", [])
        )

        context.update_hash()
        return context

    def convert_from_ms_agent(
        self, ms_data: Dict[str, Any], context_id: Optional[str] = None
    ) -> ContextState:
        """Convert MS Agent Framework format to context state.

        Args:
            ms_data: Data in MS Agent Framework format
            context_id: Optional context ID

        Returns:
            Context state
        """
        context = ContextState(
            context_id=context_id or str(uuid.uuid4()),
            current_framework="microsoft_agent_framework",
            system_prompt=ms_data.get("system_message"),
            metadata=ms_data.get("context", {}),
        )

        # Parse chat history
        for msg_data in ms_data.get("chat_history", []):
            role = msg_data.get("role", "user")
            content = msg_data.get("content", "")
            tool_calls = []

            # Handle function calls
            if "function_call" in msg_data:
                fc = msg_data["function_call"]
                tool_calls.append(ToolCall(
                    name=fc.get("name", ""),
                    arguments=json.loads(fc.get("arguments", "{}")),
                    framework="microsoft_agent_framework",
                ))

            context.add_message(
                role, content,
                metadata={"name": msg_data.get("name")},
                tool_calls=tool_calls,
            )

        # Convert functions to tools
        context.tools = self._convert_tools_from_ms_agent(
            ms_data.get("functions", [])
        )

        context.update_hash()
        return context

    def diff(
        self, source: ContextState, target: ContextState
    ) -> ContextDiff:
        """Compute differences between two context states.

        Args:
            source: Source context state
            target: Target context state

        Returns:
            Context diff object
        """
        diff = ContextDiff()

        # Compare messages by ID
        source_ids = {m.message_id for m in source.messages}
        target_ids = {m.message_id for m in target.messages}

        # Added messages
        added_ids = target_ids - source_ids
        diff.added_messages = [
            m for m in target.messages if m.message_id in added_ids
        ]

        # Removed messages
        removed_ids = source_ids - target_ids
        diff.removed_messages = [
            m for m in source.messages if m.message_id in removed_ids
        ]

        # Compare metadata
        all_keys = set(source.metadata.keys()) | set(target.metadata.keys())
        for key in all_keys:
            source_val = source.metadata.get(key)
            target_val = target.metadata.get(key)
            if source_val != target_val:
                diff.metadata_changes[key] = (source_val, target_val)

        # Compare tools
        source_tools = {t.get("name"): t for t in source.tools}
        target_tools = {t.get("name"): t for t in target.tools}
        all_tool_names = set(source_tools.keys()) | set(target_tools.keys())
        for name in all_tool_names:
            if source_tools.get(name) != target_tools.get(name):
                diff.tool_changes[name] = {
                    "from": source_tools.get(name),
                    "to": target_tools.get(name),
                }

        # Compare system prompts
        if source.system_prompt != target.system_prompt:
            diff.system_prompt_changed = True
            diff.old_system_prompt = source.system_prompt
            diff.new_system_prompt = target.system_prompt

        return diff

    def merge(
        self,
        source: ContextState,
        target: ContextState,
        resolution: Optional[ConflictResolution] = None,
    ) -> ContextState:
        """Merge two context states.

        Args:
            source: Source context state
            target: Target context state
            resolution: Conflict resolution strategy

        Returns:
            Merged context state
        """
        resolution = resolution or self._conflict_resolution
        merged = ContextState(
            context_id=target.context_id,
            current_framework=target.current_framework,
        )

        # Merge messages (combine unique messages)
        all_messages: Dict[str, Message] = {}
        for m in source.messages:
            all_messages[m.message_id] = m
        for m in target.messages:
            if m.message_id in all_messages:
                # Handle conflict
                if resolution == ConflictResolution.LATEST_WINS:
                    if m.timestamp > all_messages[m.message_id].timestamp:
                        all_messages[m.message_id] = m
                elif resolution == ConflictResolution.TARGET_WINS:
                    all_messages[m.message_id] = m
                # SOURCE_WINS: keep existing
            else:
                all_messages[m.message_id] = m

        # Sort by timestamp
        merged.messages = sorted(
            all_messages.values(), key=lambda m: m.timestamp
        )

        # Merge system prompt
        if resolution == ConflictResolution.LATEST_WINS:
            if target.last_updated > source.last_updated:
                merged.system_prompt = target.system_prompt
            else:
                merged.system_prompt = source.system_prompt
        elif resolution == ConflictResolution.TARGET_WINS:
            merged.system_prompt = target.system_prompt
        else:
            merged.system_prompt = source.system_prompt

        # Merge metadata
        merged.metadata = {**source.metadata, **target.metadata}
        if resolution == ConflictResolution.SOURCE_WINS:
            merged.metadata = {**target.metadata, **source.metadata}

        # Merge tools (union)
        tool_names = set()
        merged.tools = []
        for tool in target.tools + source.tools:
            name = tool.get("name")
            if name not in tool_names:
                tool_names.add(name)
                merged.tools.append(tool)

        merged.update_hash()
        return merged

    def sync(
        self,
        source_id: str,
        target_id: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
    ) -> ContextDiff:
        """Synchronize context between two contexts.

        Args:
            source_id: Source context ID
            target_id: Target context ID
            direction: Sync direction

        Returns:
            Diff of changes applied
        """
        source = self._contexts.get(source_id)
        target = self._contexts.get(target_id)

        if not source:
            raise ValueError(f"Source context not found: {source_id}")
        if not target:
            raise ValueError(f"Target context not found: {target_id}")

        # Compute diff
        diff = self.diff(source, target)

        if diff.is_empty():
            return diff

        # Apply sync based on direction
        if direction == SyncDirection.BIDIRECTIONAL:
            merged = self.merge(source, target)
            self._contexts[source_id] = ContextState.from_dict(merged.to_dict())
            self._contexts[source_id].context_id = source_id
            self._contexts[target_id] = merged
        elif direction == SyncDirection.CLAUDE_TO_MS:
            # Source overwrites target
            merged = self.merge(target, source, ConflictResolution.TARGET_WINS)
            self._contexts[target_id] = merged
        elif direction == SyncDirection.MS_TO_CLAUDE:
            merged = self.merge(source, target, ConflictResolution.TARGET_WINS)
            self._contexts[source_id] = merged

        self._sync_count += 1
        self._last_sync_time = time.time()

        # Notify listeners
        for listener in self._sync_listeners:
            listener(self._contexts[target_id], direction)

        return diff

    def create_snapshot(
        self, context_id: str, label: str = ""
    ) -> ContextSnapshot:
        """Create a snapshot of context state.

        Args:
            context_id: Context ID to snapshot
            label: Optional label for snapshot

        Returns:
            Created snapshot
        """
        context = self._contexts.get(context_id)
        if not context:
            raise ValueError(f"Context not found: {context_id}")

        snapshot = ContextSnapshot(
            context_id=context_id,
            state=ContextState.from_dict(context.to_dict()),
            label=label,
        )

        if context_id not in self._snapshots:
            self._snapshots[context_id] = []
        self._snapshots[context_id].append(snapshot)

        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> ContextState:
        """Restore context from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore

        Returns:
            Restored context state
        """
        for snapshots in self._snapshots.values():
            for snapshot in snapshots:
                if snapshot.snapshot_id == snapshot_id:
                    restored = snapshot.restore()
                    self._contexts[restored.context_id] = restored
                    return restored

        raise ValueError(f"Snapshot not found: {snapshot_id}")

    def get_snapshots(self, context_id: str) -> List[ContextSnapshot]:
        """Get all snapshots for a context.

        Args:
            context_id: Context ID

        Returns:
            List of snapshots
        """
        return self._snapshots.get(context_id, [])

    def add_sync_listener(
        self, listener: Callable[[ContextState, SyncDirection], None]
    ) -> None:
        """Add a listener for sync events.

        Args:
            listener: Callback function
        """
        self._sync_listeners.append(listener)

    def remove_sync_listener(
        self, listener: Callable[[ContextState, SyncDirection], None]
    ) -> None:
        """Remove a sync listener.

        Args:
            listener: Callback to remove
        """
        if listener in self._sync_listeners:
            self._sync_listeners.remove(listener)

    def _convert_tools_to_claude(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tools to Claude format."""
        claude_tools = []
        for tool in tools:
            claude_tools.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", tool.get("input_schema", {})),
            })
        return claude_tools

    def _convert_tools_to_ms_agent(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tools to MS Agent Framework format."""
        ms_functions = []
        for tool in tools:
            ms_functions.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", tool.get("parameters", {})),
            })
        return ms_functions

    def _convert_tools_from_claude(
        self, claude_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert Claude format tools to unified format."""
        tools = []
        for ct in claude_tools:
            tools.append({
                "name": ct.get("name", ""),
                "description": ct.get("description", ""),
                "parameters": ct.get("input_schema", {}),
            })
        return tools

    def _convert_tools_from_ms_agent(
        self, ms_functions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert MS Agent format functions to unified format."""
        tools = []
        for mf in ms_functions:
            tools.append({
                "name": mf.get("name", ""),
                "description": mf.get("description", ""),
                "parameters": mf.get("parameters", {}),
            })
        return tools


def create_synchronizer(
    config: Optional[HybridSessionConfig] = None,
    conflict_resolution: ConflictResolution = ConflictResolution.LATEST_WINS,
) -> ContextSynchronizer:
    """Factory function to create a context synchronizer.

    Args:
        config: Hybrid session configuration
        conflict_resolution: Conflict resolution strategy

    Returns:
        Configured context synchronizer
    """
    return ContextSynchronizer(
        config=config,
        conflict_resolution=conflict_resolution,
    )
