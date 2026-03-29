# Layer 08: MCP Tool Layer

## Identity

- Files: 75 | LOC: 20,847
- Directory: `backend/src/integrations/mcp/`
- Phase introduced: 9 (Sprint 31) | Phase last modified: 42 (Sprint 129)

---

## File Inventory

| File | LOC | Purpose | Key Classes / Functions |
|------|-----|---------|------------------------|
| `__init__.py` | 99 | Package root re-export (types, protocol, registry, security) | — |
| **core/** | | | |
| `core/__init__.py` | 35 | Core module exports | — |
| `core/types.py` | 418 | MCP type definitions (JSON Schema based) | `ToolInputType`, `ToolParameter`, `ToolSchema`, `ToolResult`, `MCPRequest`, `MCPResponse`, `MCPErrorCode` |
| `core/protocol.py` | 408 | JSON-RPC 2.0 protocol handler with tool registration | `MCPProtocol`, `ToolHandler` |
| `core/transport.py` | 373 | Transport layer (subprocess stdio + in-memory) | `BaseTransport`, `StdioTransport`, `InMemoryTransport`, `TransportError`, `ConnectionError`, `TimeoutError` |
| `core/client.py` | 447 | Client interface for connecting/calling MCP servers | `MCPClient`, `ServerConfig` |
| **registry/** | | | |
| `registry/__init__.py` | ~10 | Registry module exports | — |
| `registry/server_registry.py` | 596 | Central server lifecycle, health, auto-reconnect | `ServerRegistry`, `ServerStatus`, `RegisteredServer`, `EventHandler` |
| `registry/config_loader.py` | 440 | YAML/JSON/ENV config loading with `${VAR}` substitution | `ConfigLoader`, `ServerDefinition`, `ConfigError` |
| **security/** | | | |
| `security/__init__.py` | 44 | Security module exports | — |
| `security/permissions.py` | 459 | RBAC permission management with glob patterns | `PermissionLevel`, `Permission`, `PermissionPolicy`, `PermissionManager`, `ConditionEvaluator` |
| `security/permission_checker.py` | 183 | Sprint 113 runtime enforcement (log/enforce modes) | `MCPPermissionChecker` |
| `security/command_whitelist.py` | 225 | Three-tier command validation (allowed/blocked/approval) | `CommandWhitelist` |
| `security/audit.py` | 685 | Audit logging with pluggable storage backends | `AuditEventType`, `AuditEvent`, `AuditFilter`, `AuditStorage`, `InMemoryAuditStorage`, `FileAuditStorage`, `AuditLogger` |
| `security/redis_audit.py` | 226 | Sprint 120 Redis Sorted Set audit backend | `RedisAuditStorage` |
| **servers/azure/** | | | |
| `servers/azure/__init__.py` | ~10 | Azure server exports | — |
| `servers/azure/__main__.py` | ~15 | CLI entry point | — |
| `servers/azure/server.py` | 344 | Azure MCP Server orchestrator (stdio mode) | `AzureMCPServer`, `create_server_from_env`, `main` |
| `servers/azure/client.py` | 356 | Azure SDK lazy client manager (5 SDK clients) | `AzureConfig`, `AzureClientManager`, `AzureClient` |
| `servers/azure/tools/__init__.py` | ~10 | Tools sub-package exports | — |
| `servers/azure/tools/vm.py` | 738 | VM lifecycle: list, get, status, start, stop, restart, run_command | `VMTools`, `VMInfo` |
| `servers/azure/tools/resource.py` | 363 | Resource group CRUD + resource search | `ResourceTools` |
| `servers/azure/tools/monitor.py` | 409 | Metrics, alerts, metric definitions | `MonitorTools` |
| `servers/azure/tools/network.py` | 458 | VNets, NSGs, NSG rules, public IPs | `NetworkTools` |
| `servers/azure/tools/storage.py` | 397 | Storage accounts, containers, usage | `StorageTools` |
| **servers/filesystem/** | | | |
| `servers/filesystem/__init__.py` | ~10 | Filesystem server exports | — |
| `servers/filesystem/__main__.py` | ~15 | CLI entry point | — |
| `servers/filesystem/server.py` | 306 | Filesystem MCP Server | `FilesystemMCPServer` |
| `servers/filesystem/tools.py` | 482 | File read/write/list/search/info/delete | `FilesystemTools` |
| `servers/filesystem/sandbox.py` | 529 | Path restriction, allowed_paths, denied_extensions | `FilesystemSandbox` |
| **servers/shell/** | | | |
| `servers/shell/__init__.py` | ~10 | Shell server exports | — |
| `servers/shell/__main__.py` | ~15 | CLI entry point | — |
| `servers/shell/server.py` | 307 | Shell MCP Server | `ShellMCPServer` |
| `servers/shell/tools.py` | 290 | run_command, run_script, get_shell_info + whitelist integration | `ShellTools` |
| `servers/shell/executor.py` | 443 | Subprocess execution with timeout, output truncation | `ShellExecutor` |
| **servers/ldap/** | | | |
| `servers/ldap/__init__.py` | ~10 | LDAP server exports | — |
| `servers/ldap/__main__.py` | ~15 | CLI entry point | — |
| `servers/ldap/server.py` | 302 | LDAP MCP Server | `LDAPMCPServer` |
| `servers/ldap/client.py` | 662 | ldap3 SDK wrapper with connection pooling | `LDAPConnectionManager`, `LDAPConfig` |
| `servers/ldap/tools.py` | 495 | connect, search, search_users, search_groups, get_entry, disconnect | `LDAPTools` |
| `servers/ldap/ad_config.py` | ~120 | Active Directory-specific configuration | `ADConfig` |
| `servers/ldap/ad_operations.py` | ~200 | AD-specific operations (user/group/OU) | `ADOperations` |
| **servers/ssh/** | | | |
| `servers/ssh/__init__.py` | ~10 | SSH server exports | — |
| `servers/ssh/__main__.py` | ~15 | CLI entry point | — |
| `servers/ssh/server.py` | 303 | SSH MCP Server | `SSHMCPServer` |
| `servers/ssh/client.py` | 606 | paramiko wrapper with connection caching | `SSHConnectionManager`, `SSHConfig` |
| `servers/ssh/tools.py` | 620 | connect, execute, upload, download, list_directory, disconnect + whitelist | `SSHTools` |
| **servicenow (top-level)** | | | |
| `servicenow_config.py` | ~120 | ServiceNow instance configuration | `ServiceNowConfig` |
| `servicenow_client.py` | ~350 | REST API client (httpx-based) | `ServiceNowClient`, `ServiceNowError`, `ServiceNowAuthError`, `ServiceNowNotFoundError`, `ServiceNowPermissionError`, `ServiceNowServerError` |
| `servicenow_server.py` | 624 | 6-tool MCP Server for Incident + RITM + Attachment | `ServiceNowMCPServer` |
| **servers/n8n/** | | | |
| `servers/n8n/__init__.py` | ~10 | n8n server exports | — |
| `servers/n8n/__main__.py` | ~15 | CLI entry point | — |
| `servers/n8n/client.py` | ~280 | n8n REST API client | `N8nApiClient`, `N8nApiError`, `N8nNotFoundError` |
| `servers/n8n/server.py` | ~200 | n8n MCP Server (registers WorkflowTools + ExecutionTools) | `N8nMCPServer` |
| `servers/n8n/tools/__init__.py` | ~10 | Tools sub-package exports | — |
| `servers/n8n/tools/workflow.py` | 300 | list_workflows, get_workflow, activate_workflow | `WorkflowTools` |
| `servers/n8n/tools/execution.py` | 311 | execute_workflow, get_execution, list_executions | `ExecutionTools` |
| **servers/adf/** | | | |
| `servers/adf/__init__.py` | ~10 | ADF server exports | — |
| `servers/adf/__main__.py` | ~15 | CLI entry point | — |
| `servers/adf/client.py` | ~300 | Azure Data Factory REST API client | `AdfApiClient`, `AdfApiError`, `AdfNotFoundError` |
| `servers/adf/server.py` | ~200 | ADF MCP Server (registers PipelineTools + MonitoringTools) | `AdfMCPServer` |
| `servers/adf/tools/__init__.py` | ~10 | Tools sub-package exports | — |
| `servers/adf/tools/pipeline.py` | 377 | list_pipelines, get_pipeline, run_pipeline, cancel_pipeline_run | `PipelineTools` |
| `servers/adf/tools/monitoring.py` | 355 | get_pipeline_run, list_pipeline_runs, list_datasets, list_triggers | `MonitoringTools` |
| **servers/d365/** | | | |
| `servers/d365/__init__.py` | ~10 | D365 server exports | — |
| `servers/d365/__main__.py` | ~15 | CLI entry point | — |
| `servers/d365/auth.py` | ~150 | OAuth2 client_credentials flow for D365 | `D365AuthProvider` |
| `servers/d365/client.py` | ~350 | OData v4 Web API client | `D365ApiClient`, `D365NotFoundError`, `D365ValidationError`, `ODataQueryBuilder` |
| `servers/d365/server.py` | ~200 | D365 MCP Server (registers QueryTools + CrudTools) | `D365MCPServer` |
| `servers/d365/tools/__init__.py` | ~10 | Tools sub-package exports | — |
| `servers/d365/tools/query.py` | 405 | query_entities, get_record, list_entity_types, get_entity_metadata | `QueryTools` |
| `servers/d365/tools/crud.py` | 298 | create_record, update_record | `CrudTools` |
| `servers/__init__.py` | ~5 | Servers package marker | — |

**Total: 75 files, 20,847 LOC**

---

## Internal Architecture

```
backend/src/integrations/mcp/
│
├── core/                           [Protocol Infrastructure]
│   ├── types.py                    ToolInputType (7 JSON Schema types), ToolSchema, ToolResult,
│   │                               MCPRequest/Response (JSON-RPC 2.0), MCPErrorCode (5 codes)
│   ├── protocol.py                 MCPProtocol — 8 method handlers:
│   │                               initialize, initialized, tools/list, tools/call,
│   │                               resources/list, resources/read, prompts/list, prompts/get, ping
│   │                               + permission_checker integration (Sprint 113)
│   ├── transport.py                BaseTransport ABC → StdioTransport (subprocess stdio I/O)
│   │                                                 → InMemoryTransport (direct protocol routing)
│   │                               StdioTransport: async read_loop, write_lock, pending_requests map
│   └── client.py                   MCPClient: multi-server connection manager
│                                   connect → initialize handshake → tools/list → cache schemas
│                                   call_tool → JSON-RPC → parse result → ToolResult
│
├── registry/                       [Server Management]
│   ├── server_registry.py          ServerRegistry — lifecycle: register → connect → monitor → shutdown
│   │                               ServerStatus: REGISTERED → CONNECTING → CONNECTED → DISCONNECTED → ERROR
│   │                               Features: connect_all (parallel), auto-reconnect (exponential backoff),
│   │                               event handlers, tool catalog aggregation, status summary
│   └── config_loader.py            ConfigLoader — 3 config sources:
│                                   1. YAML file (servers: [...])
│                                   2. Environment variables (MCP_SERVER_1_NAME=xxx)
│                                   3. Programmatic dict
│                                   + ${ENV_VAR} substitution, validation, caching
│
├── security/                       [Permissions + Audit + Command Control]
│   ├── permissions.py              4-level RBAC: NONE(0) → READ(1) → EXECUTE(2) → ADMIN(3)
│   │                               PermissionPolicy: glob patterns for server/tool matching
│   │                               PermissionManager: priority-sorted evaluation, deny_list precedence,
│   │                               dynamic conditions (time_range, ip_whitelist, custom evaluators)
│   ├── permission_checker.py       MCPPermissionChecker (Sprint 113):
│   │                               MCP_PERMISSION_MODE: "log" (default) | "enforce"
│   │                               dev/testing → auto-ADMIN policy; production → explicit only
│   ├── command_whitelist.py        CommandWhitelist (Sprint 113):
│   │                               65 DEFAULT_WHITELIST commands, 26 BLOCKED_PATTERNS (regex)
│   │                               Three-tier: "allowed" → "blocked" → "requires_approval"
│   │                               + MCP_ADDITIONAL_WHITELIST env override
│   ├── audit.py                    AuditLogger + 3 storage backends:
│   │                               InMemoryAuditStorage (deque, max 10K)
│   │                               FileAuditStorage (JSON Lines)
│   │                               13 AuditEventType variants (server, tool, access, admin, system)
│   │                               AuditEvent: auto-sanitize sensitive keys (password, token, secret...)
│   └── redis_audit.py              RedisAuditStorage (Sprint 120):
│                                   Sorted Set (mcp:audit:events), score=timestamp
│                                   Auto-trim to max_size, efficient time-range queries
│
├── servicenow_config.py            ServiceNow instance config (from_env)
├── servicenow_client.py            httpx async REST client for ServiceNow Table API
├── servicenow_server.py            ServiceNowMCPServer (6 tools)
│
└── servers/                        [9 MCP Server Implementations]
    ├── azure/                      Azure resource management (23 tools, 5 SDK clients)
    ├── filesystem/                 Local file operations with sandbox (6 tools)
    ├── shell/                      Shell command execution (3 tools)
    ├── ldap/                       LDAP/AD directory operations (6 tools)
    ├── ssh/                        Remote SSH + SFTP operations (6 tools)
    ├── n8n/                        n8n workflow automation (6 tools)
    ├── adf/                        Azure Data Factory pipelines (8 tools)
    └── d365/                       Dynamics 365 CRM entities (6 tools)
```

---

## MCP Server 1: Azure (23 tools)

**Directory:** `servers/azure/` | **SDK:** azure-identity, azure-mgmt-compute/resource/network/monitor/storage

**Server class:** `AzureMCPServer` — 5 tool modules, lazy AzureClientManager, DefaultAzureCredential

### VM Tools (7 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `list_vms` | resource_group? | READ (1) | List VMs in subscription or resource group |
| `get_vm` | resource_group, vm_name | READ (1) | Get VM details (disks, NICs, status) |
| `get_vm_status` | resource_group, vm_name | READ (1) | Get power state and disk statuses |
| `start_vm` | resource_group, vm_name, wait? | ADMIN (3) | Start a stopped VM |
| `stop_vm` | resource_group, vm_name, skip_shutdown?, wait? | ADMIN (3) | Stop/deallocate a VM |
| `restart_vm` | resource_group, vm_name, wait? | EXECUTE (2) | Restart a VM |
| `run_command` | resource_group, vm_name, command, command_id? | ADMIN (3) | Execute command on VM (auto-detects OS) |

### Resource Tools (4 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `list_resource_groups` | tag_filter? | READ (1) | List all resource groups with optional tag filter |
| `get_resource_group` | resource_group | READ (1) | Get resource group details |
| `list_resources` | resource_group, resource_type? | READ (1) | List resources in a resource group |
| `search_resources` | resource_type?, tag_name?, tag_value?, name_contains? | READ (1) | Search resources across subscription |

### Monitor Tools (3 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `get_metrics` | resource_id, metric_names, timespan?, interval?, aggregation? | READ (1) | Get resource metrics (Average/Min/Max/Total/Count) |
| `list_alerts` | resource_group?, severity?, alert_state? | READ (1) | List active metric + activity log alerts |
| `get_metric_definitions` | resource_id | READ (1) | Get available metrics for a resource |

### Network Tools (5 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `list_vnets` | resource_group? | READ (1) | List VNets with address spaces and subnets |
| `get_vnet` | resource_group, vnet_name | READ (1) | Get VNet details (subnets, DNS, DDoS protection) |
| `list_nsgs` | resource_group? | READ (1) | List NSGs with rule counts |
| `get_nsg_rules` | resource_group, nsg_name | READ (1) | Get NSG security rules + default rules |
| `list_public_ips` | resource_group? | READ (1) | List public IPs with allocation method and DNS |

### Storage Tools (4 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `list_storage_accounts` | resource_group? | READ (1) | List storage accounts with SKU, tier, status |
| `get_storage_account` | resource_group, account_name | READ (1) | Get account details (endpoints, encryption, network rules) |
| `list_containers` | resource_group, account_name | READ (1) | List blob containers with access level and lease state |
| `get_storage_usage` | resource_group, account_name | READ (1) | Get storage usage and capacity by location |

---

## MCP Server 2: Filesystem (6 tools)

**Directory:** `servers/filesystem/` | **SDK:** pathlib (stdlib)

**Server class:** `FilesystemMCPServer` — FilesystemSandbox enforces path restrictions

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `read_file` | path, encoding?, max_size? | READ (1) | Read file contents with size limit |
| `write_file` | path, content, encoding?, create_dirs? | EXECUTE (2) | Write content to file, optional mkdir |
| `list_directory` | path, pattern?, recursive?, max_depth? | READ (1) | List directory with glob filter |
| `search_files` | path, pattern, content_pattern?, max_results? | READ (1) | Search files by name + optional content grep |
| `get_file_info` | path | READ (1) | Get file metadata (size, timestamps, type) |
| `delete_file` | path | ADMIN (3) | Delete a file (requires elevated permission) |

**Sandbox:** `FilesystemSandbox` (529 LOC) — `allowed_paths` whitelist, `denied_extensions` blacklist, path traversal prevention, max file size enforcement.

---

## MCP Server 3: Shell (3 tools)

**Directory:** `servers/shell/` | **SDK:** subprocess (stdlib)

**Server class:** `ShellMCPServer` — ShellExecutor with CommandWhitelist integration

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `run_command` | command, timeout?, working_directory? | ADMIN (3) | Execute shell command (max 300s timeout) |
| `run_script` | script_path, arguments?, timeout? | ADMIN (3) | Execute script file (.ps1, .sh, .bat, .cmd, .py) |
| `get_shell_info` | — | READ (1) | Get shell type, timeout, whitelist config |

**Command Security:** Every command passes through `CommandWhitelist.check_command()`:
- `"allowed"` → 65 whitelisted commands execute immediately
- `"blocked"` → 26 regex patterns reject dangerous commands (rm -rf /, format, shutdown, etc.)
- `"requires_approval"` → logs WARNING, proceeds in log-only mode (HITL enforcement deferred)

---

## MCP Server 4: LDAP (6 tools)

**Directory:** `servers/ldap/` | **SDK:** ldap3

**Server class:** `LDAPMCPServer` — LDAPConnectionManager with connection pooling

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `ldap_connect` | server?, port?, bind_dn?, bind_password? | EXECUTE (2) | Connect to LDAP/AD server |
| `ldap_search` | filter, search_base?, attributes?, scope?, size_limit? | READ (1) | Search directory with LDAP filter |
| `ldap_search_users` | username?, email?, attributes? | READ (1) | Search user entries (wildcard support) |
| `ldap_search_groups` | group_name?, attributes? | READ (1) | Search group entries |
| `ldap_get_entry` | dn, attributes? | READ (1) | Get specific entry by distinguished name |
| `ldap_disconnect` | — | READ (1) | Disconnect from LDAP server |

**AD Extensions:** `ad_config.py` + `ad_operations.py` provide Active Directory-specific OU/group/user operations.

---

## MCP Server 5: SSH (6 tools)

**Directory:** `servers/ssh/` | **SDK:** paramiko

**Server class:** `SSHMCPServer` — SSHConnectionManager with connection caching, CommandWhitelist integration

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `ssh_connect` | host, username, port?, password?, private_key_path?, private_key_passphrase? | ADMIN (3) | Connect via password or private key |
| `ssh_execute` | host, username, command, port?, timeout? | ADMIN (3) | Execute remote command (whitelist-checked) |
| `ssh_upload` | host, username, local_path, remote_path, port? | ADMIN (3) | Upload file via SFTP |
| `ssh_download` | host, username, remote_path, local_path, port? | EXECUTE (2) | Download file via SFTP |
| `ssh_list_directory` | host, username, remote_path, port? | EXECUTE (2) | List remote directory via SFTP |
| `ssh_disconnect` | host, username, port? | READ (1) | Disconnect SSH session |

**Command Security:** `ssh_execute` passes remote commands through the same `CommandWhitelist` as Shell tools.

---

## MCP Server 6: ServiceNow (6 tools)

**Directory:** `mcp/servicenow_*.py` (top-level) | **SDK:** httpx (async HTTP)

**Server class:** `ServiceNowMCPServer` — Sprint 117, ITSM incident/RITM lifecycle

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `create_incident` | short_description, description, category?, urgency?, assignment_group?, caller_id? | EXECUTE (2) | Create new Incident |
| `update_incident` | sys_id, state?, assignment_group?, work_notes?, comments?, close_code?, close_notes? | EXECUTE (2) | Update Incident (state, assign, resolve) |
| `get_incident` | number?, sys_id? | READ (1) | Query Incident by number or sys_id |
| `create_ritm` | cat_item, variables, requested_for, short_description | EXECUTE (2) | Create Requested Item from catalog |
| `get_ritm_status` | number?, sys_id? | READ (1) | Query RITM approval/fulfillment status |
| `add_attachment` | table, sys_id, file_name, content, content_type? | EXECUTE (2) | Attach file to any record |

**Error Hierarchy:** `ServiceNowError` → `ServiceNowAuthError`, `ServiceNowNotFoundError`, `ServiceNowPermissionError`, `ServiceNowServerError`

---

## MCP Server 7: n8n (6 tools)

**Directory:** `servers/n8n/` | **SDK:** httpx (async HTTP)

**Server class:** `N8nMCPServer` — Sprint 121, workflow automation integration

### Workflow Tools (3 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `n8n_list_workflows` | active?, tags?, limit? | READ (1) | List workflows with optional filtering |
| `n8n_get_workflow` | workflow_id | READ (1) | Get workflow details (nodes, connections, settings) |
| `n8n_activate_workflow` | workflow_id, active | ADMIN (3) | Activate or deactivate a workflow |

### Execution Tools (3 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `n8n_execute_workflow` | workflow_id, input_data? | EXECUTE (2) | Trigger workflow execution with input data |
| `n8n_get_execution` | execution_id | READ (1) | Get execution status, timing, and output |
| `n8n_list_executions` | workflow_id?, status?, limit? | READ (1) | List execution history with filtering |

---

## MCP Server 8: Azure Data Factory (8 tools)

**Directory:** `servers/adf/` | **SDK:** httpx (Azure REST API)

**Server class:** `AdfMCPServer` — Sprint 125, ETL pipeline management

### Pipeline Tools (4 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `adf_list_pipelines` | — | READ (1) | List pipelines with activity/parameter summary |
| `adf_get_pipeline` | pipeline_name | READ (1) | Get pipeline details (activities, dependencies, params) |
| `adf_run_pipeline` | pipeline_name, parameters? | EXECUTE (2) | Trigger pipeline run, returns run ID |
| `adf_cancel_pipeline_run` | run_id | ADMIN (3) | Cancel a running pipeline |

### Monitoring Tools (4 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `adf_get_pipeline_run` | run_id | READ (1) | Get run details (status, duration, invokedBy) |
| `adf_list_pipeline_runs` | last_updated_after?, last_updated_before? | READ (1) | Query run history with time range |
| `adf_list_datasets` | — | READ (1) | List datasets with type and linked service |
| `adf_list_triggers` | — | READ (1) | List triggers with schedule/event config |

---

## MCP Server 9: Dynamics 365 (6 tools)

**Directory:** `servers/d365/` | **SDK:** httpx (OData v4 Web API)

**Server class:** `D365MCPServer` — Sprint 129, CRM entity operations

### Query Tools (4 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `d365_query_entities` | entity_name, filter?, select?, top?, orderby? | READ (1) | OData query with $filter/$select/$top/$orderby |
| `d365_get_record` | entity_name, record_id, select? | READ (1) | Get single record by GUID |
| `d365_list_entity_types` | — | READ (1) | List all customizable entity types |
| `d365_get_entity_metadata` | entity_name | READ (1) | Get entity metadata (PK, name attribute, entity set) |

### CRUD Tools (2 tools)

| Tool | Params | Permission | Description |
|------|--------|-----------|-------------|
| `d365_create_record` | entity_name, data | EXECUTE (2) | Create new entity record |
| `d365_update_record` | entity_name, record_id, data | EXECUTE (2) | Partial update existing record |

**Auth:** `D365AuthProvider` — OAuth2 client_credentials flow with token caching.

---

## Core Protocol

### JSON-RPC 2.0 Message Flow

```
MCPClient                        StdioTransport                       MCPProtocol (Server)
   │                                   │                                     │
   │── MCPRequest (initialize) ───────▶│── JSON + \n ────────────────────────▶│
   │                                   │                                     │── _handle_initialize()
   │◀── MCPResponse (capabilities) ────│◀── JSON + \n ───────────────────────│
   │                                   │                                     │
   │── MCPRequest (tools/list) ───────▶│─────────────────────────────────────▶│
   │◀── MCPResponse ({tools: [...]}) ──│◀────────────────────────────────────│── schema.to_mcp_format()
   │                                   │                                     │
   │── MCPRequest (tools/call) ───────▶│─────────────────────────────────────▶│
   │                                   │                  permission_checker ─┤── check_tool_permission()
   │                                   │                                     │── handler(**arguments)
   │◀── MCPResponse (ToolResult) ──────│◀────────────────────────────────────│── result.to_mcp_format()
```

### Protocol Version

- **MCP_VERSION:** `2024-11-05`
- **Server Info:** `ipa-platform-mcp` v1.0.0
- **Capabilities:** `tools` (listChanged: true), `resources` (subscribe: false), `prompts`, `logging`

### Transport Implementations

| Transport | Mode | Use Case | Key Details |
|-----------|------|----------|-------------|
| `StdioTransport` | Production | Subprocess communication | `asyncio.create_subprocess_exec`, JSON-per-line, read_lock/write_lock, pending_requests Future map |
| `InMemoryTransport` | Testing | Direct protocol routing | No subprocess, routes MCPRequest → MCPProtocol.handle_request() directly |

### Error Codes (MCPErrorCode)

| Code | Name | Description |
|------|------|-------------|
| -32700 | PARSE_ERROR | Invalid JSON received |
| -32600 | INVALID_REQUEST | Invalid JSON-RPC request |
| -32601 | METHOD_NOT_FOUND | Unknown method name |
| -32602 | INVALID_PARAMS | Invalid method parameters |
| -32603 | INTERNAL_ERROR | Internal server error |

---

## Security Layer

### 4-Level RBAC (PermissionLevel)

| Level | Name | Access | Example Tools |
|-------|------|--------|---------------|
| 0 | NONE | No access | — |
| 1 | READ | List and view schemas, read-only operations | list_vms, get_incident, d365_query_entities |
| 2 | EXECUTE | Execute tools that modify state | write_file, create_incident, adf_run_pipeline |
| 3 | ADMIN | Full control, destructive operations | start_vm, run_command, ssh_connect, delete_file |

### Permission Evaluation Pipeline

```
Tool Call Request
    │
    ▼
MCPPermissionChecker
    ├── mode = "log" (default) or "enforce"
    ├── dev/testing → auto-ADMIN policy (all allowed)
    └── production → explicit PermissionPolicy required
    │
    ▼
PermissionManager.check_permission()
    ├── 1. Collect user + role policies
    ├── 2. Sort by priority (highest first)
    ├── 3. Check deny_list (fnmatch glob → immediate deny)
    ├── 4. Check server/tool pattern match
    ├── 5. Evaluate dynamic conditions (time_range, ip_whitelist, custom)
    └── 6. Compare policy.level >= required_level
    │
    ▼
Result: allowed (True) or denied (False/PermissionError)
```

### CommandWhitelist (Shell + SSH)

**65 allowed commands** organized by category:
- System info: `whoami`, `hostname`, `date`, `uptime`, `uname`
- File viewing: `ls`, `cat`, `head`, `tail`, `find`, `grep`, `stat`
- Network: `ping`, `nslookup`, `dig`, `traceroute`, `curl`, `wget`, `netstat`
- System status: `ps`, `top`, `df`, `du`, `free`, `vmstat`, `lsof`
- AD read-only: `dsquery`, `dsget`, `Get-ADUser`, `Get-ADGroup`
- Text processing: `awk`, `sed`, `sort`, `uniq`, `cut`
- PowerShell read-only: `Get-Process`, `Get-Service`, `Get-ChildItem`, `Test-Connection`

**26 blocked patterns** (regex, case-insensitive):
- Destructive: `rm -rf /`, `del /s`, `format C:`, `mkfs.*`, `dd if=.*of=/dev`
- Dangerous writes: `chmod 777 /`, `chown .* /$`
- Remote code exec: `curl.*|.*sh`, `wget.*|.*sh`
- System shutdown: `shutdown`, `reboot`, `halt`, `poweroff`, `init 0/6`
- Fork bomb: `:(){ .*:|:& }`
- Windows: `Remove-Item.*-Recurse -Force`, `Stop-Computer`, `Restart-Computer`

**Three-tier result:** "allowed" | "blocked" | "requires_approval"

### AuditLogger (3 Storage Backends)

| Backend | Class | Storage | Use Case |
|---------|-------|---------|----------|
| In-Memory | `InMemoryAuditStorage` | `deque(maxlen=10000)` | Development/testing |
| File | `FileAuditStorage` | JSON Lines file | Single-server production |
| Redis | `RedisAuditStorage` | Sorted Set (`mcp:audit:events`) | Multi-server production (Sprint 120) |

**13 Event Types:** `SERVER_CONNECT`, `SERVER_DISCONNECT`, `SERVER_ERROR`, `TOOL_LIST`, `TOOL_EXECUTION`, `TOOL_ERROR`, `ACCESS_GRANTED`, `ACCESS_DENIED`, `CONFIG_CHANGE`, `POLICY_CHANGE`, `SYSTEM_START`, `SYSTEM_SHUTDOWN`

**Sensitive key sanitization:** Automatically redacts values for keys containing: `password`, `secret`, `token`, `api_key`, `credential`, `auth`, `private_key`

---

## Known Issues

| # | Severity | Component | Issue | Evidence |
|---|----------|-----------|-------|----------|
| 1 | **CRITICAL** | AuditLogger | Default constructor falls back to `InMemoryAuditStorage` with only a warning log. No server startup code connects it to `RedisAuditStorage` or `FileAuditStorage`. All audit events are lost on restart. | `audit.py:452-454` — `logger.warning("AuditLogger: using InMemoryAuditStorage...")` |
| 2 | **HIGH** | Shell/SSH HITL | `CommandWhitelist` returns `"requires_approval"` for non-whitelisted commands, but Shell and SSH tools only log a WARNING and proceed ("log-only mode"). No actual HITL approval gate exists. | `shell/tools.py:162-165`, `ssh/tools.py:387-391` — `"(proceeding in log-only mode)"` |
| 3 | **HIGH** | PermissionChecker | `MCP_PERMISSION_MODE` defaults to `"log"`, meaning permission denials are logged but never enforced. In dev/testing, all operations get ADMIN access by default. | `permission_checker.py:52` — `self._mode = os.environ.get("MCP_PERMISSION_MODE", "log")` |
| 4 | **MEDIUM** | StdioTransport | No reconnection logic when subprocess dies unexpectedly. `_read_loop` sets `_connected = False` but caller gets no notification. | `transport.py:271-273` — `self._connected = False; break` |
| 5 | **MEDIUM** | FileAuditStorage | Uses synchronous `open()` inside async methods with `asyncio.Lock`. Under high concurrency, the blocking I/O stalls the event loop. | `audit.py:329-330` — `with open(self._file_path, "a") as f:` |
| 6 | **LOW** | ServiceNow | ServiceNow server files are at the MCP package root level (`servicenow_config.py`, `servicenow_client.py`, `servicenow_server.py`) rather than in `servers/servicenow/` like other servers. Inconsistent directory structure. | File paths in file inventory |
| 7 | **LOW** | ConfigLoader | YAML is an optional dependency (`try: import yaml`). If PyYAML is not installed, `load_from_file()` raises `ConfigError` at runtime rather than at import time. | `config_loader.py:39-44` |

---

## Tool Summary by Permission Level

| Permission Level | Count | Tools |
|-----------------|-------|-------|
| READ (1) | 46 | All list/get/search/query tools across all 9 servers |
| EXECUTE (2) | 14 | write_file, ldap_connect, restart_vm, create_incident, update_incident, create_ritm, add_attachment, n8n_execute_workflow, adf_run_pipeline, d365_create_record, d365_update_record, ssh_download, ssh_list_directory |
| ADMIN (3) | 10 | start_vm, stop_vm, run_command (Azure), run_command (Shell), run_script, delete_file, ssh_connect, ssh_execute, ssh_upload, adf_cancel_pipeline_run, n8n_activate_workflow |

**Total: 70 tools across 9 MCP Servers**

---

## Phase Evolution

| Phase | Sprint | Scope | Key Changes |
|-------|--------|-------|-------------|
| Phase 9 | 31-33 | Initial MCP infrastructure | Core protocol, types, transport, client, Azure server (VM + Resource + Monitor + Network + Storage) |
| Phase 10 | 34-36 | Additional servers | Filesystem (sandbox), Shell (executor), LDAP (client + AD), SSH (paramiko wrapper) |
| Phase 33 | 107-109 | Security hardening | — |
| Phase 35 | 113 | RBAC + Command safety | `MCPPermissionChecker` (log/enforce), `CommandWhitelist` (65 allowed, 26 blocked), per-tool PERMISSION_LEVELS |
| Phase 36 | 117 | ServiceNow integration | ServiceNowMCPServer (6 tools: incident CRUD + RITM + attachment) |
| Phase 37 | 119-120 | Audit infrastructure | `RedisAuditStorage` (Sprint 120), Redis Sorted Set for production audit |
| Phase 38 | 121 | n8n integration | N8nMCPServer (6 tools: workflow management + execution triggering) |
| Phase 40 | 125 | ADF integration | AdfMCPServer (8 tools: pipeline CRUD + monitoring + datasets + triggers) |
| Phase 42 | 129 | D365 integration | D365MCPServer (6 tools: OData query + CRUD), OAuth2 auth provider |

---

## Cross-Layer Dependencies

```
Layer 08 (MCP Tools)
    │
    ├──▶ Layer 07 (Claude SDK)           claude_sdk/mcp/ uses MCPClient for tool discovery
    ├──▶ Layer 06 (Hybrid Bridge)        HybridOrchestrator routes tool calls through MCP
    ├──▶ Layer 05 (Orchestration)        Intent router selects MCP tools for IT operations
    ├──▶ Layer 03 (AG-UI)                Tool call events streamed to frontend via SSE
    │
    ├──◀ Infrastructure: Redis           RedisAuditStorage (mcp:audit:events)
    ├──◀ Infrastructure: Azure SDK       azure-identity, azure-mgmt-* packages
    ├──◀ Infrastructure: paramiko        SSH client library
    ├──◀ Infrastructure: ldap3           LDAP protocol library
    └──◀ Infrastructure: httpx           Async HTTP for ServiceNow, n8n, ADF, D365
```
