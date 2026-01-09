// =============================================================================
// IPA Platform - Header Component
// =============================================================================
// Sprint 5: Frontend UI - Top Navigation Header
// Sprint 73: Phase 19 - Integrated UserMenu dropdown
//
// Top header with search, notifications, and user menu.
//
// Dependencies:
//   - Lucide React icons
//   - UserMenu component
// =============================================================================

import { Bell, Search } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { UserMenu } from './UserMenu';

export function Header() {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* Search bar */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索工作流、Agent..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </Button>

        {/* User menu with dropdown */}
        <UserMenu />
      </div>
    </header>
  );
}
