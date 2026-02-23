# Custom Nodes Guide

## Creating a Custom Node

Custom nodes are React components wrapped by React Flow's interactive container.

### Step 1: Define the Component

```tsx
import { memo } from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';

// Define the node data type
type AgentNodeData = {
  label: string;
  agent_id: string | null;
  config: Record<string, unknown>;
  status?: 'idle' | 'running' | 'completed' | 'error';
};

// Define the node type
type AgentNode = Node<AgentNodeData, 'agent'>;

// The component receives NodeProps with your data type
function AgentNodeComponent({ data, selected }: NodeProps<AgentNode>) {
  return (
    <div className={`agent-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />

      <div className="node-header">
        <span className="node-icon">🤖</span>
        <span className="node-label">{data.label}</span>
      </div>

      {data.agent_id && (
        <div className="node-body">
          <span className="agent-id">{data.agent_id}</span>
        </div>
      )}

      {data.status && (
        <div className={`node-status ${data.status}`}>
          {data.status}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

// ALWAYS memo custom nodes for performance
export const AgentNode = memo(AgentNodeComponent);
```

### Step 2: Register Node Types (OUTSIDE Component)

```tsx
import { AgentNode } from './nodes/AgentNode';
import { StartNode } from './nodes/StartNode';
import { EndNode } from './nodes/EndNode';
import { GatewayNode } from './nodes/GatewayNode';

// CRITICAL: Define outside the component to prevent infinite re-renders
const nodeTypes = {
  start: StartNode,
  end: EndNode,
  agent: AgentNode,
  gateway: GatewayNode,
};
```

### Step 3: Use in ReactFlow

```tsx
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}
  // ...
/>
```

### Step 4: Create Nodes with Custom Type

```tsx
const nodes: Node[] = [
  {
    id: 'agent-1',
    type: 'agent',           // matches nodeTypes key
    position: { x: 250, y: 100 },
    data: {
      label: 'Customer Support Agent',
      agent_id: 'uuid-here',
      config: { max_tokens: 1000 },
    },
  },
];
```

## Handle Component

Handles are connection points on nodes.

### Basic Usage
```tsx
import { Handle, Position } from '@xyflow/react';

// Single source and target
<Handle type="target" position={Position.Top} />
<Handle type="source" position={Position.Bottom} />
```

### Multiple Handles (for Gateway Nodes)
```tsx
// Each handle needs a unique ID when there are multiple of same type
<Handle type="target" position={Position.Top} id="input" />
<Handle type="source" position={Position.Bottom} id="default" />
<Handle type="source" position={Position.Right} id="condition-a" />
<Handle type="source" position={Position.Left} id="condition-b" />
```

### Handle with Connection Validation
```tsx
<Handle
  type="source"
  position={Position.Bottom}
  isConnectable={true}
  isConnectableStart={true}
  isConnectableEnd={false}
/>
```

### Connecting to Specific Handles
```tsx
const edges = [
  {
    id: 'e1',
    source: 'gateway-1',
    sourceHandle: 'condition-a',    // matches Handle id
    target: 'agent-1',
    targetHandle: 'input',          // matches Handle id
  },
];
```

### Handle Positions
```
Position.Top     - Top center of node
Position.Bottom  - Bottom center of node
Position.Left    - Left center of node
Position.Right   - Right center of node
```

### Dynamic Handles
When handles are added/removed programmatically, call `useUpdateNodeInternals`:
```tsx
import { useUpdateNodeInternals } from '@xyflow/react';

const updateNodeInternals = useUpdateNodeInternals();

// After adding/removing handles:
updateNodeInternals(nodeId);
```

### Hidden Handles
Use `visibility: hidden` or `opacity: 0`, NOT `display: none` (breaks dimension calculations).

## Interactive Elements Inside Nodes

### Preventing Drag on Inputs
```tsx
function AgentNode({ data }: NodeProps) {
  return (
    <div className="agent-node">
      <Handle type="target" position={Position.Top} />

      {/* className="nodrag" prevents node drag when interacting */}
      <input
        className="nodrag"
        value={data.label}
        onChange={(e) => { /* update */ }}
      />

      {/* className="nowheel" prevents zoom when scrolling */}
      <select className="nodrag nowheel">
        <option>Option 1</option>
      </select>

      {/* className="nopan" prevents panning when clicking */}
      <button className="nodrag nopan" onClick={onDelete}>
        Delete
      </button>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
```

## IPA Platform Custom Node Patterns

### StartNode
```tsx
function StartNodeComponent({ selected }: NodeProps) {
  return (
    <div className={`start-node ${selected ? 'selected' : ''}`}>
      <div className="node-content">
        <Play size={16} />
        <span>Start</span>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
export const StartNode = memo(StartNodeComponent);
```

### EndNode
```tsx
function EndNodeComponent({ selected }: NodeProps) {
  return (
    <div className={`end-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <Square size={16} />
        <span>End</span>
      </div>
    </div>
  );
}
export const EndNode = memo(EndNodeComponent);
```

### GatewayNode (Multiple Outputs)
```tsx
type GatewayNodeData = {
  label: string;
  gateway_type: 'exclusive' | 'parallel' | 'inclusive';
  conditions: Array<{ handle_id: string; expression: string; label: string }>;
};

function GatewayNodeComponent({ data, selected }: NodeProps<Node<GatewayNodeData, 'gateway'>>) {
  return (
    <div className={`gateway-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />

      <div className="node-content">
        <GitBranch size={16} />
        <span>{data.label}</span>
        <Badge>{data.gateway_type}</Badge>
      </div>

      {/* Dynamic output handles based on conditions */}
      {data.conditions.map((cond, i) => (
        <Handle
          key={cond.handle_id}
          type="source"
          position={Position.Bottom}
          id={cond.handle_id}
          style={{ left: `${((i + 1) / (data.conditions.length + 1)) * 100}%` }}
        />
      ))}

      {/* Default output */}
      <Handle type="source" position={Position.Right} id="default" />
    </div>
  );
}
export const GatewayNode = memo(GatewayNodeComponent);
```

## NodeToolbar (Contextual Actions)

```tsx
import { NodeToolbar, Position } from '@xyflow/react';

function AgentNodeComponent({ data, selected }: NodeProps) {
  return (
    <>
      <NodeToolbar isVisible={selected} position={Position.Top}>
        <button onClick={onConfigure}>Configure</button>
        <button onClick={onDuplicate}>Duplicate</button>
        <button onClick={onDelete}>Delete</button>
      </NodeToolbar>

      <div className="agent-node">
        {/* node content */}
      </div>
    </>
  );
}
```

## Performance Best Practices

1. **Always `memo()` custom nodes** - Prevents unnecessary re-renders
2. **Define `nodeTypes` outside component** - Prevents object recreation on every render
3. **Use `useCallback` for handlers** - Stable function references
4. **Avoid heavy computation in node render** - Move to effects or stores
5. **Use `useUpdateNodeInternals` sparingly** - Only when handles change dynamically
