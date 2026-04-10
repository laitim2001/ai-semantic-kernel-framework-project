# Vim Mode Implementation

> Claude Code implements a comprehensive vim emulation layer for its terminal text input, built as a pure state machine with full operator-motion composition.

## Overview

The vim mode provides a faithful emulation of vim's normal-mode editing commands within the Claude Code prompt input. It is implemented as a clean state machine architecture with separated concerns: types define the state space, transitions define the state graph, motions provide pure cursor calculations, operators execute editing commands, and text objects handle structural selection.

**Key source files:**

| File | Purpose |
|------|---------|
| `src/vim/types.ts` | Complete state machine type definitions + key constants |
| `src/vim/transitions.ts` | State transition table — the vim command parser |
| `src/vim/motions.ts` | Pure cursor motion resolution functions |
| `src/vim/operators.ts` | Operator execution (delete, change, yank, etc.) |
| `src/vim/textObjects.ts` | Text object boundary finding (iw, aw, i", a(, etc.) |

## State Machine Architecture

### State Diagram

```
                           VimState
  ┌──────────────────────────┬──────────────────────────────────────┐
  │  INSERT                  │  NORMAL                              │
  │  (tracks insertedText)   │  (CommandState machine)              │
  │                          │                                      │
  │                          │  idle ──┬─[d/c/y]──► operator        │
  │                          │         ├─[1-9]────► count           │
  │                          │         ├─[fFtT]───► find            │
  │                          │         ├─[g]──────► g               │
  │                          │         ├─[r]──────► replace         │
  │                          │         └─[><]─────► indent          │
  │                          │                                      │
  │                          │  operator ─┬─[motion]──► execute     │
  │                          │            ├─[0-9]────► operatorCount│
  │                          │            ├─[ia]─────► operatorTextObj│
  │                          │            └─[fFtT]───► operatorFind │
  └──────────────────────────┴──────────────────────────────────────┘
```

### Core Types (`types.ts`)

The top-level state discriminates on mode:

```typescript
export type VimState =
  | { mode: 'INSERT'; insertedText: string }   // tracks text for dot-repeat
  | { mode: 'NORMAL'; command: CommandState }   // state machine
```

The `CommandState` is an 11-variant discriminated union covering every intermediate parsing state:

```typescript
export type CommandState =
  | { type: 'idle' }
  | { type: 'count'; digits: string }
  | { type: 'operator'; op: Operator; count: number }
  | { type: 'operatorCount'; op: Operator; count: number; digits: string }
  | { type: 'operatorFind'; op: Operator; count: number; find: FindType }
  | { type: 'operatorTextObj'; op: Operator; count: number; scope: TextObjScope }
  | { type: 'find'; find: FindType; count: number }
  | { type: 'g'; count: number }
  | { type: 'operatorG'; op: Operator; count: number }
  | { type: 'replace'; count: number }
  | { type: 'indent'; dir: '>' | '<'; count: number }
```

### Persistent State

Survives across commands for repeats and register operations:

```typescript
export type PersistentState = {
  lastChange: RecordedChange | null   // for dot-repeat
  lastFind: { type: FindType; char: string } | null  // for ; and ,
  register: string                    // yank/delete buffer
  registerIsLinewise: boolean         // paste behavior flag
}
```

### Recorded Changes (Dot-Repeat)

A discriminated union capturing everything needed to replay a command:

```typescript
export type RecordedChange =
  | { type: 'insert'; text: string }
  | { type: 'operator'; op: Operator; motion: string; count: number }
  | { type: 'operatorTextObj'; op: Operator; objType: string; scope: TextObjScope; count: number }
  | { type: 'operatorFind'; op: Operator; find: FindType; char: string; count: number }
  | { type: 'replace'; char: string; count: number }
  | { type: 'x'; count: number }
  | { type: 'toggleCase'; count: number }
  | { type: 'indent'; dir: '>' | '<'; count: number }
  | { type: 'openLine'; direction: 'above' | 'below' }
  | { type: 'join'; count: number }
```

## Transition System (`transitions.ts`)

### Main Dispatcher

The transition function dispatches based on current state type:

```typescript
export function transition(
  state: CommandState,
  input: string,
  ctx: TransitionContext,
): TransitionResult {
  switch (state.type) {
    case 'idle':          return fromIdle(input, ctx)
    case 'count':         return fromCount(state, input, ctx)
    case 'operator':      return fromOperator(state, input, ctx)
    case 'operatorCount': return fromOperatorCount(state, input, ctx)
    // ... all 11 states handled exhaustively
  }
}
```

### TransitionResult

Each transition produces either a state change, an execution, or both:

```typescript
export type TransitionResult = {
  next?: CommandState     // new state (undefined = reset to idle)
  execute?: () => void    // side-effect to perform
}
```

### Supported Normal Mode Commands

**Movement:**
| Key | Action |
|-----|--------|
| `h/l/j/k` | Left/right/down/up (logical lines for j/k) |
| `w/b/e` | Word forward/backward/end |
| `W/B/E` | WORD forward/backward/end |
| `0/^/$` | Line start/first non-blank/line end |
| `G` | Go to last line (or line N with count) |
| `gg` | Go to first line (or line N with count) |
| `gj/gk` | Down/up by visual (wrapped) lines |
| `f/F/t/T` + char | Find character forward/backward (to/till) |
| `;/,` | Repeat/reverse last find |

**Operators (composable with motions):**
| Key | Action |
|-----|--------|
| `d` + motion | Delete |
| `c` + motion | Change (delete + enter insert) |
| `y` + motion | Yank (copy) |
| `dd/cc/yy` | Line-wise operations |
| `D/C/Y` | Shorthand line operations |

**Text Objects (with operators):**
| Key | Scope | Objects |
|-----|-------|---------|
| `i` | Inner | `w/W` words, `"/'` quotes, `(/)/b` parens, `[/]` brackets, `{/}/B` braces, `</>` angles |
| `a` | Around | Same as inner, includes delimiters/surrounding whitespace |

**Editing:**
| Key | Action |
|-----|--------|
| `x` | Delete character |
| `r` + char | Replace character |
| `~` | Toggle case |
| `J` | Join lines |
| `p/P` | Paste after/before |
| `>>/<<` | Indent/outdent |
| `o/O` | Open line below/above |
| `.` | Dot-repeat last change |
| `u` | Undo |

**Mode switching:**
| Key | Action |
|-----|--------|
| `i` | Insert at cursor |
| `I` | Insert at first non-blank |
| `a` | Append after cursor |
| `A` | Append at end of line |

### Count System

Counts work at two levels and multiply:
1. **Pre-operator count**: `3dw` = delete 3 words
2. **Post-operator count**: `d3w` = same thing
3. **Combined**: `2d3w` = delete 6 words

The count is capped at `MAX_VIM_COUNT = 10000` to prevent runaway operations.

## Motion System (`motions.ts`)

### Pure Motion Resolution

Motions are pure functions that compute a target cursor position:

```typescript
export function resolveMotion(key: string, cursor: Cursor, count: number): Cursor {
  let result = cursor
  for (let i = 0; i < count; i++) {
    const next = applySingleMotion(key, result)
    if (next.equals(result)) break  // stuck = stop early
    result = next
  }
  return result
}
```

### Motion Classification

```typescript
export function isInclusiveMotion(key: string): boolean {
  return 'eE$'.includes(key)  // includes character at destination
}

export function isLinewiseMotion(key: string): boolean {
  return 'jkG'.includes(key) || key === 'gg'  // operates on full lines
}
```

Note: `gj`/`gk` are character-wise exclusive per `:help gj`, not linewise.

## Operator System (`operators.ts`)

### Operator Context

The execution environment provided to all operators:

```typescript
export type OperatorContext = {
  cursor: Cursor
  text: string
  setText: (text: string) => void
  setOffset: (offset: number) => void
  enterInsert: (offset: number) => void
  getRegister: () => string
  setRegister: (content: string, linewise: boolean) => void
  getLastFind: () => { type: FindType; char: string } | null
  setLastFind: (type: FindType, char: string) => void
  recordChange: (change: RecordedChange) => void
}
```

### Operator Range Calculation

The `getOperatorRange()` function handles the complex logic of determining what text an operator affects:

- **Linewise motions** (`j/k/G/gg`): Extend to include entire lines, with special handling for last-line deletion
- **Inclusive motions** (`e/E/$`): Include the character at the destination
- **Special case `cw/cW`**: Changes to end of word, not start of next word (vim convention)
- **Image chip snapping**: `cursor.snapOutOfImageRef()` ensures operators never leave partial `[Image #N]` placeholders

### Line Operations (`executeLineOp`)

Handles `dd`, `cc`, `yy` with proper:
- Multi-line count support
- Linewise register content (always ends with `\n`)
- Delete: includes preceding newline when deleting to EOF
- Change: replaces affected lines with a single empty line

### Paste (`executePaste`)

Linewise vs character-wise paste behavior:
- **Linewise** (register ends with `\n`): Inserts whole lines above/below current line
- **Character-wise**: Inserts at cursor (after `p`) or before cursor (`P`)
- Count support: `3p` pastes three times

## Text Objects (`textObjects.ts`)

### Word Objects

Grapheme-safe word boundary detection using `Intl.Segmenter`:

```typescript
function findWordObject(text, offset, isInner, isWordChar): TextObjectRange
```

Three character classes: word chars, whitespace, punctuation. Inner excludes surrounding whitespace; around includes it (trailing preferred, leading as fallback).

### Quote Objects

Line-scoped paired quote finding:
- Pairs quotes left-to-right: positions 0-1, 2-3, 4-5
- Inner: between quotes (exclusive)
- Around: including quotes (inclusive)

### Bracket Objects

Nested bracket matching with depth tracking:
- Scans backward from cursor for opening bracket
- Scans forward for matching close
- Handles arbitrary nesting depth
- Supports: `()/b`, `[]`, `{}/B`, `<>`

## Key Constants

All magic strings are eliminated through named constants:

```typescript
export const OPERATORS = { d: 'delete', c: 'change', y: 'yank' } as const
export const SIMPLE_MOTIONS = new Set(['h','l','j','k','w','b','e','W','B','E','0','^','$'])
export const FIND_KEYS = new Set(['f', 'F', 't', 'T'])
export const TEXT_OBJ_SCOPES = { i: 'inner', a: 'around' } as const
export const TEXT_OBJ_TYPES = new Set(['w','W','"',"'",'`','(',')',... ])
```

## Design Patterns

1. **State Machine**: TypeScript discriminated unions ensure exhaustive handling — the compiler catches missing cases
2. **Pure Functions**: Motions and text objects are pure — no side effects, easy to test
3. **Separation of Concerns**: Types, transitions, motions, operators, and text objects are in separate files
4. **Grapheme Safety**: All text manipulation uses `Intl.Segmenter` via the `Cursor` class for correct Unicode handling
5. **Command Recording**: Every mutation records its change for dot-repeat, enabling faithful replay
