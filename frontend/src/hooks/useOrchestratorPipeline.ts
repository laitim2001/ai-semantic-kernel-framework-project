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
import { useAgentTeamStore } from '@/stores/agentTeamStore';

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
      case 'PIPELINE_START': {
        const startFrom = (data.start_from as number) || 0;
        // Only reset agent team store on fresh runs, not checkpoint resume
        if (startFrom === 0) {
          useAgentTeamStore.getState().reset();
        }
        setState(prev => {
          // If resuming from checkpoint, mark skipped steps as 'completed (restored)'
          const updatedSteps = startFrom > 0
            ? prev.steps.map(s =>
                s.index < startFrom ? { ...s, status: 'completed' as const } : s
              )
            : prev.steps;
          return {
            ...prev,
            isRunning: true,
            sessionId: data.session_id as string,
            error: null,
            dialogPause: null,
            hitlPause: null,
            steps: updatedSteps,
          };
        });
        break;
      }

      case 'STEP_START':
        updateStep(data.step_name as string, { status: 'running' });
        setState(prev => ({ ...prev, currentStepIndex: data.step_index as number }));
        break;

      case 'STEP_COMPLETE': {
        const meta = (data.metadata ?? data) as StepMetadata;
        updateStep(data.step_name as string, {
          status: 'completed',
          latencyMs: data.latency_ms as number,
          metadata: meta,
        });
        // Extract selectedRoute from llm_route_decision step metadata (fallback for checkpoint resume)
        if (data.step_name === 'llm_route_decision' && meta.route) {
          setState(prev => ({
            ...prev,
            selectedRoute: prev.selectedRoute || (meta.route as string),
            routeReasoning: prev.routeReasoning || (meta.reasoning as string) || null,
          }));
        }
        break;
      }

      case 'STEP_ERROR':
        updateStep(data.step_name as string, { status: 'error', metadata: data as StepMetadata });
        break;

      case 'LLM_ROUTE_DECISION':
        setState(prev => ({
          ...prev,
          selectedRoute: data.route as string,
          routeReasoning: (data.reasoning as string) || null,
        }));
        // Store route type in agent team store for header display
        useAgentTeamStore.getState().setRouteType(data.route as string);
        updateStep('llm_route_decision', {
          metadata: { route: data.route, reasoning: data.reasoning } as StepMetadata,
        });
        break;

      case 'DISPATCH_START':
        updateStep('dispatch', { status: 'running' });
        break;

      case 'AGENT_THINKING': {
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
        // Safety net: auto-create team from backward-compat AGENT_THINKING events
        const atStore = useAgentTeamStore.getState();
        if (!atStore.agentTeamStatus) {
          atStore.setTeamStatus({
            teamId: 'auto',
            sessionId: '',
            mode: 'parallel',
            status: 'executing',
            totalAgents: 0,
            overallProgress: 0,
            agents: [],
            createdAt: new Date().toISOString(),
            metadata: {},
          });
        }
        // Add agent if not already in roster
        const agentName = data.agent_name as string;
        if (agentName && !atStore.agentTeamStatus?.agents.find(a => a.agentName === agentName)) {
          atStore.addAgent({
            agentId: agentName,
            agentName,
            agentType: 'hybrid',
            role: (data.role as string) || 'agent',
            status: 'running',
            progress: 0,
            toolCallsCount: 0,
            createdAt: new Date().toISOString(),
          });
        }
        break;
      }

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

      case 'AGENT_COMPLETE': {
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
        // Safety net: complete agent in team store from backward-compat events
        const acStore = useAgentTeamStore.getState();
        const acName = data.agent_name as string;
        if (acStore.agentTeamStatus) {
          const agentEntry = acStore.agentTeamStatus.agents.find(a => a.agentName === acName || a.agentId === acName);
          if (agentEntry) {
            acStore.completeAgent({
              team_id: acStore.agentTeamStatus.teamId,
              agent_id: agentEntry.agentId,
              status: 'completed',
              duration_ms: (data.duration_ms as number) || 0,
              completed_at: new Date().toISOString(),
            });
          }
        }
        break;
      }

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

      // --- Rich Agent Team Events (Phase 45: Agent Team Visualization) ---

      case 'AGENT_TEAM_CREATED': {
        const store = useAgentTeamStore.getState();
        store.reset();
        const agents = data.agents as Array<{ agent_id: string; agent_name: string; role: string }>;
        store.setTeamStatus({
          teamId: data.team_id as string,
          sessionId: '',
          mode: (data.mode as 'sequential' | 'parallel') || 'sequential',
          status: 'executing',
          totalAgents: agents.length,
          overallProgress: 0,
          agents: agents.map(a => ({
            agentId: a.agent_id,
            agentName: a.agent_name,
            agentType: 'hybrid' as const,
            role: a.role,
            status: 'pending' as const,
            progress: 0,
            toolCallsCount: 0,
            createdAt: (data.created_at as string) || new Date().toISOString(),
          })),
          createdAt: (data.created_at as string) || new Date().toISOString(),
          metadata: {},
        });
        break;
      }

      case 'AGENT_MEMBER_STARTED': {
        const startStore = useAgentTeamStore.getState();
        // Safety net: auto-create team if AGENT_TEAM_CREATED was missed
        if (!startStore.agentTeamStatus) {
          startStore.setTeamStatus({
            teamId: (data.team_id as string) || 'auto',
            sessionId: '',
            mode: 'parallel',
            status: 'executing',
            totalAgents: 0,
            overallProgress: 0,
            agents: [],
            createdAt: new Date().toISOString(),
            metadata: {},
          });
        }
        const existing = startStore.agentTeamStatus?.agents.find(
          a => a.agentId === (data.agent_id as string)
        );
        if (!existing) {
          startStore.addAgent({
            agentId: data.agent_id as string,
            agentName: (data.agent_name as string) || (data.agent_id as string),
            agentType: 'hybrid',
            role: (data.role as string) || 'agent',
            status: 'running',
            progress: 0,
            toolCallsCount: 0,
            createdAt: new Date().toISOString(),
            startedAt: (data.started_at as string) || new Date().toISOString(),
          });
        } else {
          startStore.updateAgentProgress({
            team_id: data.team_id as string,
            agent_id: data.agent_id as string,
            progress: 0,
            status: 'running',
            updated_at: (data.started_at as string) || new Date().toISOString(),
          });
        }
        break;
      }

      case 'AGENT_MEMBER_THINKING': {
        const thinkStore = useAgentTeamStore.getState();
        thinkStore.updateAgentThinking({
          team_id: data.team_id as string,
          agent_id: data.agent_id as string,
          thinking_content: (data.thinking_content as string) || '',
          timestamp: (data.timestamp as string) || new Date().toISOString(),
        });
        // Push to conversation log (skip redundant team_message/approval echoes)
        const msgType = data.message_type as string;
        if (msgType !== 'team_message' && msgType !== 'approval_required' && msgType !== 'inbox_received') {
          thinkStore.addAgentEvent(
            'thinking',
            data.agent_id as string,
            data.agent_id as string,
            (data.thinking_content as string) || '',
          );
        }
        break;
      }

      case 'AGENT_MEMBER_TOOL_CALL': {
        const toolStore = useAgentTeamStore.getState();
        const toolStatus = data.status as string;
        toolStore.updateAgentToolCall({
          team_id: data.team_id as string,
          agent_id: data.agent_id as string,
          tool_call_id: data.tool_call_id as string,
          tool_name: data.tool_name as string,
          status: toolStatus as 'running' | 'completed' | 'failed',
          input_args: (data.input_args as Record<string, unknown>) || {},
          output_result: (data.output_result as Record<string, unknown>) || null,
          timestamp: (data.timestamp as string) || new Date().toISOString(),
        });
        // Push to conversation log
        toolStore.addAgentEvent(
          'tool_call',
          data.agent_id as string,
          data.agent_id as string,
          `${data.tool_name as string} [${toolStatus}]`,
          { tool_call_id: data.tool_call_id, status: toolStatus },
        );
        break;
      }

      case 'AGENT_MEMBER_COMPLETED': {
        const completeStore = useAgentTeamStore.getState();
        const agentStatus = (data.status as string) || 'completed';
        completeStore.completeAgent({
          team_id: data.team_id as string,
          agent_id: data.agent_id as string,
          status: agentStatus as 'completed' | 'failed',
          duration_ms: (data.duration_ms as number) || 0,
          completed_at: (data.completed_at as string) || new Date().toISOString(),
        });
        // Store the agent's full output for detail drawer
        if (data.output) {
          const agentId = data.agent_id as string;
          const map = completeStore.agentDataMap;
          if (!map[agentId]) {
            map[agentId] = { thinkingHistory: [], toolCalls: [], output: '' };
          }
          map[agentId].output = data.output as string;
        }
        // Push to conversation log
        completeStore.addAgentEvent(
          'task_completed',
          data.agent_id as string,
          (data.agent_name as string) || (data.agent_id as string),
          agentStatus === 'failed' ? 'Task failed' : 'Task completed',
          { duration_ms: data.duration_ms, status: agentStatus },
        );
        break;
      }

      case 'AGENT_TEAM_COMPLETED': {
        const teamCompleteStore = useAgentTeamStore.getState();
        const teamStatus = (data.status as string) === 'failed' ? 'failed' : 'completed';
        // Auto-complete any agents still at 0% (AGENT_COMPLETE events may have been lost)
        if (teamCompleteStore.agentTeamStatus) {
          for (const agent of teamCompleteStore.agentTeamStatus.agents) {
            if (agent.status === 'running' || agent.status === 'pending') {
              teamCompleteStore.completeAgent({
                team_id: teamCompleteStore.agentTeamStatus.teamId,
                agent_id: agent.agentId,
                status: teamStatus === 'failed' ? 'failed' : 'completed',
                duration_ms: 0,
                completed_at: new Date().toISOString(),
              });
            }
          }
        }
        teamCompleteStore.completeTeam(
          teamStatus as 'completed' | 'failed',
          (data.completed_at as string) || new Date().toISOString()
        );
        break;
      }

      // --- Inter-Agent Communication Events (Phase 45: Sprint D) ---

      case 'AGENT_TEAM_MESSAGE': {
        const msgStore = useAgentTeamStore.getState();
        msgStore.addTeamMessage({
          team_id: data.team_id as string,
          from_agent: data.from_agent as string,
          to_agent: (data.to_agent as string) || null,
          content: data.content as string,
          directed: (data.directed as boolean) || false,
        });
        // Push to conversation log
        const toLabel = (data.to_agent as string) || 'all';
        msgStore.addAgentEvent(
          'message',
          data.from_agent as string,
          data.from_agent as string,
          `→ ${toLabel}: ${data.content as string}`,
        );
        break;
      }

      case 'AGENT_INBOX_RECEIVED': {
        const inboxStore = useAgentTeamStore.getState();
        inboxStore.addTeamMessage({
          team_id: data.team_id as string,
          from_agent: data.from_agent as string,
          to_agent: data.agent_id as string,
          content: data.content as string,
          directed: true,
        });
        // Push to conversation log
        inboxStore.addAgentEvent(
          'inbox',
          data.agent_id as string,
          data.agent_id as string,
          `Received from ${data.from_agent as string}`,
        );
        break;
      }

      case 'AGENT_TASK_CLAIMED':
      case 'AGENT_TASK_REASSIGNED':
        // Forward to thinking for visibility
        useAgentTeamStore.getState().updateAgentThinking({
          team_id: data.team_id as string,
          agent_id: data.agent_id as string,
          thinking_content: data.thinking_content as string || `[${eventType}]`,
          timestamp: new Date().toISOString(),
        });
        break;

      // --- Per-Tool HITL Approval (Phase 45: Sprint D) ---

      case 'AGENT_APPROVAL_REQUIRED': {
        const approvalStore = useAgentTeamStore.getState();
        approvalStore.addPendingApproval({
          team_id: data.team_id as string,
          approval_id: data.approval_id as string,
          agent_name: data.agent_name as string,
          tool_name: data.tool_name as string,
          risk_level: data.risk_level as string,
          message: data.message as string,
          arguments: (data.arguments as Record<string, unknown>) || {},
        });
        // Push to conversation log
        approvalStore.addAgentEvent(
          'approval',
          data.agent_name as string,
          data.agent_name as string,
          `Approval required: ${data.tool_name as string}`,
          { approval_id: data.approval_id, risk_level: data.risk_level },
        );
        break;
      }

      case 'PIPELINE_COMPLETE': {
        // Only finalize on the truly final event (after dispatch)
        if (data.final) {
          updateStep('dispatch', { status: 'completed' });
          updateStep('post_process', { status: 'completed' });
          setState(prev => ({
            ...prev,
            isRunning: false,
            totalMs: data.total_ms as number,
          }));
          // Safety net: auto-complete any unfinished agents when pipeline ends
          const pcStore = useAgentTeamStore.getState();
          if (pcStore.agentTeamStatus && pcStore.agentTeamStatus.status !== 'completed') {
            for (const agent of pcStore.agentTeamStatus.agents) {
              if (agent.status === 'running' || agent.status === 'pending') {
                pcStore.completeAgent({
                  team_id: pcStore.agentTeamStatus.teamId,
                  agent_id: agent.agentId,
                  status: 'completed',
                  duration_ms: 0,
                  completed_at: new Date().toISOString(),
                });
              }
            }
            pcStore.completeTeam('completed', new Date().toISOString());
          }
        }
        break;
      }

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

      // SSE stream ended — ensure UI stops spinning if PIPELINE_COMPLETE wasn't received
      setState(prev => prev.isRunning ? { ...prev, isRunning: false } : prev);
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

        // SSE stream ended — ensure UI stops spinning if PIPELINE_COMPLETE wasn't received
        setState(prev => prev.isRunning ? { ...prev, isRunning: false } : prev);
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

  const resolveTeamApproval = useCallback(async (
    approvalId: string,
    decision: 'approved' | 'rejected',
    decidedBy: string = 'user'
  ) => {
    try {
      const response = await fetch(`/api/v1/orchestration/chat/team-approval/${approvalId}/decide`, {
        method: 'POST',
        headers: _authHeaders(),
        body: JSON.stringify({ decision, decided_by: decidedBy }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      // Remove from pending approvals in store
      useAgentTeamStore.getState().removePendingApproval(approvalId);
    } catch (err) {
      console.error('[resolveTeamApproval] failed:', err);
    }
  }, [_authHeaders]);

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
    resolveTeamApproval,
  };
}
