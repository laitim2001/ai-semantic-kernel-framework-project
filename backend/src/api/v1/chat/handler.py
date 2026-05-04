"""
File: backend/src/api/v1/chat/handler.py
Purpose: Builders that wire AgentLoopImpl with provider + tools by ChatMode.
Category: api/v1/chat
Scope: Phase 50 / Sprint 50.2 (Day 1.4)

Description:
    Handler factories return a fully-wired AgentLoopImpl instance ready to be
    `run()` by the router. Each factory selects the ChatClient adapter
    appropriate for the requested mode:

    - `build_echo_demo_handler()` — MockChatClient with a 2-step scripted
      response: turn 1 calls echo_tool(text=<message>), turn 2 returns the
      echoed text + END_TURN. No env requirements; works offline.

    - `build_real_llm_handler()` — AzureOpenAIAdapter; requires
      AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY + AZURE_OPENAI_DEPLOYMENT_NAME
      env vars (validated at build time, NOT inside loop). System prompt
      instructs the model to use echo_tool for Phase 50.2 demo correctness.

    Tool layer is the same across modes: 50.1 InMemoryToolRegistry +
    InMemoryToolExecutor with echo_tool registered.

Key Components:
    - build_echo_demo_handler(message: str) -> AgentLoopImpl
    - build_real_llm_handler() -> AgentLoopImpl
    - build_handler(mode: ChatMode, message: str) -> AgentLoopImpl  (dispatcher)

Created: 2026-04-30 (Sprint 50.2 Day 1.4)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.2 Day 1.4) — echo_demo via
        MockChatClient + scripted responses; real_llm via AzureOpenAIAdapter.

Related:
    - .router (calls build_handler)
    - .schemas.ChatMode
    - 50.1 agent_harness.tools._inmemory.make_echo_executor
    - 50.1 agent_harness.orchestrator_loop.AgentLoopImpl
    - 49.4 adapters.azure_openai.adapter.AzureOpenAIAdapter
    - 49.4 adapters._testing.mock_clients.MockChatClient
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from adapters._base.chat_client import ChatClient
from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    StopReason,
    ToolCall,
)
from agent_harness.orchestrator_loop import AgentLoopImpl
from agent_harness.output_parser import OutputParserImpl
from business_domain._register_all import make_default_executor

from .schemas import ChatMode

if TYPE_CHECKING:
    from agent_harness.hitl import HITLManager
    from platform_layer.governance.service_factory import ServiceFactory

# Phase 50.2 demo system prompt — instructs the model to use echo_tool when the
# user explicitly asks to "echo" something. Real LLM only.
DEMO_SYSTEM_PROMPT = (
    "You are a Sprint 50.2 demonstration agent. When the user asks you to "
    "'echo' some text, you MUST call the `echo_tool` function with that text "
    "as the `text` argument, then return the tool's output verbatim as your "
    "final answer. Do not paraphrase. For any other request, answer directly."
)


def build_echo_demo_handler(
    message: str,
    *,
    hitl_manager: "HITLManager | None" = None,
    hitl_timeout_s: int = 14400,
) -> AgentLoopImpl:
    """Wire AgentLoopImpl with a MockChatClient pre-scripted to call echo_tool.

    The mock responds with TOOL_USE on turn 1 (echo_tool with the user's
    message text) and END_TURN with the echoed content on turn 2.

    Sprint 53.6 US-4: optional `hitl_manager` opts the loop into Cat 9 Stage 3
    HITL escalation. None preserves 53.3 baseline behavior (no HITL pause).
    """
    registry, executor = make_default_executor()
    parser = OutputParserImpl()

    scripted: list[ChatResponse] = [
        ChatResponse(
            model="mock-model",
            content="",
            tool_calls=[
                ToolCall(
                    id="call_echo_demo_1",
                    name="echo_tool",
                    arguments={"text": message},
                ),
            ],
            stop_reason=StopReason.TOOL_USE,
        ),
        ChatResponse(
            model="mock-model",
            content=message,
            stop_reason=StopReason.END_TURN,
        ),
    ]
    chat_client: ChatClient = MockChatClient(responses=scripted)

    return AgentLoopImpl(
        chat_client=chat_client,
        output_parser=parser,
        tool_executor=executor,
        tool_registry=registry,
        system_prompt=DEMO_SYSTEM_PROMPT,
        max_turns=4,  # Echo demo never needs more than 2 turns; 4 = safety margin.
        hitl_manager=hitl_manager,
        hitl_timeout_s=hitl_timeout_s,
    )


def build_real_llm_handler(
    *,
    hitl_manager: "HITLManager | None" = None,
    hitl_timeout_s: int = 14400,
) -> AgentLoopImpl:
    """Wire AgentLoopImpl with AzureOpenAIAdapter. Requires env vars.

    Raises:
        RuntimeError: when any of AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY /
            AZURE_OPENAI_DEPLOYMENT_NAME is missing.
    """
    required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            "Cannot build real_llm handler — missing env vars: "
            + ", ".join(missing)
            + ". Configure .env or use mode='echo_demo'."
        )

    # Late import — keeps unit tests free of azure SDK weight when only echo_demo is exercised.
    from adapters.azure_openai.adapter import AzureOpenAIAdapter
    from adapters.azure_openai.config import AzureOpenAIConfig

    # AzureOpenAIConfig is a BaseSettings — pulls AZURE_OPENAI_* from env automatically.
    chat_client: ChatClient = AzureOpenAIAdapter(AzureOpenAIConfig())

    registry, executor = make_default_executor()
    parser = OutputParserImpl()

    return AgentLoopImpl(
        chat_client=chat_client,
        output_parser=parser,
        tool_executor=executor,
        tool_registry=registry,
        system_prompt=DEMO_SYSTEM_PROMPT,
        max_turns=8,
        hitl_manager=hitl_manager,
        hitl_timeout_s=hitl_timeout_s,
    )


def build_handler(
    mode: ChatMode,
    message: str,
    *,
    service_factory: "ServiceFactory | None" = None,
    hitl_timeout_s: int = 14400,
) -> AgentLoopImpl:
    """Dispatch to the per-mode builder. Single entry-point for the router.

    Sprint 53.6 US-4: when `service_factory` is provided AND env flag
    HITL_ENABLED is not "false", resolves the production HITLManager from the
    factory and injects it into AgentLoopImpl. Without the factory (legacy
    callers, tests) the loop runs with 53.3 baseline behavior.
    """
    hitl_manager: "HITLManager | None" = None
    if service_factory is not None and _hitl_enabled():
        hitl_manager = service_factory.get_hitl_manager()
    if mode == "echo_demo":
        return build_echo_demo_handler(
            message, hitl_manager=hitl_manager, hitl_timeout_s=hitl_timeout_s
        )
    if mode == "real_llm":
        return build_real_llm_handler(hitl_manager=hitl_manager, hitl_timeout_s=hitl_timeout_s)
    raise ValueError(f"Unsupported mode: {mode!r}")


def _hitl_enabled() -> bool:
    """Feature toggle. Default ON; explicit `HITL_ENABLED=false` disables wiring."""
    return os.environ.get("HITL_ENABLED", "true").strip().lower() != "false"
