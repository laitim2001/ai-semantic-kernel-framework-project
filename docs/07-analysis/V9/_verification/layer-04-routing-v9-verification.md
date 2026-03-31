# V9 Deep Semantic Verification: layer-04-routing.md

> 50-point functional description verification | 2026-03-31

---

## InputGateway Descriptions (15 pts)

### P1-P3: "3 handlers (ServiceNow, Prometheus, UserInput)" — Are there really only 3?

**Result**: ✅ Accurate

**Evidence**: `gateway.py` factory function `create_input_gateway()` creates exactly 3 handlers:
- `ServiceNowHandler` (line 338)
- `PrometheusHandler` (line 342)
- `UserInputHandler` (line 349, conditional on business_router)

There is also an `IncidentHandler` in `input/incident_handler.py` (Sprint 116 contracts layer), but this is in the legacy `input/` directory, NOT in `input_gateway/source_handlers/`. The doc correctly describes the 3 InputGateway handlers. The `IncidentHandler` is a separate contract-layer processor, not a source handler.

### P4-P6: Schema Validator Description

**Result**: ✅ Accurate

**Evidence**: `schema_validator.py` confirms:
- Validates against predefined schemas for ServiceNow and Prometheus (line 92-95)
- `SERVICENOW_SCHEMA` requires `["number", "category", "short_description"]` (line 124)
- `PROMETHEUS_SCHEMA` requires `["alerts"]` with nested `["alertname", "status"]` (line 150-166)
- `USER_INPUT_SCHEMA` has no required fields (line 193-195)
- Validation flow: required fields -> field types -> nested requirements -> unknown fields (lines 272-282)
- `strict_mode` vs warning-only behavior is accurate (lines 285-295)

### P7-P9: SQL Injection Fix Description

**Result**: ✅ Not present in doc (N/A)

The document does NOT mention SQL injection fixes. The `postgres_storage.py` file is in `agent_framework/memory/`, not in the orchestration module. No SQL injection claims found in this layer document. This is correct — it belongs to a different layer.

### P10-P12: Input Normalization Description

**Result**: ✅ Accurate

**Evidence**:
- `IncomingRequest.__post_init__()` normalizes headers to lowercase keys (models.py line 71)
- Factory methods: `from_user_input()`, `from_servicenow_webhook()`, `from_prometheus_webhook()` confirmed (models.py lines 82, 100, 126)
- `_identify_source()` correctly described with priority: (1) ServiceNow header, (2) Prometheus header, (3) generic `x-webhook-source` header, (4) explicit `source_type`, (5) default `"user"` (gateway.py lines 217-235). This matches doc's "Source Detection Priority" section exactly.

### P13-P15: Error Handling Description

**Result**: ✅ Accurate

**Evidence**: `gateway.py` `process()` method:
- No handler available -> returns UNKNOWN/HANDOFF/MEDIUM (lines 171-183)
- Exception catch -> returns UNKNOWN/HANDOFF/HIGH with error reasoning (lines 186-199)
- This matches the doc's architecture diagram showing UNKNOWN + HANDOFF as fallback.

---

## BusinessIntentRouter Descriptions (15 pts)

### P16-P18: Three-layer Cascade (Pattern -> Semantic -> LLM) — Is description complete? Additional fallback?

**Result**: ✅ Accurate

**Evidence**: `router.py` `route()` method (lines 180-271):
1. Validate input (empty check) -> `_build_empty_decision()`
2. Layer 1: `pattern_matcher.match()` -> if confidence >= pattern_threshold, return
3. Layer 2: `semantic_router.route()` -> if similarity >= semantic_threshold, return
4. Layer 3: `llm_classifier.classify()` -> if enabled, final fallback
5. If all fail: `_build_unknown_decision()` returns UNKNOWN with HANDOFF workflow

The doc correctly describes this as a 3-layer cascade. The "all fail" fallback to UNKNOWN/HANDOFF is also documented (line 408 of doc: "If all fail: return UNKNOWN with HANDOFF workflow").

### P19-P21: ClassificationCache Description — cache key format? TTL? invalidation?

