/**
 * useOrchestratorPipeline — SSE hook for the 8-step orchestration pipeline.
 *
 * Consumes POST /api/v1/orchestration/chat SSE stream and manages:
 * - Pipeline step progression (8 steps)
 * - Dialog pause/resume (DIALOG_REQUIRED)
 * - HITL pause/resume (HITL_REQUIRED)
 * - Dispatch events (AGENT_THINKING, TEXT_DELTA, etc.)
 * - Error handling
 *
 * Phase 45: Orchestration Core (Sprint 157)
 */

import { useState, useCallback, useRef } from 'react';
import { apiClient } from '@/api/client';

// --- Types ---

export type PipelineStepStatus = 'pending' | 'running' | 'completed' | 'paused' | 'error';

export interface StepMetadata {
  [key: string]: unknown;
}

export interface PipelineStep {
  index: number;
  name: string;
  label: string;
  status: PipelineStepStatus;
  latencyMs?: number;
  metadata?: StepMetadata;
}

export interface DialogPause {
  dialogId: string;
  questions: string[];
  missingFields: string[];
  checkpointId: string;
  completenessScore: number;
}

export interface HITLPause {
  approvalId: string;
  checkpointId: string;
  riskLevel: string;
  approvalType: string;
}

export interface AgentProgress {
  agentName: string;
  status: 'thinking' | 'tool_call' | 'completed';
  output?: string;
  durationMs?: number;
}

export interface PipelineState {
  isRunning: boolean;
  sessionId: string | null;
  steps: PipelineStep[];
  currentStepIndex: number;
  selectedRoute: string | null;
  routeReasoning: string | null;
  responseText: string;
  agents: AgentProgress[];
  dialogPause: DialogPause | null;
  hitlPause: HITLPause | null;
  error: string | null;
  totalMs: number;
}

const INITIAL_STEPS: PipelineStep[] = [
  { index: 0, name: 'memory_read', label: '記憶讀取', status: 'pending' },
  { index: 1, name: 'knowledge_search', label: '知識搜索', status: 'pending' },
  { index: 2, name: 'intent_analysis', label: '意圖分析', status: 'pending' },
  { index: 3, name: 'risk_assessment', label: '風險評估', status: 'pending' },
  { index: 4, name: 'hitl_gate', label: 'HITL 審批', status: 'pending' },
  { index: 5, name: 'llm_route_decision', label: 'LLM 選路', status: 'pending' },
  { index: 6, name: 'dispatch', label: '分派執行', status: 'pending' },
  { index: 7, name: 'post_process', label: '後處理', status: 'pending' },
];

const INITIAL_STATE: PipelineState = {
  isRunning: false,
  sessionId: null,
  steps: INITIAL_STEPS.map(s => ({ ...s })),
  currentStepIndex: -1,
  selectedRoute: null,
  routeReasoning: null,
  responseText: '',
  agents: [],
  dialogPause: null,
  hitlPause: null,
  error: null,
  totalMs: 0,
};

// --- Hook ---

