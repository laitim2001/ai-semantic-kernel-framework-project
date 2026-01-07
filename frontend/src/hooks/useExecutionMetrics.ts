/**
 * useExecutionMetrics - Execution Metrics Tracking Hook
 *
 * Sprint 65: Metrics, Checkpoints & Polish
 * S65-1: useExecutionMetrics Hook
 * Phase 16: Unified Agentic Chat Interface
 *
 * Tracks and provides comprehensive execution metrics including:
 * - Token usage (used, limit, percentage)
 * - Execution time with timer
 * - Tool call statistics
 * - Message counts
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

/** Token metrics with formatted display */
export interface TokenMetrics {
  used: number;
  limit: number;
  percentage: number;
  formatted: string; // e.g., "1.2K/4K"
}

/** Time metrics with formatted display */
export interface TimeMetrics {
  total: number; // milliseconds
  isRunning: boolean;
  formatted: string; // e.g., "3.5s" or "2m 30s"
}

/** Tool call statistics */
export interface ToolMetrics {
  total: number;
  completed: number;
  failed: number;
  pending: number;
}

/** Message statistics */
export interface MessageMetrics {
  total: number;
  user: number;
  assistant: number;
  tool: number;
}

/** Complete execution metrics */
export interface ExecutionMetricsState {
  tokens: TokenMetrics;
  time: TimeMetrics;
  tools: ToolMetrics;
  messages: MessageMetrics;
}

/** Hook options */
export interface UseExecutionMetricsOptions {
  /** Default token limit */
  defaultTokenLimit?: number;
  /** Timer update interval in ms */
  timerInterval?: number;
  /** Initial metrics state */
  initialMetrics?: Partial<ExecutionMetricsState>;
}

/** Hook return type */
export interface UseExecutionMetricsReturn {
  // Metrics state
  tokens: TokenMetrics;
  time: TimeMetrics;
  tools: ToolMetrics;
  messages: MessageMetrics;

  // Token actions
  updateTokens: (used: number, limit?: number) => void;
  setTokenLimit: (limit: number) => void;

  // Timer actions
  startTimer: () => void;
  stopTimer: () => void;
  resetTimer: () => void;

  // Tool tracking actions
  incrementToolCall: (status?: 'pending' | 'completed' | 'failed') => void;
  updateToolStatus: (from: 'pending' | 'completed' | 'failed', to: 'pending' | 'completed' | 'failed') => void;
  setToolMetrics: (metrics: Partial<ToolMetrics>) => void;

  // Message tracking actions
  incrementMessage: (role: 'user' | 'assistant' | 'tool') => void;
  setMessageMetrics: (metrics: Partial<MessageMetrics>) => void;

  // Reset
  resetMetrics: () => void;

  // Computed
  isHighUsage: boolean; // Token usage > 75%
  isCriticalUsage: boolean; // Token usage > 90%
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format token count with K suffix for large numbers
 */
const formatTokenCount = (count: number): string => {
  if (count >= 10000) {
    return `${(count / 1000).toFixed(0)}K`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

/**
 * Format token usage as "used/limit"
 */
const formatTokenUsage = (used: number, limit: number): string => {
  return `${formatTokenCount(used)}/${formatTokenCount(limit)}`;
};

/**
 * Format duration in milliseconds to human-readable string
 */
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;

  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
};

/**
 * Calculate percentage safely
 */
const calculatePercentage = (used: number, limit: number): number => {
  if (limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
};

// =============================================================================
// Default State
// =============================================================================

const DEFAULT_TOKEN_LIMIT = 4000;
const DEFAULT_TIMER_INTERVAL = 100;

const createDefaultMetrics = (options?: UseExecutionMetricsOptions): ExecutionMetricsState => {
  const tokenLimit = options?.defaultTokenLimit ?? DEFAULT_TOKEN_LIMIT;

  return {
    tokens: {
      used: 0,
      limit: tokenLimit,
      percentage: 0,
      formatted: formatTokenUsage(0, tokenLimit),
    },
    time: {
      total: 0,
      isRunning: false,
      formatted: '0s',
    },
    tools: {
      total: 0,
      completed: 0,
      failed: 0,
      pending: 0,
    },
    messages: {
      total: 0,
      user: 0,
      assistant: 0,
      tool: 0,
    },
    ...options?.initialMetrics,
  };
};

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * useExecutionMetrics Hook
 *
 * Tracks comprehensive execution metrics for the unified chat interface.
 *
 * @example
 * ```tsx
 * const {
 *   tokens,
 *   time,
 *   tools,
 *   messages,
 *   startTimer,
 *   stopTimer,
 *   updateTokens,
 *   incrementMessage,
 * } = useExecutionMetrics({ defaultTokenLimit: 8000 });
 *
 * // Display metrics
 * <div>Tokens: {tokens.formatted}</div>
 * <div>Time: {time.formatted}</div>
 * <div>Tools: {tools.completed}/{tools.total}</div>
 * ```
 */
export function useExecutionMetrics(
  options: UseExecutionMetricsOptions = {}
): UseExecutionMetricsReturn {
  const { timerInterval = DEFAULT_TIMER_INTERVAL } = options;

  // State
  const [metrics, setMetrics] = useState<ExecutionMetricsState>(() =>
    createDefaultMetrics(options)
  );

  // Timer refs
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // ==========================================================================
  // Token Actions
  // ==========================================================================

  const updateTokens = useCallback((used: number, limit?: number) => {
    setMetrics((prev) => {
      const newLimit = limit ?? prev.tokens.limit;
      const percentage = calculatePercentage(used, newLimit);
      return {
        ...prev,
        tokens: {
          used,
          limit: newLimit,
          percentage,
          formatted: formatTokenUsage(used, newLimit),
        },
      };
    });
  }, []);

  const setTokenLimit = useCallback((limit: number) => {
    setMetrics((prev) => {
      const percentage = calculatePercentage(prev.tokens.used, limit);
      return {
        ...prev,
        tokens: {
          ...prev.tokens,
          limit,
          percentage,
          formatted: formatTokenUsage(prev.tokens.used, limit),
        },
      };
    });
  }, []);

  // ==========================================================================
  // Timer Actions
  // ==========================================================================

  const startTimer = useCallback(() => {
    if (timerRef.current) return; // Already running

    startTimeRef.current = Date.now();

    setMetrics((prev) => ({
      ...prev,
      time: {
        ...prev.time,
        isRunning: true,
      },
    }));

    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        const elapsed = Date.now() - startTimeRef.current;
        setMetrics((prev) => ({
          ...prev,
          time: {
            total: prev.time.total + timerInterval,
            isRunning: true,
            formatted: formatDuration(prev.time.total + timerInterval),
          },
        }));
      }
    }, timerInterval);
  }, [timerInterval]);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    startTimeRef.current = null;

