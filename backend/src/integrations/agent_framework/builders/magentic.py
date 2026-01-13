# =============================================================================
# IPA Platform - MagenticBuilder Adapter (Magentic One)
# =============================================================================
# Sprint 17: S17-1 MagenticBuilder 適配器 (8 points)
#            S17-2 StandardMagenticManager 實現 (8 points)
#
# This module provides an adapter layer for Microsoft Agent Framework's
# MagenticBuilder (Magentic One), enabling dynamic planning and multi-agent
# orchestration with task/progress ledger support.
#
# Key Features:
# - MagenticBuilderAdapter: Core adapter wrapping Agent Framework MagenticBuilder
# - MagenticManagerAdapter: Custom manager for DynamicPlanner migration
# - Task/Progress Ledger: Fact extraction, planning, progress evaluation
# - Human Intervention: PLAN_REVIEW, TOOL_APPROVAL, STALL support
#
# Agent Framework API Mapping:
# - participants() -> MagenticBuilder.participants()
# - with_standard_manager() -> MagenticBuilder.with_standard_manager()
# - with_plan_review() -> MagenticBuilder.with_plan_review()
# - with_stall_intervention() -> Enable stall handling
# - build() -> MagenticBuilder.build()
#
# Reference: agent_framework/_workflows/_magentic.py
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
import asyncio
import logging

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 19 整合)
# =============================================================================
from agent_framework import (
    MagenticBuilder,
    MagenticManagerBase,
    StandardMagenticManager,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class MagenticStatus(str, Enum):
    """Magentic workflow execution status."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    STALLED = "stalled"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HumanInterventionKind(str, Enum):
    """
    Types of human intervention in Magentic workflows.

    Maps to Agent Framework's MagenticHumanInterventionKind.
    """

    PLAN_REVIEW = "plan_review"      # Review and approve/revise initial plan
    TOOL_APPROVAL = "tool_approval"  # Approve tool/function call
    STALL = "stall"                  # Workflow stalled, needs guidance


class HumanInterventionDecision(str, Enum):
    """
    Decision options for human intervention responses.

    Maps to Agent Framework's MagenticHumanInterventionDecision.
    """

    APPROVE = "approve"    # Approve (plan review, tool approval)
    REVISE = "revise"      # Request revision with feedback
    REJECT = "reject"      # Reject/deny
    CONTINUE = "continue"  # Continue with current state
    REPLAN = "replan"      # Trigger replanning
    GUIDANCE = "guidance"  # Provide guidance text


class MessageRole(str, Enum):
    """Message role in conversations."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    MANAGER = "manager"


# Manager name constant
MAGENTIC_MANAGER_NAME = "magentic_manager"


# =============================================================================
# Data Classes - Messages and Context
# =============================================================================


@dataclass
class MagenticMessage:
    """
    A message in a Magentic workflow conversation.

    Maps to Agent Framework's ChatMessage with Magentic-specific extensions.
    """

    role: MessageRole
    content: str
    author_name: Optional[str] = None
    timestamp: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "role": self.role.value if isinstance(self.role, MessageRole) else self.role,
            "content": self.content,
            "author_name": self.author_name,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MagenticMessage":
        """Create from dictionary."""
        role = data.get("role", "user")
        if isinstance(role, str):
            role = MessageRole(role)
        return cls(
            role=role,
            content=data.get("content", ""),
            author_name=data.get("author_name"),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MagenticParticipant:
    """
    A participant (agent) in a Magentic workflow.

    Participants are the agents that execute tasks under manager direction.
    """

    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MagenticParticipant":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MagenticContext:
    """
    Context for a Magentic workflow execution.

    Maps to Agent Framework's MagenticContext.
    """

    task: MagenticMessage
    chat_history: List[MagenticMessage] = field(default_factory=list)
    participant_descriptions: Dict[str, str] = field(default_factory=dict)
    round_count: int = 0
    stall_count: int = 0
    reset_count: int = 0

    def clone(self, deep: bool = True) -> "MagenticContext":
        """Create a clone of the context."""
        if deep:
            return MagenticContext(
                task=MagenticMessage.from_dict(self.task.to_dict()),
                chat_history=[MagenticMessage.from_dict(m.to_dict()) for m in self.chat_history],
                participant_descriptions=dict(self.participant_descriptions),
                round_count=self.round_count,
                stall_count=self.stall_count,
                reset_count=self.reset_count,
            )
        return MagenticContext(
            task=self.task,
            chat_history=list(self.chat_history),
            participant_descriptions=dict(self.participant_descriptions),
            round_count=self.round_count,
            stall_count=self.stall_count,
            reset_count=self.reset_count,
        )

    def reset(self) -> None:
        """Reset the context for replanning."""
        self.chat_history.clear()
        self.stall_count = 0
        self.reset_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task": self.task.to_dict(),
            "chat_history": [m.to_dict() for m in self.chat_history],
            "participant_descriptions": self.participant_descriptions,
            "round_count": self.round_count,
            "stall_count": self.stall_count,
            "reset_count": self.reset_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MagenticContext":
        """Create from dictionary."""
        task_data = data.get("task", {})
        return cls(
            task=MagenticMessage.from_dict(task_data) if task_data else MagenticMessage(
                role=MessageRole.USER, content=""
            ),
            chat_history=[
                MagenticMessage.from_dict(m) for m in data.get("chat_history", [])
            ],
            participant_descriptions=data.get("participant_descriptions", {}),
            round_count=data.get("round_count", 0),
            stall_count=data.get("stall_count", 0),
            reset_count=data.get("reset_count", 0),
        )


# =============================================================================
# Data Classes - Ledger System
# =============================================================================


@dataclass
class TaskLedger:
    """
    Task ledger containing facts and plan.

    Maps to Agent Framework's _MagenticTaskLedger.
    """

    facts: MagenticMessage
    plan: MagenticMessage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "facts": self.facts.to_dict(),
            "plan": self.plan.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskLedger":
        """Create from dictionary."""
        return cls(
            facts=MagenticMessage.from_dict(data.get("facts", {})),
            plan=MagenticMessage.from_dict(data.get("plan", {})),
        )


@dataclass
class ProgressLedgerItem:
    """
    A single item in the progress ledger.

    Maps to Agent Framework's _MagenticProgressLedgerItem.
    """

    reason: str
    answer: Union[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "reason": self.reason,
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressLedgerItem":
        """Create from dictionary."""
        return cls(
            reason=data.get("reason", ""),
            answer=data.get("answer", ""),
        )


@dataclass
class ProgressLedger:
    """
    Progress ledger for tracking workflow progress.

    Maps to Agent Framework's _MagenticProgressLedger.
    Contains evaluation of:
    - is_request_satisfied: Is the task complete?
    - is_in_loop: Are we stuck in a loop?
    - is_progress_being_made: Are we making forward progress?
    - next_speaker: Which agent should speak next?
    - instruction_or_question: What instruction to give the agent?
    """

    is_request_satisfied: ProgressLedgerItem
    is_in_loop: ProgressLedgerItem
    is_progress_being_made: ProgressLedgerItem
    next_speaker: ProgressLedgerItem
    instruction_or_question: ProgressLedgerItem

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_request_satisfied": self.is_request_satisfied.to_dict(),
            "is_in_loop": self.is_in_loop.to_dict(),
            "is_progress_being_made": self.is_progress_being_made.to_dict(),
            "next_speaker": self.next_speaker.to_dict(),
            "instruction_or_question": self.instruction_or_question.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressLedger":
        """Create from dictionary."""
        return cls(
            is_request_satisfied=ProgressLedgerItem.from_dict(
                data.get("is_request_satisfied", {})
            ),
            is_in_loop=ProgressLedgerItem.from_dict(
                data.get("is_in_loop", {})
            ),
            is_progress_being_made=ProgressLedgerItem.from_dict(
                data.get("is_progress_being_made", {})
            ),
            next_speaker=ProgressLedgerItem.from_dict(
                data.get("next_speaker", {})
            ),
            instruction_or_question=ProgressLedgerItem.from_dict(
                data.get("instruction_or_question", {})
            ),
        )

    @property
    def is_complete(self) -> bool:
        """Check if the task is complete."""
        answer = self.is_request_satisfied.answer
        if isinstance(answer, bool):
            return answer
        return str(answer).lower() in ("true", "yes", "1")

    @property
    def is_stalled(self) -> bool:
        """Check if the workflow is stalled."""
        in_loop = self.is_in_loop.answer
        no_progress = not self.is_progress_being_made.answer

        in_loop_bool = in_loop if isinstance(in_loop, bool) else str(in_loop).lower() in ("true", "yes", "1")
        no_progress_bool = no_progress if isinstance(no_progress, bool) else str(no_progress).lower() in ("true", "yes", "1")

        return in_loop_bool or no_progress_bool

    @property
    def selected_speaker(self) -> str:
        """Get the selected next speaker."""
        answer = self.next_speaker.answer
        return str(answer) if answer else ""

    @property
    def instruction(self) -> str:
        """Get the instruction for the next speaker."""
        answer = self.instruction_or_question.answer
        return str(answer) if answer else ""


# =============================================================================
# Data Classes - Human Intervention
# =============================================================================


@dataclass
class HumanInterventionRequest:
    """
    Request for human intervention in a Magentic workflow.

    Maps to Agent Framework's _MagenticHumanInterventionRequest.
    """

    request_id: str = field(default_factory=lambda: str(uuid4()))
    kind: HumanInterventionKind = HumanInterventionKind.PLAN_REVIEW

    # Plan review fields
    task_text: str = ""
    facts_text: str = ""
    plan_text: str = ""
    round_index: int = 0

    # Tool approval fields
    agent_id: str = ""
    prompt: str = ""
    context: Optional[str] = None
    conversation_snapshot: List[MagenticMessage] = field(default_factory=list)

    # Stall intervention fields
    stall_count: int = 0
    max_stall_count: int = 3
    stall_reason: str = ""
    last_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "kind": self.kind.value if isinstance(self.kind, HumanInterventionKind) else self.kind,
            "task_text": self.task_text,
            "facts_text": self.facts_text,
            "plan_text": self.plan_text,
            "round_index": self.round_index,
            "agent_id": self.agent_id,
            "prompt": self.prompt,
            "context": self.context,
            "conversation_snapshot": [m.to_dict() for m in self.conversation_snapshot],
            "stall_count": self.stall_count,
            "max_stall_count": self.max_stall_count,
            "stall_reason": self.stall_reason,
            "last_agent": self.last_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanInterventionRequest":
        """Create from dictionary."""
        kind = data.get("kind", "plan_review")
        if isinstance(kind, str):
            kind = HumanInterventionKind(kind)

        return cls(
            request_id=data.get("request_id", str(uuid4())),
            kind=kind,
            task_text=data.get("task_text", ""),
            facts_text=data.get("facts_text", ""),
            plan_text=data.get("plan_text", ""),
            round_index=data.get("round_index", 0),
            agent_id=data.get("agent_id", ""),
            prompt=data.get("prompt", ""),
            context=data.get("context"),
            conversation_snapshot=[
                MagenticMessage.from_dict(m) for m in data.get("conversation_snapshot", [])
            ],
            stall_count=data.get("stall_count", 0),
            max_stall_count=data.get("max_stall_count", 3),
            stall_reason=data.get("stall_reason", ""),
            last_agent=data.get("last_agent", ""),
        )


@dataclass
class HumanInterventionReply:
    """
    Reply to a human intervention request.

    Maps to Agent Framework's _MagenticHumanInterventionReply.
    """

    decision: HumanInterventionDecision
    edited_plan_text: Optional[str] = None
    comments: Optional[str] = None
    response_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "decision": self.decision.value if isinstance(self.decision, HumanInterventionDecision) else self.decision,
            "edited_plan_text": self.edited_plan_text,
            "comments": self.comments,
            "response_text": self.response_text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanInterventionReply":
        """Create from dictionary."""
        decision = data.get("decision", "approve")
        if isinstance(decision, str):
            decision = HumanInterventionDecision(decision)

        return cls(
            decision=decision,
            edited_plan_text=data.get("edited_plan_text"),
            comments=data.get("comments"),
            response_text=data.get("response_text"),
        )


# =============================================================================
# Data Classes - Execution Results
# =============================================================================


@dataclass
class MagenticRound:
    """A single round of Magentic workflow execution."""

    round_index: int
    speaker: str
    instruction: str
    response: Optional[MagenticMessage] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "round_index": self.round_index,
            "speaker": self.speaker,
            "instruction": self.instruction,
            "response": self.response.to_dict() if self.response else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class MagenticResult:
    """
    Result of a Magentic workflow execution.

    Contains the final answer, conversation history, and execution metadata.
    """

    status: MagenticStatus
    final_answer: Optional[MagenticMessage] = None
    conversation: List[MagenticMessage] = field(default_factory=list)
    rounds: List[MagenticRound] = field(default_factory=list)
    total_rounds: int = 0
    total_resets: int = 0
    participants_involved: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    termination_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status.value if isinstance(self.status, MagenticStatus) else self.status,
            "final_answer": self.final_answer.to_dict() if self.final_answer else None,
            "conversation": [m.to_dict() for m in self.conversation],
            "rounds": [r.to_dict() for r in self.rounds],
            "total_rounds": self.total_rounds,
            "total_resets": self.total_resets,
            "participants_involved": self.participants_involved,
            "duration_seconds": self.duration_seconds,
            "termination_reason": self.termination_reason,
            "metadata": self.metadata,
        }


# =============================================================================
# Manager Base Class
# =============================================================================


class MagenticManagerBase(ABC):
    """
    Base class for Magentic managers.

    Maps to Agent Framework's MagenticManagerBase.
    The manager is responsible for:
    - Creating initial plans from task descriptions
    - Evaluating progress through progress ledgers
    - Replanning when stalled
    - Preparing final answers
    """

    def __init__(
        self,
        *,
        max_stall_count: int = 3,
        max_reset_count: Optional[int] = None,
        max_round_count: Optional[int] = None,
    ):
        """
        Initialize the manager.

        Args:
            max_stall_count: Maximum consecutive stalls before intervention
            max_reset_count: Maximum resets allowed (None = unlimited)
            max_round_count: Maximum rounds allowed (None = unlimited)
        """
        self.max_stall_count = max_stall_count
        self.max_reset_count = max_reset_count
        self.max_round_count = max_round_count
        self.task_ledger: Optional[TaskLedger] = None

    @abstractmethod
    async def plan(self, context: MagenticContext) -> MagenticMessage:
        """
        Create an initial plan for the task.

        Args:
            context: Current workflow context with task and participants

        Returns:
            Message containing the task ledger (facts + plan)
        """
        ...

    @abstractmethod
    async def replan(self, context: MagenticContext) -> MagenticMessage:
        """
        Create a new plan after stalling or resetting.

        Args:
            context: Current workflow context

        Returns:
            Message containing the updated task ledger
        """
        ...

    @abstractmethod
    async def create_progress_ledger(self, context: MagenticContext) -> ProgressLedger:
        """
        Evaluate current progress and determine next steps.

        Args:
            context: Current workflow context with conversation history

        Returns:
            Progress ledger with evaluation results
        """
        ...

    @abstractmethod
    async def prepare_final_answer(self, context: MagenticContext) -> MagenticMessage:
        """
        Prepare the final answer for the task.

        Args:
            context: Current workflow context with full conversation

        Returns:
            Message containing the final answer
        """
        ...

    def on_checkpoint_save(self) -> Dict[str, Any]:
        """Serialize manager state for checkpointing."""
        return {
            "task_ledger": self.task_ledger.to_dict() if self.task_ledger else None,
        }

    def on_checkpoint_restore(self, state: Dict[str, Any]) -> None:
        """Restore manager state from checkpoint."""
        ledger_data = state.get("task_ledger")
        if ledger_data:
            self.task_ledger = TaskLedger.from_dict(ledger_data)


# =============================================================================
# Standard Manager Implementation
# =============================================================================


class StandardMagenticManager(MagenticManagerBase):
    """
    Standard Magentic manager implementation.

    Maps to Agent Framework's StandardMagenticManager.
    Uses customizable prompts for planning and progress evaluation.
    """

    # Default prompts (simplified versions of Agent Framework prompts)
    DEFAULT_FACTS_PROMPT = """Analyze the following task and list:
1. GIVEN OR VERIFIED FACTS - specific facts from the request
2. FACTS TO LOOK UP - facts that need to be researched
3. FACTS TO DERIVE - facts that need computation or deduction
4. EDUCATED GUESSES - reasonable assumptions

Task: {task}
"""

    DEFAULT_PLAN_PROMPT = """Based on the team composition and facts, create a bullet-point plan:

Team: {team}
Facts: {facts}

Create a concise plan to address the original task.
"""

    DEFAULT_PROGRESS_PROMPT = """Evaluate progress on the task:

Task: {task}
Team: {team}

Answer these questions as JSON:
{{
    "is_request_satisfied": {{"reason": "...", "answer": true/false}},
    "is_in_loop": {{"reason": "...", "answer": true/false}},
    "is_progress_being_made": {{"reason": "...", "answer": true/false}},
    "next_speaker": {{"reason": "...", "answer": "agent_name"}},
    "instruction_or_question": {{"reason": "...", "answer": "instruction text"}}
}}

Select next_speaker from: {names}
"""

    DEFAULT_FINAL_ANSWER_PROMPT = """Based on the conversation, provide the final answer to:

Task: {task}

Provide a complete answer addressing all aspects of the request.
"""

    def __init__(
        self,
        agent_executor: Optional[Callable] = None,
        task_ledger: Optional[TaskLedger] = None,
        *,
        facts_prompt: Optional[str] = None,
        plan_prompt: Optional[str] = None,
        progress_prompt: Optional[str] = None,
        final_answer_prompt: Optional[str] = None,
        max_stall_count: int = 3,
        max_reset_count: Optional[int] = None,
        max_round_count: Optional[int] = None,
    ):
        """
        Initialize the standard manager.

        Args:
            agent_executor: Callable to execute agent for LLM calls
            task_ledger: Optional pre-existing task ledger
            facts_prompt: Custom prompt for facts extraction
            plan_prompt: Custom prompt for plan creation
            progress_prompt: Custom prompt for progress evaluation
            final_answer_prompt: Custom prompt for final answer
            max_stall_count: Maximum stalls before intervention
            max_reset_count: Maximum resets allowed
            max_round_count: Maximum rounds allowed
        """
        super().__init__(
            max_stall_count=max_stall_count,
            max_reset_count=max_reset_count,
            max_round_count=max_round_count,
        )

        self._agent_executor = agent_executor
        self.task_ledger = task_ledger

        self.facts_prompt = facts_prompt or self.DEFAULT_FACTS_PROMPT
        self.plan_prompt = plan_prompt or self.DEFAULT_PLAN_PROMPT
        self.progress_prompt = progress_prompt or self.DEFAULT_PROGRESS_PROMPT
        self.final_answer_prompt = final_answer_prompt or self.DEFAULT_FINAL_ANSWER_PROMPT

    async def _execute_prompt(self, prompt: str) -> str:
        """Execute a prompt through the agent executor."""
        if self._agent_executor:
            result = await self._agent_executor(prompt)
            return result if isinstance(result, str) else str(result)

        # Fallback: Return a simulated response
        return f"[Simulated response for: {prompt[:100]}...]"

    def _format_team(self, participants: Dict[str, str]) -> str:
        """Format participant descriptions as a readable block."""
        return "\n".join(f"- {name}: {desc}" for name, desc in participants.items())

    async def plan(self, context: MagenticContext) -> MagenticMessage:
        """Create an initial plan for the task."""
        task_text = context.task.content
        team_text = self._format_team(context.participant_descriptions)

        # Extract facts
        facts_prompt = self.facts_prompt.format(task=task_text)
        facts_response = await self._execute_prompt(facts_prompt)
        facts_message = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=facts_response,
            author_name=MAGENTIC_MANAGER_NAME,
        )

        # Create plan
        plan_prompt = self.plan_prompt.format(
            team=team_text,
            facts=facts_response,
        )
        plan_response = await self._execute_prompt(plan_prompt)
        plan_message = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=plan_response,
            author_name=MAGENTIC_MANAGER_NAME,
        )

        # Store task ledger
        self.task_ledger = TaskLedger(facts=facts_message, plan=plan_message)

        # Return combined ledger message
        ledger_content = f"""Task Ledger:

TASK: {task_text}

TEAM: {team_text}

FACTS:
{facts_response}

PLAN:
{plan_response}
"""
        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=ledger_content,
            author_name=MAGENTIC_MANAGER_NAME,
        )

    async def replan(self, context: MagenticContext) -> MagenticMessage:
        """Create a new plan after stalling."""
        task_text = context.task.content
        team_text = self._format_team(context.participant_descriptions)

        old_facts = self.task_ledger.facts.content if self.task_ledger else ""

        # Update facts
        update_prompt = f"""The previous attempt stalled. Update the fact sheet:

Task: {task_text}
Old Facts: {old_facts}

Add new observations and update guesses based on what was learned.
"""
        facts_response = await self._execute_prompt(update_prompt)
        facts_message = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=facts_response,
            author_name=MAGENTIC_MANAGER_NAME,
        )

        # Create new plan
        replan_prompt = f"""Create a new plan that avoids previous mistakes:

Team: {team_text}
Updated Facts: {facts_response}

Focus on overcoming the obstacles that caused the stall.
"""
        plan_response = await self._execute_prompt(replan_prompt)
        plan_message = MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=plan_response,
            author_name=MAGENTIC_MANAGER_NAME,
        )

        # Update task ledger
        self.task_ledger = TaskLedger(facts=facts_message, plan=plan_message)

        # Return updated ledger
        ledger_content = f"""Updated Task Ledger (Reset #{context.reset_count}):

TASK: {task_text}

UPDATED FACTS:
{facts_response}

NEW PLAN:
{plan_response}
"""
        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=ledger_content,
            author_name=MAGENTIC_MANAGER_NAME,
        )

    async def create_progress_ledger(self, context: MagenticContext) -> ProgressLedger:
        """Evaluate current progress."""
        task_text = context.task.content
        team_text = self._format_team(context.participant_descriptions)
        names = ", ".join(context.participant_descriptions.keys())

        prompt = self.progress_prompt.format(
            task=task_text,
            team=team_text,
            names=names,
        )

        response = await self._execute_prompt(prompt)

        # Parse JSON response (simplified parsing)
        try:
            import json
            data = json.loads(response)
            return ProgressLedger.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            # Fallback: Create a default progress ledger
            default_speaker = list(context.participant_descriptions.keys())[0] if context.participant_descriptions else "agent"
            return ProgressLedger(
                is_request_satisfied=ProgressLedgerItem(reason="Unable to parse", answer=False),
                is_in_loop=ProgressLedgerItem(reason="Unable to parse", answer=False),
                is_progress_being_made=ProgressLedgerItem(reason="Unable to parse", answer=True),
                next_speaker=ProgressLedgerItem(reason="Default selection", answer=default_speaker),
                instruction_or_question=ProgressLedgerItem(reason="Continue task", answer="Please continue with the task."),
            )

    async def prepare_final_answer(self, context: MagenticContext) -> MagenticMessage:
        """Prepare the final answer."""
        task_text = context.task.content

        # Summarize conversation
        conversation_summary = "\n".join([
            f"[{m.author_name or m.role.value}]: {m.content[:200]}..."
            for m in context.chat_history[-10:]  # Last 10 messages
        ])

        prompt = f"""{self.final_answer_prompt.format(task=task_text)}

Conversation Summary:
{conversation_summary}

Provide the final answer:
"""
        response = await self._execute_prompt(prompt)

        return MagenticMessage(
            role=MessageRole.ASSISTANT,
            content=response,
            author_name=MAGENTIC_MANAGER_NAME,
        )


