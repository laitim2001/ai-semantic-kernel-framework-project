"""
AgentHandler — LLM Decision Engine with Function Calling.

Serves as the Agent backend within the OrchestratorMediator pipeline,
receiving results from upstream Handlers (Routing, Dialog, Approval)
and using LLM to generate intelligent responses.

Sprint 107 — Phase 35 A0 core assumption validation.
Sprint 144 — Phase 42 Function Calling integration.
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)
from src.integrations.hybrid.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from src.integrations.llm.protocol import LLMServiceProtocol

if TYPE_CHECKING:
    from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry

logger = logging.getLogger(__name__)

# Default response when LLM service is not configured
_LLM_NOT_CONFIGURED_RESPONSE = (
    "LLM 服務尚未配置，無法生成智能回應。請聯繫系統管理員配置 LLM 服務。"
)

# Maximum iterations for the function calling loop
_MAX_TOOL_ITERATIONS = 5


class AgentHandler(Handler):
    """Handler that uses LLM to generate intelligent responses.

    Positioned in the pipeline after Approval and before Execution.
    For simple conversational requests, the AgentHandler can produce
    a direct response and short-circuit the pipeline (skipping Execution).

    Sprint 144: Now supports Azure OpenAI function calling.  When tools
    are available, the handler sends tool schemas to the LLM and executes
    any tool_calls the model requests, looping until the model produces
    a final text response (or hits max iterations).
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        tool_registry: Optional["OrchestratorToolRegistry"] = None,
    ) -> None:
        self._llm_service = llm_service
        self._tool_registry = tool_registry

    @property
    def handler_type(self) -> HandlerType:
        """Return the handler's type identifier."""
        return HandlerType.AGENT

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Generate an LLM-powered response using pipeline context.

        Steps:
            1. Extract routing_decision from context.
            2. Build messages for chat completions.
            3. If tools available, use function calling loop.
            4. Otherwise, fall back to generate().
            5. Return the response wrapped in a HandlerResult.
        """
        routing_decision = context.get("routing_decision") or (
            request.metadata.get("routing_decision") if request.metadata else None
        )
        user_input = request.content

        # --- Graceful degradation when LLM is not available ----------------
        if self._llm_service is None:
            logger.warning("AgentHandler: LLM service not configured, returning fallback response")
            return HandlerResult(
                success=True,
                handler_type=HandlerType.AGENT,
                data={
                    "content": _LLM_NOT_CONFIGURED_RESPONSE,
                    "agent_source": "fallback",
                },
                should_short_circuit=True,
                short_circuit_response={
                    "content": _LLM_NOT_CONFIGURED_RESPONSE,
                    "framework_used": "agent_fallback",
                },
            )

        # --- Build messages -------------------------------------------------
        messages = self._build_messages(request, context, routing_decision)

        # --- REFACTOR-001: Use llm_service.chat_with_tools() ---------------
        tool_calls_made: List[Dict[str, Any]] = []
        try:
            tool_schemas = self._get_tool_schemas(request)
            has_tools_support = hasattr(self._llm_service, "chat_with_tools")

            if tool_schemas and has_tools_support:
                llm_response, tool_calls_made = await self._function_calling_loop(
                    messages, tool_schemas, request, context,
                )
            else:
                llm_response = await self._fallback_generate(messages, request)

            logger.info(
                "AgentHandler: response generated for request %s "
                "(tool_calls=%d)",
                request.request_id,
                len(tool_calls_made),
            )

            # Determine short-circuit
            from src.integrations.hybrid.intent import ExecutionMode
            exec_mode = context.get("execution_mode", ExecutionMode.CHAT_MODE)
            is_chat_mode = exec_mode in (ExecutionMode.CHAT_MODE, "chat")
            needs_swarm = bool(context.get("swarm_decomposition"))
            should_sc = is_chat_mode and not needs_swarm

            result_data: Dict[str, Any] = {
                "content": llm_response,
                "agent_source": "llm",
                "framework_used": "orchestrator_agent",
            }
            if tool_calls_made:
                result_data["tool_calls"] = tool_calls_made

            return HandlerResult(
                success=True,
                handler_type=HandlerType.AGENT,
                data=result_data,
                should_short_circuit=should_sc,
                short_circuit_response={
                    "content": llm_response,
                    "framework_used": "orchestrator_agent",
                    "tool_calls": tool_calls_made if tool_calls_made else None,
                } if should_sc else None,
            )

        except Exception as exc:
            logger.error(
                "AgentHandler: LLM call failed for request %s: %s",
                request.request_id,
                exc,
                exc_info=True,
            )
            error_response = (
                "抱歉，AI 助手暫時無法回應。請稍後再試或聯繫系統管理員。"
            )
            return HandlerResult(
                success=False,
                handler_type=HandlerType.AGENT,
                data={
                    "content": error_response,
                    "agent_source": "error",
                },
                error=str(exc),
                should_short_circuit=True,
                short_circuit_response={
                    "content": error_response,
                    "framework_used": "orchestrator_agent",
                    "error": str(exc),
                },
            )

    # ------------------------------------------------------------------
    # Function Calling Loop (Sprint 144)
    # ------------------------------------------------------------------

    async def _function_calling_loop(
        self,
        messages: List[Dict[str, str]],
        tool_schemas: List[Dict[str, Any]],
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> tuple:
        """Execute the function calling loop via LLMServiceProtocol.

        REFACTOR-001: Uses llm_service.chat_with_tools() instead of
        direct OpenAI client access.

        Returns:
            (response_text, list_of_tool_calls_made)
        """
        tool_calls_made: List[Dict[str, Any]] = []
        working_messages = list(messages)
        last_content = ""

        for iteration in range(_MAX_TOOL_ITERATIONS):
            try:
                result = await self._llm_service.chat_with_tools(
                    messages=working_messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    max_tokens=2048,
                    temperature=0.7,
                )
            except Exception as e:
                logger.warning(
                    "AgentHandler: chat_with_tools failed (iter=%d): %s",
                    iteration, e,
                )
                return await self._fallback_generate(messages, request), tool_calls_made

            content = result.get("content") or ""
            tool_calls = result.get("tool_calls")
            last_content = content

            if tool_calls:
                # Append assistant message with tool_calls
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

                    logger.info(
                        "AgentHandler: executing tool '%s' (iter=%d)",
                        tool_name, iteration,
                    )

                    tool_result = await self._execute_tool(
                        tool_name, tool_args, request, context,
                    )

                    tool_calls_made.append({
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "result": tool_result,
                        "iteration": iteration,
                    })

                    working_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(
                            tool_result, ensure_ascii=False, default=str,
                        ),
                    })
            else:
                return content, tool_calls_made

        logger.warning(
            "AgentHandler: max tool iterations (%d) reached",
            _MAX_TOOL_ITERATIONS,
        )
        return (
            last_content or f"已執行 {len(tool_calls_made)} 個工具操作。"
        ), tool_calls_made

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool via the OrchestratorToolRegistry."""
        if self._tool_registry is None:
            return {"error": f"Tool registry not available for '{tool_name}'"}

        user_id = getattr(request, "user_id", None) or "system"
        role = "admin"  # Pipeline runs with admin privileges
        if request.metadata and "user_role" in request.metadata:
            role = request.metadata["user_role"]

        try:
            result = await self._tool_registry.execute(
                tool_name=tool_name,
                params=tool_args,
                user_id=user_id,
                role=role,
            )
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "task_id": result.task_id,
            }
        except Exception as e:
            logger.error("Tool execution error for '%s': %s", tool_name, e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Fallback to generate()
    # ------------------------------------------------------------------

    async def _fallback_generate(
        self,
        messages: List[Dict[str, str]],
        request: OrchestratorRequest,
    ) -> str:
        """Fall back to LLMServiceProtocol.generate() for simple text."""
        full_prompt = "\n\n".join(
            f"[{m.get('role', 'user')}]\n{m.get('content', '')}"
            for m in messages
        )
        return await self._llm_service.generate(
            prompt=full_prompt,
            max_tokens=2048,
            temperature=0.7,
        )

    # ------------------------------------------------------------------
    # Message Building
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
        routing_decision: Any,
    ) -> List[Dict[str, str]]:
        """Build chat messages array for Azure OpenAI."""
        context_prompt = self._build_context_prompt(routing_decision)
        tools_text = self._build_tools_prompt(request)

        # Memory context from ContextHandler
        memory_section = ""
        memory_context = context.get("memory_context", "")
        if memory_context:
            memory_section = f"\n--- 相關記憶 ---\n{memory_context}"

        system_content = (
            f"{ORCHESTRATOR_SYSTEM_PROMPT}\n\n"
            f"{tools_text}"
            f"{memory_section}\n"
            f"--- 分析上下文 ---\n{context_prompt}"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]

        # Add conversation history
        conversation_history = context.get("conversation_history", [])
        for msg in conversation_history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:500]
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        # Add current user message
        messages.append({"role": "user", "content": request.content})

        return messages

    # ------------------------------------------------------------------
    # Tool Schema Access
    # ------------------------------------------------------------------

    def _get_tool_schemas(self, request: OrchestratorRequest) -> List[Dict[str, Any]]:
        """Get OpenAI-format tool schemas from registry."""
        if self._tool_registry is None:
            return []
        role = "operator"
        if request.metadata and "user_role" in request.metadata:
            role = request.metadata["user_role"]
        return self._tool_registry.get_openai_tool_schemas(role=role)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_tools_prompt(self, request: OrchestratorRequest) -> str:
        """Build the tools description section for the system prompt."""
        if self._tool_registry is None:
            return ""
        role = "operator"
        if request.metadata and "user_role" in request.metadata:
            role = request.metadata["user_role"]
        tools_text = self._tool_registry.get_tools_prompt(role=role)
        return f"--- 可用工具 ---\n{tools_text}\n\n"

    @staticmethod
    def _build_context_prompt(routing_decision: Any) -> str:
        """Convert a routing decision into a human-readable context summary."""
        if routing_decision is None:
            return "No routing context available."

        if isinstance(routing_decision, dict):
            intent_category = routing_decision.get("intent_category", "unknown")
            sub_intent = routing_decision.get("sub_intent", "N/A")
            confidence = routing_decision.get("confidence", 0.0)
            risk_level = routing_decision.get("risk_level", "unknown")
            completeness = routing_decision.get("completeness", 1.0)
            routing_layer = routing_decision.get("routing_layer", "unknown")
        else:
            intent_category = getattr(routing_decision, "intent_category", "unknown")
            sub_intent = getattr(routing_decision, "sub_intent", "N/A")
            confidence = getattr(routing_decision, "confidence", 0.0)
            risk_level = getattr(routing_decision, "risk_level", "unknown")
            completeness = getattr(routing_decision, "completeness", 1.0)
            routing_layer = getattr(routing_decision, "routing_layer", "unknown")

        lines = [
            f"Intent Category: {intent_category}",
            f"Sub Intent: {sub_intent}",
            f"Confidence: {confidence}",
            f"Risk Level: {risk_level}",
            f"Completeness: {completeness}",
            f"Routing Layer: {routing_layer}",
        ]
        return "\n".join(lines)
