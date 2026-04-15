/**
 * useOrchestratorHistory — Load historical pipeline execution data from API.
 *
 * Completely separate from useOrchestratorPipeline (live SSE state).
 * OrchestrationPanel can consume both hooks and switch between
 * live (SSE) and historical (API) display modes.
 *
 * Sprint 169 — Phase 47: Pipeline execution persistence.
 */

import { useState, useEffect, useCallback } from 'react';
import orchestrationApi, {
  ExecutionLogDetail,
} from '@/api/endpoints/orchestration';

interface UseOrchestratorHistoryResult {
  historicalExecution: ExecutionLogDetail | null;
  isLoadingHistory: boolean;
  historyError: string | null;
  refetchHistory: () => void;
}

export function useOrchestratorHistory(
  sessionId: string | null
): UseOrchestratorHistoryResult {
  const [historicalExecution, setHistoricalExecution] =
    useState<ExecutionLogDetail | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!sessionId) {
      setHistoricalExecution(null);
      return;
    }

    setIsLoadingHistory(true);
    setHistoryError(null);

    try {
      const resp =
        await orchestrationApi.getLatestExecutionForSession(sessionId);
      setHistoricalExecution(resp.data);
    } catch (err: unknown) {
      // 404 is expected when no execution exists for this session yet
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setHistoricalExecution(null);
      } else {
        setHistoryError(
          err instanceof Error ? err.message : 'Failed to load history'
        );
      }
    } finally {
      setIsLoadingHistory(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    historicalExecution,
    isLoadingHistory,
    historyError,
    refetchHistory: fetchHistory,
  };
}
