# Skill System

> Source: `src/skills/`, `src/tools/SkillTool/`, `src/utils/skills/`

## Overview

Skills are named prompt-based commands invoked by the model via `SkillTool`, or by users via `/skill-name`. They are Claude Code's primary extensibility mechanism — reusable task prompts with optional tool restrictions, model overrides, and reference files.

## Architecture

```
User or Model invokes /skill-name or SkillTool
    ↓
Command Registry (src/commands.ts)
    ↓
┌──────────────────────────────────┐
│ Skill sources (priority order):  │
│  1. MCP skills (mcpSkillBuilders)│
│  2. Project (.claude/commands/)  │
│  3. User (~/.claude/commands/)   │
│  4. Bundled skills (compiled-in) │
└──────────────────────────────────┘
    ↓
SkillTool → runAgent() → API call with skill prompt
```

## BundledSkillDefinition (`src/skills/bundledSkills.ts`)

```typescript
type BundledSkillDefinition = {
  name: string, description: string, aliases?: string[],
  whenToUse?: string, argumentHint?: string,
  allowedTools?: string[], model?: string,
  disableModelInvocation?: boolean, userInvocable?: boolean,
  isEnabled?: () => boolean, hooks?: HooksSettings,
  context?: 'inline' | 'fork', agent?: string,
  files?: Record<string, string>,  // reference files extracted to disk
  getPromptForCommand: (args, context) => Promise<ContentBlockParam[]>
}
```

### Reference Files (`files` field)
Files are lazily extracted to disk with:
- Per-process nonce directory (TOCTOU-safe)
- `O_EXCL | O_NOFOLLOW` flags (prevent symlink attacks)
- Directory path prepended to skill prompt
- Extraction memoized per-process

## Bundled Skills (`src/skills/bundled/`)

| Skill | Purpose |
|-------|---------|
| `update-config` | Configuration management |
| `keybindings` | Keyboard shortcut config |
| `verify` | Code verification |
| `debug` | Debugging assistance |
| `lorem-ipsum` | Placeholder text |
| `skillify` | Create skills from descriptions |
| `remember` | Save to memory |
| `simplify` | Simplify content |
| `batch` | Batch operations |
| `stuck` | Help when stuck |
| Feature-gated: `dream`, `hunter`, `loop`, `scheduleRemoteAgents`, `claudeApi`, `claudeInChrome` | Internal/flagged |

## Disk Skill Loading (`src/skills/loadSkillsDir.ts`)

Loads `.md` files from skill directories:
1. Scan `<project-root>/.claude/commands/` (project-local)
2. Scan `~/.claude/commands/` (user-global)
3. Respect `.gitignore` via `isPathGitignored()`
4. Parse frontmatter: description, allowed-tools, model, argument-hint
5. Execute shell commands in frontmatter (dynamic content)
6. Project skills override user skills of same name
7. Memoized per session ID

### Markdown Frontmatter Format

```yaml
---
description: "What this skill does"
allowed-tools: [Bash, Read, Write, Edit]
model: claude-sonnet-4-5
argument-hint: "<file> [options]"
when-to-use: "Use when..."
context: inline    # or 'fork'
user-invocable: true
---

Skill prompt body. Use $ARGUMENTS for user args.
```

## MCP Skills (`src/skills/mcpSkillBuilders.ts`)

MCP servers expose "prompts" which become skills with `source: 'mcp'`.

## SkillTool (`src/tools/SkillTool/SkillTool.ts`)

AI-invokable tool: `SKILL_TOOL_NAME = 'Task'`

```typescript
input: { description: string, prompt: string }
```

| Mode | Behavior |
|------|---------|
| `context: 'inline'` | Runs in current conversation |
| `context: 'fork'` | Spawns isolated sub-agent |

### Permission & Analytics
- `getRuleByContentsForTool()` checks rules against skill content
- `allowedTools` frontmatter restricts tool access
- `addInvokedSkill()` / `recordSkillUsage()` for tracking
- Plugin telemetry for marketplace skills

## Skill Change Detection (`src/utils/skills/skillChangeDetector.ts`)

`fs.watch` on `.claude/commands/` for hot-reload during development.

## Security

1. Path traversal prevention in `resolveSkillFilePath()`
2. TOCTOU-safe extraction with `O_EXCL | O_NOFOLLOW`
3. `0o700`/`0o600` permissions
4. Allowed tools restriction via frontmatter
5. `isInProtectedNamespace()` prevents loading from sensitive dirs
