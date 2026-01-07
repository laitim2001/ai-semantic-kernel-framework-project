/**
 * useHybridMode - Hybrid Mode Management Hook
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-2: Adaptive Layout Logic
 * Sprint 63: Mode Switching & State Management
 * S63-3: Real Mode Detection (Enhanced)
 * Phase 16: Unified Agentic Chat Interface
 *
 * Manages automatic mode detection and manual override for
 * Chat/Workflow mode switching in the unified interface.
 *
 * Enhanced in S63-3:
 * - Added switchReason for displaying why mode was switched
 * - Added switchConfidence for detection confidence level
 * - Added lastSwitchAt timestamp
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { ExecutionMode } from '@/types/unified-chat';

/** Mode detection event from AG-UI backend */
export interface ModeDetectionEvent {
  type: 'MODE_DETECTED';
  mode: ExecutionMode;
  confidence: number;
  reason?: string;
  timestamp: string;
}

/** Configuration for useHybridMode hook */
export interface UseHybridModeConfig {
  /** Initial mode (default: 'chat') */
  initialMode?: ExecutionMode;
  /** Enable auto-detection from AG-UI events (default: true) */
  enableAutoDetection?: boolean;
  /** Session ID for persisting manual override */
  sessionId?: string;
  /** Callback when mode changes */
  onModeChange?: (mode: ExecutionMode, source: 'auto' | 'manual') => void;
  /** Callback when auto mode is detected */
  onAutoModeDetected?: (mode: ExecutionMode, confidence: number) => void;
}

/** Return type for useHybridMode hook (S63-3 Enhanced) */
export interface UseHybridModeReturn {
  /** Current effective mode ('chat' or 'workflow') */
  currentMode: ExecutionMode;
  /** Auto-detected mode from IntentRouter */
  autoMode: ExecutionMode;
  /** User's manual override (null if using auto mode) */
  manualOverride: ExecutionMode | null;
  /** Whether mode is manually overridden */
  isManuallyOverridden: boolean;
  /** Set or clear manual override */
  setManualOverride: (mode: ExecutionMode | null) => void;
  /** S63-3: Reason for the last mode switch */
  switchReason: string | null;
  /** S63-3: Confidence level of the last auto-detection (0-1) */
  switchConfidence: number;
  /** S63-3: ISO timestamp of the last mode switch */
  lastSwitchAt: string | null;
}

// Session storage key for persisting manual override
const STORAGE_KEY_PREFIX = 'ipa_hybrid_mode_override_';

/**
 * useHybridMode Hook
 *
 * Provides hybrid mode management with:
 * - Auto-detection based on AG-UI events and IntentRouter results
 * - Manual override capability
 * - Session persistence for manual override preference
 * - Mode change callbacks for tracking
 *
 * @param config - Hook configuration options
 * @returns Mode state and control functions
 *
 * @example
 * ```tsx
 * const {
 *   currentMode,      // 'chat' or 'workflow' - effective mode to use
 *   autoMode,         // Auto-detected mode from backend
 *   manualOverride,   // User's manual override (or null)
 *   isManuallyOverridden,
 *   setManualOverride,
 * } = useHybridMode({
 *   onModeChange: (mode, source) => console.log(`Mode: ${mode} (${source})`)
 * });
 * ```
 */
