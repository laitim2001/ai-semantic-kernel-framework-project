# React Flow Core API Reference

## ReactFlow Component Props

### Data Props
```tsx
<ReactFlow
  // Controlled mode (recommended)
  nodes={nodes}                    // Node[] - current nodes
  edges={edges}                    // Edge[] - current edges

  // Uncontrolled mode (prototyping only)
  defaultNodes={initialNodes}      // Node[] - initial nodes
  defaultEdges={initialEdges}      // Edge[] - initial edges

  // Custom type registrations (MUST define outside component)
  nodeTypes={nodeTypes}            // Record<string, ComponentType<NodeProps>>
  edgeTypes={edgeTypes}            // Record<string, ComponentType<EdgeProps>>

  // Node origin point: [0,0]=top-left, [0.5,0.5]=center
  nodeOrigin={[0, 0]}

  // Color scheme
  colorMode="light"                // 'light' | 'dark' | 'system'
/>
```

### Viewport Props
```tsx
<ReactFlow
  defaultViewport={{ x: 0, y: 0, zoom: 1 }}
  fitView                          // Auto-fit all nodes on mount
  fitViewOptions={{ padding: 0.2 }}
  minZoom={0.5}
  maxZoom={2}
  snapToGrid={false}
  snapGrid={[15, 15]}              // Grid snapping increment [x, y]
  translateExtent={[[-Infinity, -Infinity], [Infinity, Infinity]]}
  nodeExtent={[[-Infinity, -Infinity], [Infinity, Infinity]]}
/>
```

### Edge Props
```tsx
<ReactFlow
  elevateEdgesOnSelect={false}     // Raise z-index when selected
  defaultMarkerColor="#b1b1b7"     // Arrow marker color
  edgesReconnectable={true}        // Allow edge reconnection
  reconnectRadius={10}             // Reconnect trigger distance (px)
  defaultEdgeOptions={{            // Default props for new edges
    type: 'smoothstep',
    animated: true,
  }}
/>
```

### Interaction Props
```tsx
<ReactFlow
  nodesDraggable={true}
  nodesConnectable={true}
  nodesFocusable={true}
  elementsSelectable={true}
  autoPanOnNodeDrag={true}
  autoPanOnConnect={true}
  panOnDrag={true}                 // boolean or number[] for mouse buttons
  selectionOnDrag={false}
  zoomOnScroll={true}
  zoomOnPinch={true}
  zoomOnDoubleClick={true}
  connectOnClick={true}            // Click-based connection mode
  connectionMode="strict"          // 'strict' | 'loose'
/>
```

### Keyboard Props
```tsx
<ReactFlow
  deleteKeyCode="Backspace"        // null to disable
  selectionKeyCode="Shift"
  multiSelectionKeyCode="Meta"     // Ctrl on Windows
  zoomActivationKeyCode="Meta"
  panActivationKeyCode="Space"
/>
```

### Connection Line Props
```tsx
<ReactFlow
  connectionLineType="bezier"      // 'bezier' | 'smoothstep' | 'step' | 'straight'
  connectionLineStyle={{ stroke: '#ddd' }}
  connectionRadius={20}            // Drop zone radius (px)
  connectionLineComponent={CustomConnectionLine}  // Custom component
/>
```

### CSS Class Props
```tsx
<ReactFlow
  noPanClassName="nopan"           // Elements with this class prevent panning
  noDragClassName="nodrag"         // Elements with this class prevent node dragging
  noWheelClassName="nowheel"       // Elements with this class prevent scroll zoom
/>
```

## Event Handlers

### Node Events
```tsx
<ReactFlow
  onNodesChange={onNodesChange}           // OnNodesChange - REQUIRED for controlled mode
  onNodeClick={(event, node) => {}}
  onNodeDoubleClick={(event, node) => {}}
  onNodeDragStart={(event, node, nodes) => {}}
  onNodeDrag={(event, node, nodes) => {}}
  onNodeDragStop={(event, node, nodes) => {}}
  onNodeMouseEnter={(event, node) => {}}
  onNodeMouseMove={(event, node) => {}}
  onNodeMouseLeave={(event, node) => {}}
  onNodeContextMenu={(event, node) => {}}
  onNodesDelete={(nodes) => {}}
/>
```

### Edge Events
```tsx
<ReactFlow
  onEdgesChange={onEdgesChange}           // OnEdgesChange - REQUIRED for controlled mode
  onEdgeClick={(event, edge) => {}}
  onEdgeDoubleClick={(event, edge) => {}}
  onEdgeContextMenu={(event, edge) => {}}
  onEdgeMouseEnter={(event, edge) => {}}
  onEdgeMouseMove={(event, edge) => {}}
  onEdgeMouseLeave={(event, edge) => {}}
  onEdgesDelete={(edges) => {}}
  onReconnect={(oldEdge, newConnection) => {}}
  onReconnectStart={(event, edge, handleType) => {}}
  onReconnectEnd={(event, edge, handleType) => {}}
/>
```

