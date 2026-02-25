// =============================================================================
// IPA Platform - Conditional Edge Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow edge for conditional connections with expression labels.
// Visual: Dashed line with condition badge.
// =============================================================================

import { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import { GitBranch } from 'lucide-react';

function ConditionalEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  label,
  data,
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

  const edgeData = data as Record<string, unknown> | undefined;
  const condition = (edgeData?.condition as string) || (label as string) || '';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: selected ? '#f59e0b' : '#d97706',
          strokeWidth: selected ? 2.5 : 1.5,
          strokeDasharray: '6 3',
          ...style,
        }}
      />
      {condition && (
        <EdgeLabelRenderer>
          <div
            className={`
              absolute flex items-center gap-1 px-2 py-1 rounded-md text-xs
              pointer-events-all cursor-pointer
              ${selected
                ? 'bg-amber-100 text-amber-800 border border-amber-400'
                : 'bg-amber-50 text-amber-700 border border-amber-200 shadow-sm'
              }
            `}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            <GitBranch className="w-3 h-3" />
            <span className="max-w-[120px] truncate">{condition}</span>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const ConditionalEdge = memo(ConditionalEdgeComponent);
