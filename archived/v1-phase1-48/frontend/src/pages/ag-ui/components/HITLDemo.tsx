/**
 * HITLDemo - Human-in-the-Loop Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 3: HITL Approval Workflow.
 */

import { FC, useState, useCallback } from 'react';
import { ApprovalDialog, ApprovalList } from '@/components/ag-ui/hitl';
import type { PendingApproval, RiskLevel } from '@/types/ag-ui';
import { Button } from '@/components/ui/Button';
import type { EventLogEntry } from './EventLogPanel';

export interface HITLDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

/** Generate sample approval */
const createApproval = (overrides?: Partial<PendingApproval>): PendingApproval => ({
  approvalId: `approval_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
  toolCallId: `tc_${Date.now()}`,
  toolName: 'database_delete',
  arguments: { table: 'users', where: { id: 123 } },
  riskLevel: 'high',
  riskScore: 0.75,
  reasoning: 'This operation will permanently delete data from the database.',
  createdAt: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 60000).toISOString(), // 1 minute
  ...overrides,
});

/**
 * HITLDemo Component
 *
 * Interactive demo of HITL approval workflow.
 */
export const HITLDemo: FC<HITLDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null);
  const [history, setHistory] = useState<Array<{ id: string; action: string; time: string }>>([]);

  // Add new approval
  const addApproval = useCallback((riskLevel: RiskLevel) => {
    const names: Record<RiskLevel, string> = {
      low: 'read_file',
      medium: 'write_file',
      high: 'delete_file',
      critical: 'drop_database',
    };

    const newApproval = createApproval({
      riskLevel,
      toolName: names[riskLevel],
      riskScore: { low: 0.2, medium: 0.5, high: 0.75, critical: 0.95 }[riskLevel],
    });

    setApprovals((prev) => [...prev, newApproval]);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'CUSTOM',
      timestamp: new Date().toISOString(),
      data: { event_name: 'APPROVAL_REQUIRED', tool_name: newApproval.toolName, risk_level: riskLevel },
    });
  }, [onEvent]);

  // Handle approve
  const handleApprove = useCallback((approvalId: string, comment?: string) => {
    setApprovals((prev) => prev.filter((a) => a.approvalId !== approvalId));
    setSelectedApproval(null);
    setHistory((prev) => [...prev, { id: approvalId.slice(-8), action: 'Approved', time: new Date().toLocaleTimeString() }]);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'TOOL_CALL_END',
      timestamp: new Date().toISOString(),
      data: { approval_id: approvalId, action: 'approved', comment },
    });
  }, [onEvent]);

  // Handle reject
  const handleReject = useCallback((approvalId: string, comment?: string) => {
    setApprovals((prev) => prev.filter((a) => a.approvalId !== approvalId));
    setSelectedApproval(null);
    setHistory((prev) => [...prev, { id: approvalId.slice(-8), action: 'Rejected', time: new Date().toLocaleTimeString() }]);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'TOOL_CALL_END',
      timestamp: new Date().toISOString(),
      data: { approval_id: approvalId, action: 'rejected', comment },
    });
  }, [onEvent]);

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="hitl-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 3: Human-in-the-Loop</h3>
        <p className="text-sm text-gray-500">
          Risk-based approval workflow for sensitive tool calls.
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-2 mb-4">
        <span className="text-sm text-gray-500 self-center">Add Approval:</span>
        <Button variant="outline" size="sm" onClick={() => addApproval('low')}>
          🟢 Low Risk
        </Button>
        <Button variant="outline" size="sm" onClick={() => addApproval('medium')}>
          🟡 Medium Risk
        </Button>
        <Button variant="outline" size="sm" onClick={() => addApproval('high')}>
          🟠 High Risk
        </Button>
        <Button variant="outline" size="sm" onClick={() => addApproval('critical')}>
          🔴 Critical Risk
        </Button>
      </div>

      {/* Approval List */}
      <div className="flex-1 overflow-y-auto">
        <ApprovalList
          approvals={approvals}
          onApprove={handleApprove}
          onReject={handleReject}
          onShowDetails={setSelectedApproval}
          enableBatchOps
          emptyMessage="No pending approvals. Click buttons above to add test approvals."
        />
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-500 mb-2">Action History</div>
          <div className="space-y-1">
            {history.slice(-5).map((h, i) => (
              <div key={i} className="text-xs">
                <span className="text-gray-400">{h.time}</span>
                <span className="mx-2">|</span>
                <span className="font-mono">{h.id}</span>
                <span className="mx-2">→</span>
                <span className={h.action === 'Approved' ? 'text-green-600' : 'text-red-600'}>
                  {h.action}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval Dialog */}
      {selectedApproval && (
        <ApprovalDialog
          approval={selectedApproval}
          isOpen={!!selectedApproval}
          onApprove={handleApprove}
          onReject={handleReject}
          onClose={() => setSelectedApproval(null)}
          showComment
        />
      )}
    </div>
  );
};

export default HITLDemo;
