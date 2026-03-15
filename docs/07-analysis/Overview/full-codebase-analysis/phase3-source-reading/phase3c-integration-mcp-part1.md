# Phase 3C: MCP Integration Analysis -- Part 1 (Core & Security)

> **Agent**: C8 | **Scope**: `backend/src/integrations/mcp/` -- core/, registry/, security/, root-level files
> **Date**: 2026-03-15 | **Feature Cross-Ref**: E2 (MCP Architecture), I4 (MCP Permission)

---

## 1. Module Overview

| Sub-module | Files | Key Classes | LOC (approx) |
|------------|-------|-------------|-------------|
| `core/` | 4 | MCPProtocol, MCPClient, StdioTransport, InMemoryTransport | ~1,600 |
| `registry/` | 2 | ServerRegistry, ConfigLoader | ~1,030 |
| `security/` | 5 | PermissionManager, MCPPermissionChecker, AuditLogger, RedisAuditStorage, CommandWhitelist | ~1,370 |
| Root-level | 4 | ServiceNowMCPServer, ServiceNowClient, ServiceNowConfig | ~780 |
| **Total** | **15** | | **~4,780** |

---

## 2. Core: Protocol & Transport (Feature E2)

### 2.1 Transport Layer (`core/transport.py`)

Two transport implementations exist:

| Transport | Purpose | Mechanism |
|-----------|---------|-----------|
| **StdioTransport** | Production use | Spawns subprocess via `asyncio.create_subprocess_exec`, communicates over stdin/stdout with JSON-RPC 2.0 newline-delimited messages |
| **InMemoryTransport** | Testing | Routes requests directly to an `MCPProtocol` instance in-process |

**Connection lifecycle (StdioTransport)**:
1. `start()` -- spawns subprocess, starts background `_read_loop` task
2. `send()` -- writes JSON to stdin, creates `asyncio.Future`, waits for response matched by request ID
3. `stop()` -- cancels reader, terminates subprocess (with kill fallback after 5s)

**Key design details**:
- Concurrent read/write protection via `asyncio.Lock`
- Pending request map (`Dict[Any, asyncio.Future]`) for correlating responses
- Default timeout: 30 seconds per request
- SSE and WebSocket transports are mentioned as future work but **not implemented**

### 2.2 Protocol Handler (`core/protocol.py`)

`MCPProtocol` implements a JSON-RPC 2.0 handler supporting:
- `initialize` / `initialized` -- handshake with protocol version `2024-11-05`
- `tools/list` -- returns all registered tool schemas
- `tools/call` -- executes tool handler with permission check
- `resources/list`, `resources/read` -- resource access (stub, data stored in dict)
- `prompts/list`, `prompts/get` -- prompt access (stub)
- `ping` -- health check

**Permission integration point** (Sprint 113): `_handle_tools_call()` checks `self._permission_checker` before executing the handler. If the checker is set and raises `PermissionError`, the call returns an error result. Default required level is `2` (EXECUTE) if not explicitly configured per tool.

### 2.3 Client (`core/client.py`)

`MCPClient` manages connections to multiple MCP servers:
- `connect(config)` -- creates transport, sends `initialize`, sends `initialized` notification, fetches `tools/list`
- `call_tool(server, tool, arguments)` -- sends `tools/call` via transport
- `list_tools()` -- returns cached tool schemas (with optional `refresh`)
- `close()` -- disconnects all servers

**ServerConfig** dataclass holds: name, command, args, env, transport type, timeout, cwd.

### 2.4 Types (`core/types.py`)

MCP-compliant types with JSON Schema serialization:
- `ToolInputType` (enum): string, number, integer, boolean, object, array, null
- `ToolParameter`, `ToolSchema` -- full `to_mcp_format()` / `from_mcp_format()` round-trip
- `ToolResult` -- success/error with MCP content format
- `MCPRequest` / `MCPResponse` -- JSON-RPC 2.0 messages
- `MCPErrorCode` -- standard error codes (-32700 through -32603)

