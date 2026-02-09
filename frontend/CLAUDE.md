# Frontend - React Application

> IPA Platform frontend application, built with React 18 + TypeScript + Vite

---

## Quick Reference

```bash
# Install dependencies
npm install

# Run development server (port 3005)
npm run dev

# Build for production
tsc && npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Type check
npm run typecheck

# Testing
npm run test              # Unit tests (Vitest)
npm run test:ui           # Vitest UI
npm run test:coverage     # Coverage report
npm run test:e2e          # E2E tests (Playwright)
```

---

## Technology Stack

| Category | Technology | Notes |
|----------|------------|-------|
| Framework | React 18 | Functional components only |
| Language | TypeScript 5 | Strict mode |
| Build Tool | Vite 5 | Fast HMR |
| Styling | Tailwind CSS 3 | Utility-first |
| UI Components | Shadcn UI (Radix UI) | Custom themed |
| State Management | Zustand 4 | Global state |
| Server State | TanStack React Query 5 | Data fetching + cache |
| Routing | React Router v6 | Client-side routing |
| HTTP Client | **Fetch API** (native) | NOT Axios |
| Charts | Recharts 2 | Data visualization |
| Icons | Lucide React | SVG icons |
| Immutability | Immer | State updates |
| Testing | Vitest + Playwright | Unit + E2E |

> **IMPORTANT**: This project uses the **native Fetch API**, NOT Axios. See `src/api/client.ts`.

---

## Directory Structure

```
frontend/
├── src/
│   ├── api/                    # API client (Fetch API)
│   │   ├── client.ts           # Core fetch wrapper with auth
│   │   ├── devtools.ts         # DevTools API functions
│   │   └── endpoints/          # Domain-specific API functions
│   │       ├── index.ts        # Central export
│   │       ├── ag-ui.ts        # AG-UI Protocol endpoints
│   │       ├── files.ts        # File management endpoints
│   │       └── orchestration.ts # Orchestration endpoints
│   │
│   ├── components/             # UI Components (~115 files)
│   │   ├── ag-ui/              # AG-UI Protocol components
│   │   │   ├── advanced/       # Advanced AG-UI features
│   │   │   ├── chat/           # AG-UI chat components
│   │   │   └── hitl/           # Human-in-the-loop components
│   │   ├── auth/               # Authentication components
│   │   ├── DevUI/              # Developer tools (15 components)
│   │   ├── layout/             # Layout (Header, Sidebar)
│   │   ├── shared/             # Shared/reusable components
│   │   ├── ui/                 # Shadcn UI base components
│   │   └── unified-chat/       # Main chat interface (27+ files)
│   │       ├── agent-swarm/    # Agent Swarm (15 components + 4 hooks + types)
│   │       │   ├── hooks/      # Swarm-specific hooks
│   │       │   ├── types/      # Swarm type definitions
│   │       │   └── __tests__/  # Swarm component tests
│   │       └── renderers/      # Message renderers
│   │
│   ├── pages/                  # Page components (11 modules)
│   │   ├── agents/             # Agent management
│   │   ├── ag-ui/              # AG-UI demo pages
│   │   ├── approvals/          # Approval management
│   │   ├── audit/              # Audit log pages
│   │   ├── auth/               # Login, signup pages
│   │   ├── dashboard/          # Dashboard analytics
│   │   ├── DevUI/              # Developer tools pages
│   │   ├── templates/          # Template management
│   │   ├── workflows/          # Workflow management
│   │   ├── SwarmTestPage.tsx   # Agent Swarm testing (Phase 29)
│   │   └── UnifiedChat.tsx     # Main chat page
│   │
│   ├── hooks/                  # Custom React hooks (17 files)
│   │   ├── index.ts            # Central export
│   │   ├── useAGUI.ts          # AG-UI Protocol hook
│   │   ├── useApprovalFlow.ts  # HITL approval workflow
│   │   ├── useChatThreads.ts   # Chat thread management
│   │   ├── useCheckpoints.ts   # Checkpoint system
│   │   ├── useDevTools.ts      # Developer tools
│   │   ├── useDevToolsStream.ts # SSE streaming for DevTools
│   │   ├── useEventFilter.ts   # Event filtering
│   │   ├── useExecutionMetrics.ts # Execution metrics
│   │   ├── useFileUpload.ts    # File upload handling
│   │   ├── useHybridMode.ts    # MAF/Claude SDK hybrid mode
│   │   ├── useOptimisticState.ts # Optimistic UI updates
│   │   ├── useOrchestration.ts # Intent routing orchestration
│   │   ├── useSharedState.ts   # Cross-component state
│   │   ├── useSwarmMock.ts     # Swarm mock data (dev)
│   │   ├── useSwarmReal.ts     # Swarm real API integration
│   │   └── useUnifiedChat.ts   # Main chat logic
│   │
│   ├── store/                  # Zustand stores (auth)
│   │   └── authStore.ts        # Authentication state (persisted)
│   │
│   ├── stores/                 # Zustand stores (features)
│   │   ├── swarmStore.ts       # Agent Swarm state
│   │   ├── unifiedChatStore.ts # Unified chat state
│   │   └── __tests__/          # Store tests
│   │
│   ├── types/                  # TypeScript type definitions
│   │   ├── index.ts            # Core shared types
│   │   ├── ag-ui.ts            # AG-UI Protocol types
│   │   ├── devtools.ts         # DevTools types
│   │   └── unified-chat.ts     # Chat types
│   │
│   ├── utils/                  # Utility functions
│   │   └── guestUser.ts        # Guest user ID management
│   │
│   ├── lib/                    # Library utilities
│   │   └── utils.ts            # Tailwind merge helper (cn())
│   │
│   ├── App.tsx                 # Root component with routing
│   ├── main.tsx                # Application entry point
│   └── index.css               # Global styles (Tailwind)
│
├── public/                     # Static assets
├── index.html                  # HTML template
├── vite.config.ts              # Vite configuration
├── tailwind.config.js          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Dependencies
```