### Connection Events
```tsx
<ReactFlow
  onConnect={onConnect}                   // OnConnect - fires when connection completes
  onConnectStart={(event, params) => {}}  // Connection drag started
  onConnectEnd={(event) => {}}            // Connection drag ended
  isValidConnection={(connection) => {    // Validate new connections
    return connection.source !== connection.target;
  }}
/>
```

### Viewport Events
```tsx
<ReactFlow
  onMoveStart={(event, viewport) => {}}
  onMove={(event, viewport) => {}}
  onMoveEnd={(event, viewport) => {}}
/>
```

### Pane Events
```tsx
<ReactFlow
  onPaneClick={(event) => {}}
  onPaneContextMenu={(event) => {}}
  onPaneScroll={(event) => {}}
  onPaneMouseMove={(event) => {}}
  onPaneMouseEnter={(event) => {}}
  onPaneMouseLeave={(event) => {}}
/>
```

### Selection Events
```tsx
<ReactFlow
  onSelectionChange={({ nodes, edges }) => {}}
  onSelectionDragStart={(event, nodes) => {}}
  onSelectionDrag={(event, nodes) => {}}
  onSelectionDragStop={(event, nodes) => {}}
  onSelectionContextMenu={(event, nodes) => {}}
/>
```

## Utility Functions

```tsx
import {
  applyNodeChanges,   // (changes: NodeChange[], nodes: Node[]) => Node[]
  applyEdgeChanges,   // (changes: EdgeChange[], edges: Edge[]) => Edge[]
  addEdge,            // (connection: Connection, edges: Edge[]) => Edge[]
  getOutgoers,        // (node: Node, nodes: Node[], edges: Edge[]) => Node[]
  getIncomers,        // (node: Node, nodes: Node[], edges: Edge[]) => Node[]
  getConnectedEdges,  // (nodes: Node[], edges: Edge[]) => Edge[]
  isNode,             // (element: any) => element is Node
  isEdge,             // (element: any) => element is Edge
} from '@xyflow/react';
```

## Built-in Components

### Background
```tsx
import { Background, BackgroundVariant } from '@xyflow/react';

<Background
  variant={BackgroundVariant.Dots}  // 'dots' | 'lines' | 'cross'
  gap={12}                           // Grid spacing
  size={1}                           // Dot/line size
  color="#aaa"                       // Pattern color
/>
```

### Controls
```tsx
import { Controls } from '@xyflow/react';

<Controls
  showZoom={true}
  showFitView={true}
  showInteractive={true}
  position="bottom-left"
/>
```

### MiniMap
```tsx
import { MiniMap } from '@xyflow/react';

<MiniMap
  nodeColor={(node) => {
    switch (node.type) {
      case 'start': return '#00cc00';
      case 'end': return '#cc0000';
      case 'agent': return '#0088cc';
      case 'gateway': return '#cc8800';
      default: return '#eee';
    }
  }}
  maskColor="rgba(0,0,0,0.1)"
  position="bottom-right"
/>
```

### Panel
```tsx
import { Panel } from '@xyflow/react';

<Panel position="top-left">
  <h3>Workflow Editor</h3>
  <button onClick={onSave}>Save</button>
</Panel>
```

### NodeToolbar
```tsx
import { NodeToolbar } from '@xyflow/react';

// Inside a custom node component:
<NodeToolbar isVisible={selected} position={Position.Top}>
  <button onClick={onDelete}>Delete</button>
  <button onClick={onDuplicate}>Duplicate</button>
</NodeToolbar>
```

### NodeResizer
```tsx
import { NodeResizer } from '@xyflow/react';

// Inside a custom node component:
<NodeResizer
  minWidth={100}
  minHeight={50}
  isVisible={selected}
/>
```

### EdgeLabelRenderer
```tsx
import { EdgeLabelRenderer } from '@xyflow/react';

// Inside a custom edge component:
<EdgeLabelRenderer>
  <div
    style={{
      position: 'absolute',
      transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
      pointerEvents: 'all',
    }}
    className="nodrag nopan"
  >
    <button onClick={() => onEdgeDelete(id)}>x</button>
  </div>
</EdgeLabelRenderer>
```

## Built-in Node Types

| Type | Description | Handles |
|------|-------------|---------|
| `default` | Simple node with label | 1 source (bottom), 1 target (top) |
| `input` | Input-only node | 1 source (bottom), no target |
| `output` | Output-only node | No source, 1 target (top) |
| `group` | Container for child nodes | No handles by default |

## Built-in Edge Types

| Type | Description | Path Shape |
|------|-------------|------------|
| `default` | Bezier curve | Smooth curve |
| `straight` | Direct line | Straight line |
| `step` | Right-angle path | 90-degree turns |
| `smoothstep` | Rounded step path | Rounded 90-degree turns |
