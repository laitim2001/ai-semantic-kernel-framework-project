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
  UIAgentSwarmStatus,
  UIWorkerSummary,
  WorkerDetail,
  WorkerType,
  WorkerStatus,
  SwarmMode,
  ThinkingContent,
  ToolCallInfo,
  WorkerMessage,
} from '@/components/unified-chat/agent-swarm/types';

// =============================================================================
// Types
// =============================================================================

interface MockSwarmConfig {
  mode?: SwarmMode;
  workerCount?: number;
  workerTypes?: WorkerType[];
}

interface UseSwarmMockReturn {
  // State
  swarmStatus: UIAgentSwarmStatus | null;
  selectedWorkerId: string | null;
  selectedWorkerDetail: WorkerDetail | null;
  isDrawerOpen: boolean;
  mockMessages: MockMessage[];

  // Swarm Actions
  createSwarm: (config?: MockSwarmConfig) => void;
  addWorker: (name: string, type: WorkerType, role: string) => void;
  removeWorker: (workerId: string) => void;
  completeSwarm: () => void;
  failSwarm: () => void;
  resetSwarm: () => void;

  // Worker Actions
  setWorkerStatus: (workerId: string, status: WorkerStatus) => void;
  setWorkerProgress: (workerId: string, progress: number) => void;
  addThinking: (workerId: string, content: string) => void;
  addToolCall: (workerId: string, toolName: string, status?: ToolCallInfo['status']) => void;
  addMessage: (workerId: string, role: WorkerMessage['role'], content: string) => void;
  completeWorker: (workerId: string) => void;
  failWorker: (workerId: string, error: string) => void;

