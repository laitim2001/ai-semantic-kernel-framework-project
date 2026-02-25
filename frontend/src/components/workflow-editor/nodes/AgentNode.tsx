// =============================================================================
// IPA Platform - Agent Node Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow node for Agent execution steps.
// Visual: Blue rounded rectangle with agent icon.
// =============================================================================

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Bot, Cpu } from 'lucide-react';

export interface AgentNodeData {
  label: string;
  agentId?: string | null;
  agentType?: string;
  status?: 'idle' | 'running' | 'completed' | 'failed';
  config?: Record<string, unknown>;
}

function AgentNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as unknown as AgentNodeData;
  const status = nodeData.status || 'idle';

  const statusColors: Record<string, string> = {
    idle: 'bg-blue-50 border-blue-300',
    running: 'bg-blue-100 border-blue-500 animate-pulse',
    completed: 'bg-green-50 border-green-400',
    failed: 'bg-red-50 border-red-400',
  };

  const statusDot: Record<string, string> = {
    idle: 'bg-gray-400',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-sm min-w-[160px] transition-all
        ${statusColors[status]}
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-blue-400 !w-3 !h-3 !border-2 !border-white"
      />

      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-blue-100 rounded-md">
          {nodeData.agentType === 'orchestrator' ? (
            <Cpu className="w-4 h-4 text-blue-600" />
          ) : (
            <Bot className="w-4 h-4 text-blue-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {nodeData.label || 'Agent'}
          </div>
          {nodeData.agentId && (
            <div className="text-xs text-gray-500 truncate">
              {nodeData.agentId.slice(0, 8)}...
            </div>
          )}
        </div>
        <div className={`w-2 h-2 rounded-full ${statusDot[status]}`} />
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-blue-400 !w-3 !h-3 !border-2 !border-white"
      />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
