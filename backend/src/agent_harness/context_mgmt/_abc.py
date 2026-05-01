"""
File: backend/src/agent_harness/context_mgmt/_abc.py
Purpose: Cat 4 ABCs that don't warrant a subpackage — ObservationMasker + JITRetrieval.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1

Description:
    Two single-file ABCs supporting the compaction pipeline:

      - ObservationMasker — preserves assistant tool_calls but redacts old
        role="tool" results (keep_recent recent turns intact). Decouples the
        masking algorithm from compactor implementations (Day 3.3 wires
        StructuralCompactor to inject a masker).

      - JITRetrieval — resolves a pointer (e.g. "db://memory_user/uuid?tenant_id=...")
        to its full content on demand. Lets prompts reference large blobs by
        pointer instead of inlining them, reducing baseline token cost
        (Day 3.4 ships PointerResolver with db:// scheme).

    The other 3 Cat 4 ABCs (Compactor / TokenCounter / PromptCacheManager)
    live in their own subpackages:
      - compactor/_abc.py
      - token_counter/_abc.py
      - cache_manager.py

    49.1 history: This file previously held Compactor + TokenCounter +
    PromptCacheManager stubs. Sprint 52.1 Day 1 restructured them into
    subpackages and replaced this file's contents with the two new ABCs.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1

Related:
    - compactor/_abc.py (Compactor — calls ObservationMasker)
    - 04-anti-patterns.md AP-7 (Context Rot — masking is a mitigation)
    - 10-server-side-philosophy.md §原則 1 (multi-tenant isolation — JIT requires tenant_id)

Created: 2026-04-29 (Sprint 49.1, original 3-ABC stub)
Last Modified: 2026-05-01 (Sprint 52.1 Day 1)

Modification History:
    - 2026-05-01: Restructure for Sprint 52.1 — move Compactor / TokenCounter /
      PromptCacheManager to subpackages; this file now hosts ObservationMasker
      + JITRetrieval ABCs (Sprint 52.1 Day 1)
    - 2026-04-29: Initial creation (Sprint 49.1) — Compactor + TokenCounter +
      PromptCacheManager stubs
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from agent_harness._contracts import Message


class ObservationMasker(ABC):
    """Masks old tool-result observations while preserving tool_call references.

    Concrete impl: DefaultObservationMasker (Day 3.1). Used by StructuralCompactor
    (Day 3.3 dependency injection) to keep "the agent called tool X" in context
    while replacing the heavy result blob with a tombstone.
    """

    @abstractmethod
    def mask_old_results(
        self,
        messages: list[Message],
        *,
        keep_recent: int = 5,
    ) -> list[Message]:
        """Return a new message list with old role="tool" messages redacted.

        Behaviour:
          - role="user" / "system" / "assistant" content: untouched
          - assistant tool_calls field: untouched (the *fact* of calling stays)
          - role="tool" messages older than keep_recent turns: replaced with
            a tombstone string like "[REDACTED: tool {name} result; ts={ts}; bytes={n}]"
        """
        ...


class JITRetrieval(ABC):
    """Resolves pointer references to their full content on demand.

    Concrete impl: PointerResolver (Day 3.4) supporting db:// scheme;
    other schemes (memory:// / tool:// / kb://) raise JITRetrievalNotSupportedError.

    Multi-tenant safety: every db:// pointer MUST include a tenant_id query
    parameter; resolve() MUST enforce the filter at the storage layer.
    """

    @abstractmethod
    async def resolve(
        self,
        pointer: str,
        *,
        tenant_id: UUID,
    ) -> str:
        """Resolve a pointer URI to its full string content.

        Supported schemes (Day 3.4):
          - db://<table>/<uuid>?tenant_id=<tid>   (Cat 3 memory tables)

        Unsupported schemes raise JITRetrievalNotSupportedError; caller must
        either use a supported pointer or inline the content directly.
        """
        ...
