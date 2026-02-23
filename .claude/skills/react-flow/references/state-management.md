# State Management for React Flow

## Approach Options

| Approach | When to Use |
|----------|-------------|
| Local useState | Prototyping, simple editors |
| Zustand store (recommended) | Production apps, shared state across components |
| Redux / Recoil / Jotai | When project already uses these |

React Flow internally uses Zustand, making it the natural choice.

## Zustand Store Pattern (Recommended for IPA Platform)

### Store Definition

```tsx
// stores/workflowEditorStore.ts
import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from '@xyflow/react';

// Import your app-specific node/edge types
import type { AppNode, AppEdge } from '@/types/workflow';

type WorkflowEditorState = {
  // React Flow state
  nodes: AppNode[];
  edges: AppEdge[];

  // React Flow handlers
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;

  // Setters
  setNodes: (nodes: AppNode[]) => void;
  setEdges: (edges: AppEdge[]) => void;

  // Node operations
  addNode: (node: AppNode) => void;
  removeNode: (id: string) => void;
  updateNodeData: (id: string, data: Partial<AppNode['data']>) => void;

  // Edge operations
  removeEdge: (id: string) => void;
  updateEdgeData: (id: string, data: Partial<AppEdge['data']>) => void;

  // Workflow metadata
  workflowName: string;
  workflowDescription: string;
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  setWorkflowName: (name: string) => void;
  setWorkflowDescription: (desc: string) => void;
  setTriggerType: (type: string) => void;
  setTriggerConfig: (config: Record<string, unknown>) => void;

  // Workflow lifecycle
  loadWorkflow: (definition: GraphDefinition) => void;
  toGraphDefinition: () => GraphDefinition;
  resetEditor: () => void;

  // UI state
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  isDirty: boolean;
};

const initialNodes: AppNode[] = [
  {
    id: 'start',
    type: 'start',
    position: { x: 250, y: 0 },
    data: { label: 'Start' },
  },
  {
    id: 'end',
    type: 'end',
    position: { x: 250, y: 400 },
    data: { label: 'End' },
  },
];

const initialEdges: AppEdge[] = [];

export const useWorkflowEditorStore = create<WorkflowEditorState>((set, get) => ({
  // React Flow state
  nodes: initialNodes,
  edges: initialEdges,

  // React Flow handlers - MUST create new arrays, not mutate
  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
      isDirty: true,
    });
  },
  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
      isDirty: true,
    });
  },
  onConnect: (connection) => {
    set({
      edges: addEdge(
        { ...connection, type: 'condition', data: { condition: '' } },
        get().edges,
      ),
      isDirty: true,
    });
  },

  // Setters
  setNodes: (nodes) => set({ nodes, isDirty: true }),
  setEdges: (edges) => set({ edges, isDirty: true }),

  // Node operations
  addNode: (node) => set({ nodes: [...get().nodes, node], isDirty: true }),
  removeNode: (id) => {
    if (id === 'start' || id === 'end') return; // Protect start/end
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
      isDirty: true,
    });
  },
  updateNodeData: (id, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === id
          ? { ...node, data: { ...node.data, ...data } }
          : node,
      ),
      isDirty: true,
    });
  },

  // Edge operations
  removeEdge: (id) => set({
    edges: get().edges.filter((e) => e.id !== id),
    isDirty: true,
  }),
  updateEdgeData: (id, data) => {
    set({
      edges: get().edges.map((edge) =>
        edge.id === id
          ? { ...edge, data: { ...edge.data, ...data } }
          : edge,
      ),
      isDirty: true,
    });
  },

  // Workflow metadata
  workflowName: '',
  workflowDescription: '',
  triggerType: 'manual',
  triggerConfig: {},
  setWorkflowName: (name) => set({ workflowName: name, isDirty: true }),
  setWorkflowDescription: (desc) => set({ workflowDescription: desc, isDirty: true }),
  setTriggerType: (type) => set({ triggerType: type, isDirty: true }),
  setTriggerConfig: (config) => set({ triggerConfig: config, isDirty: true }),

  // Workflow lifecycle
  loadWorkflow: (definition) => {
    const { nodes, edges } = fromGraphDefinition(definition);
    set({ nodes, edges, isDirty: false });
  },

  toGraphDefinition: () => {
    const { nodes, edges } = get();
    return toGraphDefinition(nodes, edges);
  },

  resetEditor: () => set({
    nodes: initialNodes,
    edges: initialEdges,
    workflowName: '',
    workflowDescription: '',
    triggerType: 'manual',
    triggerConfig: {},
    selectedNodeId: null,
    isDirty: false,
  }),

  // UI state
  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  isDirty: false,
}));
```

