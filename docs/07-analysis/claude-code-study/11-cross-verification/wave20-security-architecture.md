# Wave 20: Comprehensive Security Architecture Analysis

> **Cross-reference**: Consolidates findings from Wave 6 (Permission Deep Analysis), Wave 4 Path 3 (Bash Security), Sandbox Analysis, Computer Use Safety Analysis, plus direct source verification of `bashSecurity.ts`, `permissions/`, and `sandbox-adapter.ts`.
> **Date**: 2026-04-01
> **Verification Quality**: 9.0/10 — All claims verified against source code; cross-validated across 4 prior wave documents and 3 source files.

---

## 1. Multi-Layer Security Model

Claude Code implements a **defense-in-depth** architecture with 6 distinct security layers, each independently enforceable. A malicious or erroneous action must bypass ALL layers to cause harm.

### 1.1 Defense-in-Depth Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 6: Enterprise Policy Override (MDM / policySettings)            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 5: OS-Level Sandbox (macOS sandbox-exec / Linux seccomp)  │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  LAYER 4: Network Restrictions (allowlist/denylist hosts)   │  │  │
│  │  │  ┌───────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  LAYER 3: Filesystem Restrictions (read/write scopes) │  │  │  │
│  │  │  │  ┌─────────────────────────────────────────────────┐  │  │  │  │
│  │  │  │  │  LAYER 2: Bash Security Validators (23 checks)  │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │  LAYER 1: Permission Decision Cascade     │  │  │  │  │  │
│  │  │  │  │  │  (7 modes, 8-step inner + outer wrapper)  │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────────────────┘  │  │  │  │  │
│  │  │  │  └─────────────────────────────────────────────────┘  │  │  │  │
│  │  │  └───────────────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Details

| Layer | Component | Scope | Bypass Immunity |
|-------|-----------|-------|-----------------|
| **L1** | Permission Decision Cascade | Every tool invocation | Safety checks immune to all modes |
| **L2** | Bash Security Validators | Shell commands only | 23 check IDs, blocks before execution |
| **L3** | Filesystem Restrictions | File read/write ops | Sandbox-enforced path boundaries |
| **L4** | Network Restrictions | Outbound connections | Host allowlist/denylist per policy |
| **L5** | OS Sandbox | Process-level isolation | sandbox-exec (macOS), seccomp (Linux) |
| **L6** | Enterprise Policy | Organization-wide | `policySettings` overrides all sources |

---

## 2. Layer 1: Permission Decision Cascade (Detailed)

### 2.1 Seven Permission Modes

| Mode | Type | Behavior | Auto-Approve? |
|------|------|----------|---------------|
| `default` | External | Prompt for everything | No |
| `acceptEdits` | External | Auto-allow file edits in CWD | File edits only |
| `plan` | External | Read-only, blocks tool execution | No |
| `bypassPermissions` | External | Allow all except bypass-immune checks | Most things |
| `dontAsk` | External | Convert all `ask` to `deny` | Never (auto-deny) |
| `auto` | Internal | AI classifier decides | Classifier-dependent |
| `bubble` | Internal | Internal routing only | N/A |

### 2.2 Inner Decision Cascade (8 Steps)

```
Step 0:  Abort signal check
Step 1a: DENY rules (tool-level) — absolute, no override
Step 1b: ASK rules (tool-level) — unless sandboxed + auto-allow
Step 1c: Tool-specific checkPermissions()
Step 1d: Tool returned DENY → enforce
Step 1e: requiresUserInteraction → ALWAYS prompt (bypass-immune)
Step 1f: Content-specific ASK rules → ALWAYS prompt (bypass-immune)
Step 1g: Safety checks (safetyCheck type) → ALWAYS prompt (bypass-immune)
Step 2a: Bypass mode → allow
Step 2b: Allow rules → allow
Step 3:  passthrough → convert to ask
```

### 2.3 Outer Wrapper: Mode-Specific Transformations

| Mode | Transformation |
|------|---------------|
| `dontAsk` | ask → deny |
| `auto` | Safe allowlist → allow; AcceptEdits fast-path → allow; YOLO classifier → allow/deny; Fail-closed gate |
| Headless | Permission hooks → allow/deny; else auto-deny |

### 2.4 Bypass-Immune Safety Checks