---

## API Client

### Fetch API Pattern (NOT Axios)

```typescript
// src/api/client.ts - Core fetch wrapper
import { getGuestHeaders } from '@/utils/guestUser';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const guestHeaders = getGuestHeaders();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...guestHeaders,  // X-Guest-Id for sandbox isolation
    ...options?.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) handleUnauthorized();
    throw new ApiError(errorMessage, response.status, errorDetails);
  }

  return response.json();
}

// Usage
export const api = {
  get: <T>(endpoint: string) => fetchApi<T>(endpoint),
  post: <T>(endpoint: string, body?: unknown) =>
    fetchApi<T>(endpoint, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(endpoint: string, body: unknown) =>
    fetchApi<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(endpoint: string, body: unknown) =>
    fetchApi<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(endpoint: string) => fetchApi<T>(endpoint, { method: 'DELETE' }),
};
```

### Endpoint Functions

```typescript
// src/api/endpoints/ag-ui.ts
import { api } from '../client';

export const agUiApi = {
  getEvents: (sessionId: string) => api.get(`/ag-ui/sessions/${sessionId}/events`),
  sendMessage: (sessionId: string, message: string) =>
    api.post(`/ag-ui/sessions/${sessionId}/messages`, { message }),
};
```

---

## Code Standards

### TypeScript Conventions

```typescript
// Use interfaces for object shapes
interface Agent {
  id: string;
  name: string;
  type: AgentType;
  config: AgentConfig;
}

// Use type for unions and primitives
type AgentType = 'chat' | 'task' | 'orchestrator';

// Props naming: ComponentNameProps
interface AgentCardProps {
  agent: Agent;
  onSelect: (id: string) => void;
}
```

### Component Structure

```typescript
import { FC, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export const MyComponent: FC<MyComponentProps> = ({ title, onAction }) => {
  // 1. Hooks first
  const [state, setState] = useState<string>('');
  const { data, isLoading } = useQuery({...});

  // 2. Event handlers
  const handleClick = () => onAction();

  // 3. Early returns
  if (isLoading) return <Loading />;

  // 4. Main render
  return (
    <div className="flex items-center p-4">
      <h1>{title}</h1>
      <Button onClick={handleClick}>Action</Button>
    </div>
  );
};
```

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `AgentCard.tsx` |
| Pages | PascalCase | `SwarmTestPage.tsx` |
| Hooks | camelCase + use prefix | `useSwarmReal.ts` |
| Stores | camelCase + Store suffix | `swarmStore.ts` |
| Utils | camelCase | `guestUser.ts` |
| Types | camelCase | `unified-chat.ts` |

