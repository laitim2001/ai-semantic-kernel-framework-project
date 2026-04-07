# =============================================================================
# IPA Platform - Transcript Entry Model
# =============================================================================
# Append-only execution record for orchestrator pipeline.
# Inspired by Claude Code's JSONL transcript persistence,
# adapted for server-side multi-user service.
# =============================================================================

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class TranscriptEntry:
    """Single entry in the append-only execution transcript.

    Each orchestrator pipeline step produces one entry. Entries are
    immutable once written to Redis Stream — forming an audit trail.
    """

    user_id: str
    session_id: str
    step_name: str          # "read_memory", "analyze_intent", "llm_route_decision", etc.
    step_index: int         # 0-6 for 7-step pipeline
    entry_type: str         # "step_complete" | "step_error" | "decision" | "approval_required"
    output_summary: dict = field(default_factory=dict)
    checkpoint_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)   # duration_ms, token_count, etc.
    entry_id: Optional[str] = None                 # Redis Stream auto-generated ID
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_stream_dict(self) -> dict[str, str]:
        """Serialize to flat dict for Redis XADD (values must be strings)."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "step_name": self.step_name,
            "step_index": str(self.step_index),
            "entry_type": self.entry_type,
            "output_summary": json.dumps(self.output_summary, default=str),
            "checkpoint_id": self.checkpoint_id or "",
            "metadata": json.dumps(self.metadata, default=str),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_stream_dict(cls, entry_id: str, data: dict[str, str]) -> "TranscriptEntry":
        """Deserialize from Redis Stream entry."""
        return cls(
            entry_id=entry_id,
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            step_name=data.get("step_name", ""),
            step_index=int(data.get("step_index", "0")),
            entry_type=data.get("entry_type", ""),
            output_summary=json.loads(data.get("output_summary", "{}")),
            checkpoint_id=data.get("checkpoint_id") or None,
            metadata=json.loads(data.get("metadata", "{}")),
            timestamp=data.get("timestamp", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Full serialization for API responses."""
        return asdict(self)


@dataclass
class AgentSidechainEntry:
    """Entry in a subagent's sidechain transcript."""

    user_id: str
    session_id: str
    agent_name: str
    event_type: str         # "start" | "tool_call" | "tool_result" | "complete" | "error"
    content: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    entry_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_stream_dict(self) -> dict[str, str]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "event_type": self.event_type,
            "content": json.dumps(self.content, default=str),
            "metadata": json.dumps(self.metadata, default=str),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_stream_dict(cls, entry_id: str, data: dict[str, str]) -> "AgentSidechainEntry":
        return cls(
            entry_id=entry_id,
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            agent_name=data.get("agent_name", ""),
            event_type=data.get("event_type", ""),
            content=json.loads(data.get("content", "{}")),
            metadata=json.loads(data.get("metadata", "{}")),
            timestamp=data.get("timestamp", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
