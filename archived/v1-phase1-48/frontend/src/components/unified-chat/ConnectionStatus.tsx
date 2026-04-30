/**
 * ConnectionStatus - Connection Status Indicator
 *
 * Sprint 65: Metrics, Checkpoints & Polish
 * S65-3: Error Handling & Recovery
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays current SSE connection status with reconnect option.
 */

import { FC, useMemo } from 'react';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import type { ConnectionStatus as ConnectionStatusType } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface ConnectionStatusProps {
  /** Current connection status */
  status: ConnectionStatusType;
  /** Number of reconnection attempts */
  retryCount?: number;
  /** Maximum retries before giving up */
  maxRetries?: number;
  /** Callback to manually reconnect */
  onReconnect?: () => void;
  /** Error message if status is 'error' */
  errorMessage?: string;
  /** Whether to show compact version */
  compact?: boolean;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Configuration
// =============================================================================

const STATUS_CONFIG: Record<
  ConnectionStatusType,
  {
    icon: typeof Wifi;
    label: string;
    color: string;
    bgColor: string;
    animate?: boolean;
  }
> = {
  connected: {
    icon: Wifi,
    label: 'Connected',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
  connecting: {
    icon: Loader2,
    label: 'Connecting...',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    animate: true,
  },
  disconnected: {
    icon: WifiOff,
    label: 'Disconnected',
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
  },
  error: {
    icon: AlertCircle,
    label: 'Connection Error',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
  },
};

// =============================================================================
// Component
// =============================================================================

/**
 * ConnectionStatus Component
 *
 * Shows the current SSE connection status with visual indicators
 * and provides reconnection capability.
 *
 * @example
 * ```tsx
 * <ConnectionStatus
 *   status="disconnected"
 *   retryCount={3}
 *   maxRetries={5}
 *   onReconnect={handleReconnect}
 * />
 * ```
 */
export const ConnectionStatus: FC<ConnectionStatusProps> = ({
  status,
  retryCount = 0,
  maxRetries = 5,
  onReconnect,
  errorMessage,
  compact = false,
  className,
}) => {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  // Determine if we should show reconnect button
  const showReconnect = useMemo(() => {
    return (
      onReconnect &&
      (status === 'disconnected' || status === 'error') &&
      retryCount >= maxRetries
    );
  }, [status, retryCount, maxRetries, onReconnect]);

  // Determine if we're in auto-retry mode
  const isAutoRetrying = useMemo(() => {
    return status === 'connecting' && retryCount > 0;
  }, [status, retryCount]);

  // Compact version - just the indicator
  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'inline-flex items-center gap-1.5 px-2 py-1 rounded-full cursor-help',
                config.bgColor,
                className
              )}
              data-testid="connection-status"
              data-status={status}
            >
              <Icon
                className={cn(
                  'h-3.5 w-3.5',
                  config.color,
                  config.animate && 'animate-spin'
                )}
              />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{config.label}</p>
              {isAutoRetrying && (
                <p className="text-xs text-gray-400">
                  Retry {retryCount}/{maxRetries}
                </p>
              )}
              {errorMessage && (
                <p className="text-xs text-red-400">{errorMessage}</p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Full version
  return (
    <div
      className={cn(
        'inline-flex items-center gap-2',
        className
      )}
      data-testid="connection-status"
      data-status={status}
    >
      {/* Status Badge */}
      <div
        className={cn(
          'inline-flex items-center gap-1.5 px-2 py-1 rounded-full',
          config.bgColor
        )}
      >
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            config.color,
            config.animate && 'animate-spin'
          )}
        />
        <span className={cn('text-xs font-medium', config.color)}>
          {config.label}
        </span>
      </div>

      {/* Retry Counter */}
      {isAutoRetrying && (
        <span className="text-xs text-gray-500">
          Retry {retryCount}/{maxRetries}
        </span>
      )}

      {/* Error Message */}
      {status === 'error' && errorMessage && (
        <span className="text-xs text-red-500 max-w-32 truncate" title={errorMessage}>
          {errorMessage}
        </span>
      )}

      {/* Manual Reconnect Button */}
      {showReconnect && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onReconnect}
          className="h-7 px-2 text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Reconnect
        </Button>
      )}
    </div>
  );
};

export default ConnectionStatus;
