# React Flow Hooks API Reference

## Core Hooks

### useReactFlow()

The primary hook for accessing the React Flow instance. Provides methods to query and manipulate the flow.

```tsx
import { useReactFlow } from '@xyflow/react';

function MyComponent() {
  const {
    // State getters
    getNodes,            // () => Node[]
    getEdges,            // () => Edge[]
    getNode,             // (id: string) => Node | undefined
    getEdge,             // (id: string) => Edge | undefined

    // State setters
    setNodes,            // (nodes: Node[] | ((nodes: Node[]) => Node[])) => void
    setEdges,            // (edges: Edge[] | ((edges: Edge[]) => Edge[])) => void
    addNodes,            // (nodes: Node | Node[]) => void
    addEdges,            // (edges: Edge | Edge[]) => void

    // Node data update (preferred for updating node data)
    updateNodeData,      // (id: string, data: Partial<NodeData>) => void

    // Viewport
    getViewport,         // () => Viewport
    setViewport,         // (viewport: Viewport, options?: ViewportHelperOptions) => void
    fitView,             // (options?: FitViewOptions) => void
    zoomIn,              // (options?) => void
    zoomOut,             // (options?) => void
    zoomTo,              // (zoom: number, options?) => void
    setCenter,           // (x: number, y: number, options?) => void
    fitBounds,           // (bounds: Rect, options?) => void

    // Coordinate conversion
    screenToFlowPosition, // (position: XYPosition) => XYPosition
    flowToScreenPosition,  // (position: XYPosition) => XYPosition

    // Selection
    getSelectedNodes,    // () => Node[]
    getSelectedEdges,    // () => Edge[]

    // Deletion
    deleteElements,      // (params: { nodes?: Node[], edges?: Edge[] }) => void

    // Intersection
    getIntersectingNodes, // (node: Node, partially?: boolean) => Node[]
    isNodeIntersecting,   // (node: Node, area: Rect, partially?: boolean) => boolean
  } = useReactFlow();
}
```

**Usage example - Adding a node at click position:**
```tsx
const { screenToFlowPosition, addNodes } = useReactFlow();

const onPaneClick = useCallback((event: React.MouseEvent) => {
  const position = screenToFlowPosition({
    x: event.clientX,
    y: event.clientY,
  });

  addNodes({
    id: `node-${Date.now()}`,
    type: 'agent',
    position,
    data: { label: 'New Agent', agent_id: null, config: {} },
  });
}, [screenToFlowPosition, addNodes]);
```

### useNodes()

Returns current nodes array. Triggers re-render on ANY node change (position, selection, data).

```tsx
import { useNodes } from '@xyflow/react';

const nodes = useNodes();  // Node[]
```

**Warning**: Components using this will re-render frequently. Prefer `useReactFlow().getNodes()` for on-demand access.

### useEdges()

Returns current edges array. Same re-render caveat as `useNodes`.

```tsx
import { useEdges } from '@xyflow/react';

const edges = useEdges();  // Edge[]
```

### useNodesState()

Convenience hook combining `useState` with React Flow change handlers.

```tsx
import { useNodesState } from '@xyflow/react';

const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
// setNodes: React.Dispatch<SetStateAction<Node[]>>
// onNodesChange: OnNodesChange (already applies changes)
```

### useEdgesState()

Same pattern for edges.

```tsx
import { useEdgesState } from '@xyflow/react';

const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
```

## Node-Specific Hooks

### useNodeId()

Returns the ID of the node containing the hook. Useful inside deeply nested custom node components.

```tsx
import { useNodeId } from '@xyflow/react';

function DeepChildComponent() {
  const nodeId = useNodeId();  // string | null
  // Use nodeId to access node-specific data from store
}
```

### useUpdateNodeInternals()

Forces React Flow to recalculate node dimensions. Required after programmatically adding/removing handles.

```tsx
import { useUpdateNodeInternals } from '@xyflow/react';

const updateNodeInternals = useUpdateNodeInternals();

// After modifying handles:
useEffect(() => {
  updateNodeInternals(nodeId);
}, [handles.length]);
```

### useNodeConnections()

Returns connections for a specific node. Useful for computing flows.

```tsx
import { useNodeConnections } from '@xyflow/react';

function AgentNode() {
  const connections = useNodeConnections({
    type: 'target',    // 'source' | 'target'
    // handleId: 'specific-handle',  // optional
  });
  // connections: Connection[]
}
```

### useNodesData()

Retrieves data from specific nodes by ID. Optimized to only trigger re-renders when the data changes.

```tsx
import { useNodesData } from '@xyflow/react';

const nodesData = useNodesData(['node-1', 'node-2']);
// { id: string, type: string, data: NodeData }[]
```

## Selection & Interaction Hooks

### useOnSelectionChange()

Listen for selection changes without re-rendering on every node/edge change.

```tsx
import { useOnSelectionChange } from '@xyflow/react';

useOnSelectionChange({
  onChange: ({ nodes, edges }) => {
    console.log('Selected nodes:', nodes);
    console.log('Selected edges:', edges);
  },
});
```

### useConnection()

Returns the current in-progress connection during drag operations.

```tsx
import { useConnection } from '@xyflow/react';

function CustomHandle() {
  const connection = useConnection();
  // connection: { source, target, sourceHandle, targetHandle } | null

  const isTarget = connection?.target === nodeId;
  const isConnecting = !!connection;

  return (
    <Handle
      type="target"
      position={Position.Top}
      style={{ background: isTarget ? 'green' : isConnecting ? 'red' : '#555' }}
    />
  );
}
```

## Store Hooks

### useStore()

Access React Flow's internal Zustand store. Re-exported from Zustand.

```tsx
import { useStore } from '@xyflow/react';

// Select specific state to minimize re-renders
const nodeCount = useStore((state) => state.nodeInternals.size);
const zoom = useStore((state) => state.transform[2]);
```

### useStoreApi()

Get the store object directly for on-demand access (no re-renders).

```tsx
import { useStoreApi } from '@xyflow/react';

const store = useStoreApi();

// Read state on-demand (no subscription):
const currentNodes = store.getState().getNodes();
```

## Hook Usage Guidelines

| Need | Hook | Re-renders? |
|------|------|-------------|
| Full flow control | `useReactFlow()` | No (stable ref) |
| Read all nodes | `useNodes()` | Yes (every node change) |
| Read all edges | `useEdges()` | Yes (every edge change) |
| Read specific node data | `useNodesData(ids)` | Only when data changes |
| Node's own ID | `useNodeId()` | No |
| Selection tracking | `useOnSelectionChange()` | No (callback-based) |
| Connection in progress | `useConnection()` | During connection drag |
| Internal state | `useStore(selector)` | When selected state changes |
| On-demand state | `useStoreApi()` | No |

**Performance Rule**: Prefer `useReactFlow()` and `useStoreApi()` for imperative access. Use `useNodes()`/`useEdges()` only when you need reactive updates in the render output.
