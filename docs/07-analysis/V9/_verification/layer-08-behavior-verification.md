# V9 Layer-08 MCP Tools -- Behavior Verification Report

> **Verifier**: Claude Opus 4.6 (1M context)
> **Date**: 2026-03-31
> **Target**: `docs/07-analysis/V9/01-architecture/layer-08-mcp-tools.md`
> **Method**: Full source reading of core protocol, security, and all 9 server PERMISSION_LEVELS
> **Result**: **49/50 PASS, 1 MINOR issue found**

---

## P1-P10: MCP Gateway Tool Call Flow

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P1 | `MCPProtocol.handle_request()` routes by method string to 9 handlers (initialize, initialized, tools/list, tools/call, resources/list, resources/read, prompts/list, prompts/get, ping) | `protocol.py:179-196` -- exact if/elif chain for all 9 methods + ping returns `{}` | PASS |
| P2 | Permission check runs BEFORE handler invocation in `_handle_tools_call()` | `protocol.py:304-317` -- `self._permission_checker.check_tool_permission()` called before `handler(**arguments)` at line 320 | PASS |
| P3 | Default required level is 2 (EXECUTE) if not explicitly set | `protocol.py:305` -- `self._tool_permission_levels.get(tool_name, 2)` | PASS |
| P4 | In log mode, permission denial logs WARNING but tool invocation continues | `permission_checker.py:153-158` -- logs WARNING, returns `allowed` (False) but no exception raised; `protocol.py:304-317` only catches `PermissionError` so execution proceeds | PASS |
| P5 | In enforce mode, `PermissionError` is raised and caught | `permission_checker.py:143-152` -- raises `PermissionError`; `protocol.py:313` catches it and returns `isError` result | PASS |
| P6 | Tool result format: success = `{content: [{type: "text", text: "..."}]}` | `types.py:208-221` -- `to_mcp_format()` produces exactly this structure | PASS |
| P7 | Tool result format: error = `{isError: true, content: [{type: "text", text: "error msg"}]}` | `types.py:222-228` -- matches exactly, uses `self.error or "Unknown error"` | PASS |
| P8 | Auto-serializes dict/list via `json.dumps(ensure_ascii=False, indent=2)` | `types.py:214-215` -- confirmed exactly | PASS |
| P9 | Method-level try/catch wraps all handlers, returns INTERNAL_ERROR(-32603) | `protocol.py:206-212` -- outer try/except returns `MCPResponse.create_error(code=MCPErrorCode.INTERNAL_ERROR)` | PASS |
| P10 | Server identity: "ipa-platform-mcp" v1.0.0, capabilities include `{tools: {listChanged: true}}` | `protocol.py:53-54` -- `SERVER_NAME = "ipa-platform-mcp"`, `SERVER_VERSION = "1.0.0"`; line 235-240 confirms capabilities | PASS |

## P11-P15: Azure Server Tool Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P11 | VM tools: 7 tools (list_vms, get_vm, get_vm_status, start_vm, stop_vm, restart_vm, run_command) | `azure/tools/vm.py:76-84` PERMISSION_LEVELS has exactly these 7 | PASS |
| P12 | VM permission levels: list/get/status=READ(1), start/stop/run_command=ADMIN(3), restart=EXECUTE(2) | `vm.py:77-83` -- list_vms:1, get_vm:1, get_vm_status:1, start_vm:3, stop_vm:3, restart_vm:2, run_command:3 | PASS |
| P13 | Resource tools: 4 tools all READ(1) | `resource.py:42-47` -- list_resource_groups:1, get_resource_group:1, list_resources:1, search_resources:1 | PASS |
| P14 | Monitor tools: 3 tools all READ(1) | `monitor.py:42-46` -- get_metrics:1, list_alerts:1, get_metric_definitions:1 | PASS |
| P15 | Network tools: 5 tools all READ(1); Storage tools: 4 tools all READ(1) | `network.py:43-49` -- 5 tools all :1; `storage.py:42-47` -- 4 tools all :1 | PASS |

**Azure totals from source**: VM(7) + Resource(4) + Monitor(3) + Network(5) + Storage(4) = **23 tools**. Doc says 23. PASS.

## P16-P20: Shell Server Command Execution Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P16 | Shell has 3 tools: run_command, run_script, get_shell_info | `shell/tools.py:54-57` PERMISSION_LEVELS has run_command:3, run_script:3; `tools.py:125` defines `get_shell_info` in schemas | PASS |
| P17 | run_command and run_script are ADMIN(3) | `shell/tools.py:55-56` -- confirmed :3 | PASS |
| P18 | `get_shell_info` is in schemas but NOT in PERMISSION_LEVELS dict | `shell/tools.py:54-57` only has run_command and run_script; get_shell_info is defined at line 125 as ToolSchema but missing from PERMISSION_LEVELS | PASS |
| P19 | Commands validated through `CommandWhitelist` | `shell/tools.py:66` -- `self._whitelist = CommandWhitelist()` in `__init__` | PASS |
| P20 | Doc says get_shell_info permission = READ(1) | Source has NO explicit permission level for get_shell_info. Protocol default is EXECUTE(2). Doc table says READ(1). | **MINOR** ⚠️ |

