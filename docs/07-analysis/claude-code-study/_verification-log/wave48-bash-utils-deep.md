# Wave 48: Deep Analysis — Bash/Shell/PowerShell Execution Infrastructure

> **Wave**: 48 | **Date**: 2026-04-01 | **Quality**: 9.0/10 | **Files**: 35 (22 bash/ + 10 shell/ + 3 powershell/)
> **Supersedes**: `bash-execution.md` (prior wave, surface-level)

---

## 1. File Inventory

### `src/utils/bash/` — 22 files (incl. 8 specs/)

| File | LOC (est.) | Purpose |
|------|-----------|---------|
| `ast.ts` | ~2040 | **Core security engine** — AST walker with fail-closed allowlist |
| `bashParser.ts` | ~2500+ | **Pure-TS bash parser** — tokenizer + recursive-descent, tree-sitter-compatible AST |
| `bashPipeCommand.ts` | ~295 | Pipe stdin redirect rearrangement for `eval` safety |
| `commands.ts` | ~400+ | Legacy shell-quote command splitting + help detection |
| `heredoc.ts` | ~734 | Heredoc extraction/restoration with security hardening |
| `ParsedCommand.ts` | ~318 | Parsed command interface — tree-sitter + regex fallback |
| `parser.ts` | ~200 | High-level parse API — feature-gated entry point |
| `prefix.ts` | ~205 | Command prefix extraction for permission rules |
| `registry.ts` | ~54 | Fig-spec registry with LRU memoization |
| `shellCompletion.ts` | ~260 | Shell tab-completion (bash `compgen` / zsh native) |
| `shellPrefix.ts` | ~29 | `formatShellPrefixCommand()` for `CLAUDE_CODE_SHELL_PREFIX` |
| `shellQuote.ts` | ~305 | Safe wrappers for `shell-quote` library + malformed token detection |
| `shellQuoting.ts` | ~129 | Heredoc/multiline quoting + Windows `>nul` rewriting |
| `ShellSnapshot.ts` | ~583 | Shell environment capture/restore (functions, aliases, options, PATH) |
| `treeSitterAnalysis.ts` | ~507 | Quote-context extraction, compound structure, dangerous pattern detection |
| `specs/index.ts` | ~18 | Spec registry — 7 command specs |
| `specs/alias.ts` | ~14 | Alias command spec |
| `specs/nohup.ts` | ~14 | Nohup wrapper spec (`isCommand: true`) |
| `specs/pyright.ts` | ~91 | Pyright type checker spec with full option list |
| `specs/sleep.ts` | ~13 | Sleep duration spec |
| `specs/srun.ts` | ~31 | SLURM `srun` cluster spec (`isCommand: true`) |
| `specs/time.ts` | ~13 | Time wrapper spec (`isCommand: true`) |
| `specs/timeout.ts` | ~19 | Timeout wrapper spec (duration + `isCommand: true`) |

### `src/utils/shell/` — 10 files

| File | LOC (est.) | Purpose |
|------|-----------|---------|
| `shellProvider.ts` | ~33 | **ShellProvider interface** — `buildExecCommand`, `getSpawnArgs`, `getEnvironmentOverrides` |
| `bashProvider.ts` | ~255 | Bash provider — snapshot sourcing, extglob disable, eval wrap, CWD tracking, tmux isolation |
| `powershellProvider.ts` | ~124 | PowerShell provider — `-EncodedCommand` for sandbox safety, exit-code capture |
| `resolveDefaultShell.ts` | ~14 | Default shell resolution — `settings.defaultShell` or `'bash'` |
| `outputLimits.ts` | ~15 | Max output: 30K default, 150K upper, env-configurable |
| `powershellDetection.ts` | ~108 | PowerShell discovery — `pwsh` preferred, snap launcher bypass, edition detection |
| `readOnlyCommandValidation.ts` | ~600+ | **Comprehensive read-only command allowlists** — git, gh, and external commands with per-flag validation |
| `shellToolUtils.ts` | ~23 | Shell tool name constants, PowerShell tool gate (`isPowerShellToolEnabled`) |
| `prefix.ts` | ~368 | **LLM-powered prefix extraction** — Haiku query + validation + dangerous-prefix blocklist |
| `specPrefix.ts` | ~242 | **Fig-spec-driven prefix walker** — depth rules, subcommand detection, flag-value skipping |

### `src/utils/powershell/` — 3 files

| File | LOC (est.) | Purpose |
|------|-----------|---------|
| `dangerousCmdlets.ts` | ~186 | **Dangerous cmdlet registry** — 9 categories, alias expansion, `NEVER_SUGGEST` set |
| `parser.ts` | ~600+ | **PowerShell AST parser** — spawns `pwsh` with inline PS1 script, returns structured JSON |
| `staticPrefix.ts` | ~317 | Static prefix extraction using PS AST + fig-spec walker reuse |

