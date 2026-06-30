# Sprint 57.151 Drive-Through Snapshot — cross-session conversation recall

**Date**: 2026-06-30 · real chat-v2 (localhost:3007) + real backend (127.0.0.1:8000, branch code, migrated DB head 0033) + real Azure gpt-5.2 (`real_llm` mode). Backend fresh no-reload PID 61048 (startup clean, `load_dotenv` → Azure creds; `CHAT_SESSION_SUMMARY` default ON). Frontend vite PID 31616 / claude-code UNTOUCHED.

## Leg 1 — Formation (session A, dan@acme.com / acme-prod)

**Sent** (1 distinctive multi-面向 turn): *"We are migrating the billing service from MongoDB to PostgreSQL. We decided to use a dual-write pattern during the cutover window. We are still blocked on the invoices table schema — specifically whether line items should be a JSONB column or their own separate table. Please just acknowledge…"*

- Session A = `bac53436-f2bb-416b-8e67-e183c4c28100` (tenant acme-prod `09eb1b62`, user dan `cf2b40a1`).
- Agent acknowledged correctly + Verification 0.99 (result RENDERED — AP-4 satisfied).
- **post-send BackgroundTask wrote `memory_session_summary`** (DB inspector via `claude_57151_db.py`):
  - `summary` = "The team is migrating the billing service from MongoDB to PostgreSQL and plans to use a dual-write pattern during the cutover window. The conversation ended with an open schema decision for the PostgreSQL `invoices` table, specifically how to model invoice line items."
  - `key_decisions` = `['Use a dual-write pattern during the MongoDB to PostgreSQL cutover']`
  - `unresolved_issues` = `['Decide whether invoice line items should be stored in a JSONB column or a separate normalized table']`
  - All 3 designed columns populated; tenant via session FK; updated_at set.

## Leg 2 — Recall (NEW session B, same user dan) — THE fix

**Sent**: *"What were we working on in my last session? Please remind me of the project and where we left off."*

- Session B = `760d5db9-8de6-4824-9886-2e05334a22bf` (NEW — no shared live transcript with A).
- **Agent recalled session A's content** (Verification 0.98): *"You were working on the **billing service migration from MongoDB to PostgreSQL**… **dual-write pattern** during the cutover… open item was a **PostgreSQL schema decision**: whether **invoice line items** should be stored in a **JSONB column** or modeled in a **separate relational table**."*
- This is EXACTLY session A's summary, surfaced in a separate new session via `MemoryRetrieval.recent_sessions()` inject (excluding B). Cross-session conversation recall WORKS.
- Bonus: also surfaced dan's "Project Aurora / Q3 go-live" user FACT (57.149 auto-extract) — the session-summary recall (this sprint) coexists cleanly with the user-fact recall. The billing/invoices content is specifically from this sprint's session-summary path.
- Screenshot: `dt151-recall-session-b.png`.

## Leg 3 — Per-user isolation (priya@acme.com, SAME tenant)

**Sent** (same question): *"What were we working on in my last session?…"*

- Agent: *"I don't have any stored notes or session memory showing what we were working on last time."* + only **priya's own** profile (compliance lead, SOC 2 Type II audit).
- **0 leak** of dan's billing/MongoDB/invoices/dual-write/Aurora content (`dan_content_leak: false`). `memory_search` hints `[]`.
- The recall JOIN filters by `sessions.user_id` (priya ≠ dan) → priya never sees dan's session summaries. Per-user isolation holds for BOTH session summaries AND user facts.
- Screenshot: `dt151-isolation-priya.png`.

## Verdict

**STRONG PASS** — all 3 legs on the real chat path. Formation (designed `memory_session_summary` filled with summary + decisions + open issues), recall (new session surfaces the prior session's arc, excluding current), and per-user isolation (0 cross-user leak) all verified end-to-end with real UI + real backend + real Azure. NOT a Potemkin: the result renders, the labels are real, the DB row is the real formed memory.

## Observed vs intended

| Intended | Observed |
|----------|----------|
| Session A's conversation → a `memory_session_summary` row | ✅ row with all 3 columns populated, correct content |
| New session B recalls A (excluding B) | ✅ agent recited billing/dual-write/invoices from A |
| Different user → no leak | ✅ priya got only her own SOC 2 profile, 0 dan content |
| Flag default ON, byte-identical when off | ✅ default ON drove the run; off-path unit-tested |
