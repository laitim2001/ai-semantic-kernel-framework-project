# Sprint 57.134 Drive-Through Results — 2026-06-17

Real running uvicorn server (PID 55768, fresh restart with the new routes) + real admin auth
(dev-login dan@acme.com → roles `["user","admin","platform_admin"]`, httpOnly cookie via the
Vite `/api` proxy) + real PostgreSQL DB. Driven via the browser (`fetch(..., credentials:include)`).

## Leg 1 — preview on acme-prod (real data, NON-destructive, config-responsive)

tenant `09eb1b62-9fd3-439a-8229-1c923cc667e9` (acme-prod):

| step | result |
|------|--------|
| GET preview (retention 90) | 200 · cutoff `2026-03-19` · would_delete 0/0 |
| PATCH retention_days=1 | 200 · retention_days → 1 |
| GET preview (retention 1) | 200 · cutoff `2026-06-16` · would_delete 0/0 |
| PATCH retention_days=90 (reset) | 200 · retention_days → 90 |
| GET preview (after reset) | 200 · cutoff `2026-03-19` · would_delete 0/0 |

✅ Route registered on the running server (200, not 404); admin auth enforced; the canonical
`tenants.retention_days` is read + the cutoff tracks PATCH changes (90→1→90 ⇒
2026-03-19→2026-06-16→2026-03-19); NON-destructive (a count; reset left retention_days=90).
would_delete=0 is CORRECT — acme-prod has no transcript rows older than the cutoff (historical
sessions are 0-turn / pre-57.127 unpersisted; recent rows are today, < the 1-day cutoff).

## Leg 2 — apply on a throwaway tenant (DESTRUCTIVE primary path, real server)

Seeded throwaway tenant `66bf3b8d-...` (retention_days=30) via `seed_drivethrough.py`: an OLD
row (now-60d) + a RECENT row (now-5d) in messages + message_events.

| step | result |
|------|--------|
| GET preview | 200 · retention 30 · cutoff `2026-05-18` · would_delete **1/1** (the old row) |
| POST apply | 200 · **deleted_messages 1 · deleted_events 1** |
| GET preview (after) | 200 · would_delete **0/0** |
| DB verify | `REMAINING_MESSAGES=1` (the recent now-5d row SURVIVED the 30-day window) |
| cleanup | throwaway tenant deleted (CASCADE; WORM trigger toggled) |

✅ The destructive apply primary path driven end-to-end through the real server + real admin
auth + real DB: deleted exactly the old row (1/1), kept the recent (REMAINING_MESSAGES=1),
preview_after=0. Tenant-scoped + RLS-safe (the apply's `set_config` + explicit WHERE).

## Verdict

Drive-through PASS. Preview (non-destructive) + apply (destructive) both driven on the real
running server; deletion correctness (old deleted / recent kept / count match) + config
responsiveness + admin auth all confirmed. Complements the 7 integration tests (real PostgreSQL,
backdated rows, multi-tenant isolation, audit chain).
