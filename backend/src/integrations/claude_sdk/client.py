"""Claude Agent SDK Client wrapper."""

import uuid
from typing import Optional, List, Any, Dict, Callable, Awaitable, AsyncGenerator, TYPE_CHECKING

from anthropic import AsyncAnthropic

from .config import ClaudeSDKConfig
from .exceptions import ClaudeSDKError

if TYPE_CHECKING:
    from .types import QueryResult, Message, ThinkingEvent
    from .session import Session

# Type alias for thinking callback
ThinkingCallback = Callable[[str, int], Awaitable[None]]


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

    async def execute_with_thinking(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking_callback: Optional[ThinkingCallback] = None,
        max_tokens: int = 16000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute Claude API call with Extended Thinking content capture.

        Sprint 104: Extended Thinking Support

        This method streams the response and captures extended thinking
        (anthropic-beta: extended-thinking) content, calling the callback
        for each thinking update.

        Args:
            messages: List of message dicts for the conversation
            tools: Tool definitions for the request
            thinking_callback: Async callback (thinking_content: str, token_count: int) -> None
            max_tokens: Maximum tokens per response (default: 16000 for thinking)

        Yields:
            Event dicts from the streaming response

        Example:
            async def on_thinking(content: str, tokens: int):
                print(f"Thinking ({tokens} tokens): {content[:50]}...")

            async for event in client.execute_with_thinking(
                messages=[{"role": "user", "content": "Analyze this problem"}],
                thinking_callback=on_thinking,
            ):
                if event.get("type") == "text":
                    print(event.get("text"))
        """
        try:
            # Build request kwargs
            request_kwargs: Dict[str, Any] = {
                "model": self.config.model,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            if self.config.system_prompt:
                request_kwargs["system"] = self.config.system_prompt

            if tools:
                request_kwargs["tools"] = tools

            # Use streaming API with extended thinking beta
            # Note: Extended thinking requires anthropic-beta header
            extra_headers = {"anthropic-beta": "extended-thinking-2024-10"}

            async with self._client.messages.stream(
                **request_kwargs,
                extra_headers=extra_headers,
            ) as stream:
                current_thinking = ""
                current_block_type: Optional[str] = None

                async for event in stream:
                    event_type = getattr(event, "type", None)

                    if event_type == "content_block_start":
                        # Check if this is a thinking block
                        content_block = getattr(event, "content_block", None)
                        if content_block:
                            block_type = getattr(content_block, "type", None)
                            if block_type == "thinking":
                                current_block_type = "thinking"
                                current_thinking = ""
                            else:
                                current_block_type = block_type

                        yield {
                            "type": "content_block_start",
                            "block_type": current_block_type,
                        }

                    elif event_type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        if delta:
                            # Check for thinking delta
                            thinking_delta = getattr(delta, "thinking", None)
                            if thinking_delta:
                                current_thinking += thinking_delta
                                # Estimate token count (rough: ~4 chars per token)
                                token_count = len(current_thinking.split())

                                # Call thinking callback
                                if thinking_callback:
                                    await thinking_callback(current_thinking, token_count)

                                yield {
                                    "type": "thinking_delta",
                                    "thinking": current_thinking,
                                    "token_count": token_count,
                                }

                            # Check for text delta
                            text_delta = getattr(delta, "text", None)
                            if text_delta:
                                yield {
                                    "type": "text_delta",
                                    "text": text_delta,
                                }

                            # Check for tool use delta
                            if hasattr(delta, "type") and delta.type == "input_json_delta":
                                yield {
                                    "type": "tool_input_delta",
                                    "partial_json": getattr(delta, "partial_json", ""),
                                }

                    elif event_type == "content_block_stop":
                        if current_block_type == "thinking":
                            # Final thinking block complete
                            yield {
                                "type": "thinking_complete",
                                "content": current_thinking,
                                "token_count": len(current_thinking.split()),
                            }
                        current_block_type = None
                        yield {"type": "content_block_stop"}

                    elif event_type == "message_start":
                        yield {
                            "type": "message_start",
                            "message": {
                                "id": getattr(event.message, "id", None) if hasattr(event, "message") else None,
                                "model": getattr(event.message, "model", None) if hasattr(event, "message") else None,
                            },
                        }

                    elif event_type == "message_delta":
                        yield {
                            "type": "message_delta",
                            "stop_reason": getattr(event.delta, "stop_reason", None) if hasattr(event, "delta") else None,
                        }

                    elif event_type == "message_stop":
                        yield {"type": "message_stop"}

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
            }
