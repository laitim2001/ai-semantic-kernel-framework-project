# Component Library

> 200+ React components overview, design system, agent wizard, and major component groups.

## Architecture Overview

Claude Code's UI is built from 200+ React components organized into functional groups. The component library follows a layered architecture from low-level Ink primitives to high-level feature-specific components.

```
src/components/
├── permissions/         # Permission dialogs and rule management
├── diff/                # Diff rendering (word-level, structured)
├── StructuredDiff/      # Enhanced diff with syntax highlighting
├── PromptInput/         # Main input area with mode routing
├── unified-chat/        # Chat message rendering
├── agent-swarm/         # Team visualization
├── ui/                  # Shared UI primitives
├── layout/              # Layout components
└── [feature-specific]/  # Feature-grouped components
```

## Major Component Groups

### Chat & Messages (`src/components/unified-chat/`)

The primary chat interface with 27+ components:

| Component | Purpose |
|-----------|---------|
| `MessageThread` | Renders conversation message list |
| `AssistantMessage` | AI response with tool calls |
| `UserMessage` | User input display |
| `ToolUseMessage` | Tool invocation display |
| `ToolResultMessage` | Tool output display |
| `ThinkingBlock` | Extended thinking display |
| `ProgressIndicator` | Streaming progress |
| `Spinner` | Activity spinner with mode display |
| `CompactMessage` | Condensed message view |
| `MessageSelector` | Navigate between messages |

### Permission UI (`src/components/permissions/`)

Interactive permission dialogs:

| Component | Purpose |
|-----------|---------|
| `PermissionDialog` | Main permission prompt |
| `PermissionExplainer` | Risk level explanation |
| `RuleEditor` | Edit permission rules |
| `PermissionModeIndicator` | Current mode display |
| `BashPermissionDetail` | Bash-specific permission info |

### Diff Components (`src/components/diff/`, `src/components/StructuredDiff/`)

File diff rendering with multiple backends:

| Component | Purpose |
|-----------|---------|
| `WordDiff` | Word-level inline diff |
| `StructuredDiff` | Side-by-side structured diff |
| `DiffHeader` | File path and change summary |
| `DiffHunk` | Individual diff hunk |
| `SyntaxHighlighter` | Code syntax coloring |
| `LineNumbers` | Line number gutters |

### Input System (`src/components/PromptInput/`)

The main user input area:

| Component | Purpose |
|-----------|---------|
| `PromptInput` | Main input container |
| `TextEditor` | Multi-line text editing |
| `ModeIndicator` | Permission mode display |
| `TokenCounter` | Input token estimation |
| `SlashCommandTypeahead` | Command autocomplete |
| `FileAutocomplete` | File path completion |
| `HistoryNavigator` | Arrow key history |

### Agent & Team (`src/components/agent-swarm/`)

Agent swarm visualization (15 components + 4 hooks):

| Component | Purpose |
|-----------|---------|
| `TeamPanel` | Team overview panel |
| `AgentCard` | Individual agent status |
| `MailboxView` | Inter-agent messages |
| `TaskProgress` | Background task progress |
| `SwarmVisualization` | Team topology display |

### Developer UI (`src/components/DevUI/`)

Developer tools (15 components):

| Component | Purpose |
|-----------|---------|
| `ContextInspector` | Context window usage |
| `TokenCounter` | Detailed token breakdown |
| `MessageInspector` | Raw message viewer |
| `ToolCallViewer` | Tool call details |
| `PerformanceMonitor` | Timing and metrics |

### Shared UI (`src/components/ui/`)

Reusable UI primitives (Shadcn-inspired for terminal):

| Component | Purpose |
|-----------|---------|
| `Badge` | Status badges |
| `Separator` | Visual separators |
| `Tabs` | Tabbed interface |
| `Table` | Data tables |
| `ProgressBar` | Progress indicators |
| `Tooltip` | Hover tooltips |

## Screen Components (`src/screens/`)

Full-screen views:

| Screen | Purpose |
|--------|---------|
| `REPL` | Main interactive REPL screen |
| `Transcript` | Full conversation transcript |
| `TodoPanel` | Task/todo management panel |
| `TeammatePreview` | Agent teammate view |
| `BriefPanel` | Session brief display |
| `TerminalPanel` | Integrated terminal |
| `GlobalSearch` | Cross-session search |
| `QuickOpen` | Quick file/command open |

## Design Patterns

### Lazy Loading

Heavy components use dynamic imports:

```typescript
// insights.ts is 113KB — lazy load on command invocation
const real = (await import('./commands/insights.js')).default
```

### React Compiler

The codebase uses React Compiler (`react/compiler-runtime`) for automatic memoization. Compiled output uses `_c()` cache arrays:

```typescript
const $ = _c(13)
// Compiler-managed memoization via $ array indices
```

### Theme System

Components accept `ThemeName` for consistent styling:

| Theme | Description |
|-------|-------------|
| `dark` | Default dark theme |
| `light` | Light terminal theme |
| `system` | Follow terminal theme |

### Verbose Mode

Components accept `verbose: boolean` for detail level:
- **Non-verbose**: Condensed, collapsed tool results
- **Verbose**: Expanded, full detail

Many tool result renderers support click-to-expand via `isResultTruncated()`.

### Grouped Tool Rendering

Tools can implement `renderGroupedToolUse()` to render multiple parallel instances as a single visual group (e.g., multiple file reads shown as a list rather than individual blocks).

### Condensed Style

`style?: 'condensed'` flag triggers compressed rendering for:
- Tool results in non-verbose mode
- Transcript export
- Background agent output

## Component Rendering Pipeline

### Message Rendering

```
Message[] → MessageThread
  → UserMessage | AssistantMessage | SystemMessage
    → ToolUseMessage + ToolResultMessage (for assistant tool calls)
      → tool.renderToolUseMessage()
      → tool.renderToolResultMessage()
      → tool.renderToolUseProgressMessage()
```

### Tool Rendering Lifecycle

Each tool provides rendering methods:

1. `renderToolUseMessage(input)` — Shows what the tool is doing
2. `renderToolUseProgressMessage(progress)` — Live progress during execution
3. `renderToolResultMessage(output)` — Final result display
4. `renderToolUseRejectedMessage(input)` — When permission denied
5. `renderToolUseErrorMessage(result)` — Error display
6. `renderToolUseTag(input)` — Metadata tag (timeout, model, etc.)

### Transcript Search Integration

`extractSearchText(output)` provides indexable text for transcript search. Ensures count matches highlights by returning only actually-rendered text.

## Interactive Elements

### Focus Management

Ink's focus system manages which component receives keyboard input:
- `useFocus()` — Register focusable component
- `useFocusManager()` — Programmatic focus control
- Tab/Shift+Tab navigation

### Typeahead System (`src/hooks/useTypeahead.tsx`)

Provides autocomplete for:
- Slash commands
- File paths
- Agent names
- MCP server names

### Virtual Scroll (`src/hooks/useVirtualScroll.ts`)

Handles long conversation rendering:
- Only renders visible messages
- Smooth scrolling with keyboard shortcuts
- Efficient DOM recycling

## Key Source Files

| File | Purpose |
|------|---------|
| `src/components/` | All UI components |
| `src/screens/` | Full-screen views |
| `src/hooks/useTypeahead.tsx` | Autocomplete system |
| `src/hooks/useVirtualScroll.ts` | Virtual scrolling |
| `src/outputStyles/` | Output style configuration |
| `src/main.tsx` | Root component and app layout |
