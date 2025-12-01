// =============================================================================
// IPA Platform - Sidebar Navigation
// =============================================================================
// Sprint 5: Frontend UI - Navigation Component
//
// Sidebar navigation with links to all main sections.
//
// Dependencies:
//   - React Router (NavLink)
//   - Lucide React icons
// =============================================================================

import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Workflow,
  Bot,
  ClipboardCheck,
  FileText,
  BookTemplate,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: '工作流', href: '/workflows', icon: Workflow },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: '模板市場', href: '/templates', icon: BookTemplate },
  { name: '審批中心', href: '/approvals', icon: ClipboardCheck },
  { name: '審計日誌', href: '/audit', icon: FileText },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo / Brand */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg">IPA Platform</span>
        </div>
      </div>

      {/* Navigation links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="p-3 border-t border-gray-200">
        <NavLink
          to="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <Settings className="w-5 h-5" />
          設置
        </NavLink>
      </div>
    </aside>
  );
}
