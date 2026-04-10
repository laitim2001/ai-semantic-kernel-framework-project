# Git Integration

> Analysis of Claude Code's git operations, filesystem-based git state reading, GitHub integration, and branch management.

## Overview

Claude Code's git integration spans three layers: filesystem-based git state reading (avoiding subprocess spawns), shell-based git operations through the Bash tool, and GitHub API integration. The system prioritizes performance by reading `.git/` directly and security by validating ref names against injection attacks.

**Key source files:**
- `src/utils/git/gitFilesystem.ts` — Filesystem-based git state (HEAD, refs, branch watcher)
- `src/utils/git/gitConfigParser.ts` — Git config file parser
- `src/utils/git/gitignore.ts` — Gitignore pattern handling
- `src/utils/github/ghAuthStatus.ts` — GitHub CLI auth status
- `src/tools/BashTool/` — Git commands execute through the Bash tool
- `src/tools/shared/gitOperationTracking.ts` — Git operation tracking

---

## Filesystem-Based Git State

### Design Philosophy

`src/utils/git/gitFilesystem.ts` reads git state directly from the filesystem rather than spawning `git` subprocesses. This is significantly faster for frequent operations like branch detection and SHA resolution.

Correctness is verified against git source code:
- **HEAD:** `ref: refs/heads/<branch>\n` or raw SHA (`refs/files-backend.c`)
- **Packed-refs:** `<sha> <refname>\n`, skip `#` and `^` lines (`packed-backend.c`)
- **.git file (worktree):** `gitdir: <path>\n` with optional relative path (`setup.c`)
- **Shallow:** Mere existence of `<commonDir>/shallow` means shallow (`shallow.c`)

### resolveGitDir

Resolves the actual `.git` directory, handling worktrees and submodules:

```typescript
async function resolveGitDir(startPath?: string): Promise<string | null>
```

1. Calls `findGitRoot(cwd)` to locate the repository root
2. Stats `<root>/.git`:
   - If **directory** → regular repo, returns path directly
   - If **file** → worktree/submodule, parses `gitdir: <path>` content
3. Resolves relative `gitdir` paths against the repo root
4. Results are **memoized** per start path (`resolveGitDirCache`)

### Ref Name Validation (Security)

`isSafeRefName(name)` validates ref/branch names read from `.git/`:

**Threat model:** An attacker controlling `.git/HEAD` or a loose ref file could embed:
- Path traversal (`..`)
- Argument injection (leading `-`)
- Shell metacharacters (backticks, `$`, `;`, `|`, `&`, etc.)

**Allowlist approach:** Only ASCII alphanumerics, `/`, `.`, `_`, `+`, `-`, `@` are permitted. This covers all legitimate git branch names while rejecting dangerous characters.

```typescript
function isSafeRefName(name: string): boolean {
  if (!name || name.startsWith('-') || name.startsWith('/')) return false
  // Regex: only safe characters, no '..' path traversal
  return /^[a-zA-Z0-9/._+\-@]+$/.test(name) && !name.includes('..')
}
```

### GitHeadWatcher

A file system watcher that monitors `.git/HEAD` for branch/SHA changes:
- Uses `fs.watchFile` (polling-based, works across all platforms)
- Caches the current branch name and commit SHA
- Notifies subscribers when the HEAD changes (branch switch, new commit)
- Handles worktree-specific HEAD files

---

## Git Config Parser

`src/utils/git/gitConfigParser.ts` provides `parseGitConfigValue()` for extracting values from git config files without spawning `git config`:

- Handles section headers `[section "subsection"]`
- Supports multi-line values with backslash continuation
- Parses boolean values (`true`/`false`/`yes`/`no`)

---

## Gitignore Handling

`src/utils/git/gitignore.ts` handles `.gitignore` pattern matching:

- Used by file search tools (Glob, Grep) to exclude ignored files
- Respects nested `.gitignore` files in subdirectories
- Integrates with the file indexing system for efficient filtering

---

## GitHub Integration

### GitHub Auth Status

`src/utils/github/ghAuthStatus.ts` provides:

```typescript
function ghAuthStatus(): Promise<{ authenticated: boolean, user?: string }>
```

Checks if the GitHub CLI (`gh`) is authenticated by running `gh auth status`. Used to:
- Gate GitHub-dependent features (PR creation, issue management)
- Display authentication status in the UI
- Determine available capabilities for git-related agents

### Git Operation Tracking

`src/tools/shared/gitOperationTracking.ts` provides `trackGitOperations()`:

- Monitors Bash tool invocations for git commands
- Tracks which git operations the model performs (commit, push, branch, etc.)
- Used for analytics and to detect when the model is performing git workflows
- Enables automatic git status updates in the UI after git operations

---

## Git Operations via Bash Tool

Git commands execute through the Bash tool (`src/tools/BashTool/BashTool.tsx`). The tool has specific awareness of git:

### Command Classification

The Bash tool classifies git commands for UI and permission purposes:
- **Read commands:** `git status`, `git log`, `git diff`, `git branch`, `git show` — typically auto-approved
- **Write commands:** `git add`, `git commit`, `git push`, `git checkout` — may require permission
- **Destructive commands:** `git reset --hard`, `git push --force` — flagged by security analysis

### Security Analysis Integration

`parseForSecurity()` from `src/utils/bash/ast.ts` analyzes git commands for:
- Force push detection
- Hard reset detection  
- Branch deletion
- Potentially dangerous flag combinations

### Git-Aware Features

- **CWD tracking:** The Bash tool tracks when `cd` commands change directory and updates git context
- **File modification detection:** After git operations, the system can detect file changes
- **Commit message generation:** Agents generate commit messages based on staged changes
- **Branch management:** Agents create feature branches, switch branches, manage worktrees

---

## Worktree Support

Git worktrees are a first-class concept in Claude Code:

### Agent Worktree Isolation

Agents can run in isolated worktrees via `isolation: 'worktree'`:
1. A temporary worktree is created from the current branch
2. The agent operates in the worktree directory
3. Changes are isolated from the main working copy
4. On completion: if changes were made, the worktree path and branch are returned
5. If no changes: worktree is automatically cleaned up

### Fork Worktree Notice

When a fork subagent runs in a worktree, `buildWorktreeNotice()` injects guidance:
- Inherited context paths refer to the parent's working directory
- The agent must translate paths to its worktree root
- Files should be re-read before editing (parent may have modified them)
- Changes stay in the worktree and won't affect parent's files

### resolveGitDir Worktree Handling

`resolveGitDir()` transparently handles worktrees where `.git` is a file containing `gitdir: <path>` rather than being a directory. This ensures all git filesystem operations work correctly regardless of whether the cwd is a regular repo or a worktree.

---

## Key Design Patterns

1. **Filesystem-first** — Read `.git/` directly instead of spawning `git` subprocesses for performance
2. **Security validation** — Ref names validated against injection attacks before use in paths/shell
3. **Memoization** — Git dir resolution cached per path to avoid repeated filesystem traversal
4. **Platform compatibility** — `fs.watchFile` polling works across all OS platforms
5. **Worktree transparency** — All operations handle regular repos and worktrees uniformly
6. **Git source verification** — Implementation validated against git C source code for correctness
7. **Layered integration** — Filesystem reading for state, Bash tool for operations, GitHub CLI for API
