# =============================================================================
# IPA Platform - Agentic Chat Handler
# =============================================================================
# Sprint 59: AG-UI Basic Features
# S59-1: Agentic Chat (7 pts)
#
# Agentic Chat feature handler that provides real-time streaming conversation
# with agents using the AG-UI protocol.
#
# Key Features:
#   - Integration with HybridOrchestratorV2 for intelligent execution
#   - Integration with HybridEventBridge for AG-UI event streaming
#   - Support for tool calls embedded in conversation
#   - Session and thread management
#
# Dependencies:
#   - HybridOrchestratorV2 (src.integrations.hybrid.orchestrator_v2)
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

from src.integrations.ag_ui.bridge import (
    HybridEventBridge,
    RunAgentInput,
    BridgeConfig,
)
from src.integrations.ag_ui.events import (
    BaseAGUIEvent,
    AGUIEventType,
    CustomEvent,
)

if TYPE_CHECKING:
    from src.integrations.hybrid.orchestrator_v2 import HybridOrchestratorV2
    from src.integrations.hybrid.intent import ExecutionMode

logger = logging.getLogger(__name__)


class ChatRole(str, Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """
    A single chat message.

    Attributes:
        role: Role of the message sender
        content: Message content
        id: Unique message ID
        timestamp: Message timestamp
        tool_calls: Associated tool calls (for assistant messages)
        tool_call_id: ID of the tool call (for tool messages)
        metadata: Additional metadata
    """

    role: ChatRole
    content: str
    id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "role": self.role.value,
            "content": self.content,
            "id": self.id,
            "timestamp": self.timestamp,
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create from dictionary representation."""
        return cls(
            role=ChatRole(data.get("role", "user")),
            content=data.get("content", ""),
            id=data.get("id", f"msg-{uuid.uuid4().hex[:12]}"),
            timestamp=data.get("timestamp", time.time()),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChatConfig:
    """
    Configuration for chat handling.

    Attributes:
        max_history_length: Maximum number of messages to keep in history
        enable_intent_analysis: Whether to enable intent analysis
        enable_tool_calls: Whether to enable tool calls
        default_timeout: Default timeout for execution
        stream_chunk_size: Size of text chunks for streaming
    """

    max_history_length: int = 50
    enable_intent_analysis: bool = True
    enable_tool_calls: bool = True
    default_timeout: float = 300.0
    stream_chunk_size: int = 100


@dataclass
class ChatSession:
    """
    Chat session state.

    Attributes:
        session_id: Unique session ID
        thread_id: Associated thread ID
        messages: Conversation messages
        metadata: Session metadata
        created_at: Session creation time
        last_activity: Last activity timestamp
    """

    session_id: str
    thread_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)


class AgenticChatHandler:
    """
    Agentic Chat feature handler.

    Provides real-time streaming conversation with agents using
    the AG-UI protocol and HybridOrchestratorV2 for intelligent execution.

    Key Features:
    - Stream chat responses as AG-UI events
    - Support for tool calls embedded in conversation
    - Intent analysis for mode selection
    - Session and thread management

    Example:
        >>> orchestrator = HybridOrchestratorV2()
        >>> bridge = HybridEventBridge(orchestrator=orchestrator)
        >>> handler = AgenticChatHandler(
        ...     orchestrator=orchestrator,
        ...     event_bridge=bridge,
        ... )
        >>> async for event in handler.handle_chat(
        ...     thread_id="thread-123",
        ...     message="Hello, how can you help?",
        ... ):
        ...     print(event)
    """

    def __init__(
        self,
        *,
        orchestrator: "HybridOrchestratorV2",
        event_bridge: HybridEventBridge,
        config: Optional[ChatConfig] = None,
    ):
        """
        Initialize AgenticChatHandler.

        Args:
            orchestrator: HybridOrchestratorV2 instance for execution
            event_bridge: HybridEventBridge for AG-UI event streaming
            config: Optional chat configuration
        """
        self._orchestrator = orchestrator
        self._event_bridge = event_bridge
        self._config = config or ChatConfig()

        # Session storage (in-memory, can be replaced with persistent storage)
        self._sessions: Dict[str, ChatSession] = {}

        logger.info(
            f"AgenticChatHandler initialized: "
            f"intent_analysis={self._config.enable_intent_analysis}, "
            f"tool_calls={self._config.enable_tool_calls}"
        )

    @property
    def orchestrator(self) -> "HybridOrchestratorV2":
        """Get the orchestrator instance."""
        return self._orchestrator

    @property
    def event_bridge(self) -> HybridEventBridge:
        """Get the event bridge instance."""
        return self._event_bridge

    @property
    def config(self) -> ChatConfig:
        """Get the chat configuration."""
        return self._config

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def create_session(
        self,
        thread_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            thread_id: Thread ID for conversation context
            session_id: Optional custom session ID
            metadata: Optional session metadata

        Returns:
            The created ChatSession
        """
        sid = session_id or str(uuid.uuid4())
        session = ChatSession(
            session_id=sid,
            thread_id=thread_id,
            metadata=metadata or {},
        )
        self._sessions[sid] = session
        logger.info(f"Created chat session: {sid} for thread: {thread_id}")
        return session

    def get_or_create_session(
        self,
        thread_id: str,
        session_id: Optional[str] = None,
    ) -> ChatSession:
        """
        Get or create a chat session.

        Args:
            thread_id: Thread ID for conversation context
            session_id: Optional session ID to look up

        Returns:
            Existing or new ChatSession
        """
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session(thread_id, session_id)

    def close_session(self, session_id: str) -> bool:
        """
        Close and remove a session.

        Args:
            session_id: Session ID to close

        Returns:
            True if session was closed, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Closed chat session: {session_id}")
            return True
        return False

    def add_message(
        self,
        session_id: str,
        message: ChatMessage,
    ) -> bool:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            message: Message to add

        Returns:
            True if message was added, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.messages.append(message)
        session.last_activity = time.time()

        # Trim history if needed
        if len(session.messages) > self._config.max_history_length:
            session.messages = session.messages[-self._config.max_history_length :]

        return True

    async def handle_chat(
        self,
        thread_id: str,
        message: str,
        *,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        force_mode: Optional["ExecutionMode"] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[BaseAGUIEvent, None]:
        """
        Handle a chat message and stream AG-UI events.

        This is the main entry point for chat handling.
        The method:
        1. Gets or creates a session
        2. Adds the user message to history
        3. Creates RunAgentInput
        4. Streams events via event bridge
        5. Adds assistant response to history

        Args:
            thread_id: Thread ID for conversation context
            message: User message content
            session_id: Optional session ID
            run_id: Optional run ID
            force_mode: Force specific execution mode
            tools: Available tools for execution
            max_tokens: Maximum tokens for response
            timeout: Execution timeout in seconds
            metadata: Additional metadata

        Yields:
            AG-UI events (BaseAGUIEvent instances)
        """
        # 1. Get or create session
        session = self.get_or_create_session(thread_id, session_id)

        # 2. Add user message to history
        user_message = ChatMessage(
            role=ChatRole.USER,
            content=message,
            metadata=metadata or {},
        )
        self.add_message(session.session_id, user_message)

        # 3. Create RunAgentInput
        run_input = RunAgentInput(
            prompt=message,
            thread_id=thread_id,
            run_id=run_id,
            session_id=session.session_id,
            force_mode=force_mode,
            tools=tools if self._config.enable_tool_calls else None,
            max_tokens=max_tokens,
            timeout=timeout or self._config.default_timeout,
            metadata={
                **(metadata or {}),
                "chat_handler": "AgenticChatHandler",
                "message_id": user_message.id,
            },
        )

        # 4. Stream events via event bridge
        assistant_content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []

        async for event in self._event_bridge.stream_events_raw(run_input):
            # Collect assistant content for history
            if event.type == AGUIEventType.TEXT_MESSAGE_CONTENT:
                if hasattr(event, "delta") and event.delta:
                    assistant_content_parts.append(event.delta)

            # Collect tool calls for history
            elif event.type == AGUIEventType.TOOL_CALL_END:
                if hasattr(event, "tool_call_id") and hasattr(event, "tool_name"):
                    tool_calls.append({
                        "id": getattr(event, "tool_call_id", ""),
                        "name": getattr(event, "tool_name", ""),
                        "result": getattr(event, "result", None),
                        "error": getattr(event, "error", None),
                    })

            yield event

        # 5. Add assistant message to history
        assistant_content = "".join(assistant_content_parts)
        if assistant_content or tool_calls:
            assistant_message = ChatMessage(
                role=ChatRole.ASSISTANT,
                content=assistant_content,
                tool_calls=tool_calls if tool_calls else None,
            )
            self.add_message(session.session_id, assistant_message)

    async def handle_chat_sse(
        self,
        thread_id: str,
        message: str,
        *,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        force_mode: Optional["ExecutionMode"] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Handle a chat message and stream SSE-formatted events.

        Same as handle_chat but yields SSE-formatted strings
        instead of BaseAGUIEvent objects.

        Args:
            thread_id: Thread ID for conversation context
            message: User message content
            session_id: Optional session ID
            run_id: Optional run ID
            force_mode: Force specific execution mode
            tools: Available tools for execution
            max_tokens: Maximum tokens for response
            timeout: Execution timeout in seconds
            metadata: Additional metadata

        Yields:
            SSE-formatted event strings ("data: {...}\\n\\n")
        """
        async for event in self.handle_chat(
            thread_id=thread_id,
            message=message,
            session_id=session_id,
            run_id=run_id,
            force_mode=force_mode,
            tools=tools,
            max_tokens=max_tokens,
            timeout=timeout,
            metadata=metadata,
        ):
            yield event.to_sse()

    def get_conversation_history(
        self,
        session_id: str,
        *,
        limit: Optional[int] = None,
        include_system: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            include_system: Whether to include system messages

        Returns:
            List of message dictionaries
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        messages = session.messages
        if not include_system:
            messages = [m for m in messages if m.role != ChatRole.SYSTEM]
        if limit:
            messages = messages[-limit:]

        return [m.to_dict() for m in messages]

    async def emit_typing_indicator(
        self,
        thread_id: str,
        run_id: str,
        is_typing: bool = True,
    ) -> CustomEvent:
        """
        Create a typing indicator custom event.

        Args:
            thread_id: Thread ID
            run_id: Run ID
            is_typing: Whether typing is in progress

        Returns:
            CustomEvent for typing indicator
        """
        return CustomEvent(
            type=AGUIEventType.CUSTOM,
            name="typing_indicator",
            value={
                "thread_id": thread_id,
                "run_id": run_id,
                "is_typing": is_typing,
            },
        )


def create_chat_handler(
    *,
    orchestrator: "HybridOrchestratorV2",
    event_bridge: Optional[HybridEventBridge] = None,
    config: Optional[ChatConfig] = None,
) -> AgenticChatHandler:
    """
    Factory function to create AgenticChatHandler.

    Args:
        orchestrator: HybridOrchestratorV2 instance
        event_bridge: Optional HybridEventBridge (created if not provided)
        config: Optional ChatConfig

    Returns:
        Configured AgenticChatHandler instance
    """
    if not event_bridge:
        from src.integrations.ag_ui.bridge import create_bridge

        event_bridge = create_bridge(orchestrator=orchestrator)

    return AgenticChatHandler(
        orchestrator=orchestrator,
        event_bridge=event_bridge,
        config=config,
    )
