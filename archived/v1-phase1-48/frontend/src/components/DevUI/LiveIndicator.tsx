// =============================================================================
// IPA Platform - DevUI Live Indicator Component
// =============================================================================
// Sprint 89: S89-2 - Real-time Trace Updates
//
// Visual indicator for real-time streaming connection status.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC } from 'react';
import {
  Radio,
  Wifi,
  WifiOff,
  Loader2,
  AlertCircle,
  Pause,
  Play,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ConnectionStatus } from '@/hooks/useDevToolsStream';

interface LiveIndicatorProps {
  /** Connection status */
  status: ConnectionStatus;
  /** Is paused */
  isPaused?: boolean;
  /** Last update time */
  lastUpdate?: Date | null;
  /** Reconnect attempts */
  reconnectAttempts?: number;
  /** Max reconnect attempts */
  maxReconnectAttempts?: number;
  /** Pause handler */
  onPause?: () => void;
  /** Resume handler */
  onResume?: () => void;
  /** Disconnect handler */
  onDisconnect?: () => void;
  /** Reconnect handler */
  onReconnect?: () => void;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Format last update time
 */
function formatLastUpdate(date: Date | null): string {
  if (!date) return '-';
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Live Indicator Component
 * Shows real-time streaming connection status
 */
export const LiveIndicator: FC<LiveIndicatorProps> = ({
  status,
  isPaused = false,
  lastUpdate,
  reconnectAttempts = 0,
  maxReconnectAttempts = 5,
  onPause,
  onResume,
  onDisconnect,
  onReconnect,
  compact = false,
  className,
}) => {
  // Status configuration
  const statusConfig = {
    disconnected: {
      icon: WifiOff,
      color: 'text-gray-500',
      bgColor: 'bg-gray-100',
      label: '已斷開',
      pulse: false,
    },
    connecting: {
      icon: Loader2,
      color: 'text-blue-500',
      bgColor: 'bg-blue-100',
      label: '連接中...',
      pulse: false,
    },
    connected: {
      icon: isPaused ? Pause : Radio,
      color: isPaused ? 'text-yellow-500' : 'text-green-500',
      bgColor: isPaused ? 'bg-yellow-100' : 'bg-green-100',
      label: isPaused ? '已暫停' : '實時追蹤中',
      pulse: !isPaused,
    },
    error: {
      icon: AlertCircle,
      color: 'text-red-500',
      bgColor: 'bg-red-100',
      label: '連接錯誤',
      pulse: false,
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  // Compact mode - just show indicator dot
  if (compact) {
    return (
      <div
        className={cn('flex items-center gap-2', className)}
        title={`${config.label}${lastUpdate ? ` - 最後更新: ${formatLastUpdate(lastUpdate)}` : ''}`}
      >
        <div className="relative flex items-center">
          <div
            className={cn(
              'w-2 h-2 rounded-full',
              status === 'connected' && !isPaused ? 'bg-green-500' : '',
              status === 'connected' && isPaused ? 'bg-yellow-500' : '',
              status === 'connecting' ? 'bg-blue-500' : '',
              status === 'disconnected' ? 'bg-gray-400' : '',
              status === 'error' ? 'bg-red-500' : ''
            )}
          />
          {config.pulse && (
            <div
              className={cn(
                'absolute inset-0 w-2 h-2 rounded-full animate-ping',
                status === 'connected' && !isPaused ? 'bg-green-500' : ''
              )}
            />
          )}
        </div>
        <span className="text-xs text-gray-500">{config.label}</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg border',
        config.bgColor,
        'border-transparent',
        className
      )}
    >
      {/* Status icon */}
      <div className="relative flex items-center">
        <Icon
          className={cn(
            'w-4 h-4',
            config.color,
            status === 'connecting' && 'animate-spin'
          )}
        />
        {config.pulse && (
          <div
            className={cn(
              'absolute inset-0 w-4 h-4 rounded-full animate-ping opacity-50',
              status === 'connected' && !isPaused ? 'bg-green-500' : ''
            )}
          />
        )}
      </div>

      {/* Status text */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('text-sm font-medium', config.color)}>
            {config.label}
          </span>
          {status === 'error' && reconnectAttempts > 0 && (
            <span className="text-xs text-gray-500">
              (重試 {reconnectAttempts}/{maxReconnectAttempts})
            </span>
          )}
        </div>
        {lastUpdate && status === 'connected' && (
          <span className="text-xs text-gray-500">
            最後更新: {formatLastUpdate(lastUpdate)}
          </span>
        )}
      </div>

      {/* Control buttons */}
      <div className="flex items-center gap-1">
        {status === 'connected' && (
          <>
            {isPaused ? (
              <button
                onClick={onResume}
                className="p-1 hover:bg-white/50 rounded transition-colors"
                title="繼續"
              >
                <Play className="w-4 h-4 text-green-600" />
              </button>
            ) : (
              <button
                onClick={onPause}
                className="p-1 hover:bg-white/50 rounded transition-colors"
                title="暫停"
              >
                <Pause className="w-4 h-4 text-yellow-600" />
              </button>
            )}
            <button
              onClick={onDisconnect}
              className="p-1 hover:bg-white/50 rounded transition-colors"
              title="斷開連接"
            >
              <WifiOff className="w-4 h-4 text-gray-500" />
            </button>
          </>
        )}

        {(status === 'disconnected' || status === 'error') && (
          <button
            onClick={onReconnect}
            className="p-1 hover:bg-white/50 rounded transition-colors"
            title="重新連接"
          >
            <RefreshCw className="w-4 h-4 text-blue-600" />
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * Minimal dot indicator for inline use
 */
export const LiveDot: FC<{
  isLive: boolean;
  className?: string;
}> = ({ isLive, className }) => (
  <div className={cn('relative flex items-center', className)}>
    <div
      className={cn(
        'w-2 h-2 rounded-full',
        isLive ? 'bg-green-500' : 'bg-gray-400'
      )}
    />
    {isLive && (
      <div className="absolute inset-0 w-2 h-2 rounded-full bg-green-500 animate-ping" />
    )}
  </div>
);

/**
 * Connection badge for status display
 */
export const ConnectionBadge: FC<{
  status: ConnectionStatus;
  className?: string;
}> = ({ status, className }) => {
  const badges = {
    disconnected: { label: '離線', color: 'bg-gray-100 text-gray-600' },
    connecting: { label: '連接中', color: 'bg-blue-100 text-blue-600' },
    connected: { label: '在線', color: 'bg-green-100 text-green-600' },
    error: { label: '錯誤', color: 'bg-red-100 text-red-600' },
  };

  const badge = badges[status];

  return (
    <span
      className={cn(
        'px-2 py-0.5 text-xs font-medium rounded',
        badge.color,
        className
      )}
    >
      {status === 'connecting' && (
        <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />
      )}
      {status === 'connected' && <Wifi className="w-3 h-3 inline-block mr-1" />}
      {badge.label}
    </span>
  );
};

export default LiveIndicator;
