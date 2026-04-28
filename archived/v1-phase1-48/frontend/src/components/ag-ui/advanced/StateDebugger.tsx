/**
 * StateDebugger - Shared State Debug Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-2: Shared State
 *
 * Developer tool for debugging and visualizing shared state.
 * Shows state tree, pending diffs, conflicts, and sync status.
 */

import { FC, useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/Card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/Collapsible';
import type { SharedState, StateDiff, StateConflict, StateSyncStatus } from '@/types/ag-ui';

export interface StateDebuggerProps {
  /** Shared state object */
  state: SharedState;
  /** Current sync status */
  syncStatus: StateSyncStatus;
  /** Callback to force sync */
  onForceSync?: () => void;
  /** Callback to clear state */
  onClearState?: () => void;
  /** Callback to resolve conflict */
  onResolveConflict?: (conflict: StateConflict, resolution: 'client' | 'server') => void;
  /** Additional CSS classes */
  className?: string;
}

/** Sync status badge colors */
const SYNC_STATUS_COLORS: Record<StateSyncStatus, string> = {
  synced: 'bg-green-500',
  syncing: 'bg-blue-500',
  pending: 'bg-yellow-500',
  conflict: 'bg-red-500',
  error: 'bg-destructive',
};

/** Sync status labels */
const SYNC_STATUS_LABELS: Record<StateSyncStatus, string> = {
  synced: 'Synced',
  syncing: 'Syncing...',
  pending: 'Pending',
  conflict: 'Conflict',
  error: 'Error',
};

/**
 * JSON Tree Viewer - Renders expandable JSON tree
 */
const JsonTreeViewer: FC<{ data: unknown; name?: string; depth?: number }> = ({
  data,
  name,
  depth = 0,
}) => {
  const [isOpen, setIsOpen] = useState(depth < 2);

  const isObject = data !== null && typeof data === 'object';
  const isArray = Array.isArray(data);

  if (!isObject) {
    // Primitive value
    return (
      <div className="flex items-center gap-2">
        {name && <span className="text-purple-500">{name}:</span>}
        <span
          className={cn(
            typeof data === 'string' && 'text-green-500',
            typeof data === 'number' && 'text-blue-500',
            typeof data === 'boolean' && 'text-orange-500',
            data === null && 'text-muted-foreground italic'
          )}
        >
          {data === null
            ? 'null'
            : typeof data === 'string'
            ? `"${data}"`
            : String(data)}
        </span>
      </div>
    );
  }

  const entries = isArray
    ? (data as unknown[]).map((v, i) => [i, v] as [number, unknown])
    : Object.entries(data as Record<string, unknown>);

  const bracketOpen = isArray ? '[' : '{';
  const bracketClose = isArray ? ']' : '}';

  if (entries.length === 0) {
    return (
      <span>
        {name && <span className="text-purple-500">{name}: </span>}
        {bracketOpen}
        {bracketClose}
      </span>
    );
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center gap-1 hover:bg-muted/50 rounded px-1">
        <span className="text-muted-foreground text-xs">{isOpen ? '▼' : '▶'}</span>
        {name && <span className="text-purple-500">{name}:</span>}
        <span>{bracketOpen}</span>
        {!isOpen && (
          <span className="text-muted-foreground">
            {entries.length} {entries.length === 1 ? 'item' : 'items'}
          </span>
        )}
        {!isOpen && <span>{bracketClose}</span>}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-4 border-l border-muted pl-2">
          {entries.map(([key, value]) => (
            <JsonTreeViewer key={key} data={value} name={String(key)} depth={depth + 1} />
          ))}
        </div>
        <span>{bracketClose}</span>
      </CollapsibleContent>
    </Collapsible>
  );
};

/**
 * Diff Viewer - Renders state diffs
 */
const DiffViewer: FC<{ diffs: StateDiff[] }> = ({ diffs }) => {
  if (diffs.length === 0) {
    return <p className="text-muted-foreground text-sm">No pending changes</p>;
  }

  return (
    <div className="space-y-2">
      {diffs.map((diff, index) => (
        <div key={index} className="flex items-start gap-2 text-sm font-mono">
          <Badge
            variant={
              diff.operation === 'add'
                ? 'default'
                : diff.operation === 'remove'
                ? 'destructive'
                : 'secondary'
            }
            className="text-xs"
          >
            {diff.operation.toUpperCase()}
          </Badge>
          <span className="text-purple-500">{diff.path}</span>
          {diff.oldValue !== undefined && (
            <span className="text-red-500 line-through">
              {JSON.stringify(diff.oldValue)}
            </span>
          )}
          {diff.newValue !== undefined && (
            <span className="text-green-500">{JSON.stringify(diff.newValue)}</span>
          )}
        </div>
      ))}
    </div>
  );
};

/**
 * Conflict Viewer - Renders state conflicts
 */
const ConflictViewer: FC<{
  conflicts: StateConflict[];
  onResolve?: (conflict: StateConflict, resolution: 'client' | 'server') => void;
}> = ({ conflicts, onResolve }) => {
  if (conflicts.length === 0) {
    return <p className="text-muted-foreground text-sm">No conflicts</p>;
  }

  return (
    <div className="space-y-4">
      {conflicts.map((conflict, index) => (
        <div key={index} className="border rounded-lg p-3 space-y-2">
          <div className="font-mono text-sm">
            <span className="text-purple-500">{conflict.path}</span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground mb-1">Client Value:</p>
              <pre className="bg-muted p-2 rounded text-xs overflow-auto">
                {JSON.stringify(conflict.clientValue, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-muted-foreground mb-1">Server Value:</p>
              <pre className="bg-muted p-2 rounded text-xs overflow-auto">
                {JSON.stringify(conflict.serverValue, null, 2)}
              </pre>
            </div>
          </div>
          {onResolve && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onResolve(conflict, 'client')}
              >
                Use Client
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onResolve(conflict, 'server')}
              >
                Use Server
              </Button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

/**
 * StateDebugger - Main debugger component
 */
export const StateDebugger: FC<StateDebuggerProps> = ({
  state,
  syncStatus,
  onForceSync,
  onClearState,
  onResolveConflict,
  className,
}) => {
  const [activeTab, setActiveTab] = useState<'state' | 'diffs' | 'conflicts'>('state');

  // Format last sync time
  const lastSyncFormatted = useMemo(() => {
    if (!state.lastSync) return 'Never';
    return new Date(state.lastSync).toLocaleTimeString();
  }, [state.lastSync]);

  return (
    <Card className={cn('font-mono text-sm', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              State Debugger
              <Badge className={cn('text-xs', SYNC_STATUS_COLORS[syncStatus])}>
                {SYNC_STATUS_LABELS[syncStatus]}
              </Badge>
            </CardTitle>
            <CardDescription>
              Session: {state.sessionId} | Version: {state.version.version} | Last Sync:{' '}
              {lastSyncFormatted}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {onForceSync && (
              <Button size="sm" variant="outline" onClick={onForceSync}>
                Force Sync
              </Button>
            )}
            {onClearState && (
              <Button size="sm" variant="destructive" onClick={onClearState}>
                Clear
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Tab Navigation */}
        <div className="flex gap-2 mb-4 border-b">
          <button
            className={cn(
              'px-3 py-2 text-sm transition-colors',
              activeTab === 'state'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setActiveTab('state')}
          >
            State Tree
          </button>
          <button
            className={cn(
              'px-3 py-2 text-sm transition-colors flex items-center gap-1',
              activeTab === 'diffs'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setActiveTab('diffs')}
          >
            Pending Diffs
            {state.pendingDiffs.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {state.pendingDiffs.length}
              </Badge>
            )}
          </button>
          <button
            className={cn(
              'px-3 py-2 text-sm transition-colors flex items-center gap-1',
              activeTab === 'conflicts'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setActiveTab('conflicts')}
          >
            Conflicts
            {state.conflicts.length > 0 && (
              <Badge variant="destructive" className="text-xs">
                {state.conflicts.length}
              </Badge>
            )}
          </button>
        </div>

        {/* Tab Content */}
        <div className="max-h-96 overflow-auto">
          {activeTab === 'state' && <JsonTreeViewer data={state.state} />}
          {activeTab === 'diffs' && <DiffViewer diffs={state.pendingDiffs} />}
          {activeTab === 'conflicts' && (
            <ConflictViewer conflicts={state.conflicts} onResolve={onResolveConflict} />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default StateDebugger;