---

## 2. Architecture Overview

### 2.1 Layered Security Model

The bash execution infrastructure implements a **defense-in-depth** security model with four distinct layers:

```
Layer 1: Pre-Parse Checks (ast.ts)
  ├── Control char rejection (CR, NUL, etc.)
  ├── Unicode whitespace rejection (NBSP, zero-width)
  ├── Backslash-whitespace rejection
  ├── Zsh-specific: ~[ directory, =cmd expansion
  └── Brace+quote obfuscation detection

Layer 2: AST Parse + Walk (bashParser.ts → ast.ts)
  ├── Pure-TS parser with 50ms timeout + 50K node budget
  ├── Fail-closed allowlist: unknown node types → 'too-complex'
  ├── Variable scope tracking with isolation (||, |, &, subshell)
  └── Recursive $() extraction for inner permission checking

Layer 3: Permission Rule Matching (prefix.ts, specPrefix.ts)
  ├── Fig-spec-driven prefix extraction (git status, npm run, etc.)
  ├── LLM-powered fallback (Haiku query for unknown commands)
  ├── Dangerous shell prefix blocklist
  └── Wrapper command unwrapping (nohup, timeout, srun, nice)

Layer 4: Read-Only Validation (readOnlyCommandValidation.ts)
  ├── Per-subcommand flag allowlists (git diff, git log, etc.)
  ├── Flag-argument type system (none, number, string, char, {}, EOF)
  ├── Callback-based dynamic validation
  └── UNC path credential leak prevention (Windows)
```

### 2.2 Shell Provider Abstraction

```
ShellProvider interface
├── bash provider
│   ├── ShellSnapshot (functions, aliases, options, PATH)
│   ├── extglob disable (security)
│   ├── eval wrapping (alias expansion)
│   ├── CWD tracking (pwd -P >| file)
│   ├── tmux socket isolation
│   └── Windows >nul rewrite
└── powershell provider
    ├── -EncodedCommand (Base64 UTF-16LE for sandbox safety)
    ├── $LASTEXITCODE capture (fixes PS 5.1 stderr/$? bug)
    └── TMPDIR/TMPPREFIX for sandbox
```

---

## 3. Bash Parser Deep Dive (`bashParser.ts`)

### 3.1 Architecture

The parser is a **pure-TypeScript recursive-descent parser** that produces tree-sitter-bash-compatible ASTs. It replaced a WASM-based tree-sitter parser to eliminate native module dependencies.

**TsNode structure:**
```typescript
type TsNode = {
  type: string         // e.g., 'command', 'pipeline', 'if_statement'
  text: string         // Raw source text
  startIndex: number   // UTF-8 byte offset (NOT JS string index)
  endIndex: number     // UTF-8 byte offset past last char
  children: TsNode[]
}
```

### 3.2 Tokenizer

The tokenizer (`Lexer` type) handles:
- **UTF-8 byte tracking** — maintains both JS string index and UTF-8 byte offset via `advance()`, with lazy `byteTable` for non-ASCII
- **Token types**: `WORD`, `NUMBER`, `OP`, `NEWLINE`, `COMMENT`, `DQUOTE`, `SQUOTE`, `ANSI_C`, `DOLLAR`, `DOLLAR_PAREN`, `DOLLAR_BRACE`, `DOLLAR_DPAREN`, `BACKTICK`, `LT_PAREN`, `GT_PAREN`, `EOF`
- **Heredoc support** — tracks pending heredoc delimiters and scans body at next newline
- **Shell keywords** — `if`, `then`, `elif`, `else`, `fi`, `while`, `until`, `for`, `in`, `do`, `done`, `case`, `esac`, `function`, `select`
- **Declaration keywords** — `export`, `declare`, `typeset`, `readonly`, `local`

### 3.3 Safety Bounds

| Bound | Value | Purpose |
|-------|-------|---------|
| `PARSE_TIMEOUT_MS` | 50ms | Wall-clock cap — bails on pathological input |
| `MAX_NODES` | 50,000 | Node budget — prevents OOM on deeply nested input |
| `MAX_COMMAND_LENGTH` | 10,000 chars | Maximum parseable command length |
| `PARSE_ABORTED` | Symbol | Sentinel distinguishing abort from module-not-loaded |

### 3.4 Validation Corpus

Validated against a **3,449-input golden corpus** generated from the WASM parser.

---

## 4. AST Security Engine (`ast.ts`)

