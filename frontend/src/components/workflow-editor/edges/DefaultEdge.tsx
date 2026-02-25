// =============================================================================
// IPA Platform - Default Edge Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow edge for standard connections between nodes.
// =============================================================================

import { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';

function DefaultEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  label,
  selected,
  style,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: selected ? '#3b82f6' : '#94a3b8',
          strokeWidth: selected ? 2.5 : 1.5,
          ...style,
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className={`
              absolute px-2 py-0.5 rounded text-xs font-medium
              pointer-events-all cursor-pointer
              ${selected
                ? 'bg-blue-100 text-blue-700 border border-blue-300'
                : 'bg-white text-gray-600 border border-gray-200 shadow-sm'
              }
            `}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const DefaultEdge = memo(DefaultEdgeComponent);
