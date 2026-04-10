# Enterprise Services

> Remote managed settings (MDM) and team memory sync — enterprise deployment backbone for centralized governance and shared institutional knowledge.

**Source**: `remoteManagedSettings/` (5 files, ~640 LOC) + `teamMemorySync/` (5 files, ~1,257 LOC) — 10 files, ~1,897 LOC total
**Quality**: 9.4/10

---

## 1. Executive Summary

These two services represent Claude Code's **enterprise deployment backbone** -- the mechanisms by which organizations centrally govern CLI behavior (MDM settings) and share institutional knowledge across team members (team memory). Together they form a bidirectional enterprise control plane: settings flow **admin-to-client** while memory flows **peer-to-peer** through a server hub.

| Service | Direction | Auth Model | Sync Model | Conflict Strategy |
|---------|-----------|------------|------------|-------------------|
| remoteManagedSettings | Server -> Client (admin push) | API Key OR OAuth | Poll (1h) + ETag cache | Server wins; user veto on dangerous |
| teamMemorySync | Bidirectional (peer-to-peer via server) | OAuth only | fs.watch + debounced push | Local-wins-on-push; server-wins-on-pull |

---

## 2. Remote Managed Settings (`remoteManagedSettings/`)

### 2.1 Architecture Overview

```
Enterprise Admin Console
        |
        v  PUT settings
   Anthropic API  (/api/claude_code/settings)
        |
        v  GET (ETag: sha256:...)
   remoteManagedSettings/index.ts
        |
        +-- syncCache.ts -------- eligibility check (auth-touching)
        +-- syncCacheState.ts --- leaf state (no auth import, breaks SCC cycle)
        +-- securityCheck.tsx --- dangerous settings approval dialog
        +-- types.ts ----------- Zod schemas for API response
        |
        v
   ~/.claude/remote-settings.json  (persisted, mode 0o600)
        |
        v
   settings.ts (merged into policySettings layer)
```

### 2.2 MDM Settings Sync Protocol

**Initialization sequence:**
1. `initializeRemoteManagedSettingsLoadingPromise()` -- called early in `init.ts`, creates a Promise with 30s timeout deadlock guard
2. `loadRemoteManagedSettings()` -- cache-first: applies disk cache immediately to unblock waiters, then fetches async
3. On fetch success: applies security check, saves to disk, notifies `settingsChangeDetector`
4. Starts background polling (1-hour interval)

**Fetch flow (single attempt):**
1. Refresh OAuth token (`checkAndRefreshOAuthTokenIfNeeded`)
2. Build auth headers (API key via `x-api-key` OR OAuth via `Bearer` token)
3. GET endpoint with optional `If-None-Match` header for ETag caching
4. Handle responses: 200 (new settings), 304 (cache valid), 204/404 (no settings exist)
5. Validate response envelope via `RemoteManagedSettingsResponseSchema` (Zod)
6. Validate settings body via `SettingsSchema.safeParse()`

**Retry strategy:**
- Up to 5 retries with exponential backoff (`getRetryDelay`)
- Auth errors (401/403) skip retry entirely (`skipRetry: true`)
- Network/timeout errors are retryable

**Checksum computation:**
```
sha256(JSON.stringify(sortKeysDeep(settings)))
```
Must match Python server's `json.dumps(settings, sort_keys=True, separators=(",", ":"))` -- keys sorted recursively, no whitespace separators.

### 2.3 Eligibility Model

Determined in `syncCache.ts` via `isRemoteManagedSettingsEligible()`:

| User Type | Eligible | Rationale |
|-----------|----------|-----------|
| Console (API key) | Yes | All first-party API key holders |
| OAuth Enterprise/C4E | Yes | Enterprise subscription |
| OAuth Team | Yes | Team subscription |
| OAuth null subscriptionType | Yes | Externally-injected tokens (CCD, CCR, Agent SDK); let API decide |
| OAuth Individual/Free | No | Not enterprise-managed |
| Third-party provider | No | Custom LLM backends |
| Custom base URL | No | Non-Anthropic endpoints |
| Cowork (`local-agent`) | No | VM permission model differs; MDM doesn't apply |

