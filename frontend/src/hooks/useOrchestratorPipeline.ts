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
import { useAuthStore } from '@/store/authStore';

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
  originalTask: string | null;
  originalUserId: string | null;
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
  originalTask: null,
  originalUserId: null,
  error: null,
  totalMs: 0,
};

// --- Hook ---

export function useOrchestratorPipeline() {
  const [state, setState] = useState<PipelineState>({ ...INITIAL_STATE, steps: INITIAL_STEPS.map(s => ({ ...s })) });
  const abortRef = useRef<AbortController | null>(null);
  const token = useAuthStore((s) => s.token);

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
        // Only finalize on the truly final event (after dispatch)
        if (data.final) {
          updateStep('dispatch', { status: 'completed' });
          updateStep('post_process', { status: 'completed' });
          setState(prev => ({
            ...prev,
            isRunning: false,
            totalMs: data.total_ms as number,
          }));
        }
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

  const sendMessage = useCallback(async (task: string, userId: string = 'default-user', options?: { hitl_pre_approved?: boolean }) => {
    // Reset state
    const newSessionId = `pipeline-${Date.now()}`;
    setState({
      ...INITIAL_STATE,
      steps: INITIAL_STEPS.map(s => ({ ...s })),
      isRunning: true,
      sessionId: newSessionId,
      originalTask: task,
      originalUserId: userId,
    });

    abortRef.current = new AbortController();

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('/api/v1/orchestration/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({ task, user_id: userId, hitl_pre_approved: options?.hitl_pre_approved || false }),
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
  }, [handleSSEEvent, token]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState(prev => ({ ...prev, isRunning: false }));
  }, []);

  const _authHeaders = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  }, [token]);

  const resumeApproval = useCallback(async (status: 'approved' | 'rejected', approver: string = 'user') => {
    if (!state.hitlPause) return;

    if (status === 'rejected') {
      setState(prev => ({
        ...prev,
        hitlPause: null,
        isRunning: false,
        error: 'Operation rejected by approver',
      }));
      return;
    }

    const checkpointId = state.hitlPause.checkpointId;
    const task = state.originalTask;
    console.log('[resumeApproval] checkpoint:', checkpointId, 'task:', task?.substring(0, 30));

    // Clear HITL pause, mark Steps 1-5 as "restored"
    setState(prev => ({
      ...prev,
      hitlPause: null,
      isRunning: true,
    }));

    // True resume via checkpoint_id (skips Steps 1-5, restores context from Redis)
    if (checkpointId && task) {
      try {
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch('/api/v1/orchestration/chat', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            task,
            user_id: state.originalUserId || 'default-user',
            checkpoint_id: checkpointId,
          }),
          signal: abortRef.current?.signal,
        });

        if (!response.ok) throw new Error(`Resume failed: ${response.status}`);

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

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
          console.error('[resumeApproval] checkpoint resume failed:', err);
          setState(prev => ({ ...prev, isRunning: false, error: (err as Error).message }));
        }
      }
    } else if (task) {
      // Fallback: re-run with hitl_pre_approved (backward compatible)
      console.log('[resumeApproval] fallback: re-run with hitl_pre_approved');
      await sendMessage(task, state.originalUserId || 'default-user', { hitl_pre_approved: true });
    }
  }, [state.hitlPause, state.originalTask, state.originalUserId, token, handleSSEEvent, sendMessage]);

  const respondDialog = useCallback(async (responses: Record<string, string>) => {
    if (!state.dialogPause) return;

    // Build enriched task: original task + user's supplementary answers
    const originalTask = state.steps[0]?.metadata?.step === 'memory_read'
      ? '' : '';  // We need the original task
    const supplement = Object.entries(responses)
      .map(([field, value]) => `${field}: ${value}`)
      .join(', ');

    setState(prev => ({ ...prev, dialogPause: null }));

    // Re-run pipeline with enriched task (original task stored in sessionStorage)
    const storedTask = sessionStorage.getItem(`pipeline-task-${state.sessionId}`) || '';
    const enrichedTask = storedTask
      ? `${storedTask}\n\nAdditional info: ${supplement}`
      : supplement;

    // Re-trigger the full pipeline with enriched context
    await sendMessage(enrichedTask);
  }, [state.dialogPause, state.sessionId, state.steps, sendMessage]);

  return {
    ...state,
    sendMessage,
    cancel,
    resumeApproval,
    respondDialog,
  };
}