---

## 3. Registry: Server Lifecycle (`registry/`)

### 3.1 ServerRegistry (`registry/server_registry.py`)

Central manager for MCP server lifecycle:

| Capability | Detail |
|-----------|--------|
| **Registration** | `register(server, connect=False)` -- stores `RegisteredServer` in dict |
| **Connection** | `connect(name)` -- delegates to `MCPClient.connect()`, caches tool list |
| **Bulk connect** | `connect_all()` -- parallel `asyncio.gather` for all enabled servers |
| **Reconnection** | `reconnect(name)` -- exponential backoff retry (default 3 retries, doubling delay from 1s) |
| **Tool catalog** | `get_all_tools()` -- aggregates tools from all CONNECTED servers |
| **Tool lookup** | `find_tool(name)` -- cross-server tool search |
| **Tool call** | `call_tool(tool_name)` -- auto-discovers which server has the tool |
| **Events** | `add_event_handler()` -- async callbacks on status changes |
| **Health** | `get_status_summary()` -- counts by status, total tools, per-server details |
| **Shutdown** | `shutdown()` -- cancels reconnect tasks, disconnects all, closes client |

**Server statuses**: REGISTERED, CONNECTING, CONNECTED, DISCONNECTING, DISCONNECTED, ERROR, RECONNECTING

### 3.2 ConfigLoader (`registry/config_loader.py`)

Loads server definitions from three sources:
1. **YAML files** -- `load_from_file()` with caching and `${ENV_VAR}` substitution
2. **Dictionaries** -- `load_from_dict()`
3. **Environment variables** -- `load_from_env()` with `MCP_SERVER_N_FIELD` naming convention

Includes `validate_config()` for pre-registration validation (duplicate names, invalid transport types, etc.).

---

## 4. Security Layer (Feature I4)

### 4.1 Permission Manager (`security/permissions.py`)

RBAC system with four levels:

| Level | Value | Access |
|-------|-------|--------|
| NONE | 0 | No access |
| READ | 1 | List/view tool schemas |
| EXECUTE | 2 | Execute tools |
| ADMIN | 3 | Full control |

**PermissionPolicy** supports:
- Glob patterns for servers and tools (e.g., `dev-*`, `read_*`)
- Explicit deny list with `server/tool` patterns (takes precedence)
- Priority-based evaluation (highest first)
- Dynamic conditions: time ranges, IP whitelists, custom evaluators

**Evaluation logic** (`check_permission`):
1. Collect policies from user-specific assignments, then role-based assignments
2. If no specific policies exist, fall back to ALL defined policies
3. Sort by priority descending
4. First matching policy wins (deny > allow)
5. Default deny (returns `self._default_level >= required_level`)

### 4.2 MCPPermissionChecker (`security/permission_checker.py`) -- Sprint 113

Wraps `PermissionManager` with two operational modes:

| Mode | Env Var `MCP_PERMISSION_MODE` | Behavior |
|------|-------------------------------|----------|
| `log` (default) | `log` | Logs WARNING on denial, **does not block** |
| `enforce` | `enforce` | Raises `PermissionError`, blocks execution |

**Default policy**: In `development` / `testing` environments (`APP_ENV`), a permissive `dev_default` policy grants `ADMIN` on all servers/tools. In production, no default policy is added -- explicit configuration required.

**Statistics**: Tracks `check_count` and `deny_count` with `get_stats()`.

### 4.3 CRITICAL FINDING: Is Permission Checking Actually Wired In?

**YES -- it is wired in and active.** The permission checker is integrated at two levels:

**Level 1 -- Protocol handler** (`core/protocol.py:304`):
```python
if self._permission_checker is not None:
    required_level = self._tool_permission_levels.get(tool_name, 2)
    self._permission_checker.check_tool_permission(...)
```
This runs inside `_handle_tools_call()` before the tool handler executes.