export function useOrchestratorPipeline() {
  const [state, setState] = useState<PipelineState>({ ...INITIAL_STATE, steps: INITIAL_STEPS.map(s => ({ ...s })) });
  const abortRef = useRef<AbortController | null>(null);

  const updateStep = useCallback((stepName: string, updates: Partial<PipelineStep>) => {
    setState(prev => ({
      ...prev,
      steps: prev.steps.map(s =>
        s.name === stepName ? { ...s, ...updates } : s
      ),
    }));
  }, []);

  const handleSSEEvent = useCallback((eventType: string, data: Record<string, unknown>) => {
    switch (eventType) {
      case 'PIPELINE_START':
        setState(prev => ({
          ...prev,
          isRunning: true,
          sessionId: data.session_id as string,
          error: null,
          dialogPause: null,
          hitlPause: null,
        }));
        break;

      case 'STEP_START':
        updateStep(data.step_name as string, { status: 'running' });
        setState(prev => ({ ...prev, currentStepIndex: data.step_index as number }));
        break;

      case 'STEP_COMPLETE':
        updateStep(data.step_name as string, {
          status: 'completed',
          latencyMs: data.latency_ms as number,
          metadata: (data.metadata ?? data) as StepMetadata,
        });
        break;

      case 'STEP_ERROR':
        updateStep(data.step_name as string, { status: 'error', metadata: data as StepMetadata });
        break;

      case 'LLM_ROUTE_DECISION':
        setState(prev => ({
          ...prev,
          selectedRoute: data.route as string,
          routeReasoning: (data.reasoning as string) || null,
        }));
        updateStep('llm_route_decision', {
          metadata: { route: data.route, reasoning: data.reasoning } as StepMetadata,
        });
        break;

      case 'DISPATCH_START':
        updateStep('dispatch', { status: 'running' });
        break;

      case 'AGENT_THINKING':
        setState(prev => ({
          ...prev,
          agents: [
            ...prev.agents.filter(a => a.agentName !== (data.agent_name as string)),
            {
              agentName: data.agent_name as string,
              status: 'thinking',
            },
          ],
        }));
        break;

      case 'AGENT_TOOL_CALL':
        setState(prev => ({
          ...prev,
          agents: prev.agents.map(a =>
            a.agentName === (data.agent_name as string)
              ? { ...a, status: 'tool_call' as const }
              : a
          ),
        }));
        break;

      case 'AGENT_COMPLETE':
        setState(prev => ({
          ...prev,
          agents: prev.agents.map(a =>
            a.agentName === (data.agent_name as string)
              ? {
                  ...a,
                  status: 'completed' as const,
                  output: data.output_preview as string,
                  durationMs: data.duration_ms as number,
                }
              : a
          ),
        }));
        break;

      case 'TEXT_DELTA':
        setState(prev => ({
          ...prev,
          responseText: prev.responseText + (data.content as string),
        }));
        break;

      case 'DIALOG_REQUIRED':
        updateStep('intent_analysis', { status: 'paused' });
        setState(prev => ({
          ...prev,
          isRunning: false,
          dialogPause: {
            dialogId: data.dialog_id as string,
            questions: data.questions as string[],
            missingFields: data.missing_fields as string[],
            checkpointId: data.checkpoint_id as string,
            completenessScore: data.completeness_score as number,
          },
        }));
        break;

      case 'HITL_REQUIRED':
        updateStep('hitl_gate', { status: 'paused' });
        setState(prev => ({
          ...prev,
          isRunning: false,
          hitlPause: {
            approvalId: data.approval_id as string,
            checkpointId: data.checkpoint_id as string,
            riskLevel: data.risk_level as string,
            approvalType: data.approval_type as string,
          },
        }));
        break;

      case 'PIPELINE_COMPLETE':
        updateStep('dispatch', { status: 'completed' });
        updateStep('post_process', { status: 'completed' });
        setState(prev => ({
          ...prev,
          isRunning: false,
          totalMs: data.total_ms as number,
        }));
        break;

      case 'PIPELINE_ERROR':
        setState(prev => ({
          ...prev,
          isRunning: false,
          error: data.error as string,
        }));
        break;
    }
  }, [updateStep]);

  const sendMessage = useCallback(async (task: string, userId: string = 'default-user') => {
    // Reset state
    setState({
      ...INITIAL_STATE,
      steps: INITIAL_STEPS.map(s => ({ ...s })),
      isRunning: true,
    });

    abortRef.current = new AbortController();

    try {
      const response = await fetch('/api/v1/orchestration/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, user_id: userId }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Pipeline request failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              handleSSEEvent(currentEvent, data);
            } catch {
              // skip malformed JSON
            }
            currentEvent = '';
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setState(prev => ({
          ...prev,
          isRunning: false,
          error: (err as Error).message,
        }));
      }
    }
  }, [handleSSEEvent]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState(prev => ({ ...prev, isRunning: false }));
  }, []);

  const resumeApproval = useCallback(async (status: 'approved' | 'rejected', approver: string = 'user') => {
    if (!state.hitlPause) return;

    try {
      await fetch('/api/v1/orchestration/chat/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          checkpoint_id: state.hitlPause.checkpointId,
          user_id: 'default-user',
          approval_status: status,
          approval_approver: approver,
        }),
      });
      setState(prev => ({ ...prev, hitlPause: null }));
    } catch (err) {
      setState(prev => ({ ...prev, error: (err as Error).message }));
    }
  }, [state.hitlPause]);

  const respondDialog = useCallback(async (responses: Record<string, string>) => {
    if (!state.dialogPause) return;

    try {
      await fetch('/api/v1/orchestration/chat/dialog-respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          checkpoint_id: state.dialogPause.checkpointId,
          user_id: 'default-user',
          dialog_id: state.dialogPause.dialogId,
          responses,
        }),
      });
      setState(prev => ({ ...prev, dialogPause: null }));
    } catch (err) {
      setState(prev => ({ ...prev, error: (err as Error).message }));
    }
  }, [state.dialogPause]);

  return {
    ...state,
    sendMessage,
    cancel,
    resumeApproval,
    respondDialog,
  };
}