**Performance optimization**: OAuth check runs before API key check to avoid spawning `security find-generic-password` subprocess (~20-50ms) for OAuth-only users.

### 2.4 Security Check (Dangerous Settings)

`securityCheck.tsx` implements a **blocking approval dialog** for dangerous settings changes:

1. Extract dangerous settings from new payload via `extractDangerousSettings()`
2. Compare against cached settings via `hasDangerousSettingsChanged()`
3. If changed AND interactive mode: render `ManagedSettingsSecurityDialog` (React/Ink)
4. User approves -> apply settings; User rejects -> `gracefulShutdownSync(1)` exits process

**Non-interactive bypass**: In non-interactive mode (CI/CD, Agent SDK), dangerous settings are silently accepted (`no_check_needed`).

### 2.5 Cache Architecture (SCC Cycle Break)

The cache is split across two files to break a circular dependency:

```
settings.ts --> syncCacheState.ts (leaf: no auth import)
     |                |
     |                v
     +------> syncCache.ts (has auth import for eligibility)
```

**syncCacheState.ts** (leaf module):
- Manages `sessionCache` (in-memory) and `eligible` (tri-state: undefined/true/false)
- On first disk read: calls `resetSettingsCache()` to flush any poisoned merged cache (gh-23085)

**syncCache.ts** (auth-touching):
- Owns `isRemoteManagedSettingsEligible()` with auth checks
- Re-exports leaf state functions

### 2.6 Sync Intervals & Lifecycle

| Phase | Interval | Mechanism |
|-------|----------|-----------|
| Initial load | Once at startup | `loadRemoteManagedSettings()` |
| Background poll | Every 60 minutes | `setInterval` with `.unref()` |
| Auth change | On login/logout | `refreshRemoteManagedSettings()` |
| Shutdown | Cleanup registered | `stopBackgroundPolling()` via `registerCleanup` |

### 2.7 Graceful Degradation (Fail-Open)

The entire service is designed to **fail open**:
- Fetch failure + cached settings -> use stale cache
- Fetch failure + no cache -> continue without remote settings (null)
- Background poll failure -> silently ignored
- Save failure -> ignored (refetch on next startup)
- Empty settings (204/404) -> delete cached file to avoid stale persistence

---

## 3. Team Memory Sync (`teamMemorySync/`)

### 3.1 Architecture Overview

```
Developer A (local)                    Anthropic API                     Developer B (local)
   .claude/memory/                /api/claude_code/team_memory             .claude/memory/
        |                                  |                                    |
   fs.watch (recursive)          repo-scoped KV store                    fs.watch (recursive)
        |                         (owner/repo keyed)                          |
        v                                  ^                                    v
   watcher.ts                              |                             watcher.ts
   (debounce 2s)                           |                             (debounce 2s)
        |                                  |                                    |
        +---> pushTeamMemory() ---PUT----->+<------PUT--- pushTeamMemory() <---+
        |                                  |                                    |
        +<--- pullTeamMemory() ---GET------+-------GET---> pullTeamMemory() ---+
                                           |
                                    secretScanner.ts
                                  (pre-upload filtering)
```

### 3.2 Sync Protocol Detail

**Pull semantics (server wins per-key):**
1. Check OAuth + GitHub repo availability
2. Fetch with ETag (`If-None-Match`) for 304 optimization
3. Validate response via `TeamMemoryDataSchema` (Zod)
4. Refresh `serverChecksums` map from `entryChecksums`
5. Write entries to disk via `writeRemoteEntriesToLocal()`:
   - Validate every path against team memory directory boundary (`PathTraversalError`)
   - Skip oversized entries (>250KB)
   - Skip entries where disk content already matches (preserves mtime, avoids watcher triggers)
   - Parallel writes with `Promise.all()`
6. Clear memory file caches if any files written

