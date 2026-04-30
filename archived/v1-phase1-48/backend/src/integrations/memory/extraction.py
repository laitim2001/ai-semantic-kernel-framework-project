# =============================================================================
# IPA Platform - Memory Extraction Service
# =============================================================================
# CC-Inspired post-pipeline memory extraction using LLM.
#
# CC Equivalent: extractMemories service — after conversation, LLM extracts
# structured learnings and writes them to CLAUDE.md.
#
# Server-Side Adaptation: Async background job that runs after each pipeline
# completion. Extracts FACTS, PREFERENCES, DECISIONS, PATTERNS from the
# full conversation turn. High-value items are auto-pinned.
#
# This replaces the old Step 6 which only saved:
#   f"User asked about: {task[:80]}. Routed to: {mode}"
# with rich, structured extraction via LLM.
#
# Cost note: This uses an LLM call per pipeline completion.
# The user's principle: "adopt effective patterns first, optimize cost later."
# =============================================================================

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import MemoryLayer, MemoryMetadata, MemoryRecord, MemoryType

logger = logging.getLogger(__name__)

# Extraction prompt — instructs LLM to extract structured knowledge
EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction system for an IT Operations platform.
Analyze the conversation turn below and extract structured knowledge.

Extract ONLY what is clearly stated or strongly implied. Do NOT invent or assume.

IMPORTANT: Distinguish between STABLE KNOWLEDGE and TRANSIENT EVENTS.
- STABLE: User's role, responsibilities, infrastructure topology, preferences → extract these
- TRANSIENT: Active incidents, current CPU %, pending tasks → do NOT extract as facts

Categories:
1. FACTS: STABLE facts about the user, their role, or infrastructure topology.
   YES: "User manages APAC ETL Pipeline", "CRM uses PostgreSQL 16 on db-prod-03"
   NO: "CRM CPU at 85%" (transient), "K8s needs scaling" (pending task)
2. PREFERENCES: How the user wants things done (stable, long-term).
   Examples: "Prefers Chinese responses", "Prefers team mode for investigations"
3. DECISIONS: Decisions made and their rationale (for historical record).
   Examples: "Chose to increase connection pool from 10 to 50"
4. PATTERNS: Recurring behaviors or needs observed over time.
   Examples: "User frequently checks ETL Pipeline health on Mondays"

Return a JSON object:
{
  "facts": ["fact1", "fact2"],
  "preferences": ["pref1"],
  "decisions": ["decision1"],
  "patterns": ["pattern1"],
  "skip": false
}