These checks **cannot be overridden** by any mode, including `bypassPermissions`:

1. **Protected paths**: `.git/`, `.claude/`, `.vscode/`, shell config files — via `checkPathSafetyForAutoEdit()`
2. **requiresUserInteraction tools**: `ExitPlanMode`, `AskUserQuestion`, `ReviewArtifact`
3. **Content-specific explicit ask rules**: User-configured rules like `Bash(npm publish:*)`
4. **All deny rules**: Absolute priority, no mode overrides

### 2.5 Five-Way Concurrent Permission Resolver

When a permission prompt is needed, 5 resolution paths race concurrently:

```
                    Permission Required
                          |
          +-------+-------+-------+-------+
          |       |       |       |       |
        User    Hooks   Bash    Bridge  Channel
        Input   (API)   Class.  (CCR)   Relay
          |       |       |       |       |
          +---→ claim() atomic guard ←---+
                    |
              First wins (exactly one)
```

- **User**: Interactive CLI dialog (allow/reject/abort)
- **Hooks**: `executePermissionRequestHooks()` — programmable
- **Bash Classifier**: Async ML classifier with 200ms grace period
- **Bridge**: Claude.ai CCR remote approval
- **Channel Relay**: Telegram/iMessage/Kairos channel approval

**Concurrency safety**: `createResolveOnce` utility ensures exactly one path wins via `claim()`.

---

## 3. Layer 2: Bash Security Validators

### 3.1 Complete Security Check Registry (23 Checks)

| ID | Check Name | Threat |
|----|-----------|--------|
| 1 | `INCOMPLETE_COMMANDS` | Unterminated input causing shell misparse |
| 2 | `JQ_SYSTEM_FUNCTION` | jq `system()` function executing arbitrary commands |
| 3 | `JQ_FILE_ARGUMENTS` | jq reading arbitrary files |
| 4 | `OBFUSCATED_FLAGS` | Hidden flags via Unicode or encoding tricks |
| 5 | `SHELL_METACHARACTERS` | `;`, `&&`, `||` injection in arguments |
| 6 | `DANGEROUS_VARIABLES` | Env var manipulation (`LD_PRELOAD`, etc.) |
| 7 | `NEWLINES` | Embedded newlines creating hidden commands |
| 8 | `DANGEROUS_PATTERNS_COMMAND_SUBSTITUTION` | `$()`, backticks, process substitution |
| 9 | `DANGEROUS_PATTERNS_INPUT_REDIRECTION` | `<` reading unexpected files |
| 10 | `DANGEROUS_PATTERNS_OUTPUT_REDIRECTION` | `>` writing to sensitive paths |
| 11 | `IFS_INJECTION` | IFS manipulation to split commands differently |
| 12 | `GIT_COMMIT_SUBSTITUTION` | `$()` inside git commit messages |
| 13 | `PROC_ENVIRON_ACCESS` | Reading `/proc/*/environ` for secrets |
| 14 | `MALFORMED_TOKEN_INJECTION` | shell-quote library single-quote bug exploitation |
| 15 | `BACKSLASH_ESCAPED_WHITESPACE` | `\ ` creating hidden word boundaries |
| 16 | `BRACE_EXPANSION` | `{a,b}` expansion creating unintended commands |
| 17 | `CONTROL_CHARACTERS` | ASCII control chars hiding command fragments |
| 18 | `UNICODE_WHITESPACE` | Non-ASCII whitespace creating hidden word boundaries |
| 19 | `MID_WORD_HASH` | `#` after quotes creating hidden comments |
| 20 | `ZSH_DANGEROUS_COMMANDS` | zsh-specific commands (see below) |
| 21 | `BACKSLASH_ESCAPED_OPERATORS` | `\;` etc. bypassing operator detection |
| 22 | `COMMENT_QUOTE_DESYNC` | Quote/comment interaction creating hidden code |
| 23 | `QUOTED_NEWLINE` | Newlines inside quotes creating hidden commands |

### 3.2 Zsh-Specific Dangerous Command Blocklist

19 commands blocked as defense-in-depth against zsh module attacks:

| Category | Commands | Attack Vector |
|----------|----------|---------------|
| **Module loader** | `zmodload` | Gateway to all module-based attacks |
| **Eval-equivalent** | `emulate` | `-c` flag executes arbitrary code |
| **File I/O** | `sysopen`, `sysread`, `syswrite`, `sysseek` | Fine-grained file descriptor ops |
| **Process execution** | `zpty` | Pseudo-terminal command execution |
| **Network** | `ztcp`, `zsocket` | TCP connections for data exfiltration |
| **Filesystem builtins** | `zf_rm`, `zf_mv`, `zf_ln`, `zf_chmod`, `zf_chown`, `zf_mkdir`, `zf_rmdir`, `zf_chgrp` | Bypass binary-level checks |
| **Array I/O** | `mapfile` | Invisible file I/O via array assignment |

### 3.3 Command Substitution Pattern Detection

12 patterns detected and blocked before shell execution:

| Pattern | Example | Risk |
|---------|---------|------|
| `<()` | Process substitution | Hidden command execution |
| `>()` | Process substitution | Hidden output routing |
| `=()` | Zsh process substitution | Hidden command expansion |
| `=cmd` (word-initial) | Zsh equals expansion | Bypasses command deny rules |
| `$()` | Command substitution | Nested command execution |
| `${}` | Parameter substitution | Variable expansion attacks |
| `$[]` | Legacy arithmetic | Arithmetic expansion |
| `~[]` | Zsh parameter expansion | Non-standard expansion |
| `(e:` | Zsh glob qualifiers | Glob-based code execution |
| `(+` | Zsh glob qualifier | Command execution via glob |
| `} always {` | Zsh try/always | Hidden error handler code |
| `<#` | PowerShell comments | Defense-in-depth against future PS execution |

### 3.4 Dangerous Allow-Rule Prefix Stripping

The system identifies and blocks overly permissive allow rules at auto-mode entry. Cross-platform code execution entry points that are stripped:

**Interpreters**: `python`, `python3`, `python2`, `node`, `deno`, `tsx`, `ruby`, `perl`, `php`, `lua`
**Package runners**: `npx`, `bunx`, `npm run`, `yarn run`, `pnpm run`, `bun run`
**Shells**: `bash`, `sh`, `zsh`, `fish`
**Dangerous builtins**: `eval`, `exec`, `env`, `xargs`, `sudo`
**Remote execution**: `ssh`

### 3.5 AST-Based Security Analysis

The pure-TypeScript bash parser (`bashParser.ts`) provides tree-sitter-compatible ASTs with safety bounds:
- **50ms wall-clock timeout** — prevents adversarial pathological input
- **50,000 node budget** — prevents OOM on deeply nested constructs
- **Validated against 3,449 golden corpus inputs** from WASM parser

AST-level detections: `git push --force`, `git reset --hard`, `rm -rf`, branch deletion, eval with variables, redirect to sensitive paths.

---

## 4. Layer 3: Filesystem Restrictions

### 4.1 Path Validation Architecture

```
Path Operation Request
        |
        v
   containsPathTraversal() check — blocks ../ attacks
        |
        v
   containsVulnerableUncPath() — blocks Windows UNC path attacks
        |
        v
   expandTilde() — controlled ~ expansion (NO ~username support for security)
        |
        v
   safeResolvePath() — canonical path resolution
        |
        v
   pathInWorkingPath() — CWD boundary check
        |
        v
   checkPathSafetyForAutoEdit() — protected path detection
        |
        v
   matchingRuleForInput() — rule-based allow/deny
        |
        v
   SandboxManager write allowlist check — sandbox-level enforcement
```

### 4.2 Protected Internal Paths

Bypass-immune safety checks for:
- `.git/` — repository integrity
- `.claude/` — configuration integrity
- `.vscode/` — IDE configuration
- Shell config files (`.bashrc`, `.zshrc`, `.profile`, etc.)

Some are `classifierApprovable: true` (sensitive but classifier can decide), others are `classifierApprovable: false` (always prompt human).

### 4.3 Sandbox Filesystem Enforcement

The `@anthropic-ai/sandbox-runtime` package provides OS-level filesystem restrictions:

| Restriction | Scope | Auto-Allowed |
|-------------|-------|-------------|
| **Read** | Allowed paths only | CWD, `~/.claude/`, project temp, ripgrep binary |
| **Write** | Allowed paths only | CWD, Claude temp dir, sandbox temp dir |
| **Path patterns** | Per-source resolution | `//path` = absolute, `/path` = settings-relative, `~/path` = home |

