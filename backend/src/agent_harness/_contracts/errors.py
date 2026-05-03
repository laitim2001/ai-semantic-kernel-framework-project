"""
File: backend/src/agent_harness/_contracts/errors.py
Purpose: Single-source ErrorContext + base exception hierarchy for Cat 8 Error Handling.
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 53.2 / Sprint 53.2

Description:
    Defines the data model that any range Cat 8 implementation (`error_handling/`)
    consumes when classifying or routing exceptions:
      - `ErrorContext` (frozen dataclass): metadata about the failure point
        (source category / tool / provider / attempt count / state version).
      - Base exceptions for the 4-class taxonomy mapping that the stub
        `_abc.py::ErrorClass` enum already declares (TRANSIENT /
        LLM_RECOVERABLE / HITL_RECOVERABLE / FATAL).

    These are pure-data declarations — no IO, no dependencies on
    LLM SDKs, no business logic. Cat 8 concrete implementations
    (`error_handling/policy.py`) and adapter integrations import
    from here.

Key Components:
    - ErrorContext: frozen dataclass passed alongside the raw exception
    - AuthenticationError / MissingDataError: USER_FIXABLE (HITL_RECOVERABLE)
      base classes. Concrete adapters subclass.
    - ToolExecutionError: LLM_RECOVERABLE base class for tool-side failures
      that should be returned to the LLM as an error ToolResult instead
      of bubbling up.

Owner: 01-eleven-categories-spec.md §Cat 8 + 17.md §1.1
Single-source: this file (do not redefine these elsewhere)
Created: 2026-05-03 (Sprint 53.2 Day 1)

Modification History (newest-first):
    - 2026-05-03: Initial creation (Sprint 53.2 Day 1) — supports Cat 8 production impl
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ErrorContext:
    """Metadata around a Cat 8 classification call.

    Passed by callers (Loop / Tool layer / Adapter) into ErrorPolicy.classify
    so policy decisions can be enriched with situational data without
    changing the exception object itself.

    Attributes:
        source_category: name of the calling range — e.g. "tools" /
            "adapters" / "verification" / "orchestrator_loop".
        tool_name: tool identifier when the exception came from tool
            execution (Cat 2). Optional.
        provider: LLM provider identifier when the exception came from
            an adapter call (e.g. "azure_openai", "anthropic"). Optional.
        attempt_num: 1-indexed attempt count within the current retry
            cycle. Used by RetryPolicy.should_retry caps.
        state_version: Cat 7 state version reference at the moment of
            failure. Optional — useful for audit / debug trace correlation.
        tenant_id: multi-tenant boundary attribute (per
            multi-tenant-data.md). Optional but should be populated by
            Loop integration in 53.2 Day 3-4.
    """

    source_category: str
    tool_name: str | None = None
    provider: str | None = None
    attempt_num: int = 1
    state_version: int | None = None
    tenant_id: UUID | None = None


# === Cat 8 base exception hierarchy ============================================
# Why: ErrorClass enum (in error_handling/_abc.py) classifies BY TYPE.
# Concrete adapters / tool authors raise these (or subclass) so the
# DefaultErrorPolicy registry can map them via MRO walk.


class AuthenticationError(Exception):
    """User-fixable: invalid credentials / expired token / permission denied.

    Maps to ErrorClass.HITL_RECOVERABLE. The user (or governance flow)
    must update credentials before the loop can resume.
    """


class MissingDataError(Exception):
    """User-fixable: required input / parameter not supplied.

    Maps to ErrorClass.HITL_RECOVERABLE. Surfaces an HITL prompt asking
    the user to provide the missing field.
    """


class ToolExecutionError(Exception):
    """LLM-recoverable: tool ran but returned an error / wrong shape.

    Maps to ErrorClass.LLM_RECOVERABLE. The Loop should NOT raise this
    upward — instead, materialise it as `ToolResult(is_error=True, ...)`
    and append to messages so the LLM can self-correct on the next turn
    (per Anthropic / LangGraph pattern, Cat 8 §LLM-recoverable in the
    spec).

    Subclass for finer-grained tool failure modes:
        class SalesforceConnectionError(ToolExecutionError): ...
    """