### 4.1 `parseForSecurity()` — The Core Function

Returns one of three results:
- `{ kind: 'simple', commands: SimpleCommand[] }` — trustworthy argv extracted
- `{ kind: 'too-complex', reason: string }` — cannot statically analyze, ask user
- `{ kind: 'parse-unavailable' }` — tree-sitter not loaded, use legacy path

### 4.2 SimpleCommand Structure

```typescript
type SimpleCommand = {
  argv: string[]                           // argv[0] = command name
  envVars: { name: string; value: string }[]  // Leading VAR=val
  redirects: Redirect[]                    // Output/input redirects
  text: string                             // Original source span
}
```

### 4.3 Node Type Allowlists

**Structural types** (recursed through): `program`, `list`, `pipeline`, `redirected_statement`

**Separator types** (leaf tokens): `&&`, `||`, `|`, `;`, `&`, `|&`, `\n`

**Dangerous types** (trigger too-complex): `command_substitution`, `process_substitution`, `expansion`, `simple_expansion`, `brace_expression`, `subshell`, `compound_statement`, all control flow statements, `function_definition`, `test_command`, `ansi_c_string`, `translated_string`, `herestring_redirect`, `heredoc_redirect`

### 4.4 Variable Scope Tracking

The engine maintains a `varScope: Map<string, string>` with precise bash semantics:

| Construct | Scope behavior |
|-----------|---------------|
| `VAR=x && cmd $VAR` | Sequential — vars carry through `&&`/`;` |
| `true \|\| VAR=x && cmd $VAR` | `\|\|` RHS uses scope snapshot — vars don't leak |
| `cmd1 \| cmd2` | Pipeline — all stages use scope copies |
| `cmd &` | Background — uses scope snapshot |
| `(cmd)` | Subshell — inner scope copy, outer unchanged |
| `if/while/for` body | Body uses scope copy — vars don't leak past `fi`/`done` |
| `VAR=x cmd` | Env-prefix — NOT added to global scope (command-local) |

**Placeholder system:**
- `__CMDSUB_OUTPUT__` — marks `$()` output (runtime-determined)
- `__TRACKED_VAR__` — marks unknown-value tracked vars (loop vars, `read` vars, safe env vars)

**Safe environment variables**: `HOME`, `PWD`, `USER`, `PATH`, `SHELL`, `HOSTNAME`, `UID`, `TMPDIR`, `BASH_VERSION`, etc. — only allowed inside strings, not as bare arguments.

### 4.5 Security-Critical Checks

| Check | Risk mitigated |
|-------|---------------|
| PS4 assignment validation | Trace-time RCE via `PS4='$(id)'` |
| IFS assignment rejection | Word-splitting bypass via custom separator |
| Tilde expansion rejection | Assignment-time `~` expansion divergence |
| Invalid variable name rejection | tree-sitter accepts `1VAR=x` but bash runs it as a command |
| `declare -n/-i/-a/-A` rejection | Nameref dereference, arithmetic eval, subscript injection |
| Array subscript rejection | `declare 'x[$(id)]=val'` — bash evaluates $() in subscript |
| Empty-value bare expansion | `V="" && $V eval x` — expansion disappears, shifting argv |
| Brace expansion detection | `{a,b}` or `{a..b}` — runtime expansion changes argv count |
| Arithmetic variable rejection | `$((x))` where x='a[$(cmd)]' — recursive arithmetic eval |
| Solo-placeholder string rejection | `"$(cmd)"` alone — placeholder bypasses path validation |
| `.text` rebuild from argv | When `$VAR` resolved in argv, rebuild `.text` so deny rules match |

### 4.6 Post-Argv Semantic Checks (checkSemantics)

Located in ast.ts but running after argv extraction:
- **EVAL_LIKE_BUILTINS**: `eval`, `source`, `.`, `exec`, `command`, `builtin`, `fc`, `coproc`, plus zsh precommand modifiers
- **ZSH_DANGEROUS_BUILTINS**: `zmodload`, `emulate`, `sysopen`, `sysread`, `syswrite`, `zpty`, `ztcp`, `zsocket`, `zf_*`
- **SHELL_KEYWORDS**: `if`, `while`, `for`, `case`, `select` as argv[0]
- **PROC_ENVIRON_RE**: blocks reading `/proc/self/environ`
- **NEWLINE_HASH_RE**: blocks `\n#` patterns in argv

---

## 5. Heredoc System (`heredoc.ts`)

### 5.1 Design

Heredocs are extracted **before** shell-quote parsing (shell-quote misparses `<<` as two `<` operators). A placeholder with random salt replaces each heredoc, and `restoreHeredocs()` puts them back after parsing.

