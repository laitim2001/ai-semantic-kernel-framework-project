"""
File: tests/unit/agent_harness/prompt_builder/conftest.py
Purpose: Shared fixtures + helpers for Cat 5 PromptBuilder unit tests.
Category: Tests / Cat 5
Scope: Sprint 52.2 Day 1.8
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agent_harness._contracts import (
    CachePolicy,
    DurableState,
    LoopState,
    MemoryHint,
    Message,
    StateVersion,
    ToolAnnotations,
    ToolSpec,
    TransientState,
)
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter.generic_approx import (
    GenericApproxCounter,
)
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder


def msg(role: str, content: str, **metadata: object) -> Message:
    return Message(role=role, content=content, metadata=dict(metadata))


def make_state(
    *,
    messages: list[Message] | None = None,
    tenant_id=None,
    user_id=None,
) -> LoopState:
    return LoopState(
        transient=TransientState(messages=messages or []),
        durable=DurableState(
            session_id=uuid4(),
            tenant_id=tenant_id or uuid4(),
            user_id=user_id,
        ),
        version=StateVersion(
            version=1,
            parent_version=None,
            created_at=datetime.now(timezone.utc),
            created_by_category="orchestrator_loop",
        ),
    )


def make_memory_hint(
    *,
    layer: str = "user",
    time_scale: str = "long_term",
    summary: str = "test hint",
    confidence: float = 0.9,
    relevance_score: float = 0.8,
) -> MemoryHint:
    return MemoryHint(
        hint_id=uuid4(),
        layer=layer,  # type: ignore[arg-type]
        time_scale=time_scale,  # type: ignore[arg-type]
        summary=summary,
        confidence=confidence,
        relevance_score=relevance_score,
        full_content_pointer=f"db://memory/{uuid4()}",
        timestamp=datetime.now(timezone.utc),
    )


def make_tool_spec(name: str = "search") -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"{name} tool",
        input_schema={"type": "object", "properties": {}},
        annotations=ToolAnnotations(
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
        version="1.0",
    )


@pytest.fixture
def builder() -> DefaultPromptBuilder:
    return DefaultPromptBuilder(
        memory_retrieval=MemoryRetrieval(layers={}),
        cache_manager=InMemoryCacheManager(),
        token_counter=GenericApproxCounter(),
    )


@pytest.fixture
def cache_policy_default() -> CachePolicy:
    return CachePolicy()
