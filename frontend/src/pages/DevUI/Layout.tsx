// =============================================================================
// IPA Platform - DevUI Layout Component
// =============================================================================
// Sprint 87: S87-1 - DevUI Core Pages
//
// Layout component for DevUI with sidebar navigation and breadcrumbs.
//
// Dependencies:
//   - React Router
//   - Lucide React icons
// =============================================================================

import { FC } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Bug,
  ListTree,
  Home,
  ChevronRight,
  Activity,
  Settings,
  TestTube2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Navigation items for DevUI
 */
interface DevUINavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const devUINavigation: DevUINavItem[] = [
  { name: 'Overview', href: '/devui', icon: Home },
  { name: 'AG-UI Test', href: '/devui/ag-ui-test', icon: TestTube2 },
  { name: 'Traces', href: '/devui/traces', icon: ListTree },
  { name: 'Live Monitor', href: '/devui/monitor', icon: Activity },
  { name: 'Settings', href: '/devui/settings', icon: Settings },
];

/**
 * Breadcrumb segment interface
 */
interface BreadcrumbSegment {
  name: string;
  href?: string;
}

/**
 * Generate breadcrumbs from current path
 */
function getBreadcrumbs(pathname: string): BreadcrumbSegment[] {
  const segments = pathname.split('/').filter(Boolean);
  const breadcrumbs: BreadcrumbSegment[] = [];

  // Always start with DevUI
  if (segments[0] === 'devui') {
    breadcrumbs.push({ name: 'DevUI', href: '/devui' });

    if (segments[1] === 'traces') {
      breadcrumbs.push({ name: 'Traces', href: '/devui/traces' });

      // If there's a trace ID
      if (segments[2]) {
        breadcrumbs.push({ name: `Trace ${segments[2].slice(0, 8)}...` });
      }
    } else if (segments[1] === 'ag-ui-test') {
      breadcrumbs.push({ name: 'AG-UI Test' });
    } else if (segments[1] === 'monitor') {
      breadcrumbs.push({ name: 'Live Monitor' });
    } else if (segments[1] === 'settings') {
      breadcrumbs.push({ name: 'Settings' });
    }
  }

  return breadcrumbs;
}

/**
 * DevUI Layout Component
 * Provides sidebar navigation and breadcrumb navigation for DevUI pages
 */
export const DevUILayout: FC = () => {
  const location = useLocation();
  const breadcrumbs = getBreadcrumbs(location.pathname);

  return (
    <div className="flex h-full bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo / Title */}
        <div className="h-14 flex items-center px-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Bug className="w-5 h-5 text-purple-600" />
            <span className="font-semibold text-gray-900">DevUI</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {devUINavigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              end={item.href === '/devui'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-purple-50 text-purple-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )
              }
            >
              <item.icon className="w-4 h-4" />
              <span>{item.name}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            Developer Tools v1.0
          </p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumbs */}
        <div className="h-12 bg-white border-b border-gray-200 flex items-center px-6">
          <nav className="flex items-center gap-1 text-sm">
            {breadcrumbs.map((segment, index) => (
              <div key={index} className="flex items-center gap-1">
                {index > 0 && (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                {segment.href ? (
                  <NavLink
                    to={segment.href}
                    className="text-gray-600 hover:text-gray-900"
                  >
                    {segment.name}
                  </NavLink>
                ) : (
                  <span className="text-gray-900 font-medium">
                    {segment.name}
                  </span>
                )}
              </div>
            ))}
          </nav>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
