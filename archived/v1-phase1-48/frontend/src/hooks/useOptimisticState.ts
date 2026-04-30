/**
 * useOptimisticState - Optimistic State Hook
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-3: Predictive State Updates
 *
 * React hook for managing optimistic/predictive state updates.
 * Supports immediate UI updates with server confirmation/rollback.
 */

import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import type {
  PredictionResult,
  PredictionStatus,
  PredictionConfig,
  OptimisticUpdateRequest,
  DiffOperation,
} from '@/types/ag-ui';

/** Hook configuration options */
export interface UseOptimisticStateOptions<T = Record<string, unknown>> {
  /** Initial state */
  initialState: T;
  /** Prediction configuration */
  config?: Partial<PredictionConfig>;
  /** API endpoint for confirmation */
  apiUrl?: string;
  /** Callback when prediction is confirmed */
  onConfirm?: (prediction: PredictionResult) => void;
  /** Callback when prediction is rolled back */
  onRollback?: (prediction: PredictionResult) => void;
  /** Callback when conflict occurs */
  onConflict?: (prediction: PredictionResult) => void;
}

/** Hook return value */
export interface UseOptimisticStateReturn<T = Record<string, unknown>> {
  /** Current confirmed state */
  currentState: T;
  /** Optimistic state (includes pending predictions) */
  optimisticState: T;
  /** Whether current display is optimistic */
  isOptimistic: boolean;
  /** All pending predictions */
  predictions: PredictionResult[];
  /** Apply optimistic update */
  optimisticUpdate: (request: OptimisticUpdateRequest) => string;
  /** Confirm a prediction */
  confirmPrediction: (predictionId: string, serverState?: Partial<T>) => void;
  /** Rollback a prediction */
  rollbackPrediction: (predictionId: string, reason?: string) => void;
  /** Rollback all pending predictions */
  rollbackAll: () => void;
  /** Get prediction by ID */
  getPrediction: (predictionId: string) => PredictionResult | undefined;
}

