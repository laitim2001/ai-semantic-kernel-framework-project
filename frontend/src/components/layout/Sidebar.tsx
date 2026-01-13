// =============================================================================
// IPA Platform - Sidebar Navigation
// =============================================================================
// Sprint 5: Frontend UI - Navigation Component
// Sprint 12: S12-4 UI Integration - Added Performance Monitoring
// Sprint 69: S69-4 - Added Chat navigation for Dashboard integration
// Sprint 73: S73-2 - Collapsible Sidebar Feature
// Sprint 87: S87-1 - Added DevUI navigation (Phase 26)
//
// Sidebar navigation with links to all main sections.
// Supports collapse/expand for more screen space.
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
  Activity,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Bug,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'AI 助手', href: '/chat', icon: MessageSquare },
  { name: '效能監控', href: '/performance', icon: Activity },
  { name: '工作流', href: '/workflows', icon: Workflow },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: '模板市場', href: '/templates', icon: BookTemplate },
  { name: '審批中心', href: '/approvals', icon: ClipboardCheck },
  { name: '審計日誌', href: '/audit', icon: FileText },
  { name: 'DevUI', href: '/devui', icon: Bug },
];

/**
 * S73-2: Sidebar Props for collapse functionality
 */
interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'bg-white border-r border-gray-200 flex flex-col transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo / Brand */}
      <div
        className={cn(
          'h-16 flex items-center border-b border-gray-200',
          isCollapsed ? 'px-4 justify-center' : 'px-6'
        )}
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shrink-0">
            <Bot className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <span className="font-bold text-lg whitespace-nowrap">IPA Platform</span>
          )}
        </div>
      </div>

      {/* Navigation links */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            title={isCollapsed ? item.name : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isCollapsed && 'justify-center',
                isActive
                  ? 'bg-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              )
            }
          >
            <item.icon className="w-5 h-5 shrink-0" />
            {!isCollapsed && <span>{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom section with Settings and Toggle */}
      <div className="p-2 border-t border-gray-200 space-y-1">
        {/* Settings link */}
        <NavLink
          to="/settings"
          title={isCollapsed ? '設置' : undefined}
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors',
            isCollapsed && 'justify-center'
          )}
        >
          <Settings className="w-5 h-5 shrink-0" />
          {!isCollapsed && <span>設置</span>}
        </NavLink>

        {/* Toggle button */}
        <button
          onClick={onToggle}
          className={cn(
            'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium',
            'text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors',
            isCollapsed && 'justify-center'
          )}
          aria-label={isCollapsed ? '展開側邊欄' : '收起側邊欄'}
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5" />
              <span>收起</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
