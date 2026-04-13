/**
 * useAgentTeamEvents Hook
 *
 * React hook for handling Agent Team SSE events.
 * Sprint 101: Agent Team Event System + SSE Integration
 *
 * @example
 * ```tsx
 * function SwarmPanel({ eventSource }) {
 *   const [agentTeamStatus, setTeamStatus] = useState<TeamStatusUpdatePayload | null>(null);
 *
 *   useAgentTeamEvents(eventSource, {
 *     onTeamCreated: (payload) => console.log('Team created:', payload),
 *     onTeamStatusUpdate: (payload) => setTeamStatus(payload),
 *     onTeamCompleted: (payload) => console.log('Team completed:', payload),
 *     onWorkerProgress: (payload) => console.log('Agent progress:', payload),
 *   });
 *
 *   return <div>{agentTeamStatus?.overall_progress}%</div>;
 * }
 * ```
 */

import { useCallback, useEffect, useRef } from 'react';
import {
  SwarmEventNames,
  SwarmEventHandlers,
  TeamCreatedPayload,
  TeamStatusUpdatePayload,
  TeamCompletedPayload,
  AgentStartedPayload,
  AgentProgressPayload,
  AgentThinkingPayload,
  AgentToolCallPayload,
  AgentMessagePayload,
  AgentCompletedPayload,
} from '../types/events';

/**
 * Hook for handling Agent Team SSE events
 *
 * @param eventSource - EventSource instance or null
 * @param handlers - Event handlers for different team events
 */
export function useAgentTeamEvents(
  eventSource: EventSource | null,
  handlers: SwarmEventHandlers
): void {
  // Use ref to avoid re-creating callback when handlers change
  const handlersRef = useRef<SwarmEventHandlers>(handlers);
  handlersRef.current = handlers;

  /**
   * Process incoming SSE message
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      // Only handle CUSTOM type events (team events come as CustomEvent)
      if (data.type !== 'CUSTOM') {
        return;
      }

      const { event_name, payload } = data;

      // Dispatch to appropriate handler based on event name
      switch (event_name) {
        case SwarmEventNames.SWARM_CREATED:
          handlersRef.current.onTeamCreated?.(payload as TeamCreatedPayload);
          break;

        case SwarmEventNames.SWARM_STATUS_UPDATE:
          handlersRef.current.onTeamStatusUpdate?.(
            payload as TeamStatusUpdatePayload
          );
          break;

        case SwarmEventNames.SWARM_COMPLETED:
          handlersRef.current.onTeamCompleted?.(
            payload as TeamCompletedPayload
          );
          break;

        case SwarmEventNames.WORKER_STARTED:
          handlersRef.current.onWorkerStarted?.(payload as AgentStartedPayload);
          break;

        case SwarmEventNames.WORKER_PROGRESS:
          handlersRef.current.onWorkerProgress?.(
            payload as AgentProgressPayload
          );
          break;

        case SwarmEventNames.WORKER_THINKING:
          handlersRef.current.onWorkerThinking?.(
            payload as AgentThinkingPayload
          );
          break;

        case SwarmEventNames.WORKER_TOOL_CALL:
          handlersRef.current.onWorkerToolCall?.(
            payload as AgentToolCallPayload
          );
          break;

        case SwarmEventNames.WORKER_MESSAGE:
          handlersRef.current.onAgentMessage?.(payload as AgentMessagePayload);
          break;

        case SwarmEventNames.WORKER_COMPLETED:
          handlersRef.current.onWorkerCompleted?.(
            payload as AgentCompletedPayload
          );
          break;

        default:
          // Unknown event, ignore silently
          break;
      }
    } catch (error) {
      console.error('Failed to parse team event:', error);
      handlersRef.current.onError?.(
        error instanceof Error ? error : new Error(String(error))
      );
    }
  }, []);

  /**
   * Handle EventSource errors
   */
  const handleError = useCallback((event: Event) => {
    console.error('Agent Team EventSource error:', event);
    handlersRef.current.onError?.(new Error('EventSource connection error'));
  }, []);

  // Set up event listeners
  useEffect(() => {
    if (!eventSource) {
      return;
    }

    eventSource.addEventListener('message', handleMessage);
    eventSource.addEventListener('error', handleError);

    return () => {
      eventSource.removeEventListener('message', handleMessage);
      eventSource.removeEventListener('error', handleError);
    };
  }, [eventSource, handleMessage, handleError]);
}

/**
 * Check if an SSE event is a team event
 *
 * @param data - Parsed SSE event data
 * @returns True if the event is a team event
 */
export function isTeamEvent(data: unknown): boolean {
  if (typeof data !== 'object' || data === null) {
    return false;
  }

  const event = data as { type?: string; event_name?: string };

  if (event.type !== 'CUSTOM') {
    return false;
  }

  const swarmEventNames = Object.values(SwarmEventNames);
  return swarmEventNames.includes(event.event_name as (typeof swarmEventNames)[number]);
}

/**
 * Get team event category
 *
 * @param eventName - Event name
 * @returns 'team' for team-level events, 'agent' for agent-level events
 */
export function getTeamEventCategory(
  eventName: string
): 'team' | 'agent' | null {
  const swarmEvents = [
    SwarmEventNames.SWARM_CREATED,
    SwarmEventNames.SWARM_STATUS_UPDATE,
    SwarmEventNames.SWARM_COMPLETED,
  ];

  const workerEvents = [
    SwarmEventNames.WORKER_STARTED,
    SwarmEventNames.WORKER_PROGRESS,
    SwarmEventNames.WORKER_THINKING,
    SwarmEventNames.WORKER_TOOL_CALL,
    SwarmEventNames.WORKER_MESSAGE,
    SwarmEventNames.WORKER_COMPLETED,
  ];

  if (swarmEvents.includes(eventName as (typeof swarmEvents)[number])) {
    return 'team';
  }

  if (workerEvents.includes(eventName as (typeof workerEvents)[number])) {
    return 'agent';
  }

  return null;
}

export default useAgentTeamEvents;