  // UI Actions
  selectWorker: (workerId: string | null) => void;
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

const createMockWorker = (
  name: string,
  type: WorkerType,
  role: string,
  index: number
): UIWorkerSummary => ({
  workerId: `worker-${index}-${generateId()}`,
  workerName: name,
  workerType: type,
  role,
  status: 'pending',
  progress: 0,
  toolCallsCount: 0,
  createdAt: new Date().toISOString(),
});

const createMockSwarm = (config: MockSwarmConfig = {}): UIAgentSwarmStatus => {
  const { mode = 'sequential' } = config;
  return {
    swarmId: `swarm-${generateId()}`,
    sessionId: `session-${generateId()}`,
    mode,
    status: 'initializing',
    totalWorkers: 0,
    overallProgress: 0,
    workers: [],
    createdAt: new Date().toISOString(),
    metadata: { mock: true },
  };
};

const createEmptyWorkerDetail = (worker: UIWorkerSummary): WorkerDetail => ({
  ...worker,
  taskId: `task-${generateId()}`,
  taskDescription: `執行 ${worker.workerName} 的任務`,
  thinkingHistory: [],
  toolCalls: [],
  messages: [],
});

// =============================================================================
// Preset Scenarios
// =============================================================================

const ETL_SCENARIO = {
  swarmConfig: { mode: 'sequential' as SwarmMode },
  workers: [
    { name: '診斷專家', type: 'claude_sdk' as WorkerType, role: 'Diagnostic' },
    { name: '修復專家', type: 'claude_sdk' as WorkerType, role: 'Remediation' },
    { name: '驗證專家', type: 'maf' as WorkerType, role: 'Verification' },
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
  swarmConfig: { mode: 'parallel' as SwarmMode },
  workers: [
    { name: '網路掃描', type: 'maf' as WorkerType, role: 'Network Scanner' },
    { name: '漏洞分析', type: 'claude_sdk' as WorkerType, role: 'Vulnerability Analyzer' },
    { name: '合規檢查', type: 'hybrid' as WorkerType, role: 'Compliance Checker' },
    { name: '報告生成', type: 'claude_sdk' as WorkerType, role: 'Report Generator' },
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
  swarmConfig: { mode: 'pipeline' as SwarmMode },
  workers: [
    { name: '數據提取', type: 'maf' as WorkerType, role: 'Data Extractor' },
    { name: '數據清洗', type: 'claude_sdk' as WorkerType, role: 'Data Cleaner' },
    { name: '數據轉換', type: 'claude_sdk' as WorkerType, role: 'Data Transformer' },
    { name: '數據載入', type: 'maf' as WorkerType, role: 'Data Loader' },
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
  const [swarmStatus, setSwarmStatus] = useState<UIAgentSwarmStatus | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<string | null>(null);
  const [workerDetails, setWorkerDetails] = useState<Map<string, WorkerDetail>>(new Map());
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [mockMessages, setMockMessages] = useState<MockMessage[]>([]);

  // ---------------------------------------------------------------------------
  // Swarm Actions
  // ---------------------------------------------------------------------------

  const createSwarm = useCallback((config: MockSwarmConfig = {}) => {
    const newSwarm = createMockSwarm(config);
    newSwarm.status = 'executing';
    newSwarm.startedAt = new Date().toISOString();
    setSwarmStatus(newSwarm);
    setWorkerDetails(new Map());
    setMockMessages([]);
  }, []);

  const addWorker = useCallback((name: string, type: WorkerType, role: string) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      const newWorker = createMockWorker(name, type, role, prev.workers.length);
      const detail = createEmptyWorkerDetail(newWorker);
      setWorkerDetails((details) => new Map(details).set(newWorker.workerId, detail));
      return {
        ...prev,
        workers: [...prev.workers, newWorker],
        totalWorkers: prev.workers.length + 1,
      };
    });
  }, []);

  const removeWorker = useCallback((workerId: string) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      const newWorkers = prev.workers.filter((w) => w.workerId !== workerId);
      return {
        ...prev,
        workers: newWorkers,
        totalWorkers: newWorkers.length,
      };
    });
    setWorkerDetails((details) => {
      const newDetails = new Map(details);
      newDetails.delete(workerId);
      return newDetails;
    });
  }, []);

  const completeSwarm = useCallback(() => {
    setSwarmStatus((prev) => {
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
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        status: 'failed',
        completedAt: new Date().toISOString(),
      };
    });
  }, []);

  const resetSwarm = useCallback(() => {
    setSwarmStatus(null);
    setSelectedWorkerId(null);
    setWorkerDetails(new Map());
    setIsDrawerOpen(false);
    setMockMessages([]);
  }, []);

  // ---------------------------------------------------------------------------
  // Worker Actions
  // ---------------------------------------------------------------------------

  const setWorkerStatus = useCallback((workerId: string, status: WorkerStatus) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        workers: prev.workers.map((w) =>
          w.workerId === workerId
            ? { ...w, status, startedAt: status === 'running' ? new Date().toISOString() : w.startedAt }
            : w
        ),
      };
    });
    setWorkerDetails((details) => {
      const detail = details.get(workerId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(workerId, { ...detail, status });
      return newDetails;
    });
  }, []);

  const setWorkerProgress = useCallback((workerId: string, progress: number) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      const newWorkers = prev.workers.map((w) =>
        w.workerId === workerId ? { ...w, progress, status: 'running' as WorkerStatus } : w
      );
      const totalProgress = newWorkers.reduce((sum, w) => sum + w.progress, 0);
      const overallProgress = Math.round(totalProgress / newWorkers.length);
      return {
        ...prev,
        workers: newWorkers,
        overallProgress,
      };
    });
    setWorkerDetails((details) => {
      const detail = details.get(workerId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(workerId, { ...detail, progress, status: 'running' });
      return newDetails;
    });
  }, []);

  const addThinking = useCallback((workerId: string, content: string) => {
    setWorkerStatus(workerId, 'running');
    setWorkerDetails((details) => {
      const detail = details.get(workerId);
      if (!detail) return details;
      const thinking: ThinkingContent = {
        content,
        timestamp: new Date().toISOString(),
        tokenCount: Math.ceil(content.length / 4),
      };
      const newDetails = new Map(details);
      newDetails.set(workerId, {
        ...detail,
        thinkingHistory: [...detail.thinkingHistory, thinking],
      });
      return newDetails;
    });
  }, [setWorkerStatus]);

  const addToolCall = useCallback(
    (workerId: string, toolName: string, status: ToolCallInfo['status'] = 'running') => {
      setSwarmStatus((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          workers: prev.workers.map((w) =>
            w.workerId === workerId
              ? { ...w, toolCallsCount: w.toolCallsCount + 1, currentAction: `Calling ${toolName}...` }
              : w
          ),
        };
      });
      setWorkerDetails((details) => {
        const detail = details.get(workerId);
        if (!detail) return details;
        const toolCall: ToolCallInfo = {
          toolCallId: `tc-${generateId()}`,
          toolName,
          status,
          inputArgs: { mock: true },
          startedAt: new Date().toISOString(),
        };
        const newDetails = new Map(details);
        newDetails.set(workerId, {
          ...detail,
          toolCalls: [...detail.toolCalls, toolCall],
        });
        return newDetails;
      });
    },
    []
  );

  const addMessage = useCallback(
    (workerId: string, role: WorkerMessage['role'], content: string) => {
      setWorkerDetails((details) => {
        const detail = details.get(workerId);
        if (!detail) return details;
        const message: WorkerMessage = {
          role,
          content,
          timestamp: new Date().toISOString(),
        };
        const newDetails = new Map(details);
        newDetails.set(workerId, {
          ...detail,
          messages: [...detail.messages, message],
        });
        return newDetails;
      });
    },
    []
  );

  const completeWorker = useCallback((workerId: string) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      const newWorkers = prev.workers.map((w) =>
        w.workerId === workerId
          ? { ...w, status: 'completed' as WorkerStatus, progress: 100, completedAt: new Date().toISOString() }
          : w
      );
      const totalProgress = newWorkers.reduce((sum, w) => sum + w.progress, 0);
      const overallProgress = Math.round(totalProgress / newWorkers.length);
      return {
        ...prev,
        workers: newWorkers,
        overallProgress,
      };
    });
    setWorkerDetails((details) => {
      const detail = details.get(workerId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(workerId, {
        ...detail,
        status: 'completed',
        progress: 100,
        completedAt: new Date().toISOString(),
      });
      return newDetails;
    });
  }, []);

  const failWorker = useCallback((workerId: string, error: string) => {
    setSwarmStatus((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        workers: prev.workers.map((w) =>
          w.workerId === workerId
            ? { ...w, status: 'failed' as WorkerStatus, completedAt: new Date().toISOString() }
            : w
        ),
      };
    });
    setWorkerDetails((details) => {
      const detail = details.get(workerId);
      if (!detail) return details;
      const newDetails = new Map(details);
      newDetails.set(workerId, {
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

  const selectWorker = useCallback((workerId: string | null) => {
    setSelectedWorkerId(workerId);
    if (workerId) {
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

      // Add workers
      const workers: UIWorkerSummary[] = [];
      const details = new Map<string, WorkerDetail>();

      scenario.workers.forEach((w, index) => {
        const worker = createMockWorker(w.name, w.type, w.role, index);
        workers.push(worker);
        details.set(worker.workerId, createEmptyWorkerDetail(worker));
      });

      newSwarm.workers = workers;
      newSwarm.totalWorkers = workers.length;

      // Add mock messages
      const messages: MockMessage[] = scenario.messages.map((m) => ({
        id: generateId(),
        role: m.role,
        content: m.content,
        timestamp: new Date().toISOString(),
      }));

      // Set first worker as running with some progress
      if (workers.length > 0) {
        workers[0].status = 'running';
        workers[0].progress = 35;
        workers[0].startedAt = new Date().toISOString();

        // Add thinking content to first worker
        const firstWorkerDetail = details.get(workers[0].workerId);
        if (firstWorkerDetail) {
          firstWorkerDetail.status = 'running';
          firstWorkerDetail.progress = 35;
          firstWorkerDetail.thinkingHistory = [
            {
              content: scenario.thinkingContent,
              timestamp: new Date().toISOString(),
              tokenCount: Math.ceil(scenario.thinkingContent.length / 4),
            },
          ];
          details.set(workers[0].workerId, firstWorkerDetail);
        }

        // Calculate overall progress
        newSwarm.overallProgress = Math.round(
          workers.reduce((sum, w) => sum + w.progress, 0) / workers.length
        );
      }

      setSwarmStatus(newSwarm);
      setWorkerDetails(details);
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

  const selectedWorkerDetail = selectedWorkerId
    ? workerDetails.get(selectedWorkerId) || null
    : null;

  return {
    // State
    swarmStatus,
    selectedWorkerId,
    selectedWorkerDetail,
    isDrawerOpen,
    mockMessages,

    // Swarm Actions
    createSwarm,
    addWorker,
    removeWorker,
    completeSwarm,
    failSwarm,
    resetSwarm,

    // Worker Actions
    setWorkerStatus,
    setWorkerProgress,
    addThinking,
    addToolCall,
    addMessage,
    completeWorker,
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