**Push semantics (local wins on conflict, delta upload):**
1. Read all local team memory files (`readLocalTeamMemory`)
2. Scan each file for secrets (`scanForSecrets`); skip files with detections
3. Compute SHA-256 hash for each local entry
4. Compute delta: only keys where `localHash !== serverChecksums[key]`
5. Split delta into PUT-sized batches (max 200KB per PUT body)
6. Upload each batch with `If-Match` ETag for optimistic locking
7. On 412 conflict: probe `?view=hashes`, refresh serverChecksums, recompute delta, retry (max 2 retries)

### 3.3 Conflict Resolution

```
Push attempt with If-Match ETag
         |
    412 Precondition Failed?
         |
    Yes: Probe GET ?view=hashes (lightweight, no bodies)
         |
         v
    Refresh serverChecksums from server
         |
         v
    Recompute delta (naturally drops keys matching teammate's push)
         |
         v
    Retry PUT with new ETag (max 2 conflict retries)
```

**Key design decisions:**
- **Local-wins-on-push**: User actively editing should not have work silently discarded
- **Server-wins-on-pull**: Pull overwrites local with server content
- **No merge**: Same key edited by both sides -> local version overwrites server on push
- **Deletions do NOT propagate**: Deleting a local file won't remove it from server; next pull restores it

### 3.4 Secret Scanning (34 rules)

Client-side secret scanner using curated rules from gitleaks:

| Category | Rules | Examples |
|----------|-------|---------|
| Cloud Providers | 4 | AWS access token, GCP API key, Azure AD client secret, DigitalOcean PAT |
| AI APIs | 4 | Anthropic API key, Anthropic admin key, OpenAI API key, HuggingFace token |
| Version Control | 7 | GitHub PAT/fine-grained/app/OAuth/refresh, GitLab PAT/deploy token |
| Communication | 4 | Slack bot/user/app tokens, Twilio API key |
| Dev Tooling | 6 | NPM, PyPI, Databricks, HashiCorp TF, Pulumi, Postman tokens |
| Observability | 4 | Grafana API key/cloud/service account, Sentry user/org tokens |
| Payment | 3 | Stripe access token, Shopify access/shared secret |
| Crypto | 1 | PEM private key blocks |
| SendGrid | 1 | SendGrid API token |

**Design patterns:**
- **Lazy compilation**: Regex patterns compiled on first `scanForSecrets()` call
- **Prefix obfuscation**: Anthropic key prefix assembled at runtime to avoid triggering excluded-strings checks
- **No secret logging**: Matched text is intentionally never returned; only rule IDs and labels
- **Team memory guard**: `checkTeamMemSecrets()` in FileWriteTool/FileEditTool prevents the AI model from writing secrets into team memory files

### 3.5 File Watcher (`watcher.ts`)

**Implementation**: `fs.watch({recursive: true})` on the team memory directory.

**Why not chokidar**: chokidar 4+ dropped fsevents; Bun's fallback uses kqueue with one fd per file. With 500+ files that's 500+ permanently-held fds.

| Platform | Mechanism | FD Usage |
|----------|-----------|----------|
| macOS | FSEvents via Bun | O(1) fds regardless of tree size |
| Linux | inotify | O(subdirs) -- one watch per directory |

**Debounce**: 2-second debounce after last change before pushing.

**Push suppression** (permanent failure protection):
- After a permanent failure (no_oauth, no_repo, 4xx except 409/429), `pushSuppressedReason` is set
- Prevents watcher events from driving infinite retry loops
- Cleared ONLY by file deletion (recovery action for too-many-entries)

### 3.6 Batch Upload Strategy

Delta entries are split into PUT-sized batches:
- `MAX_PUT_BODY_BYTES = 200,000` (200KB)
- `MAX_FILE_SIZE_BYTES = 250,000` (250KB per entry)
- **Greedy bin-packing** over sorted keys for deterministic batches
- Single entry exceeding 200KB goes into solo batch
- `serverChecksums` updated after each successful batch

### 3.7 Server-Enforced Limits

| Limit | Value | Source |
|-------|-------|--------|
| Per-entry size | 250KB | Client-side pre-filter |
| PUT body size | 200KB | Client-side batch split |
| Max entries | Per-org (GB-tunable) | Server-side; learned via structured 413 |
| Gateway body | ~256-512KB | API gateway |
| Sync timeout | 30s | `TEAM_MEMORY_SYNC_TIMEOUT_MS` |