**Level 2 -- All 8 server implementations** wire it during initialization:
| Server | File | Line |
|--------|------|------|
| Azure | `servers/azure/server.py` | L90-91 |
| Filesystem | `servers/filesystem/server.py` | L76-77 |
| Shell | `servers/shell/server.py` | L77-78 |
| SSH | `servers/ssh/server.py` | L76-77 |
| LDAP | `servers/ldap/server.py` | L75-76 |
| n8n | `servers/n8n/server.py` | L102-103 |
| ADF | `servers/adf/server.py` | L98-99 |
| D365 | `servers/d365/server.py` | L103-104 |

Each server creates `MCPPermissionChecker()` and calls `self._protocol.set_permission_checker(checker, server_name)`.

**However**: The default mode is `log` (not `enforce`), and in dev/test environments the default policy grants ADMIN to everything. So while the checker **runs**, it effectively **allows all operations** unless `MCP_PERMISSION_MODE=enforce` is set and custom policies are configured. This is a **security gap for production deployments** if not explicitly configured.

**Notable exception**: The `ServiceNowMCPServer` (root-level) does NOT wire in the permission checker. It sets `_tool_permission_levels` on the protocol but never calls `set_permission_checker()`. Permission checking is therefore **not active** for ServiceNow tools.

### 4.4 Command Whitelist (`security/command_whitelist.py`) -- Sprint 113

Three-tier command security for Shell and SSH servers:

| Tier | Behavior |
|------|----------|
| **blocked** | Regex-matched dangerous commands (always rejected) |
| **allowed** | Whitelisted safe commands (always permitted) |
| **requires_approval** | Everything else (triggers HITL approval flow) |

**Blocked patterns** (26 regex patterns): `rm -rf /`, `format C:`, `dd if=...of=/dev`, `curl|sh`, fork bombs, `shutdown`, `reboot`, `Remove-Item -Recurse -Force`, `Stop-Computer`, etc.

**Default whitelist** (65+ commands): System info (`whoami`, `hostname`), file viewing (`ls`, `cat`, `grep`), network diagnostics (`ping`, `curl`), system status (`ps`, `df`), AD read-only (`dsquery`, `Get-ADUser`), text processing (`awk`, `sed`), PowerShell read-only cmdlets.

**Wiring**: The CommandWhitelist is instantiated in:
- `servers/shell/tools.py:66` -- `self._whitelist = CommandWhitelist()`
- `servers/ssh/tools.py:74` -- `self._whitelist = CommandWhitelist()`

**Extensibility**: Additional whitelisted commands via `MCP_ADDITIONAL_WHITELIST` env var (comma-separated) or constructor parameter.

### 4.5 Audit Logging (`security/audit.py`)

**AuditLogger** with pluggable storage backends:

| Storage Backend | Location | Use Case |
|----------------|----------|----------|
| `InMemoryAuditStorage` | `audit.py` | Dev/testing (deque, max 10K events) |
| `FileAuditStorage` | `audit.py` | Production (JSON Lines file) |
| `RedisAuditStorage` | `redis_audit.py` | Production (Redis Sorted Set, Sprint 120) |

**Event types**: SERVER_CONNECT, SERVER_DISCONNECT, SERVER_ERROR, TOOL_LIST, TOOL_EXECUTION, TOOL_ERROR, ACCESS_GRANTED, ACCESS_DENIED, CONFIG_CHANGE, POLICY_CHANGE, SYSTEM_START, SYSTEM_SHUTDOWN

**Features**:
- Argument sanitization (redacts password, secret, token, api_key, credential, auth, private_key)
- Real-time event handlers via `add_handler()`
- Querying with `AuditFilter` (by user, server, tool, type, status, time range, pagination)
- Cleanup (`delete_before` for retention management)
- `RedisAuditStorage` uses Sorted Set with Unix timestamp as score for efficient range queries; auto-trims to max_size

**Wiring gap**: `AuditLogger` is **NOT imported or instantiated** by any of the MCP server implementations. The audit infrastructure is fully built but not connected to actual tool execution. This means **no MCP tool calls are being audited** at runtime.

