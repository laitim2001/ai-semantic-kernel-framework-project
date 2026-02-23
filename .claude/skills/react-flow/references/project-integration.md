# IPA Platform Integration Guide

How React Flow integrates with the existing IPA Platform architecture.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (React 18)                     │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ React Flow Canvas (visual editor)                    │  │
│  │  - Custom nodes: Start, End, Agent, Gateway          │  │
│  │  - Custom edges: Condition edges with labels         │  │
│  │  - Drag & drop from sidebar palette                  │  │
│  │  - Connection validation                             │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ Zustand Store (workflowEditorStore)                  │  │
│  │  - nodes[], edges[] (React Flow state)               │  │
│  │  - toGraphDefinition() (convert to backend format)   │  │
│  │  - loadWorkflow() (convert from backend format)      │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ POST/PUT graph_definition JSON   │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ API Client (frontend/src/api/client.ts)              │  │
│  │  - Fetch API with auth headers                       │  │
│  └──────────────────────┬──────────────────────────────┘  │
└─────────────────────────┼─────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼─────────────────────────────────┐
│                  Backend (FastAPI)                          │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API Route: POST /api/v1/workflows/                    │  │
│  │ WorkflowCreateRequest (Pydantic validation)           │  │
│  │  - Validates: has START node, has END node             │  │
│  │  - Validates: node types match NodeType enum           │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │ Domain: WorkflowDefinition                            │  │
│  │  - WorkflowNode (id, type, name, agent_id, config)    │  │
│  │  - WorkflowEdge (source, target, condition)            │  │
│  │  - Validation: agent nodes must have agent_id          │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │ Execution: WorkflowDefinitionAdapter                  │  │
│  │  → WorkflowNodeExecutor (extends MAF Executor)        │  │
│  │  → WorkflowEdgeAdapter (condition evaluation)          │  │
│  │  → WorkflowBuilder.build() → MAF Workflow.run()        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## Data Flow: React Flow -> Backend

### React Flow Internal State
```tsx
// React Flow manages nodes as:
{
  id: 'agent-1',
  type: 'agent',
  position: { x: 250, y: 150 },
  data: {
    label: 'Customer Support',
    agent_id: '550e8400-e29b-41d4-a716-446655440000',
    config: { max_tokens: 1000 },
    status: 'idle',        // UI-only, not sent to backend
  },
  selected: false,          // UI-only
  dragging: false,          // UI-only
}
```

### graph_definition (Backend Contract)
```json
{
  "nodes": [
    {
      "id": "agent-1",
      "type": "agent",
      "name": "Customer Support",
      "agent_id": "550e8400-e29b-41d4-a716-446655440000",
      "config": { "max_tokens": 1000 },
      "position": { "x": 250, "y": 150 }
    }
  ],
  "edges": [
    {
      "source": "start",
      "target": "agent-1",
      "condition": "",
      "label": ""
    }
  ],
  "variables": {}
}
```

### Conversion Functions

```tsx
// frontend/src/utils/workflowConverter.ts

import type { Node, Edge } from '@xyflow/react';

/**
 * Convert React Flow state to backend graph_definition format.
 * Strips UI-only fields (selected, dragging, etc.)
 */
export function toGraphDefinition(
  rfNodes: Node[],
  rfEdges: Edge[],
): GraphDefinition {
  return {
    nodes: rfNodes.map((node) => ({
      id: node.id,
      type: node.type || 'agent',
      name: node.data?.label || node.data?.name || '',
      agent_id: node.data?.agent_id || null,
      config: node.data?.config || {},
      position: { x: node.position.x, y: node.position.y },
    })),
    edges: rfEdges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      condition: edge.data?.condition || '',
      label: typeof edge.label === 'string' ? edge.label : '',
    })),
    variables: {},
  };
}

/**
 * Convert backend graph_definition to React Flow state.
 * Adds React Flow required fields (position, data wrapper).
 */
export function fromGraphDefinition(
  def: GraphDefinition,
): { nodes: Node[]; edges: Edge[] } {
  return {
    nodes: def.nodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position || { x: 0, y: 0 },
      data: {
        label: node.name,
        name: node.name,
        agent_id: node.agent_id,
        config: node.config || {},
      },
    })),
    edges: def.edges.map((edge, index) => ({
      id: `e-${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      type: edge.condition ? 'condition' : 'smoothstep',
      label: edge.label || undefined,
      data: {
        condition: edge.condition || '',
      },
    })),
  };
}
```

## Connection Validation

Validate connections against backend rules before allowing them:

```tsx
import { useCallback } from 'react';
import type { Connection, IsValidConnection } from '@xyflow/react';

