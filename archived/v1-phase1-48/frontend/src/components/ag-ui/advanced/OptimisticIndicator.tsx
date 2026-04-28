/**
 * OptimisticIndicator - Optimistic State Indicator Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-3: Predictive State Updates
 *
 * Visual indicator showing optimistic/predictive state status.
 * Shows pending predictions, confirmation status, and rollback warnings.
 */

import { FC, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import type { PredictionResult, PredictionStatus } from '@/types/ag-ui';

export interface OptimisticIndicatorProps {
  /** List of pending predictions */
  predictions: PredictionResult[];
  /** Whether the current displayed state is optimistic */
  isOptimistic: boolean;
  /** Callback to manually confirm a prediction */
  onConfirm?: (predictionId: string) => void;
  /** Callback to manually rollback a prediction */
  onRollback?: (predictionId: string) => void;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/** Status colors for prediction states */
const STATUS_COLORS: Record<PredictionStatus, string> = {
  pending: 'bg-yellow-500',
  confirmed: 'bg-green-500',
  rolled_back: 'bg-gray-500',
  expired: 'bg-orange-500',
  conflicted: 'bg-red-500',
};

/** Status icons */
const STATUS_ICONS: Record<PredictionStatus, string> = {
  pending: '⏳',
  confirmed: '✓',
  rolled_back: '↺',
  expired: '⏰',
  conflicted: '⚠',
};

/** Status labels - exported for external use */
export const STATUS_LABELS: Record<PredictionStatus, string> = {
  pending: 'Pending',
  confirmed: 'Confirmed',
  rolled_back: 'Rolled Back',
  expired: 'Expired',
  conflicted: 'Conflicted',
};

/**
 * Single Prediction Item
 */
const PredictionItem: FC<{
  prediction: PredictionResult;
  onConfirm?: (id: string) => void;
  onRollback?: (id: string) => void;
}> = ({ prediction, onConfirm, onRollback }) => {
  // Calculate time until expiry
  const expiryInfo = useMemo(() => {
    if (!prediction.expiresAt) return null;
    const expiresAt = new Date(prediction.expiresAt);
    const now = new Date();
    const diffMs = expiresAt.getTime() - now.getTime();

    if (diffMs <= 0) return 'Expired';
    if (diffMs < 1000) return '<1s';
    if (diffMs < 60000) return `${Math.ceil(diffMs / 1000)}s`;
    return `${Math.ceil(diffMs / 60000)}m`;
  }, [prediction.expiresAt]);

  return (
    <div className="flex items-center justify-between gap-2 p-2 border rounded-lg text-sm">
      <div className="flex items-center gap-2">
        <span className="text-lg">{STATUS_ICONS[prediction.status]}</span>
        <div>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn('text-xs', STATUS_COLORS[prediction.status], 'text-white')}
            >
              {prediction.predictionType}
            </Badge>
            <span className="text-muted-foreground">{prediction.predictionId.slice(0, 8)}</span>
          </div>
          <div className="text-xs text-muted-foreground">
            Confidence: {(prediction.confidence * 100).toFixed(0)}%
            {expiryInfo && prediction.status === 'pending' && (
              <span className="ml-2">Expires: {expiryInfo}</span>
            )}
          </div>
        </div>
      </div>

      {prediction.status === 'pending' && (onConfirm || onRollback) && (
        <div className="flex gap-1">
          {onConfirm && (
            <button
              className="p-1 hover:bg-muted rounded text-green-500"
              onClick={() => onConfirm(prediction.predictionId)}
              title="Confirm prediction"
            >
              ✓
            </button>
          )}
          {onRollback && (
            <button
              className="p-1 hover:bg-muted rounded text-red-500"
              onClick={() => onRollback(prediction.predictionId)}
              title="Rollback prediction"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {prediction.status === 'conflicted' && prediction.conflictReason && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <span className="text-red-500">ℹ</span>
            </TooltipTrigger>
            <TooltipContent>
              <p className="max-w-xs">{prediction.conflictReason}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
};

/**
 * Compact Indicator - Small badge-style indicator
 */
const CompactIndicator: FC<{
  predictions: PredictionResult[];
  isOptimistic: boolean;
}> = ({ predictions, isOptimistic }) => {
  const pendingCount = predictions.filter((p) => p.status === 'pending').length;
  const conflictCount = predictions.filter((p) => p.status === 'conflicted').length;

  if (!isOptimistic && pendingCount === 0 && conflictCount === 0) {
    return null;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="inline-flex items-center gap-1">
            {isOptimistic && (
              <Badge variant="secondary" className="text-xs animate-pulse">
                ⚡ Optimistic
              </Badge>
            )}
            {pendingCount > 0 && (
              <Badge variant="outline" className="text-xs bg-yellow-500/20">
                ⏳ {pendingCount}
              </Badge>
            )}
            {conflictCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                ⚠ {conflictCount}
              </Badge>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="space-y-1 text-xs">
            {isOptimistic && <p>State includes unconfirmed predictions</p>}
            {pendingCount > 0 && <p>{pendingCount} pending predictions</p>}
            {conflictCount > 0 && <p>{conflictCount} conflicts need resolution</p>}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

/**
 * OptimisticIndicator - Main component
 */
export const OptimisticIndicator: FC<OptimisticIndicatorProps> = ({
  predictions,
  isOptimistic,
  onConfirm,
  onRollback,
  compact = false,
  className,
}) => {
  // Group predictions by status
  const groupedPredictions = useMemo(() => {
    return {
      pending: predictions.filter((p) => p.status === 'pending'),
      conflicted: predictions.filter((p) => p.status === 'conflicted'),
      recent: predictions.filter(
        (p) => p.status === 'confirmed' || p.status === 'rolled_back'
      ).slice(0, 3),
    };
  }, [predictions]);

  // Render compact mode
  if (compact) {
    return (
      <div className={className}>
        <CompactIndicator predictions={predictions} isOptimistic={isOptimistic} />
      </div>
    );
  }

  // Full indicator
  return (
    <div className={cn('space-y-4', className)}>
      {/* Status Header */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Optimistic State</span>
        <Badge variant={isOptimistic ? 'default' : 'secondary'}>
          {isOptimistic ? '⚡ Active' : '✓ Synced'}
        </Badge>
      </div>

      {/* Pending Predictions */}
      {groupedPredictions.pending.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2 text-yellow-600">
            Pending ({groupedPredictions.pending.length})
          </h4>
          <div className="space-y-2">
            {groupedPredictions.pending.map((prediction) => (
              <PredictionItem
                key={prediction.predictionId}
                prediction={prediction}
                onConfirm={onConfirm}
                onRollback={onRollback}
              />
            ))}
          </div>
        </div>
      )}

      {/* Conflicted Predictions */}
      {groupedPredictions.conflicted.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2 text-red-600">
            Conflicts ({groupedPredictions.conflicted.length})
          </h4>
          <div className="space-y-2">
            {groupedPredictions.conflicted.map((prediction) => (
              <PredictionItem
                key={prediction.predictionId}
                prediction={prediction}
                onRollback={onRollback}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent History */}
      {groupedPredictions.recent.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2 text-muted-foreground">Recent</h4>
          <div className="space-y-2 opacity-60">
            {groupedPredictions.recent.map((prediction) => (
              <PredictionItem key={prediction.predictionId} prediction={prediction} />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {predictions.length === 0 && (
        <p className="text-sm text-muted-foreground">No predictions in progress</p>
      )}
    </div>
  );
};

export default OptimisticIndicator;
