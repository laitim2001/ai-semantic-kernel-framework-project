// =============================================================================
// IPA Platform - Workflow Editor Page
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Page wrapper for WorkflowCanvas component.
// Route: /workflows/:id/editor
// =============================================================================

import { useParams, Navigate } from 'react-router-dom';
import { WorkflowCanvas } from '@/components/workflow-editor/WorkflowCanvas';

export function WorkflowEditorPage() {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return <Navigate to="/workflows" replace />;
  }

  return <WorkflowCanvas workflowId={id} />;
}
