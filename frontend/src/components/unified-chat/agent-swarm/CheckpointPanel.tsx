/**
 * CheckpointPanel Component
 *
 * Displays checkpoint information for a Worker.
 * Sprint 103: WorkerDetailDrawer
 */

import { FC } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Save, Database, CheckCircle, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface CheckpointPanelProps {
  checkpointId: string;
  backend?: string;
  onRestore?: () => void;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * CheckpointPanel - Displays checkpoint information
 *
 * @param checkpointId - The checkpoint ID
 * @param backend - The storage backend (e.g., Redis, File)
 * @param onRestore - Handler for restore action
 * @param className - Additional CSS classes
 */
export const CheckpointPanel: FC<CheckpointPanelProps> = ({
  checkpointId,
  backend = 'Unknown',
  onRestore,
  className,
}) => {
  // Truncate checkpoint ID for display
  const displayId = checkpointId.length > 20
    ? `${checkpointId.slice(0, 10)}...${checkpointId.slice(-6)}`
    : checkpointId;

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 text-sm font-medium">
        <Save className="h-4 w-4 text-muted-foreground" />
        <span>Checkpoint</span>
      </div>

      {/* Checkpoint info card */}
      <div className="bg-muted/50 rounded-md p-3 space-y-3">
        {/* ID and Backend row */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">ID:</span>
            <code
              className="text-xs bg-muted px-2 py-0.5 rounded font-mono"
              title={checkpointId}
            >
              {displayId}
            </code>
          </div>

          <div className="flex items-center gap-2">
            <Database className="h-3 w-3 text-muted-foreground" />
            <Badge variant="outline" className="text-xs h-5">
              {backend}
            </Badge>
          </div>
        </div>

        {/* Status and Restore row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
            <CheckCircle className="h-3 w-3" />
            <span>Recoverable</span>
          </div>

          {onRestore && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={onRestore}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Restore
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CheckpointPanel;
