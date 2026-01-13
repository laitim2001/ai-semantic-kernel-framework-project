// =============================================================================
// IPA Platform - DevUI Duration Bar Component
// =============================================================================
// Sprint 88: S88-1 - Timeline Visualization
//
// Visual duration bar showing relative execution time.
//
// Dependencies:
//   - Tailwind CSS
// =============================================================================

import { FC } from 'react';
import { cn } from '@/lib/utils';

interface DurationBarProps {
  /** Duration in milliseconds */
  durationMs: number;
  /** Maximum duration for scale (ms) */
  maxDurationMs: number;
  /** Color variant */
  variant?: 'default' | 'success' | 'warning' | 'error';
  /** Show duration label */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Format duration in human-readable form
 */
function formatDuration(ms: number): string {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Duration Bar Component
 * Displays a visual bar representing execution duration
 */
export const DurationBar: FC<DurationBarProps> = ({
  durationMs,
  maxDurationMs,
  variant = 'default',
  showLabel = true,
  className,
}) => {
  // Calculate percentage width (min 2% for visibility)
  const percentage = Math.max(
    2,
    Math.min(100, (durationMs / maxDurationMs) * 100)
  );

  // Determine color based on variant
  const barColors = {
    default: 'bg-purple-500',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  const bgColors = {
    default: 'bg-purple-100',
    success: 'bg-green-100',
    warning: 'bg-yellow-100',
    error: 'bg-red-100',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Bar container */}
      <div className={cn('flex-1 h-2 rounded-full', bgColors[variant])}>
        <div
          className={cn('h-full rounded-full transition-all duration-300', barColors[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Duration label */}
      {showLabel && (
        <span className="text-xs text-gray-500 min-w-[48px] text-right font-mono">
          {formatDuration(durationMs)}
        </span>
      )}
    </div>
  );
};

/**
 * Compact duration display for inline use
 */
export const DurationBadge: FC<{
  durationMs?: number;
  variant?: 'default' | 'success' | 'warning' | 'error';
}> = ({ durationMs, variant = 'default' }) => {
  if (durationMs === undefined || durationMs === null) {
    return (
      <span className="text-xs text-gray-400 font-mono">-</span>
    );
  }

  const bgColors = {
    default: 'bg-gray-100 text-gray-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
  };

  return (
    <span className={cn(
      'px-2 py-0.5 text-xs rounded font-mono',
      bgColors[variant]
    )}>
      {formatDuration(durationMs)}
    </span>
  );
};

export default DurationBar;
