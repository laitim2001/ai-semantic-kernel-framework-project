/**
 * ToolRenderingDemo - Tool Rendering Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 2: Tool Result Rendering with different formats.
 */

import { FC, useState } from 'react';
import { ToolCallCard } from '@/components/ag-ui/chat';
import type { ToolCallState, ToolCallStatus } from '@/types/ag-ui';
import { Button } from '@/components/ui/Button';
import type { EventLogEntry } from './EventLogPanel';

export interface ToolRenderingDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

/** Sample tool calls with different result types */
const sampleToolCalls: ToolCallState[] = [
  {
    id: 'tc_1',
    toolCallId: 'tc_code_1',
    name: 'execute_code',
    arguments: { language: 'python', code: 'print("Hello, World!")' },
    status: 'completed',
    result: { output: 'Hello, World!', exitCode: 0 },
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
  },
  {
    id: 'tc_2',
    toolCallId: 'tc_json_2',
    name: 'fetch_data',
    arguments: { url: 'https://api.example.com/users' },
    status: 'completed',
    result: {
      users: [
        { id: 1, name: 'Alice', email: 'alice@example.com' },
        { id: 2, name: 'Bob', email: 'bob@example.com' },
      ],
      total: 2,
    },
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
  },
  {
    id: 'tc_3',
    toolCallId: 'tc_error_3',
    name: 'database_query',
    arguments: { query: 'SELECT * FROM invalid_table' },
    status: 'failed',
    error: 'Table "invalid_table" does not exist in the database',
    startedAt: new Date().toISOString(),
    completedAt: new Date().toISOString(),
  },
  {
    id: 'tc_4',
    toolCallId: 'tc_pending_4',
    name: 'delete_file',
    arguments: { path: '/important/file.txt' },
    status: 'requires_approval',
    startedAt: new Date().toISOString(),
  },
];

/**
 * ToolRenderingDemo Component
 *
 * Showcases different tool result rendering formats.
 */
export const ToolRenderingDemo: FC<ToolRenderingDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [toolCalls, setToolCalls] = useState<ToolCallState[]>(sampleToolCalls);

  // Handle tool call action
  const handleAction = (toolCallId: string, action: 'approve' | 'reject') => {
    const newStatus: ToolCallStatus = action === 'approve' ? 'approved' : 'rejected';

    setToolCalls((prev) =>
      prev.map((tc) =>
        tc.toolCallId === toolCallId
          ? { ...tc, status: newStatus, completedAt: new Date().toISOString() }
          : tc
      )
    );

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'TOOL_CALL_END',
      timestamp: new Date().toISOString(),
      data: { tool_call_id: toolCallId, action },
    });
  };

  // Reset demo
  const handleReset = () => {
    setToolCalls(sampleToolCalls);
  };

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="tool-rendering-demo">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Feature 2: Tool Rendering</h3>
          <p className="text-sm text-gray-500">
            Different tool result formats: code output, JSON data, errors.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleReset}>
          Reset Demo
        </Button>
      </div>

      {/* Tool Call Cards */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {toolCalls.map((toolCall) => (
          <div key={toolCall.id}>
            <div className="text-xs text-gray-500 mb-1">
              Result Type: {
                toolCall.status === 'failed' ? 'Error' :
                toolCall.status === 'requires_approval' ? 'Pending Approval' :
                typeof toolCall.result === 'object' ? 'JSON' : 'Text'
              }
            </div>
            <ToolCallCard
              toolCall={toolCall}
              showArguments
              showResult
              onAction={handleAction}
            />
          </div>
        ))}
      </div>

      {/* Tips */}
      <div className="mt-4 p-3 bg-purple-50 rounded-lg text-sm text-purple-800">
        <strong>Result Types:</strong>
        <ul className="list-disc list-inside mt-1">
          <li>Code output with syntax highlighting</li>
          <li>JSON data with formatting</li>
          <li>Error messages with red styling</li>
          <li>Pending approval with action buttons</li>
        </ul>
      </div>
    </div>
  );
};

export default ToolRenderingDemo;