export function useConnectionValidation() {
  const { getNodes, getEdges } = useReactFlow();

  const isValidConnection: IsValidConnection = useCallback(
    (connection: Connection) => {
      const nodes = getNodes();
      const edges = getEdges();

      // Rule 1: No self-connections
      if (connection.source === connection.target) return false;

      // Rule 2: No duplicate edges
      const exists = edges.some(
        (e) => e.source === connection.source && e.target === connection.target,
      );
      if (exists) return false;

      // Rule 3: START nodes can only be source
      const sourceNode = nodes.find((n) => n.id === connection.source);
      if (sourceNode?.type === 'end') return false;

      // Rule 4: END nodes can only be target
      const targetNode = nodes.find((n) => n.id === connection.target);
      if (targetNode?.type === 'start') return false;

      // Rule 5: No cycles (basic check)
      // For full cycle detection, implement DFS/BFS

      return true;
    },
    [getNodes, getEdges],
  );

  return isValidConnection;
}
```

## Node Palette (Drag & Drop)

### Sidebar Component

```tsx
// components/workflow-editor/NodePalette.tsx

const nodeTemplates = [
  {
    type: 'agent',
    label: 'Agent Node',
    icon: Bot,
    description: 'Execute an AI agent',
  },
  {
    type: 'gateway',
    label: 'Gateway',
    icon: GitBranch,
    description: 'Conditional branching',
  },
];

export function NodePalette() {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="node-palette">
      {nodeTemplates.map((template) => (
        <div
          key={template.type}
          className="palette-item"
          onDragStart={(e) => onDragStart(e, template.type)}
          draggable
        >
          <template.icon size={16} />
          <span>{template.label}</span>
        </div>
      ))}
    </div>
  );
}
```

### Drop Handler on Canvas

```tsx
// In WorkflowEditor component
const { screenToFlowPosition, addNodes } = useReactFlow();

const onDragOver = useCallback((event: React.DragEvent) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
}, []);

const onDrop = useCallback(
  (event: React.DragEvent) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/reactflow');
    if (!type) return;

    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    const newNode: AppNode = {
      id: `${type}-${Date.now()}`,
      type,
      position,
      data: {
        label: `New ${type}`,
        agent_id: null,
        config: {},
      },
    };

    addNodes(newNode);
  },
  [screenToFlowPosition, addNodes],
);

<ReactFlow onDragOver={onDragOver} onDrop={onDrop} /* ... */ />
```

## Existing Backend Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/workflows/` | POST | Create workflow (graph_definition) |
| `/api/v1/workflows/` | GET | List workflows |
| `/api/v1/workflows/{id}` | GET | Get workflow details |
| `/api/v1/workflows/{id}` | PUT | Update workflow |
| `/api/v1/workflows/{id}` | DELETE | Delete workflow |
| `/api/v1/workflows/{id}/execute` | POST | Execute workflow |
| `/api/v1/workflows/{id}/activate` | POST | Activate workflow |
| `/api/v1/workflows/{id}/deactivate` | POST | Deactivate workflow |
| `/api/v1/agents/?status=active` | GET | List agents for node assignment |

## Existing Frontend Files to Modify

| File | Current State | Change Needed |
|------|---------------|---------------|
| `frontend/src/pages/workflows/CreateWorkflowPage.tsx` | 5-step wizard form (887 lines) | Replace with React Flow editor |
| `frontend/src/App.tsx:81` | Routes to CreateWorkflowPage | No change needed |
| `frontend/src/types/index.ts` | WorkflowGraphDefinition types | May need updates |
| `frontend/src/api/client.ts` | Generic API client | No change needed |

## New Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/workflow-editor/WorkflowCanvas.tsx` | React Flow canvas component |
| `frontend/src/components/workflow-editor/nodes/StartNode.tsx` | Custom start node |
| `frontend/src/components/workflow-editor/nodes/EndNode.tsx` | Custom end node |
| `frontend/src/components/workflow-editor/nodes/AgentNode.tsx` | Custom agent node |
| `frontend/src/components/workflow-editor/nodes/GatewayNode.tsx` | Custom gateway node |
| `frontend/src/components/workflow-editor/edges/ConditionEdge.tsx` | Custom condition edge |
| `frontend/src/components/workflow-editor/NodePalette.tsx` | Draggable node sidebar |
| `frontend/src/components/workflow-editor/NodeConfigPanel.tsx` | Node property editor |
| `frontend/src/components/workflow-editor/WorkflowToolbar.tsx` | Save, execute, undo/redo |
| `frontend/src/stores/workflowEditorStore.ts` | Zustand store |
| `frontend/src/utils/workflowConverter.ts` | RF <-> graph_definition conversion |
| `frontend/src/hooks/useConnectionValidation.ts` | Connection validation logic |

## Backend Validation Rules (Must Match Frontend)

From `backend/src/domain/workflows/schemas.py` and `models.py`:

1. Must have at least one node
2. Must have exactly one START node
3. Must have exactly one END node
4. Node types must be: `start`, `end`, `agent`, `gateway`
5. Agent nodes must have `agent_id` (validated in domain model)
6. Node IDs must match pattern: `^[a-zA-Z0-9_-]+$`
7. Edge source/target must reference existing node IDs

## Auto-Layout with Dagre

```tsx
// utils/layoutWorkflow.ts
import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';

const NODE_WIDTH = 200;
const NODE_HEIGHT = 60;

export function layoutWorkflow(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB',
): Node[] {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  return nodes.map((node) => {
    const dagreNode = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: dagreNode.x - NODE_WIDTH / 2,
        y: dagreNode.y - NODE_HEIGHT / 2,
      },
    };
  });
}
```
