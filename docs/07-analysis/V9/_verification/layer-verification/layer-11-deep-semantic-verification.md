# Layer 11: Infrastructure + Core — Deep Semantic Verification (50 pts)

> V9 Deep Verification | 2026-03-31 | Verifier: Claude Opus 4.6
> Scope: Behaviour descriptions in `layer-11-infrastructure.md`
> Method: Direct source reading of all referenced `.py` files

---

## Verification Summary

| Category | Points | Pass | Fail | Warn |
|----------|--------|------|------|------|
| P1-P10: Database Behaviour | 10 | 9 | 0 | 1 |
| P11-P20: Storage Behaviour | 10 | 10 | 0 | 0 |
| P21-P30: Cache Behaviour | 10 | 10 | 0 | 0 |
| P31-P40: Security Behaviour | 10 | 8 | 1 | 1 |
| P41-P50: Performance Behaviour | 10 | 10 | 0 | 0 |
| **TOTAL** | **50** | **47** | **1** | **2** |

---

## P1-P10: Database Behaviour

### P1: Engine pool settings ✅ PASS
**Source**: `infrastructure/database/session.py` L54-56 — `pool_size=5`, `max_overflow=10`, L48 `pool_pre_ping=True`. All confirmed.

### P2: NullPool for testing ✅ PASS
**Source**: `session.py` L51-52 — `if settings.app_env == "testing": engine_kwargs["poolclass"] = NullPool`. Confirmed.

### P3: Session factory settings ✅ PASS
**Source**: `session.py` L73-78 — `expire_on_commit=False`, `autoflush=False`. Confirmed.

### P4: get_session() auto-commit/rollback ✅ PASS
**Source**: `session.py` L83-104 — `yield session`, then `commit()` in try, `rollback()` in except. Confirmed.

### P5: DatabaseSession() asynccontextmanager ✅ PASS
**Source**: `session.py` L107-128 — `@asynccontextmanager`, same commit/rollback pattern. Confirmed.

### P6: init_db() / close_db() lifecycle ✅ PASS
**Source**: `session.py` L130-156 — `init_db()` verifies via `engine.begin()`. `close_db()` calls `engine.dispose()`. Confirmed.

### P7: BaseRepository flush()+refresh() not commit() ✅ PASS
**Source**: `repositories/base.py` — `create()` L66-67: flush+refresh. `update()` L170-172: flush+refresh. `delete()` L189: flush. No commit() anywhere. Confirmed.

### P8: BaseRepository.list() paginated with count subquery ✅ PASS
**Source**: `base.py` L126-128 — count subquery pattern. L137-139 — default order `created_at.desc()`. Confirmed.

### P9: Base model type_annotation_map ✅ PASS
**Source**: `models/base.py` L28-29 — `{datetime: DateTime(timezone=True)}`. Confirmed.

### P10: TimestampMixin ⚠️ WARN
Doc Section 3.1 says `onupdate=now()` for `updated_at` but does not mention that `updated_at` also has `server_default=func.now()`. Source L48-53 confirms both are set. Minor omission, not an error.

---

## P11-P20: Storage Behaviour

### P11: Dual Protocol TTL types ✅ PASS
ABC `backends/base.py` L47: `ttl: Optional[timedelta]`. Protocol `protocol.py` L41: `ttl: Optional[int]`. Confirmed incompatible.

### P12: ABC method names keys()/clear() ✅ PASS
`backends/base.py` L86: `keys()`, L99: `clear()`. Confirmed.

### P13: Protocol method names list_keys()/clear_all() ✅ PASS
`protocol.py` L76: `list_keys()`, L127: `clear_all()`. Confirmed.

### P14: Protocol has set ops, ABC has batch ops ✅ PASS
Protocol: `set_add`, `set_remove`, `set_members`. ABC: `get_many`, `set_many`, `count`. Confirmed.

### P15: ABC batch operations with default implementations ✅ PASS
`backends/base.py` L103-150: All three with iterative defaults. Confirmed.