export function useHybridMode(config: UseHybridModeConfig = {}): UseHybridModeReturn {
  const {
    initialMode = 'chat',
    enableAutoDetection = true,
    sessionId,
    onModeChange,
    onAutoModeDetected,
  } = config;

  // Load persisted manual override from session storage
  const loadPersistedOverride = useCallback((): ExecutionMode | null => {
    if (!sessionId) return null;
    try {
      const stored = sessionStorage.getItem(`${STORAGE_KEY_PREFIX}${sessionId}`);
      if (stored === 'chat' || stored === 'workflow') {
        return stored;
      }
    } catch {
      // Session storage not available
    }
    return null;
  }, [sessionId]);

  // State
  const [autoMode, setAutoMode] = useState<ExecutionMode>(initialMode);
  const [manualOverride, setManualOverrideState] = useState<ExecutionMode | null>(
    loadPersistedOverride
  );

  // S63-3: Switch tracking state
  const [switchReason, setSwitchReason] = useState<string | null>(null);
  const [switchConfidence, setSwitchConfidence] = useState<number>(0);
  const [lastSwitchAt, setLastSwitchAt] = useState<string | null>(null);

  // Ref to track previous mode for change detection
  const prevModeRef = useRef<ExecutionMode | null>(null);

  // Computed values
  const isManuallyOverridden = manualOverride !== null;
  const currentMode = manualOverride ?? autoMode;

  // Persist manual override to session storage
  const persistManualOverride = useCallback(
    (mode: ExecutionMode | null) => {
      if (!sessionId) return;
      try {
        if (mode) {
          sessionStorage.setItem(`${STORAGE_KEY_PREFIX}${sessionId}`, mode);
        } else {
          sessionStorage.removeItem(`${STORAGE_KEY_PREFIX}${sessionId}`);
        }
      } catch {
        // Session storage not available
      }
    },
    [sessionId]
  );

  // Set manual override
  const setManualOverride = useCallback(
    (mode: ExecutionMode | null) => {
      setManualOverrideState(mode);
      persistManualOverride(mode);

      // S63-3: Track manual switch metadata
      if (mode !== manualOverride) {
        const newCurrentMode = mode ?? autoMode;
        if (mode) {
          setSwitchReason(`Manually switched to ${mode} mode`);
          setSwitchConfidence(1.0); // Manual override = 100% confidence
        } else {
          setSwitchReason('Returned to auto-detected mode');
          // Keep existing confidence from auto-detection
        }
        setLastSwitchAt(new Date().toISOString());

        // Trigger callback
        onModeChange?.(newCurrentMode, mode ? 'manual' : 'auto');
      }
    },
    [autoMode, manualOverride, persistManualOverride, onModeChange]
  );

  // Handle auto mode detection from AG-UI events
  const handleModeDetection = useCallback(
    (event: ModeDetectionEvent) => {
      if (!enableAutoDetection) return;

      const { mode, confidence, reason, timestamp } = event;

      // Only update if confidence is high enough (> 0.7)
      if (confidence >= 0.7) {
        setAutoMode(mode);
        onAutoModeDetected?.(mode, confidence);

        // S63-3: Track switch metadata
        setSwitchReason(reason ?? `Auto-detected ${mode} mode`);
        setSwitchConfidence(confidence);
        setLastSwitchAt(timestamp);

        // If no manual override, trigger mode change callback
        if (!manualOverride) {
          onModeChange?.(mode, 'auto');
        }
      }
    },
    [enableAutoDetection, manualOverride, onModeChange, onAutoModeDetected]
  );

  // Track mode changes
  useEffect(() => {
    if (prevModeRef.current !== null && prevModeRef.current !== currentMode) {
      // Mode has changed
      onModeChange?.(currentMode, isManuallyOverridden ? 'manual' : 'auto');
    }
    prevModeRef.current = currentMode;
  }, [currentMode, isManuallyOverridden, onModeChange]);

  // Listen for AG-UI mode detection events (SSE)
  // This will be integrated with useAGUI hook in S62-3
  useEffect(() => {
    if (!enableAutoDetection) return;

    // For now, we expose handleModeDetection via a custom event
    // that can be triggered by parent components or AG-UI integration
    // Note: SSE integration will be added when ChatArea connects to useAGUI
    const handleCustomEvent = (e: CustomEvent<ModeDetectionEvent>) => {
      handleModeDetection(e.detail);
    };

    window.addEventListener(
      'ipa-mode-detection' as keyof WindowEventMap,
      handleCustomEvent as EventListener
    );

    return () => {
      window.removeEventListener(
        'ipa-mode-detection' as keyof WindowEventMap,
        handleCustomEvent as EventListener
      );
    };
  }, [enableAutoDetection, handleModeDetection]);

  return {
    currentMode,
    autoMode,
    manualOverride,
    isManuallyOverridden,
    setManualOverride,
    // S63-3: Switch tracking
    switchReason,
    switchConfidence,
    lastSwitchAt,
  };
}

/**
 * Dispatch a mode detection event
 *
 * Utility function to trigger mode detection from anywhere in the app.
 * Used primarily for testing and integration with AG-UI backend.
 *
 * @param event - Mode detection event data
 */
export function dispatchModeDetection(event: Omit<ModeDetectionEvent, 'type' | 'timestamp'>) {
  const fullEvent: ModeDetectionEvent = {
    type: 'MODE_DETECTED',
    timestamp: new Date().toISOString(),
    ...event,
  };

  window.dispatchEvent(
    new CustomEvent('ipa-mode-detection', { detail: fullEvent })
  );
}

export default useHybridMode;
