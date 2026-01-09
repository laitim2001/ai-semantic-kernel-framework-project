"""Claude Agent SDK Client wrapper."""

import uuid
from typing import Optional, List, Any, Dict, TYPE_CHECKING

from anthropic import AsyncAnthropic

from .config import ClaudeSDKConfig
from .exceptions import ClaudeSDKError

if TYPE_CHECKING:
    from .types import QueryResult, Message
    from .session import Session


class ClaudeSDKClient:
    """
    Claude Agent SDK Client for autonomous AI agent operations.

    Provides both one-shot query() and multi-turn session management.

    Example:
        # One-shot query
        result = await client.query("Analyze this code", tools=["Read", "Grep"])

        # Multi-turn session
        session = await client.create_session()
        await session.query("Read the auth module")
        await session.query("What issues do you see?")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        timeout: int = 300,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        hooks: Optional[List[Any]] = None,
        mcp_servers: Optional[List[Any]] = None,
    ):
        """
        Initialize Claude SDK Client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens per response
            timeout: Request timeout in seconds
            system_prompt: System prompt for all queries
            tools: List of built-in tools to enable
            hooks: List of Hook instances for behavior interception
            mcp_servers: List of MCP servers to connect
        """
        self.config = ClaudeSDKConfig(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
            system_prompt=system_prompt,
        )

        self._client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=float(self.config.timeout),
        )

        self.tools = tools or []
        self.hooks = hooks or []
        self.mcp_servers = mcp_servers or []
        self._sessions: Dict[str, "Session"] = {}

    async def query(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        working_directory: Optional[str] = None,
    ) -> "QueryResult":
        """
        Execute a one-shot autonomous task.

        Args:
            prompt: Task description
            tools: Override default tools for this query
            max_tokens: Override default max_tokens
            timeout: Override default timeout
            working_directory: Set working directory for file operations

        Returns:
            QueryResult with content, tool_calls, and metadata
        """
        from .query import execute_query

        return await execute_query(
            client=self._client,
            config=self.config,
            prompt=prompt,
            tools=tools or self.tools,
            max_tokens=max_tokens or self.config.max_tokens,
            timeout=timeout or self.config.timeout,
            working_directory=working_directory,
            hooks=self.hooks,
            mcp_servers=self.mcp_servers,
        )

    async def create_session(
        self,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List["Message"]] = None,
    ) -> "Session":
        """
        Create a new multi-turn conversation session.

        Args:
            session_id: Custom session identifier
            context: Initial context variables
            history: Pre-load conversation history

        Returns:
            Session instance for multi-turn interactions
        """
        from .session import Session

        sid = session_id or str(uuid.uuid4())
        session = Session(
            session_id=sid,
            client=self._client,
            config=self.config,
            tools=self.tools,
            hooks=self.hooks,
            mcp_servers=self.mcp_servers,
            context=context,
            history=history,
        )

        self._sessions[sid] = session

        # Trigger session start hooks
        for hook in self.hooks:
            await hook.on_session_start(sid)

        return session

    async def resume_session(self, session_id: str) -> "Session":
        """Resume an existing session by ID."""
        if session_id not in self._sessions:
            raise ClaudeSDKError(f"Session {session_id} not found")
        return self._sessions[session_id]

    def get_sessions(self) -> Dict[str, "Session"]:
        """Get all active sessions."""
        return self._sessions.copy()

    async def close(self):
        """Close client and all sessions."""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()
        await self._client.close()

    async def send_with_attachments(
        self,
        message: str,
        attachments: List[Dict[str, Any]],
        tools: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
    ) -> "QueryResult":
        """
        Send a message with file attachments.

        Sprint 75: File Attachment Support

        Args:
            message: User message text
            attachments: List of attachment dicts with:
                - id: File ID
                - name: Filename
                - mime_type: MIME type
                - content: File content (text or base64 for images)
                - is_image: Whether this is an image
            tools: Override default tools for this query
            max_tokens: Override default max_tokens

        Returns:
            QueryResult with content, tool_calls, and metadata
        """
        from .query import execute_query_with_attachments

        return await execute_query_with_attachments(
            client=self._client,
            config=self.config,
            message=message,
            attachments=attachments,
            tools=tools or self.tools,
            max_tokens=max_tokens or self.config.max_tokens,
            hooks=self.hooks,
            mcp_servers=self.mcp_servers,
        )
