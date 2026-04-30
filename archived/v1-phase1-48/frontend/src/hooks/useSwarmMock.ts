/**
 * useSwarmMock Hook
 *
 * Mock hook for testing Agent Swarm UI components.
 * Provides complete control over swarm state without backend dependency.
 *
 * Phase 29: Agent Swarm Visualization Testing
 */

import { useCallback, useState } from 'react';
import type {
  UIAgentTeamStatus,
  UIAgentSummary,
  AgentDetail,
  AgentType,
  AgentMemberStatus,
  TeamMode,
  ThinkingContent,
  ToolCallInfo,
  AgentMessage,
} from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Types
// =============================================================================

interface MockSwarmConfig {
  mode?: TeamMode;
  workerCount?: number;
  agentTypes?: AgentType[];
}

interface UseSwarmMockReturn {
  // State
  agentTeamStatus: UIAgentTeamStatus | null;
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  isDrawerOpen: boolean;
  mockMessages: MockMessage[];

  // Swarm Actions
  createSwarm: (config?: MockSwarmConfig) => void;
  addAgent: (name: string, type: AgentType, role: string) => void;
  removeWorker: (agentId: string) => void;
  completeTeam: () => void;
  failSwarm: () => void;
  resetSwarm: () => void;

  // Worker Actions
  setAgentMemberStatus: (agentId: string, status: AgentMemberStatus) => void;
  setWorkerProgress: (agentId: string, progress: number) => void;
  addThinking: (agentId: string, content: string) => void;
  addToolCall: (agentId: string, toolName: string, status?: ToolCallInfo['status']) => void;
  addMessage: (agentId: string, role: AgentMessage['role'], content: string) => void;
  completeAgent: (agentId: string) => void;
  failWorker: (agentId: string, error: string) => void;