**Result**: ✅ Accurate

**Evidence**: `cache.py`:
- Cache key: SHA256 hash of `user_input + include_completeness + simplified` (line 87-100)
- Default TTL: 1800 seconds (30 minutes) (line 25)
- Prefix: `"classify"` (line 56)
- No explicit invalidation mechanism (only TTL-based expiry via Redis)
- Doc says "ClassificationCache for LLM result caching" — accurate.

### P22-P24: Multi-task Description (intent + completeness in one call) — Is risk really separate?

**Result**: ✅ Accurate

**Evidence**: 
- `prompts.py` `CLASSIFICATION_PROMPT` (line 16-81): Tasks are 1) intent category, 2) sub-intent, 3) completeness assessment, 4) missing fields. **No risk assessment in prompt**.
- Doc correctly states: "Multi-task: intent + completeness in one call (risk handled separately by RiskAssessor)" (line 52 of doc).
- `RiskAssessor` is a completely separate class in `risk_assessor/assessor.py`.

### P25-P27: LLMClassifier Prompt Description — system prompt content mentioned?

**Result**: ✅ Accurate

**Evidence**: `prompts.py`:
- Prompt is in Traditional Chinese (line 16: "你是一個 IT 服務管理分類專家")
- Multi-task output: intent + sub_intent + completeness + missing_fields (lines 17-20)
- Required fields per category documented in prompt (lines 46-63) match doc's table exactly
- Doc correctly mentions "Traditional Chinese, simplified variant" — there is `SIMPLE_CLASSIFICATION_PROMPT` (line 88)

### P28-P30: Intent Category List — Is it complete?

**Result**: ✅ Accurate

**Evidence**: `models.py` `ITIntentCategory` enum (lines 19-34):
- INCIDENT, REQUEST, CHANGE, QUERY, UNKNOWN — exactly 5 values
- Doc lists these same 5 values in the table at line 388.

**Sub-intents in prompt** (prompts.py lines 28-41):
- incident: etl_failure, network_issue, performance_degradation, system_unavailable, database_error
- request: account_creation, permission_change, software_installation, password_reset, hardware_request
- change: release_deployment, configuration_update, database_change, infrastructure_upgrade
- query: status_inquiry, report_request, ticket_status, documentation_request, general_question

The `get_sub_intent_examples()` function (line 198-230) has additional sub-intents not in the prompt: `authentication_failure`, `vpn_access`, `security_patch`, `general_question`. These are helper examples, not part of the classification prompt. Doc does not enumerate all sub-intents exhaustively, which is acceptable.

---

## RiskAssessor Descriptions (10 pts)

### P31-P33: 7 Dimensions — Is each dimension's logic correct?

**Result**: ❌ Partial inaccuracy in dimension details

**Evidence**: `assessor.py` `_collect_factors()` (lines 304-411):

| # | Doc Description | Source Code | Match? |
|---|----------------|-------------|--------|
| 1 | intent_category, weight 0.2-0.8 | `_get_category_weight()`: INCIDENT=0.8, CHANGE=0.6, UNKNOWN=0.5, REQUEST=0.4, QUERY=0.2 | ✅ |
| 2 | sub_intent, weight 0.1-0.5 | `_get_sub_intent_weight()`: system_down=0.5, emergency_change=0.5, etl_failure=0.4, database_change=0.4, access_request=0.3, default=0.1 | ✅ |
| 3 | is_production, 0.3 (fixed) | weight=0.3, impact="increase" (line 357) | ✅ |
| 4 | is_weekend, 0.2 (fixed) | weight=0.2, impact="increase" (line 369) | ✅ |
| 5 | is_urgent, 0.15 (fixed) | weight=0.15, impact="increase" (line 381) | ✅ |
| 6 | affected_systems, 0.1*count cap 0.3 | `weight = min(0.1 * system_count, 0.3)`, impact="increase" if count > 2 (lines 388-398) | ❌ Doc says "impact increase if count > 0" but code says impact="increase" only if `system_count > 2`, otherwise "neutral" |
| 7 | low_confidence, 0.2*(1-confidence) | `confidence_penalty = 0.2 * (1 - routing_decision.confidence)` when confidence < 0.8 (lines 401-411) | ✅ |