Set "skip": true if the conversation is trivial (greetings, simple status checks with no new info).
Keep each item concise (1-2 sentences max).
Respond ONLY with valid JSON, no markdown."""


@dataclass
class ExtractionResult:
    """Result of a memory extraction operation."""
    facts: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    skipped: bool = False
    memories_created: int = 0
    error: Optional[str] = None


class MemoryExtractionService:
    """Post-pipeline memory extraction — CC's extractMemories equivalent.

    After each pipeline completion, this service uses LLM to extract
    structured facts, preferences, decisions, and patterns from the
    conversation. All extractions go to LONG_TERM (CC's Memory Files
    equivalent). Pinned layer is user-controlled only (CC's CLAUDE.md).

    Usage:
        extraction_svc = MemoryExtractionService(memory_manager)

        # Fire-and-forget after pipeline completes:
        asyncio.create_task(extraction_svc.extract_and_store(
            user_id="user-chris",
            session_id="session-123",
            user_message="APAC ETL Pipeline is down",
            assistant_response="I investigated and found...",
            pipeline_context={...}
        ))
    """

    def __init__(self, memory_manager):
        """Initialize with a UnifiedMemoryManager instance."""
        self._memory_manager = memory_manager

    async def extract_and_store(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        pipeline_context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        """Extract structured knowledge from a pipeline turn and store it.

        This is the main entry point. Designed to be called as an async
        background task (non-blocking to the pipeline response).

        Args:
            user_id: User identifier.
            session_id: Session identifier.
            user_message: The user's original request.
            assistant_response: The orchestrator's response.
            pipeline_context: Optional context (route decision, risk level, etc.)

        Returns:
            ExtractionResult with extraction details.
        """
        result = ExtractionResult()

        try:
            # Build the conversation context for extraction
            conversation_text = self._build_conversation_text(
                user_message, assistant_response, pipeline_context
            )

            # Call LLM for extraction
            extractions = await self._extract_via_llm(conversation_text)

            if extractions.get("skip", False):
                result.skipped = True
                logger.info(f"Extraction skipped (trivial) for session {session_id[:12]}")
                return result

            result.facts = extractions.get("facts", [])
            result.preferences = extractions.get("preferences", [])
            result.decisions = extractions.get("decisions", [])
            result.patterns = extractions.get("patterns", [])

            # Store all extractions to LONG_TERM (CC's Memory Files equivalent).
            # Pinned layer is user-controlled only — no auto-pin.
            created = await self._store_extractions(user_id, session_id, result)
            result.memories_created = created

            logger.info(
                f"Extraction complete for session {session_id[:12]}: "
                f"{created} memories stored to LONG_TERM"
            )

        except Exception as e:
            result.error = str(e)[:300]
            logger.error(f"Memory extraction failed for session {session_id[:12]}: {e}")

        return result

    def _build_conversation_text(
        self,
        user_message: str,
        assistant_response: str,
        pipeline_context: Optional[Dict[str, Any]],
    ) -> str:
        """Build the conversation text for LLM extraction."""
        parts = [
            f"## User Message\n{user_message}",
            f"\n## Assistant Response\n{assistant_response[:2000]}",
        ]

        if pipeline_context:
            ctx_parts = []
            if pipeline_context.get("route_decision"):
                ctx_parts.append(f"Route: {pipeline_context['route_decision']}")
            if pipeline_context.get("risk_level"):
                ctx_parts.append(f"Risk: {pipeline_context['risk_level']}")
            if pipeline_context.get("intent_category"):
                ctx_parts.append(f"Intent: {pipeline_context['intent_category']}")
            if pipeline_context.get("agent_states"):
                agents = ", ".join(pipeline_context["agent_states"].keys())
                ctx_parts.append(f"Agents used: {agents}")
            if ctx_parts:
                parts.append(f"\n## Pipeline Context\n" + "\n".join(ctx_parts))

        return "\n".join(parts)

    async def _extract_via_llm(self, conversation_text: str) -> Dict[str, Any]:
        """Call LLM to extract structured knowledge from conversation.

        Uses the same LLM infrastructure as the orchestrator pipeline.
        """
        import os

        try:
            from agent_framework import Agent
            from src.api.v1.poc.agent_team_poc import _create_client

            # Use a lightweight model for extraction to balance cost/quality
            model = os.getenv("MEMORY_EXTRACTION_MODEL",
                              os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini"))

            client = _create_client(
                provider="azure",
                model=model,
                azure_api_version="2025-03-01-preview",
                max_tokens=1024,
            )

            extractor = Agent(
                client,
                name="MemoryExtractor",
                instructions=EXTRACTION_SYSTEM_PROMPT,
            )

            response = await extractor.run(conversation_text)

            # Parse response
            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text
            elif hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "text") and msg.text:
                        response_text += msg.text

            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # Strip markdown code block
                lines = json_text.split("\n")
                json_lines = [l for l in lines if not l.startswith("```")]
                json_text = "\n".join(json_lines)

            return json.loads(json_text)

        except json.JSONDecodeError as je:
            logger.warning(f"Extraction LLM returned invalid JSON: {je}")
            return {"skip": True}
        except Exception as e:
            logger.error(f"Extraction LLM call failed: {e}")
            return {"skip": True}

    async def _store_extractions(
        self,
        user_id: str,
        session_id: str,
        result: ExtractionResult,
    ) -> int:
        """Store extracted knowledge as memories in appropriate layers."""
        mgr = self._memory_manager
        created = 0

        type_mapping = {
            "facts": MemoryType.EXTRACTED_FACT,
            "preferences": MemoryType.EXTRACTED_PREFERENCE,
            "decisions": MemoryType.DECISION,
            "patterns": MemoryType.EXTRACTED_PATTERN,
        }

        for category, memory_type in type_mapping.items():
            items = getattr(result, category, [])
            for item in items:
                if not item or not item.strip():
                    continue
                try:
                    metadata = MemoryMetadata(
                        source="extraction",
                        session_id=session_id,
                        importance=0.7,  # Extracted items are higher than default 0.5
                        tags=["extracted", category],
                    )
                    await mgr.add(
                        content=item.strip(),
                        user_id=user_id,
                        memory_type=memory_type,
                        metadata=metadata,
                        layer=MemoryLayer.LONG_TERM,
                    )
                    created += 1
                except Exception as e:
                    logger.warning(f"Failed to store extracted {category}: {e}")

        return created

    # NOTE: _auto_pin() was removed. Pinned layer is user-controlled only,
    # matching CC's architecture where CLAUDE.md is never auto-written by AI.
    # All AI-extracted knowledge goes to LONG_TERM and is retrieved via
    # semantic search when relevant (CC's Memory Files equivalent).
