/**
 * StreamingIndicator - Streaming Response Indicator
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-2: Chat Components
 *
 * Visual indicator for AI response streaming with typing animation effect.
 */

import { FC } from 'react';

export interface StreamingIndicatorProps {
  /** Whether actively streaming */
  isStreaming?: boolean;
  /** Custom text to display */
  text?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/**
 * StreamingIndicator Component
 *
 * Displays a pulsing animation to indicate AI is generating a response.
 * Shows animated dots with typing effect.
 */
export const StreamingIndicator: FC<StreamingIndicatorProps> = ({
  isStreaming = true,
  text = 'AI is typing',
  size = 'md',
  className = '',
}) => {
  if (!isStreaming) return null;

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const dotSizes = {
    sm: 'w-1 h-1',
    md: 'w-1.5 h-1.5',
    lg: 'w-2 h-2',
  };

  return (
    <div
      className={`flex items-center gap-2 text-gray-500 ${sizeClasses[size]} ${className}`}
      data-testid="streaming-indicator"
      role="status"
      aria-label={text}
    >
      <span>{text}</span>
      <div className="flex items-center gap-1">
        <span
          className={`${dotSizes[size]} bg-gray-400 rounded-full animate-bounce`}
          style={{ animationDelay: '0ms', animationDuration: '600ms' }}
        />
        <span
          className={`${dotSizes[size]} bg-gray-400 rounded-full animate-bounce`}
          style={{ animationDelay: '150ms', animationDuration: '600ms' }}
        />
        <span
          className={`${dotSizes[size]} bg-gray-400 rounded-full animate-bounce`}
          style={{ animationDelay: '300ms', animationDuration: '600ms' }}
        />
      </div>
    </div>
  );
};

export default StreamingIndicator;