---

## 4. Enterprise Deployment Model

### 4.1 Authentication Matrix

| Feature | API Key | OAuth (Enterprise/Team) | OAuth (Individual) | OAuth (null/injected) | 3rd-party |
|---------|---------|------------------------|--------------------|-----------------------|-----------|
| Remote Settings | Yes | Yes | No | Yes (API decides) | No |
| Team Memory Sync | No | Yes (needs profile scope) | No | No | No |

### 4.2 Deployment Topology

```
IT Admin Portal
    |
    v  Configure settings per org/team
Anthropic Console API
    |
    +--> Remote Settings Endpoint (/api/claude_code/settings)
    |         |
    |         v  Polled every 1h + on auth change
    |    Claude Code CLI (each developer machine)
    |         |
    |         v  Merged as policySettings layer
    |    Settings hierarchy: user < project < remote(policy)
    |
    +--> Team Memory Endpoint (/api/claude_code/team_memory)
              |
              v  Push on local edit (2s debounce), Pull on startup
         Claude Code CLI (bidirectional sync)
              |
              v  Scoped by GitHub repo (owner/repo)
         .claude/memory/ directory
```

### 4.3 Data Flow Guarantees

| Property | Remote Settings | Team Memory |
|----------|----------------|-------------|
| Consistency | Eventual (1h poll) | Eventual (2s debounce + watcher) |
| Durability | File-persisted (0o600) | File-persisted + server-backed |
| Availability | Fail-open (stale cache) | Fail-open (local files persist) |
| Confidentiality | HTTPS + auth headers | HTTPS + OAuth + secret scanning |
| Integrity | SHA-256 checksum + Zod validation | SHA-256 per-entry + ETag optimistic locking |

---

## 5. Error Handling Summary

### 5.1 Remote Settings Error Strategy

| Error | Behavior | Retry |
|-------|----------|-------|
| Auth failure (401/403) | Skip retry, fail open | No |
| Network error | Retry with backoff | Yes (5x) |
| Timeout (10s) | Retry with backoff | Yes (5x) |
| Invalid response format | Fail, use cache | No |
| Invalid settings structure | Fail, use cache | No |
| File save error | Ignore, refetch later | N/A |
| User rejects dangerous settings | Use cached or null | N/A |

### 5.2 Team Memory Error Strategy

| Error | Behavior | Retry |
|-------|----------|-------|
| No OAuth | Return immediately, suppress watcher | No |
| No GitHub repo | Return immediately, suppress watcher | No |
| Auth failure | Skip retry | No |
| 412 Conflict | Probe hashes, recompute delta | Yes (2x) |
| 413 Too Many Entries | Learn cap, fail push | No (next push truncates) |
| Network/timeout | Fail push, watcher retries on next edit | Watcher-driven |
| Permanent 4xx | Suppress push until file deletion | Suppressed |
| Secret detected in file | Skip file, push rest | N/A |
| Path traversal on pull | Skip entry, log warning | N/A |

---

## 6. Quality Assessment

### Strengths

1. **Robust cycle-breaking architecture**: The syncCache/syncCacheState split elegantly solves the settings SCC problem
2. **Comprehensive secret scanning**: 34 gitleaks-derived rules with lazy compilation and no-secret-logging discipline
3. **Intelligent conflict resolution**: Hash-based delta + lightweight probe avoids full re-download on 412
4. **Push suppression**: Prevents watcher-driven infinite retry loops
5. **Batch upload**: Greedy bin-packing with deterministic ordering handles gateway limits gracefully
6. **Fail-open design**: Both services degrade gracefully; enterprise settings never block CLI startup

### Potential Concerns

1. **Deletion gap**: File deletions never propagate in team memory (intentional but may confuse users)
2. **Local-wins-on-push data loss**: Concurrent edits to the same key -> last pusher's version wins
3. **Non-interactive dangerous settings bypass**: CI/CD silently accepts dangerous settings changes
4. **30s loading timeout**: If settings endpoint is slow, other systems may initialize with stale/missing policy
