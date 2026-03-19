"""Orchestrator Memory Manager — automatic memory write + retrieval injection.

Connects the Orchestrator to the three-layer memory system:
  - Auto-summarise conversation on session end → write to mem0 Long-term
  - Auto-retrieve relevant memories on new conversation → inject into context
  - Working Memory ↔ Long-term Memory promotion mechanism

Sprint 117 — Phase 38 E2E Assembly C.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Summarisation prompt for extracting structured memories from conversations
SUMMARY_PROMPT = """你是 IPA Platform 的記憶摘要助手。請從以下對話中提取關鍵資訊，生成結構化摘要。

## 對話內容
{conversation}

## 提取要求
請用以下格式回應（JSON）：
{{
    "problem": "用戶遇到的問題描述",
    "resolution": "處理方式和採取的行動",
    "outcome": "最終結果",
    "lessons": "學習到的教訓或模式",
    "tags": ["相關標籤1", "相關標籤2"],
    "importance": "high/medium/low"
}}

如果對話是簡單問答（無需記憶），返回：
{{"importance": "low", "skip": true}}

請直接返回 JSON，不要加其他文字。"""

# Context injection prompt for retrieved memories
MEMORY_INJECTION_TEMPLATE = """--- 相關歷史記憶 ---
以下是與當前對話相關的歷史記錄，供參考：

{memories_text}

