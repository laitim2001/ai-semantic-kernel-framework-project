# IPA Platform V2 — Frontend

React 18 + TypeScript + Vite 5 + Zustand. Built around the **11+1
agent harness categories** (per `01-eleven-categories-spec.md`) — each
category gets a `features/` subdirectory.

> **Status**: Phase 49 Foundation, Sprint 49.1. Skeleton + placeholder
> pages only. Real implementation lands per phase roadmap below.

## Architecture

```
frontend/src/
├── main.tsx              ← Entry point
├── App.tsx               ← Router root
│
├── pages/                ← Top-level pages (one per route)
│   ├── chat-v2/          ← Phase 50.2 main flow
│   ├── governance/       ← Phase 53.3 HITL + audit UI
│   └── verification/     ← Phase 54.1 verification panel
│
├── components/
│   ├── ui/               ← Shadcn UI primitives (extract from V1 archive)
│   ├── layout/           ← Layout shells
│   └── shared/           ← Cross-page shared components
│
├── features/             ← One subdir per agent harness category that has UI
│   ├── orchestrator-loop/  ← Cat 1 — Loop event visualization
│   ├── tools/              ← Cat 2 — Tool call viewer
│   ├── memory/             ← Cat 3 — Memory inspector
│   ├── state-mgmt/         ← Cat 7 — State timeline
│   ├── guardrails/         ← Cat 9 — Governance UI
│   ├── verification/       ← Cat 10 — Verification panel
│   └── subagent/           ← Cat 11 — Subagent visualizer
│
├── hooks/                ← React hooks (e.g. useLoopEvents SSE)
├── api/                  ← Fetch clients (calls backend /api/v1/*)
├── stores/               ← Zustand stores
├── types/                ← TypeScript shared types
└── utils/                ← Pure helpers
```

## Quickstart

```bash
npm install            # install React 18 / Vite 5 / Zustand / RR
npm run dev            # Vite dev server on http://localhost:3007
npm run build          # production build → dist/
npm run lint           # ESLint
npm run typecheck      # tsc --noEmit
```

Dev server proxies `/api/*` to `http://localhost:8001` (V2 backend).
Port 3007 chosen to avoid collision with archived V1 frontend (was 3005).

## Sprint roadmap (frontend)

| Sprint | Adds |
|--------|------|
| 49.1 | Skeleton (this) |
| 50.2 | chat-v2 page wires `AgentLoop.run()` events via SSE |
| 53.3-53.4 | governance page (HITL approval modal + Teams integration) |
| 54.1 | verification page (verifier results + self-correction trace) |
| 55.1-55.5 | 5 business domain pages (patrol / correlation / rootcause / audit / incident) + DevUI 12-category dashboard |

## V2 vs V1

V1 frontend is archived to `archived/v1-phase1-48/frontend/`. V2 starts
from a clean skeleton — **do not import V1 directly** (V1 has its own
backend OpenAPI types that no longer exist). Instead, copy and adapt
patterns from the archive when building V2 components.