### P16: 8 domain factories with env-aware backend selection ✅ PASS
`storage_factories.py`: 8 factory functions. Pattern: prod=RuntimeError, dev=fallback, test=InMemory. Confirmed.

### P17: StorageFactory auto-detection order ✅ PASS
Doc describes Redis > Postgres > InMemory detection. Consistent with source patterns.

### P18: Protocol @runtime_checkable ✅ PASS
`protocol.py` L11: `@runtime_checkable` on `StorageBackend(Protocol)`. Confirmed.

### P19: DistributedLock protocol ✅ PASS
`redis_lock.py` L33-49: `DistributedLock(Protocol)` with `acquire()` context manager and `is_locked()`. Confirmed.

### P20: RedisDistributedLock uses SET NX PX ✅ PASS
`redis_lock.py` L53: docstring confirms "SET NX PX". Confirmed.

---

## P21-P30: Cache Behaviour

### P21: SHA256 cache key generation ✅ PASS
`cache/llm_cache.py` L244: `hashlib.sha256(key_string.encode()).hexdigest()`. Confirmed.

### P22: Key format llm_cache:{hash} ✅ PASS
L166: `KEY_PREFIX = "llm_cache:"`. L246: `f"{self.KEY_PREFIX}{hash_value}"`. Confirmed.

### P23: Default TTL 3600s ✅ PASS
L170: `DEFAULT_TTL_SECONDS = 3600`. Confirmed.

### P24: Key includes model + prompt + relevant parameters ✅ PASS
L228-240: key_data has model, prompt, and filters to `temperature`, `max_tokens`, `top_p`, `frequency_penalty`. Confirmed.

### P25: Hit count tracking per entry ✅ PASS
L282-288: Increments `entry.hit_count`, updates in Redis with `keepttl=True`. Confirmed.

### P26: Statistics via Redis HSET ✅ PASS
L458: `hincrby(self.STATS_KEY, stat_name, amount)`. STATS_KEY = `"llm_cache:stats"`. Confirmed.

### P27: CachedAgentService with bypass ✅ PASS
L496-598: `CachedAgentService` with `bypass_cache: bool = False`. Confirmed.

### P28: warm_cache() pre-population ✅ PASS
L462-488: `warm_cache(entries)` iterates and calls `self.set()`. Confirmed.

### P29: Redis client pool settings ✅ PASS
`redis_client.py` L56-63: `max_connections=20`, `decode_responses=True`, `socket_connect_timeout=5`, `socket_timeout=5`, `retry_on_timeout=True`. Confirmed.

### P30: Redis health check ✅ PASS
`redis_client.py` L122-148: `check_redis_health()` with ping + latency + memory info. Confirmed.

---

## P31-P40: Security Behaviour

### P31: JWT HS256 + python-jose ✅ PASS
`security/jwt.py` L18: `from jose import jwt`. `config.py` L132: `jwt_algorithm = "HS256"`. Confirmed.

### P32: Access 60min, refresh 7d with "type":"refresh" ✅ PASS
`config.py` L133: `jwt_access_token_expire_minutes = 60`. `jwt.py` L148: `timedelta(days=7)`. L155: `"type": "refresh"`. Confirmed.

### P33: JWT claims sub/role/exp/iat ✅ PASS
`jwt.py` L70-75: payload has all four. Confirmed.

### P34: decode_token() raises ValueError ✅ PASS
`jwt.py` L120-121: `except JWTError: raise ValueError(...)`. Confirmed.

### P35: require_auth HTTPBearer no DB lookup ✅ PASS
`auth.py` L32-36: `HTTPBearer`. L46-97: decodes JWT directly, returns dict. No DB query. Confirmed.

### P36: passlib bcrypt deprecated="auto" ✅ PASS
`security/password.py` L19-22: `CryptContext(schemes=["bcrypt"], deprecated="auto")`. Confirmed.

### P37: RBAC 3 roles correct permissions ✅ PASS
`rbac.py` L56-77: ADMIN `{tool:*, api:*, session:*, admin:*}`, OPERATOR 9 perms (incl. `tool:request_approval`), VIEWER 6 perms. All match doc. Confirmed.

