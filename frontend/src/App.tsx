// =============================================================================
// IPA Platform - Main Application Component
// =============================================================================
// Sprint 5: Frontend UI - App Shell
// Sprint 12: S12-4 UI Integration - Added Performance Monitoring
//
// Root application component with routing configuration.
//
// Dependencies:
//   - React Router 6
// =============================================================================

import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { PerformancePage } from '@/pages/dashboard/PerformancePage';
import { WorkflowsPage } from '@/pages/workflows/WorkflowsPage';
import { WorkflowDetailPage } from '@/pages/workflows/WorkflowDetailPage';
import { CreateWorkflowPage } from '@/pages/workflows/CreateWorkflowPage';
import { EditWorkflowPage } from '@/pages/workflows/EditWorkflowPage';
import { AgentsPage } from '@/pages/agents/AgentsPage';
import { AgentDetailPage } from '@/pages/agents/AgentDetailPage';
import { CreateAgentPage } from '@/pages/agents/CreateAgentPage';
import { EditAgentPage } from '@/pages/agents/EditAgentPage';
import { ApprovalsPage } from '@/pages/approvals/ApprovalsPage';
import { AuditPage } from '@/pages/audit/AuditPage';
import { TemplatesPage } from '@/pages/templates/TemplatesPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        {/* Default redirect to dashboard */}
        <Route index element={<Navigate to="/dashboard" replace />} />

        {/* Dashboard */}
        <Route path="dashboard" element={<DashboardPage />} />

        {/* Performance Monitoring (Sprint 12 - Phase 2) */}
        <Route path="performance" element={<PerformancePage />} />

        {/* Workflows */}
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="workflows/new" element={<CreateWorkflowPage />} />
        <Route path="workflows/:id" element={<WorkflowDetailPage />} />
        <Route path="workflows/:id/edit" element={<EditWorkflowPage />} />

        {/* Agents */}
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<CreateAgentPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="agents/:id/edit" element={<EditAgentPage />} />

        {/* Templates */}
        <Route path="templates" element={<TemplatesPage />} />

        {/* Approvals */}
        <Route path="approvals" element={<ApprovalsPage />} />

        {/* Audit */}
        <Route path="audit" element={<AuditPage />} />

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
