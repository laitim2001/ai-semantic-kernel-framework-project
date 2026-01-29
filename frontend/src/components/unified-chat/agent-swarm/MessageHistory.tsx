/**
 * MessageHistory Component
 *
 * Displays the conversation history for a Worker.
 * Sprint 103: WorkerDetailDrawer
 */

import { FC, useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/Collapsible';
import {
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Bot,
  User,
  Settings,
  Wrench,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkerMessage } from './types';

// =============================================================================
// Types
// =============================================================================

interface MessageHistoryProps {
  messages: WorkerMessage[];
  defaultExpanded?: boolean;
  maxPreviewLength?: number;
  className?: string;
}

type MessageRole = 'system' | 'user' | 'assistant' | 'tool';

// =============================================================================
// Constants
// =============================================================================

interface RoleConfig {
  icon: typeof Bot;
  color: string;
  bgColor: string;
  label: string;
}

const ROLE_CONFIG: Record<MessageRole, RoleConfig> = {
  system: {
    icon: Settings,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    label: 'System',
  },
  user: {
    icon: User,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    label: 'User',
  },
  assistant: {
    icon: Bot,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-950/30',
    label: 'Assistant',
  },
  tool: {
    icon: Wrench,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
    label: 'Tool',
  },
};

// =============================================================================
// Helper Components
// =============================================================================

interface MessageItemProps {
  message: WorkerMessage;
  maxPreviewLength: number;
}

const MessageItem: FC<MessageItemProps> = ({ message, maxPreviewLength }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const roleConfig = ROLE_CONFIG[message.role];
  const RoleIcon = roleConfig.icon;

  const needsTruncation = message.content.length > maxPreviewLength;
  const displayContent = isExpanded || !needsTruncation
    ? message.content
    : `${message.content.slice(0, maxPreviewLength)}...`;

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return '--:--:--';
    }
  };

  return (
    <div className={cn('rounded-md p-3', roleConfig.bgColor)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <RoleIcon className={cn('h-4 w-4', roleConfig.color)} />
          <Badge variant="outline" className="text-xs h-5">
            {roleConfig.label}
          </Badge>
          {message.toolCallId && (
            <span className="text-xs text-muted-foreground font-mono">
              {message.toolCallId}
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {/* Content */}
      <div className="text-sm whitespace-pre-wrap break-words">
        {displayContent}
      </div>

      {/* Expand/Collapse */}
      {needsTruncation && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs px-2 mt-2"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </Button>
      )}
    </div>
  );
};

// =============================================================================
// Component
// =============================================================================

/**
 * MessageHistory - Displays conversation history
 *
 * @param messages - Array of messages
 * @param defaultExpanded - Whether to expand by default
 * @param maxPreviewLength - Max characters before truncation
 * @param className - Additional CSS classes
 */
export const MessageHistory: FC<MessageHistoryProps> = ({
  messages,
  defaultExpanded = false,
  maxPreviewLength = 300,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  // Count messages by role
  const messageCounts = messages.reduce(
    (acc, msg) => {
      acc[msg.role] = (acc[msg.role] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className={cn('space-y-2', className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        {/* Header */}
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-2 h-auto hover:bg-accent"
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span>Message History ({messages.length})</span>
            </div>

            <div className="flex items-center gap-2">
              {/* Message counts */}
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                {messageCounts.assistant && (
                  <span className="text-green-600 dark:text-green-400">
                    {messageCounts.assistant} assistant
                  </span>
                )}
                {messageCounts.tool && (
                  <span className="text-orange-600 dark:text-orange-400">
                    {messageCounts.tool} tool
                  </span>
                )}
              </div>

              {isOpen ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>

        {/* Content */}
        <CollapsibleContent>
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground text-sm py-6 bg-muted/30 rounded-md">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No messages yet</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1 scrollbar-thin">
              {messages.map((message, index) => (
                <MessageItem
                  key={`${message.role}-${index}`}
                  message={message}
                  maxPreviewLength={maxPreviewLength}
                />
              ))}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
};

export default MessageHistory;