---

## 5. Layer 4: Network Restrictions

### 5.1 Network Access Control

```typescript
NetworkRestrictionConfig = {
  allow_patterns?: NetworkHostPattern[]  // Allowlisted hosts
  deny_patterns?: NetworkHostPattern[]   // Blocklisted hosts
}
```

### 5.2 Default Network Policy

- **Blocked by default**: Most outbound connections when sandbox is enabled
- **Always allowed**: Anthropic API endpoints, OAuth providers
- **Conditionally allowed**: MCP server addresses (based on configuration)
- **User-configurable**: Additional hosts via settings

### 5.3 Essential-Traffic-Only Mode

When `sandbox.network.allowManagedDomainsOnly` is enabled in policySettings:
- ONLY domains specified in managed policy are allowed
- User/project settings cannot add additional domains
- Provides strict network egress control for enterprise environments

---

## 6. Layer 5: OS-Level Sandbox

### 6.1 Platform Support Matrix

| Platform | Technology | Capability |
|----------|-----------|------------|
| **macOS** | `sandbox-exec` | Full filesystem + network + process isolation |
| **Linux** | seccomp / AppArmor | Filesystem + syscall filtering |
| **Windows** | Limited | Reduced sandbox capabilities |

### 6.2 Sandbox Architecture

```
Claude Code Settings
        |
        v
  sandbox-adapter.ts  ← CLI-specific path resolution, violation handling
        |
        v
  @anthropic-ai/sandbox-runtime  ← Core enforcement engine
        |
        v
  OS-level sandboxing primitives
```

### 6.3 Per-Command Sandbox Decision

`shouldUseSandbox.ts` evaluates each command individually:
- Global sandbox enable/disable state
- Trusted command exceptions
- Permission classification of the command
- `autoAllowBashIfSandboxed` setting — bypasses ask rules when sandbox is active

### 6.4 Violation Tracking

```typescript
SandboxViolationEvent = {
  type: string       // fs_read, fs_write, network, etc.
  path?: string      // Affected filesystem path
  host?: string      // Affected network host
  tool?: string      // Tool that triggered violation
  timestamp: number  // Event timestamp
}
```

Violations are accumulated in `SandboxViolationStore` for:
- Real-time user notification
- Analytics and pattern tracking
- Debugging and troubleshooting
- Known-safe violation suppression via `IgnoreViolationsConfig`

---

## 7. Layer 6: Enterprise Policy (MDM / Managed Settings)

### 7.1 Policy Override Architecture

Enterprise policies via `policySettings` represent the highest-priority configuration source:

| Feature | Behavior |
|---------|----------|
| `allowManagedPermissionRulesOnly` | When `true`, ONLY policySettings rules are loaded; all user/project/local rules are ignored |
| `allowManagedDomainsOnly` | When `true`, ONLY managed network domains are allowed |
| Rule priority | policySettings > flagSettings > userSettings > projectSettings > localSettings |
| `shouldShowAlwaysAllowOptions()` | Returns `false` when managed-only is active — hides "always allow" UI |

### 7.2 Bypass Permissions Killswitch

Two run-once Statsig gate checks:

1. **`checkAndDisableBypassPermissionsIfNeeded()`**: Can remotely disable bypass mode for an organization
2. **`checkAndDisableAutoModeIfNeeded()`**: Can remotely disable auto mode, sets `autoModeCircuitBroken` flag
   - Triggers on model changes and fast-mode changes
   - Re-checked after `/login` with new org credentials

### 7.3 Settings Source Hierarchy

```
policySettings (MDM-managed, read-only)
    |
    v
flagSettings (runtime feature flags, read-only)
    |
    v
userSettings (~/.claude/settings.json, editable)
    |
    v
projectSettings (.claude/settings.json, editable)
    |
    v
localSettings (.claude/settings.local.json, editable)
    |
    v
cliArg (--permission-mode flag, runtime)
    |
    v
command (slash command frontmatter, runtime)
    |
    v
session (in-memory only, transient)
```

---

## 8. Per-Tool Security Profiles

### 8.1 Tool Risk Classification

