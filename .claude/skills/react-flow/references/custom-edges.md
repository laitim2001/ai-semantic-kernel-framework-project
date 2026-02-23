# Custom Edges Guide

## Creating a Custom Edge

Custom edges are React components that render SVG paths between nodes.

### Basic Custom Edge

```tsx
import { memo } from 'react';
import {
  BaseEdge,
  getSmoothStepPath,
  type EdgeProps,
  type Edge,
} from '@xyflow/react';

type ConditionEdgeData = {
  condition: string;
  label?: string;
};

type ConditionEdge = Edge<ConditionEdgeData, 'condition'>;

function ConditionEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  markerEnd,
}: EdgeProps<ConditionEdge>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {data?.condition && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              background: '#fff',
              padding: '2px 6px',
              borderRadius: 4,
              fontSize: 11,
              border: '1px solid #ddd',
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            {data.condition}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const ConditionEdge = memo(ConditionEdgeComponent);
```

### Register Edge Types (OUTSIDE Component)

```tsx
import { ConditionEdge } from './edges/ConditionEdge';

// CRITICAL: Define outside component
const edgeTypes = {
  condition: ConditionEdge,
};
```

## Path Utility Functions

React Flow provides four built-in path generators:

```tsx
import {
  getBezierPath,        // Smooth bezier curve
  getSimpleBezierPath,  // Simplified bezier
  getSmoothStepPath,    // Rounded right-angle path (recommended for workflows)
  getStraightPath,      // Direct line
} from '@xyflow/react';

// All return [path: string, labelX: number, labelY: number, offsetX: number, offsetY: number]
const [edgePath, labelX, labelY] = getSmoothStepPath({
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  borderRadius: 8,      // smoothstep only
  offset: 0,            // smoothstep only
});
```

### Path Type Recommendations for IPA Platform

| Edge Context | Recommended Path | Reason |
|-------------|-----------------|--------|
| Sequential flow | `getSmoothStepPath` | Clean right-angle workflow appearance |
| Condition branches | `getBezierPath` | Smooth curves for diverging paths |
| Loop/feedback | `getBezierPath` | Handles reverse direction gracefully |
| Direct connection | `getStraightPath` | Minimal visual for simple links |

## Edge with Delete Button

```tsx
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, useReactFlow } from '@xyflow/react';

function DeletableEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }: EdgeProps) {
  const { setEdges } = useReactFlow();
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const onDelete = () => {
    setEdges((edges) => edges.filter((e) => e.id !== id));
  };

  return (
    <>
      <BaseEdge id={id} path={edgePath} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <button className="edge-delete-btn" onClick={onDelete}>
            ×
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
```

## Edge with Condition Editor

For IPA Platform gateway edges that need condition expressions:

```tsx
function EditableConditionEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, data,
}: EdgeProps<ConditionEdge>) {
  const { setEdges } = useReactFlow();
  const [editing, setEditing] = useState(false);
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const updateCondition = (condition: string) => {
    setEdges((edges) =>
      edges.map((e) =>
        e.id === id ? { ...e, data: { ...e.data, condition } } : e
      )
    );
  };

  return (
    <>
      <BaseEdge id={id} path={edgePath} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          {editing ? (
            <input
              className="nodrag"
              defaultValue={data?.condition || ''}
              onBlur={(e) => {
                updateCondition(e.target.value);
                setEditing(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  updateCondition(e.currentTarget.value);
                  setEditing(false);
                }
              }}
              autoFocus
            />
          ) : (
            <div
              className="edge-condition-label"
              onDoubleClick={() => setEditing(true)}
            >
              {data?.condition || 'click to set condition'}
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
```

## Animated Edges

```tsx
// Built-in animation via edge data
const edges = [
  {
    id: 'e1',
    source: 'node-1',
    target: 'node-2',
    animated: true,       // Adds animated dash pattern
    style: { stroke: '#0088cc' },
  },
];
```

## Edge Markers (Arrows)

```tsx
import { MarkerType } from '@xyflow/react';

const edges = [
  {
    id: 'e1',
    source: 'node-1',
    target: 'node-2',
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 20,
      height: 20,
      color: '#333',
    },
  },
];
```

## Custom SVG Paths

For non-standard edge shapes, build SVG path strings manually:

```tsx
function WavyEdge({ sourceX, sourceY, targetX, targetY, id }: EdgeProps) {
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;

  // SVG path commands:
  // M = Move to, L = Line to, Q = Quadratic bezier, C = Cubic bezier
  const edgePath = `M ${sourceX} ${sourceY} Q ${midX} ${sourceY} ${midX} ${midY} Q ${midX} ${targetY} ${targetX} ${targetY}`;

  return <BaseEdge id={id} path={edgePath} />;
}
```

## Performance Notes

1. **Always `memo()` custom edges** - Same as nodes
2. **Define `edgeTypes` outside component** - Prevents recreation
3. **Use `EdgeLabelRenderer` for HTML labels** - It's a portal, efficient rendering
4. **Avoid heavy computation in edge render** - Edges re-render on every connected node move
