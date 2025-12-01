// =============================================================================
// IPA Platform - Main Application Component
// =============================================================================
// Sprint 5: Frontend UI - App Shell
//
// Root application component with routing configuration.
//
// Dependencies:
//   - React Router 6
// =============================================================================

import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { WorkflowsPage } from '@/pages/workflows/WorkflowsPage';
import { WorkflowDetailPage } from '@/pages/workflows/WorkflowDetailPage';
import { AgentsPage } from '@/pages/agents/AgentsPage';
import { AgentDetailPage } from '@/pages/agents/AgentDetailPage';
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

        {/* Workflows */}
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="workflows/:id" element={<WorkflowDetailPage />} />

        {/* Agents */}
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />

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
