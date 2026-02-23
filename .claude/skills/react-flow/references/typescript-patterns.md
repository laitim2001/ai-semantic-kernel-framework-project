# TypeScript Patterns for React Flow

React Flow is written in TypeScript. Use these patterns for type-safe implementations.

## Core Type Imports

```tsx
import type {
  // Data types
  Node,
  Edge,
  Connection,
  XYPosition,
  Viewport,

  // Change types
  NodeChange,
  EdgeChange,

  // Callback types
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  OnNodeDrag,
  OnSelectionChangeFunc,
  OnMove,
  IsValidConnection,

  // Component prop types
  NodeProps,
  EdgeProps,

  // Enum types
  Position,
  MarkerType,
  ConnectionMode,

  // Built-in types
  BuiltInNode,
  BuiltInEdge,

  // Utility types
  Rect,
  CoordinateExtent,
  FitViewOptions,
  ReactFlowInstance,
} from '@xyflow/react';
```

## Custom Node Types

### Define Node Data Types

```tsx
// Each custom node type has its own data shape
type StartNodeData = {
  label: string;
};

type EndNodeData = {
  label: string;
};

type AgentNodeData = {
  label: string;
  agent_id: string | null;
  config: Record<string, unknown>;
  status?: 'idle' | 'running' | 'completed' | 'error';
};

type GatewayNodeData = {
  label: string;
  gateway_type: 'exclusive' | 'parallel' | 'inclusive';
  conditions: Array<{
    handle_id: string;
    expression: string;
    label: string;
  }>;
};
```

### Define Node Types with Generic

```tsx
// Node<DataType, TypeString>
type StartNode = Node<StartNodeData, 'start'>;
type EndNode = Node<EndNodeData, 'end'>;
type AgentNode = Node<AgentNodeData, 'agent'>;
type GatewayNode = Node<GatewayNodeData, 'gateway'>;

// Union type for all app nodes
type AppNode = StartNode | EndNode | AgentNode | GatewayNode;
```

### Type-Safe Node Components

```tsx
// NodeProps is generic: NodeProps<YourNodeType>
function AgentNodeComponent({ data, selected, id }: NodeProps<AgentNode>) {
  // data is typed as AgentNodeData
  // data.agent_id    -- string | null  ✅
  // data.label       -- string         ✅
  // data.config      -- Record<...>    ✅
  // data.nonexistent -- ❌ TypeScript error
  return (/* ... */);
}
```

## Custom Edge Types

```tsx
// Edge data type
type ConditionEdgeData = {
  condition: string;
  priority?: number;
};

// Edge<DataType, TypeString>
type ConditionEdge = Edge<ConditionEdgeData, 'condition'>;

// Union type for all app edges
type AppEdge = BuiltInEdge | ConditionEdge;

// Type-safe edge component
function ConditionEdgeComponent(props: EdgeProps<ConditionEdge>) {
  // props.data.condition -- string ✅
  return (/* ... */);
}
```

## Type-Safe Callbacks

```tsx
// Pass union types to callback generics
const onNodeClick = useCallback<(event: React.MouseEvent, node: AppNode) => void>(
  (event, node) => {
    // node.type is 'start' | 'end' | 'agent' | 'gateway'
    if (node.type === 'agent') {
      // TypeScript narrows: node is AgentNode
      console.log(node.data.agent_id);
    }
  },
  [],
);

const onNodeDrag: OnNodeDrag<AppNode> = useCallback((event, node) => {
  if (node.type === 'gateway') {
    console.log(node.data.gateway_type);
  }
}, []);
```

## Type-Safe Hooks

```tsx
// useReactFlow with generic types
const { getNodes, getEdges, setNodes, setEdges } = useReactFlow<AppNode, AppEdge>();

// getNodes() returns AppNode[]
// getEdges() returns AppEdge[]

// updateNodeData is type-safe
const { updateNodeData } = useReactFlow<AppNode, AppEdge>();
updateNodeData('agent-1', { status: 'running' });
```

## Type Guards

Create reusable type narrowing functions:

```tsx
function isAgentNode(node: AppNode): node is AgentNode {
  return node.type === 'agent';
}

function isGatewayNode(node: AppNode): node is GatewayNode {
  return node.type === 'gateway';
}

function isConditionEdge(edge: AppEdge): edge is ConditionEdge {
  return edge.type === 'condition';
}

// Usage:
const agentNodes = nodes.filter(isAgentNode);
// agentNodes is AgentNode[] - fully typed
```

## nodeTypes / edgeTypes Typing

```tsx
import type { NodeTypes, EdgeTypes } from '@xyflow/react';

const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  agent: AgentNode,
  gateway: GatewayNode,
} satisfies NodeTypes;

const edgeTypes: EdgeTypes = {
  condition: ConditionEdge,
} satisfies EdgeTypes;
```

## Type-Safe State Management (Zustand)

```tsx
import { create } from 'zustand';
import type { OnNodesChange, OnEdgesChange, OnConnect } from '@xyflow/react';
import { applyNodeChanges, applyEdgeChanges, addEdge } from '@xyflow/react';

type WorkflowState = {
  nodes: AppNode[];
  edges: AppEdge[];
  onNodesChange: OnNodesChange<AppNode>;
  onEdgesChange: OnEdgesChange<AppEdge>;
  onConnect: OnConnect;
  setNodes: (nodes: AppNode[]) => void;
  setEdges: (edges: AppEdge[]) => void;
  updateNodeData: <T extends AppNode['type']>(
    id: string,
    data: Partial<Extract<AppNode, { type: T }>['data']>
  ) => void;
};

const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: [],
  edges: [],
  onNodesChange: (changes) =>
    set({ nodes: applyNodeChanges(changes, get().nodes) }),
  onEdgesChange: (changes) =>
    set({ edges: applyEdgeChanges(changes, get().edges) }),
  onConnect: (connection) =>
    set({ edges: addEdge(connection, get().edges) }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  updateNodeData: (id, data) =>
    set({
      nodes: get().nodes.map((node) =>
        node.id === id ? { ...node, data: { ...node.data, ...data } } : node
      ),
    }),
}));
```

## ReactFlow Component with Full Types

```tsx
<ReactFlow<AppNode, AppEdge>
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}
  edgeTypes={edgeTypes}
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
  onConnect={onConnect}
  onNodeClick={onNodeClick}
  isValidConnection={isValidConnection}
  fitView
>
  <Controls />
  <MiniMap nodeColor={getNodeColor} />
  <Background />
</ReactFlow>
```

## Common Type Pitfalls

| Issue | Wrong | Correct |
|-------|-------|---------|
| Node data access | `node.data.x` without narrowing | `if (node.type === 'agent') node.data.agent_id` |
| Missing BuiltInNode | `type AppNode = AgentNode` | `type AppNode = BuiltInNode \| AgentNode` |
| nodeTypes inside component | `const nodeTypes = { ... }` inside | Define outside or use `useMemo` |
| Mutating state | `nodes[0].data.x = 'y'` | `setNodes(nodes.map(...))` |
