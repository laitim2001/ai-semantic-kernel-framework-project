// =============================================================================
// IPA Platform - Main Application Component
// =============================================================================
// Sprint 5: Frontend UI - App Shell
// Sprint 12: S12-4 UI Integration - Added Performance Monitoring
// Sprint 61: AG-UI Demo Page Route
// Sprint 62: Unified Chat Interface Route (Phase 16)
// Sprint 69: S69-4 - Integrated Chat into AppLayout (Dashboard integration)
// Sprint 71: S71-2 - Added Login/Signup routes (Phase 18)
// Sprint 71: S71-3 - Added ProtectedRoute wrapper (Phase 18)
// Sprint 87: S87-1 - Added DevUI routes (Phase 26)
//
// Root application component with routing configuration.
//
// Dependencies:
//   - React Router 6
// =============================================================================

import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
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
import { AGUIDemoPage } from '@/pages/ag-ui/AGUIDemoPage';
import { UnifiedChat } from '@/pages/UnifiedChat';
import { LoginPage } from '@/pages/auth/LoginPage';
import { SignupPage } from '@/pages/auth/SignupPage';
// Sprint 87: DevUI pages
import { DevUILayout } from '@/pages/DevUI/Layout';
import { DevUIOverview } from '@/pages/DevUI/index';
import { TraceList } from '@/pages/DevUI/TraceList';
import { TraceDetail } from '@/pages/DevUI/TraceDetail';
import { LiveMonitor } from '@/pages/DevUI/LiveMonitor';
import { Settings as DevUISettings } from '@/pages/DevUI/Settings';
import { AGUITestPanel } from '@/pages/DevUI/AGUITestPanel';
// Phase 29: Agent Swarm Test Page
import { SwarmTestPage } from '@/pages/SwarmTestPage';
// Sprint 133: Workflow DAG Editor (Phase 34)
import { WorkflowEditorPage } from '@/pages/workflows/WorkflowEditorPage';
// Sprint 138: Session Management Pages (Phase 40)
import { SessionsPage } from '@/pages/sessions/SessionsPage';
import { SessionDetailPage } from '@/pages/sessions/SessionDetailPage';
// Sprint 139: Task Dashboard Pages (Phase 40)
import { TaskDashboardPage } from '@/pages/tasks/TaskDashboardPage';
import { TaskDetailPage } from '@/pages/tasks/TaskDetailPage';
// Sprint 140: Knowledge + Memory Pages (Phase 40)
import { KnowledgePage } from '@/pages/knowledge/KnowledgePage';
import { MemoryPage } from '@/pages/memory/MemoryPage';

function App() {
  return (
    <Routes>
      {/* Auth Pages (Sprint 71) - Standalone full-screen layout */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      {/* AG-UI Demo Page (Sprint 61) - Standalone full-screen layout */}
      <Route path="/ag-ui-demo" element={<AGUIDemoPage />} />

      {/* Phase 29: Agent Swarm Test Page - Standalone full-screen layout */}
      <Route path="/swarm-test" element={<SwarmTestPage />} />

      {/* Protected Routes (Sprint 71) - Require authentication */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        {/* Default redirect to dashboard */}
        <Route index element={<Navigate to="/dashboard" replace />} />

        {/* Dashboard */}
        <Route path="dashboard" element={<DashboardPage />} />

        {/* Unified Chat Interface (Sprint 69: Integrated into AppLayout) */}
        <Route path="chat" element={<UnifiedChat />} />

        {/* Performance Monitoring (Sprint 12 - Phase 2) */}
        <Route path="performance" element={<PerformancePage />} />

        {/* Workflows */}
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="workflows/new" element={<CreateWorkflowPage />} />
        <Route path="workflows/:id" element={<WorkflowDetailPage />} />
        <Route path="workflows/:id/edit" element={<EditWorkflowPage />} />
        <Route path="workflows/:id/editor" element={<WorkflowEditorPage />} />

        {/* Agents */}
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<CreateAgentPage />} />
        <Route path="agents/:id" element={<AgentDetailPage />} />
        <Route path="agents/:id/edit" element={<EditAgentPage />} />

        {/* Templates */}
        <Route path="templates" element={<TemplatesPage />} />

        {/* Sessions (Sprint 138 - Phase 40) */}
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="sessions/:id" element={<SessionDetailPage />} />

        {/* Tasks (Sprint 139 - Phase 40) */}
        <Route path="tasks" element={<TaskDashboardPage />} />
        <Route path="tasks/:id" element={<TaskDetailPage />} />

        {/* Knowledge (Sprint 140 - Phase 40) */}
        <Route path="knowledge" element={<KnowledgePage />} />

        {/* Memory (Sprint 140 - Phase 40) */}
        <Route path="memory" element={<MemoryPage />} />

        {/* Approvals */}
        <Route path="approvals" element={<ApprovalsPage />} />

        {/* Audit */}
        <Route path="audit" element={<AuditPage />} />

        {/* DevUI (Sprint 87) - Developer Tools with nested layout */}
        <Route path="devui" element={<DevUILayout />}>
          <Route index element={<DevUIOverview />} />
          <Route path="ag-ui-test" element={<AGUITestPanel />} />
          <Route path="traces" element={<TraceList />} />
          <Route path="traces/:id" element={<TraceDetail />} />
          <Route path="monitor" element={<LiveMonitor />} />
          <Route path="settings" element={<DevUISettings />} />
        </Route>

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
