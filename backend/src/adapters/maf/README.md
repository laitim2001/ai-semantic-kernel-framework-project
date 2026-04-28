# adapters/maf — Microsoft Agent Framework Adapter (CONDITIONAL)

**Status**: Reserved placeholder at Sprint 49.1.
**Implementation**: **Sprint 54.2 IF needed** (only if subagent multi-agent
patterns prove valuable).

## Why this is here AND why it's conditional

V1 was built around MAF (Microsoft Agent Framework) — V1 had ConcurrentBuilder /
GroupChatBuilder / HandoffBuilder / MagenticBuilder integrations. V2
intentionally walks AWAY from MAF as a core architecture (per
03-rebirth-strategy.md): Sprint 49.1 archives the entire V1 MAF
integration to `archived/v1-phase1-48/backend/src/integrations/agent_framework/`.

**However**, MAF's multi-agent builders may still be useful as a
specific subagent backend. If Phase 54.2 (Subagent Orchestration)
discovers MAF builders solve a problem cleanly, this adapter wraps
them — exposing only `SubagentDispatcher` ABC, NOT MAF specifics.

## If activated (Sprint 54.2 conditional)

- `adapter.py` — wraps MAF builders behind `SubagentDispatcher` ABC
- Translates V2 `SubagentMode` enum → MAF builder pattern selection
- Strictly contained: NO MAF imports leak outside this directory

## If NOT activated

Delete this directory in a future sprint and update this README to
"Permanently archived — V2 does not use MAF".
