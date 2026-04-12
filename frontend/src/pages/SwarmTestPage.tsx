/**
 * SwarmTestPage - Agent Swarm Visualization Test Page
 *
 * Standalone test page for Phase 29 Agent Swarm UI components.
 * Supports both Mock mode (for UI testing) and Real mode (connected to backend).
 *
 * Route: /swarm-test
 * Phase 29: Agent Swarm Visualization Testing
 */

import { FC, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import {
  Play,
  RotateCcw,
  UserPlus,
  Brain,
  Wrench,
  MessageSquare,
  CheckCircle,
  XCircle,
  Loader2,
  Send,
  Zap,
  Shield,
  Database,
  ChevronDown,
  ChevronRight,
  Wifi,
  WifiOff,
  Radio,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import {
  AgentTeamPanel,
  AgentDetailDrawer,
} from '@/components/unified-chat/agent-team';
import { useSwarmMock, type MockMessage } from '@/hooks/useSwarmMock';
import { useSwarmReal } from '@/hooks/useSwarmReal';
import type { AgentType, AgentMemberStatus, UIAgentSummary } from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Types
// =============================================================================

type TestMode = 'mock' | 'real';

interface ControlSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

// =============================================================================
// Sub-Components
// =============================================================================

const ControlSection: FC<ControlSectionProps> = ({
  title,
  icon,
  children,
  defaultOpen = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span>{title}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
      </button>
      {isOpen && <div className="p-3 border-t bg-gray-50/50">{children}</div>}
    </div>
  );
};

const MockMessageItem: FC<{ message: MockMessage }> = ({ message }) => {
  const isUser = message.role === 'user';
  return (
    <div
      className={cn(
        'p-3 rounded-lg text-sm',
        isUser ? 'bg-blue-100 ml-8' : 'bg-gray-100 mr-8'
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={cn('text-xs font-medium', isUser ? 'text-blue-700' : 'text-gray-700')}>
          {isUser ? '👤 User' : '🤖 Assistant'}
        </span>
        <span className="text-xs text-gray-400">
          {new Date(message.timestamp).toLocaleTimeString()}
        </span>
      </div>
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  );
};

const ModeSwitch: FC<{
  mode: TestMode;
  onModeChange: (mode: TestMode) => void;
  isConnected: boolean;
}> = ({ mode, onModeChange, isConnected }) => (
  <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
    <button
      onClick={() => onModeChange('mock')}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
        mode === 'mock'
          ? 'bg-white text-indigo-700 shadow-sm'
          : 'text-gray-600 hover:text-gray-900'
      )}
    >
      <WifiOff className="w-3.5 h-3.5" />
      Mock
    </button>
    <button
      onClick={() => onModeChange('real')}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
        mode === 'real'
          ? 'bg-white text-green-700 shadow-sm'
          : 'text-gray-600 hover:text-gray-900'
      )}
    >
      {isConnected ? (
        <Wifi className="w-3.5 h-3.5 text-green-500" />
      ) : (
        <Radio className="w-3.5 h-3.5" />
      )}
      Real
    </button>
  </div>
);

// =============================================================================
// Main Component
// =============================================================================

