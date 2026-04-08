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
  | 'SWARM_PROGRESS'
  | 'APPROVAL_REQUIRED'
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
};

export function useOrchestratorSSE() {
  const [state, setState] = useState<OrchestratorStreamState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (params: URLSearchParams) => {
    // Reset state
    setState({ ...initialState, isStreaming: true, phase: 'orchestrator' });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(
        `/api/v1/poc/agent-team/test-orchestrator-stream?${params}`,
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
      setState(s => ({
        ...s,
        phase: data.step?.startsWith('7_') ? 'agents' : 'orchestrator',
        steps: [...s.steps, {
          step: data.step || '',
          status: 'running',
          label: data.label || data.step,
          data,
          timestamp: data.timestamp,
        }],
      }));
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
        // If this is step start, add to steps
        if (data.step && data.status === 'running') {
          return {
            ...s,
            steps: [...s.steps, { step: data.step, status: 'running', label: data.label || 'LLM Thinking...', data }],
            thinkingText: data.thinking || s.thinkingText,
          };
        }
        return { ...s, thinkingText: s.thinkingText + (data.thinking || '') };
      });
      break;

    case 'TEXT_DELTA':
      setState(s => {
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
        agentEvents: [...s.agentEvents, { agent: data.agent || data.worker || '?', text: '[Started]', timestamp: data.timestamp }],
      }));
      break;

    case 'SWARM_PROGRESS':
      // Raw workflow event — can show as debug
      setState(s => ({
        ...s,
        agentEvents: [...s.agentEvents, {
          agent: data.agent || 'workflow',
          text: data.preview || data.event_type || '',
          timestamp: data.timestamp,
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

export type { OrchestratorStreamState, StepEvent, AgentEvent, ApprovalInfo };
