"""One-shot query execution for Claude SDK."""

import time
from typing import Optional, List, Any

from anthropic import AsyncAnthropic

from .config import ClaudeSDKConfig
from .types import QueryResult, ToolCall, ToolCallContext, ToolResultContext
from .tools import get_tool_definitions, execute_tool
from .exceptions import TimeoutError


async def execute_query(
    client: AsyncAnthropic,
    config: ClaudeSDKConfig,
    prompt: str,
    tools: List[str],
    max_tokens: int,
    timeout: int,
    working_directory: Optional[str],
    hooks: List[Any],
    mcp_servers: List[Any],
) -> QueryResult:
    """
    Execute a one-shot autonomous query.

    Args:
        client: Anthropic client instance
        config: SDK configuration
        prompt: Task description
        tools: List of enabled tool names
        max_tokens: Maximum response tokens
        timeout: Timeout in seconds
        working_directory: Working directory for file operations
        hooks: List of hooks for interception
        mcp_servers: List of MCP servers

    Returns:
        QueryResult with response and metadata
    """
    start_time = time.time()
    tool_calls: List[ToolCall] = []
    total_tokens = 0

    try:
        # Get tool definitions for enabled tools
        tool_definitions = get_tool_definitions(tools, mcp_servers)

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Agentic loop - continue until task complete
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Query exceeded timeout of {timeout}s")

            # Call Claude API
            response = await client.messages.create(
                model=config.model,
                max_tokens=max_tokens,
                system=config.system_prompt or "",
                messages=messages,
                tools=tool_definitions if tool_definitions else None,
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens

            # Check for tool use
            has_tool_use = any(
                block.type == "tool_use" for block in response.content
            )

            if not has_tool_use:
                # No tool use - extract final response
                final_content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_content += block.text

                return QueryResult(
                    content=final_content,
                    tool_calls=tool_calls,
                    tokens_used=total_tokens,
                    duration=time.time() - start_time,
                    status="success",
                )

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_call = ToolCall(
                        id=block.id,
                        name=block.name,
                        args=block.input,
                    )
                    tool_calls.append(tool_call)

                    # Execute hook checks
                    hook_rejected = False
                    for hook in hooks:
                        hook_result = await hook.on_tool_call(
                            ToolCallContext(
                                tool_name=block.name,
                                args=block.input,
                                session_id=None,
                            )
                        )
                        if hook_result and hook_result.is_rejected:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Rejected: {hook_result.reason}",
                                "is_error": True,
                            })
                            hook_rejected = True
                            break

                    if hook_rejected:
                        continue

                    # Execute tool
                    try:
                        result = await execute_tool(
                            tool_name=block.name,
                            args=block.input,
                            working_directory=working_directory,
                            mcp_servers=mcp_servers,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                        # Trigger tool result hooks
                        for hook in hooks:
                            await hook.on_tool_result(
                                ToolResultContext(
                                    tool_name=block.name,
                                    result=result,
                                    success=True,
                                )
                            )

                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True,
                        })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    except TimeoutError:
        return QueryResult(
            content="",
            tool_calls=tool_calls,
            tokens_used=total_tokens,
            duration=time.time() - start_time,
            status="timeout",
            error="Query timed out",
        )

    except Exception as e:
        return QueryResult(
            content="",
            tool_calls=tool_calls,
            tokens_used=total_tokens,
            duration=time.time() - start_time,
            status="error",
            error=str(e),
        )
