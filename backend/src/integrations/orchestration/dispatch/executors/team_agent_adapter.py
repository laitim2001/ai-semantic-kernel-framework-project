"""
TeamAgentAdapter — Wraps CachedLLMService to provide MAF Agent-compatible interface.

Bridges the production LLM service (CachedLLMService → AzureOpenAILLMService)
with the PoC's agent_work_loop.py which expects objects with .run(context) and .name.

The PoC's _sync_agent_run() calls agent.run(context) in a thread with a fresh
event loop. This adapter's .run() is async and uses chat_with_tools() — the same
proven loop from SwarmWorkerExecutor.

Phase 45: Sprint C — PoC Persistent Loop integration.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response object with .content attribute (MAF Agent.run() compatibility)."""
    content: str


class TeamAgentAdapter:
    """MAF Agent-compatible adapter wrapping CachedLLMService.

    Provides:
        - .run(context) → async, returns AgentResponse with .content
        - .name → agent name string
        - .tools → tool list (for compatibility)

    Used by agent_work_loop._sync_agent_run() which calls:
        loop.run_until_complete(agent.run(context))
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: Any = None,
        name: str = "Agent",
        instructions: str = "",
        tools: Optional[List] = None,
        max_iterations: int = 5,
    ):
        self._llm = llm_service
        self._tool_registry = tool_registry
        self._name = name
        self._instructions = instructions
        self._tools = tools or []
        self._max_iterations = max_iterations

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: str) -> AgentResponse:
        """Execute a chat_with_tools loop and return the final text response.

        Mirrors SwarmWorkerExecutor's proven LLM loop but in a simpler form
        compatible with agent_work_loop's _sync_agent_run().
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._instructions or f"You are {self._name}."},
            {"role": "user", "content": context},
        ]

        # Get tool schemas if registry available
        tool_schemas = self._get_tool_schemas()

        for iteration in range(self._max_iterations):
            is_last = iteration >= self._max_iterations - 1

            try:
                if tool_schemas and hasattr(self._llm, "chat_with_tools"):
                    result = await self._llm.chat_with_tools(
                        messages=messages,
                        tools=tool_schemas,
                        tool_choice="auto" if not is_last else "none",
                        max_tokens=4096,
                        temperature=0.7,
                    )
                else:
                    # No tools — direct generate
                    content = await self._llm.generate(
                        prompt=context,
                        max_tokens=4096,
                        temperature=0.7,
                    )
                    return AgentResponse(content=content or "")
            except Exception as e:
                logger.error("TeamAgentAdapter %s: LLM call failed iter %d: %s", self._name, iteration, e)
                if iteration == 0:
                    continue
                return AgentResponse(content=f"ERROR: {str(e)[:200]}")

            content = result.get("content") or ""
            tool_calls = result.get("tool_calls")
            finish_reason = result.get("finish_reason", "stop")

            # Tool calls — execute and continue loop
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in tool_calls
                    ],
                })
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        tool_args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        tool_args = {}

                    tool_result = await self._execute_tool(tool_name, tool_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                    })
                continue

            # No tool calls — final response
            if content.strip():
                return AgentResponse(content=content)

            # Empty content (possibly finish_reason=length) — compact retry
            if finish_reason == "length" or not content.strip():
                try:
                    compact = [
                        {"role": "system", "content": self._instructions or f"You are {self._name}."},
                        {"role": "user", "content": (
                            f"{context}\n\n"
                            f"請直接用你的專業知識完成分析。給出具體的診斷結果和建議。"
                        )},
                    ]
                    retry = await self._llm.chat_with_tools(
                        messages=compact, tools=None, max_tokens=4096, temperature=0.7,
                    )
                    retry_content = retry.get("content") or ""
                    if retry_content.strip():
                        return AgentResponse(content=retry_content)
                except Exception:
                    pass

                # Final fallback
                try:
                    fallback = await self._llm.generate(
                        prompt=f"{self._instructions}\n\n{context}\n\n請直接回答。",
                        max_tokens=4096, temperature=0.7,
                    )
                    return AgentResponse(content=fallback or f"Agent {self._name} 完成分析但無法生成報告。")
                except Exception:
                    return AgentResponse(content=f"Agent {self._name} 完成分析但無法生成報告。")

        # Max iterations reached
        return AgentResponse(content=f"Agent {self._name} 達到最大迭代次數。")

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-format tool schemas from registry."""
        if not self._tool_registry:
            return []
        try:
            return self._tool_registry.get_openai_tool_schemas(role="admin")
        except Exception:
            return []

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via the registry."""
        if not self._tool_registry:
            return {"error": f"Tool registry unavailable for '{tool_name}'"}
        try:
            result = await self._tool_registry.execute(
                tool_name=tool_name,
                params=tool_args,
                user_id=f"agent-{self._name}",
                role="admin",
            )
            return {"success": result.success, "data": result.data, "error": result.error}
        except Exception as e:
            return {"success": False, "error": str(e)}
