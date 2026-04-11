"""
Step 6: LLM Route Decision — Dynamic execution route selection.

Extracted from PoC agent_team_poc.py lines 1166-1237.
Uses an OrchestratorAgent with select_route() function calling to choose
the best execution route based on ALL prior context.

Outputs:
    context.selected_route — One of: direct_answer/subagent/team/swarm/workflow
    context.route_reasoning — LLM's reasoning for the choice.

Phase 45: Orchestration Core (Sprint 155)
"""

import logging
import os
from typing import Any, Callable, Dict, Optional

from ..context import PipelineContext
from .base import PipelineStep

logger = logging.getLogger(__name__)

VALID_ROUTES = {"direct_answer", "subagent", "team", "swarm", "workflow"}
DEFAULT_ROUTE = "team"

ORCHESTRATOR_SYSTEM_PROMPT = """You are an IT Operations Orchestrator. Based on the context below, \
call select_route to choose the best execution mode.

## User Request
{task}

## Memory Context (structured, token-budgeted)
{memory_text}

## Knowledge Base Results
{knowledge_text}

## Intent Analysis
Category: {intent_category}, Sub-intent: {sub_intent}
Confidence: {confidence:.2f}, Layer: {routing_layer}

## Risk Assessment
Level: {risk_level}, Score: {risk_score:.2f}
Requires Approval: {requires_approval}

Choose ONE route:
- direct_answer: simple questions, low risk, factual Q&A
- subagent: independent parallel checks (e.g., check 3 systems separately)
- team: complex investigation needing expert collaboration
- swarm: critical incidents needing deep Manager-driven analysis
- workflow: structured processes (deploy, change management)

Call select_route with your choice and reasoning."""


class LLMRouteStep(PipelineStep):
    """LLM-driven route selection via function calling.

    The Orchestrator Agent receives the full pipeline context
    (memory + knowledge + intent + risk) and calls select_route()
    to dynamically choose the execution strategy.

    This is the ONLY step that uses LLM reasoning — all prior steps
    are deterministic (code-enforced).
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        provider: str = "azure",
        model: Optional[str] = None,
    ):
        """Initialize LLMRouteStep.

        Args:
            llm_client: Pre-configured LLM client (Azure OpenAI or compatible).
                If None, creates one from environment variables.
            provider: LLM provider ("azure", "openai", "anthropic").
            model: Model name/deployment to use.
        """
        self._llm_client = llm_client
        self._provider = provider
        self._model = model

    @property
    def name(self) -> str:
        return "llm_route_decision"

    @property
    def step_index(self) -> int:
        return 5

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Select execution route via LLM function calling.

        Args:
            context: PipelineContext with all prior step outputs.

        Returns:
            PipelineContext with selected_route and route_reasoning set.
        """
        try:
            prompt = self._build_prompt(context)
            selected_route, reasoning, response_text = await self._call_llm(
                context.task, prompt
            )

            context.selected_route = selected_route
            context.route_reasoning = reasoning
            context.metadata["llm_route_response"] = response_text[:500]

            logger.info(
                "LLMRouteStep: selected=%s, reasoning=%s",
                selected_route,
                reasoning[:100] if reasoning else "none",
            )

        except Exception as e:
            logger.warning(
                "LLMRouteStep: LLM call failed, defaulting to '%s' — %s",
                DEFAULT_ROUTE,
                str(e)[:150],
            )
            context.selected_route = DEFAULT_ROUTE
            context.route_reasoning = f"Fallback due to LLM error: {str(e)[:100]}"

        return context

    def _build_prompt(self, context: PipelineContext) -> str:
        """Build orchestrator system prompt with all context."""
        rd = context.routing_decision
        ra = context.risk_assessment

        return ORCHESTRATOR_SYSTEM_PROMPT.format(
            task=context.task,
            memory_text=context.memory_text[:2000] if context.memory_text else "(no memory)",
            knowledge_text=context.knowledge_text[:2000] if context.knowledge_text else "(no knowledge)",
            intent_category=(
                rd.intent_category.value
                if rd and hasattr(rd.intent_category, "value")
                else str(rd.intent_category) if rd else "unknown"
            ),
            sub_intent=rd.sub_intent if rd else "unknown",
            confidence=rd.confidence if rd else 0.0,
            routing_layer=rd.routing_layer if rd else "unknown",
            risk_level=(
                ra.level.value
                if ra and hasattr(ra.level, "value")
                else str(ra.level) if ra else "unknown"
            ),
            risk_score=ra.score if ra else 0.0,
            requires_approval=ra.requires_approval if ra else False,
        )

    async def _call_llm(
        self, task: str, system_prompt: str
    ) -> tuple:
        """Call LLM with select_route tool.

        Returns:
            Tuple of (selected_route, reasoning, response_text).
        """
        client = self._get_client()

        try:
            from agents import Agent, function_tool

            @function_tool(
                name="select_route",
                description=(
                    "Select the execution route for this task. Options: "
                    "'direct_answer' (simple Q&A), 'subagent' (parallel independent), "
                    "'team' (expert collaboration), 'swarm' (deep Manager analysis), "
                    "'workflow' (structured process)."
                ),
            )
            def select_route(route: str, reasoning: str) -> str:
                """Select execution route with reasoning."""
                return f"Route: {route}. Reason: {reasoning}"

            orchestrator = Agent(
                client,
                name="Orchestrator",
                instructions=system_prompt,
                tools=[select_route],
            )

            response = await orchestrator.run(task)

            # Extract response text
            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            # Extract route from response
            selected_route, reasoning = self._extract_route(response_text)

            # Fallback response if LLM only called tool
            if not response_text.strip():
                response_text = f"Selected route: {selected_route}. {reasoning}"

            return selected_route, reasoning, response_text

        except ImportError:
            # Fallback: use raw LLM call without agent framework
            return await self._call_llm_raw(client, task, system_prompt)

    async def _call_llm_raw(
        self, client: Any, task: str, system_prompt: str
    ) -> tuple:
        """Fallback: raw LLM chat completion without Agent framework.

        Used when `agents` package is not available.
        """
        try:
            response = client.chat.completions.create(
                model=self._model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": task},
                ],
                max_tokens=512,
                temperature=0.3,
            )
            text = response.choices[0].message.content or ""
            route, reasoning = self._extract_route(text)
            return route, reasoning, text
        except Exception as e:
            logger.error("Raw LLM call also failed: %s", str(e)[:100])
            return DEFAULT_ROUTE, f"All LLM calls failed: {str(e)[:100]}", ""

    @staticmethod
    def _extract_route(text: str) -> tuple:
        """Extract selected route and reasoning from LLM response text.

        Args:
            text: LLM response text containing route keyword.

        Returns:
            Tuple of (route, reasoning).
        """
        text_lower = text.lower()
        selected = DEFAULT_ROUTE
        for keyword in VALID_ROUTES:
            if keyword in text_lower:
                selected = keyword
                break

        # Try to extract reasoning
        reasoning = ""
        for marker in ["reason:", "reasoning:", "because", "since"]:
            idx = text_lower.find(marker)
            if idx >= 0:
                reasoning = text[idx:idx + 200].strip()
                break

        if not reasoning:
            reasoning = text[:200].strip()

        return selected, reasoning

    def _get_client(self) -> Any:
        """Get or create LLM client."""
        if self._llm_client is not None:
            return self._llm_client

        if self._provider == "azure":
            from openai import AzureOpenAI

            self._llm_client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
        else:
            from openai import OpenAI

            self._llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        return self._llm_client
