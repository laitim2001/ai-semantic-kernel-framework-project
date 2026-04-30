// =============================================================================
// IPA Platform - Condition Node Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow node for conditional branching (gateway).
// Visual: Diamond shape with condition icon.
// =============================================================================

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { GitBranch } from 'lucide-react';

export interface ConditionNodeData {
  label: string;
  gatewayType?: 'exclusive' | 'parallel' | 'inclusive';
  condition?: string;
  status?: 'idle' | 'running' | 'completed' | 'failed';
}

function ConditionNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as unknown as ConditionNodeData;
  const gatewayType = nodeData.gatewayType || 'exclusive';
  const status = nodeData.status || 'idle';

  const typeIcons: Record<string, string> = {
    exclusive: 'X',
    parallel: '+',
    inclusive: 'O',
  };

  const statusColors: Record<string, string> = {
    idle: 'bg-amber-50 border-amber-300',
    running: 'bg-amber-100 border-amber-500 animate-pulse',
    completed: 'bg-green-50 border-green-400',
    failed: 'bg-red-50 border-red-400',
  };

  return (
    <div
      className={`
        relative w-[120px] h-[120px] flex items-center justify-center
        ${selected ? 'drop-shadow-lg' : ''}
      `}
    >
      {/* Diamond shape via rotated inner div */}
      <div
        className={`
          absolute w-[85px] h-[85px] rotate-45 rounded-md border-2 shadow-sm
          ${statusColors[status]}
          ${selected ? 'ring-2 ring-amber-500 ring-offset-2' : ''}
        `}
      />

      {/* Content (not rotated) */}
      <div className="relative z-10 flex flex-col items-center gap-1">
        <GitBranch className="w-4 h-4 text-amber-600" />
        <div className="text-xs font-bold text-amber-700">
          {typeIcons[gatewayType]}
        </div>
        <div className="text-[10px] font-medium text-gray-700 text-center max-w-[80px] truncate">
          {nodeData.label || 'Condition'}
        </div>
      </div>

      <Handle
        type="target"
        position={Position.Top}
        className="!bg-amber-400 !w-3 !h-3 !border-2 !border-white"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-amber-400 !w-3 !h-3 !border-2 !border-white"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!bg-amber-400 !w-3 !h-3 !border-2 !border-white"
      />
      <Handle
        type="source"
        position={Position.Left}
        id="left"
        className="!bg-amber-400 !w-3 !h-3 !border-2 !border-white"
      />
    </div>
  );
}

export const ConditionNode = memo(ConditionNodeComponent);
