/**
 * useSharedState - Shared State Hook
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-2: Shared State
 *
 * React hook for managing shared state with server synchronization.
 * Supports bidirectional sync via SSE, conflict resolution, and offline support.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type {
  SharedState,
  StateDiff,
  StateConflict,
  StateSyncStatus,
  StateSyncEvent,
  DiffOperation,
  ConflictResolutionStrategy,
  StateVersion,
} from '@/types/ag-ui';

/** Hook configuration options */
export interface UseSharedStateOptions {
  /** Session ID for state isolation */
  sessionId: string;
  /** API base URL for state sync */
  apiUrl?: string;
  /** SSE endpoint for real-time updates */
  sseEndpoint?: string;
  /** Initial state values */
  initialState?: Record<string, unknown>;
  /** Conflict resolution strategy */
  conflictStrategy?: ConflictResolutionStrategy;
  /** Auto-sync interval in ms (0 to disable) */
  autoSyncInterval?: number;
  /** Enable offline support */
  offlineSupport?: boolean;
  /** Callback when state changes */
  onStateChange?: (state: Record<string, unknown>) => void;
  /** Callback when sync status changes */
  onSyncStatusChange?: (status: StateSyncStatus) => void;
  /** Callback when conflict occurs */
  onConflict?: (conflict: StateConflict) => void;
}

/** Hook return value */
export interface UseSharedStateReturn {
  /** Current state */
  state: Record<string, unknown>;
  /** Shared state with metadata */
  sharedState: SharedState;
  /** Current sync status */
  syncStatus: StateSyncStatus;
  /** Get value at path */
  get: <T = unknown>(path: string) => T | undefined;
  /** Set value at path */
  set: (path: string, value: unknown) => void;
  /** Delete value at path */
  remove: (path: string) => void;
  /** Apply multiple diffs atomically */
  applyDiffs: (diffs: StateDiff[]) => void;
  /** Force sync with server */
  forceSync: () => Promise<void>;
  /** Clear all state */
  clearState: () => void;
  /** Resolve a conflict */
  resolveConflict: (conflict: StateConflict, resolution: 'client' | 'server') => void;
  /** Check if connected to server */
  isConnected: boolean;
}

/**
 * Get nested value from object by path
 */
const getByPath = (obj: Record<string, unknown>, path: string): unknown => {
  const keys = path.split('.');
  let current: unknown = obj;

  for (const key of keys) {
    if (current === null || current === undefined) return undefined;
    if (typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[key];
  }

  return current;
};

/**
 * Set nested value in object by path (immutable)
 */
const setByPath = (
  obj: Record<string, unknown>,
  path: string,
  value: unknown
): Record<string, unknown> => {
  const keys = path.split('.');
  const result = { ...obj };

  let current = result;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    current[key] = { ...(current[key] as Record<string, unknown> || {}) };
    current = current[key] as Record<string, unknown>;
  }

  current[keys[keys.length - 1]] = value;
  return result;
};

/**
 * Delete nested value from object by path (immutable)
 */
const deleteByPath = (
  obj: Record<string, unknown>,
  path: string
): Record<string, unknown> => {
  const keys = path.split('.');
  const result = { ...obj };

  if (keys.length === 1) {
    delete result[keys[0]];
    return result;
  }

  let current = result;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    current[key] = { ...(current[key] as Record<string, unknown> || {}) };
    current = current[key] as Record<string, unknown>;
  }

  delete current[keys[keys.length - 1]];
  return result;
};

/**
 * useSharedState - Main hook implementation
 */
