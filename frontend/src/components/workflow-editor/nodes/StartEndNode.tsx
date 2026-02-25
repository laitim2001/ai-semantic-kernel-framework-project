// =============================================================================
// IPA Platform - Start/End Node Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow node for workflow start and end points.
// Visual: Circle (start) / Double circle (end).
// =============================================================================

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Play, Square } from 'lucide-react';

export interface StartEndNodeData {
  label: string;
  nodeRole: 'start' | 'end';
}

function StartEndNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as unknown as StartEndNodeData;
  const isStart = nodeData.nodeRole === 'start';

  return (
    <div
      className={`
        flex items-center justify-center transition-all
        ${isStart ? 'w-16 h-16' : 'w-[72px] h-[72px]'}
      `}
    >
      {/* Outer circle (end node only) */}
      {!isStart && (
        <div
          className={`
            absolute w-[72px] h-[72px] rounded-full border-2 border-gray-400
            ${selected ? 'ring-2 ring-gray-500 ring-offset-2' : ''}
          `}
        />
      )}

      {/* Main circle */}
      <div
        className={`
          flex flex-col items-center justify-center rounded-full border-2 shadow-sm
          ${isStart
            ? `w-16 h-16 bg-indigo-50 border-indigo-400 ${selected ? 'ring-2 ring-indigo-500 ring-offset-2' : ''}`
            : 'w-14 h-14 bg-gray-50 border-gray-400'
          }
        `}
      >
        {isStart ? (
          <Play className="w-5 h-5 text-indigo-600 ml-0.5" />
        ) : (
          <Square className="w-4 h-4 text-gray-600" />
        )}
        <span className={`text-[10px] font-medium mt-0.5 ${isStart ? 'text-indigo-700' : 'text-gray-600'}`}>
          {nodeData.label || (isStart ? 'Start' : 'End')}
        </span>
      </div>

      {/* Handles */}
      {isStart ? (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!bg-indigo-400 !w-3 !h-3 !border-2 !border-white"
        />
      ) : (
        <Handle
          type="target"
          position={Position.Top}
          className="!bg-gray-400 !w-3 !h-3 !border-2 !border-white"
        />
      )}
    </div>
  );
}

export const StartEndNode = memo(StartEndNodeComponent);
