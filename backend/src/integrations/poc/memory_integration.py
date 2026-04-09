"""TeamMemoryIntegration — Cross-session memory for agent team.

Wraps the existing OrchestratorMemoryManager to provide:
  - Pre-Phase 0: retrieve relevant past findings for the current goal
  - Post-Phase 2: store synthesis results as long-term memory
  - Post-Phase 2: store full execution transcript

Graceful fallback: if memory system is unavailable (MEM0_ENABLED=false
or import errors), all methods return empty/None without raising.

PoC: Agent Team V4 — Sprint 155.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TeamMemoryIntegration:
    """Memory integration for agent team pre-retrieval and post-storage."""

    def __init__(self, memory_manager):
        """
        Args:
            memory_manager: An OrchestratorMemoryManager instance.
        """
        self._mm = memory_manager

    # ------------------------------------------------------------------
    # Pre-Phase 0: Retrieve relevant past findings
    # ------------------------------------------------------------------

    async def retrieve_for_goal(
        self,
        goal: str,
        user_id: str = "system",
        limit: int = 5,
    ) -> str:
        """Search long-term memory for past findings relevant to the goal.

        Returns a formatted context string for injection into agent prompts.
        Returns "" if no relevant memories found or memory unavailable.
        """
        try:
            memories = await self._mm.retrieve_relevant_memories(
                query=goal,
                user_id=user_id,
                limit=limit,
            )
            if not memories:
                return ""

            context = self._format_memory_context(memories)
            logger.info(
                f"Memory: retrieved {len(memories)} relevant memories "
                f"({len(context)} chars) for goal"
            )
            return context
        except Exception as e:
            logger.warning(f"Memory retrieval failed (non-fatal): {e}")
            return ""

    # ------------------------------------------------------------------
    # Post-Phase 2: Store synthesis as long-term memory
    # ------------------------------------------------------------------

    async def store_synthesis(
        self,
        session_id: str,
        goal: str,
        synthesis: str,
        agent_results: dict[str, str],
        user_id: str = "system",
    ) -> Optional[dict[str, Any]]:
        """Store the team's final synthesis as a long-term memory.

        Formats agent results + synthesis into a conversation-like text
        and delegates to OrchestratorMemoryManager.summarise_and_store().
        """
        try:
            conversation_text = self._format_as_conversation(
                goal, agent_results, synthesis
            )
            result = await self._mm.summarise_and_store(
                session_id=session_id,
                user_id=user_id,
                conversation_text=conversation_text,
            )
            if result:
                logger.info(f"Memory: stored synthesis for session {session_id}")
            return result
        except Exception as e:
            logger.warning(f"Memory storage failed (non-fatal): {e}")
            return None

    # ------------------------------------------------------------------
    # Post-Phase 2: Store full execution transcript
    # ------------------------------------------------------------------

    async def store_transcript(
        self,
        session_id: str,
        transcript: dict[str, Any],
        user_id: str = "system",
    ) -> Optional[dict[str, Any]]:
        """Store full execution transcript for future reference.

        Uses the memory system's add() method for direct storage.
        """
        try:
            if self._mm._memory is None:
                return None

            content = json.dumps(transcript, ensure_ascii=False, default=str)
            # Truncate if too large for memory storage
            if len(content) > 8000:
                content = content[:8000] + "...(truncated)"

            if hasattr(self._mm._memory, "add"):
                result = await self._mm._memory.add(
                    content=f"Agent team execution transcript:\n{content}",
                    user_id=user_id,
                    metadata={
                        "session_id": session_id,
                        "source": "agent_team_transcript",
                        "stored_at": datetime.utcnow().isoformat(),
                    },
                )
                logger.info(f"Memory: stored transcript for session {session_id}")
                return result
            return None
        except Exception as e:
            logger.warning(f"Transcript storage failed (non-fatal): {e}")
            return None

    # ------------------------------------------------------------------
    # Context injection helper
    # ------------------------------------------------------------------

    def build_agent_context_with_memories(
        self,
        agent_instruction: str,
        memory_context: str,
    ) -> str:
        """Inject memory context into an agent's system prompt."""
        if not memory_context:
            return agent_instruction
        return (
            f"RELEVANT PAST FINDINGS:\n{memory_context}\n\n"
            f"{agent_instruction}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_as_conversation(
        goal: str,
        agent_results: dict[str, str],
        synthesis: str,
    ) -> str:
        """Format team execution as conversation text for summarisation."""
        lines = [f"[USER]: {goal}"]
        for agent_name, result in agent_results.items():
            # Truncate individual results to keep within LLM context
            result_text = result[:1500] if result else "(no output)"
            lines.append(f"[AGENT:{agent_name}]: {result_text}")
        if synthesis:
            lines.append(f"[LEAD_SYNTHESIS]: {synthesis[:2000]}")
        return "\n\n".join(lines)

    @staticmethod
    def _format_memory_context(memories: list[dict[str, Any]]) -> str:
        """Format retrieved memories into a readable context block."""
        if not memories:
            return ""
        lines = ["=== Past Findings (from previous investigations) ==="]
        for i, mem in enumerate(memories, 1):
            content = mem.get("content") or mem.get("memory") or str(mem)
            # Truncate each memory
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"\n[Memory {i}]: {content}")
        lines.append("\n=== End Past Findings ===")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_memory_integration() -> Optional[TeamMemoryIntegration]:
    """Create TeamMemoryIntegration if memory services are available.

    Returns None if memory is disabled or dependencies unavailable.
    """
    try:
        from src.integrations.hybrid.orchestrator.memory_manager import (
            OrchestratorMemoryManager,
        )

        # Try to get the memory client
        memory_client = None
        try:
            from src.integrations.memory.unified_memory import UnifiedMemoryManager
            memory_client = UnifiedMemoryManager()
        except Exception:
            pass

        if memory_client is None:
            logger.info("Memory: UnifiedMemoryManager unavailable, skipping integration")
            return None

        mm = OrchestratorMemoryManager(
            llm_service=None,  # PoC: basic summary without LLM
            memory_client=memory_client,
        )
        logger.info("Memory: TeamMemoryIntegration initialized")
        return TeamMemoryIntegration(mm)

    except Exception as e:
        logger.info(f"Memory integration unavailable: {e}")
        return None