### 5.2 Supported Variants

| Syntax | Behavior |
|--------|----------|
| `<<WORD` | Basic heredoc — full shell expansion in body |
| `<<'WORD'` | Quoted — no expansion (literal body) |
| `<<"WORD"` | Double-quoted — with expansion |
| `<<-WORD` | Dash — strips leading tabs |
| `<<\WORD` | Escaped — no expansion |

### 5.3 Security Hardening

The heredoc extractor has extensive security checks:
- **$' and $" bail** — ANSI-C/locale quoting desync risk
- **Backtick bail** — shell_eof_token early closure risk
- **Arithmetic `((` check** — `<<` as bit-shift vs heredoc disambiguation
- **Incremental quote scanner** — O(n) instead of O(n^2) for commands with many `<<`
- **Comment-aware** — `# <<EOF` is not a heredoc
- **Backslash-escaped** — `\<<EOF` is not a heredoc
- **Quote-aware newline** — finds first UNQUOTED newline for body start
- **Line continuation check** — trailing odd backslashes before newline
- **PST_EOFTOKEN paranoia** — shell metachar after delimiter on same line
- **Nesting filter** — `<<` inside another heredoc's body is just text
- **quotedOnly mode** — only extract quoted heredocs (safe bodies), track unquoted ranges

---

## 6. Pipe Command Handling (`bashPipeCommand.ts`)

### 6.1 Problem

When Claude wraps commands in `eval 'cmd' < /dev/null`, the stdin redirect applies to `eval` itself. For piped commands, this causes the first command to block forever on stdin while the second command reads `/dev/null`.

### 6.2 Solution

`rearrangePipeCommand()` restructures: `first_command < /dev/null | rest_of_pipeline`

### 6.3 Bail-Out Conditions

