/**
 * AgenticChatDemo - Agentic Chat Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 1: Agentic Chat with message streaming.
 */

import { FC, useState, useCallback } from 'react';
import { ChatContainer } from '@/components/ag-ui/chat';
import type { ChatMessage, PendingApproval } from '@/types/ag-ui';
import type { EventLogEntry } from './EventLogPanel';

export interface AgenticChatDemoProps {
  /** Thread ID for the demo */
  threadId: string;
  /** API base URL */
  apiUrl?: string;
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * AgenticChatDemo Component
 *
 * Interactive demo of the Agentic Chat feature.
 */
export const AgenticChatDemo: FC<AgenticChatDemoProps> = ({
  threadId,
  apiUrl,
  onEvent,
  className = '',
}) => {
  const [lastMessage, setLastMessage] = useState<ChatMessage | null>(null);
  const [approvalCount, setApprovalCount] = useState(0);

  // Handle message sent
  const handleMessageSent = useCallback((message: ChatMessage) => {
    setLastMessage(message);
    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'TEXT_MESSAGE_START',
      timestamp: new Date().toISOString(),
      data: { role: message.role, content: message.content.slice(0, 100) },
    });
  }, [onEvent]);

  // Handle approval required
  const handleApprovalRequired = useCallback((approval: PendingApproval) => {
    setApprovalCount((prev) => prev + 1);
    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'CUSTOM',
      timestamp: new Date().toISOString(),
      data: { event_name: 'APPROVAL_REQUIRED', tool_name: approval.toolName },
    });
  }, [onEvent]);

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="agentic-chat-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 1: Agentic Chat</h3>
        <p className="text-sm text-gray-500">
          Interactive chat with AI agent. Messages are streamed in real-time.
        </p>
      </div>

      {/* Stats */}
      <div className="flex gap-4 mb-4 text-sm">
        <div className="px-3 py-1.5 bg-gray-100 rounded">
          <span className="text-gray-500">Last Message:</span>{' '}
          <span className="font-medium">
            {lastMessage ? lastMessage.role : 'None'}
          </span>
        </div>
        <div className="px-3 py-1.5 bg-gray-100 rounded">
          <span className="text-gray-500">Approvals:</span>{' '}
          <span className="font-medium">{approvalCount}</span>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 min-h-0">
        <ChatContainer
          threadId={threadId}
          apiUrl={apiUrl}
          mode="chat"
          onMessageSent={handleMessageSent}
          onApprovalRequired={handleApprovalRequired}
          showStatus
          debug={false}
        />
      </div>

      {/* Tips */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
        <strong>Tips:</strong> Try asking about weather, calculations, or request a tool call
        to see streaming in action.
      </div>
    </div>
  );
};

export default AgenticChatDemo;
