/**
 * useSwarmEvents Hook
 *
 * React hook for handling Swarm SSE events.
 * Sprint 101: Swarm Event System + SSE Integration
 *
 * @example
 * ```tsx
 * function SwarmPanel({ eventSource }) {
 *   const [swarmStatus, setSwarmStatus] = useState<SwarmStatusUpdatePayload | null>(null);
 *
 *   useSwarmEvents(eventSource, {
 *     onSwarmCreated: (payload) => console.log('Swarm created:', payload),
 *     onSwarmStatusUpdate: (payload) => setSwarmStatus(payload),
 *     onSwarmCompleted: (payload) => console.log('Swarm completed:', payload),
 *     onWorkerProgress: (payload) => console.log('Worker progress:', payload),
 *   });
 *
 *   return <div>{swarmStatus?.overall_progress}%</div>;
 * }
 * ```
 */

import { useCallback, useEffect, useRef } from 'react';
import {
  SwarmEventNames,
  SwarmEventHandlers,
  SwarmCreatedPayload,
  SwarmStatusUpdatePayload,
  SwarmCompletedPayload,
  WorkerStartedPayload,
  WorkerProgressPayload,
  WorkerThinkingPayload,
  WorkerToolCallPayload,
  WorkerMessagePayload,
  WorkerCompletedPayload,
} from '../types/events';

/**
 * Hook for handling Swarm SSE events
 *
 * @param eventSource - EventSource instance or null
 * @param handlers - Event handlers for different swarm events
 */
export function useSwarmEvents(
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

      // Only handle CUSTOM type events (swarm events come as CustomEvent)
      if (data.type !== 'CUSTOM') {
        return;
      }

      const { event_name, payload } = data;

      // Dispatch to appropriate handler based on event name
      switch (event_name) {
        case SwarmEventNames.SWARM_CREATED:
          handlersRef.current.onSwarmCreated?.(payload as SwarmCreatedPayload);
          break;

        case SwarmEventNames.SWARM_STATUS_UPDATE:
          handlersRef.current.onSwarmStatusUpdate?.(
            payload as SwarmStatusUpdatePayload
          );
          break;

        case SwarmEventNames.SWARM_COMPLETED:
          handlersRef.current.onSwarmCompleted?.(
            payload as SwarmCompletedPayload
          );
          break;

        case SwarmEventNames.WORKER_STARTED:
          handlersRef.current.onWorkerStarted?.(payload as WorkerStartedPayload);
          break;

        case SwarmEventNames.WORKER_PROGRESS:
          handlersRef.current.onWorkerProgress?.(
            payload as WorkerProgressPayload
          );
          break;

        case SwarmEventNames.WORKER_THINKING:
          handlersRef.current.onWorkerThinking?.(
            payload as WorkerThinkingPayload
          );
          break;

        case SwarmEventNames.WORKER_TOOL_CALL:
          handlersRef.current.onWorkerToolCall?.(
            payload as WorkerToolCallPayload
          );
          break;

        case SwarmEventNames.WORKER_MESSAGE:
          handlersRef.current.onWorkerMessage?.(payload as WorkerMessagePayload);
          break;

        case SwarmEventNames.WORKER_COMPLETED:
          handlersRef.current.onWorkerCompleted?.(
            payload as WorkerCompletedPayload
          );
          break;

        default:
          // Unknown event, ignore silently
          break;
      }
    } catch (error) {
      console.error('Failed to parse swarm event:', error);
      handlersRef.current.onError?.(
        error instanceof Error ? error : new Error(String(error))
      );
    }
  }, []);

  /**
   * Handle EventSource errors
   */
  const handleError = useCallback((event: Event) => {
    console.error('Swarm EventSource error:', event);
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
 * Check if an SSE event is a swarm event
 *
 * @param data - Parsed SSE event data
 * @returns True if the event is a swarm event
 */
export function isSwarmEvent(data: unknown): boolean {
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
 * Get swarm event category
 *
 * @param eventName - Event name
 * @returns 'swarm' for swarm-level events, 'worker' for worker-level events
 */
export function getSwarmEventCategory(
  eventName: string
): 'swarm' | 'worker' | null {
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
    return 'swarm';
  }

  if (workerEvents.includes(eventName as (typeof workerEvents)[number])) {
    return 'worker';
  }

  return null;
}

export default useSwarmEvents;
