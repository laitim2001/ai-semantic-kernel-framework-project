/**
 * ChatHeader - Unified Chat Header Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 * Sprint 65: Enhanced with ConnectionStatus component
 *
 * Header component with mode toggle, connection status, and settings.
 */

import { FC, useCallback } from 'react';
import { MessageSquare, Workflow, Settings } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ConnectionStatus } from './ConnectionStatus';
import type { ChatHeaderProps, ExecutionMode } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

/**
 * ChatHeader Component
 *
 * Displays the header with:
 * - Title/Logo
 * - Mode toggle buttons (Chat/Workflow)
 * - Connection status indicator with reconnect
 * - Settings button
 */
export const ChatHeader: FC<ChatHeaderProps> = ({
  title = 'IPA Assistant',
  currentMode,
  autoMode,
  isManuallyOverridden,
  connection,
  onModeChange,
  onSettingsClick,
  onReconnect,
  retryCount = 0,
  maxRetries = 5,
  connectionError,
}) => {
  // Handle mode button click
  const handleModeClick = useCallback(
    (mode: ExecutionMode) => {
      onModeChange(mode);
    },
    [onModeChange]
  );

  return (
    <header
      className="flex items-center justify-between px-4 py-3 border-b bg-white"
      data-testid="chat-header"
    >
      {/* Left: Title */}
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
        {isManuallyOverridden && (
          <Badge variant="outline" className="text-xs">
            Manual
          </Badge>
        )}
      </div>

      {/* Center: Mode Toggle */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
        <Button
          variant={currentMode === 'chat' ? 'default' : 'ghost'}
          size="sm"
          className={cn(
            'gap-2 transition-all',
            currentMode === 'chat' && 'shadow-sm'
          )}
          onClick={() => handleModeClick('chat')}
          data-testid="mode-toggle-chat"
        >
          <MessageSquare className="h-4 w-4" />
          Chat
        </Button>
        <Button
          variant={currentMode === 'workflow' ? 'default' : 'ghost'}
          size="sm"
          className={cn(
            'gap-2 transition-all',
            currentMode === 'workflow' && 'shadow-sm'
          )}
          onClick={() => handleModeClick('workflow')}
          data-testid="mode-toggle-workflow"
        >
          <Workflow className="h-4 w-4" />
          Workflow
        </Button>
      </div>

      {/* Right: Status and Settings */}
      <div className="flex items-center gap-3">
        {/* Auto Mode Indicator */}
        {autoMode !== currentMode && (
          <span className="text-xs text-gray-500">
            Auto: {autoMode === 'chat' ? 'Chat' : 'Workflow'}
          </span>
        )}

        {/* Connection Status (Sprint 65 enhancement) */}
        <ConnectionStatus
          status={connection}
          retryCount={retryCount}
          maxRetries={maxRetries}
          onReconnect={onReconnect}
          errorMessage={connectionError}
          compact={false}
        />

        {/* Settings Button */}
        {onSettingsClick && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onSettingsClick}
            className="h-8 w-8"
            data-testid="settings-button"
          >
            <Settings className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
};

export default ChatHeader;
