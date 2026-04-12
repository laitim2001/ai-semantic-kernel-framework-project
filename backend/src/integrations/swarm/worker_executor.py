"""SwarmWorkerExecutor — individual Worker agent execution with LLM + tools.

Each Worker runs independently with its own role-specific system prompt,
tool subset, and message history. Emits SSE events during execution for
real-time frontend visualization.

Sprint 148 — Phase 43 Swarm Core Engine.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.integrations.swarm.worker_roles import get_role
from src.integrations.swarm.task_decomposer import DecomposedTask

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 5


@dataclass
class WorkerResult:
    """Outcome of a single Worker execution."""

    worker_id: str
    role: str
    task_title: str
    status: str  # "completed" | "failed" | "timeout"
    content: str = ""
    tool_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    thinking_steps: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    error: Optional[str] = None


class SwarmWorkerExecutor:
    """Executes a single Worker agent with real LLM + function calling.

    Each Worker:
    - Has a role-specific system prompt
    - Uses a filtered tool subset based on its role
    - Runs an independent function calling loop
    - Emits SSE events for thinking, tool calls, progress

    Args:
        worker_id: Unique worker identifier.
        task: The decomposed sub-task to execute.
        llm_service: LLM service with chat_with_tools() support.
        tool_registry: Tool registry for executing tools.
        event_emitter: SSE event emitter for real-time updates.
        timeout: Maximum execution time in seconds.
    """

    def __init__(
        self,
        worker_id: str,
        task: DecomposedTask,
        llm_service: Any,
        tool_registry: Any,
        event_emitter: Optional[Any] = None,
        timeout: float = 60.0,
    ) -> None:
        self._worker_id = worker_id
        self._task = task
        self._llm = llm_service
        self._tool_registry = tool_registry
        self._emitter = event_emitter
        self._timeout = timeout
        self._role_def = get_role(task.role)

    async def execute(self) -> WorkerResult:
        """Execute the worker's sub-task with LLM + function calling.

        Returns:
            WorkerResult with content, tool calls, thinking steps.
        """
        start_time = time.time()
        thinking_steps: List[Dict[str, Any]] = []
        tool_calls_made: List[Dict[str, Any]] = []
        messages: List[Dict[str, Any]] = []

        try:
            # Emit SWARM_WORKER_START
            await self._emit("SWARM_WORKER_START", {
                "worker_id": self._worker_id,
                "agent_name": self._role_def.get("name", "Worker"),
                "display_name": self._role_def.get("display_name", "Worker"),
                "role": self._task.role,
                "task": self._task.title,
                "task_description": self._task.description,
            })

            # Build messages with role-specific system prompt
            system_prompt = (
                f"{self._role_def.get('system_prompt', '')}\n\n"
                f"## 你的任務\n{self._task.description}"
            )
            working_messages: List[Dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._task.description},
            ]
            messages.extend(working_messages)

            # Get role-filtered tool schemas
            tool_schemas = self._get_filtered_tool_schemas()

            # Function calling loop
            for iteration in range(_MAX_TOOL_ITERATIONS):
                elapsed = time.time() - start_time
                if elapsed > self._timeout:
                    logger.warning(
                        "Worker %s: timeout after %.1fs", self._worker_id, elapsed
                    )
                    return WorkerResult(
                        worker_id=self._worker_id,
                        role=self._task.role,
                        task_title=self._task.title,
                        status="timeout",
                        content=f"Worker 執行超時 ({self._timeout}s)",
                        tool_calls_made=tool_calls_made,
                        thinking_steps=thinking_steps,
                        messages=messages,
                        duration_ms=(time.time() - start_time) * 1000,
                        error="Execution timeout",
                    )

                # Update progress
                progress = min(90, int((iteration + 1) / _MAX_TOOL_ITERATIONS * 80) + 10)
                await self._emit("SWARM_WORKER_PROGRESS", {
                    "worker_id": self._worker_id,
                    "progress": progress,
                    "current_action": f"Iteration {iteration + 1}",
                    "status": "running",
                })

                # Call LLM with tools
                # Force text response on last iteration to prevent infinite tool loops
                is_last_iteration = iteration >= _MAX_TOOL_ITERATIONS - 1
                try:
                    if tool_schemas and hasattr(self._llm, "chat_with_tools"):
                        result = await self._llm.chat_with_tools(
                            messages=working_messages,
                            tools=tool_schemas,
                            tool_choice="auto" if not is_last_iteration else "none",
                            max_tokens=2048,
                            temperature=0.7,
                        )
                    else:
                        # Fallback: no tools
                        content = await self._llm.generate(
                            prompt="\n".join(
                                f"[{m['role']}] {m.get('content', '')}"
                                for m in working_messages
                            ),
                            max_tokens=2048,
                            temperature=0.7,
                        )
                        result = {"content": content, "tool_calls": None, "finish_reason": "stop"}
                except Exception as llm_err:
                    logger.error("Worker %s: LLM call failed: %s", self._worker_id, llm_err)
                    # Retry once
                    if iteration == 0:
                        continue
                    return WorkerResult(
                        worker_id=self._worker_id,
                        role=self._task.role,
                        task_title=self._task.title,
                        status="failed",
                        content="",
                        tool_calls_made=tool_calls_made,
                        thinking_steps=thinking_steps,
                        messages=messages,
                        duration_ms=(time.time() - start_time) * 1000,
                        error=str(llm_err),
                    )

                content = result.get("content") or ""
                tool_calls = result.get("tool_calls")

                # Emit thinking event
                if content:
                    step = {
                        "iteration": iteration,
                        "content": content,
                        "timestamp": time.time(),
                        "has_tool_calls": bool(tool_calls),
                    }
                    thinking_steps.append(step)
                    await self._emit("SWARM_WORKER_THINKING", {
                        "worker_id": self._worker_id,
                        "content": content[:500],
                        "iteration": iteration,
                    })

                # Process tool calls
                if tool_calls:
                    working_messages.append({
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
                        except json.JSONDecodeError:
                            tool_args = {}

                        # Emit tool call event
                        await self._emit("SWARM_WORKER_TOOL_CALL", {
                            "worker_id": self._worker_id,
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "status": "running",
                        })

                        # Execute tool
                        tool_result = await self._execute_tool(tool_name, tool_args)

                        tool_calls_made.append({
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "result": tool_result,
                            "iteration": iteration,
                        })

                        # Emit tool call completed
                        await self._emit("SWARM_WORKER_TOOL_CALL", {
                            "worker_id": self._worker_id,
                            "tool_name": tool_name,
                            "result": tool_result,
                            "status": "completed",
                        })

                        working_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                        })
                        messages.append({"role": "tool", "tool_name": tool_name, "result": tool_result})
                else:
                    # No tool calls — final response
                    # If content is empty, retry with tool_choice="none" to force text output
                    # keeping full chat history (tool results) for context
                    if not content.strip():
                        logger.info(
                            "Worker %s: empty content on iteration %d (tool_calls_made=%d), forcing text response",
                            self._worker_id, iteration, len(tool_calls_made),
                        )
                        try:
                            # Add instruction to produce analysis, then call with tool_choice="none"
                            retry_messages = working_messages + [{
                                "role": "user",
                                "content": "請根據以上所有資訊和工具結果，直接用你的專業知識完成分析並回答任務。給出具體的診斷結果和建議。",
                            }]
                            retry_result = await self._llm.chat_with_tools(
                                messages=retry_messages,
                                tools=tool_schemas,
                                tool_choice="none",
                                max_tokens=2048,
                                temperature=0.7,
                            )
                            content = retry_result.get("content") or ""
                        except Exception as retry_err:
                            logger.warning("Worker %s: forced text retry failed: %s", self._worker_id, retry_err)

                        # Final fallback: generate() without chat context
                        if not content.strip():
                            try:
                                content = await self._llm.generate(
                                    prompt=(
                                        f"{self._role_def.get('system_prompt', '')}\n\n"
                                        f"## 任務\n{self._task.description}\n\n"
                                        f"請直接用你的專業知識分析並回答。"
                                    ),
                                    max_tokens=2048,
                                    temperature=0.7,
                                )
                            except Exception as gen_err:
                                logger.warning("Worker %s: generate fallback failed: %s", self._worker_id, gen_err)
                                content = f"Worker {self._worker_id} 已完成分析但無法生成摘要。"

                    messages.append({"role": "assistant", "content": content})
                    duration_ms = (time.time() - start_time) * 1000

                    await self._emit("SWARM_WORKER_COMPLETED", {
                        "worker_id": self._worker_id,
                        "status": "completed",
                        "content_preview": content[:200],
                        "tool_calls_count": len(tool_calls_made),
                        "duration_ms": round(duration_ms, 2),
                    })

                    return WorkerResult(
                        worker_id=self._worker_id,
                        role=self._task.role,
                        task_title=self._task.title,
                        status="completed",
                        content=content,
                        tool_calls_made=tool_calls_made,
                        thinking_steps=thinking_steps,
                        messages=messages,
                        duration_ms=duration_ms,
                    )

            # Max iterations reached — force final text response with full chat context
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Worker %s: max iterations reached (thinking_steps=%d, tool_calls=%d)",
                self._worker_id, len(thinking_steps), len(tool_calls_made),
            )
            last_content = thinking_steps[-1]["content"] if thinking_steps else ""
            if not last_content.strip():
                # Retry with tool_choice="none" preserving full chat history
                try:
                    retry_messages = working_messages + [{
                        "role": "user",
                        "content": "請根據以上所有資訊和工具結果，直接用你的專業知識完成分析並回答任務。給出具體的診斷結果和建議。",
                    }]
                    retry_result = await self._llm.chat_with_tools(
                        messages=retry_messages,
                        tools=tool_schemas,
                        tool_choice="none",
                        max_tokens=2048,
                        temperature=0.7,
                    )
                    last_content = retry_result.get("content") or ""
                except Exception as retry_err:
                    logger.warning("Worker %s: max-iter forced text failed: %s", self._worker_id, retry_err)

                if not last_content.strip():
                    last_content = f"Worker {self._worker_id} 已完成分析但無法生成摘要。"

            await self._emit("SWARM_WORKER_COMPLETED", {
                "worker_id": self._worker_id,
                "status": "completed",
                "content_preview": last_content[:200],
                "tool_calls_count": len(tool_calls_made),
                "duration_ms": round(duration_ms, 2),
            })

            return WorkerResult(
                worker_id=self._worker_id,
                role=self._task.role,
                task_title=self._task.title,
                status="completed",
                content=last_content,
                tool_calls_made=tool_calls_made,
                thinking_steps=thinking_steps,
                messages=messages,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Worker %s failed: %s", self._worker_id, exc, exc_info=True)

            await self._emit("SWARM_WORKER_FAILED", {
                "worker_id": self._worker_id,
                "error": str(exc),
                "duration_ms": round(duration_ms, 2),
            })

            return WorkerResult(
                worker_id=self._worker_id,
                role=self._task.role,
                task_title=self._task.title,
                status="failed",
                tool_calls_made=tool_calls_made,
                thinking_steps=thinking_steps,
                messages=messages,
                duration_ms=duration_ms,
                error=str(exc),
            )

    def _get_filtered_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI tool schemas filtered by this worker's role."""
        if not self._tool_registry:
            return []

        allowed_tools = set(self._role_def.get("tools", []))
        all_schemas = self._tool_registry.get_openai_tool_schemas(role="admin")

        return [
            schema for schema in all_schemas
            if schema.get("function", {}).get("name") in allowed_tools
        ]

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via the registry."""
        if not self._tool_registry:
            return {"error": f"Tool registry unavailable for '{tool_name}'"}

        try:
            result = await self._tool_registry.execute(
                tool_name=tool_name,
                params=tool_args,
                user_id=f"swarm-worker-{self._worker_id}",
                role="admin",
            )
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an SSE event if emitter is available."""
        if self._emitter and hasattr(self._emitter, "emit"):
            try:
                from src.integrations.hybrid.orchestrator.sse_events import SSEEventType
                # Map swarm-specific events to known SSE types
                type_map = {
                    "SWARM_WORKER_START": SSEEventType.SWARM_WORKER_START,
                    "SWARM_WORKER_THINKING": SSEEventType.SWARM_PROGRESS,
                    "SWARM_WORKER_TOOL_CALL": SSEEventType.SWARM_PROGRESS,
                    "SWARM_WORKER_PROGRESS": SSEEventType.SWARM_PROGRESS,
                    "SWARM_WORKER_COMPLETED": SSEEventType.SWARM_PROGRESS,
                    "SWARM_WORKER_FAILED": SSEEventType.PIPELINE_ERROR,
                }
                sse_type = type_map.get(event_type, SSEEventType.SWARM_PROGRESS)
                import asyncio
                await self._emitter.emit(sse_type, {"event_subtype": event_type, **data})
                await asyncio.sleep(0)  # yield for SSE streaming
            except Exception:
                pass
