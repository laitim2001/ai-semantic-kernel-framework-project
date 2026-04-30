/**
 * PredictiveDemo - Predictive State Updates Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 7: Optimistic Updates with Rollback.
 */

import { FC, useState, useCallback } from 'react';
import { Badge } from '@/components/ui/Badge';
import type { EventLogEntry } from './EventLogPanel';

export interface PredictiveDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

interface Task {
  id: string;
  title: string;
  completed: boolean;
  isOptimistic?: boolean;
}

type PredictionStatus = 'idle' | 'pending' | 'confirmed' | 'rolled_back';

/**
 * PredictiveDemo Component
 *
 * Interactive demo of optimistic updates with confirmation and rollback.
 */
export const PredictiveDemo: FC<PredictiveDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', title: 'Review pull request', completed: false },
    { id: '2', title: 'Write documentation', completed: false },
    { id: '3', title: 'Fix bug #123', completed: true },
    { id: '4', title: 'Deploy to staging', completed: false },
  ]);
  const [pendingUpdates, setPendingUpdates] = useState<Map<string, { original: boolean; status: PredictionStatus }>>(new Map());
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [history, setHistory] = useState<string[]>([]);

  // Add to history
  const addHistory = useCallback((message: string) => {
    setHistory((prev) => [...prev.slice(-9), `${new Date().toLocaleTimeString()}: ${message}`]);
  }, []);

  // Toggle task with optimistic update
  const toggleTask = useCallback((taskId: string) => {
    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;

    const originalCompleted = task.completed;
    const newCompleted = !originalCompleted;

    // Optimistic update
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, completed: newCompleted, isOptimistic: true } : t
      )
    );

    setPendingUpdates((prev) => {
      const next = new Map(prev);
      next.set(taskId, { original: originalCompleted, status: 'pending' });
      return next;
    });

    addHistory(`Optimistic: "${task.title}" → ${newCompleted ? 'completed' : 'incomplete'}`);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'STATE_DELTA',
      timestamp: new Date().toISOString(),
      data: { task_id: taskId, prediction_type: 'optimistic', new_value: newCompleted },
    });

    // Simulate server response
    setTimeout(() => {
      if (simulateFailure && Math.random() > 0.5) {
        // Rollback
        setTasks((prev) =>
          prev.map((t) =>
            t.id === taskId ? { ...t, completed: originalCompleted, isOptimistic: false } : t
          )
        );

        setPendingUpdates((prev) => {
          const next = new Map(prev);
          next.set(taskId, { original: originalCompleted, status: 'rolled_back' });
          return next;
        });

        addHistory(`Rollback: "${task.title}" → ${originalCompleted ? 'completed' : 'incomplete'}`);

        onEvent?.({
          id: `evt_${Date.now()}`,
          type: 'CUSTOM',
          timestamp: new Date().toISOString(),
          data: { event_name: 'PREDICTION_ROLLED_BACK', task_id: taskId },
        });
      } else {
        // Confirm
        setTasks((prev) =>
          prev.map((t) =>
            t.id === taskId ? { ...t, isOptimistic: false } : t
          )
        );

        setPendingUpdates((prev) => {
          const next = new Map(prev);
          next.set(taskId, { original: originalCompleted, status: 'confirmed' });
          return next;
        });

        addHistory(`Confirmed: "${task.title}" → ${newCompleted ? 'completed' : 'incomplete'}`);
      }

      // Clear status after animation
      setTimeout(() => {
        setPendingUpdates((prev) => {
          const next = new Map(prev);
          next.delete(taskId);
          return next;
        });
      }, 1500);
    }, 1000);
  }, [tasks, simulateFailure, addHistory, onEvent]);

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="predictive-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 7: Predictive State</h3>
        <p className="text-sm text-gray-500">
          Optimistic updates with automatic rollback on failure.
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={simulateFailure}
            onChange={(e) => setSimulateFailure(e.target.checked)}
            className="w-4 h-4"
          />
          <span className="text-sm">Simulate Random Failures (50%)</span>
        </label>
        <div className="flex-1" />
        {/* Simple Optimistic Indicator */}
        {pendingUpdates.size > 0 && (
          <Badge variant="secondary" className="animate-pulse">
            ⚡ {pendingUpdates.size} pending
          </Badge>
        )}
      </div>

      {/* Task List */}
      <div className="flex-1 space-y-2 overflow-y-auto">
        {tasks.map((task) => {
          const updateInfo = pendingUpdates.get(task.id);
          const isPending = updateInfo?.status === 'pending';
          const isRolledBack = updateInfo?.status === 'rolled_back';
          const isConfirmed = updateInfo?.status === 'confirmed';

          return (
            <div
              key={task.id}
              className={`
                flex items-center gap-3 p-3 rounded-lg border transition-all duration-300
                ${isPending ? 'bg-blue-50 border-blue-200' :
                  isRolledBack ? 'bg-red-50 border-red-200 animate-shake' :
                  isConfirmed ? 'bg-green-50 border-green-200' :
                  'bg-white border-gray-200'}
                ${task.isOptimistic ? 'opacity-75' : ''}
              `}
              data-testid={`task-${task.id}`}
            >
              {/* Checkbox */}
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
                disabled={isPending}
                className="w-5 h-5 rounded"
              />

              {/* Title */}
              <span
                className={`flex-1 ${task.completed ? 'line-through text-gray-400' : 'text-gray-900'}`}
              >
                {task.title}
              </span>

              {/* Status Badge */}
              {isPending && (
                <Badge variant="secondary" className="animate-pulse">
                  Saving...
                </Badge>
              )}
              {isRolledBack && (
                <Badge variant="destructive">
                  Rolled Back
                </Badge>
              )}
              {isConfirmed && (
                <Badge variant="default">
                  Saved ✓
                </Badge>
              )}
              {task.isOptimistic && !updateInfo && (
                <Badge variant="outline">
                  Optimistic
                </Badge>
              )}
            </div>
          );
        })}
      </div>

      {/* History Log */}
      {history.length > 0 && (
        <div className="mt-4 p-3 bg-gray-900 rounded-lg">
          <div className="text-xs font-medium text-gray-400 mb-2">Update History</div>
          <div className="space-y-1 text-xs font-mono text-gray-300">
            {history.map((entry, i) => (
              <div key={i}>{entry}</div>
            ))}
          </div>
        </div>
      )}

      {/* Tips */}
      <div className="mt-4 p-3 bg-orange-50 rounded-lg text-sm text-orange-800">
        <strong>How it works:</strong> Toggle a task → instant UI update (optimistic) →
        server confirms or rollback occurs after 1 second.
      </div>
    </div>
  );
};

export default PredictiveDemo;
