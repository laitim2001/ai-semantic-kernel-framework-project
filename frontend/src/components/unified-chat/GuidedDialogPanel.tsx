/**
 * GuidedDialogPanel — Renders guided dialog questions inline.
 *
 * When the pipeline pauses at Step 3 (intent analysis) because
 * user input is incomplete, this panel displays the questions
 * the user needs to answer before the pipeline can continue.
 *
 * Phase 45: Orchestration Core (Sprint 157)
 */

import { FC, useState, useCallback } from 'react';
import type { DialogPause } from '@/hooks/useOrchestratorPipeline';

interface GuidedDialogPanelProps {
  dialogPause: DialogPause;
  onSubmit: (responses: Record<string, string>) => void;
  isSubmitting?: boolean;
}

export const GuidedDialogPanel: FC<GuidedDialogPanelProps> = ({
  dialogPause,
  onSubmit,
  isSubmitting = false,
}) => {
  const [responses, setResponses] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const field of dialogPause.missingFields) {
      init[field] = '';
    }
    return init;
  });

  const handleChange = useCallback((field: string, value: string) => {
    setResponses(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = useCallback(() => {
    // Filter out empty responses
    const filled = Object.fromEntries(
      Object.entries(responses).filter(([, v]) => v.trim() !== '')
    );
    if (Object.keys(filled).length > 0) {
      onSubmit(filled);
    }
  }, [responses, onSubmit]);

  const allFilled = Object.values(responses).every(v => v.trim() !== '');

  return (
    <div className="border rounded-lg bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-yellow-600 dark:text-yellow-400">⚠</span>
        <span className="font-medium text-sm">需要補充資訊</span>
        <span className="text-xs text-muted-foreground">
          (完整度: {Math.round(dialogPause.completenessScore * 100)}%)
        </span>
      </div>

      {/* Questions */}
      <div className="space-y-3">
        {dialogPause.questions.map((question, idx) => {
          const fieldName = dialogPause.missingFields[idx] || `field_${idx}`;
          return (
            <div key={fieldName} className="space-y-1">
              <label className="text-sm font-medium" htmlFor={`dialog-${fieldName}`}>
                {question}
              </label>
              <input
                id={`dialog-${fieldName}`}
                type="text"
                className="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-yellow-500"
                placeholder={`請輸入 ${fieldName}...`}
                value={responses[fieldName] || ''}
                onChange={(e) => handleChange(fieldName, e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          );
        })}
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!allFilled || isSubmitting}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            allFilled && !isSubmitting
              ? 'bg-yellow-600 text-white hover:bg-yellow-700'
              : 'bg-gray-200 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isSubmitting ? '提交中...' : '繼續 Pipeline'}
        </button>
      </div>
    </div>
  );
};