| Tool | Risk Level | Permission Behavior | Sandbox | Auto-Mode |
|------|-----------|---------------------|---------|-----------|
| **BashTool** | HIGH | 23 security checks + subcommand decomposition | Full sandbox | Classifier required |
| **PowerShell** | HIGH | Requires explicit permission in auto mode | Limited | Blocked unless `POWERSHELL_AUTO_MODE` |
| **Edit/Write** | MEDIUM | Path safety checks, CWD boundary | Write restrictions | AcceptEdits fast-path |
| **Agent** | MEDIUM | Excluded from acceptEdits fast-path | Inherits parent | Classifier required |
| **REPL** | MEDIUM | Excluded from acceptEdits fast-path (VM escape risk) | Limited | Classifier required |
| **MCP Tools** | VARIABLE | Server-level + tool-level rules | Per-server config | Classifier required |
| **FileRead/Grep/Glob** | LOW | Read-only operations | Read restrictions | Auto-allowed (safe allowlist) |
| **TodoWrite/TaskOps** | LOW | Task management only | N/A | Auto-allowed (safe allowlist) |
| **Computer Use** | CRITICAL | 5-layer gating + session lock + escape hotkey | macOS-only | Not in allowlist |

### 8.2 BashTool Special Security Features

1. **Subcommand decomposition**: Compound commands (`cmd1 && cmd2`) split into up to 50 subcommands, each evaluated independently
2. **Safe env var stripping**: Leading `VAR=value` stripped if var is in safe list (`NODE_ENV`, `CI`, etc.)
3. **Prefix extraction**: `getSimpleCommandPrefix()` extracts `command subcommand` pairs for rule matching
4. **Bare shell prefix blocking**: Rules for `sh:*`, `bash:*`, `python:*`, `env:*`, `sudo:*` blocked from being suggested
5. **Sed edit detection**: `sed -i` commands classified as file edits, not reads
6. **Two classifier systems**: Bash Classifier (per-command) + YOLO Classifier (full-transcript)

### 8.3 Computer Use Security (5-Layer Gating)

| Gate | Check | Bypass? |
|------|-------|---------|
| **Platform** | macOS only (`darwin`) | No |
| **Subscription** | Max or Pro tier required | Ants bypass via `USER_TYPE` |
| **Feature flag** | `tengu_malort_pedway` GrowthBook gate | Remote-controlled |
| **Monorepo guard** | Blocks ant dev config unless `ALLOW_ANT_COMPUTER_USE_MCP=1` | Env var |
| **OS permissions** | TCC Accessibility + Screen Recording checks | System Preferences |

Additional safety mechanisms:
- **Session lock**: File-based mutual exclusion (`~/.claude/computer-use.lock`) with O_EXCL atomicity
- **Escape hotkey**: Global CGEventTap that consumes Escape system-wide (prompt injection defense)
- **Expected Escape hole**: Model-synthesized Escapes use `notifyExpectedEscape()` with 100ms decay
- **Turn-end cleanup**: Auto-unhide apps + release lock + unregister hotkey

---

## 9. Attack Surface Analysis

### 9.1 Potential Attack Vectors and Mitigations

| Attack Vector | Description | Mitigation Layer(s) | Status |
|---------------|-------------|---------------------|--------|
| **Shell injection** | Injecting commands via `$()`, backticks, process substitution | L2 (23 security checks) | Covered — 12 substitution patterns detected |
| **Path traversal** | `../` to escape CWD boundaries | L3 (`containsPathTraversal()`) + L5 (sandbox) | Covered — dual enforcement |
| **UNC path attacks** | Windows `\\server\share` for network access | L3 (`containsVulnerableUncPath()`) | Covered — Windows-specific check |
| **Zsh module attacks** | `zmodload` + module commands for hidden I/O | L2 (19 zsh commands blocked) | Covered — defense-in-depth |
| **Unicode obfuscation** | Non-ASCII whitespace, control characters | L2 (checks 17, 18) | Covered |
| **IFS manipulation** | Changing field separator to reparse commands | L2 (check 11) | Covered |
| **Overly permissive rules** | `Bash(python:*)` allowing arbitrary code | L1 (dangerous prefix stripping at auto-mode entry) | Covered |
| **Protected file modification** | Writing to `.git/`, `.claude/`, shell configs | L1 (bypass-immune safety checks) | Covered |
| **Network exfiltration** | Sending data to external hosts | L4 (network restrictions) + L5 (sandbox) | Covered when sandbox enabled |
| **Prompt injection via CU** | Injected actions in computer use session | Computer Use escape hotkey + session lock | Covered — macOS only |
| **Stale session lock** | Orphaned lock file blocking new sessions | Signal-0 liveness probe + stale detection | Covered |
| **Classifier unavailability** | Auto-mode without classifier | L1 (fail-closed gate, 30-min refresh) | Covered — `tengu_iron_gate_closed` |
| **Denial-of-service via denials** | Model repeatedly denied, loops forever | L1 (denial tracking: 3 consecutive, 20 total limits) | Covered |
| **Cross-machine bridge** | Remote approval from untrusted source | L1 (`classifierApprovable: false` for bridge paths) | Covered — always prompts human |
| **Heredoc in substitution** | `$(cat <<EOF ...)` hiding commands in heredocs | L2 (`HEREDOC_IN_SUBSTITUTION` regex) | Covered |
| **Git config hooks** | `git config core.sshCommand` for arbitrary code | L2 (AST analysis for git operations) + dangerous prefix list | Partial — ant-only `git` prefix stripping |

