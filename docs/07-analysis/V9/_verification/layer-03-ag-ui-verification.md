# Layer 03 AG-UI — V9 Deep Semantic Verification Results

**Verifier**: Claude Opus 4.6 | **Date**: 2026-03-31 | **Scope**: 50-point behavioral verification

---

## Summary

- **Total Points**: 50
- **PASS**: 47
- **FAIL (corrected)**: 2
- **INFO**: 1

---

## P1-P10: HybridEventBridge Event Conversion Behavior

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P1 | EVENT_MAPPING maps 11 HybridEventType to 11 AGUIEventType | PASS | `converters.py:115-127` — all 11 mappings verified |
| P2 | `from_result()` generates: TextMessageStart → Content(chunks) → ToolCall events → TextMessageEnd → RunFinished | PASS | `converters.py:532-669` — sequence confirmed |
| P3 | `content_to_chunks()` uses `range(0, len(content), self._chunk_size)` with default 100 | PASS | `converters.py:275-299`, chunk_size=100 at line 132 |
| P4 | HIGH_RISK_TOOLS = ["Write", "Edit", "MultiEdit", "Bash", "Task"] for HITL | PASS | `converters.py:576` — exact match |
| P5 | HITL_APPROVAL_REQUIRED CustomEvent emitted for high-risk tools | PASS | `converters.py:599-610` — event_name="HITL_APPROVAL_REQUIRED" |
| P6 | `from_result()` skips RUN_STARTED (already sent by bridge) | PASS | `converters.py:563-564` — commented out, confirmed |
| P7 | `from_result()` includes RUN_FINISHED at end for completeness | PASS | `converters.py:648-667` — appended as last event |
| P8 | Bridge `stream_events` yields events[:-1] then separate RUN_FINISHED | PASS | `bridge.py:869-887` — confirmed |
| P9 | `_format_sse()` delegates to `event.to_sse()` which returns `"data: {json}\n\n"` | PASS | `bridge.py:1007-1017`, `events/base.py:103-115` |
| P10 | Bridge uses `asyncio.Queue` + `execute_task()` + `heartbeat_task()` concurrently | PASS | `bridge.py:552-832` — confirmed pattern |

## P11-P20: MediatorEventBridge SSE Chunk Streaming

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P11 | MediatorEventBridge chunks content into 50-char pieces | PASS | `mediator_bridge.py:126` — `chunk_size = 50` |
| P12 | Uses `await asyncio.sleep(0.01)` between chunks | PASS | `mediator_bridge.py:133` |
| P13 | EVENT_MAP maps 13 mediator events to AG-UI types | PASS | `mediator_bridge.py:33-49` — all 13 entries verified |
| P14 | `pipeline.started` → `RUN_STARTED`, `pipeline.completed` → `RUN_FINISHED` | PASS | `mediator_bridge.py:34-35` |
| P15 | `routing.started/completed` → `STEP_STARTED/FINISHED` | PASS | `mediator_bridge.py:37-38` |
| P16 | `approval.pending` → `STATE_SNAPSHOT` | PASS | `mediator_bridge.py:42` |
| P17 | SSE format includes `id:`, `event:`, `data:` fields | PASS | `mediator_bridge.py:177` — `f"id: {event_id}\nevent: {event_type}\ndata: {sse_data}\n\n"` |
| P18 | Buffer for reconnection support via `self._buffer.buffer_event()` | PASS | `mediator_bridge.py:180-189` |
| P19 | Uses `asyncio.get_event_loop().create_task()` for buffering | PASS | `mediator_bridge.py:182` — confirmed deprecated usage |
| P20 | RUN_FINISHED includes `processing_time_ms` and `framework_used` | PASS | `mediator_bridge.py:140-146` |

## P21-P30: AG-UI Feature Behaviors

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P21 | SharedState DiffOperation has 6 values (ADD, REMOVE, REPLACE, MOVE, COPY, TEST) | **FAIL → CORRECTED** | `shared_state.py:38-44` — only 4 values: ADD, REMOVE, REPLACE, MOVE. **COPY and TEST do not exist.** |
| P22 | ConflictResolutionStrategy has 4 values (SERVER_WINS, CLIENT_WINS, MANUAL, MERGE) | **FAIL → CORRECTED** | `shared_state.py:47-54` — has 5 values: SERVER_WINS, CLIENT_WINS, LAST_WRITE_WINS, MERGE, MANUAL. **LAST_WRITE_WINS was missing.** |
| P23 | StateSyncManager default strategy is LAST_WRITE_WINS | PASS | `shared_state.py:174` — `conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS` |
| P24 | SharedStateHandler uses STATE_SNAPSHOT and STATE_DELTA events | PASS | `shared_state.py:29-33` — imports StateSnapshotEvent, StateDeltaEvent |
| P25 | ApprovalStorage uses in-memory dict with TTL default 5 min (300s) | PASS | `human_in_loop.py:64,178-189` — `DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300`, `self._requests: Dict` |
| P26 | ApprovalStorage TTL is checked on access via `is_expired()` | PASS | `human_in_loop.py:124-126` — `is_expired()` checks `datetime.utcnow() > self.expires_at` |
| P27 | HITLHandler imports RiskAssessmentEngine, RiskLevel from hybrid.risk | PASS | `human_in_loop.py:33-37` — exact imports confirmed |
| P28 | GenerativeUIHandler emits workflow_progress and mode_switch CustomEvents | PASS | Doc line 350 matches source header comments at `generative_ui.py` |
| P29 | AGUIApprovalDelegate delegates to UnifiedApprovalManager | PASS | Doc line 355-358, imports confirmed at `approval_delegate.py` |
| P30 | ThreadManager uses Write-Through pattern (cache + repo) | PASS | `thread/storage.py:12-14` — "Write-Through pattern: Cache + DB simultaneous writes" |

