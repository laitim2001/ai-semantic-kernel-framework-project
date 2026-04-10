# Keybinding System

> Source: `src/keybindings/` (14 files)

## Overview

Claude Code implements a fully configurable keyboard shortcut system with context-scoped bindings, user overrides via `keybindings.json`, chord sequences, platform-specific defaults, and file watcher for hot-reload.

## Architecture

```
User keypress (raw terminal input)
    ↓
KeybindingProviderSetup (loads + watches keybindings.json)
    ↓
KeybindingContext (React context with parsed bindings)
    ↓
useKeybinding(action, handler) / useKeybindings(map)
    ↓
resolveKey(input, key, activeContexts, bindings)
    ↓
Action string → handler function called
```

## Core Files

| File | Role |
|------|------|
| `defaultBindings.ts` | `DEFAULT_BINDINGS` — all built-in shortcuts |
| `schema.ts` | Zod schema, `KEYBINDING_CONTEXTS` (17), `KEYBINDING_ACTIONS` (70+) |
| `loadUserBindings.ts` | Load/validate/watch `keybindings.json` |
| `KeybindingContext.tsx` | React context providing parsed bindings |
| `KeybindingProviderSetup.tsx` | Provider — loads and hot-reloads |
| `useKeybinding.ts` | `useKeybinding()`, `useKeybindings()` hooks |
| `resolver.ts` | `resolveKey()` — pure matching function |
| `match.ts` | `matchesBinding()` — keystroke comparison |
| `parser.ts` | Parses `"ctrl+k"` → `ParsedKeystroke[]` |
| `reservedShortcuts.ts` | Non-rebindable shortcuts |
| `validate.ts` | User config validation |

## Contexts (`src/keybindings/schema.ts`)

17 contexts: `Global`, `Chat`, `Autocomplete`, `Confirmation`, `Help`, `Transcript`, `HistorySearch`, `Task`, `ThemePicker`, `Settings`, `Tabs`, `Attachments`, `Footer`, `MessageSelector`, `DiffDialog`, `ModelPicker`, `Select`, `Plugin`

## Key Default Bindings

### Global Context
| Key | Action |
|-----|--------|
| `ctrl+c` | `app:interrupt` (reserved, double-press exits) |
| `ctrl+d` | `app:exit` (reserved) |
| `ctrl+l` | `app:redraw` |
| `ctrl+r` | `history:search` |

### Chat Context
| Key | Action |
|-----|--------|
| `enter` | `chat:submit` |
| `escape` | `chat:cancel` |
| `shift+tab` / `meta+m` | `chat:cycleMode` (prompt/bash/auto) |
| `meta+p` | `chat:modelPicker` |
| `meta+o` | `chat:fastMode` |
| `meta+t` | `chat:thinkingToggle` |
| `ctrl+x ctrl+e` / `ctrl+g` | `chat:externalEditor` |
| `ctrl+s` | `chat:stash` |
| `ctrl+v` / `alt+v` (Win) | `chat:imagePaste` |

### Platform-Specific
- Image paste: Windows uses `alt+v` (ctrl+v is system paste)
- Mode cycle: Windows without VT mode uses `meta+m` (shift+tab unreliable pre-Node 22.17.0)

## keybindings.json Format

```json
{
  "bindings": [{
    "context": "Chat",
    "bindings": {
      "ctrl+k": "chat:cancel",
      "ctrl+t": null
    }
  }]
}
```

- `null` unbinds a default shortcut
- `"command:name"` executes a slash command
- User bindings merged after defaults (last wins)

## Loading Pipeline (`src/keybindings/loadUserBindings.ts`)

1. Parse `getDefaultParsedBindings()`
2. Check `isKeybindingCustomizationEnabled()`
3. Read `~/.claude/keybindings.json`
4. Validate via `KeybindingsSchema` (Zod)
5. Check against reserved shortcuts
6. Merge: user appended after defaults

### Hot Reload
`fs.watch` on keybindings file → `handleChange()` → reload → `keybindingsChanged.emit()`. Components subscribe via `subscribeToKeybindingChanges`.

## Key Resolver (`src/keybindings/resolver.ts`)

```typescript
resolveKey(input, key, activeContexts, bindings)
  → { type: 'match', action } | { type: 'none' } | { type: 'unbound' }
```

- Filter by `activeContexts` set
- Last binding wins (user overrides)
- `action === null` → `'unbound'` (swallows event)
- `'none'` → other handlers can process

### Chord Support (partial)

```typescript
type ChordResolveResult =
  | { type: 'match'; action }
  | { type: 'none' }
  | { type: 'unbound' }
  | { type: 'chord_started'; pending: ParsedKeystroke[] }
  | { type: 'chord_cancelled' }
```

Already used: `ctrl+x ctrl+e` (external editor).

## Hooks (`src/keybindings/useKeybinding.ts`)

```typescript
useKeybinding(action, handler, { isActive? })   // single
useKeybindings(map, { isActive? })               // multiple
```

Internally calls `useInput` with wrapper: `resolveKey()` → match → call handler.

## Reserved Shortcuts

`ctrl+c` and `ctrl+d` cannot be rebound — special double-press handling.

## Integration with PromptInput

```typescript
useKeybindings({
  'chat:submit': handleSubmit,
  'chat:cancel': handleCancel,
  'chat:cycleMode': handleCycleMode,
  // ... separates key→action (configurable) from action→handler (fixed)
})
```
