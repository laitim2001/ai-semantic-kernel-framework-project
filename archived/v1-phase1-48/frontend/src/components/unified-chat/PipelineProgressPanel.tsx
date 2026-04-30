/**
 * PipelineProgressPanel — 8-step visual progress tracker.
 *
 * Shows each pipeline step with status icons and latency.
 * Used in OrchestratorChat to visualize pipeline execution.
 *
 * Phase 45: Orchestration Core (Sprint 157)
 */

import { FC } from 'react';
import type { PipelineStep, PipelineStepStatus } from '@/hooks/useOrchestratorPipeline';

interface PipelineProgressPanelProps {
  steps: PipelineStep[];
  currentStepIndex: number;
  selectedRoute: string | null;
  totalMs: number;
  isRunning: boolean;
}

const STATUS_ICONS: Record<PipelineStepStatus, string> = {
  pending: '○',
  running: '◉',
  completed: '✓',
  paused: '⏸',
  error: '✗',
};

const STATUS_COLORS: Record<PipelineStepStatus, string> = {
  pending: 'text-gray-400',
  running: 'text-blue-500 animate-pulse',
  completed: 'text-green-500',
  paused: 'text-yellow-500',
  error: 'text-red-500',
};

const ROUTE_LABELS: Record<string, string> = {
  direct_answer: '直接回答',
  subagent: '並行 Subagent',
  team: '專家團隊',
};

export const PipelineProgressPanel: FC<PipelineProgressPanelProps> = ({
  steps,
  currentStepIndex,
  selectedRoute,
  totalMs,
  isRunning,
}) => {
  return (
    <div className="border rounded-lg bg-card p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">Pipeline 進度</span>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {totalMs > 0 && (
            <span>{(totalMs / 1000).toFixed(1)}s</span>
          )}
          {isRunning && (
            <span className="text-blue-500 animate-pulse">執行中...</span>
          )}
        </div>
      </div>

      {/* Route Decision — prominent banner, shown immediately when available */}
      {selectedRoute && (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium ${
          selectedRoute === 'team'
            ? 'bg-orange-100 text-orange-800 dark:bg-orange-950/30 dark:text-orange-300 border border-orange-200 dark:border-orange-800'
            : selectedRoute === 'subagent'
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/30 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
              : 'bg-green-100 text-green-800 dark:bg-green-950/30 dark:text-green-300 border border-green-200 dark:border-green-800'
        }`}>
          <span>Route Decision</span>
          <span className="font-bold">{ROUTE_LABELS[selectedRoute] || selectedRoute}</span>
        </div>
      )}

      {/* Steps */}
      <div className="space-y-1">
        {steps.map((step) => (
          <div
            key={step.name}
            className={`flex items-center gap-2 text-xs py-0.5 ${
              step.index === currentStepIndex && step.status === 'running'
                ? 'bg-blue-50 dark:bg-blue-950 rounded px-1 -mx-1'
                : ''
            }`}
          >
            {/* Status icon */}
            <span className={`w-4 text-center font-mono ${STATUS_COLORS[step.status]}`}>
              {STATUS_ICONS[step.status]}
            </span>

            {/* Step label */}
            <span className={`flex-1 ${
              step.status === 'completed'
                ? 'text-muted-foreground'
                : step.status === 'running'
                ? 'font-medium'
                : ''
            }`}>
              {step.label}
            </span>

            {/* Latency */}
            {step.latencyMs != null && step.latencyMs > 0 && (
              <span className="text-muted-foreground tabular-nums">
                {step.latencyMs < 1000
                  ? `${Math.round(step.latencyMs)}ms`
                  : `${(step.latencyMs / 1000).toFixed(1)}s`
                }
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
