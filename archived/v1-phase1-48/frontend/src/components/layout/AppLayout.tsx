// =============================================================================
// IPA Platform - Application Layout
// =============================================================================
// Sprint 5: Frontend UI - Main Layout Component
// Sprint 73: S73-2 - Sidebar Collapse Feature
//
// Root layout component with sidebar navigation and header.
// Supports collapsible sidebar for more screen space.
//
// Dependencies:
//   - React Router (Outlet)
//   - Sidebar, Header components
// =============================================================================

import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function AppLayout() {
  // S73-2: Sidebar collapse state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar navigation with collapse support */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top header */}
        <Header />

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
