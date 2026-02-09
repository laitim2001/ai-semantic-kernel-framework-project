# MCP — Model Context Protocol Integration

> Phase 9-10 | 43 Python files, ~3,900 LOC | Protocol infrastructure + 5 server implementations
>
> File count breakdown: core(4) + registry(2) + security(2) + servers(30: azure 10, filesystem 5, shell 5, ldap 5, ssh 5) + __init__.py files(5) = 43
> *(directory tree below shows key files only; `__init__.py` and `__main__.py` omitted for brevity)*

---

## Directory Structure

```
mcp/
├── __init__.py                     # Core exports (types, protocol, registry, security)
│
├── core/                           # Protocol infrastructure
│   ├── types.py                    # ToolInputType, ToolSchema, MCPRequest/Response (417 LOC)
│   ├── protocol.py                 # MCPProtocol — JSON-RPC 2.0 handler (360 LOC)
│   ├── transport.py                # BaseTransport, StdioTransport, InMemoryTransport (372 LOC)
│   └── client.py                   # MCPClient — Connect, discover, call tools (446 LOC)
│
├── registry/                       # Server management
│   ├── server_registry.py          # ServerRegistry — Registration + health monitoring (595 LOC)
│   └── config_loader.py            # ConfigLoader — JSON/YAML server configs (439 LOC)
│
├── security/                       # Permissions & audit
│   ├── permissions.py              # PermissionManager — RBAC (458 LOC)
│   └── audit.py                    # AuditLogger — Event logging + storage (679 LOC)
│
└── servers/                        # 5 MCP server implementations
    ├── azure/                      # Azure resource management
    │   ├── server.py               # AzureMCPServer (333 LOC)
    │   ├── client.py               # Azure SDK wrapper (355 LOC)
    │   └── tools/
    │       ├── vm.py               # VM management (737 LOC)
    │       ├── resource.py         # Resource group discovery (362 LOC)
    │       ├── storage.py          # Storage accounts (396 LOC)
    │       ├── monitor.py          # Metrics, alerts (408 LOC)
    │       └── network.py          # VNets, NSGs (457 LOC)
    │
    ├── filesystem/                 # Local file access
    │   ├── server.py               # FilesystemMCPServer (306 LOC)
    │   ├── tools.py                # File operations (481 LOC)
    │   └── sandbox.py              # Sandbox restrictions (529 LOC)
    │
    ├── shell/                      # Shell execution
    │   ├── server.py               # ShellMCPServer (307 LOC)
    │   ├── tools.py                # Shell commands (240 LOC)
    │   └── executor.py             # Command execution (443 LOC)
    │
    ├── ldap/                       # LDAP directory
    │   ├── server.py               # LDAPMCPServer (302 LOC)
    │   ├── client.py               # LDAP SDK wrapper (662 LOC)
    │   └── tools.py                # LDAP operations (494 LOC)
    │
    └── ssh/                        # Remote SSH
        ├── server.py               # SSHMCPServer (303 LOC)
        ├── client.py               # SSH client wrapper (606 LOC)
        └── tools.py                # Remote execution (593 LOC)
```

---

## Architecture

```
┌─────────────────────────────────┐
│         MCPClient               │
│  connect() → discover() → call()│
└──────────┬──────────────────────┘
           │ JSON-RPC 2.0
    ┌──────▼──────────────────────┐
    │      MCPProtocol            │
    │  initialize, tools/list,    │
    │  tools/call, ping           │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │     Transport Layer         │
    │  StdioTransport (local)     │
    │  InMemoryTransport (test)   │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │   ServerRegistry            │
    │  register, connect, health  │
    └──────┬──────────────────────┘
           │
    ┌──────▼──────────┬───────┬──────────┬───────┐
    │ Azure MCP       │ FS    │ Shell    │ LDAP  │ SSH   │
    │ (VM, Storage,   │       │          │       │       │
    │  Monitor, Net)  │       │          │       │       │
    └─────────────────┴───────┴──────────┴───────┴───────┘
```

---

## Server Capabilities

| Server | Tools | External SDK | Purpose |
|--------|-------|-------------|---------|
| **Azure** | 5 sets (VM, Resource, Storage, Monitor, Network) | azure-identity, azure-mgmt-* | Azure cloud resource management |
| **Filesystem** | Read, Write, List, Search | pathlib | Local file access with sandbox |
| **Shell** | Execute, Script | subprocess | Shell command execution |
| **LDAP** | Search, Bind, Modify | ldap3 | Active Directory integration |
| **SSH** | Connect, Execute, Transfer | paramiko | Remote server management |

---

## Security Model

```
Tool Call Request
    ↓
PermissionManager (RBAC)
    ├── PermissionLevel: NONE | READ | EXECUTE | ADMIN
    ├── PermissionPolicy (glob patterns for tools)
    └── Role-based access check
    ↓
AuditLogger
    ├── AuditEventType: TOOL_CALL, AUTH, ERROR, etc.
    ├── InMemoryAuditStorage (dev)
    └── FileAuditStorage (production)
    ↓
Server Execution
```

---

## Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| **ServerRegistry** | registry/server_registry.py | 595 | Central server management + health |
| **AuditLogger** | security/audit.py | 679 | Event logging with storage backends |
| **PermissionManager** | security/permissions.py | 458 | RBAC permission checks |
| **MCPClient** | core/client.py | 446 | Client interface for tool calls |
| **ConfigLoader** | registry/config_loader.py | 439 | JSON/YAML config loading |

---

**Last Updated**: 2026-02-09