### Using Store in Components

```tsx
// WorkflowEditor.tsx - Main editor component
import { useWorkflowEditorStore } from '@/stores/workflowEditorStore';

export function WorkflowEditor() {
  const {
    nodes, edges,
    onNodesChange, onEdgesChange, onConnect,
  } = useWorkflowEditorStore();

  return (
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
      <Background />
    </ReactFlow>
  );
}
```

```tsx
// NodeConfigPanel.tsx - Side panel that edits selected node
import { useWorkflowEditorStore } from '@/stores/workflowEditorStore';

export function NodeConfigPanel() {
  const { selectedNodeId, nodes, updateNodeData } = useWorkflowEditorStore();
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  if (!selectedNode) return <div>Select a node to configure</div>;

  return (
    <div>
      <h3>{selectedNode.data.label}</h3>
      {selectedNode.type === 'agent' && (
        <AgentConfig
          agentId={selectedNode.data.agent_id}
          onChange={(agent_id) => updateNodeData(selectedNode.id, { agent_id })}
        />
      )}
    </div>
  );
}
```

```tsx
// Inside a custom node - access store directly
import { useWorkflowEditorStore } from '@/stores/workflowEditorStore';

function AgentNode({ id, data }: NodeProps<AgentNode>) {
  const updateNodeData = useWorkflowEditorStore((s) => s.updateNodeData);

  return (
    <div>
      <input
        className="nodrag"
        value={data.label}
        onChange={(e) => updateNodeData(id, { label: e.target.value })}
      />
    </div>
  );
}
```

## State Immutability Rules

React Flow detects changes via reference equality. You MUST create new objects.

```tsx
// ✅ CORRECT - new object
set({
  nodes: get().nodes.map((n) =>
    n.id === id ? { ...n, data: { ...n.data, ...newData } } : n
  ),
});

// ❌ WRONG - mutation (React Flow won't detect change)
const nodes = get().nodes;
const node = nodes.find((n) => n.id === id);
node.data.label = 'new label';  // Mutation!
set({ nodes });
```

## Saving & Loading Workflows

### Save to Backend
```tsx
const saveWorkflow = async () => {
  const store = useWorkflowEditorStore.getState();
  const payload = {
    name: store.workflowName,
    description: store.workflowDescription,
    trigger_type: store.triggerType,
    trigger_config: store.triggerConfig,
    graph_definition: store.toGraphDefinition(),
  };

  await api.post('/workflows/', payload);
  set({ isDirty: false });
};
```

### Load from Backend
```tsx
const loadWorkflow = async (id: string) => {
  const workflow = await api.get(`/workflows/${id}`);
  const store = useWorkflowEditorStore.getState();

  store.setWorkflowName(workflow.name);
  store.setWorkflowDescription(workflow.description);
  store.setTriggerType(workflow.trigger_type);
  store.setTriggerConfig(workflow.trigger_config);
  store.loadWorkflow(workflow.graph_definition);
};
```

## Undo/Redo (Advanced)

Use Zustand's `temporal` middleware for undo/redo:

```bash
npm install zundo
```

```tsx
import { temporal } from 'zundo';

const useWorkflowEditorStore = create<WorkflowEditorState>()(
  temporal(
    (set, get) => ({
      // ... store definition
    }),
    {
      // Only track node/edge changes, not UI state
      partialize: (state) => ({
        nodes: state.nodes,
        edges: state.edges,
      }),
    },
  ),
);

// Usage:
const { undo, redo } = useWorkflowEditorStore.temporal.getState();
```