---

## State Management

### Zustand Stores

```typescript
// src/store/authStore.ts - Persisted auth state
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  user: User | null;
  login: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'auth-storage' }
  )
);
```

```typescript
// src/stores/unifiedChatStore.ts - Chat state
import { create } from 'zustand';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  addMessage: (msg: Message) => void;
  setStreaming: (streaming: boolean) => void;
}

export const useUnifiedChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
}));
```

### React Query for Server State

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Fetching data
const { data, isLoading, error } = useQuery({
  queryKey: ['agents'],
  queryFn: () => api.get<Agent[]>('/agents'),
});

// Mutations
const queryClient = useQueryClient();
const mutation = useMutation({
  mutationFn: (data: CreateAgentRequest) => api.post<Agent>('/agents', data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['agents'] });
  },
});
```

---

## Key Feature Areas

### Unified Chat (`components/unified-chat/`)

Main chat interface with 27+ components:
- `ChatArea.tsx` / `ChatInput.tsx` / `MessageList.tsx` - Core chat UI
- `OrchestrationPanel.tsx` - Three-tier intent routing display
- `InlineApproval.tsx` / `ApprovalDialog.tsx` - HITL approval UI
- `FileUpload.tsx` / `FileMessage.tsx` - File attachment support
- `ToolCallTracker.tsx` - Tool call visualization
- `ModeIndicator.tsx` / `RiskIndicator.tsx` - Status indicators

### Agent Swarm (`components/unified-chat/agent-swarm/`)

Phase 29 Agent Swarm visualization (15 components + 4 hooks):
- `AgentSwarmPanel.tsx` - Main swarm container
- `WorkerCard.tsx` / `WorkerCardList.tsx` - Worker agent cards
- `WorkerDetailDrawer.tsx` - Worker detail side panel
- `ExtendedThinkingPanel.tsx` - AI thinking process display
- `ToolCallsPanel.tsx` / `ToolCallItem.tsx` - Tool execution tracking
- `SwarmHeader.tsx` / `SwarmStatusBadges.tsx` - Swarm status display
- `CheckpointPanel.tsx` / `OverallProgress.tsx` - Progress tracking

### DevUI (`components/DevUI/`)

Developer tools (15 components):
- Event timeline, filtering, and tree visualization
- LLM event panel, tool event panel
- Statistics and charts

### AG-UI (`components/ag-ui/`)

AG-UI Protocol components organized in 3 subdirectories:
- `advanced/` - Advanced agentic UI features
- `chat/` - AG-UI chat components
- `hitl/` - Human-in-the-loop components

---

## Styling

### Tailwind CSS

```tsx
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
  <span className="text-lg font-semibold text-gray-900">Title</span>
  <button className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700">
    Action
  </button>
</div>
```

### Shadcn UI Components

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardContent } from '@/components/ui/card';

<Button variant="default" size="sm">Submit</Button>
<Button variant="outline">Cancel</Button>
<Button variant="destructive">Delete</Button>
```

---

## Environment Variables

```bash
# .env.local
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=IPA Platform
```

Access in code:
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
```

---

## Common Patterns

### Loading States

```tsx
{isLoading ? (
  <div className="flex items-center justify-center h-64">
    <Spinner />
  </div>
) : (
  <DataTable data={data} />
)}
```

### Error Handling

```tsx
{error && (
  <Alert variant="destructive">
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>{error.message}</AlertDescription>
  </Alert>
)}
```

### SSE Streaming

```typescript
// Pattern used for DevTools and Swarm real-time updates
const eventSource = new EventSource(`${API_BASE_URL}/sessions/${id}/stream`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle streaming event
};
```

---

**Last Updated**: 2026-02-09
