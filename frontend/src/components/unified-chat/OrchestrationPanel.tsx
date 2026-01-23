/**
 * OrchestrationPanel - Debug Panel for Phase 28 Orchestration Flow
 *
 * Sprint 99: Phase 28 Integration
 *
 * Displays:
 * - Three-layer routing decision details
 * - Risk assessment information
 * - Guided dialog questions
 * - Execution status
 */

import { FC, useState } from 'react';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronRight,
  Route,
  Shield,
  MessageCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  Info,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import type {
  RoutingDecision,
  RiskAssessment,
  DialogQuestion,
} from '@/api/endpoints/orchestration';
import type { OrchestrationPhase } from '@/hooks/useOrchestration';

// =============================================================================
// Types
// =============================================================================

interface OrchestrationPanelProps {
  /** Current orchestration phase */
  phase: OrchestrationPhase;
  /** Routing decision from intent classification */
  routingDecision: RoutingDecision | null;
  /** Risk assessment result */
  riskAssessment: RiskAssessment | null;
  /** Current dialog questions */
  dialogQuestions: DialogQuestion[] | null;
  /** Whether the panel is loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Callback when user responds to dialog */
  onDialogResponse?: (responses: Record<string, string>) => void;
  /** Callback when user approves execution */
  onApprove?: () => void;
  /** Callback when user rejects execution */
  onReject?: () => void;
  /** Callback when user wants to skip dialog and execute directly */
  onSkipDialog?: () => void;
  /** Whether to show as collapsed */
  defaultCollapsed?: boolean;
  /** Class name */
  className?: string;
}

// =============================================================================
// Sub-Components
// =============================================================================

