/**
 * useSwarmReal Hook
 *
 * Real hook for Agent Swarm UI components with backend connection.
 * Connects to backend SSE events for real-time swarm state updates.
 *
 * Phase 29: Agent Swarm Visualization - Real Execution Mode
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  UIAgentTeamStatus,
  UIAgentSummary,
  AgentDetail,
  ThinkingContent,
  ToolCallInfo,
} from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Types
// =============================================================================

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  workers_count: number;
  estimated_duration: string;
}

interface DemoStartRequest {
  scenario: 'security_audit' | 'etl_pipeline' | 'data_pipeline' | 'custom';
  mode?: 'parallel' | 'sequential' | 'hierarchical';
  speed_multiplier?: number;
}

interface DemoStartResponse {
  swarm_id: string;
  session_id: string;
  status: string;
  message: string;
  sse_endpoint: string;
}

interface SwarmUpdateEvent {
  swarm_id: string;
  status: string;
  mode: string;
  overall_progress: number;
  total_tool_calls: number;
  completed_tool_calls: number;
  agents: WorkerEventData[];
}

interface WorkerEventData {
  worker_id: string;
  worker_name: string;
  worker_type: string;
  role: string;
  status: string;
  progress: number;
  current_task: string | null;
  tool_calls_count: number;
  tool_calls: {
    tool_id: string;
    tool_name: string;
    status: string;
    is_mcp: boolean;
  }[];
  thinking_contents: {
    content: string;
    token_count: number | null;
  }[];
}

export interface MockMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface UseSwarmRealReturn {
  // State
  agentTeamStatus: UIAgentTeamStatus | null;
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  isDrawerOpen: boolean;
  mockMessages: MockMessage[];

  // Connection State
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  isCompleted: boolean;

  // Available Scenarios
  scenarios: DemoScenario[];

  // Demo Actions
  startDemo: (request: DemoStartRequest) => Promise<void>;
  stopDemo: () => Promise<void>;
  loadScenarios: () => Promise<void>;

  // UI Actions
  selectWorker: (agentId: string | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;

  // Mock Chat (for display purposes)
  addMockUserMessage: (content: string) => void;
  addMockAssistantMessage: (content: string) => void;

  // Reset
  reset: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Helper Functions
// =============================================================================

const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

const mapAgentType = (type: string): UIAgentSummary['agentType'] => {
  const typeMap: Record<string, UIAgentSummary['agentType']> = {
    'analyst': 'claude_sdk',
    'coder': 'maf',
    'writer': 'claude_sdk',
    'reviewer': 'hybrid',
    'researcher': 'claude_sdk',
    'designer': 'maf',
    'coordinator': 'hybrid',
    'tester': 'maf',
    'custom': 'claude_sdk',
  };
  return typeMap[type.toLowerCase()] || 'claude_sdk';
};

const mapAgentMemberStatus = (status: string): UIAgentSummary['status'] => {
  const statusMap: Record<string, UIAgentSummary['status']> = {
    'pending': 'pending',
    'running': 'running',
    'thinking': 'running',
    'tool_calling': 'running',
    'completed': 'completed',
    'failed': 'failed',
  };
  return statusMap[status.toLowerCase()] || 'pending';
};

const mapTeamMode = (mode: string): UIAgentTeamStatus['mode'] => {
  const modeMap: Record<string, UIAgentTeamStatus['mode']> = {
    'parallel': 'parallel',
    'sequential': 'sequential',
    'hierarchical': 'hierarchical',
  };
  return modeMap[mode.toLowerCase()] || 'parallel';
};

const mapSwarmStatus = (status: string): UIAgentTeamStatus['status'] => {
  const statusMap: Record<string, UIAgentTeamStatus['status']> = {
    'running': 'executing',
    'executing': 'executing',
    'completed': 'completed',
    'failed': 'failed',
    'pending': 'executing',
  };
  return statusMap[status.toLowerCase()] || 'executing';
};

// =============================================================================
// Hook Implementation
// =============================================================================

export function useSwarmReal(): UseSwarmRealReturn {
  // State
  const [agentTeamStatus, setTeamStatus] = useState<UIAgentTeamStatus | null>(null);
  const [selectedAgentId, setSelectedWorkerId] = useState<string | null>(null);
  const [selectedAgentDetail, setSelectedAgentDetail] = useState<AgentDetail | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [mockMessages, setMockMessages] = useState<MockMessage[]>([]);

  // Connection State
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);

  // Scenarios
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const currentSwarmIdRef = useRef<string | null>(null);

  // Store full worker data from SSE events (includes tool_calls and thinking_contents)
  const workersDataRef = useRef<Map<string, WorkerEventData>>(new Map());

  // =============================================================================
  // API Functions
  // =============================================================================

  const loadScenarios = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/swarm/demo/scenarios`);
      if (!response.ok) {
        throw new Error(`Failed to load scenarios: ${response.status}`);
      }
      const data = await response.json();
      setScenarios(data);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
      setError(err instanceof Error ? err.message : 'Failed to load scenarios');
    }
  }, []);

  const startDemo = useCallback(async (request: DemoStartRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      // Start demo
      const response = await fetch(`${API_BASE_URL}/swarm/demo/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to start demo: ${response.status}`);
      }

      const data: DemoStartResponse = await response.json();
      currentSwarmIdRef.current = data.swarm_id;

      // Add initial messages based on scenario
      const scenarioMessages: Record<string, { user: string; assistant: string }> = {
        security_audit: {
          user: '請對生產環境執行完整的安全審計',
          assistant: '正在啟動安全審計流程，將並行執行網路掃描、漏洞分析和合規檢查...',
        },
        etl_pipeline: {
          user: 'ETL Pipeline 出現錯誤，請診斷問題並提供修復方案',
          assistant: '正在分析 ETL Pipeline 錯誤，將調查日誌、根因和解決方案...',
        },
        data_pipeline: {
          user: '請監控資料管道的品質和效能',
          assistant: '正在監控資料管道，將檢查資料品質指標和效能優化機會...',
        },
        custom: {
          user: '執行自訂的多代理任務',
          assistant: '正在啟動自訂任務執行...',
        },
      };

      const msgs = scenarioMessages[request.scenario] || scenarioMessages.custom;
      const timestamp = new Date().toISOString();

      setMockMessages([
        {
          id: generateId(),
          role: 'user',
          content: msgs.user,
          timestamp,
        },
        {
          id: generateId(),
          role: 'assistant',
          content: msgs.assistant,
          timestamp,
        },
      ]);

      // Connect to SSE
      const sseUrl = `${API_BASE_URL}/swarm/demo/events/${data.swarm_id}`;
      const eventSource = new EventSource(sseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setIsLoading(false);
      };

      eventSource.addEventListener('swarm_update', (event) => {
        const eventData: SwarmUpdateEvent = JSON.parse(event.data);
        updateSwarmStatus(eventData);
      });

      eventSource.addEventListener('swarm_complete', (event) => {
        const eventData = JSON.parse(event.data);
        console.log('Swarm completed:', eventData);
        // Mark as completed
        setIsCompleted(true);
        // Keep connection open briefly to ensure final state is captured
        setTimeout(() => {
          eventSource.close();
          setIsConnected(false);
          // Clear error on successful completion
          setError(null);
        }, 1000);
      });

      eventSource.addEventListener('error', (event) => {
        // Only handle explicit error events with data
        try {
          const messageEvent = event as MessageEvent;
          if (messageEvent.data) {
            const errorData = JSON.parse(messageEvent.data);
            if (errorData.error) {
              setError(errorData.error);
              eventSource.close();
              setIsConnected(false);
            }
          }
        } catch {
          // Ignore parse errors - this might be a normal close
        }
      });

      eventSource.onerror = () => {
        // Don't set error here as it might be a normal close
        // Only update connection state if we're still supposed to be connected
        if (eventSourceRef.current === eventSource) {
          setIsConnected(false);
        }
      };

    } catch (err) {
      console.error('Failed to start demo:', err);
      setError(err instanceof Error ? err.message : 'Failed to start demo');
      setIsLoading(false);
    }
  }, []);

  const stopDemo = useCallback(async () => {
    if (currentSwarmIdRef.current) {
      try {
        await fetch(`${API_BASE_URL}/swarm/demo/stop/${currentSwarmIdRef.current}`, {
          method: 'POST',
        });
      } catch (err) {
        console.error('Failed to stop demo:', err);
      }
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    currentSwarmIdRef.current = null;
  }, []);

  // =============================================================================
  // State Update Functions
  // =============================================================================

  const updateSwarmStatus = useCallback((data: SwarmUpdateEvent) => {
    // Store full worker data for later use (includes tool_calls and thinking_contents)
    data.agents.forEach((w) => {
      workersDataRef.current.set(w.worker_id, w);
    });

    const agents: UIAgentSummary[] = data.agents.map((w) => ({
      agentId: w.worker_id,
      agentName: w.worker_name,
      agentType: mapAgentType(w.worker_type),
      role: w.role,
      status: mapAgentMemberStatus(w.status),
      progress: w.progress,
      currentAction: w.current_task || undefined,
      toolCallsCount: w.tool_calls_count,
      createdAt: new Date().toISOString(),
    }));

    const newStatus: UIAgentTeamStatus = {
      teamId: data.swarm_id,
      sessionId: `session-${data.swarm_id}`,
      mode: mapTeamMode(data.mode),
      status: mapSwarmStatus(data.status),
      overallProgress: data.overall_progress,
      agents,
      totalAgents: agents.length,
      createdAt: new Date().toISOString(),
      startedAt: new Date().toISOString(),
      metadata: {
        totalToolCalls: data.total_tool_calls,
        completedToolCalls: data.completed_tool_calls,
      },
    };

    setTeamStatus(newStatus);

    // Update selected worker detail if drawer is open
    if (selectedAgentId) {
      const selectedWorkerData = data.agents.find(w => w.worker_id === selectedAgentId);
      if (selectedWorkerData) {
        updateAgentDetail(selectedWorkerData);
      }
    }
  }, [selectedAgentId]);

  const updateAgentDetail = useCallback((workerData: WorkerEventData) => {
    const thinkingHistory: ThinkingContent[] = workerData.thinking_contents.map((tc) => ({
      content: tc.content,
      timestamp: new Date().toISOString(),
      tokenCount: tc.token_count || undefined,
    }));

    const toolCalls: ToolCallInfo[] = workerData.tool_calls.map(tc => ({
      toolCallId: tc.tool_id,
      toolName: tc.tool_name,
      status: tc.status as ToolCallInfo['status'],
      inputArgs: {},
      startedAt: new Date().toISOString(),
    }));

    const detail: AgentDetail = {
      agentId: workerData.worker_id,
      agentName: workerData.worker_name,
      agentType: mapAgentType(workerData.worker_type),
      role: workerData.role,
      status: mapAgentMemberStatus(workerData.status),
      progress: workerData.progress,
      currentAction: workerData.current_task || undefined,
      toolCallsCount: workerData.tool_calls_count,
      createdAt: new Date().toISOString(),
      taskId: `task-${workerData.worker_id}`,
      taskDescription: workerData.current_task || `${workerData.role} - ${workerData.worker_name}`,
      thinkingHistory,
      toolCalls,
      messages: [],
      startedAt: new Date().toISOString(),
    };

    setSelectedAgentDetail(detail);
  }, []);

  // =============================================================================
  // UI Actions
  // =============================================================================

  const selectWorker = useCallback((agentId: string | null) => {
    setSelectedWorkerId(agentId);
    if (agentId && agentTeamStatus) {
      const worker = agentTeamStatus.agents.find(w => w.agentId === agentId);
      if (worker) {
        // Try to get full worker data from stored SSE events
        const fullWorkerData = workersDataRef.current.get(agentId);

        if (fullWorkerData) {
          // Use full data with tool_calls and thinking_contents
          updateAgentDetail(fullWorkerData);
        } else {
          // Fallback: Create basic detail from summary
          setSelectedAgentDetail({
            agentId: worker.agentId,
            agentName: worker.agentName,
            agentType: worker.agentType,
            role: worker.role,
            status: worker.status,
            progress: worker.progress,
            currentAction: worker.currentAction,
            toolCallsCount: worker.toolCallsCount,
            createdAt: worker.createdAt,
            taskId: `task-${worker.agentId}`,
            taskDescription: worker.currentAction || `${worker.role} - ${worker.agentName}`,
            thinkingHistory: [],
            toolCalls: [],
            messages: [],
            startedAt: worker.createdAt,
          });
        }
        // Auto open drawer when selecting a worker
        setIsDrawerOpen(true);
      }
    } else {
      setSelectedAgentDetail(null);
      setIsDrawerOpen(false);
    }
  }, [agentTeamStatus, updateAgentDetail]);

  const openDrawer = useCallback(() => {
    setIsDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setIsDrawerOpen(false);
    setSelectedWorkerId(null);
    setSelectedAgentDetail(null);
  }, []);

  // =============================================================================
  // Mock Chat Actions
  // =============================================================================

  const addMockUserMessage = useCallback((content: string) => {
    setMockMessages(prev => [
      ...prev,
      {
        id: generateId(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const addMockAssistantMessage = useCallback((content: string) => {
    setMockMessages(prev => [
      ...prev,
      {
        id: generateId(),
        role: 'assistant',
        content,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  // =============================================================================
  // Reset
  // =============================================================================

  const reset = useCallback(() => {
    stopDemo();
    setTeamStatus(null);
    setSelectedWorkerId(null);
    setSelectedAgentDetail(null);
    setIsDrawerOpen(false);
    setMockMessages([]);
    setError(null);
    setIsCompleted(false);
    // Clear stored worker data
    workersDataRef.current.clear();
  }, [stopDemo]);

  // =============================================================================
  // Cleanup
  // =============================================================================

  useEffect(() => {
    // Load scenarios on mount
    loadScenarios();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [loadScenarios]);

  // =============================================================================
  // Return
  // =============================================================================

  return {
    // State
    agentTeamStatus,
    selectedAgentId,
    selectedAgentDetail,
    isDrawerOpen,
    mockMessages,

    // Connection State
    isConnected,
    isLoading,
    error,
    isCompleted,

    // Scenarios
    scenarios,

    // Demo Actions
    startDemo,
    stopDemo,
    loadScenarios,

    // UI Actions
    selectWorker,
    openDrawer,
    closeDrawer,

    // Mock Chat
    addMockUserMessage,
    addMockAssistantMessage,

    // Reset
    reset,
  };
}

export default useSwarmReal;
