/**
 * WorkerActionList Component
 *
 * Displays a list of Worker actions in a timeline format.
 * Similar to Kimi AI's action list design.
 *
 * Sprint 104: ExtendedThinking + 工具調用展示優化
 */

import { FC } from 'react';
import {
  Search,
  FileText,
  Brain,
  Edit,
  Code,
  Database,
  ChevronRight,
  Eye,
  Download,
  Upload,
  Terminal,
  Globe,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

/**
 * Action types supported by the component
 */
export type ActionType =
  | 'read_todo'
  | 'write_todo'
  | 'think'
  | 'search'
  | 'file_read'
  | 'file_write'
  | 'file_created'
  | 'code'
  | 'database'
  | 'terminal'
  | 'web'
  | 'view'
  | 'download'
  | 'upload'
  | 'custom';

/**
 * Worker action data structure
 */
export interface WorkerAction {
  /** Unique action identifier */
  id: string;
  /** Type of action */
  type: ActionType;
  /** Action title/description */
  title: string;
  /** Optional secondary description */
  description?: string;
  /** When the action occurred */
  timestamp: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Whether clicking reveals more details */
  expandable?: boolean;
}

interface WorkerActionListProps {
  /** Array of actions to display */
  actions: WorkerAction[];
  /** Handler for action clicks */
  onActionClick?: (action: WorkerAction) => void;
  /** Maximum height before scroll (optional) */
  maxHeight?: number;
  /** Optional class name */
  className?: string;
}

// =============================================================================
// Icon and Color Mappings
// =============================================================================

/**
 * Map action types to Lucide icons
 */
const ACTION_ICONS: Record<ActionType, LucideIcon> = {
  read_todo: FileText,
  write_todo: Edit,
  think: Brain,
  search: Search,
  file_read: Eye,
  file_write: Edit,
  file_created: FileText,
  code: Code,
  database: Database,
  terminal: Terminal,
  web: Globe,
  view: Eye,
  download: Download,
  upload: Upload,
  custom: ChevronRight,
};

/**
 * Map action types to Tailwind text colors
 */
const ACTION_COLORS: Record<ActionType, string> = {
  read_todo: 'text-blue-500',
  write_todo: 'text-green-500',
  think: 'text-purple-500',
  search: 'text-orange-500',
  file_read: 'text-blue-400',
  file_write: 'text-green-400',
  file_created: 'text-teal-500',
  code: 'text-pink-500',
  database: 'text-cyan-500',
  terminal: 'text-gray-600 dark:text-gray-400',
  web: 'text-indigo-500',
  view: 'text-blue-500',
  download: 'text-green-600',
  upload: 'text-amber-500',
  custom: 'text-gray-500',
};

/**
 * Map action types to display labels
 */
const ACTION_LABELS: Record<ActionType, string> = {
  read_todo: 'Read',
  write_todo: 'Write',
  think: 'Think',
  search: 'Search',
  file_read: 'Read File',
  file_write: 'Write File',
  file_created: 'Created',
  code: 'Code',
  database: 'Database',
  terminal: 'Command',
  web: 'Web',
  view: 'View',
  download: 'Download',
  upload: 'Upload',
  custom: 'Action',
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format timestamp to relative or absolute time
 */
function formatActionTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 60) {
      return `${diffSecs}s ago`;
    } else if (diffSecs < 3600) {
      return `${Math.floor(diffSecs / 60)}m ago`;
    } else {
      return date.toLocaleTimeString();
    }
  } catch {
    return timestamp;
  }
}

// =============================================================================
// ActionItem Sub-component
// =============================================================================

interface ActionItemProps {
  action: WorkerAction;
  onClick?: () => void;
}

const ActionItem: FC<ActionItemProps> = ({ action, onClick }) => {
  const Icon = ACTION_ICONS[action.type] || ACTION_ICONS.custom;
  const color = ACTION_COLORS[action.type] || ACTION_COLORS.custom;
  const label = ACTION_LABELS[action.type] || 'Action';

  return (
    <div
      className={cn(
        'flex items-center justify-between py-2 px-3 rounded-md',
        'hover:bg-accent cursor-pointer transition-colors',
        'group',
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      {/* Left side: Icon + Content */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {/* Icon */}
        <Icon className={cn('h-4 w-4 flex-shrink-0', color)} />

        {/* Action type label (optional) */}
        <span className="text-xs text-muted-foreground flex-shrink-0 min-w-[40px]">
          {label}
        </span>

        {/* Separator */}
        <span className="text-muted-foreground">|</span>

        {/* Title */}
        <span className="text-sm truncate flex-1">{action.title}</span>

        {/* Description (if exists) */}
        {action.description && (
          <span className="text-xs text-muted-foreground truncate hidden sm:inline max-w-[120px]">
            {action.description}
          </span>
        )}
      </div>

      {/* Right side: Metadata + Chevron */}
      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
        {/* Result count (if in metadata) */}
        {action.metadata?.resultCount !== undefined && (
          <span className="text-xs text-muted-foreground">
            {String(action.metadata.resultCount)} results
          </span>
        )}

        {/* Time */}
        <span className="text-xs text-muted-foreground hidden sm:inline">
          {formatActionTime(action.timestamp)}
        </span>

        {/* Expand indicator */}
        {action.expandable && (
          <ChevronRight
            className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
          />
        )}
      </div>
    </div>
  );
};

// =============================================================================
// WorkerActionList Component
// =============================================================================

/**
 * WorkerActionList - Timeline of Worker actions
 *
 * Features:
 * - Color-coded action types
 * - Icon mapping for different operations
 * - Hover states and click handlers
 * - Responsive design
 *
 * @param actions - Array of actions to display
 * @param onActionClick - Handler for action clicks
 * @param maxHeight - Maximum height before scroll
 * @param className - Additional CSS classes
 */
export const WorkerActionList: FC<WorkerActionListProps> = ({
  actions,
  onActionClick,
  maxHeight,
  className,
}) => {
  if (actions.length === 0) {
    return (
      <div className={cn('text-sm text-muted-foreground text-center py-4', className)}>
        No actions recorded
      </div>
    );
  }

  return (
    <div
      className={cn('space-y-1', className)}
      style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}
    >
      {actions.map((action) => (
        <ActionItem
          key={action.id}
          action={action}
          onClick={() => onActionClick?.(action)}
        />
      ))}
    </div>
  );
};

// =============================================================================
// Utility: Convert tool calls to actions
// =============================================================================

/**
 * Infer action type from tool name
 *
 * Note: More specific patterns are checked first to avoid false positives
 */
export function inferActionType(toolName: string): ActionType {
  const name = toolName.toLowerCase();

  // Check more specific patterns first
  if (name.includes('todo')) {
    if (name.includes('read') || name.includes('list')) return 'read_todo';
    return 'write_todo';
  }
  if (name.includes('terminal') || name.includes('bash') || name.includes('shell')) return 'terminal';
  if (name.includes('database') || name.includes('sql') || name.includes('query')) return 'database';
  if (name.includes('search') || name.includes('grep') || name.includes('find')) return 'search';
  if (name.includes('web') || name.includes('http') || name.includes('fetch')) return 'web';
  if (name.includes('think') || name.includes('analyze')) return 'think';
  if (name.includes('code') || name.includes('execute')) return 'code';
  if (name.includes('read') || name.includes('get')) return 'file_read';
  if (name.includes('write') || name.includes('save') || name.includes('edit')) return 'file_write';

  return 'custom';
}

export default WorkerActionList;
