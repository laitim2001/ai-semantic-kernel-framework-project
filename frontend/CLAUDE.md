# Frontend - React Application

> IPA Platform frontend application, built with React 18 + TypeScript + Vite

---

## Quick Reference

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Framework | React 18 |
| Language | TypeScript 5 |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| UI Components | Shadcn UI |
| State Management | Zustand |
| Data Fetching | React Query (TanStack Query) |
| Routing | React Router v6 |
| HTTP Client | Axios |
| Icons | Lucide React |

---

## Directory Structure

```
frontend/
├── src/
│   ├── api/                # API client and endpoints
│   │   ├── client.ts       # Axios instance configuration
│   │   └── endpoints/      # API endpoint functions
│   │
│   ├── components/         # Reusable UI components
│   │   ├── layout/         # Layout components (Header, Sidebar)
│   │   ├── shared/         # Shared components
│   │   └── ui/             # Shadcn UI components
│   │
│   ├── pages/              # Page components (routes)
│   │   ├── dashboard/      # Dashboard page
│   │   ├── agents/         # Agent management pages
│   │   ├── workflows/      # Workflow management pages
│   │   ├── approvals/      # Approval management pages
│   │   ├── templates/      # Template management pages
│   │   └── audit/          # Audit log pages
│   │
│   ├── lib/                # Utility functions and helpers
│   │   └── utils.ts        # Common utilities
│   │
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts        # Shared types
│   │
│   ├── App.tsx             # Root component with routing
│   ├── main.tsx            # Application entry point
│   └── index.css           # Global styles (Tailwind)
│
├── public/                 # Static assets
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
└── tsconfig.json           # TypeScript configuration
```

---

## Code Standards

### TypeScript Conventions

```typescript
// Type definitions - use interfaces for objects
interface Agent {
  id: string;
  name: string;
  type: AgentType;
  config: AgentConfig;
}

// Use type for unions and primitives
type AgentType = 'chat' | 'task' | 'orchestrator';
type AgentId = string;

// Props interface naming: ComponentNameProps
interface AgentCardProps {
  agent: Agent;
  onSelect: (id: string) => void;
}
```

### Component Structure

```typescript
// Standard component template
import { FC } from 'react';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export const MyComponent: FC<MyComponentProps> = ({ title, onAction }) => {
  // Hooks first
  const [state, setState] = useState<string>('');

  // Event handlers
  const handleClick = () => {
    onAction();
  };

  // Render
  return (
    <div className="...">
      <h1>{title}</h1>
      <button onClick={handleClick}>Action</button>
    </div>
  );
};
```

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `AgentCard.tsx` |
| Pages | PascalCase | `AgentDetailPage.tsx` |
| Hooks | camelCase + use prefix | `useAgents.ts` |
| Utils | camelCase | `formatDate.ts` |
| Types | camelCase | `types.ts` |

---

## Styling Guidelines

### Tailwind CSS

```tsx
// Use Tailwind classes for styling
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
  <span className="text-lg font-semibold text-gray-900">Title</span>
  <button className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700">
    Action
  </button>
</div>
```

### Shadcn UI Components

```tsx
// Import from @/components/ui
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

// Use Shadcn components with variants
<Button variant="default" size="sm">Submit</Button>
<Button variant="outline">Cancel</Button>
<Button variant="destructive">Delete</Button>
```

---

## State Management

### Zustand Store Pattern

```typescript
// src/store/agentStore.ts
import { create } from 'zustand';

interface AgentState {
  agents: Agent[];
  selectedAgent: Agent | null;
  setAgents: (agents: Agent[]) => void;
  selectAgent: (agent: Agent) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  selectedAgent: null,
  setAgents: (agents) => set({ agents }),
  selectAgent: (agent) => set({ selectedAgent: agent }),
}));
```

### React Query for Server State

```typescript
// Fetching data
const { data, isLoading, error } = useQuery({
  queryKey: ['agents'],
  queryFn: () => api.getAgents(),
});

// Mutations
const mutation = useMutation({
  mutationFn: (data: CreateAgentRequest) => api.createAgent(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['agents'] });
  },
});
```

---

## API Integration

### API Client Structure

```typescript
// src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Endpoint Functions

```typescript
// src/api/endpoints/agents.ts
import { apiClient } from '../client';
import { Agent, CreateAgentRequest } from '@/types';

export const agentsApi = {
  getAll: () => apiClient.get<Agent[]>('/agents').then(res => res.data),
  getById: (id: string) => apiClient.get<Agent>(`/agents/${id}`).then(res => res.data),
  create: (data: CreateAgentRequest) => apiClient.post<Agent>('/agents', data).then(res => res.data),
  update: (id: string, data: Partial<Agent>) => apiClient.put<Agent>(`/agents/${id}`, data).then(res => res.data),
  delete: (id: string) => apiClient.delete(`/agents/${id}`),
};
```

---

## Page Development

### Page Component Template

```typescript
// src/pages/agents/AgentDetailPage.tsx
import { FC } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { agentsApi } from '@/api/endpoints/agents';
import { PageHeader } from '@/components/layout/PageHeader';
import { AgentCard } from '@/components/shared/AgentCard';

export const AgentDetailPage: FC = () => {
  const { id } = useParams<{ id: string }>();

  const { data: agent, isLoading, error } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => agentsApi.getById(id!),
    enabled: !!id,
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading agent</div>;
  if (!agent) return <div>Agent not found</div>;

  return (
    <div className="p-6">
      <PageHeader title={agent.name} />
      <AgentCard agent={agent} />
    </div>
  );
};
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

### Form Handling

```tsx
import { useForm } from 'react-hook-form';

const { register, handleSubmit, formState: { errors } } = useForm<FormData>();

const onSubmit = (data: FormData) => {
  mutation.mutate(data);
};
```

---

**Last Updated**: 2026-01-23