export function useSharedState(options: UseSharedStateOptions): UseSharedStateReturn {
  const {
    sessionId,
    apiUrl = '/api/v1/ag-ui/state',
    sseEndpoint = '/api/v1/ag-ui/state/stream',
    initialState = {},
    conflictStrategy = 'last_write_wins',
    autoSyncInterval = 0,
    offlineSupport = true,
    onStateChange,
    onSyncStatusChange,
    onConflict,
  } = options;

  // State management
  const [state, setState] = useState<Record<string, unknown>>(initialState);
  const [version, setVersion] = useState<StateVersion>({
    version: 0,
    timestamp: new Date().toISOString(),
    source: 'client',
  });
  const [pendingDiffs, setPendingDiffs] = useState<StateDiff[]>([]);
  const [conflicts, setConflicts] = useState<StateConflict[]>([]);
  const [syncStatus, setSyncStatus] = useState<StateSyncStatus>('pending');
  const [isConnected, setIsConnected] = useState(false);

  // Refs for SSE and intervals
  const eventSourceRef = useRef<EventSource | null>(null);
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Shared state object
  const sharedState = useMemo<SharedState>(
    () => ({
      sessionId,
      state,
      version,
      lastSync: version.timestamp,
      pendingDiffs,
      conflicts,
    }),
    [sessionId, state, version, pendingDiffs, conflicts]
  );

  // Update sync status and notify
  const updateSyncStatus = useCallback(
    (newStatus: StateSyncStatus) => {
      setSyncStatus(newStatus);
      onSyncStatusChange?.(newStatus);
    },
    [onSyncStatusChange]
  );

  // Get value at path
  const get = useCallback(
    <T = unknown>(path: string): T | undefined => {
      return getByPath(state, path) as T | undefined;
    },
    [state]
  );

  // Set value at path
  const set = useCallback(
    (path: string, value: unknown) => {
      const oldValue = getByPath(state, path);
      const diff: StateDiff = {
        path,
        operation: oldValue === undefined ? 'add' : 'replace',
        oldValue,
        newValue: value,
      };

      setState((prev) => {
        const newState = setByPath(prev, path, value);
        onStateChange?.(newState);
        return newState;
      });

      setPendingDiffs((prev) => [...prev, diff]);
      updateSyncStatus('pending');
    },
    [state, onStateChange, updateSyncStatus]
  );

  // Remove value at path
  const remove = useCallback(
    (path: string) => {
      const oldValue = getByPath(state, path);
      if (oldValue === undefined) return;

      const diff: StateDiff = {
        path,
        operation: 'remove',
        oldValue,
      };

      setState((prev) => {
        const newState = deleteByPath(prev, path);
        onStateChange?.(newState);
        return newState;
      });

      setPendingDiffs((prev) => [...prev, diff]);
      updateSyncStatus('pending');
    },
    [state, onStateChange, updateSyncStatus]
  );

  // Apply multiple diffs atomically
  const applyDiffs = useCallback(
    (diffs: StateDiff[]) => {
      setState((prev) => {
        let newState = prev;
        for (const diff of diffs) {
          switch (diff.operation) {
            case 'add':
            case 'replace':
              newState = setByPath(newState, diff.path, diff.newValue);
              break;
            case 'remove':
              newState = deleteByPath(newState, diff.path);
              break;
          }
        }
        onStateChange?.(newState);
        return newState;
      });

      setPendingDiffs((prev) => [...prev, ...diffs]);
      updateSyncStatus('pending');
    },
    [onStateChange, updateSyncStatus]
  );

  // Force sync with server
  const forceSync = useCallback(async () => {
    if (pendingDiffs.length === 0) {
      updateSyncStatus('synced');
      return;
    }

    updateSyncStatus('syncing');

    try {
      const response = await fetch(`${apiUrl}/${sessionId}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          diffs: pendingDiffs,
          version: version.version,
          conflictStrategy,
        }),
      });

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.status}`);
      }

      const result = await response.json();

      // Update version
      setVersion({
        version: result.version,
        timestamp: new Date().toISOString(),
        source: 'server',
      });

      // Clear pending diffs
      setPendingDiffs([]);

      // Handle any conflicts from server
      if (result.conflicts?.length > 0) {
        setConflicts(result.conflicts);
        result.conflicts.forEach((c: StateConflict) => onConflict?.(c));
        updateSyncStatus('conflict');
      } else {
        updateSyncStatus('synced');
      }
    } catch (error) {
      console.error('Sync error:', error);
      updateSyncStatus('error');

      // Store locally if offline support enabled
      if (offlineSupport) {
        try {
          localStorage.setItem(
            `ag-ui-state-${sessionId}`,
            JSON.stringify({ state, pendingDiffs, version })
          );
        } catch {
          // localStorage might be full or unavailable
        }
      }
    }
  }, [
    apiUrl,
    sessionId,
    pendingDiffs,
    version,
    conflictStrategy,
    state,
    offlineSupport,
    onConflict,
    updateSyncStatus,
  ]);

  // Clear all state
  const clearState = useCallback(() => {
    setState({});
    setPendingDiffs([]);
    setConflicts([]);
    setVersion({
      version: 0,
      timestamp: new Date().toISOString(),
      source: 'client',
    });
    updateSyncStatus('pending');
    onStateChange?.({});
  }, [onStateChange, updateSyncStatus]);

  // Resolve a conflict
  const resolveConflict = useCallback(
    (conflict: StateConflict, resolution: 'client' | 'server') => {
      const resolvedValue = resolution === 'client' ? conflict.clientValue : conflict.serverValue;

      setState((prev) => setByPath(prev, conflict.path, resolvedValue));
      setConflicts((prev) => prev.filter((c) => c.path !== conflict.path));

      // Check if all conflicts resolved
      if (conflicts.length <= 1) {
        updateSyncStatus('pending');
      }
    },
    [conflicts.length, updateSyncStatus]
  );

  // Handle SSE events
  const handleSSEEvent = useCallback(
    (event: StateSyncEvent) => {
      switch (event.type) {
        case 'snapshot':
          setState(event.data as Record<string, unknown>);
          setVersion({
            version: event.version,
            timestamp: event.timestamp,
            source: 'server',
          });
          updateSyncStatus('synced');
          break;

        case 'delta':
          const deltas = event.data as StateDiff[];
          applyDiffs(deltas);
          setVersion((prev) => ({
            ...prev,
            version: event.version,
            timestamp: event.timestamp,
          }));
          break;

        case 'conflict':
          const conflict = event.data as StateConflict;
          setConflicts((prev) => [...prev, conflict]);
          onConflict?.(conflict);
          updateSyncStatus('conflict');
          break;

        case 'ack':
          // Server acknowledged our changes
          setPendingDiffs([]);
          updateSyncStatus('synced');
          break;
      }
    },
    [applyDiffs, onConflict, updateSyncStatus]
  );

  // Setup SSE connection
  useEffect(() => {
    const eventSource = new EventSource(`${sseEndpoint}?sessionId=${sessionId}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      updateSyncStatus('synced');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StateSyncEvent;
        handleSSEEvent(data);
      } catch (error) {
        console.error('SSE parse error:', error);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      updateSyncStatus('error');
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [sessionId, sseEndpoint, handleSSEEvent, updateSyncStatus]);

  // Setup auto-sync interval
  useEffect(() => {
    if (autoSyncInterval > 0) {
      syncIntervalRef.current = setInterval(() => {
        if (pendingDiffs.length > 0) {
          forceSync();
        }
      }, autoSyncInterval);

      return () => {
        if (syncIntervalRef.current) {
          clearInterval(syncIntervalRef.current);
        }
      };
    }
  }, [autoSyncInterval, pendingDiffs.length, forceSync]);

  // Load from localStorage on mount (offline support)
  useEffect(() => {
    if (offlineSupport) {
      try {
        const saved = localStorage.getItem(`ag-ui-state-${sessionId}`);
        if (saved) {
          const { state: savedState, pendingDiffs: savedDiffs, version: savedVersion } =
            JSON.parse(saved);
          setState(savedState);
          setPendingDiffs(savedDiffs);
          setVersion(savedVersion);
        }
      } catch {
        // Ignore localStorage errors
      }
    }
  }, [sessionId, offlineSupport]);

  return {
    state,
    sharedState,
    syncStatus,
    get,
    set,
    remove,
    applyDiffs,
    forceSync,
    clearState,
    resolveConflict,
    isConnected,
  };
}

export default useSharedState;
