/**
 * GenerativeUIDemo - Generative UI Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 4: Dynamic UI Generation.
 */

import { FC, useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { EventLogEntry } from './EventLogPanel';

export interface GenerativeUIDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

type DemoMode = 'idle' | 'analyzing' | 'generating' | 'complete';

interface ProgressStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete';
}

/**
 * GenerativeUIDemo Component
 *
 * Showcases dynamic UI generation with progress indicators.
 */
export const GenerativeUIDemo: FC<GenerativeUIDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [mode, setMode] = useState<DemoMode>('idle');
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<ProgressStep[]>([
    { id: '1', label: 'Analyzing request', status: 'pending' },
    { id: '2', label: 'Generating structure', status: 'pending' },
    { id: '3', label: 'Applying styles', status: 'pending' },
    { id: '4', label: 'Finalizing output', status: 'pending' },
  ]);

  // Reset demo
  const resetDemo = useCallback(() => {
    setMode('idle');
    setProgress(0);
    setSteps((prev) => prev.map((s) => ({ ...s, status: 'pending' })));
  }, []);

  // Start generation
  const startGeneration = useCallback(() => {
    setMode('analyzing');
    setProgress(0);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'RUN_STARTED',
      timestamp: new Date().toISOString(),
      data: { mode: 'generative_ui' },
    });
  }, [onEvent]);

  // Simulate progress - using ref to track progress to avoid setState in setState callback
  useEffect(() => {
    if (mode === 'idle' || mode === 'complete') return;

    const stepIndex = mode === 'analyzing' ? 0 : mode === 'generating' ? 1 : 2;
    let currentProgress = 0;

    const interval = setInterval(() => {
      currentProgress += Math.random() * 15;

      if (currentProgress >= 100) {
        // Move to next step
        if (stepIndex < 3) {
          setSteps((s) =>
            s.map((step, i) => ({
              ...step,
              status: i < stepIndex + 1 ? 'complete' : i === stepIndex + 1 ? 'active' : 'pending',
            }))
          );

          const nextMode: DemoMode = stepIndex === 0 ? 'generating' : 'complete';

          if (nextMode === 'complete') {
            setSteps((s) => s.map((step) => ({ ...step, status: 'complete' })));

            onEvent?.({
              id: `evt_${Date.now()}`,
              type: 'RUN_FINISHED',
              timestamp: new Date().toISOString(),
              data: { finish_reason: 'complete' },
            });
          }

          setProgress(0);
          setMode(nextMode);
          currentProgress = 0;
        } else {
          setProgress(100);
        }
      } else {
        setProgress(currentProgress);

        setSteps((s) =>
          s.map((step, i) => ({
            ...step,
            status: i < stepIndex ? 'complete' : i === stepIndex ? 'active' : 'pending',
          }))
        );
      }
    }, 200);

    return () => clearInterval(interval);
  }, [mode, onEvent]);

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="generative-ui-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 4: Generative UI</h3>
        <p className="text-sm text-gray-500">
          Dynamic UI generation with progress indicators and mode transitions.
        </p>
      </div>

      {/* Controls */}
      <div className="flex gap-2 mb-4">
        <Button
          variant="default"
          onClick={startGeneration}
          disabled={mode !== 'idle'}
        >
          Start Generation
        </Button>
        <Button
          variant="outline"
          onClick={resetDemo}
          disabled={mode === 'idle'}
        >
          Reset
        </Button>
        <Badge variant={mode === 'complete' ? 'default' : 'secondary'}>
          Mode: {mode.toUpperCase()}
        </Badge>
      </div>

      {/* Progress Visualization */}
      <div className="flex-1 space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Overall Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step Indicators */}
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                step.status === 'active'
                  ? 'bg-blue-50 border-blue-200'
                  : step.status === 'complete'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-gray-50 border-gray-200'
              }`}
            >
              {/* Step Icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold ${
                  step.status === 'active'
                    ? 'bg-blue-600 animate-pulse'
                    : step.status === 'complete'
                    ? 'bg-green-600'
                    : 'bg-gray-300'
                }`}
              >
                {step.status === 'complete' ? '✓' : index + 1}
              </div>

              {/* Step Label */}
              <span
                className={`flex-1 ${
                  step.status === 'pending' ? 'text-gray-400' : 'text-gray-900'
                }`}
              >
                {step.label}
              </span>

              {/* Step Status */}
              {step.status === 'active' && (
                <span className="text-blue-600 text-sm animate-pulse">
                  In progress...
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Completion Message */}
        {mode === 'complete' && (
          <div className="p-4 bg-green-100 rounded-lg text-center">
            <div className="text-3xl mb-2">🎉</div>
            <div className="font-semibold text-green-800">Generation Complete!</div>
            <div className="text-sm text-green-600">UI successfully generated</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GenerativeUIDemo;
