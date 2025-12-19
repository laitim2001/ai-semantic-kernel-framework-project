---
paths: frontend/**/*.{ts,tsx}
---

# React Frontend Rules

> Rules for TypeScript/React code in the frontend.

## Component Structure

```tsx
// 1. Imports
import { FC, useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';

// 2. Types
interface MyComponentProps {
  title: string;
  onAction: () => void;
}

// 3. Component
export const MyComponent: FC<MyComponentProps> = ({ title, onAction }) => {
  // Hooks first
  const [state, setState] = useState('');
  const { data, isLoading } = useQuery({...});

  // Event handlers
  const handleClick = () => onAction();

  // Early returns for loading/error
  if (isLoading) return <Loading />;

  // Main render
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick}>Action</Button>
    </div>
  );
};
```

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `AgentCard.tsx` |
| Hooks | camelCase + use | `useAgents.ts` |
| Utils | camelCase | `formatDate.ts` |
| Types | PascalCase | `Agent`, `AgentProps` |
| Constants | UPPER_SNAKE | `MAX_RETRY_COUNT` |

## State Management

```tsx
// Zustand for global state
import { useAgentStore } from '@/store/agentStore';
const { agents, selectAgent } = useAgentStore();

// React Query for server state
const { data, isLoading } = useQuery({
  queryKey: ['agents'],
  queryFn: () => api.getAgents(),
});

// useState for local state
const [isOpen, setIsOpen] = useState(false);
```

## Styling with Tailwind

```tsx
// Use Tailwind classes
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
  <span className="text-lg font-semibold text-gray-900">Title</span>
</div>

// Shadcn UI components
<Button variant="default" size="sm">Submit</Button>
<Button variant="outline">Cancel</Button>
<Button variant="destructive">Delete</Button>
```

## Prohibited

- ❌ `any` type (use proper types)
- ❌ `console.log` in production
- ❌ Inline styles (use Tailwind)
- ❌ Direct DOM manipulation
- ❌ Class components (use functional)
