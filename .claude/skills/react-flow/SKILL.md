---
name: react-flow
description: |
  Development guide for React Flow (@xyflow/react) visual workflow editor in IPA Platform.

  MUST READ when working with:
  - Visual workflow editor (frontend/src/pages/workflows/)
  - Custom node components for workflow node types
  - Custom edge components for workflow connections
  - Drag-and-drop flow canvas with node/edge state management
  - Integration between React Flow graph_definition and MAF backend execution

  PROVIDES: Official API patterns, TypeScript types, custom node/edge creation,
  state management with Zustand, Handle configuration, layouting strategies.

  INTEGRATION: React Flow frontend editor -> graph_definition JSON -> MAF backend execution
---

# React Flow (@xyflow/react) - Development Guide

**Purpose**: This skill guides correct implementation of React Flow as the visual workflow editor in the IPA Platform. React Flow is the frontend graph editing layer that produces `graph_definition` JSON consumed by the MAF backend execution engine.

**Package**: `@xyflow/react` (v12+)
**Docs**: https://reactflow.dev

## Architecture Position in IPA Platform

```
React Flow (Frontend Visual Editor)
    |
    | Produces: graph_definition JSON
    | { nodes: WorkflowGraphNode[], edges: WorkflowGraphEdge[], variables: {} }
    |
    v
POST /api/v1/workflows/  (Backend API)
    |
    v
WorkflowDefinition (Domain Model)
    |
    v
WorkflowDefinitionAdapter -> WorkflowBuilder -> MAF Workflow.run()
```

React Flow ONLY replaces the frontend editing UI. The backend pipeline is unchanged.

## CRITICAL RULES

1. **ALWAYS import from `@xyflow/react`** - NOT from `react-flow-renderer` (deprecated) or `reactflow` (old package)
2. **ALWAYS import the CSS** - `import '@xyflow/react/dist/style.css'` is mandatory
3. **ALWAYS set parent container dimensions** - ReactFlow requires explicit width/height on parent element
4. **ALWAYS define `nodeTypes`/`edgeTypes` OUTSIDE components** - Defining inside causes infinite re-renders
5. **ALWAYS use `useCallback` for event handlers** - Prevents re-render loops
6. **NEVER mutate node/edge arrays directly** - Use `applyNodeChanges`, `applyEdgeChanges`, `addEdge` helpers
7. **Use `nodrag` class on interactive elements** - Inputs, selects, buttons inside nodes need `className="nodrag"`
8. **Use `nowheel` class on scrollable elements** - Prevents viewport zoom when scrolling inside nodes
9. **Use `nopan` class on interactive areas** - Prevents viewport panning when interacting with node content

## Installation

```bash
cd frontend && npm install @xyflow/react
```

No additional dependencies required for core functionality. For auto-layouting, add:
```bash
npm install dagre          # Tree layouts (~40KB, synchronous, recommended)
# OR
npm install elkjs          # Advanced layouts (~1.5MB, async, powerful)
```

## Essential Setup Pattern

```tsx
import { useCallback, useState } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// MUST define outside component to prevent re-renders
const nodeTypes = { /* custom node types */ };
const edgeTypes = { /* custom edge types */ };

export default function WorkflowEditor() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  );

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [],
  );

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background variant="dots" gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}
```

## IPA Platform Node Type Mapping

These are the node types that map to the existing MAF backend:

| React Flow Node Type | MAF NodeType | Backend Executor | Handle Config |
|---------------------|--------------|------------------|---------------|
| `start` | `START` | Pass-through | 1 source (bottom) |
| `end` | `END` | Finalize | 1 target (top) |
| `agent` | `AGENT` | `AgentService.execute()` | 1 target (top), 1 source (bottom) |
| `gateway` | `GATEWAY` | `ConditionEvaluator` | 1 target (top), N sources (bottom/right) |
| `subworkflow` | N/A (future) | `WorkflowExecutor` | 1 target (top), 1 source (bottom) |
| `concurrent` | N/A (future) | `ConcurrentBuilder` | 1 target (top), N sources (bottom) |

## graph_definition JSON Format (Backend Contract)

The React Flow editor MUST produce this exact JSON structure for backend compatibility:

```json
{
  "nodes": [
    {
      "id": "node-1",
      "type": "start",
      "name": "Start",
      "agent_id": null,
      "config": {},
      "position": { "x": 250, "y": 0 }
    },
    {
      "id": "node-2",
      "type": "agent",
      "name": "Customer Support Agent",
      "agent_id": "uuid-of-agent",
      "config": { "max_tokens": 1000 },
      "position": { "x": 250, "y": 150 }
    }
  ],
  "edges": [
    {
      "source": "node-1",
      "target": "node-2",
      "condition": "",
      "label": ""
    }
  ],
  "variables": {}
}
```

### Conversion: React Flow State -> graph_definition

```tsx
function toGraphDefinition(rfNodes: Node[], rfEdges: Edge[]): GraphDefinition {
  return {
    nodes: rfNodes.map((node) => ({
      id: node.id,
      type: node.type || 'agent',
      name: node.data.label || node.data.name || '',
      agent_id: node.data.agent_id || null,
      config: node.data.config || {},
      position: node.position,
    })),
    edges: rfEdges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      condition: edge.data?.condition || '',
      label: edge.label?.toString() || '',
    })),
    variables: {},
  };
}
```

### Conversion: graph_definition -> React Flow State

```tsx
function fromGraphDefinition(def: GraphDefinition): { nodes: Node[]; edges: Edge[] } {
  return {
    nodes: def.nodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position || { x: 0, y: 0 },
      data: {
        label: node.name,
        name: node.name,
        agent_id: node.agent_id,
        config: node.config,
      },
    })),
    edges: def.edges.map((edge, i) => ({
      id: `e-${edge.source}-${edge.target}-${i}`,
      source: edge.source,
      target: edge.target,
      label: edge.label || undefined,
      data: { condition: edge.condition },
    })),
  };
}
```

## Before Implementing, Check:

1. **`references/core-api.md`** - ReactFlow component props, utility functions, built-in components
2. **`references/custom-nodes.md`** - Custom node creation, Handle component, node patterns
3. **`references/custom-edges.md`** - Custom edge creation, path utilities, edge labels
4. **`references/hooks-api.md`** - All React Flow hooks (useReactFlow, useNodes, useEdges, etc.)
5. **`references/typescript-patterns.md`** - Type-safe patterns for custom nodes/edges
6. **`references/state-management.md`** - Zustand integration, external store patterns
7. **`references/project-integration.md`** - IPA Platform specific integration guide

## Quick Reference

| Need | Use This | NOT This |
|------|----------|----------|
| Install | `@xyflow/react` | `reactflow` or `react-flow-renderer` |
| Node state | `applyNodeChanges()` | Direct array mutation |
| Edge state | `applyEdgeChanges()` | Direct array mutation |
| New connection | `addEdge()` | Manual edge push |
| Custom nodes | `nodeTypes` prop (outside component) | Inline node rendering |
| Custom edges | `edgeTypes` prop (outside component) | Inline SVG paths |
| Access instance | `useReactFlow()` hook | DOM manipulation |
| Handle positions | `Position.Top/Bottom/Left/Right` | CSS absolute positioning |
| Prevent drag on inputs | `className="nodrag"` | `stopPropagation` hacks |
| Auto layout | `dagre` library | Manual position calculation |
| State management | Zustand store | Prop drilling through node data |
