// =============================================================================
// IPA Platform - Action Node Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Custom ReactFlow node for system action steps.
// Visual: Green rounded rectangle with action icon.
// =============================================================================

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Zap, Mail, Webhook, Database } from 'lucide-react';

export interface ActionNodeData {
  label: string;
  actionType?: 'notification' | 'webhook' | 'database' | 'generic';
  status?: 'idle' | 'running' | 'completed' | 'failed';
  config?: Record<string, unknown>;
}

const actionIcons: Record<string, typeof Zap> = {
  notification: Mail,
  webhook: Webhook,
  database: Database,
  generic: Zap,
};

function ActionNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as unknown as ActionNodeData;
  const actionType = nodeData.actionType || 'generic';
  const status = nodeData.status || 'idle';
  const Icon = actionIcons[actionType] || Zap;

  const statusColors: Record<string, string> = {
    idle: 'bg-emerald-50 border-emerald-300',
    running: 'bg-emerald-100 border-emerald-500 animate-pulse',
    completed: 'bg-green-50 border-green-400',
    failed: 'bg-red-50 border-red-400',
  };

  const statusDot: Record<string, string> = {
    idle: 'bg-gray-400',
    running: 'bg-emerald-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-sm min-w-[150px] transition-all
        ${statusColors[status]}
        ${selected ? 'ring-2 ring-emerald-500 ring-offset-2' : ''}
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-emerald-400 !w-3 !h-3 !border-2 !border-white"
      />

      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-emerald-100 rounded-md">
          <Icon className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {nodeData.label || 'Action'}
          </div>
          <div className="text-xs text-gray-500 capitalize">
            {actionType}
          </div>
        </div>
        <div className={`w-2 h-2 rounded-full ${statusDot[status]}`} />
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-emerald-400 !w-3 !h-3 !border-2 !border-white"
      />
    </div>
  );
}

export const ActionNode = memo(ActionNodeComponent);