# =============================================================================
# MagenticBuilder Adapter
# =============================================================================


class MagenticBuilderAdapter:
    """
    Adapter for Agent Framework MagenticBuilder.

    Provides a fluent API for creating Magentic One multi-agent workflows
    with dynamic planning, progress tracking, and human intervention support.

    Usage:
        adapter = (
            MagenticBuilderAdapter(id="my-workflow")
            .participants(
                researcher=MagenticParticipant(name="researcher", description="Research agent"),
                writer=MagenticParticipant(name="writer", description="Writing agent"),
            )
            .with_standard_manager(max_round_count=20, max_stall_count=3)
            .with_plan_review(enable=True)
            .build()
        )

        result = await adapter.run("Research and write an article about AI")
    """

    def __init__(
        self,
        id: str,
        participants: Optional[List[MagenticParticipant]] = None,
        max_round_count: int = 20,
        max_stall_count: int = 3,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the adapter.

        Args:
            id: Unique identifier for this workflow
            participants: Optional list of MagenticParticipant (for backward compatibility)
            max_round_count: Maximum number of execution rounds
            max_stall_count: Maximum stall count before intervention
            config: Optional configuration dictionary

        Raises:
            ValueError: If id is empty or participants list is empty (when provided)
        """
        if not id:
            raise ValueError("ID cannot be empty")

        self._id = id
        self._config = config or {}
        self._max_round_count = max_round_count
        self._max_stall_count = max_stall_count

        # Builder state
        self._participants: Dict[str, MagenticParticipant] = {}
        self._manager: Optional[MagenticManagerBase] = None
        self._enable_plan_review: bool = False
        self._enable_stall_intervention: bool = False
        self._max_plan_review_rounds: int = 3

        # Execution state
        self._status = MagenticStatus.IDLE
        self._context: Optional[MagenticContext] = None
        self._is_built = False
        self._is_initialized = False

        # Execution tracking
        self._round_count = 0
        self._stall_count = 0
        self._events: List[Dict[str, Any]] = []

        # Sprint 19: 使用官方 MagenticBuilder API
        self._builder = MagenticBuilder()

        # Add initial participants if provided (backward compatibility)
        if participants is not None:
            if len(participants) == 0:
                raise ValueError("At least one participant is required")
            for participant in participants:
                self._participants[participant.name] = participant

    @property
    def id(self) -> str:
        """Get the workflow ID."""
        return self._id

    @property
    def status(self) -> MagenticStatus:
        """Get the current execution status."""
        return self._status

    @property
    def is_built(self) -> bool:
        """Check if the workflow has been built."""
        return self._is_built

    @property
    def is_initialized(self) -> bool:
        """Check if the workflow has been initialized."""
        return self._is_initialized

    @property
    def participants(self) -> List[MagenticParticipant]:
        """Get the list of participants."""
        return list(self._participants.values())

    def add_participant(self, participant: MagenticParticipant) -> "MagenticBuilderAdapter":
        """
        Add a single participant to the workflow.

        Args:
            participant: MagenticParticipant to add

        Returns:
            Self for method chaining

        Raises:
            ValueError: If participant with same name already exists
        """
        if participant.name in self._participants:
            raise ValueError(f"Participant '{participant.name}' already exists")
        self._participants[participant.name] = participant
        return self

    def remove_participant(self, name: str) -> bool:
        """
        Remove a participant by name.

        Args:
            name: Name of the participant to remove

        Returns:
            True if participant was removed, False if not found
        """
        if name in self._participants:
            del self._participants[name]
            return True
        return False

    def set_max_round_count(self, count: int) -> None:
        """Set the maximum number of execution rounds."""
        self._max_round_count = count

    def set_max_stall_count(self, count: int) -> None:
        """Set the maximum stall count before intervention."""
        self._max_stall_count = count

    async def initialize(self) -> None:
        """Initialize the adapter for execution."""
        self._is_initialized = True
        self._status = MagenticStatus.IDLE

    async def cleanup(self) -> None:
        """Cleanup resources after execution."""
        self._is_initialized = False
        self._is_built = False
        self._context = None
        self._events.clear()

    async def reset(self) -> None:
        """Reset the adapter state for a new execution."""
        self._round_count = 0
        self._stall_count = 0
        self._status = MagenticStatus.IDLE
        self._context = None

    def get_ledger(self) -> Optional[Dict[str, Any]]:
        """Get the current execution ledger."""
        if self._context:
            return {
                "task_ledger": self._context.task_ledger.to_dict() if self._context.task_ledger else None,
                "progress_ledger": self._context.progress_ledger.to_dict() if self._context.progress_ledger else None,
            }
        return None

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all execution events."""
        return list(self._events)

    def clear_events(self) -> None:
        """Clear all execution events."""
        self._events.clear()

    def set_participants(self, **participants: MagenticParticipant) -> "MagenticBuilderAdapter":
        """
        Add participant agents to the workflow.

        Args:
            **participants: Named participants (name=MagenticParticipant)

        Returns:
            Self for method chaining
        """
        for name, participant in participants.items():
            if isinstance(participant, MagenticParticipant):
                self._participants[name] = participant
            elif isinstance(participant, dict):
                self._participants[name] = MagenticParticipant.from_dict(participant)
            else:
                # Create from name/description tuple or string
                self._participants[name] = MagenticParticipant(
                    name=name,
                    description=str(participant) if participant else "",
                )
        return self

    def with_manager(self, manager: MagenticManagerBase) -> "MagenticBuilderAdapter":
        """
        Set a custom manager for the workflow.

        Args:
            manager: Custom manager instance

        Returns:
            Self for method chaining
        """
        self._manager = manager
        return self

    def with_standard_manager(
        self,
        manager: Optional[MagenticManagerBase] = None,
        *,
        agent_executor: Optional[Callable] = None,
        max_stall_count: int = 3,
        max_reset_count: Optional[int] = None,
        max_round_count: Optional[int] = None,
        facts_prompt: Optional[str] = None,
        plan_prompt: Optional[str] = None,
        progress_prompt: Optional[str] = None,
        final_answer_prompt: Optional[str] = None,
    ) -> "MagenticBuilderAdapter":
        """
        Configure a standard manager for the workflow.

        Args:
            manager: Optional pre-configured manager instance
            agent_executor: Callable for LLM execution
            max_stall_count: Maximum stalls before intervention
            max_reset_count: Maximum resets allowed
            max_round_count: Maximum rounds allowed
            facts_prompt: Custom facts extraction prompt
            plan_prompt: Custom plan creation prompt
            progress_prompt: Custom progress evaluation prompt
            final_answer_prompt: Custom final answer prompt

        Returns:
            Self for method chaining
        """
        if manager is not None:
            self._manager = manager
        else:
            self._manager = StandardMagenticManager(
                agent_executor=agent_executor,
                max_stall_count=max_stall_count,
                max_reset_count=max_reset_count,
                max_round_count=max_round_count,
                facts_prompt=facts_prompt,
                plan_prompt=plan_prompt,
                progress_prompt=progress_prompt,
                final_answer_prompt=final_answer_prompt,
            )
        # Update adapter's own max values
        if max_round_count is not None:
            self._max_round_count = max_round_count
        self._max_stall_count = max_stall_count
        return self

    def with_plan_review(
        self,
        enable: bool = True,
        max_rounds: int = 3,
    ) -> "MagenticBuilderAdapter":
        """
        Enable human-in-the-loop plan review.

        When enabled, the workflow pauses after initial planning for human approval.

        Args:
            enable: Whether to enable plan review
            max_rounds: Maximum review rounds before auto-approval

        Returns:
            Self for method chaining
        """
        self._enable_plan_review = enable
        self._max_plan_review_rounds = max_rounds
        return self

    def with_stall_intervention(self, enable: bool = True) -> "MagenticBuilderAdapter":
        """
        Enable human intervention when workflow stalls.

        Args:
            enable: Whether to enable stall intervention

        Returns:
            Self for method chaining
        """
        self._enable_stall_intervention = enable
        return self

    def build(self) -> "MagenticBuilderAdapter":
        """
        Build the workflow.

        使用官方 Agent Framework MagenticBuilder API 構建工作流。

        Returns:
            Self for method chaining

        Raises:
            ValueError: If configuration is invalid
        """
        if not self._participants:
            raise ValueError("No participants added to workflow")

        if self._manager is None:
            # Create default manager
            self._manager = StandardMagenticManager()

        # Sprint 19: 使用官方 MagenticBuilder API 構建工作流
        # 將 IPA 平台參與者轉換為官方 API 格式
        # Note: 使用參與者的 metadata.get('agent') 或直接使用參與者名稱列表
        participant_agents = []
        for p in self._participants.values():
            agent = p.metadata.get('agent') if p.metadata else None
            if agent:
                participant_agents.append(agent)

        try:
            if participant_agents:
                # 調用官方 MagenticBuilder.participants().build()
                workflow = (
                    self._builder
                    .participants(participant_agents)
                    .build()
                )
                self._workflow = workflow
                logger.info(f"Official MagenticBuilder workflow created: {self._id}")
            else:
                # 沒有 agent 實例時，使用 Mock 工作流
                self._workflow = None
                logger.info(f"Using IPA platform implementation for workflow: {self._id}")
        except Exception as e:
            # 如果官方 API 失敗，記錄警告但繼續使用內部實現
            logger.warning(
                f"Official MagenticBuilder.build() failed: {e}. "
                f"Falling back to IPA platform implementation."
            )
            self._workflow = None

        self._is_built = True
        logger.info(f"Built Magentic workflow '{self._id}' with {len(self._participants)} participants")

        return self

    async def run(
        self,
        task: Union[str, MagenticMessage],
        timeout: Optional[float] = None,
    ) -> MagenticResult:
        """
        Run the workflow synchronously.

        Args:
            task: Task description or message
            timeout: Optional timeout in seconds

        Returns:
            Execution result
        """
        if not self._is_built:
            self.build()

        start_time = datetime.now()

        # Initialize context
        task_message = task if isinstance(task, MagenticMessage) else MagenticMessage(
            role=MessageRole.USER,
            content=task,
        )

        self._context = MagenticContext(
            task=task_message,
            participant_descriptions={
                name: p.description for name, p in self._participants.items()
            },
        )

        self._status = MagenticStatus.PLANNING
        self._is_initialized = True

        try:
            # Create initial plan
            task_ledger = await self._manager.plan(self._context.clone())
            self._context.chat_history.append(task_ledger)

            # Plan review (if enabled)
            if self._enable_plan_review:
                self._status = MagenticStatus.WAITING_APPROVAL
                # In real implementation, would pause for human review
                # For now, auto-approve
                logger.info("Plan review enabled but auto-approving for simulation")

            # Main execution loop
            self._status = MagenticStatus.EXECUTING
            rounds: List[MagenticRound] = []
            participants_involved: List[str] = []

            while True:
                # Check limits
                if self._manager.max_round_count and self._context.round_count >= self._manager.max_round_count:
                    self._status = MagenticStatus.COMPLETED
                    break

                if self._manager.max_reset_count and self._context.reset_count >= self._manager.max_reset_count:
                    self._status = MagenticStatus.COMPLETED
                    break

                # Evaluate progress
                progress = await self._manager.create_progress_ledger(self._context.clone())

                if progress.is_complete:
                    self._status = MagenticStatus.COMPLETED
                    break

                if progress.is_stalled:
                    self._context.stall_count += 1

                    if self._context.stall_count >= self._manager.max_stall_count:
                        if self._enable_stall_intervention:
                            self._status = MagenticStatus.STALLED
                            # Would pause for human intervention
                            logger.info("Stall intervention enabled but auto-replanning")

                        # Replan
                        self._status = MagenticStatus.REPLANNING
                        self._context.reset()
                        replan_message = await self._manager.replan(self._context.clone())
                        self._context.chat_history.append(replan_message)
                        self._status = MagenticStatus.EXECUTING
                        continue

                # Select next speaker and execute
                speaker = progress.selected_speaker
                instruction = progress.instruction

                if speaker not in self._participants:
                    logger.warning(f"Invalid speaker: {speaker}")
                    break

                if speaker not in participants_involved:
                    participants_involved.append(speaker)

                # Simulate agent response (in real implementation, would call agent)
                response = MagenticMessage(
                    role=MessageRole.ASSISTANT,
                    content=f"[Response from {speaker}]: Processed instruction: {instruction}",
                    author_name=speaker,
                )

                self._context.chat_history.append(response)
                self._context.round_count += 1
                self._context.stall_count = 0  # Reset stall count on progress

                rounds.append(MagenticRound(
                    round_index=self._context.round_count,
                    speaker=speaker,
                    instruction=instruction,
                    response=response,
                ))

            # Prepare final answer
            final_answer = await self._manager.prepare_final_answer(self._context.clone())

            duration = (datetime.now() - start_time).total_seconds()

            return MagenticResult(
                status=self._status,
                final_answer=final_answer,
                conversation=list(self._context.chat_history),
                rounds=rounds,
                total_rounds=self._context.round_count,
                total_resets=self._context.reset_count,
                participants_involved=participants_involved,
                duration_seconds=duration,
                termination_reason="completed" if self._status == MagenticStatus.COMPLETED else "limit_reached",
            )

        except Exception as e:
            self._status = MagenticStatus.FAILED
            logger.error(f"Workflow execution failed: {e}")

            duration = (datetime.now() - start_time).total_seconds()

            return MagenticResult(
                status=self._status,
                conversation=list(self._context.chat_history) if self._context else [],
                duration_seconds=duration,
                termination_reason=str(e),
            )

    async def run_stream(
        self,
        task: Union[str, MagenticMessage],
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the workflow with streaming events.

        Args:
            task: Task description or message

        Yields:
            Event dictionaries with execution updates
        """
        if not self._is_built:
            self.build()

        # Initialize
        task_message = task if isinstance(task, MagenticMessage) else MagenticMessage(
            role=MessageRole.USER,
            content=task,
        )

        self._context = MagenticContext(
            task=task_message,
            participant_descriptions={
                name: p.description for name, p in self._participants.items()
            },
        )

        self._status = MagenticStatus.PLANNING
        self._is_initialized = True

        yield {
            "type": "status",
            "status": self._status.value,
            "message": "Starting workflow",
        }

        # Planning phase
        task_ledger = await self._manager.plan(self._context.clone())
        self._context.chat_history.append(task_ledger)

        yield {
            "type": "plan",
            "content": task_ledger.content,
        }

        # Plan review
        if self._enable_plan_review:
            self._status = MagenticStatus.WAITING_APPROVAL
            yield {
                "type": "plan_review_request",
                "status": self._status.value,
            }
            # Auto-approve for simulation

        # Execution loop
        self._status = MagenticStatus.EXECUTING
        yield {"type": "status", "status": self._status.value}

        while True:
            # Check limits
            if self._manager.max_round_count and self._context.round_count >= self._manager.max_round_count:
                break

            # Progress evaluation
            progress = await self._manager.create_progress_ledger(self._context.clone())

            yield {
                "type": "progress",
                "is_complete": progress.is_complete,
                "is_stalled": progress.is_stalled,
                "next_speaker": progress.selected_speaker,
            }

            if progress.is_complete:
                break

            if progress.is_stalled:
                self._context.stall_count += 1
                if self._context.stall_count >= self._manager.max_stall_count:
                    self._status = MagenticStatus.REPLANNING
                    yield {"type": "status", "status": self._status.value}

                    self._context.reset()
                    replan_message = await self._manager.replan(self._context.clone())
                    self._context.chat_history.append(replan_message)

                    yield {"type": "replan", "content": replan_message.content}

                    self._status = MagenticStatus.EXECUTING
                    continue

            # Execute round
            speaker = progress.selected_speaker
            instruction = progress.instruction

            if speaker not in self._participants:
                break

            yield {
                "type": "round_start",
                "round": self._context.round_count + 1,
                "speaker": speaker,
                "instruction": instruction,
            }

            # Simulate response
            response = MagenticMessage(
                role=MessageRole.ASSISTANT,
                content=f"[{speaker}]: Processed: {instruction}",
                author_name=speaker,
            )

            self._context.chat_history.append(response)
            self._context.round_count += 1
            self._context.stall_count = 0

            yield {
                "type": "round_complete",
                "round": self._context.round_count,
                "response": response.to_dict(),
            }

        # Final answer
        self._status = MagenticStatus.COMPLETED
        final_answer = await self._manager.prepare_final_answer(self._context.clone())

        yield {
            "type": "complete",
            "status": self._status.value,
            "final_answer": final_answer.to_dict(),
        }

    def get_state(self) -> Dict[str, Any]:
        """Get the current workflow state for checkpointing."""
        return {
            "id": self._id,
            "status": self._status.value,
            "is_built": self._is_built,
            "is_initialized": self._is_initialized,
            "participants": {
                name: p.to_dict() for name, p in self._participants.items()
            },
            "context": self._context.to_dict() if self._context else None,
            "manager_state": self._manager.on_checkpoint_save() if self._manager else None,
            "config": {
                "enable_plan_review": self._enable_plan_review,
                "enable_stall_intervention": self._enable_stall_intervention,
                "max_plan_review_rounds": self._max_plan_review_rounds,
            },
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore workflow state from checkpoint."""
        self._status = MagenticStatus(state.get("status", "idle"))
        self._is_built = state.get("is_built", False)
        self._is_initialized = state.get("is_initialized", False)

        # Restore participants
        participants_data = state.get("participants", {})
        self._participants = {
            name: MagenticParticipant.from_dict(p)
            for name, p in participants_data.items()
        }

        # Restore context
        context_data = state.get("context")
        if context_data:
            self._context = MagenticContext.from_dict(context_data)

        # Restore manager state
        manager_state = state.get("manager_state")
        if manager_state and self._manager:
            self._manager.on_checkpoint_restore(manager_state)

        # Restore config
        config = state.get("config", {})
        self._enable_plan_review = config.get("enable_plan_review", False)
        self._enable_stall_intervention = config.get("enable_stall_intervention", False)
        self._max_plan_review_rounds = config.get("max_plan_review_rounds", 3)


# =============================================================================
# Factory Functions
# =============================================================================


def create_magentic_adapter(
    id: str,
    participants: Optional[Union[Dict[str, Any], List[MagenticParticipant]]] = None,
    max_round_count: int = 20,
    max_stall_count: int = 3,
    enable_plan_review: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> MagenticBuilderAdapter:
    """
    Create a MagenticBuilderAdapter with common configuration.

    Args:
        id: Workflow identifier
        participants: Optional participant definitions (dict or list)
        max_round_count: Maximum execution rounds
        max_stall_count: Maximum stalls before intervention
        enable_plan_review: Enable plan review
        config: Additional configuration

    Returns:
        Configured adapter instance
    """
    adapter = MagenticBuilderAdapter(id=id, config=config)

    if participants:
        if isinstance(participants, list):
            # Handle list of MagenticParticipant
            for participant in participants:
                if isinstance(participant, MagenticParticipant):
                    adapter._participants[participant.name] = participant
                elif isinstance(participant, dict):
                    p = MagenticParticipant.from_dict(participant)
                    adapter._participants[p.name] = p
        elif isinstance(participants, dict):
            # Handle dict of participants
            for name, participant in participants.items():
                if isinstance(participant, MagenticParticipant):
                    adapter._participants[name] = participant
                elif isinstance(participant, dict):
                    adapter._participants[name] = MagenticParticipant.from_dict(participant)
                else:
                    adapter._participants[name] = MagenticParticipant(
                        name=name,
                        description=str(participant),
                    )

    adapter.with_standard_manager(
        max_round_count=max_round_count,
        max_stall_count=max_stall_count,
    )

    if enable_plan_review:
        adapter.with_plan_review(enable=True)

    return adapter


def create_research_workflow(
    id: str = "research-workflow",
    max_rounds: int = 15,
) -> MagenticBuilderAdapter:
    """
    Create a pre-configured research workflow.

    Args:
        id: Workflow identifier
        max_rounds: Maximum execution rounds

    Returns:
        Research workflow adapter
    """
    adapter = MagenticBuilderAdapter(id=id)
    adapter.add_participant(MagenticParticipant(
        name="researcher",
        description="Research specialist for information gathering",
        capabilities=["search", "analyze", "summarize"],
    ))
    adapter.add_participant(MagenticParticipant(
        name="analyst",
        description="Data analyst for processing and computation",
        capabilities=["compute", "visualize", "statistics"],
    ))
    adapter.add_participant(MagenticParticipant(
        name="writer",
        description="Technical writer for documentation",
        capabilities=["write", "edit", "format"],
    ))
    adapter.with_standard_manager(max_round_count=max_rounds)
    adapter.with_plan_review(enable=True)
    return adapter


def create_coding_workflow(
    id: str = "coding-workflow",
    max_rounds: int = 20,
) -> MagenticBuilderAdapter:
    """
    Create a pre-configured coding workflow.

    Args:
        id: Workflow identifier
        max_rounds: Maximum execution rounds

    Returns:
        Coding workflow adapter
    """
    adapter = MagenticBuilderAdapter(id=id)
    adapter.add_participant(MagenticParticipant(
        name="architect",
        description="Software architect for design decisions",
        capabilities=["design", "architecture", "patterns"],
    ))
    adapter.add_participant(MagenticParticipant(
        name="coder",
        description="Developer for implementation",
        capabilities=["code", "implement", "debug"],
    ))
    adapter.add_participant(MagenticParticipant(
        name="reviewer",
        description="Code reviewer for quality assurance",
        capabilities=["review", "test", "validate"],
    ))
    adapter.with_standard_manager(max_round_count=max_rounds, max_stall_count=5)
    adapter.with_stall_intervention(enable=True)
    return adapter


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Enums
    "MagenticStatus",
    "HumanInterventionKind",
    "HumanInterventionDecision",
    "MessageRole",
    # Constants
    "MAGENTIC_MANAGER_NAME",
    # Data Classes - Messages
    "MagenticMessage",
    "MagenticParticipant",
    "MagenticContext",
    # Data Classes - Ledger
    "TaskLedger",
    "ProgressLedgerItem",
    "ProgressLedger",
    # Data Classes - Human Intervention
    "HumanInterventionRequest",
    "HumanInterventionReply",
    # Data Classes - Results
    "MagenticRound",
    "MagenticResult",
    # Manager Classes
    "MagenticManagerBase",
    "StandardMagenticManager",
    # Adapter
    "MagenticBuilderAdapter",
    # Factory Functions
    "create_magentic_adapter",
    "create_research_workflow",
    "create_coding_workflow",
]
