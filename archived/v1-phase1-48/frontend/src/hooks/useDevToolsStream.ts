// =============================================================================
// IPA Platform - DevTools Streaming Hook
// =============================================================================
// Sprint 89: S89-2 - Real-time Trace Updates
//
// SSE-based hook for real-time trace event streaming.
//
// Dependencies:
//   - EventSource API (browser native)
// =============================================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import type { TraceEvent } from '@/types/devtools';

/**
 * Connection status
 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Hook options
 */
export interface UseDevToolsStreamOptions {
  /** Auto-connect on mount */
  autoConnect?: boolean;
  /** Reconnect on error */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number;
  /** On event received callback */
  onEvent?: (event: TraceEvent) => void;
  /** On error callback */
  onError?: (error: Error) => void;
  /** On connection status change */
  onStatusChange?: (status: ConnectionStatus) => void;
}

/**
 * Hook return type
 */
export interface UseDevToolsStreamReturn {
  /** Received events */
  events: TraceEvent[];
  /** Connection status */
  status: ConnectionStatus;
  /** Is connected */
  isConnected: boolean;
  /** Is paused */
  isPaused: boolean;
  /** Last update timestamp */
  lastUpdate: Date | null;
  /** Error message if any */
  error: string | null;
  /** Reconnect attempt count */
  reconnectAttempts: number;
  /** Connect to stream */
  connect: () => void;
  /** Disconnect from stream */
  disconnect: () => void;
  /** Pause receiving events */
  pause: () => void;
  /** Resume receiving events */
  resume: () => void;
  /** Clear received events */
  clearEvents: () => void;
}

/**
 * SSE hook for real-time trace streaming
 */
export function useDevToolsStream(
  executionId: string | undefined,
  options: UseDevToolsStreamOptions = {}
): UseDevToolsStreamReturn {
  const {
    autoConnect = true,
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
    onEvent,
    onError,
    onStatusChange,
  } = options;

  // State
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isPaused, setIsPaused] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs for cleanup
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pausedEventsRef = useRef<TraceEvent[]>([]);

  // Update status with callback
  const updateStatus = useCallback(
    (newStatus: ConnectionStatus) => {
      setStatus(newStatus);
      onStatusChange?.(newStatus);
    },
    [onStatusChange]
  );

  // Connect to SSE stream
  const connect = useCallback(() => {
    if (!executionId) return;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    updateStatus('connecting');
    setError(null);

    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    const url = `${apiBase}/devtools/traces/${executionId}/stream`;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        updateStatus('connected');
        setReconnectAttempts(0);
      };

      eventSource.onmessage = (e) => {
        try {
          const event: TraceEvent = JSON.parse(e.data);
          setLastUpdate(new Date());

          if (isPaused) {
            pausedEventsRef.current.push(event);
          } else {
            setEvents((prev) => [...prev, event]);
            onEvent?.(event);
          }
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = (e) => {
        console.error('SSE connection error:', e);
        updateStatus('error');
        setError('Connection lost');
        eventSource.close();
        eventSourceRef.current = null;

        // Auto-reconnect logic
        if (autoReconnect && reconnectAttempts < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connect();
          }, reconnectDelay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          const err = new Error('Max reconnect attempts reached');
          onError?.(err);
        }
      };

      // Handle specific event types
      eventSource.addEventListener('trace_complete', () => {
        updateStatus('disconnected');
        eventSource.close();
        eventSourceRef.current = null;
      });

      eventSource.addEventListener('error', (e: MessageEvent) => {
        const errData = JSON.parse(e.data);
        setError(errData.message || 'Stream error');
        onError?.(new Error(errData.message));
      });
    } catch (err) {
      updateStatus('error');
      setError((err as Error).message);
      onError?.(err as Error);
    }
  }, [
    executionId,
    isPaused,
    autoReconnect,
    reconnectDelay,
    maxReconnectAttempts,
    reconnectAttempts,
    updateStatus,
    onEvent,
    onError,
  ]);

  // Disconnect from stream
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    updateStatus('disconnected');
    setReconnectAttempts(0);
  }, [updateStatus]);

  // Pause receiving events
  const pause = useCallback(() => {
    setIsPaused(true);
    pausedEventsRef.current = [];
  }, []);

  // Resume receiving events
  const resume = useCallback(() => {
    setIsPaused(false);
    // Flush paused events
    if (pausedEventsRef.current.length > 0) {
      setEvents((prev) => [...prev, ...pausedEventsRef.current]);
      pausedEventsRef.current = [];
    }
  }, []);

  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
    pausedEventsRef.current = [];
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && executionId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [executionId, autoConnect]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    events,
    status,
    isConnected: status === 'connected',
    isPaused,
    lastUpdate,
    error,
    reconnectAttempts,
    connect,
    disconnect,
    pause,
    resume,
    clearEvents,
  };
}

export default useDevToolsStream;
