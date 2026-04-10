import { useState, useCallback, useRef } from 'react';

// SSE Event types from backend PipelineEventEmitter
type SSEEventType =
  | 'PIPELINE_START'
  | 'TASK_DISPATCHED'
  | 'ROUTING_COMPLETE'
  | 'AGENT_THINKING'
  | 'TEXT_DELTA'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_END'
  | 'SWARM_WORKER_START'
  | 'SWARM_WORKER_END'
  | 'SWARM_PROGRESS'
  | 'APPROVAL_REQUIRED'
  // V2: Parallel team events
  | 'TEAM_MESSAGE'
  | 'INBOX_RECEIVED'
  | 'TASK_COMPLETED'
  | 'ALL_TASKS_DONE'
  | 'PIPELINE_COMPLETE'
  | 'PIPELINE_ERROR';

interface StepEvent {
  step: string;
  status: 'running' | 'complete' | 'error';
  label?: string;
  data?: Record<string, any>;
  timestamp?: string;
}

interface AgentEvent {
  agent: string;
  text: string;
  timestamp?: string;
  type?: 'start' | 'thinking' | 'response' | 'tool_call' | 'message_sent' | 'message_received' | 'task_claimed' | 'task_completed' | 'finished' | 'progress';
  to_agent?: string;  // V2: directed message target
  directed?: boolean; // V2: is this a directed message?
}

// V2: Per-agent status tracking for parallel execution
interface AgentStatus {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  currentTaskId?: string;
  currentTaskDesc?: string;
  iterations?: number;
}

// V2: Task progress tracking
interface TaskProgress {
  total: number;
  completed: number;
  in_progress: number;
  pending: number;
}

interface ApprovalInfo {
  approval_id: string;
  checkpoint_id: string;
  risk_level: string;
  message: string;
}

interface OrchestratorStreamState {
  isStreaming: boolean;
  phase: 'idle' | 'orchestrator' | 'agents' | 'complete' | 'error' | 'pending_approval';
  steps: StepEvent[];
  agentEvents: AgentEvent[];  // agent responses from Phase 2
  thinkingText: string;
  llmResponse: string;        // accumulated TEXT_DELTA
  selectedMode: string;
  approval: ApprovalInfo | null;
  error: string | null;
  metadata: Record<string, any>;
  // V2: Parallel team tracking
  agentStatuses: Record<string, AgentStatus>;  // per-agent live status
  taskProgress: TaskProgress;                  // task completion progress
  teamMessages: AgentEvent[];                  // directed + broadcast messages
  terminationReason: string;                   // "all_done" | "timeout" | "no_progress"
}

const initialState: OrchestratorStreamState = {
  isStreaming: false,
  phase: 'idle',
  steps: [],
  agentEvents: [],
  thinkingText: '',
  llmResponse: '',
  selectedMode: '',
  approval: null,
  error: null,
  metadata: {},
  agentStatuses: {},
  taskProgress: { total: 0, completed: 0, in_progress: 0, pending: 0 },
  teamMessages: [],
  terminationReason: '',
};

export function useOrchestratorSSE() {
  const [state, setState] = useState<OrchestratorStreamState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (params: URLSearchParams, endpoint?: string) => {
    // Reset state
    setState({ ...initialState, isStreaming: true, phase: 'orchestrator' });

    const controller = new AbortController();
    abortRef.current = controller;

    const url = endpoint || '/api/v1/poc/agent-team/test-orchestrator-stream';

    try {
      const response = await fetch(
        `${url}?${params}`,
        { method: 'POST', signal: controller.signal }
      );

      if (!response.ok || !response.body) {
        setState(s => ({ ...s, isStreaming: false, phase: 'error', error: `HTTP ${response.status}` }));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // keep incomplete line in buffer

        let currentEventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEventType) {
            try {
              const data = JSON.parse(line.slice(6));
              dispatchEvent(currentEventType as SSEEventType, data, setState);
            } catch (e) {
              console.warn('SSE parse error:', e);
            }
            currentEventType = '';
          }
        }
      }

      // Stream ended
      setState(s => ({ ...s, isStreaming: false }));

    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setState(s => ({ ...s, isStreaming: false, phase: 'error', error: err.message }));
      }
    }
  }, []);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setState(s => ({ ...s, isStreaming: false }));
  }, []);

  return { state, startStream, cancelStream };
}