export const SwarmTestPage: FC = () => {
  // Test Mode State
  const [testMode, setTestMode] = useState<TestMode>('mock');

  // Mock Hook
  const mockHook = useSwarmMock();

  // Real Hook
  const realHook = useSwarmReal();

  // Choose which hook to use based on mode
  const {
    agentTeamStatus,
    selectedAgentId,
    selectedAgentDetail,
    isDrawerOpen,
    mockMessages,
    selectWorker,
    closeDrawer,
  } = testMode === 'mock' ? mockHook : realHook;

  // Local state for inputs
  const [chatInput, setChatInput] = useState('');
  const [newWorkerName, setNewWorkerName] = useState('');
  const [newAgentType, setNewAgentType] = useState<AgentType>('claude_sdk');
  const [newWorkerRole, setNewWorkerRole] = useState('');
  const [selectedControlWorkerId, setSelectedControlWorkerId] = useState<string | null>(null);
  const [thinkingInput, setThinkingInput] = useState('');
  const [toolNameInput, setToolNameInput] = useState('');
  const [selectedScenario, setSelectedScenario] = useState<string>('security_audit');
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1.0);

  // Get selected worker for controls
  const selectedControlWorker = agentTeamStatus?.workers.find(
    (w) => w.agentId === selectedControlWorkerId
  );

  // Mode change handler
  const handleModeChange = useCallback((newMode: TestMode) => {
    if (newMode === 'mock') {
      mockHook.resetSwarm();
    } else {
      realHook.reset();
    }
    setTestMode(newMode);
  }, [mockHook, realHook]);

  // Handlers for Mock Mode
  const handleSendMessage = useCallback(() => {
    if (!chatInput.trim()) return;
    if (testMode === 'mock') {
      mockHook.addMockUserMessage(chatInput);
      setChatInput('');
      setTimeout(() => {
        mockHook.addMockAssistantMessage('收到您的訊息，正在處理中...');
      }, 500);
    } else {
      realHook.addMockUserMessage(chatInput);
      setChatInput('');
    }
  }, [chatInput, testMode, mockHook, realHook]);

  const handleAddWorker = useCallback(() => {
    if (!newWorkerName.trim() || testMode !== 'mock') return;
    mockHook.addAgent(newWorkerName, newAgentType, newWorkerRole || 'Worker');
    setNewWorkerName('');
    setNewWorkerRole('');
  }, [newWorkerName, newAgentType, newWorkerRole, mockHook, testMode]);

  const handleWorkerClick = useCallback(
    (worker: UIAgentSummary) => {
      selectWorker(worker.agentId);
    },
    [selectWorker]
  );

  const handleAddThinking = useCallback(() => {
    if (!selectedControlWorkerId || !thinkingInput.trim() || testMode !== 'mock') return;
    mockHook.addThinking(selectedControlWorkerId, thinkingInput);
    setThinkingInput('');
  }, [selectedControlWorkerId, thinkingInput, mockHook, testMode]);

  const handleAddToolCall = useCallback(() => {
    if (!selectedControlWorkerId || !toolNameInput.trim() || testMode !== 'mock') return;
    mockHook.addToolCall(selectedControlWorkerId, toolNameInput, 'running');
    setToolNameInput('');
  }, [selectedControlWorkerId, toolNameInput, mockHook, testMode]);

  // Handlers for Real Mode
  const handleStartRealDemo = useCallback(async () => {
    await realHook.startDemo({
      scenario: selectedScenario as 'security_audit' | 'etl_pipeline' | 'data_pipeline',
      mode: 'parallel',
      speed_multiplier: speedMultiplier,
    });
  }, [realHook, selectedScenario, speedMultiplier]);

  const handleStopRealDemo = useCallback(async () => {
    await realHook.stopDemo();
  }, [realHook]);

  return (
    <div className="flex h-full bg-gray-100">
      {/* Left: Control Panel */}
      <div className="w-80 bg-white border-r flex flex-col h-full overflow-hidden">
        <div className="px-4 py-3 border-b bg-gradient-to-r from-indigo-600 to-purple-600">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Swarm 測試控制台
          </h1>
          <p className="text-xs text-indigo-200 mt-1">Phase 29 UI Testing</p>
        </div>

        {/* Mode Switch */}
        <div className="px-3 py-2 border-b bg-gray-50">
          <ModeSwitch
            mode={testMode}
            onModeChange={handleModeChange}
            isConnected={realHook.isConnected}
          />
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* ============================================== */}
          {/* REAL MODE Controls */}
          {/* ============================================== */}
          {testMode === 'real' && (
            <>
              {/* Connection Status */}
              <div className={cn(
                'p-3 rounded-lg text-sm',
                realHook.isConnected ? 'bg-green-50 border border-green-200' :
                realHook.isCompleted ? 'bg-blue-50 border border-blue-200' :
                'bg-gray-50 border'
              )}>
                <div className="flex items-center gap-2">
                  {realHook.isConnected ? (
                    <>
                      <Wifi className="w-4 h-4 text-green-600" />
                      <span className="font-medium text-green-700">已連接</span>
                    </>
                  ) : realHook.isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="font-medium text-blue-700">連接中...</span>
                    </>
                  ) : realHook.isCompleted ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-blue-600" />
                      <span className="font-medium text-blue-700">演示已完成</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-600">未連接</span>
                    </>
                  )}
                </div>
                {realHook.error && (
                  <div className="flex items-center gap-1 mt-2 text-xs text-red-600">
                    <AlertCircle className="w-3 h-3" />
                    {realHook.error}
                  </div>
                )}
              </div>

              {/* Start Real Demo */}
              <ControlSection
                title="啟動真實演示"
                icon={<Play className="w-4 h-4 text-green-600" />}
              >
                <div className="space-y-3">
                  {/* Scenario Selection */}
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">選擇場景</label>
                    <select
                      className="w-full p-2 text-sm border rounded"
                      value={selectedScenario}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      disabled={realHook.isConnected || realHook.isLoading}
                    >
                      {realHook.scenarios.map((scenario) => (
                        <option key={scenario.id} value={scenario.id}>
                          {scenario.name} ({scenario.workers_count} Workers)
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Speed Multiplier */}
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">
                      速度倍率: {speedMultiplier.toFixed(1)}x
                    </label>
                    <input
                      type="range"
                      min="0.5"
                      max="5"
                      step="0.5"
                      value={speedMultiplier}
                      onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
                      disabled={realHook.isConnected || realHook.isLoading}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>0.5x (慢)</span>
                      <span>5x (快)</span>
                    </div>
                  </div>

                  {/* Selected Scenario Info */}
                  {selectedScenario && (
                    <div className="p-2 bg-blue-50 rounded text-xs text-blue-700">
                      {realHook.scenarios.find(s => s.id === selectedScenario)?.description}
                    </div>
                  )}

                  {/* Start/Stop Buttons */}
                  {!realHook.isConnected ? (
                    <Button
                      onClick={handleStartRealDemo}
                      disabled={realHook.isLoading}
                      className="w-full"
                    >
                      {realHook.isLoading ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4 mr-2" />
                      )}
                      啟動演示
                    </Button>
                  ) : (
                    <Button
                      variant="destructive"
                      onClick={handleStopRealDemo}
                      className="w-full"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      停止演示
                    </Button>
                  )}

                  {/* Reset Button */}
                  <Button
                    variant="outline"
                    onClick={() => realHook.reset()}
                    className="w-full"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    重置
                  </Button>
                </div>
              </ControlSection>

              {/* Backend Info */}
              <ControlSection
                title="後端資訊"
                icon={<Database className="w-4 h-4 text-blue-600" />}
                defaultOpen={false}
              >
                <div className="text-xs text-gray-600 space-y-1">
                  <div>API: {import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}</div>
                  <div>場景數量: {realHook.scenarios.length}</div>
                  {agentTeamStatus && (
                    <>
                      <div className="pt-2 border-t mt-2">
                        <div>Swarm ID: {agentTeamStatus.swarmId}</div>
                        <div>狀態: {agentTeamStatus.status}</div>
                        <div>進度: {agentTeamStatus.overallProgress}%</div>
                      </div>
                    </>
                  )}
                </div>
              </ControlSection>
            </>
          )}

          {/* ============================================== */}
          {/* MOCK MODE Controls */}
          {/* ============================================== */}
          {testMode === 'mock' && (
            <>
              {/* Preset Scenarios */}
              <ControlSection
                title="預設場景"
                icon={<Database className="w-4 h-4 text-green-600" />}
              >
                <div className="space-y-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={mockHook.loadETLScenario}
                    className="w-full justify-start"
                  >
                    <Wrench className="w-4 h-4 mr-2" />
                    ETL 故障診斷
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={mockHook.loadSecurityAuditScenario}
                    className="w-full justify-start"
                  >
                    <Shield className="w-4 h-4 mr-2" />
                    安全審計
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={mockHook.loadDataPipelineScenario}
                    className="w-full justify-start"
                  >
                    <Database className="w-4 h-4 mr-2" />
                    數據管線
                  </Button>
                </div>
              </ControlSection>

              {/* Swarm Controls */}
              <ControlSection
                title="Swarm 控制"
                icon={<Play className="w-4 h-4 text-blue-600" />}
              >
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => mockHook.createSwarm({ mode: 'sequential' })}
                      disabled={!!agentTeamStatus}
                      className="flex-1"
                    >
                      <Play className="w-4 h-4 mr-1" />
                      建立
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={mockHook.resetSwarm}
                      disabled={!agentTeamStatus}
                    >
                      <RotateCcw className="w-4 h-4" />
                    </Button>
                  </div>
                  {agentTeamStatus && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={mockHook.completeTeam}
                        className="flex-1"
                      >
                        <CheckCircle className="w-4 h-4 mr-1 text-green-500" />
                        完成
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={mockHook.failSwarm}
                        className="flex-1"
                      >
                        <XCircle className="w-4 h-4 mr-1 text-red-500" />
                        失敗
                      </Button>
                    </div>
                  )}
                  {agentTeamStatus && (
                    <div className="text-xs text-gray-500 p-2 bg-gray-50 rounded">
                      <div>ID: {agentTeamStatus.swarmId.slice(0, 15)}...</div>
                      <div>模式: {agentTeamStatus.mode}</div>
                      <div>狀態: {agentTeamStatus.status}</div>
                      <div>進度: {agentTeamStatus.overallProgress}%</div>
                    </div>
                  )}
                </div>
              </ControlSection>

              {/* Add Worker */}
              <ControlSection
                title="新增 Worker"
                icon={<UserPlus className="w-4 h-4 text-purple-600" />}
                defaultOpen={!!agentTeamStatus}
              >
                <div className="space-y-2">
                  <Input
                    placeholder="Worker 名稱"
                    value={newWorkerName}
                    onChange={(e) => setNewWorkerName(e.target.value)}
                    disabled={!agentTeamStatus}
                  />
                  <select
                    className="w-full p-2 text-sm border rounded"
                    value={newAgentType}
                    onChange={(e) => setNewAgentType(e.target.value as AgentType)}
                    disabled={!agentTeamStatus}
                  >
                    <option value="claude_sdk">Claude SDK</option>
                    <option value="maf">MAF</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="research">Research</option>
                  </select>
                  <Input
                    placeholder="角色 (可選)"
                    value={newWorkerRole}
                    onChange={(e) => setNewWorkerRole(e.target.value)}
                    disabled={!agentTeamStatus}
                  />
                  <Button
                    size="sm"
                    onClick={handleAddWorker}
                    disabled={!agentTeamStatus || !newWorkerName.trim()}
                    className="w-full"
                  >
                    <UserPlus className="w-4 h-4 mr-1" />
                    新增 Worker
                  </Button>
                </div>
              </ControlSection>

              {/* Worker Controls */}
              {agentTeamStatus && agentTeamStatus.workers.length > 0 && (
                <ControlSection
                  title="Worker 控制"
                  icon={<Wrench className="w-4 h-4 text-orange-600" />}
                >
                  <div className="space-y-2">
                    {/* Worker Selector */}
                    <select
                      className="w-full p-2 text-sm border rounded"
                      value={selectedControlWorkerId || ''}
                      onChange={(e) => setSelectedControlWorkerId(e.target.value || null)}
                    >
                      <option value="">選擇 Worker...</option>
                      {agentTeamStatus.workers.map((w) => (
                        <option key={w.agentId} value={w.agentId}>
                          {w.agentName} ({w.status})
                        </option>
                      ))}
                    </select>

                    {selectedControlWorker && (
                      <>
                        {/* Status Controls */}
                        <div className="flex gap-1 flex-wrap">
                          {(['pending', 'running', 'paused'] as AgentMemberStatus[]).map((status) => (
                            <Button
                              key={status}
                              size="sm"
                              variant={selectedControlWorker.status === status ? 'default' : 'outline'}
                              onClick={() => mockHook.setAgentMemberStatus(selectedControlWorkerId!, status)}
                              className="text-xs px-2 py-1"
                            >
                              {status}
                            </Button>
                          ))}
                        </div>

                        {/* Progress Slider */}
                        <div className="space-y-1">
                          <label className="text-xs text-gray-500">
                            進度: {selectedControlWorker.progress}%
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={selectedControlWorker.progress}
                            onChange={(e) =>
                              mockHook.setWorkerProgress(selectedControlWorkerId!, parseInt(e.target.value))
                            }
                            className="w-full"
                          />
                        </div>

                        {/* Thinking Input */}
                        <div className="space-y-1">
                          <label className="text-xs text-gray-500 flex items-center gap-1">
                            <Brain className="w-3 h-3" /> 思考內容
                          </label>
                          <textarea
                            className="w-full p-2 text-sm border rounded resize-none"
                            rows={2}
                            placeholder="輸入思考內容..."
                            value={thinkingInput}
                            onChange={(e) => setThinkingInput(e.target.value)}
                          />
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleAddThinking}
                            disabled={!thinkingInput.trim()}
                            className="w-full"
                          >
                            <Brain className="w-4 h-4 mr-1" />
                            新增思考
                          </Button>
                        </div>

                        {/* Tool Call Input */}
                        <div className="space-y-1">
                          <label className="text-xs text-gray-500 flex items-center gap-1">
                            <Wrench className="w-3 h-3" /> 工具調用
                          </label>
                          <Input
                            placeholder="工具名稱 (e.g., query_adf_logs)"
                            value={toolNameInput}
                            onChange={(e) => setToolNameInput(e.target.value)}
                          />
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleAddToolCall}
                            disabled={!toolNameInput.trim()}
                            className="w-full"
                          >
                            <Wrench className="w-4 h-4 mr-1" />
                            新增工具調用
                          </Button>
                        </div>

                        {/* Complete/Fail Buttons */}
                        <div className="flex gap-2 pt-2 border-t">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => mockHook.completeAgent(selectedControlWorkerId!)}
                            className="flex-1"
                          >
                            <CheckCircle className="w-4 h-4 mr-1 text-green-500" />
                            完成
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => mockHook.failWorker(selectedControlWorkerId!, 'Mock error')}
                            className="flex-1"
                          >
                            <XCircle className="w-4 h-4 mr-1 text-red-500" />
                            失敗
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                </ControlSection>
              )}
            </>
          )}
        </div>
      </div>

      {/* Center: Mock Chat Area */}
      <div className="flex-1 flex flex-col bg-white min-w-0">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-blue-600" />
            <span className="font-semibold">
              {testMode === 'mock' ? '模擬對話' : '演示對話'}
            </span>
            <Badge variant="outline" className="text-xs">
              {mockMessages.length} 訊息
            </Badge>
            {testMode === 'real' && realHook.isConnected && (
              <Badge className="text-xs bg-green-100 text-green-700">
                <Wifi className="w-3 h-3 mr-1" />
                Live
              </Badge>
            )}
          </div>
          {agentTeamStatus && (
            <div className="flex items-center gap-2">
              <Badge
                className={cn(
                  'text-xs',
                  agentTeamStatus.status === 'executing' && 'bg-blue-100 text-blue-800',
                  agentTeamStatus.status === 'completed' && 'bg-green-100 text-green-800',
                  agentTeamStatus.status === 'failed' && 'bg-red-100 text-red-800'
                )}
              >
                {agentTeamStatus.status === 'executing' && (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                )}
                {agentTeamStatus.status}
              </Badge>
              <span className="text-sm text-gray-500">
                {agentTeamStatus.overallProgress}%
              </span>
            </div>
          )}
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {mockMessages.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">
                {testMode === 'mock'
                  ? '載入預設場景或手動發送訊息開始測試'
                  : '啟動演示以開始真實執行'}
              </p>
            </div>
          ) : (
            mockMessages.map((msg) => (
              <MockMessageItem key={msg.id} message={msg} />
            ))
          )}
        </div>

        {/* Chat Input */}
        <div className="p-4 border-t bg-gray-50">
          <div className="flex gap-2">
            <Input
              placeholder="輸入測試訊息..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              className="flex-1"
            />
            <Button onClick={handleSendMessage} disabled={!chatInput.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Right: Agent Swarm Panel */}
      <div className="w-96 border-l flex flex-col h-full overflow-hidden bg-gray-50">
        <div className="px-4 py-3 border-b bg-white">
          <h2 className="font-semibold text-gray-900">Orchestration Panel</h2>
          <p className="text-xs text-gray-500 mt-1">
            Phase 29 Agent Swarm Visualization
            {testMode === 'real' && realHook.isConnected && (
              <span className="ml-2 text-green-600">(Live)</span>
            )}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {/* Swarm Panel */}
          <Card className="shadow-sm">
            <CardContent className="p-0">
              <AgentTeamPanel
                agentTeamStatus={agentTeamStatus}
                onWorkerClick={handleWorkerClick}
                isLoading={testMode === 'real' && realHook.isLoading}
                className="border-0 shadow-none"
              />
            </CardContent>
          </Card>

          {/* Debug Info */}
          {agentTeamStatus && (
            <Card className="mt-3 shadow-sm">
              <CardHeader className="py-2 px-3">
                <CardTitle className="text-sm font-medium">Debug Info</CardTitle>
              </CardHeader>
              <CardContent className="p-3 text-xs text-gray-600 space-y-1">
                <div>Mode: <Badge variant="outline" className="text-xs ml-1">{testMode.toUpperCase()}</Badge></div>
                <div>Swarm ID: {agentTeamStatus.swarmId}</div>
                <div>Session ID: {agentTeamStatus.sessionId}</div>
                <div>Execution Mode: {agentTeamStatus.mode}</div>
                <div>Workers: {agentTeamStatus.totalWorkers}</div>
                <div>Progress: {agentTeamStatus.overallProgress}%</div>
                <div>Selected Worker: {selectedAgentId || 'None'}</div>
                <div>Drawer Open: {isDrawerOpen ? 'Yes' : 'No'}</div>
                {testMode === 'real' && (
                  <div>Connected: {realHook.isConnected ? 'Yes' : 'No'}</div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Worker Detail Drawer */}
      <AgentDetailDrawer
        open={isDrawerOpen}
        onClose={closeDrawer}
        swarmId={agentTeamStatus?.swarmId || ''}
        worker={
          agentTeamStatus?.workers.find((w) => w.agentId === selectedAgentId) || null
        }
        workerDetail={selectedAgentDetail}
      />
    </div>
  );
};

export default SwarmTestPage;
