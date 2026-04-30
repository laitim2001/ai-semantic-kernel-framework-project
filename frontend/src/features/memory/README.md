# features/memory

UI components for **Category 3 (Memory)** — 5-layer memory inspector.

**Backend pair**: `backend/src/agent_harness/memory/`
**First impl**: Phase 51.2

## Components (planned)

- `<MemoryHintList>` — show `MemoryHint` returned from search (lazy-resolve)
- `<MemoryLayerInspector>` — debug view of all 5 layers (system / tenant / role / user / session)
- `<MemoryWriteForm>` — admin tool for direct write to specific layer