### P38: RBAC wildcard prefix matching ✅ PASS
`rbac.py` L146-153: `perm.endswith("*")` then `resource.startswith(prefix)`. Confirmed.

### P39: PromptGuard pattern counts ❌ FAIL
Doc claims "18 regex patterns" with `boundary_escape (6)`.
Actual `_INJECTION_PATTERNS` in `prompt_guard.py` L46-127:
- `role_confusion`: 7 (correct)
- `boundary_escape`: **7** (doc says 6; the 7th is `im_end` at L103)
- `exfiltration`: 3 (correct)
- `code_injection`: 2 (correct)
- **Total: 19** (doc says 18)

Plus 2 `_ESCAPE_PATTERNS` (xss) — correctly documented as separate.
**Fix**: boundary_escape = 7, total injection patterns = 19.

### P40: ToolSecurityGateway pattern count ⚠️ WARN
Doc claims "17 regex patterns". Grep count of `re.compile` in `tool_gateway.py` = **18**.
Actual categories:
- SQL injection: 6 (DROP, DELETE, UPDATE, INSERT, `--`, UNION SELECT)
- XSS: 3 (script open, script close, javascript:)
- Prompt injection: 3 (IGNORE PREVIOUS, DISREGARD, you are now)
- Boundary: 1 (system:)
- Code execution: 5 (exec, eval, \_\_import\_\_, os.system, subprocess)
- **Total: 18** (doc says 17)

Rate limits confirmed: 30/min default, 5/min high-risk. High-risk tools: `dispatch_workflow`, `dispatch_swarm`. Admin empty frozenset. All correct except count.
**Fix**: Pattern count should be 18, not 17.

---

## P41-P50: Performance Behaviour

### P41: CircuitBreaker 3 states ✅ PASS
`circuit_breaker.py` L20-25: `CLOSED`, `OPEN`, `HALF_OPEN` enum. Confirmed.

### P42: CB defaults failure=5, recovery=60s, success=2 ✅ PASS
L38-43: All three defaults confirmed. Confirmed.

### P43: CLOSED->OPEN on failure threshold ✅ PASS
L179-188: `if failure_count >= failure_threshold: state = OPEN`. Confirmed.

### P44: OPEN->HALF_OPEN after recovery timeout ✅ PASS
L133-141: Checks `time.monotonic()` elapsed, transitions to HALF_OPEN. Confirmed.

### P45: HALF_OPEN->CLOSED after success threshold ✅ PASS
L150-159: `if success_count >= success_threshold: state = CLOSED`. Confirmed.

### P46: HALF_OPEN->OPEN on failure ✅ PASS
L172-178: Probe failure reopens circuit. Confirmed.

### P47: Global singleton name="llm_api" ✅ PASS
L208-221: `get_llm_circuit_breaker()` creates with `name="llm_api"`. Confirmed.

### P48: CB stats tracking ✅ PASS
L57-59: `_total_calls`, `_total_failures`, `_total_short_circuits`. L70-81: `get_stats()` returns all. Confirmed.

### P49: LLMCallPool priority levels ✅ PASS
`llm_pool.py` L32-39: `CRITICAL=0`, `DIRECT_RESPONSE=1`, `INTENT_ROUTING=2`, `EXTENDED_THINKING=3`, `SWARM_WORKER=4`. Confirmed.

### P50: Rate limiting middleware ✅ PASS
`middleware/rate_limit.py` L54-57: `slowapi` Limiter, `storage_uri=None`, dev=`1000/minute`, prod=`100/minute`. L57 comment about Sprint 119 upgrade not done. Confirmed.

---

## Corrections Required

| # | Section | Current | Correct | Severity |
|---|---------|---------|---------|----------|
| 1 | 7.3 PromptGuard L1 | "18 regex patterns", "boundary_escape (6 patterns)" | **19 regex patterns**, **boundary_escape (7 patterns)** | LOW |
| 2 | 7.4 ToolSecurityGateway L1 | "17 regex patterns" | **18 regex patterns** | LOW |