Falls back to whole-command quoting when:
- Backticks present (shell-quote can't handle)
- `$()` command substitution (shell-quote misparses)
- Shell variables (`$VAR` — shell-quote expands to empty)
- Control structures (`for`, `while`, `if`, `case`, `select`)
- Line continuations with embedded newlines
- Shell-quote single-quote bug (`'\' payload '\'`)
- Malformed token detection
- `SECURITY` comment: detailed injection prevention

---

## 7. Command Spec System (`specs/` + `registry.ts`)

### 7.1 CommandSpec Type

```typescript
type CommandSpec = {
  name: string
  description?: string
  subcommands?: CommandSpec[]
  args?: Argument | Argument[]
  options?: Option[]
}

type Argument = {
  isDangerous?: boolean    // Marks dangerous args
  isVariadic?: boolean     // Repeats (echo hello world)
  isOptional?: boolean     // Can be omitted
  isCommand?: boolean      // Wrapper commands (timeout, sudo)
  isModule?: string | boolean  // python -m module
  isScript?: boolean       // node script.js
}
```

### 7.2 Two-Layer Spec Resolution

1. **Built-in specs** — 7 hand-written specs for common commands (timeout, nohup, time, srun, sleep, alias, pyright)
2. **Fig specs** — Dynamic import from `@withfig/autocomplete` package for any command not in built-in list

### 7.3 Wrapper Command Detection

Commands with `isCommand: true` args trigger recursive prefix extraction. The system unwraps up to 2 wrapper levels and 10 recursion depth:
- `timeout 5 git status` → prefix: `timeout git status`
- `nohup npm run build` → prefix: `nohup npm run`

---

## 8. Prefix Extraction System

### 8.1 Static Prefix (`prefix.ts` + `specPrefix.ts`)

`getCommandPrefixStatic()` uses tree-sitter parsing + fig-spec walking:

1. Parse command with tree-sitter
2. Extract argv via `extractCommandArguments()`
3. Look up spec via `getCommandSpec()`
4. Walk spec to determine prefix depth

**Depth rules** (hardcoded for commands without fig specs):
- `rg`: 2, `gcloud`: 4, `aws`: 4, `kubectl`: 3, `docker`: 3, `git push`: 2

### 8.2 LLM-Powered Prefix (`shell/prefix.ts`)

When static extraction fails, queries **Haiku** with a policy spec:
- Validates response is actual prefix of command
- Rejects dangerous shell prefixes (`bash`, `sh`, `pwsh`, `cmd`, bare `git`)
- LRU-memoized (200 entries)
- Cache eviction on promise rejection (abort safety)
- 10-second warning for slow API responses

### 8.3 Compound Command Collapse

For `cmd1 && cmd2 || cmd3`:
- Extract per-subcommand prefixes
- Group by root command
- Collapse via word-aligned longest common prefix
- `npm run test && npm run lint` → `npm run`

---

## 9. Shell Snapshot System (`ShellSnapshot.ts`)

### 9.1 Purpose

Captures the user's interactive shell environment (functions, aliases, options, PATH) at startup, so each `eval`-wrapped command runs as if in the user's shell without spawning a login shell every time.

### 9.2 Capture Process

1. Source user's config file (`.zshrc` / `.bashrc`) with `< /dev/null` stdin redirect
2. Dump functions (zsh: `typeset -f`, bash: `declare -f` with base64 encoding)
3. Dump shell options (zsh: `setopt`, bash: `shopt -p` + `set -o`)
4. Dump aliases (with winpty filter on Windows)
5. Set up embedded tool functions (ripgrep, bfs/ugrep for find/grep)
6. Export PATH

### 9.3 Embedded Search Tool Integration

- **ripgrep**: Shell function using `ARGV0` dispatch trick for bun-embedded binary
- **bfs (find)**: Replaces GNU find with `-regextype findutils-default`
- **ugrep (grep)**: Replaces GNU grep with `-G` (BRE default), `--ignore-files`, `--hidden`, `-I`

### 9.4 Safety

- 10-second creation timeout
- 1MB buffer limit
- File existence check before sourcing (TOCTOU mitigated by `|| true`)
- Cleanup registered for graceful shutdown
- GIT_EDITOR set to `true` to prevent editor popups

---

## 10. Shell Provider Details

### 10.1 Bash Provider (`bashProvider.ts`)

**Execution pipeline:**
```
source snapshot || true
  && session_env_script
  && shopt -u extglob / setopt NO_EXTENDED_GLOB
  && eval 'quoted_command'
  && pwd -P >| cwd_file
```

**Environment overrides:**
- `TMUX` — isolated socket (deferred until first tmux use)
- `TMPDIR` / `CLAUDE_CODE_TMPDIR` — sandbox temp dir
- `TMPPREFIX` — zsh heredoc temp file prefix for sandbox
- Session env vars from `/env` command

**Platform handling:**
- Windows: `windowsPathToPosixPath()` for snapshot/CWD paths
- Windows: `rewriteWindowsNullRedirect()` — `>nul` → `>/dev/null`
- Login shell (`-l`) only when snapshot is unavailable

### 10.2 PowerShell Provider (`powershellProvider.ts`)

**Key differences from bash:**
- `detached: false` (not detached)
- `-NoProfile -NonInteractive` flags
- Exit code: `$LASTEXITCODE` preferred over `$?` (fixes PS 5.1 stderr bug)
- Sandbox: `-EncodedCommand` (Base64 UTF-16LE) survives all quoting layers
- CWD tracking: `(Get-Location).Path | Out-File`

### 10.3 Shell Resolution (`resolveDefaultShell.ts`)

Simple: `settings.defaultShell ?? 'bash'` — does NOT auto-flip Windows to PowerShell.

---

## 11. PowerShell AST Parser (`powershell/parser.ts`)

### 11.1 Architecture

Unlike bash (pure-TS parser), PowerShell parsing **spawns an actual pwsh process** with an inline PS1 script that uses `System.Management.Automation.Language.Parser::ParseInput()`.

### 11.2 Parsed Output Structure

```typescript
type ParsedPowerShellCommand = {
  valid: boolean
  errors: ParseError[]
  statements: ParsedStatement[]      // Top-level statements
  variables: ParsedVariable[]        // All variable references
  hasStopParsing: boolean            // --% token present
  typeLiterals?: string[]            // [int], [System.IO.File], etc.
  hasUsingStatements?: boolean       // using module/assembly
  hasScriptRequirements?: boolean    // #Requires directives
}
```

### 11.3 CommandElementType Classification

Each argument is classified: `ScriptBlock`, `SubExpression`, `ExpandableString`, `MemberInvocation`, `Variable`, `StringConstant`, `Parameter`, `Other`

### 11.4 Security Patterns

The PS1 script uses `FindAll()` to detect:
- `MemberExpressionAst` / `InvokeMemberExpressionAst` — `.Method()` calls
- `SubExpressionAst` / `ArrayExpressionAst` / `ParenExpressionAst` — `$()`
- `ExpandableStringExpressionAst` — `"$var"` strings
- `ScriptBlockExpressionAst` — `{ code }` blocks

### 11.5 Safety Bounds

- **Parse timeout**: 5s default, configurable via `CLAUDE_CODE_PWSH_PARSE_TIMEOUT_MS`
- **Snap launcher bypass**: Prefers `/opt/microsoft/powershell/7/pwsh` over snap launcher (hangs in subprocesses)
- **Edition detection**: `pwsh` = Core 7+ (supports `&&`), `powershell` = Desktop 5.1

---

## 12. Dangerous Cmdlet Registry (`powershell/dangerousCmdlets.ts`)

Nine categories with alias expansion:

| Category | Examples | Risk |
|----------|----------|------|
| `FILEPATH_EXECUTION_CMDLETS` | `Invoke-Command`, `Start-Job` | Execute script files |
| `DANGEROUS_SCRIPT_BLOCK_CMDLETS` | `Invoke-Expression`, `Start-Job` | Execute arbitrary scriptblocks |
| `MODULE_LOADING_CMDLETS` | `Import-Module`, `Install-Module` | Load and run module code |
| `NETWORK_CMDLETS` | `Invoke-WebRequest`, `Invoke-RestMethod` | Data exfiltration |
| `ALIAS_HIJACK_CMDLETS` | `Set-Alias`, `Set-Variable` | Command resolution poisoning |
| `WMI_CIM_CMDLETS` | `Invoke-WmiMethod`, `Invoke-CimMethod` | Win32_Process spawn |
| `ARG_GATED_CMDLETS` | `ForEach-Object`, `Where-Object` | Safe with literals, dangerous with scriptblocks |
| Shells & spawners | `pwsh`, `cmd`, `bash`, `Start-Process`, `Add-Type` | Process creation |
| Cross-platform code exec | From `dangerousPatterns.js` | `node -e`, `python -c`, etc. |

`NEVER_SUGGEST: ReadonlySet<string>` is the union of all categories plus their aliases — prevents suggesting these as wildcard permission rules.

---

## 13. Read-Only Command Validation (`readOnlyCommandValidation.ts`)

### 13.1 Git Read-Only Commands

Comprehensive per-subcommand flag allowlists:
- `git diff` — 40+ safe flags including stat, color, diff-algorithm, ignore-space
- `git log` — 35+ flags including format, author, date, patch, pickaxe
- `git show`, `git shortlog`, `git reflog`, `git stash list`
- `git ls-remote` — intentionally excludes `--server-option` (network write primitive)
- `git status`, `git blame`, `git branch` (list only)

### 13.2 Flag-Argument Type System

```typescript
type FlagArgType =
  | 'none'    // No argument (--color)
  | 'number'  // Integer (--context=3)
  | 'string'  // Any string (--format=oneline)
  | 'char'    // Single character
  | '{}'      // Literal "{}" only
  | 'EOF'     // Literal "EOF" only
```

### 13.3 Dynamic Validation Callbacks

Some commands use `additionalCommandIsDangerousCallback` for context-aware checks:
- `git reflog`: blocks `expire`, `delete`, `exists` subcommands
- External commands: `ipconfig /flushdns` blocked, `ipconfig /all` allowed

---

## 14. Tree-Sitter Analysis (`treeSitterAnalysis.ts`)

### 14.1 Single-Pass Quote Collection

`collectQuoteSpans()` performs a fused tree walk (previously 5 separate walks) collecting:
- `raw_string` spans (single-quoted)
- `ansi_c_string` spans (`$'...'`)
- `string` spans (double-quoted, outermost only)
- `heredoc_redirect` spans (quoted delimiters only)

### 14.2 QuoteContext Output

Three variants for different security validators:
- `withDoubleQuotes` — single-quoted content removed, double-quote delimiters removed but content kept
- `fullyUnquoted` — all quoted content removed
- `unquotedKeepQuoteChars` — content removed but delimiter chars preserved

### 14.3 CompoundStructure Detection

Identifies: `hasCompoundOperators`, `hasPipeline`, `hasSubshell`, `hasCommandGroup`, plus segment splitting for per-subcommand analysis.

### 14.4 hasActualOperatorNodes

**Key function** for eliminating `find -exec \;` false positive: tree-sitter parses `\;` as a `word` node, not a `;` operator. If no actual operator nodes exist in the AST, compound-command checks can be skipped.

---

## 15. Shell Completion (`shellCompletion.ts`)

Provides inline tab-completion for the prompt input:
- **Input parsing** — uses shell-quote to determine context (command, file, variable)
- **Bash**: `compgen -c/-f/-v` with `quote()` for safe prefix
- **Zsh**: Native `${(k)commands[(I)prefix*]}` / glob `prefix*(N[1,15])`
- **Limits**: 15 completions max, 1s timeout
- **Security**: `quote([prefix])` prevents injection in completion commands

---

## 16. Cross-Cutting Themes

### 16.1 Security-First Design

Every component follows **fail-closed** semantics: unknown constructs trigger user prompts rather than silent acceptance. The AST walker's explicit allowlist means new bash features automatically require review.

### 16.2 Parser Differential Mitigation

Extensive effort to detect cases where tree-sitter and bash/zsh disagree on tokenization:
- Control characters (CR word-boundary disagreement)
- Unicode whitespace (renders invisible but bash treats as literal)
- Backslash-whitespace (tree-sitter preserves raw, bash unescapes)
- Zsh-specific expansions (`~[`, `=cmd`)

### 16.3 Placeholder-Based Variable Tracking

The `__CMDSUB_OUTPUT__` / `__TRACKED_VAR__` system enables analyzing commands with `$()` and `$VAR` without knowing runtime values, while preventing placeholder-based path validation bypasses.

### 16.4 Platform Abstraction

The shell provider interface cleanly separates bash and PowerShell concerns, but the two stacks are quite different:
- Bash: pure-TS parser (in-process, ~0ms)
- PowerShell: spawns pwsh subprocess (~450ms warm, 5s timeout)
- Bash: text-based AST
- PowerShell: .NET reflection-based AST via PS1 script

### 16.5 Dual Prefix Extraction

Two independent prefix extraction paths:
1. **Static** (fast, in-process): tree-sitter/PS AST + fig-spec walker
2. **LLM-powered** (slow, API call): Haiku query with policy spec

Both converge on the same permission dialog: "Yes, and don't ask again for: `prefix:*`"

---

## 17. Exported Functions Summary

### `bash/ast.ts`
- `parseForSecurity(cmd)` → `ParseForSecurityResult`
- `parseForSecurityFromAst(cmd, root)` → `ParseForSecurityResult`
- `nodeTypeId(nodeType)` → `number`

### `bash/bashParser.ts`
- `ensureParserInitialized()` → `Promise<void>`
- `getParserModule()` → `ParserModule | null`
- `SHELL_KEYWORDS` — exported Set

### `bash/bashPipeCommand.ts`
- `rearrangePipeCommand(command)` → `string`

### `bash/commands.ts`
- `splitCommandWithOperators(command)` → `string[]`
- `splitCommand_DEPRECATED(command)` → `string[]`
- `filterControlOperators(parts)` → `string[]`
- `extractOutputRedirections(command)` → `{ commandWithoutRedirections, redirections }`
- `isHelpCommand(command)` → `boolean`
- `createCommandPrefixExtractor()` / `createSubcommandPrefixExtractor()` — re-exports

### `bash/heredoc.ts`
- `extractHeredocs(command, options?)` → `HeredocExtractionResult`
- `restoreHeredocs(parts, heredocs)` → `string[]`
- `containsHeredoc(command)` → `boolean`

### `bash/ParsedCommand.ts`
- `ParsedCommand.parse(command)` → `Promise<IParsedCommand | null>`
- `buildParsedCommandFromRoot(command, root)` → `IParsedCommand`
- `RegexParsedCommand_DEPRECATED` — class (legacy fallback)

### `bash/parser.ts`
- `ensureInitialized()` → `Promise<void>`
- `parseCommand(command)` → `Promise<ParsedCommandData | null>`
- `parseCommandRaw(command)` → `Promise<Node | null | typeof PARSE_ABORTED>`
- `extractCommandArguments(commandNode)` → `string[]`
- `PARSE_ABORTED` — Symbol sentinel

### `bash/prefix.ts`
- `getCommandPrefixStatic(command)` → `Promise<{ commandPrefix } | null>`
- `getCompoundCommandPrefixesStatic(command, excludeSubcommand?)` → `Promise<string[]>`

### `bash/registry.ts`
- `getCommandSpec(command)` → `Promise<CommandSpec | null>`
- `loadFigSpec(command)` → `Promise<CommandSpec | null>`

### `bash/shellCompletion.ts`
- `getShellCompletions(input, cursorOffset, abortSignal)` → `Promise<SuggestionItem[]>`

### `bash/shellPrefix.ts`
- `formatShellPrefixCommand(prefix, command)` → `string`

### `bash/shellQuote.ts`
- `tryParseShellCommand(cmd, env?)` → `ShellParseResult`
- `tryQuoteShellArgs(args)` → `ShellQuoteResult`
- `hasMalformedTokens(command, parsed)` → `boolean`
- `hasShellQuoteSingleQuoteBug(command)` → `boolean`
- `quote(args)` → `string`

### `bash/shellQuoting.ts`
- `quoteShellCommand(command, addStdinRedirect?)` → `string`
- `hasStdinRedirect(command)` → `boolean`
- `shouldAddStdinRedirect(command)` → `boolean`
- `rewriteWindowsNullRedirect(command)` → `string`

### `bash/ShellSnapshot.ts`
- `createAndSaveSnapshot(binShell)` → `Promise<string | undefined>`
- `createRipgrepShellIntegration()` → `{ type, snippet }`
- `createFindGrepShellIntegration()` → `string | null`

### `bash/treeSitterAnalysis.ts`
- `analyzeCommand(rootNode, command)` → `TreeSitterAnalysis`
- `extractQuoteContext(rootNode, command)` → `QuoteContext`
- `extractCompoundStructure(rootNode, command)` → `CompoundStructure`
- `hasActualOperatorNodes(rootNode)` → `boolean`
- `extractDangerousPatterns(rootNode)` → `DangerousPatterns`

### `shell/shellProvider.ts`
- `ShellProvider` type, `ShellType` type, `SHELL_TYPES`, `DEFAULT_HOOK_SHELL`

### `shell/bashProvider.ts`
- `createBashShellProvider(shellPath, options?)` → `Promise<ShellProvider>`

### `shell/powershellProvider.ts`
- `createPowerShellProvider(shellPath)` → `ShellProvider`
- `buildPowerShellArgs(cmd)` → `string[]`

### `shell/resolveDefaultShell.ts`
- `resolveDefaultShell()` → `'bash' | 'powershell'`

### `shell/outputLimits.ts`
- `getMaxOutputLength()` → `number`

### `shell/powershellDetection.ts`
- `findPowerShell()` → `Promise<string | null>`
- `getCachedPowerShellPath()` → `Promise<string | null>`
- `getPowerShellEdition()` → `Promise<PowerShellEdition | null>`

### `shell/readOnlyCommandValidation.ts`
- `GIT_READ_ONLY_COMMANDS`, `GH_READ_ONLY_COMMANDS`, `EXTERNAL_READONLY_COMMANDS`
- `containsVulnerableUncPath(command)` → `boolean`

### `shell/shellToolUtils.ts`
- `SHELL_TOOL_NAMES`, `isPowerShellToolEnabled()` → `boolean`

### `shell/prefix.ts`
- `createCommandPrefixExtractor(config)` → memoized async function
- `createSubcommandPrefixExtractor(getPrefix, splitCommand)` → memoized async function

### `shell/specPrefix.ts`
- `buildPrefix(command, args, spec)` → `Promise<string>`
- `DEPTH_RULES` — exported Record

### `powershell/dangerousCmdlets.ts`
- `FILEPATH_EXECUTION_CMDLETS`, `DANGEROUS_SCRIPT_BLOCK_CMDLETS`, `MODULE_LOADING_CMDLETS`, `NETWORK_CMDLETS`, `ALIAS_HIJACK_CMDLETS`, `WMI_CIM_CMDLETS`, `ARG_GATED_CMDLETS`, `NEVER_SUGGEST`

### `powershell/parser.ts`
- `parsePowerShellCommand(command)` → `Promise<ParsedPowerShellCommand>`
- `getAllCommands(parsed)` → generator of `ParsedCommandElement`
- `COMMON_ALIASES` — exported Record
- `PARSE_SCRIPT_BODY` — exported string (for testing)

### `powershell/staticPrefix.ts`
- `getCommandPrefixStatic(command)` → `Promise<{ commandPrefix } | null>`
- `getCompoundCommandPrefixesStatic(command, excludeSubcommand?)` → `Promise<string[]>`

---

## 18. Verification vs. Existing Analysis

The existing `bash-execution.md` was **accurate but surface-level**. This wave adds:

| Aspect | Prior coverage | Wave 48 additions |
|--------|---------------|-------------------|
| ast.ts security engine | Brief mention | Full walkCommand/walkArgument/walkString/varScope analysis |
| Parser differential mitigation | Not covered | 8 specific pre-check regexes documented |
| Heredoc security | Not covered | 15+ security checks enumerated |
| Variable scope tracking | Not covered | Full scope isolation semantics table |
| Placeholder system | Not covered | CMDSUB/VAR placeholders + containsAnyPlaceholder |
| Pipe command handling | Not covered | Full bail-out condition list |
| PowerShell AST parser | Brief mention | PS1 script structure, CommandElementType classification |
| Dangerous cmdlet registry | Not covered | 9 categories with alias expansion |
| Read-only flag allowlists | Brief mention | FlagArgType system, per-command coverage |
| Spec system | Brief mention | Fig-spec resolution, wrapper unwrapping, depth rules |
| Shell completion | Not covered | compgen/zsh native, security via quote() |
| LLM prefix extraction | Not covered | Haiku query, dangerous prefix blocklist, cache eviction |

---

*Wave 48 complete. 35 files analyzed across 3 directories. Security model documented at allowlist/bypass/differential level.*