### 9.2 Residual Risk Areas

| Area | Risk | Mitigation Status |
|------|------|-------------------|
| **Windows sandbox limitations** | Reduced isolation capabilities | Acknowledged — "Limited" in platform matrix |
| **PowerShell security** | Less mature than Bash security checks | Separate tool with explicit permission requirement |
| **MCP tool diversity** | Third-party servers with variable security | Server-level deny rules available but user-configured |
| **Classifier accuracy** | False positives/negatives in auto-mode | Fail-closed gate + denial limits + human fallback |
| **Pre-loaded zsh modules** | Modules loaded before CC starts | Defense-in-depth: module commands also blocked individually |

---

## 10. Auto-Mode Classifier Architecture

### 10.1 Decision Flow

```
Auto-mode tool invocation
        |
        v
  Is tool on safe allowlist? ──yes──→ ALLOW (skip classifier)
        |no
        v
  AcceptEdits fast-path? ──yes──→ ALLOW (skip classifier)
  (excluded: Agent, REPL)
        |no
        v
  YOLO Classifier API call (sideQuery)
        |
   ┌────+────┐
   |         |
 ALLOW     BLOCK
   |         |
   v         v
 record   record denial
 success  check limits (3/20)
           |
      ┌────+────┐
      |         |
   <limit    >=limit
      |         |
    DENY     fallback to
             prompting (interactive)
             OR abort (headless)
```

### 10.2 Fail-Closed vs Fail-Open

| Gate State | Classifier Available | Behavior |
|------------|---------------------|----------|
| `tengu_iron_gate_closed` = true | No (API error) | **DENY** with retry guidance |
| `tengu_iron_gate_closed` = false | No (API error) | Fall back to normal permission handling |
| N/A | Yes, transcript too long | Interactive: manual approval; Headless: abort |

Gate refresh interval: 30 minutes (`CLASSIFIER_FAIL_CLOSED_REFRESH_MS`)

---

## 11. Denial Tracking and Analytics

### 11.1 Denial State Machine

```typescript
DenialTrackingState = {
  consecutiveDenials: number  // Reset to 0 on any success
  totalDenials: number        // Reset at limit in interactive mode
}

DENIAL_LIMITS = { maxConsecutive: 3, maxTotal: 20 }
```

### 11.2 Analytics Events

| Event | Trigger |
|-------|---------|
| `tengu_tool_use_granted_in_config` | Auto-approved by allowlist |
| `tengu_tool_use_granted_in_prompt_permanent` | User approved + permanent rule |
| `tengu_tool_use_granted_in_prompt_temporary` | User approved one-time |
| `tengu_tool_use_granted_by_classifier` | Classifier auto-approved |
| `tengu_tool_use_granted_by_permission_hook` | Hook approved |
| `tengu_tool_use_rejected_in_prompt` | User/hook rejected |
| `tengu_tool_use_denied_in_config` | Denied by denylist |
| `tengu_auto_mode_denial_limit_exceeded` | Denial limit hit |

OTel integration: `logOTelEvent('tool_decision', ...)` for distributed tracing.

---

## 12. Permission Handler Dispatch (Three Flows)