**Issue**: Dimension 6 (affected_systems) — Doc line 582 says `Trigger: len(systems) > 0` but source code (line 397) sets `impact="increase" if system_count > 2 else "neutral"`. The factor is ADDED when count > 0, but its impact direction is "neutral" for 1-2 systems and "increase" only for > 2. The doc's description is slightly misleading — it implies all non-zero system counts trigger an "increase" impact.

### P34-P36: Risk Level Decision Logic (thresholds)

**Result**: ✅ Accurate

**Evidence**: 
- `RISK_LEVEL_SCORES`: LOW=0.25, MEDIUM=0.50, HIGH=0.75, CRITICAL=1.0 (lines 181-186)
- Score calculation: `base_score + factor_adjustment`, clamped 0.0-1.0 (lines 534-566)
- `factor_adjustment = sum(weight * 0.1 for "increase") - sum(weight * 0.1 for "decrease")` (lines 558-562)
- Doc's formula matches exactly.

However, the mermaid diagram threshold values (score < 0.3 = LOW, 0.3-0.7 = MEDIUM, >= 0.7 = HIGH) do NOT directly map to the code. The code uses **policy-based level** (not score thresholds) and then calculates a score FROM the level. The score ranges are emergent, not direct thresholds. This is a presentation choice in the diagram, not an error per se.

### P37-P40: HITL Integration Description

**Result**: ✅ Accurate

**Evidence**:
- `_requires_approval()`: returns True for HIGH and CRITICAL (line 578)
- `_get_approval_type()`: CRITICAL -> "multi", HIGH -> "single", else "none" (lines 580-594)
- Doc's table matches: CRITICAL=multi, HIGH=single, MEDIUM=none, LOW=none

---

## GuidedDialog Descriptions (10 pts)

### P41-P43: Dialog Engine's 5-phase Description

**Result**: ❌ Inaccuracy in phase count

**Evidence**: `engine.py` `DialogState` (line 49):
- `phase: str = "initial"` — default phase
- Actual phases used in code: `"initial"`, `"gathering"`, `"complete"`, `"handoff"`, `"clarification"`
- Doc line 543 says "5 phases: initial -> gathering -> complete -> handoff -> clarification" — this is **5 phases**, matching the code.

BUT the doc line 169 (file inventory) says: `5 phases: initial→gathering→complete→handoff→clarification. Direct deps: BusinessIntentRouter, ConversationContextManager (optional), QuestionGenerator (optional). RefinementRules is indirect via ContextManager`

Wait — let me re-verify. The `_handle_unknown_intent()` sets phase to `"clarification"` (line 356). The `_evaluate_and_respond()` sets phase to `"gathering"` (line 273). The `_complete_dialog()` sets phase to `"complete"` (line 304). The `_complete_with_handoff()` sets phase to `"handoff"` (line 334). Initial is the default.

**Result**: ✅ Actually accurate — 5 phases confirmed: initial, gathering, complete, handoff, clarification.

### P44-P46: CompletenessCheck Trigger Conditions

**Result**: ✅ Accurate

**Evidence**: `engine.py` `_evaluate_and_respond()` (lines 242-289):
- Checks `completeness.is_complete` (line 263)
- If complete -> `_complete_dialog()` (line 264)
- If not complete -> generate questions for missing fields (line 267)
- Unknown intent handled separately with clarification (line 260)

### P47-P50: Max Turns and Timeout Description

**Result**: ⚠️ Partial concern

**Evidence**:
- `GuidedDialogEngine.__init__()` has `max_turns: int = 5` (line 132) — doc says max 5 turns, ✅ correct for the engine
- `PersistentConversationContextManager` config has `max_turns: int = 10` (context_manager.py line 46) and `timeout_minutes: int = 30` (line 45)
- Doc section 4.3 says "Session TTL: 30 minutes (configurable)" ✅ and "Max turns: 10 (configurable)" ✅

