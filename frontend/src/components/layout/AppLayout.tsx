// =============================================================================
// IPA Platform - Application Layout
// =============================================================================
// Sprint 5: Frontend UI - Main Layout Component
//
// Root layout component with sidebar navigation and header.
//
// Dependencies:
//   - React Router (Outlet)
//   - Sidebar, Header components
// =============================================================================

import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function AppLayout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar navigation */}
      <Sidebar />

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