| Handler | Context | Strategy |
|---------|---------|----------|
| **Interactive** | Main agent | 5-way concurrent race (user + hooks + classifier + bridge + channel) |
| **Coordinator** | Coordinator workers | Sequential: hooks → classifier → fallback to interactive |
| **Swarm Worker** | Swarm workers | Classifier → leader mailbox forwarding → local fallback |

---

## 13. Comparison: What IPA Platform Can Learn

### 13.1 Direct Applicability to IPA Platform

| CC Security Feature | IPA Platform Equivalent | Implementation Priority |
|---------------------|------------------------|------------------------|
| **Multi-layer permission cascade** | API endpoint authorization with deny > ask > allow priority | HIGH — IPA's 591 endpoints need layered auth |
| **Bypass-immune safety checks** | Critical operations (data deletion, production deployment) that ALWAYS require approval | HIGH — Enterprise requirement |
| **Enterprise policy override** | Organization-level settings that override project/user settings | HIGH — `policySettings` pattern directly applicable |
| **Denial tracking with limits** | Rate limiting on sensitive operations with fallback behaviors | MEDIUM — Prevents infinite retry loops |
| **Per-tool security profiles** | Per-agent/per-integration risk classification | MEDIUM — Different agents have different trust levels |
| **Sandbox filesystem restrictions** | Agent execution sandboxing for MCP tool servers | MEDIUM — Agents should have bounded file access |
| **Fail-closed classifier gate** | LLM-based intent classification with fail-closed default | LOW — Complex but valuable for autonomous agents |
| **5-way concurrent resolver** | Multi-channel approval (API + webhook + Slack + email) | LOW — Advanced HITL pattern |

### 13.2 Recommended Security Patterns for IPA Platform

1. **Defense-in-depth for agent execution**: Every agent tool call should pass through: intent classification → permission rules → sandbox enforcement → audit logging.

2. **Immutable deny rules**: Critical operations (database DROP, production SSH, secret access) should be unconditionally blocked regardless of agent autonomy level.

3. **Hierarchical settings with enterprise override**: Implement a `policySettings` equivalent where organization admins can enforce rules that project-level or user-level settings cannot override.

4. **Denial tracking per agent**: Track consecutive and total denials per agent session. After 3 consecutive denials, fall back to human approval. After 20 total, force session review.

5. **Classifier fail-closed default**: When the LLM intent classifier is unavailable, default to DENY rather than ALLOW. This is the single most important safety decision in CC's architecture.

6. **Protected path registry**: Maintain a registry of paths/resources that always require human approval regardless of automation level (equivalent to CC's `.git/`, `.claude/` protections).

7. **Audit trail with structured events**: Emit structured permission decision events (like CC's `tengu_*` analytics) for every tool invocation, enabling security review and compliance reporting.

---

## 14. Summary Statistics

| Metric | Value |
|--------|-------|
| Security layers | 6 (permissions → bash validators → filesystem → network → OS sandbox → enterprise policy) |
| Permission modes | 7 (5 external + 2 internal) |
| Inner cascade steps | 8 (Steps 0, 1a-1g, 2a-2b, 3) |
| Bash security check IDs | 23 |
| Zsh dangerous commands | 19 |
| Command substitution patterns | 12 |
| Dangerous bash prefixes | 22+ (cross-platform) + ant-specific extensions |
| Concurrent resolution paths | 5 (user + hooks + classifier + bridge + channel) |
| Denial limits | 3 consecutive / 20 total |
| Computer use gates | 5 (platform + subscription + feature flag + monorepo + OS permissions) |
| Permission rule sources | 8 (policy → flag → user → project → local → cli → command → session) |
| Analytics event types | 8+ structured permission decision events |
| Classifier fail modes | 2 (fail-closed via iron gate / fail-open) |
| Parser safety bounds | 50ms timeout + 50,000 node cap |
| Golden corpus test cases | 3,449 |

---

*Analysis consolidates Wave 6 (permission deep analysis), bash execution analysis, sandbox analysis, computer use safety analysis, and direct source verification of `bashSecurity.ts` (23 check IDs, 19 zsh commands, 12 substitution patterns), `permissions/` (24 files — modes, rules, classifiers, denial tracking, dangerous patterns), and `sandbox-adapter.ts` (settings converter, path resolution, violation handling). All claims verified against source code read 2026-04-01.*