/** Generate unique prediction ID */
const generatePredictionId = (): string => {
  return `pred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Get nested value from object by path
 */
const getByPath = <T>(obj: T, path: string): unknown => {
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
const setByPath = <T extends Record<string, unknown>>(
  obj: T,
  path: string,
  value: unknown
): T => {
  const keys = path.split('.');
  const result = { ...obj } as Record<string, unknown>;

  let current = result;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    current[key] = { ...(current[key] as Record<string, unknown> || {}) };
    current = current[key] as Record<string, unknown>;
  }

  current[keys[keys.length - 1]] = value;
  return result as T;
};

/**
 * Delete nested value from object by path (immutable)
 */
const deleteByPath = <T extends Record<string, unknown>>(
  obj: T,
  path: string
): T => {
  const keys = path.split('.');
  const result = { ...obj } as Record<string, unknown>;

  if (keys.length === 1) {
    delete result[keys[0]];
    return result as T;
  }

  let current = result;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    current[key] = { ...(current[key] as Record<string, unknown> || {}) };
    current = current[key] as Record<string, unknown>;
  }

  delete current[keys[keys.length - 1]];
  return result as T;
};

/**
 * Apply operation to state
 */
const applyOperation = <T extends Record<string, unknown>>(
  state: T,
  path: string,
  operation: DiffOperation,
  value: unknown
): T => {
  switch (operation) {
    case 'add':
    case 'replace':
      return setByPath(state, path, value);
    case 'remove':
      return deleteByPath(state, path);
    case 'move':
      // Move requires source and target paths
      if (typeof value === 'object' && value !== null) {
        const { from, to } = value as { from: string; to: string };
        const moveValue = getByPath(state, from);
        const withoutSource = deleteByPath(state, from);
        return setByPath(withoutSource, to, moveValue);
      }
      return state;
    default:
      return state;
  }
};

/**
 * Default prediction configuration
 */
const DEFAULT_CONFIG: PredictionConfig = {
  enabled: true,
  defaultTimeout: 5000,
  maxPendingPredictions: 10,
  autoRollbackOnConflict: true,
  confidenceThreshold: 0.8,
};

/**
 * useOptimisticState - Main hook implementation
 */
export function useOptimisticState<T extends Record<string, unknown> = Record<string, unknown>>(
  options: UseOptimisticStateOptions<T>
): UseOptimisticStateReturn<T> {
  const {
    initialState,
    config: userConfig,
    apiUrl,
    onConfirm,
    onRollback,
    onConflict,
  } = options;

  // Merge config with defaults
  const config = useMemo<PredictionConfig>(
    () => ({ ...DEFAULT_CONFIG, ...userConfig }),
    [userConfig]
  );

  // State management
  const [currentState, setCurrentState] = useState<T>(initialState);
  const [predictions, setPredictions] = useState<PredictionResult[]>([]);

  // Timeout refs for auto-expiry
  const timeoutRefs = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Calculate optimistic state from current + pending predictions
  const optimisticState = useMemo<T>(() => {
    const pending = predictions.filter((p) => p.status === 'pending');
    if (pending.length === 0) return currentState;

    return pending.reduce(
      (state, prediction) => {
        // Apply predicted state changes
        return { ...state, ...prediction.predictedState } as T;
      },
      currentState
    );
  }, [currentState, predictions]);

  // Check if currently showing optimistic state
  const isOptimistic = useMemo(() => {
    return predictions.some((p) => p.status === 'pending');
  }, [predictions]);

  // Get prediction by ID
  const getPrediction = useCallback(
    (predictionId: string): PredictionResult | undefined => {
      return predictions.find((p) => p.predictionId === predictionId);
    },
    [predictions]
  );

  // Apply optimistic update
  const optimisticUpdate = useCallback(
    (request: OptimisticUpdateRequest): string => {
      if (!config.enabled) {
        // If predictions disabled, apply directly to current state
        setCurrentState((prev) =>
          applyOperation(prev, request.path, request.operation, request.value)
        );
        return '';
      }

      // Check max pending predictions
      const pendingCount = predictions.filter((p) => p.status === 'pending').length;
      if (pendingCount >= config.maxPendingPredictions) {
        console.warn('Max pending predictions reached, applying directly');
        setCurrentState((prev) =>
          applyOperation(prev, request.path, request.operation, request.value)
        );
        return '';
      }

      // Create prediction
      const predictionId = generatePredictionId();
      const timeout = request.timeout || config.defaultTimeout;
      const expiresAt = new Date(Date.now() + timeout).toISOString();

      // Calculate predicted state
      const predictedState = applyOperation(
        currentState,
        request.path,
        request.operation,
        request.value
      );

      const prediction: PredictionResult = {
        predictionId,
        predictionType: request.predictionType || 'optimistic',
        status: 'pending',
        predictedState: predictedState as Record<string, unknown>,
        originalState: currentState as Record<string, unknown>,
        confidence: config.confidenceThreshold,
        expiresAt,
      };

      // Add to predictions
      setPredictions((prev) => [...prev, prediction]);

      // Set expiry timeout
      const timeoutId = setTimeout(() => {
        setPredictions((prev) =>
          prev.map((p) =>
            p.predictionId === predictionId
              ? { ...p, status: 'expired' as PredictionStatus }
              : p
          )
        );
        timeoutRefs.current.delete(predictionId);
      }, timeout);

      timeoutRefs.current.set(predictionId, timeoutId);

      // Optionally send to server for confirmation
      if (apiUrl) {
        fetch(`${apiUrl}/predictions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ predictionId, request }),
        }).catch((error) => {
          console.error('Failed to send prediction to server:', error);
        });
      }

      return predictionId;
    },
    [config, currentState, predictions, apiUrl]
  );

  // Confirm a prediction
  const confirmPrediction = useCallback(
    (predictionId: string, serverState?: Partial<T>) => {
      const prediction = predictions.find((p) => p.predictionId === predictionId);
      if (!prediction) return;

      // Clear timeout
      const timeoutId = timeoutRefs.current.get(predictionId);
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutRefs.current.delete(predictionId);
      }

      // Update prediction status
      const confirmedPrediction: PredictionResult = {
        ...prediction,
        status: 'confirmed',
        confirmedAt: new Date().toISOString(),
      };

      setPredictions((prev) =>
        prev.map((p) => (p.predictionId === predictionId ? confirmedPrediction : p))
      );

      // Apply to current state
      const newState = serverState
        ? { ...currentState, ...serverState }
        : (prediction.predictedState as T);

      setCurrentState(newState);

      // Notify callback
      onConfirm?.(confirmedPrediction);

      // Clean up old confirmed predictions after delay
      setTimeout(() => {
        setPredictions((prev) => prev.filter((p) => p.predictionId !== predictionId));
      }, 2000);
    },
    [predictions, currentState, onConfirm]
  );

  // Rollback a prediction
  const rollbackPrediction = useCallback(
    (predictionId: string, reason?: string) => {
      const prediction = predictions.find((p) => p.predictionId === predictionId);
      if (!prediction) return;

      // Clear timeout
      const timeoutId = timeoutRefs.current.get(predictionId);
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutRefs.current.delete(predictionId);
      }

      // Update prediction status
      const rolledBackPrediction: PredictionResult = {
        ...prediction,
        status: reason ? 'conflicted' : 'rolled_back',
        rolledBackAt: new Date().toISOString(),
        conflictReason: reason,
      };

      setPredictions((prev) =>
        prev.map((p) => (p.predictionId === predictionId ? rolledBackPrediction : p))
      );

      // Notify callbacks
      if (reason) {
        onConflict?.(rolledBackPrediction);
      } else {
        onRollback?.(rolledBackPrediction);
      }

      // Clean up after delay
      setTimeout(() => {
        setPredictions((prev) => prev.filter((p) => p.predictionId !== predictionId));
      }, 3000);
    },
    [predictions, onRollback, onConflict]
  );

  // Rollback all pending predictions
  const rollbackAll = useCallback(() => {
    const pending = predictions.filter((p) => p.status === 'pending');
    pending.forEach((p) => rollbackPrediction(p.predictionId));
  }, [predictions, rollbackPrediction]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      timeoutRefs.current.forEach((timeout) => clearTimeout(timeout));
      timeoutRefs.current.clear();
    };
  }, []);

  return {
    currentState,
    optimisticState,
    isOptimistic,
    predictions,
    optimisticUpdate,
    confirmPrediction,
    rollbackPrediction,
    rollbackAll,
    getPrediction,
  };
}

export default useOptimisticState;