    setMetrics((prev) => ({
      ...prev,
      time: {
        ...prev.time,
        isRunning: false,
      },
    }));
  }, []);

  const resetTimer = useCallback(() => {
    stopTimer();
    setMetrics((prev) => ({
      ...prev,
      time: {
        total: 0,
        isRunning: false,
        formatted: '0s',
      },
    }));
  }, [stopTimer]);

  // ==========================================================================
  // Tool Tracking Actions
  // ==========================================================================

  const incrementToolCall = useCallback(
    (status: 'pending' | 'completed' | 'failed' = 'pending') => {
      setMetrics((prev) => ({
        ...prev,
        tools: {
          ...prev.tools,
          total: prev.tools.total + 1,
          [status]: prev.tools[status] + 1,
        },
      }));
    },
    []
  );

  const updateToolStatus = useCallback(
    (from: 'pending' | 'completed' | 'failed', to: 'pending' | 'completed' | 'failed') => {
      if (from === to) return;

      setMetrics((prev) => ({
        ...prev,
        tools: {
          ...prev.tools,
          [from]: Math.max(0, prev.tools[from] - 1),
          [to]: prev.tools[to] + 1,
        },
      }));
    },
    []
  );

  const setToolMetrics = useCallback((toolMetrics: Partial<ToolMetrics>) => {
    setMetrics((prev) => ({
      ...prev,
      tools: {
        ...prev.tools,
        ...toolMetrics,
      },
    }));
  }, []);

  // ==========================================================================
  // Message Tracking Actions
  // ==========================================================================

  const incrementMessage = useCallback((role: 'user' | 'assistant' | 'tool') => {
    setMetrics((prev) => ({
      ...prev,
      messages: {
        ...prev.messages,
        total: prev.messages.total + 1,
        [role]: prev.messages[role] + 1,
      },
    }));
  }, []);

  const setMessageMetrics = useCallback((messageMetrics: Partial<MessageMetrics>) => {
    setMetrics((prev) => {
      const newMessages = { ...prev.messages, ...messageMetrics };
      // Recalculate total if individual counts were updated
      if ('user' in messageMetrics || 'assistant' in messageMetrics || 'tool' in messageMetrics) {
        newMessages.total = newMessages.user + newMessages.assistant + newMessages.tool;
      }
      return {
        ...prev,
        messages: newMessages,
      };
    });
  }, []);

  // ==========================================================================
  // Reset
  // ==========================================================================

  const resetMetrics = useCallback(() => {
    stopTimer();
    setMetrics(createDefaultMetrics(options));
  }, [stopTimer, options]);

  // ==========================================================================
  // Computed Values
  // ==========================================================================

  const isHighUsage = useMemo(() => metrics.tokens.percentage >= 75, [metrics.tokens.percentage]);
  const isCriticalUsage = useMemo(() => metrics.tokens.percentage >= 90, [metrics.tokens.percentage]);

  // ==========================================================================
  // Cleanup
  // ==========================================================================

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // Metrics state
    tokens: metrics.tokens,
    time: metrics.time,
    tools: metrics.tools,
    messages: metrics.messages,

    // Token actions
    updateTokens,
    setTokenLimit,

    // Timer actions
    startTimer,
    stopTimer,
    resetTimer,

    // Tool tracking actions
    incrementToolCall,
    updateToolStatus,
    setToolMetrics,

    // Message tracking actions
    incrementMessage,
    setMessageMetrics,

    // Reset
    resetMetrics,

    // Computed
    isHighUsage,
    isCriticalUsage,
  };
}

export default useExecutionMetrics;