  // UI Actions
  selectWorker: (agentId: string | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;

  // Mock Chat
  addMockUserMessage: (content: string) => void;
  addMockAssistantMessage: (content: string) => void;

  // Preset Scenarios
  loadETLScenario: () => void;
  loadSecurityAuditScenario: () => void;
  loadDataPipelineScenario: () => void;
}

export interface MockMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

const generateId = () => `mock-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

const createMockAgent = (
  name: string,
  type: AgentType,
  role: string,
  index: number
): UIAgentSummary => ({
  agentId: `worker-${index}-${generateId()}`,
  agentName: name,
  agentType: type,
  role,
  status: 'pending',
  progress: 0,
  toolCallsCount: 0,
  createdAt: new Date().toISOString(),
});

const createMockSwarm = (config: MockSwarmConfig = {}): UIAgentTeamStatus => {
  const { mode = 'sequential' } = config;
  return {
    teamId: `swarm-${generateId()}`,
    sessionId: `session-${generateId()}`,
    mode,
    status: 'initializing',
    totalAgents: 0,
    overallProgress: 0,
    agents: [],
    createdAt: new Date().toISOString(),
    metadata: { mock: true },
  };
};

const createEmptyAgentDetail = (worker: UIAgentSummary): AgentDetail => ({
  ...worker,
  taskId: `task-${generateId()}`,
  taskDescription: `執行 ${worker.agentName} 的任務`,
  thinkingHistory: [],
  toolCalls: [],
  messages: [],
});

// =============================================================================
// Preset Scenarios
// =============================================================================

const ETL_SCENARIO = {
  swarmConfig: { mode: 'sequential' as TeamMode },
  agents: [
    { name: '診斷專家', type: 'claude_sdk' as AgentType, role: 'Diagnostic' },
    { name: '修復專家', type: 'claude_sdk' as AgentType, role: 'Remediation' },
    { name: '驗證專家', type: 'maf' as AgentType, role: 'Verification' },
  ],
  messages: [
    { role: 'user' as const, content: 'APAC Glider ETL Pipeline 連續第三天失敗，日報表完全無法產出' },
    { role: 'assistant' as const, content: '我來組建專業團隊分析這個 ETL 失敗問題。正在啟動診斷流程...' },
  ],
  thinkingContent: `我需要分析這個 ETL 失敗問題。根據用戶提供的信息：

1. 錯誤是 "Connection timeout to source database"
2. 連續三天失敗
3. 影響 APAC Finance Daily Report

這表明問題可能是：
- 網路配置變更
- 防火牆規則調整
- 源數據庫負載過高
- 連接池配置問題

我應該先查詢 ADF 的詳細日誌來確認具體的錯誤模式...`,
};

const SECURITY_AUDIT_SCENARIO = {
  swarmConfig: { mode: 'parallel' as TeamMode },
  agents: [
    { name: '網路掃描', type: 'maf' as AgentType, role: 'Network Scanner' },
    { name: '漏洞分析', type: 'claude_sdk' as AgentType, role: 'Vulnerability Analyzer' },
    { name: '合規檢查', type: 'hybrid' as AgentType, role: 'Compliance Checker' },
    { name: '報告生成', type: 'claude_sdk' as AgentType, role: 'Report Generator' },
  ],
  messages: [
    { role: 'user' as const, content: '請對生產環境執行完整的安全審計' },
    { role: 'assistant' as const, content: '正在啟動安全審計流程，將並行執行網路掃描、漏洞分析和合規檢查...' },
  ],
  thinkingContent: `執行安全審計需要多個專業領域的協作：

1. 網路掃描 - 檢測開放端口和服務
2. 漏洞分析 - 識別已知漏洞
3. 合規檢查 - 驗證安全策略符合性
4. 報告生成 - 彙整所有發現

各模組將並行執行以提高效率...`,
};

const DATA_PIPELINE_SCENARIO = {
  swarmConfig: { mode: 'pipeline' as TeamMode },
  agents: [
    { name: '數據提取', type: 'maf' as AgentType, role: 'Data Extractor' },
    { name: '數據清洗', type: 'claude_sdk' as AgentType, role: 'Data Cleaner' },
    { name: '數據轉換', type: 'claude_sdk' as AgentType, role: 'Data Transformer' },
    { name: '數據載入', type: 'maf' as AgentType, role: 'Data Loader' },
  ],
  messages: [
    { role: 'user' as const, content: '請執行每日數據同步管線' },
    { role: 'assistant' as const, content: '正在啟動數據管線，將依序執行提取、清洗、轉換、載入...' },
  ],
  thinkingContent: `數據管線執行計劃：

1. 提取 (Extract) - 從源系統讀取數據
2. 清洗 (Clean) - 移除異常值和重複數據
3. 轉換 (Transform) - 格式轉換和計算衍生欄位
4. 載入 (Load) - 寫入目標系統

這是一個典型的 ETL 流程...`,
};

// =============================================================================
// Hook Implementation
// =============================================================================

export const useSwarmMock = (): UseSwarmMockReturn => {
  const [agentTeamStatus, setTeamStatus] = useState<UIAgentTeamStatus | null>(null);
  const [selectedAgentId, setSelectedWorkerId] = useState<string | null>(null);
  const [workerDetails, setAgentDetails] = useState<Map<string, AgentDetail>>(new Map());
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [mockMessages, setMockMessages] = useState<MockMessage[]>([]);

  // ---------------------------------------------------------------------------
  // Swarm Actions
  // ---------------------------------------------------------------------------

  const createSwarm = useCallback((config: MockSwarmConfig = {}) => {
    const newSwarm = createMockSwarm(config);
    newSwarm.status = 'executing';
    newSwarm.startedAt = new Date().toISOString();
    setTeamStatus(newSwarm);
    setAgentDetails(new Map());
    setMockMessages([]);
  }, []);

  const addAgent = useCallback((name: string, type: AgentType, role: string) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      const newAgent = createMockAgent(name, type, role, prev.agents.length);
      const detail = createEmptyAgentDetail(newAgent);
      setAgentDetails((details) => new Map(details).set(newAgent.agentId, detail));
      return {
        ...prev,
        agents: [...prev.agents, newAgent],
        totalAgents: prev.agents.length + 1,
      };
    });
  }, []);

  const removeWorker = useCallback((agentId: string) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      const newAgents = prev.agents.filter((w) => w.agentId !== agentId);
      return {
        ...prev,
        agents: newAgents,
        totalAgents: newAgents.length,
      };
    });
    setAgentDetails((details) => {
      const newDetails = new Map(details);
      newDetails.delete(agentId);
      return newDetails;
    });
  }, []);

  const completeTeam = useCallback(() => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        status: 'completed',
        overallProgress: 100,
        completedAt: new Date().toISOString(),
      };
    });
  }, []);

  const failSwarm = useCallback(() => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        status: 'failed',
        completedAt: new Date().toISOString(),
      };
    });
  }, []);

  const resetSwarm = useCallback(() => {
    setTeamStatus(null);
    setSelectedWorkerId(null);
    setAgentDetails(new Map());
    setIsDrawerOpen(false);
    setMockMessages([]);
  }, []);

  // ---------------------------------------------------------------------------
  // Worker Actions
  // ---------------------------------------------------------------------------

  const setAgentMemberStatus = useCallback((agentId: string, status: AgentMemberStatus) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        agents: prev.agents.map((w) =>
          w.agentId === agentId
            ? { ...w, status, startedAt: status === 'running' ? new Date().toISOString() : w.startedAt }
            : w
        ),
      };
    });
    setAgentDetails((details) => {
      const detail = details.get(agentId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(agentId, { ...detail, status });
      return newDetails;
    });
  }, []);

  const setWorkerProgress = useCallback((agentId: string, progress: number) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      const newAgents = prev.agents.map((w) =>
        w.agentId === agentId ? { ...w, progress, status: 'running' as AgentMemberStatus } : w
      );
      const totalProgress = newAgents.reduce((sum, w) => sum + w.progress, 0);
      const overallProgress = Math.round(totalProgress / newAgents.length);
      return {
        ...prev,
        agents: newAgents,
        overallProgress,
      };
    });
    setAgentDetails((details) => {
      const detail = details.get(agentId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(agentId, { ...detail, progress, status: 'running' });
      return newDetails;
    });
  }, []);

  const addThinking = useCallback((agentId: string, content: string) => {
    setAgentMemberStatus(agentId, 'running');
    setAgentDetails((details) => {
      const detail = details.get(agentId);
      if (!detail) return details;
      const thinking: ThinkingContent = {
        content,
        timestamp: new Date().toISOString(),
        tokenCount: Math.ceil(content.length / 4),
      };
      const newDetails = new Map(details);
      newDetails.set(agentId, {
        ...detail,
        thinkingHistory: [...detail.thinkingHistory, thinking],
      });
      return newDetails;
    });
  }, [setAgentMemberStatus]);

  const addToolCall = useCallback(
    (agentId: string, toolName: string, status: ToolCallInfo['status'] = 'running') => {
      setTeamStatus((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          agents: prev.agents.map((w) =>
            w.agentId === agentId
              ? { ...w, toolCallsCount: w.toolCallsCount + 1, currentAction: `Calling ${toolName}...` }
              : w
          ),
        };
      });
      setAgentDetails((details) => {
        const detail = details.get(agentId);
        if (!detail) return details;
        const toolCall: ToolCallInfo = {
          toolCallId: `tc-${generateId()}`,
          toolName,
          status,
          inputArgs: { mock: true },
          startedAt: new Date().toISOString(),
        };
        const newDetails = new Map(details);
        newDetails.set(agentId, {
          ...detail,
          toolCalls: [...detail.toolCalls, toolCall],
        });
        return newDetails;
      });
    },
    []
  );

  const addMessage = useCallback(
    (agentId: string, role: AgentMessage['role'], content: string) => {
      setAgentDetails((details) => {
        const detail = details.get(agentId);
        if (!detail) return details;
        const message: AgentMessage = {
          role,
          content,
          timestamp: new Date().toISOString(),
        };
        const newDetails = new Map(details);
        newDetails.set(agentId, {
          ...detail,
          messages: [...detail.messages, message],
        });
        return newDetails;
      });
    },
    []
  );

  const completeAgent = useCallback((agentId: string) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      const newAgents = prev.agents.map((w) =>
        w.agentId === agentId
          ? { ...w, status: 'completed' as AgentMemberStatus, progress: 100, completedAt: new Date().toISOString() }
          : w
      );
      const totalProgress = newAgents.reduce((sum, w) => sum + w.progress, 0);
      const overallProgress = Math.round(totalProgress / newAgents.length);
      return {
        ...prev,
        agents: newAgents,
        overallProgress,
      };
    });
    setAgentDetails((details) => {
      const detail = details.get(agentId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(agentId, {
        ...detail,
        status: 'completed',
        progress: 100,
        completedAt: new Date().toISOString(),
      });
      return newDetails;
    });
  }, []);

  const failWorker = useCallback((agentId: string, error: string) => {
    setTeamStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        agents: prev.agents.map((w) =>
          w.agentId === agentId
            ? { ...w, status: 'failed' as AgentMemberStatus, completedAt: new Date().toISOString() }
            : w
        ),
      };
    });
    setAgentDetails((details) => {
      const detail = details.get(agentId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(agentId, {
        ...detail,
        status: 'failed',
        error,
        completedAt: new Date().toISOString(),
      });
      return newDetails;
    });
  }, []);

  // ---------------------------------------------------------------------------
  // UI Actions
  // ---------------------------------------------------------------------------

  const selectWorker = useCallback((agentId: string | null) => {
    setSelectedWorkerId(agentId);
    if (agentId) {
      setIsDrawerOpen(true);
    }
  }, []);

  const openDrawer = useCallback(() => setIsDrawerOpen(true), []);
  const closeDrawer = useCallback(() => {
    setIsDrawerOpen(false);
    setSelectedWorkerId(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Mock Chat
  // ---------------------------------------------------------------------------

  const addMockUserMessage = useCallback((content: string) => {
    setMockMessages((prev) => [
      ...prev,
      { id: generateId(), role: 'user', content, timestamp: new Date().toISOString() },
    ]);
  }, []);

  const addMockAssistantMessage = useCallback((content: string) => {
    setMockMessages((prev) => [
      ...prev,
      { id: generateId(), role: 'assistant', content, timestamp: new Date().toISOString() },
    ]);
  }, []);

  // ---------------------------------------------------------------------------
  // Preset Scenarios
  // ---------------------------------------------------------------------------

  const loadScenario = useCallback(
    (
      scenario: typeof ETL_SCENARIO
    ) => {
      // Reset first
      resetSwarm();

      // Create swarm
      const newSwarm = createMockSwarm(scenario.swarmConfig);
      newSwarm.status = 'executing';
      newSwarm.startedAt = new Date().toISOString();

      // Add agents
      const agents: UIAgentSummary[] = [];
      const details = new Map<string, AgentDetail>();

      scenario.agents.forEach((w, index) => {
        const worker = createMockAgent(w.name, w.type, w.role, index);
        agents.push(worker);
        details.set(worker.agentId, createEmptyAgentDetail(worker));
      });

      newSwarm.agents = agents;
      newSwarm.totalAgents = agents.length;

      // Add mock messages
      const messages: MockMessage[] = scenario.messages.map((m) => ({
        id: generateId(),
        role: m.role,
        content: m.content,
        timestamp: new Date().toISOString(),
      }));

      // Set first worker as running with some progress
      if (agents.length > 0) {
        agents[0].status = 'running';
        agents[0].progress = 35;
        agents[0].startedAt = new Date().toISOString();

        // Add thinking content to first worker
        const firstAgentDetail = details.get(agents[0].agentId);
        if (firstAgentDetail) {
          firstAgentDetail.status = 'running';
          firstAgentDetail.progress = 35;
          firstAgentDetail.thinkingHistory = [
            {
              content: scenario.thinkingContent,
              timestamp: new Date().toISOString(),
              tokenCount: Math.ceil(scenario.thinkingContent.length / 4),
            },
          ];
          details.set(agents[0].agentId, firstAgentDetail);
        }

        // Calculate overall progress
        newSwarm.overallProgress = Math.round(
          agents.reduce((sum, w) => sum + w.progress, 0) / agents.length
        );
      }

      setTeamStatus(newSwarm);
      setAgentDetails(details);
      setMockMessages(messages);
    },
    [resetSwarm]
  );

  const loadETLScenario = useCallback(() => loadScenario(ETL_SCENARIO), [loadScenario]);
  const loadSecurityAuditScenario = useCallback(() => loadScenario(SECURITY_AUDIT_SCENARIO), [loadScenario]);
  const loadDataPipelineScenario = useCallback(() => loadScenario(DATA_PIPELINE_SCENARIO), [loadScenario]);

  // ---------------------------------------------------------------------------
  // Return
  // ---------------------------------------------------------------------------

  const selectedAgentDetail = selectedAgentId
    ? workerDetails.get(selectedAgentId) || null
    : null;

  return {
    // State
    agentTeamStatus,
    selectedAgentId,
    selectedAgentDetail,
    isDrawerOpen,
    mockMessages,

    // Swarm Actions
    createSwarm,
    addAgent,
    removeWorker,
    completeTeam,
    failSwarm,
    resetSwarm,

    // Worker Actions
    setAgentMemberStatus,
    setWorkerProgress,
    addThinking,
    addToolCall,
    addMessage,
    completeAgent,
    failWorker,

    // UI Actions
    selectWorker,
    openDrawer,
    closeDrawer,

    // Mock Chat
    addMockUserMessage,
    addMockAssistantMessage,

    // Preset Scenarios
    loadETLScenario,
    loadSecurityAuditScenario,
    loadDataPipelineScenario,
  };
};

export default useSwarmMock;