function dispatchEvent(
  type: SSEEventType,
  data: Record<string, any>,
  setState: React.Dispatch<React.SetStateAction<OrchestratorStreamState>>
) {
  switch (type) {
    case 'PIPELINE_START':
      setState(s => ({ ...s, phase: 'orchestrator', metadata: { ...s.metadata, session_id: data.session_id } }));
      break;

    case 'TASK_DISPATCHED':
      setState(s => {
        // If status=complete, update existing step instead of adding new one
        if (data.status === 'complete' || data.status === 'error') {
          const steps = [...s.steps];
          let idx = -1;
          for (let i = steps.length - 1; i >= 0; i--) {
            if (steps[i].step === data.step) { idx = i; break; }
          }
          if (idx >= 0) {
            steps[idx] = { ...steps[idx], status: data.status, data: { ...steps[idx].data, ...data } };
            return { ...s, steps };
          }
        }
        return {
          ...s,
          phase: data.step?.startsWith('7_') ? 'agents' : 'orchestrator',
          steps: [...s.steps, {
            step: data.step || '',
            status: data.status || 'running',
            label: data.label || data.step,
            data,
            timestamp: data.timestamp,
          }],
        };
      });
      break;

    case 'ROUTING_COMPLETE':
      setState(s => {
        const steps = [...s.steps];
        // findLastIndex polyfill for ES2022 compat
        let idx = -1;
        for (let i = steps.length - 1; i >= 0; i--) {
          if (steps[i].step === data.step) { idx = i; break; }
        }
        if (idx >= 0) {
          steps[idx] = { ...steps[idx], status: 'complete', data: { ...steps[idx].data, ...data } };
        }
        return {
          ...s,
          steps,
          selectedMode: data.selected_mode || s.selectedMode,
        };
      });
      break;

    case 'AGENT_THINKING':
      setState(s => {
        // If status=complete, update existing step
        if (data.step && data.status === 'complete') {
          const steps = [...s.steps];
          let idx = -1;
          for (let i = steps.length - 1; i >= 0; i--) {
            if (steps[i].step === data.step) { idx = i; break; }
          }
          if (idx >= 0) {
            steps[idx] = { ...steps[idx], status: 'complete', data: { ...steps[idx].data, ...data } };
            return { ...s, steps };
          }
        }
        // If this is step start, add to steps
        if (data.step && data.status === 'running') {
          return {
            ...s,
            steps: [...s.steps, { step: data.step, status: 'running', label: data.label || data.agent || 'LLM Thinking...', data }],
            thinkingText: data.thinking || s.thinkingText,
          };
        }
        return { ...s, thinkingText: s.thinkingText + (data.thinking || '') };
      });
      break;

    case 'TEXT_DELTA':
      setState(s => {
        // Synthesis from TeamLead → goes to llmResponse (main response panel)
        if (data.source === 'synthesis') {
          return { ...s, llmResponse: s.llmResponse + (data.delta || '') };
        }
        // If from an agent, add to agent events
        if (data.agent) {
          return {
            ...s,
            agentEvents: [...s.agentEvents, { agent: data.agent, text: data.delta || '', timestamp: data.timestamp }],
          };
        }
        return { ...s, llmResponse: s.llmResponse + (data.delta || '') };
      });
      break;

    case 'SWARM_WORKER_START':
      setState(s => ({
        ...s,
        phase: 'agents',
        agentEvents: [...s.agentEvents, {
          agent: data.agent || data.worker || '?', text: '[Started]',
          timestamp: data.timestamp, type: 'start',
        }],
        agentStatuses: {
          ...s.agentStatuses,
          [data.agent || '']: { name: data.agent || '', status: 'running' },
        },
      }));
      break;

    case 'SWARM_WORKER_END':
      setState(s => ({
        ...s,
        agentEvents: [...s.agentEvents, {
          agent: data.agent || '?', text: `[Finished: ${data.status || 'done'}]`,
          timestamp: data.timestamp, type: 'finished',
        }],
        agentStatuses: {
          ...s.agentStatuses,
          [data.agent || '']: {
            ...s.agentStatuses[data.agent || ''],
            status: 'completed',
            iterations: data.iterations,
          },
        },
      }));
      break;

    case 'SWARM_PROGRESS':
      setState(s => {
        const updates: Partial<OrchestratorStreamState> = {};

        // V2: Handle specific parallel event types within SWARM_PROGRESS
        if (data.event_type === 'task_claimed') {
          updates.agentStatuses = {
            ...s.agentStatuses,
            [data.agent || '']: {
              ...s.agentStatuses[data.agent || ''],
              status: 'running',
              currentTaskId: data.task_id,
              currentTaskDesc: data.description,
            },
          };
        } else if (data.event_type === 'task_completed') {
          const prog = { ...s.taskProgress };
          prog.completed = (prog.completed || 0) + 1;
          prog.in_progress = Math.max(0, (prog.in_progress || 0) - 1);
          updates.taskProgress = prog;
        } else if (data.event_type === 'phase0_complete') {
          updates.taskProgress = {
            total: data.tasks_created || 0,
            completed: 0,
            in_progress: 0,
            pending: data.tasks_created || 0,
          };
        } else if (data.event_type === 'team_complete') {
          updates.terminationReason = data.termination_reason || '';
        } else if (data.event_type === 'agent_idle') {
          // V3: agent completed task, now polling for messages
          if (data.agent) {
            updates.agentStatuses = {
              ...s.agentStatuses,
              [data.agent]: {
                ...s.agentStatuses[data.agent],
                status: 'idle' as any,
              },
            };
          }
        } else if (data.event_type === 'communication_window') {
          // V3: all tasks done, agents staying alive for cross-agent messaging
          updates.terminationReason = `communication window (${data.duration_s || 15}s)`;
        } else if (data.event_type === 'shutdown_signal') {
          // V3: lead shutting down all agents
          updates.terminationReason = 'shutdown';
        } else if (data.event_type === 'shutdown_request') {
          // V4: graceful shutdown — mark all agents as shutting down
          if (data.agents && Array.isArray(data.agents)) {
            const newStatuses = { ...s.agentStatuses };
            for (const name of data.agents) {
              if (newStatuses[name]) {
                newStatuses[name] = { ...newStatuses[name], status: 'idle' as any };
              }
            }
            updates.agentStatuses = newStatuses;
          }
          updates.terminationReason = 'shutting down (awaiting ACK)';
        } else if (data.event_type === 'shutdown_ack') {
          // V4: agent acknowledged shutdown
          if (data.agent && s.agentStatuses[data.agent]) {
            updates.agentStatuses = {
              ...s.agentStatuses,
              [data.agent]: { ...s.agentStatuses[data.agent], status: 'completed' },
            };
          }
        } else if (data.event_type === 'shutdown_complete') {
          // V4: all agents shut down
          updates.terminationReason = `shutdown (${data.acked?.length || 0} ACKed, ${data.force_killed?.length || 0} force-killed)`;
        }

        return {
          ...s,
          ...updates,
          agentEvents: [...s.agentEvents, {
            agent: data.agent || 'workflow',
            text: data.preview || data.event_type || '',
            timestamp: data.timestamp,
            type: 'progress',
          }],
        };
      });
      break;

    // V2: Parallel team communication events
    case 'TEAM_MESSAGE':
      setState(s => ({
        ...s,
        teamMessages: [...s.teamMessages, {
          agent: data.from || data.agent || '?',
          text: data.content || data.message || '',
          to_agent: data.to,
          directed: data.directed || !!data.to,
          timestamp: data.timestamp,
          type: 'message_sent',
        }],
        agentEvents: [...s.agentEvents, {
          agent: data.from || '?',
          text: data.to
            ? `→ ${data.to}: ${data.content || data.message || ''}`
            : `[broadcast]: ${data.content || data.message || ''}`,
          to_agent: data.to,
          directed: data.directed || !!data.to,
          timestamp: data.timestamp,
          type: 'message_sent',
        }],
      }));
      break;

    case 'INBOX_RECEIVED':
      setState(s => ({
        ...s,
        agentEvents: [...s.agentEvents, {
          agent: data.agent || '?',
          text: `[inbox] from ${data.from || '?'}`,
          timestamp: data.timestamp,
          type: 'message_received',
        }],
      }));
      break;

    case 'TASK_COMPLETED':
      setState(s => {
        const prog = { ...s.taskProgress };
        prog.completed = (prog.completed || 0) + 1;
        prog.in_progress = Math.max(0, (prog.in_progress || 0) - 1);
        return {
          ...s,
          taskProgress: prog,
          agentEvents: [...s.agentEvents, {
            agent: data.agent || '?',
            text: `[task ${data.task_id} completed]`,
            timestamp: data.timestamp,
            type: 'task_completed',
          }],
        };
      });
      break;

    case 'ALL_TASKS_DONE':
      setState(s => ({
        ...s,
        terminationReason: data.reason || 'all_completed',
        agentEvents: [...s.agentEvents, {
          agent: 'system',
          text: `All tasks done: ${data.reason || 'completed'}`,
          timestamp: data.timestamp,
          type: 'finished',
        }],
      }));
      break;

    case 'APPROVAL_REQUIRED':
      setState(s => ({
        ...s,
        phase: 'pending_approval',
        approval: {
          approval_id: data.approval_id || '',
          checkpoint_id: data.checkpoint_id || '',
          risk_level: data.risk_level || '',
          message: data.message || 'Approval required',
        },
      }));
      break;

    case 'PIPELINE_COMPLETE':
      setState(s => ({
        ...s,
        isStreaming: false,
        phase: data.status === 'pending_approval' ? 'pending_approval' : 'complete',
        metadata: { ...s.metadata, ...data },
      }));
      break;

    case 'PIPELINE_ERROR':
      setState(s => ({
        ...s,
        isStreaming: false,
        phase: 'error',
        error: data.error || 'Unknown error',
      }));
      break;

    default:
      // Unknown event — ignore
      break;
  }
}

export type { OrchestratorStreamState, StepEvent, AgentEvent, ApprovalInfo, AgentStatus, TaskProgress };
