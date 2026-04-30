/**
 * useOrchestratorHistory — Load historical pipeline execution data from API.
 *
 * Completely separate from useOrchestratorPipeline (live SSE state).
 * OrchestratorChat consumes both hooks and switches between
 * live (SSE) and historical (API) display modes via effectivePanelData.
 *
 * Sprint 169 — Phase 47: Pipeline execution persistence + UI integration.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import orchestrationApi, {
  ExecutionLogDetail,
} from '@/api/endpoints/orchestration';
import type { PipelineStep, AgentProgress } from './useOrchestratorPipeline';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HistoricalPanelData {
  steps: PipelineStep[];
  agents: AgentProgress[];
  selectedRoute: string | null;
  routeReasoning: string | null;
  totalMs: number;
  isHistorical: true;
}

interface UseOrchestratorHistoryResult {
  historicalExecution: ExecutionLogDetail | null;
  historicalPanelData: HistoricalPanelData | null;
  isLoadingHistory: boolean;
  historyError: string | null;
  refetchHistory: () => void;
}

// ---------------------------------------------------------------------------
// Step ordering & labels (must match INITIAL_STEPS in useOrchestratorPipeline)
// ---------------------------------------------------------------------------

const STEP_ORDER = [
  'memory_read',
  'knowledge_search',
  'intent_analysis',
  'risk_assessment',
  'hitl_gate',
  'llm_route_decision',
  'dispatch',
  'post_process',
] as const;

const STEP_LABELS: Record<string, string> = {
  memory_read: '記憶讀取',
  knowledge_search: '知識搜索',
  intent_analysis: '意圖分析',
  risk_assessment: '風險評估',
  hitl_gate: 'HITL 審批',
  llm_route_decision: 'LLM 選路',
  dispatch: '分派執行',
  post_process: '後處理',
};

// ---------------------------------------------------------------------------
// Transformer: ExecutionLogDetail → HistoricalPanelData
// ---------------------------------------------------------------------------

export function transformExecutionLogToPanel(
  log: ExecutionLogDetail
): HistoricalPanelData {
  const pipelineSteps = log.pipeline_steps || {};
  const rd = log.routing_decision as Record<string, unknown> | null;
  const ra = log.risk_assessment as Record<string, unknown> | null;
  const ci = log.completeness_info as Record<string, unknown> | null;

  const steps: PipelineStep[] = STEP_ORDER.map((name, index) => {
    const record = pipelineSteps[name];
    const status = record
      ? record.status === 'completed'
        ? 'completed'
        : record.status === 'error'
          ? 'error'
          : record.status === 'paused'
            ? 'paused'
            : 'completed'
      : 'pending';

    const latencyMs = record?.latency_ms ?? undefined;

    // Build step-specific metadata from the JSONB columns.
    // For memory_read / knowledge_search, the per-step metadata is stored
    // inline on the pipeline_steps record (see backend persistence.py).
    let metadata: Record<string, unknown> | undefined = (record as
      | { metadata?: Record<string, unknown> }
      | undefined)?.metadata;

    if (name === 'intent_analysis' && rd) {
      metadata = {
        intent: rd.intent_category,
        sub_intent: rd.sub_intent,
        confidence: rd.confidence,
        routing_layer: rd.routing_layer,
        ...(ci
          ? {
              is_complete: ci.is_complete,
              completeness_score: ci.completeness_score,
              missing_fields: ci.missing_fields,
            }
          : {}),
      };
    } else if (name === 'risk_assessment' && ra) {
      metadata = {
        level: ra.level,
        score: ra.score,
        requires_approval: ra.requires_approval,
        approval_type: ra.approval_type,
        reasoning: ra.reasoning,
        policy_id: ra.policy_id,
      };
    } else if (name === 'hitl_gate' && ra) {
      metadata = {
        approval_status: ra.requires_approval ? 'approved' : 'not_required',
      };
    } else if (name === 'llm_route_decision') {
      metadata = {
        selected_route: log.selected_route,
        reasoning: log.route_reasoning,
      };
    } else if (name === 'dispatch') {
      metadata = {
        route: log.selected_route,
      };
    } else if (name === 'post_process') {
      metadata = {
        memory_extraction: 'scheduled',
      };
    }

    return {
      index,
      name,
      label: STEP_LABELS[name] || name,
      status: status as PipelineStep['status'],
      latencyMs,
      ...(metadata ? { metadata } : {}),
    };
  });

  // Transform agent_events → AgentProgress[]
  const agents: AgentProgress[] = [];
  if (log.agent_events && Array.isArray(log.agent_events)) {
    for (const evt of log.agent_events) {
      const e = evt as Record<string, unknown>;
      agents.push({
        agentName: (e.agent_name as string) || 'unknown',
        status: 'completed',
        output: e.output as string | undefined,
        durationMs: e.duration_ms as number | undefined,
      });
    }
  }

  return {
    steps,
    agents,
    selectedRoute: log.selected_route,
    routeReasoning: log.route_reasoning,
    totalMs: log.total_ms || 0,
    isHistorical: true,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

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

  // Auto-transform when historicalExecution changes
  const historicalPanelData = useMemo(() => {
    if (!historicalExecution) return null;
    return transformExecutionLogToPanel(historicalExecution);
  }, [historicalExecution]);

  return {
    historicalExecution,
    historicalPanelData,
    isLoadingHistory,
    historyError,
    refetchHistory: fetchHistory,
  };
}