> **P20 Detail**: The doc table (Section 4.3) claims `get_shell_info` has permission `READ (1)`, but the source code `PERMISSION_LEVELS` dict does NOT include `get_shell_info`. The protocol default (`protocol.py:305`) is `2` (EXECUTE), not `1` (READ). The Note in Section 4.10 correctly identifies this gap but the table in 4.3 states `READ (1)` which is inferred, not from source. The Note at section 4.10 line 519 is accurate; the table at 4.3 is slightly misleading.

## P21-P25: Filesystem Server File Operation Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P21 | 6 tools: read_file, list_directory, search_files, get_file_info, write_file, delete_file | `filesystem/tools.py:47-54` PERMISSION_LEVELS has exactly these 6 | PASS |
| P22 | read_file, list_directory, search_files, get_file_info = READ(1) | Lines 48-51: all :1 | PASS |
| P23 | write_file = EXECUTE(2) | Line 52: `"write_file": 2` | PASS |
| P24 | delete_file = ADMIN(3) | Line 53: `"delete_file": 3` | PASS |
| P25 | Sandbox: `FilesystemSandbox` with `SandboxConfig` | `filesystem/tools.py:56` -- `__init__(self, sandbox: FilesystemSandbox)` confirmed | PASS |

## P26-P30: SSH/LDAP Server Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P26 | SSH 6 tools: ssh_connect(3), ssh_execute(3), ssh_upload(3), ssh_download(2), ssh_list_directory(2), ssh_disconnect(1) | `ssh/tools.py:58-65` -- exact match: connect:3, execute:3, upload:3, download:2, list_directory:2, disconnect:1 | PASS |
| P27 | SSH remote commands validated through CommandWhitelist | `ssh/tools.py:74` -- `self._whitelist = CommandWhitelist()` | PASS |
| P28 | LDAP 6 tools: ldap_connect(2), ldap_search(1), ldap_search_users(1), ldap_search_groups(1), ldap_get_entry(1), ldap_disconnect(1) | `ldap/tools.py:47-54` -- exact match | PASS |
| P29 | LDAP doc says ldap_connect = EXECUTE(2) | `ldap/tools.py:48` -- `"ldap_connect": 2` confirmed | PASS |
| P30 | LDAP doc says ldap_disconnect = READ(1) | `ldap/tools.py:53` -- `"ldap_disconnect": 1` confirmed | PASS |

## P31-P35: ServiceNow/n8n/D365/ADF Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P31 | ServiceNow 6 tools: create_incident(2), update_incident(2), get_incident(1), create_ritm(2), get_ritm_status(1), add_attachment(2) | `servicenow_server.py:58-65` -- exact match | PASS |
| P32 | ServiceNow root-level files (not under servers/) | Files: `servicenow_server.py`, `servicenow_client.py`, `servicenow_config.py` at `mcp/` root level confirmed by glob | PASS |
| P33 | n8n 6 tools: workflow(list:1, get:1, activate:3) + execution(execute:2, get:1, list:1) | `n8n/tools/workflow.py:43-47` + `n8n/tools/execution.py:44-48` -- exact match, totals 6 | PASS |
| P34 | ADF 8 tools: pipeline(list:1, get:1, run:2, cancel:3) + monitoring(get_run:1, list_runs:1, list_datasets:1, list_triggers:1) | `adf/tools/pipeline.py:45-50` + `adf/tools/monitoring.py:42-47` -- exact match, totals 8 | PASS |
| P35 | D365 6 tools: query(query_entities:1, get_record:1, list_entity_types:1, get_entity_metadata:1) + crud(create_record:2, update_record:2) | `d365/tools/query.py:45-50` + `d365/tools/crud.py:46-49` -- exact match, totals 6 | PASS |

## P36-P40: CommandWhitelist Matching Logic

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P36 | Three-tier check: blocked first, then whitelist, then requires_approval | `command_whitelist.py:162-183` -- blocked patterns checked first (line 162), then whitelist (line 174), else requires_approval (line 183) | PASS |
| P37 | 79 DEFAULT_WHITELIST commands | Counted from source list at `command_whitelist.py:42-71`: **79** commands confirmed | PASS |
| P38 | 24 BLOCKED_PATTERNS compiled with `re.IGNORECASE` | `command_whitelist.py:73-98`: 24 patterns; `line 134: re.compile(pattern, re.IGNORECASE)` | PASS |
| P39 | Matching: blocked uses regex `pattern.search()`, whitelist uses exact `cmd_name in self._whitelist` (Set lookup) | `line 163: pattern.search(command_stripped)` for blocked; `line 174: cmd_name in self._whitelist` (Set) for whitelist | PASS |
| P40 | Command name extraction strips sudo/nohup/env/time prefixes, handles path-prefixed commands | `command_whitelist.py:197-213` -- strips `("sudo ", "nohup ", "env ", "time ")`, then `rsplit("/")[-1]` and `rsplit("\\")[-1]` | PASS |

