// =============================================================================
// IPA Platform - Node Drag Hook
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Manages node drag state and auto-save after drag ends.
// Debounces save calls to avoid excessive API requests.
// =============================================================================

import { useCallback, useRef, useState } from 'react';
import type { Node, OnNodeDrag } from '@xyflow/react';

interface UseNodeDragOptions {
  onSave?: (nodes: Node[]) => void;
  debounceMs?: number;
}

interface UseNodeDragResult {
  isDragging: boolean;
  hasUnsavedChanges: boolean;
  onNodeDragStart: OnNodeDrag;
  onNodeDragStop: OnNodeDrag;
  markSaved: () => void;
}

export function useNodeDrag(options: UseNodeDragOptions = {}): UseNodeDragResult {
  const { onSave, debounceMs = 1000 } = options;
  const [isDragging, setIsDragging] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestNodesRef = useRef<Node[]>([]);

  const scheduleSave = useCallback(
    (nodes: Node[]) => {
      if (!onSave) return;

      // Clear previous timer
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }

      latestNodesRef.current = nodes;
      setHasUnsavedChanges(true);

      saveTimerRef.current = setTimeout(() => {
        onSave(latestNodesRef.current);
        saveTimerRef.current = null;
      }, debounceMs);
    },
    [onSave, debounceMs]
  );

  const onNodeDragStart: OnNodeDrag = useCallback(() => {
    setIsDragging(true);
  }, []);

  const onNodeDragStop: OnNodeDrag = useCallback(
    (_event: React.MouseEvent, _node: Node, nodes: Node[]) => {
      setIsDragging(false);
      scheduleSave(nodes);
    },
    [scheduleSave]
  );

  const markSaved = useCallback(() => {
    setHasUnsavedChanges(false);
  }, []);

  return {
    isDragging,
    hasUnsavedChanges,
    onNodeDragStart,
    onNodeDragStop,
    markSaved,
  };
}