The two different max_turns values (5 for engine, 10 for persistent context manager) are both documented correctly in their respective sections. The doc accurately distinguishes them.

**Result**: ✅ Accurate

---

## Response Parsing (additional verification)

### Doc says "3-level fallback" for LLM response parsing

**Result**: ❌ Should be 4-level fallback

**Evidence**: `classifier.py` `_parse_response()` (lines 194-239):
1. Strip markdown code block markers, then `json.loads(text)` (line 225)
2. Regex `\{[^{}]*\}` to find JSON in text (line 230)
3. `_extract_from_text()` — keyword-based extraction (line 239)

And the doc (line 513-517) says:
```
1. Direct JSON parse
2. Extract JSON from markdown code blocks
3. Regex extract `{...}` from text
4. Keyword-based text extraction (incident/request/change/query keywords)
```

Actually the doc lists 4 levels, but calls it "3-level fallback" at line 513. Let me re-read...

Doc line 513: `**Response Parsing** (3-level fallback):`  followed by items 1-4.

The code actually has steps: (a) strip markdown then JSON parse, (b) regex extract, (c) keyword extraction = 3 fallback levels after the primary attempt. But the doc lists 4 items. The first two (direct JSON + markdown strip) are really one step in code.

**Result**: ⚠️ Ambiguous — code has 3 code paths (strip+parse, regex, keyword), doc lists 4 items calling it "3-level". The numbering says 4 but label says 3. Minor inconsistency.

---

## Summary

| Section | Points | Result |
|---------|--------|--------|
| **P1-P3**: 3 handlers | 3/3 | ✅ Accurate |
| **P4-P6**: Schema Validator | 3/3 | ✅ Accurate |
| **P7-P9**: SQL Injection | 3/3 | ✅ N/A (not in doc) |
| **P10-P12**: Input normalization | 3/3 | ✅ Accurate |
| **P13-P15**: Error handling | 3/3 | ✅ Accurate |
| **P16-P18**: 3-layer cascade | 3/3 | ✅ Accurate |
| **P19-P21**: ClassificationCache | 3/3 | ✅ Accurate |
| **P22-P24**: Multi-task (intent+completeness) | 3/3 | ✅ Accurate |
| **P25-P27**: LLM prompt | 3/3 | ✅ Accurate |
| **P28-P30**: Intent categories | 3/3 | ✅ Accurate |
| **P31-P33**: 7 risk dimensions | 2/3 | ❌ affected_systems impact trigger: doc says "> 0", code says impact="increase" only if > 2 |
| **P34-P36**: Risk score calculation | 3/3 | ✅ Accurate |
| **P37-P40**: HITL integration | 4/4 | ✅ Accurate |
| **P41-P43**: Dialog 5 phases | 3/3 | ✅ Accurate |
| **P44-P46**: Completeness trigger | 3/3 | ✅ Accurate |
| **P47-P50**: Max turns + timeout | 4/4 | ✅ Accurate |
| **Bonus**: Response parsing label | — | ⚠️ "3-level" label but lists 4 items |

**Total: 47/50 pts accurate, 1 error found, 1 ambiguity noted**

---

## Corrections Needed

### Correction 1: RiskAssessor Dimension 6 — affected_systems impact trigger

**File**: `layer-04-routing.md`, line 582
**Current**: `| 6 | Affected Systems Count | affected_systems | 0.1 * count (cap 0.3) | len(systems) > 0 |`
**Issue**: Factor is added when count > 0, but `impact="increase"` only when `system_count > 2`, otherwise `impact="neutral"`
**Suggested fix**: Change trigger column to `len(systems) > 0 (impact=increase only if > 2)`

### Correction 2 (minor): Response Parsing label vs content mismatch

**File**: `layer-04-routing.md`, line 513
**Current**: `**Response Parsing** (3-level fallback):`  followed by 4 numbered items
**Issue**: Label says "3-level" but 4 items are listed. In code, steps 1+2 are really one code path (strip markdown then parse JSON).
**Suggested fix**: Either change to "(4-step fallback)" or merge items 1+2 into one item.
