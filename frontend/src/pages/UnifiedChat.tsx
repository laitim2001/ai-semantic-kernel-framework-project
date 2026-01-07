/**
 * UnifiedChat - Unified Agentic Chat Interface Page
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 * Phase 16: Unified Agentic Chat Interface
 *
 * Main page component for the unified chat interface.
 * Integrates Chat and Workflow modes with adaptive layout.
 */

import { FC, useState, useCallback, useMemo } from 'react';
import { ChatHeader } from '@/components/unified-chat/ChatHeader';
import { ChatInput } from '@/components/unified-chat/ChatInput';
import { StatusBar } from '@/components/unified-chat/StatusBar';
import type {
  UnifiedChatProps,
  ExecutionMode,
  ConnectionStatus,
  ExecutionMetrics,
} from '@/types/unified-chat';
import type { RiskLevel, ChatMessage } from '@/types/ag-ui';
import { cn } from '@/lib/utils';

// Default metrics for initial state
const defaultMetrics: ExecutionMetrics = {
  tokens: { used: 0, limit: 4000, percentage: 0 },
  time: { total: 0, isRunning: false },
  toolCallCount: 0,
  messageCount: 0,
};

/**
 * UnifiedChat Page Component
 *
 * Main unified chat interface with:
 * - Adaptive layout (Chat mode: full width, Workflow mode: with side panel)
 * - Mode toggle in header
 * - Chat area for messages
 * - Status bar at bottom
 */
// Simple ID generator for session/thread IDs
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

export const UnifiedChat: FC<UnifiedChatProps> = ({
  initialThreadId,
  initialSessionId,
  // Reserved for future AG-UI integration
  // tools = [],
  // apiUrl,
}) => {
  // Generate IDs if not provided
  const threadId = useMemo(() => initialThreadId || generateId(), [initialThreadId]);
  const sessionId = useMemo(() => initialSessionId || generateId(), [initialSessionId]);

  // Mode state (setAutoMode will be used when AG-UI events trigger mode detection)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [autoMode, _setAutoMode] = useState<ExecutionMode>('chat');
  const [manualOverride, setManualOverride] = useState<ExecutionMode | null>(null);
  const isManuallyOverridden = manualOverride !== null;

  // Connection state
  const [connection, setConnection] = useState<ConnectionStatus>('disconnected');

  // Message state (placeholder for S62-3)
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Metrics state (placeholder values)
  const [metrics, setMetrics] = useState<ExecutionMetrics>(defaultMetrics);

  // Risk state (placeholder - will be updated via AG-UI events)
  const [riskLevel] = useState<RiskLevel>('low');
  const [riskScore] = useState(0.15);

  // Checkpoint state (placeholder - will be updated via checkpoint API)
  const [hasCheckpoint] = useState(false);
  const [canRestore] = useState(false);

  // Handle mode change from header
  const handleModeChange = useCallback((mode: ExecutionMode) => {
    setManualOverride(mode);
  }, []);

  // Handle send message
  const handleSend = useCallback((content: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Update metrics
    setMetrics((prev) => ({
      ...prev,
      messageCount: prev.messageCount + 1,
    }));

    // Simulate streaming response (placeholder - will be replaced with real AG-UI integration)
    setIsStreaming(true);
    setConnection('connected');

    // Simulate AI response after delay
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Received your message: "${content}"\n\nThis is a placeholder response. The full AG-UI integration will be completed in Sprint 62-3.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsStreaming(false);
      setMetrics((prev) => ({
        ...prev,
        messageCount: prev.messageCount + 1,
        tokens: {
          ...prev.tokens,
          used: prev.tokens.used + content.length * 2,
          percentage: ((prev.tokens.used + content.length * 2) / prev.tokens.limit) * 100,
        },
      }));
    }, 1500);
  }, []);

  // Handle cancel streaming
  const handleCancel = useCallback(() => {
    setIsStreaming(false);
  }, []);

  // Handle checkpoint restore
  const handleRestore = useCallback(() => {
    console.log('Restore checkpoint triggered');
    // Placeholder - will be implemented with checkpoint integration
  }, []);

  // Determine effective mode
  const effectiveMode = manualOverride ?? autoMode;

  return (
    <div
      className="flex flex-col h-screen bg-gray-50"
      data-testid="unified-chat-page"
      data-thread-id={threadId}
      data-session-id={sessionId}
    >
      {/* Header */}
      <ChatHeader
        title="IPA Assistant"
        currentMode={effectiveMode}
        autoMode={autoMode}
        isManuallyOverridden={isManuallyOverridden}
        connection={connection}
        onModeChange={handleModeChange}
      />

      {/* Main Content Area */}
      <main className={cn('flex-1 flex overflow-hidden')}>
        {/* Chat Area */}
        <div
          className={cn(
            'flex-1 flex flex-col bg-white',
            effectiveMode === 'workflow' && 'border-r'
          )}
        >
          {/* Messages Area (Placeholder - to be replaced with ChatArea in S62-3) */}
          <div className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <div className="text-6xl mb-4">
                    {effectiveMode === 'chat' ? '💬' : '📋'}
                  </div>
                  <h2 className="text-xl font-medium text-gray-600 mb-2">
                    {effectiveMode === 'chat'
                      ? 'Start a conversation'
                      : 'Start a workflow'}
                  </h2>
                  <p className="text-sm text-gray-400 max-w-md">
                    {effectiveMode === 'chat'
                      ? 'Type a message below to begin chatting with the AI assistant.'
                      : 'Type a task description to start a multi-step workflow.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex',
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[70%] px-4 py-3 rounded-2xl',
                        message.role === 'user'
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                      )}
                    >
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                ))}
                {isStreaming && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-bl-sm px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" />
                        <div
                          className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                          style={{ animationDelay: '0.1s' }}
                        />
                        <div
                          className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                          style={{ animationDelay: '0.2s' }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Workflow Side Panel (Only visible in Workflow mode) */}
        {effectiveMode === 'workflow' && (
          <aside
            className="w-80 bg-gray-50 border-l overflow-y-auto"
            data-testid="workflow-side-panel-placeholder"
          >
            <div className="p-4">
              <h3 className="font-medium text-gray-700 mb-4">Workflow Progress</h3>
              <div className="text-sm text-gray-500 text-center py-8">
                <div className="text-4xl mb-2">📋</div>
                <p>Workflow panel will be implemented in S62-4</p>
              </div>
            </div>
          </aside>
        )}
      </main>

      {/* Input Area */}
      <ChatInput
        onSend={handleSend}
        isStreaming={isStreaming}
        onCancel={handleCancel}
        placeholder={
          effectiveMode === 'chat'
            ? 'Type a message...'
            : 'Describe your task...'
        }
      />

      {/* Status Bar */}
      <StatusBar
        mode={effectiveMode}
        modeSource={isManuallyOverridden ? 'manual' : 'auto'}
        riskLevel={riskLevel}
        riskScore={riskScore}
        metrics={metrics}
        hasCheckpoint={hasCheckpoint}
        canRestore={canRestore}
        onRestore={handleRestore}
      />
    </div>
  );
};

export default UnifiedChat;