--- 歷史記憶結束 ---
"""


class OrchestratorMemoryManager:
    """Manages automatic memory operations for the Orchestrator.

    Provides three core capabilities:
    1. **Auto-summarise**: Extract structured memory from completed conversations
    2. **Auto-retrieve**: Search and inject relevant memories for new conversations
    3. **Memory promotion**: Move important Working Memory to Long-term

    Args:
        llm_service: LLM service for summarisation.
        memory_client: mem0 client or UnifiedMemoryManager.
        conversation_store: L1 ConversationStateStore for reading conversation data.
    """

    def __init__(
        self,
        llm_service: Any = None,
        memory_client: Any = None,
        conversation_store: Any = None,
    ) -> None:
        self._llm = llm_service
        self._memory = memory_client
        self._conv_store = conversation_store

    # ------------------------------------------------------------------
    # Auto-summarise on conversation end
    # ------------------------------------------------------------------

    async def summarise_and_store(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        conversation_text: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Auto-summarise a completed conversation and store in Long-term Memory.

        Steps:
        1. Load conversation from L1 store (or use provided text)
        2. Generate structured summary via LLM
        3. Write summary to mem0 Long-term Memory
        4. Return the stored memory record

        Args:
            session_id: The session to summarise.
            user_id: User ID for memory association.
            conversation_text: Optional pre-formatted conversation text.

        Returns:
            The memory record dict, or None if skipped.
        """
        # Step 1: Get conversation text
        if conversation_text is None:
            conversation_text = await self._load_conversation_text(session_id)
        if not conversation_text or len(conversation_text.strip()) < 20:
            logger.info("Memory: conversation too short to summarise, skipping")
            return None

        # Step 2: Generate summary
        summary = await self._generate_summary(conversation_text)
        if summary is None or summary.get("skip"):
            logger.info("Memory: conversation marked as low-importance, skipping")
            return None

        # Step 3: Write to Long-term Memory
        memory_content = self._format_memory_content(summary)
        memory_record = await self._write_to_longterm(
            content=memory_content,
            user_id=user_id or "system",
            metadata={
                "session_id": session_id,
                "source": "auto_summary",
                "importance": summary.get("importance", "medium"),
                "tags": summary.get("tags", []),
                "problem": summary.get("problem", ""),
                "resolution": summary.get("resolution", ""),
                "outcome": summary.get("outcome", ""),
                "summarised_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            "Memory: conversation summarised and stored for session=%s user=%s",
            session_id, user_id,
        )
        return memory_record

    # ------------------------------------------------------------------
    # Auto-retrieve on new conversation
    # ------------------------------------------------------------------

    async def retrieve_relevant_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search Long-term Memory for relevant past experiences.

        Args:
            query: The user's current input to match against.
            user_id: Filter memories by user.
            limit: Maximum memories to return.

        Returns:
            List of relevant memory records.
        """
        if self._memory is None:
            return []

        try:
            # Try UnifiedMemoryManager.search() first
            if hasattr(self._memory, "search"):
                results = await self._memory.search(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                )
                if isinstance(results, list):
                    return results

            # Fallback: Try Mem0Client.search_memory()
            if hasattr(self._memory, "search_memory"):
                from src.integrations.memory.types import MemorySearchQuery
                search_query = MemorySearchQuery(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                )
                results = await self._memory.search_memory(search_query)
                return [r.to_dict() if hasattr(r, "to_dict") else r for r in results]

        except ImportError:
            logger.warning("Memory: types module not available")
        except Exception as e:
            logger.error("Memory: retrieval failed: %s", e, exc_info=True)

        return []

    def build_memory_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format retrieved memories into a context string for prompt injection.

        Args:
            memories: List of memory records from retrieve_relevant_memories().

        Returns:
            Formatted string to inject into the system prompt.
        """
        if not memories:
            return ""

        memory_lines: List[str] = []
        for i, mem in enumerate(memories[:5], 1):
            content = mem.get("content") or mem.get("memory") or str(mem)
            metadata = mem.get("metadata", {})
            timestamp = metadata.get("summarised_at", metadata.get("created_at", ""))
            if timestamp:
                memory_lines.append(f"{i}. [{timestamp[:10]}] {content}")
            else:
                memory_lines.append(f"{i}. {content}")

        if not memory_lines:
            return ""

        memories_text = "\n".join(memory_lines)
        return MEMORY_INJECTION_TEMPLATE.format(memories_text=memories_text)

    # ------------------------------------------------------------------
    # Memory promotion
    # ------------------------------------------------------------------

    async def promote_working_to_longterm(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> int:
        """Promote important Working Memory entries to Long-term.

        Scans the session's Working Memory (Redis) for entries marked as
        important, then writes them to Long-term Memory (mem0).

        Returns:
            Number of memories promoted.
        """
        if self._conv_store is None or self._memory is None:
            return 0

        promoted = 0
        try:
            state = await self._conv_store.load(session_id)
            if state is None:
                return 0

            # Promote tool call results that are significant
            for tool_call in state.active_tool_calls:
                if tool_call.get("important", False):
                    content = f"Tool result: {tool_call.get('tool_name', 'unknown')}: {tool_call.get('result', '')}"
                    await self._write_to_longterm(
                        content=content[:500],
                        user_id=user_id or "system",
                        metadata={
                            "session_id": session_id,
                            "source": "working_memory_promotion",
                            "tool_name": tool_call.get("tool_name"),
                        },
                    )
                    promoted += 1

        except Exception as e:
            logger.error("Memory promotion failed: %s", e, exc_info=True)

        if promoted > 0:
            logger.info("Memory: promoted %d entries from Working → Long-term", promoted)
        return promoted

    # ------------------------------------------------------------------
    # Enhanced search_memory tool handler
    # ------------------------------------------------------------------

    async def handle_search_memory(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
        time_range: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Enhanced search_memory handler with semantic search + filters.

        This replaces the basic handler in DispatchHandlers for richer
        memory search capabilities.

        Args:
            query: Search query string.
            user_id: Filter by user.
            limit: Max results.
            time_range: Optional time filter (e.g., "7d", "30d").

        Returns:
            Dict with results and count.
        """
        memories = await self.retrieve_relevant_memories(
            query=query,
            user_id=user_id,
            limit=limit,
        )

        # Apply time_range filter if provided
        if time_range and memories:
            memories = self._filter_by_time(memories, time_range)

        return {
            "results": memories,
            "count": len(memories),
            "query": query,
            "user_id": user_id,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_conversation_text(self, session_id: str) -> Optional[str]:
        """Load and format conversation text from L1 store."""
        if self._conv_store is None:
            return None
        try:
            state = await self._conv_store.load(session_id)
            if state is None or not state.messages:
                return None
            lines = []
            for msg in state.messages:
                role = msg.role.upper()
                lines.append(f"[{role}]: {msg.content}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("Failed to load conversation: %s", e)
            return None

    async def _generate_summary(self, conversation_text: str) -> Optional[Dict[str, Any]]:
        """Generate structured summary via LLM."""
        if self._llm is None:
            # Without LLM, create a basic summary
            return {
                "problem": conversation_text[:200],
                "resolution": "",
                "outcome": "",
                "lessons": "",
                "tags": [],
                "importance": "medium",
            }

        try:
            import json as json_module
            prompt = SUMMARY_PROMPT.format(conversation=conversation_text[:3000])
            response = await self._llm.generate(
                prompt=prompt,
                max_tokens=512,
                temperature=0.2,
            )
            return json_module.loads(response)
        except Exception as e:
            logger.error("Summary generation failed: %s", e)
            return {
                "problem": conversation_text[:200],
                "resolution": "",
                "outcome": "",
                "lessons": "",
                "tags": [],
                "importance": "medium",
            }

    @staticmethod
    def _format_memory_content(summary: Dict[str, Any]) -> str:
        """Format summary dict into a memory content string."""
        parts = []
        if summary.get("problem"):
            parts.append(f"問題: {summary['problem']}")
        if summary.get("resolution"):
            parts.append(f"處理: {summary['resolution']}")
        if summary.get("outcome"):
            parts.append(f"結果: {summary['outcome']}")
        if summary.get("lessons"):
            parts.append(f"教訓: {summary['lessons']}")
        return " | ".join(parts) if parts else str(summary)

    async def _write_to_longterm(
        self,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Write a memory record to Long-term Memory."""
        if self._memory is None:
            logger.warning("Memory: no memory client configured")
            return None

        try:
            if hasattr(self._memory, "add"):
                result = await self._memory.add(
                    content=content,
                    user_id=user_id,
                    metadata=metadata,
                )
                return result if isinstance(result, dict) else {"id": str(result)}

            if hasattr(self._memory, "add_memory"):
                result = await self._memory.add_memory(
                    content=content,
                    user_id=user_id,
                    metadata=metadata,
                )
                return result.to_dict() if hasattr(result, "to_dict") else {"id": str(result)}

        except Exception as e:
            logger.error("Memory write failed: %s", e, exc_info=True)
        return None

    @staticmethod
    def _filter_by_time(
        memories: List[Dict[str, Any]], time_range: str
    ) -> List[Dict[str, Any]]:
        """Filter memories by time range string (e.g., '7d', '30d')."""
        from datetime import timedelta
        try:
            days = int(time_range.rstrip("d"))
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = []
            for mem in memories:
                meta = mem.get("metadata", {})
                created = meta.get("created_at") or meta.get("summarised_at")
                if created:
                    if isinstance(created, str):
                        try:
                            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            if dt.replace(tzinfo=None) >= cutoff:
                                filtered.append(mem)
                                continue
                        except (ValueError, TypeError):
                            pass
                # If we can't parse date, include the memory
                filtered.append(mem)
            return filtered
        except (ValueError, AttributeError):
            return memories