/** Section header with collapse toggle */
const SectionHeader: FC<{
  title: string;
  icon: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  badge?: React.ReactNode;
}> = ({ title, icon, isOpen, onToggle, badge }) => (
  <button
    onClick={onToggle}
    className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded"
  >
    <div className="flex items-center gap-2">
      {icon}
      <span>{title}</span>
      {badge}
    </div>
    {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
  </button>
);

/** Risk level badge */
const RiskBadge: FC<{ level: string }> = ({ level }) => {
  const variants: Record<string, string> = {
    low: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  };

  return (
    <Badge className={cn('text-xs', variants[level] || variants.medium)}>
      {level.toUpperCase()}
    </Badge>
  );
};

/** Routing layer badge */
const LayerBadge: FC<{ layer: string }> = ({ layer }) => {
  const variants: Record<string, string> = {
    pattern: 'bg-blue-100 text-blue-800',
    semantic: 'bg-purple-100 text-purple-800',
    llm: 'bg-indigo-100 text-indigo-800',
    none: 'bg-gray-100 text-gray-800',
  };

  return (
    <Badge className={cn('text-xs', variants[layer] || variants.none)}>
      {layer.toUpperCase()}
    </Badge>
  );
};

/** Phase indicator */
const PhaseIndicator: FC<{ phase: OrchestrationPhase; isLoading: boolean }> = ({
  phase,
  isLoading,
}) => {
  const phaseConfig: Record<OrchestrationPhase, { icon: React.ReactNode; label: string; color: string }> = {
    idle: { icon: <Clock className="w-4 h-4" />, label: 'Idle', color: 'text-gray-500' },
    routing: { icon: <Route className="w-4 h-4" />, label: 'Routing', color: 'text-blue-500' },
    dialog: { icon: <MessageCircle className="w-4 h-4" />, label: 'Dialog', color: 'text-purple-500' },
    risk_assessment: { icon: <Shield className="w-4 h-4" />, label: 'Risk Check', color: 'text-orange-500' },
    awaiting_approval: { icon: <AlertTriangle className="w-4 h-4" />, label: 'Awaiting Approval', color: 'text-yellow-500' },
    executing: { icon: <Loader2 className="w-4 h-4 animate-spin" />, label: 'Executing', color: 'text-blue-500' },
    completed: { icon: <CheckCircle className="w-4 h-4" />, label: 'Completed', color: 'text-green-500' },
    error: { icon: <X className="w-4 h-4" />, label: 'Error', color: 'text-red-500' },
  };

  const config = phaseConfig[phase];

  return (
    <div className={cn('flex items-center gap-2', config.color)}>
      {isLoading && phase !== 'executing' ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        config.icon
      )}
      <span className="text-sm font-medium">{config.label}</span>
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

export const OrchestrationPanel: FC<OrchestrationPanelProps> = ({
  phase,
  routingDecision,
  riskAssessment,
  dialogQuestions,
  isLoading,
  error,
  onDialogResponse,
  onApprove,
  onReject,
  onSkipDialog,
  defaultCollapsed = false,
  className,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [routingOpen, setRoutingOpen] = useState(true);
  const [riskOpen, setRiskOpen] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(true);
  const [dialogResponses, setDialogResponses] = useState<Record<string, string>>({});

  const handleDialogSubmit = () => {
    onDialogResponse?.(dialogResponses);
    setDialogResponses({});
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className={cn(
          'fixed right-4 top-20 z-50 p-2 bg-white rounded-lg shadow-lg border',
          'hover:bg-gray-50 transition-colors',
          className
        )}
        title="Show Orchestration Panel"
      >
        <Info className="w-5 h-5 text-gray-600" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        'w-80 bg-white border-l flex flex-col h-full',
        'shadow-lg',
        className
      )}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Route className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-gray-900">Orchestration</span>
        </div>
        <div className="flex items-center gap-2">
          <PhaseIndicator phase={phase} isLoading={isLoading} />
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 hover:bg-gray-200 rounded"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">Error</span>
            </div>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        )}

        {/* Routing Decision Section */}
        {routingDecision && (
          <div className="border rounded-lg overflow-hidden">
            <SectionHeader
              title="Routing Decision"
              icon={<Route className="w-4 h-4 text-blue-600" />}
              isOpen={routingOpen}
              onToggle={() => setRoutingOpen(!routingOpen)}
              badge={<LayerBadge layer={routingDecision.routing_layer} />}
            />
            {routingOpen && (
              <div className="px-3 pb-3 space-y-2 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-gray-500">Intent:</span>
                    <p className="font-medium">{routingDecision.intent_category}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Sub-intent:</span>
                    <p className="font-medium">{routingDecision.sub_intent || '-'}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Confidence:</span>
                    <p className="font-medium">{(routingDecision.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Workflow:</span>
                    <p className="font-medium">{routingDecision.workflow_type}</p>
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">Completeness:</span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{
                          width: `${(routingDecision.completeness?.completeness_score || 0) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-600">
                      {((routingDecision.completeness?.completeness_score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">Reasoning:</span>
                  <p className="text-gray-700 text-xs mt-1">{routingDecision.reasoning}</p>
                </div>
                <div className="text-xs text-gray-400">
                  Processing: {routingDecision.processing_time_ms.toFixed(2)}ms
                </div>
              </div>
            )}
          </div>
        )}

        {/* Risk Assessment Section */}
        {riskAssessment && (
          <div className="border rounded-lg overflow-hidden">
            <SectionHeader
              title="Risk Assessment"
              icon={<Shield className="w-4 h-4 text-orange-600" />}
              isOpen={riskOpen}
              onToggle={() => setRiskOpen(!riskOpen)}
              badge={<RiskBadge level={riskAssessment.level} />}
            />
            {riskOpen && (
              <div className="px-3 pb-3 space-y-2 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-gray-500">Score:</span>
                    <p className="font-medium">{(riskAssessment.score * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Approval:</span>
                    <p className="font-medium">
                      {riskAssessment.requires_approval ? 'Required' : 'Not Required'}
                    </p>
                  </div>
                </div>
                {riskAssessment.factors.length > 0 && (
                  <div>
                    <span className="text-gray-500">Factors:</span>
                    <ul className="mt-1 space-y-1">
                      {riskAssessment.factors.slice(0, 3).map((factor, idx) => (
                        <li key={idx} className="text-xs text-gray-600 flex items-center gap-1">
                          <span
                            className={cn(
                              'w-2 h-2 rounded-full',
                              factor.impact === 'increase'
                                ? 'bg-red-400'
                                : factor.impact === 'decrease'
                                ? 'bg-green-400'
                                : 'bg-gray-400'
                            )}
                          />
                          {factor.name}: {factor.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-xs text-gray-600">{riskAssessment.reasoning}</p>

                {/* Approval Buttons */}
                {riskAssessment.requires_approval && phase === 'awaiting_approval' && (
                  <div className="flex gap-2 mt-2">
                    <Button size="sm" onClick={onApprove} className="flex-1">
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={onReject} className="flex-1">
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Dialog Questions Section */}
        {dialogQuestions && dialogQuestions.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <SectionHeader
              title="Additional Information"
              icon={<MessageCircle className="w-4 h-4 text-purple-600" />}
              isOpen={dialogOpen}
              onToggle={() => setDialogOpen(!dialogOpen)}
              badge={
                <Badge className="bg-purple-100 text-purple-800 text-xs">
                  {dialogQuestions.length}
                </Badge>
              }
            />
            {dialogOpen && (
              <div className="px-3 pb-3 space-y-3">
                {dialogQuestions.map((q) => (
                  <div key={q.question_id} className="space-y-1">
                    <label className="text-sm text-gray-700">
                      {q.question}
                      {q.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    {q.options && q.options.length > 0 ? (
                      <select
                        className="w-full p-2 text-sm border rounded"
                        value={dialogResponses[q.field_name] || ''}
                        onChange={(e) =>
                          setDialogResponses((prev) => ({
                            ...prev,
                            [q.field_name]: e.target.value,
                          }))
                        }
                      >
                        <option value="">Select...</option>
                        {q.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        placeholder={`Enter ${q.field_name}`}
                        value={dialogResponses[q.field_name] || ''}
                        onChange={(e) =>
                          setDialogResponses((prev) => ({
                            ...prev,
                            [q.field_name]: e.target.value,
                          }))
                        }
                      />
                    )}
                  </div>
                ))}
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleDialogSubmit} className="flex-1">
                    Submit
                  </Button>
                  {onSkipDialog && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onSkipDialog}
                      className="flex-1"
                      title="Skip dialog and execute directly"
                    >
                      Skip & Execute
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Idle State */}
        {phase === 'idle' && !routingDecision && (
          <div className="text-center py-8 text-gray-500">
            <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Send a message to see orchestration details</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrchestrationPanel;
