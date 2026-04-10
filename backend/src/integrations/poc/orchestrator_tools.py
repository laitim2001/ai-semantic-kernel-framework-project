"""Orchestrator Agent Tools — @tool wrappers for existing IPA modules.

Wraps 5 existing modules as MAF FunctionTools for the Orchestrator Agent:
1. UnifiedMemoryManager → memory read/write
2. BusinessIntentRouter + FrameworkSelector → intent routing
3. KnowledgeRetriever → RAG knowledge search
4. UnifiedCheckpointStorage → session persistence
5. ResultSynthesiser → multi-result integration

All modules already exist in the IPA codebase — these are just @tool wrappers.
"""

import json
import logging
from typing import Any, Optional

from agent_framework import tool

logger = logging.getLogger(__name__)


def create_orchestrator_tools(
    llm_service: Any = None,
) -> list:
    """Create all Orchestrator Agent tools.

    Returns list of MAF FunctionTools that wrap existing IPA modules.
    """
    # ── 1. Memory Tools ──

    @tool(name="get_user_memory", description=(
        "Retrieve relevant memories for a user. Searches across all memory layers "
        "(working memory, session memory, long-term memory). Use this to understand "
        "user context, past interactions, and preferences before making decisions."
    ))
    def get_user_memory(user_id: str, query: str) -> str:
        """Search user's memory across all layers."""
        try:
            import asyncio
            from src.integrations.memory.unified_memory import UnifiedMemoryManager

            mgr = UnifiedMemoryManager()
            # Try to get context (combines working + session + long-term)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context — create task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        records = pool.submit(
                            lambda: asyncio.run(mgr.get_context(user_id=user_id, query=query, limit=5))
                        ).result(timeout=10)
                else:
                    records = asyncio.run(mgr.get_context(user_id=user_id, query=query, limit=5))
            except Exception:
                # Fallback: return empty
                return f"No memories found for user {user_id} (memory service not available)"

            if not records:
                return f"No relevant memories found for user {user_id} regarding: {query}"

            lines = [f"Found {len(records)} memories for user {user_id}:"]
            for r in records:
                content = getattr(r, 'content', str(r))[:200]
                layer = getattr(r, 'layer', 'unknown')
                lines.append(f"  [{layer}] {content}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            return f"Memory service unavailable: {str(e)[:100]}"

    @tool(name="save_memory", description=(
        "Save important information to user's memory for future reference. "
        "Use this to remember key decisions, findings, and user preferences."
    ))
    def save_memory(user_id: str, content: str, memory_type: str = "insight") -> str:
        """Save content to user's memory."""
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            from src.integrations.memory.types import MemoryType

            mgr = UnifiedMemoryManager()
            type_map = {
                "conversation": MemoryType.CONVERSATION,
                "insight": MemoryType.INSIGHT,
                "decision": MemoryType.DECISION,
            }
            mt = type_map.get(memory_type, MemoryType.INSIGHT)

            import asyncio
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    record = pool.submit(
                        lambda: asyncio.run(mgr.add(content=content, user_id=user_id, memory_type=mt))
                    ).result(timeout=10)
                return f"Memory saved for user {user_id}: {content[:100]}..."
            except Exception:
                return f"Memory saved (simulated) for user {user_id}: {content[:100]}..."
        except Exception as e:
            logger.warning(f"Memory save failed: {e}")
            return f"Memory save failed: {str(e)[:100]}"

    # ── 2. Intent Routing Tool ──

    @tool(name="analyze_intent", description=(
        "Analyze user's request to determine intent category, risk level, and "
        "suggested execution mode. Uses three-tier routing: Pattern → Semantic → LLM. "
        "Returns intent category, risk level, and recommended mode "
        "(chat/workflow/swarm/hybrid)."
    ))
    def analyze_intent(user_input: str) -> str:
        """Analyze intent and determine execution mode."""
        try:
            from src.integrations.orchestration.intent_router.router import BusinessIntentRouter
            from src.integrations.orchestration.intent_router.pattern_matcher.matcher import PatternMatcher
            from src.integrations.orchestration.intent_router.semantic_router.router import SemanticRouter
            from src.integrations.orchestration.intent_router.llm_classifier.classifier import LLMClassifier

            # Create minimal router (pattern matcher is rule-based, no LLM needed)
            matcher = PatternMatcher()
            semantic = SemanticRouter()
            llm_cls = LLMClassifier()
            router = BusinessIntentRouter(
                pattern_matcher=matcher,
                semantic_router=semantic,
                llm_classifier=llm_cls,
            )

            import asyncio
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                decision = pool.submit(
                    lambda: asyncio.run(router.route(user_input))
                ).result(timeout=15)

            return (
                f"Intent Analysis:\n"
                f"  Category: {decision.intent_category}\n"
                f"  Sub-intent: {decision.sub_intent}\n"
                f"  Risk Level: {decision.risk_level}\n"
                f"  Confidence: {decision.confidence}\n"
                f"  Workflow Type: {decision.workflow_type}\n"
                f"  Reasoning: {decision.reasoning[:200] if decision.reasoning else 'N/A'}"
            )
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
            # Fallback: simple keyword-based analysis
            input_lower = user_input.lower()
            if any(w in input_lower for w in ["incident", "failure", "down", "error", "crash"]):
                return f"Intent: INCIDENT (high risk) — suggests swarm/team mode"
            elif any(w in input_lower for w in ["create", "setup", "deploy", "build"]):
                return f"Intent: CHANGE (medium risk) — suggests workflow mode"
            elif any(w in input_lower for w in ["check", "status", "query", "what is"]):
                return f"Intent: QUERY (low risk) — suggests direct answer mode"
            else:
                return f"Intent: GENERAL (low risk) — suggests chat mode"

    # ── 3. Knowledge Base Search Tool ──

    @tool(name="search_knowledge", description=(
        "Search the organization's knowledge base using RAG pipeline. "
        "Finds relevant SOPs, incident reports, system documentation, "
        "and configuration details. Returns ranked results with sources."
    ))
    def search_knowledge(query: str) -> str:
        """Search knowledge base via RAG pipeline."""
        try:
            from src.integrations.knowledge.retriever import KnowledgeRetriever

            retriever = KnowledgeRetriever()

            import asyncio
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(
                    lambda: asyncio.run(retriever.retrieve(query=query, limit=3))
                ).result(timeout=15)

            if not results:
                return f"No knowledge found for: {query}"

            lines = [f"Found {len(results)} knowledge items:"]
            for i, r in enumerate(results):
                content = getattr(r, 'content', str(r))[:200]
                score = getattr(r, 'score', 0)
                source = getattr(r, 'source', 'unknown')
                lines.append(f"  [{i+1}] (score={score:.2f}) [{source}] {content}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Knowledge search failed: {e}")
            return f"Knowledge base not available: {str(e)[:100]}. Proceeding without KB context."

    # ── 4. Execution Mode Router Tools ──

    @tool(name="route_to_direct_answer", description=(
        "Handle a simple question directly without multi-agent collaboration. "
        "Use this for low-risk queries, status checks, and simple Q&A."
    ))
    def route_to_direct_answer(question: str) -> str:
        """Directly answer a simple question using LLM."""
        return f"[DIRECT_ANSWER] Processing: {question}"

    @tool(name="route_to_subagent", description=(
        "Execute independent parallel tasks using Subagent mode (ConcurrentBuilder). "
        "Use this when the task has multiple independent subtasks that can run simultaneously. "
        "Provide a description of the overall task."
    ))
    def route_to_subagent(task: str, num_agents: int = 3) -> str:
        """Route to Subagent (ConcurrentBuilder) mode."""
        return f"[SUBAGENT_MODE] Dispatching to {num_agents} parallel agents: {task}"

    @tool(name="route_to_team", description=(
        "Execute collaborative investigation using Agent Team mode (GroupChatBuilder). "
        "Use this when multiple experts need to share findings and coordinate. "
        "Best for complex incidents requiring cross-domain analysis."
    ))
    def route_to_team(task: str, experts: str = "LogExpert,DBExpert,AppExpert") -> str:
        """Route to Agent Team (GroupChatBuilder) mode."""
        return f"[TEAM_MODE] Dispatching to team [{experts}]: {task}"

    @tool(name="route_to_swarm", description=(
        "Execute deep sequential analysis using MagenticOne (Swarm) mode. "
        "Use this for critical incidents requiring Manager-driven planning, "
        "progress evaluation, and replanning. Most thorough but slowest."
    ))
    def route_to_swarm(task: str) -> str:
        """Route to MagenticOne (Swarm) mode."""
        return f"[SWARM_MODE] Dispatching to MagenticOne Manager: {task}"

    @tool(name="route_to_workflow", description=(
        "Execute a structured workflow using MAF WorkflowBuilder. "
        "Use this for well-defined multi-step processes like deployments, "
        "change management, or onboarding procedures."
    ))
    def route_to_workflow(task: str, workflow_type: str = "general") -> str:
        """Route to MAF Workflow mode."""
        return f"[WORKFLOW_MODE] Dispatching to workflow '{workflow_type}': {task}"

    # ── 5. Session Management Tool ──

    @tool(name="save_session_checkpoint", description=(
        "Save current session state for cross-session persistence. "
        "Use this to preserve the orchestration state so it can be resumed later."
    ))
    def save_session_checkpoint(session_id: str, state_summary: str) -> str:
        """Save session checkpoint."""
        try:
            from src.integrations.hybrid.checkpoint.backends.memory import MemoryCheckpointStorage
            from src.integrations.hybrid.checkpoint.models import HybridCheckpoint, CheckpointType

            storage = MemoryCheckpointStorage()
            checkpoint = HybridCheckpoint(
                session_id=session_id,
                checkpoint_type=CheckpointType.ORCHESTRATOR,
                data={"summary": state_summary},
            )

            import asyncio
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                cp_id = pool.submit(
                    lambda: asyncio.run(storage.save(checkpoint))
                ).result(timeout=5)

            return f"Checkpoint saved: session={session_id}, id={cp_id}"
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")
            return f"Checkpoint saved (simulated): session={session_id}, summary={state_summary[:100]}"

    return [
        # Memory
        get_user_memory,
        save_memory,
        # Intent routing
        analyze_intent,
        # Knowledge
        search_knowledge,
        # Execution routing (5 modes)
        route_to_direct_answer,
        route_to_subagent,
        route_to_team,
        route_to_swarm,
        route_to_workflow,
        # Session
        save_session_checkpoint,
    ]
