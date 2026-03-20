"""
AgentHandler — LLM Decision Engine

Serves as the Agent backend within the OrchestratorMediator pipeline,
receiving results from upstream Handlers (Routing, Dialog, Approval)
and using LLM to generate intelligent responses.

Sprint 107 — Phase 35 A0 core assumption validation.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

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


class AgentHandler(Handler):
    """Handler that uses LLM to generate intelligent responses.

    Positioned in the pipeline after Approval and before Execution.
    For simple conversational requests, the AgentHandler can produce
    a direct response and short-circuit the pipeline (skipping Execution).

    Args:
        llm_service: Optional LLM service instance. When ``None``, the handler
            returns a graceful fallback response instead of raising.
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
            1. Extract ``routing_decision`` from *context* (set by RoutingHandler).
            2. Build a full prompt from system prompt + routing context + user input.
            3. Call ``LLMServiceProtocol.generate()`` to obtain a response.
            4. Return the response wrapped in a ``HandlerResult``.

        If the LLM service is unavailable the handler returns a fallback message
        without raising, ensuring the pipeline does not crash.
        """
        # Look up routing_decision from pipeline context first, then fall
        # back to request.metadata (used by the orchestrator chat endpoint
        # which runs routing externally before calling the mediator).
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

        # --- Build the full prompt -----------------------------------------
        context_prompt = self._build_context_prompt(routing_decision)
        tools_prompt = self._build_tools_prompt(request)

        # Phase 41: Inject memory context from ContextHandler (if available)
        memory_section = ""
        memory_context = context.get("memory_context", "")
        if memory_context:
            memory_section = f"--- 相關記憶 ---\n{memory_context}\n\n"

        # Phase 41: Inject conversation history for multi-turn context
        history_section = ""
        conversation_history = context.get("conversation_history", [])
        if conversation_history:
            history_lines = []
            # Keep last 10 messages to avoid prompt overflow
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:300]
                history_lines.append(f"{'用戶' if role == 'user' else '助手'}: {content}")
            if history_lines:
                history_section = "--- 對話歷史 ---\n" + "\n".join(history_lines) + "\n\n"

        full_prompt = (
            f"{ORCHESTRATOR_SYSTEM_PROMPT}\n\n"
            f"{tools_prompt}"
            f"{memory_section}"
            f"{history_section}"
            f"--- 分析上下文 ---\n{context_prompt}\n\n"
            f"--- 用戶輸入 ---\n{user_input}"
        )

        # --- Call LLM ------------------------------------------------------
        try:
            logger.info(
                "AgentHandler: generating LLM response for request %s",
                request.request_id,
            )
            llm_response = await self._llm_service.generate(
                prompt=full_prompt,
                max_tokens=2048,
                temperature=0.7,
            )
            logger.info(
                "AgentHandler: LLM response generated successfully for request %s",
                request.request_id,
            )

            # Phase 41: Only short-circuit for CHAT_MODE.
            # WORKFLOW_MODE / HYBRID_MODE should proceed to ExecutionHandler
            # for MAF/Claude/Swarm task dispatch.
            from src.integrations.hybrid.intent import ExecutionMode
            exec_mode = context.get("execution_mode", ExecutionMode.CHAT_MODE)
            is_chat_mode = exec_mode in (ExecutionMode.CHAT_MODE, "chat")
            needs_swarm = bool(context.get("swarm_decomposition"))

            should_sc = is_chat_mode and not needs_swarm

            return HandlerResult(
                success=True,
                handler_type=HandlerType.AGENT,
                data={
                    "content": llm_response,
                    "agent_source": "llm",
                    "framework_used": "orchestrator_agent",
                },
                should_short_circuit=should_sc,
                short_circuit_response={
                    "content": llm_response,
                    "framework_used": "orchestrator_agent",
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
    # Private helpers
    # ------------------------------------------------------------------

    def _build_tools_prompt(self, request: OrchestratorRequest) -> str:
        """Build the tools description section for the system prompt.

        If no tool registry is configured an empty string is returned so
        the prompt remains unchanged.

        The caller's role is extracted from ``request.metadata`` (key
        ``"user_role"``), defaulting to ``"operator"``.
        """
        if self._tool_registry is None:
            return ""
        role = "operator"
        if request.metadata and "user_role" in request.metadata:
            role = request.metadata["user_role"]
        tools_text = self._tool_registry.get_tools_prompt(role=role)
        return f"--- 可用工具 ---\n{tools_text}\n\n"

    @staticmethod
    def _build_context_prompt(
        routing_decision: Any,
    ) -> str:
        """Convert a routing decision into a human-readable context summary.

        Handles both ``RoutingDecision`` objects (with attributes) and plain
        ``dict`` representations produced by serialization.

        Args:
            routing_decision: The routing decision from the RoutingHandler,
                either a ``RoutingDecision`` dataclass or a ``dict``.

        Returns:
            A formatted string summarising intent, risk, and completeness.
        """
        if routing_decision is None:
            return "No routing context available."

        # Support both object attribute access and dict key access
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