---

## 5. Root-Level: ServiceNow MCP Server (Sprint 117)

Three files at `mcp/` root level implement a ServiceNow integration:

| File | Purpose |
|------|---------|
| `servicenow_config.py` | Environment-based config (Basic Auth / OAuth2, retry settings) |
| `servicenow_client.py` | Async httpx client with retry/backoff for Table API |
| `servicenow_server.py` | MCP server with 6 tools registered via MCPProtocol |

**Tools**: `create_incident`, `update_incident`, `get_incident`, `create_ritm`, `get_ritm_status`, `add_attachment`

**Security note**: Permission levels are defined (`PERMISSION_LEVELS` dict) and set on the protocol via `set_tool_permission_level()`, but `set_permission_checker()` is **never called** -- so permission checks do not execute for ServiceNow tools.

---

## 6. Findings Summary

### Strengths

1. **Well-structured protocol layer**: Clean JSON-RPC 2.0 implementation with proper request/response correlation, timeouts, and error handling
2. **Flexible registry**: Parallel connect, auto-reconnect with exponential backoff, event-driven status monitoring
3. **Comprehensive RBAC model**: Glob patterns, deny lists, priority evaluation, dynamic conditions (time ranges, IP whitelists)
4. **Three-tier command security**: Blocked/allowed/requires-approval with HITL integration for unknown commands
5. **Multiple audit backends**: InMemory, File, and Redis storage with argument sanitization
6. **Config flexibility**: YAML, dict, and env-var sources with env substitution

### Issues & Gaps

| ID | Severity | Issue | Affected Feature |
|----|----------|-------|------------------|
| **MCP-S1** | HIGH | `AuditLogger` is not wired into any server -- tool executions are not audited | I4 |
| **MCP-S2** | MEDIUM | Default permission mode is `log` (not `enforce`) -- denials are logged but not blocked | I4 |
| **MCP-S3** | MEDIUM | `ServiceNowMCPServer` does not call `set_permission_checker()` -- permissions not checked | I4 |
| **MCP-S4** | LOW | SSE and WebSocket transports referenced in config validation but not implemented | E2 |
| **MCP-S5** | LOW | `PermissionManager.check_permission` falls back to ALL policies when no user/role policies match -- may produce unexpected grants in multi-policy setups | I4 |
| **MCP-S6** | INFO | `_check_time_range` defaults to allow if parsing fails -- should default to deny for security | I4 |
| **MCP-S7** | INFO | `FileAuditStorage` uses synchronous file I/O inside async lock -- could block event loop | I4 |

### Architecture Diagram

```
                     MCPClient
                        |
                   connect() / call_tool()
                        |
              +---------+----------+
              |                    |
        StdioTransport      InMemoryTransport
         (subprocess)           (testing)
              |                    |
              +--------+-----------+
                       |
                  MCPProtocol
                  (JSON-RPC 2.0)
                       |
            +----------+----------+
            |                     |
   tools/call handler      tools/list handler
            |
   MCPPermissionChecker  <-- set by each server.py
     (log | enforce)
            |
   PermissionManager
     (RBAC policies)
            |
   Tool Handler executes
            |
   [AuditLogger NOT connected]   <-- gap
            |
   CommandWhitelist              <-- Shell/SSH only
     (blocked/allowed/approval)
```

---

## 7. Recommendations

1. **Wire AuditLogger into MCPProtocol** -- Add `set_audit_logger()` to protocol and log every `tools/call` execution (success and failure) with duration
2. **Default to enforce mode in production** -- When `APP_ENV=production`, auto-set `MCP_PERMISSION_MODE=enforce`
3. **Add permission checker to ServiceNowMCPServer** -- Mirror the pattern used by all other servers
4. **Fail-closed on time range parsing errors** -- Change `_check_time_range` default from allow to deny
5. **Use async file I/O for FileAuditStorage** -- Use `aiofiles` to avoid blocking the event loop

---

*Analysis performed by Agent C8. All files read in full.*