## P31-P40: AG-UI Frontend Hook Behaviors

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P31 | useAGUI manages SSE connection via EventSource ref | PASS | `useAGUI.ts:240` — `eventSourceRef = useRef<EventSource \| null>(null)` |
| P32 | useAGUI integrates useSharedState and useOptimisticState | PASS | `useAGUI.ts:250-259` — both hooks composed inline |
| P33 | handleSSEEvent parses JSON via parseSSEData and switches on eventType | PASS | `useAGUI.ts:558-564` — `parseSSEData(event.data)` then `switch (eventType)` |
| P34 | TEXT_MESSAGE_CONTENT updates message via delta concatenation | PASS | `useAGUI.ts:617-619` — `updateCurrentMessage(data.delta)` which appends to `content` |
| P35 | STATE_SNAPSHOT applies as full replace via sharedState.applyDiffs | PASS | `useAGUI.ts:646-654` — `operation: 'replace'` with snapshot |
| P36 | STATE_DELTA maps operations: set→replace, delete→remove | PASS | `useAGUI.ts:657-666` — mapping confirmed |
| P37 | CUSTOM event handles APPROVAL_REQUIRED by calling addPendingApproval | PASS | `useAGUI.ts:672-686` — `eventName === 'APPROVAL_REQUIRED'` |
| P38 | Heartbeat events update HeartbeatState (count, elapsedSeconds, message, status) | PASS | `useAGUI.ts:687-695` — all 4 fields mapped |
| P39 | Step progress events handled for S69-3 hierarchical display | PASS | `useAGUI.ts:696-699` — `eventName === 'step_progress'` |
| P40 | RUN_FINISHED clears heartbeat and step progress state | PASS | `useAGUI.ts:585-586` — `setHeartbeat(null)`, `setStepProgress({...})` |

## P41-P50: Known Issues Accuracy

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| P41 | Issue 1: HybridEventBridge waits for complete HybridResultV2 before emitting | PASS | `bridge.py:647-656` — `result = await self._orchestrator.execute(...)` then `converters.from_result(result)` |
| P42 | Issue 1: chunk_size=100 default | PASS | `bridge.py:106`, `converters.py:132` |
| P43 | Issue 2: MediatorEventBridge uses 50-char chunks with sleep(0.01) | PASS | `mediator_bridge.py:126-133` |
| P44 | Issue 3: ApprovalStorage is in-memory dict, TTL only checked on access | PASS | `human_in_loop.py:157-189` — no background cleanup task |
| P45 | Issue 4: InMemoryCache stores TTL but never enforces expiry | PASS | `thread/storage.py:341-378` — `_ttls` stored but never checked |
| P46 | Issue 5: Default _send_custom_event only logs via logger.debug | PASS | `bridge.py:246-258` — `logger.debug(f"Sending custom event: {event.event_name}")` |
| P47 | Issue 6: MediatorEventBridge uses deprecated asyncio.get_event_loop() | PASS | `mediator_bridge.py:182` |
| P48 | Issue 7: SSEEventBuffer falls back to in-memory dict, TTL only for Redis | PASS | `sse_buffer.py:43,59,68-69` — memory fallback has no TTL |
| P49 | Issue 7: max_size=100 enforced for both Redis and in-memory | PASS | `sse_buffer.py:57-58,68-69` — both paths trim to max_size |
| P50 | Issue 8: Dual bridge with different chunking (100 vs 50) | INFO | Accurate description. Both bridges confirmed with different chunk sizes. |

---

## Corrections Applied

### Fix 1: DiffOperation enum values (P21)
- **File**: `layer-03-ag-ui.md` line 365
- **Was**: `ADD`, `REMOVE`, `REPLACE`, `MOVE`, `COPY`, `TEST` (6 values)
- **Now**: `ADD`, `REMOVE`, `REPLACE`, `MOVE` (4 values)
- **Source**: `shared_state.py:38-44`

### Fix 2: ConflictResolutionStrategy enum values (P22)
- **File**: `layer-03-ag-ui.md` line 366
- **Was**: `SERVER_WINS`, `CLIENT_WINS`, `MANUAL`, `MERGE` (4 values)
- **Now**: `SERVER_WINS`, `CLIENT_WINS`, `LAST_WRITE_WINS`, `MERGE`, `MANUAL` (5 values)
- **Source**: `shared_state.py:47-54`
