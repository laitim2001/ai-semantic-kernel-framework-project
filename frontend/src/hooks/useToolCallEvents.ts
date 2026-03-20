/**
 * useToolCallEvents - Tool Call Event Management Hook
 *
 * Phase 41 Sprint 142: S142-2 - ToolCallTracker Integration
 *
 * Manages tool call state from pipeline responses and SSE events.
 * Converts pipeline tool call data to TrackedToolCall format
 * for display in the ToolCallTracker component.
 */

import { useState, useCallback } from 'react';
import type { TrackedToolCall } from '@/types/unified-chat';
import type { PipelineToolCall } from '@/types/ag-ui';

interface UseToolCallEventsReturn {
  /** Current list of tracked tool calls */
  toolCalls: TrackedToolCall[];
  /** Add tool calls from a pipeline response */
  addFromPipeline: (pipelineToolCalls: PipelineToolCall[]) => void;
  /** Update a specific tool call's status */
  updateToolCall: (id: string, updates: Partial<TrackedToolCall>) => void;
  /** Clear all tracked tool calls */
  clear: () => void;
}

/**
 * Maps pipeline tool call status to ToolCallStatus.
 */
function mapStatus(status: PipelineToolCall['status']): TrackedToolCall['status'] {
  switch (status) {
    case 'running': return 'executing';
    case 'completed': return 'completed';
    case 'failed': return 'failed';
    case 'pending': return 'pending';
    default: return 'pending';
  }
}

/**
 * Hook to manage tool call events from the pipeline.
 */
export function useToolCallEvents(): UseToolCallEventsReturn {
  const [toolCalls, setToolCalls] = useState<TrackedToolCall[]>([]);

  const addFromPipeline = useCallback((pipelineToolCalls: PipelineToolCall[]) => {
    const mapped: TrackedToolCall[] = pipelineToolCalls.map((tc) => ({
      id: tc.id,
      toolCallId: tc.id,
      name: tc.toolName,
      arguments: tc.args ? { raw: tc.args } : {},
      status: mapStatus(tc.status),
      result: tc.result,
      duration: tc.durationMs,
      startedAt: new Date().toISOString(),
    }));
    setToolCalls((prev) => [...prev, ...mapped]);
  }, []);

  const updateToolCall = useCallback((id: string, updates: Partial<TrackedToolCall>) => {
    setToolCalls((prev) =>
      prev.map((tc) => (tc.id === id ? { ...tc, ...updates } : tc))
    );
  }, []);

  const clear = useCallback(() => {
    setToolCalls([]);
  }, []);

  return { toolCalls, addFromPipeline, updateToolCall, clear };
}

export default useToolCallEvents;