## P41-P45: ToolSchema Parameter Validation Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P41 | 7 ToolInputType values: STRING, NUMBER, INTEGER, BOOLEAN, OBJECT, ARRAY, NULL | `types.py:24-30` -- all 7 enum members confirmed | PASS |
| P42 | ToolParameter.to_json_schema() produces standard JSON Schema | `types.py:59-79` -- returns `{type, description}` + optional default/enum/items/properties | PASS |
| P43 | ToolSchema.to_mcp_format() produces `{name, description, inputSchema: {type: "object", properties, required}}` | `types.py:116-142` -- exact structure confirmed | PASS |
| P44 | ToolSchema.from_mcp_format() graceful type fallback: unknown types -> STRING | `types.py:162-164` -- `try: ToolInputType(param_type)` / `except ValueError: ToolInputType.STRING` | PASS |
| P45 | ToolParameter fields: name, type, description, required, default, enum, items, properties | `types.py:50-57` -- exact match of all 8 fields | PASS |

## P46-P50: Audit Logging Record Behavior

| # | Claim | Source Evidence | Verdict |
|---|-------|----------------|---------|
| P46 | 12 AuditEventType values across 5 categories | `audit.py:40-63` -- 12 enum values: 3 Connection + 3 Tool + 2 Access + 2 Admin + 2 System = 12 | PASS |
| P47 | Sensitive field redaction for keys containing: password, secret, token, api_key, credential, auth, private_key | `audit.py:129-137` -- exact 7-item set, recursive redaction via `_sanitize_arguments()` | PASS |
| P48 | InMemoryAuditStorage: bounded deque(maxlen=10000), asyncio.Lock | `audit.py:271,277-278` -- `deque(maxlen=max_size)` with default `max_size=10000`, `self._lock = asyncio.Lock()` | PASS |
| P49 | RedisAuditStorage: Sorted Set with timestamp scores, auto-trim, key `mcp:audit:events` | `redis_audit.py:47,89-100` -- `DEFAULT_KEY = "mcp:audit:events"`, `zadd(key, {data: score})` with score from timestamp, `zremrangebyrank` for trimming | PASS |
| P50 | AuditLogger convenience methods: log_tool_execution(), log_access(), log_server_event(), get_user_activity(hours=24), get_server_activity(hours=24), cleanup(days=30), add_handler(), enabled property | `audit.py:488-686` -- all methods confirmed: log_tool_execution(488), log_access(527), log_server_event(564), get_user_activity(607, hours=24), get_server_activity(627, hours=24), cleanup(647, days=30), add_handler(661), enabled property(678-686) | PASS |

---

## Summary

| Category | Points | Pass | Minor | Fail |
|----------|--------|------|-------|------|
| P1-P10: MCP Gateway Flow | 10 | 10 | 0 | 0 |
| P11-P15: Azure Server | 5 | 5 | 0 | 0 |
| P16-P20: Shell Server | 5 | 4 | 1 | 0 |
| P21-P25: Filesystem Server | 5 | 5 | 0 | 0 |
| P26-P30: SSH/LDAP Server | 5 | 5 | 0 | 0 |
| P31-P35: ServiceNow/n8n/D365/ADF | 5 | 5 | 0 | 0 |
| P36-P40: CommandWhitelist Logic | 5 | 5 | 0 | 0 |
| P41-P45: ToolSchema Validation | 5 | 5 | 0 | 0 |
| P46-P50: Audit Logging | 5 | 5 | 0 | 0 |
| **Total** | **50** | **49** | **1** | **0** |

## Issue Found

### P20: get_shell_info Permission Level Mismatch (MINOR, cosmetic)

- **Location**: Section 4.3 table, line `| get_shell_info | READ (1) |`
- **Problem**: The document table states `get_shell_info` has permission `READ (1)`, but the source `ShellTools.PERMISSION_LEVELS` dict only includes `run_command` and `run_script`. Since `get_shell_info` is not in the dict, the protocol default of `2` (EXECUTE) applies at runtime.
- **Note**: The doc's own Note at Section 4.10 (line 519) correctly identifies this gap: "Shell's `get_shell_info` is defined in schemas but not in `PERMISSION_LEVELS`". The table in 4.3 is slightly misleading by showing a specific permission level that isn't explicitly set in code.
- **Recommendation**: Either add `"get_shell_info": 1` to `ShellTools.PERMISSION_LEVELS` in source code to match the intended behavior, or change the table in 4.3 to show the runtime default of EXECUTE (2) with a footnote.
- **Severity**: MINOR -- the Note already documents the discrepancy; this is a table-vs-note inconsistency within the same document.
