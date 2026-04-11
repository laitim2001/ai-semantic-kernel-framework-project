/**
 * StepDetailPanel — Displays detailed results for each pipeline step.
 *
 * Shows step-specific information as it becomes available:
 * - Memory: pinned count, budget %, chars
 * - Knowledge: result count, scores
 * - Intent: category, sub_intent, confidence, layer, completeness
 * - Risk: level, score, requires_approval
 * - HITL: approval status
 * - LLM Route: selected route, reasoning
 * - Agents: status, output preview
 * - PostProcess: checkpoint ID
 *
 * Phase 45: Orchestration Core
 */

import { FC } from 'react';
import type { PipelineStep, AgentProgress } from '@/hooks/useOrchestratorPipeline';

interface StepDetailPanelProps {
  steps: PipelineStep[];
  agents: AgentProgress[];
  selectedRoute: string | null;
  routeReasoning: string | null;
}

const ROUTE_LABELS: Record<string, string> = {
  direct_answer: 'Direct Answer (直接回答)',
  subagent: 'Subagent (並行執行)',
  team: 'Team (專家協作)',
};

const RISK_COLORS: Record<string, string> = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-orange-600',
  critical: 'text-red-600',
};

export const StepDetailPanel: FC<StepDetailPanelProps> = ({
  steps,
  agents,
  selectedRoute,
  routeReasoning,
}) => {
  const completedSteps = steps.filter(s => s.status === 'completed' || s.status === 'paused');

  if (completedSteps.length === 0) {
    return (
      <div className="text-xs text-muted-foreground p-3 text-center">
        等待 pipeline 執行...
      </div>
    );
  }

  return (
    <div className="space-y-2 p-3 overflow-y-auto">
      {completedSteps.map(step => (
        <StepDetail key={step.name} step={step} />
      ))}

      {/* Route Decision */}
      {selectedRoute && (
        <div className="border rounded p-2 bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
          <div className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
            Route Decision
          </div>
          <div className="text-sm font-medium">
            {ROUTE_LABELS[selectedRoute] || selectedRoute}
          </div>
          {routeReasoning && (
            <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {routeReasoning}
            </div>
          )}
        </div>
      )}

      {/* Agents */}
      {agents.length > 0 && (
        <div className="border rounded p-2">
          <div className="text-xs font-medium mb-1">Agents</div>
          <div className="space-y-1">
            {agents.map(agent => (
              <AgentRow key={agent.agentName} agent={agent} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Step Detail Row ---

const StepDetail: FC<{ step: PipelineStep }> = ({ step }) => {
  const meta = step.metadata || {};

  return (
    <div className="border rounded p-2 text-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium">{step.label}</span>
        {step.latencyMs != null && (
          <span className="text-muted-foreground tabular-nums">
            {step.latencyMs < 1000
              ? `${Math.round(step.latencyMs)}ms`
              : `${(step.latencyMs / 1000).toFixed(1)}s`
            }
          </span>
        )}
      </div>

      {/* Step-specific metadata */}
      {step.name === 'memory_read' && <MemoryDetail meta={meta} />}
      {step.name === 'knowledge_search' && <KnowledgeDetail meta={meta} />}
      {step.name === 'intent_analysis' && <IntentDetail meta={meta} />}
      {step.name === 'risk_assessment' && <RiskDetail meta={meta} />}
      {step.name === 'hitl_gate' && <HITLDetail meta={meta} step={step} />}
      {step.name === 'llm_route_decision' && <RouteDetail meta={meta} />}
      {step.name === 'post_process' && <PostProcessDetail meta={meta} />}
    </div>
  );
};

// --- Step-specific detail components ---

const MemoryDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => (
  <div className="text-muted-foreground space-y-0.5">
    {meta.pinned_count != null && <div>Pinned: {String(meta.pinned_count)}</div>}
    {meta.budget_used_pct != null && <div>Budget: {Number(meta.budget_used_pct).toFixed(0)}%</div>}
    {meta.memory_chars != null && <div>Chars: {String(meta.memory_chars)}</div>}
    {meta.status && <div>Status: {String(meta.status)}</div>}
  </div>
);

const KnowledgeDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => (
  <div className="text-muted-foreground space-y-0.5">
    {meta.result_count != null && <div>Results: {String(meta.result_count)}</div>}
    {meta.collection && <div>Collection: {String(meta.collection)}</div>}
    {Array.isArray(meta.scores) && meta.scores.length > 0 && (
      <div>Scores: {(meta.scores as number[]).map(s => s.toFixed(2)).join(', ')}</div>
    )}
    {meta.status && <div>Status: {String(meta.status)}</div>}
  </div>
);

const IntentDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => (
  <div className="text-muted-foreground space-y-0.5">
    {meta.intent && (
      <div>
        Intent: <span className="font-medium text-foreground">{String(meta.intent)}</span>
      </div>
    )}
    {meta.confidence != null && (
      <div>Confidence: {(Number(meta.confidence) * 100).toFixed(0)}%</div>
    )}
    {meta.routing_layer && <div>Layer: {String(meta.routing_layer)}</div>}
  </div>
);

const RiskDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => {
  const level = String(meta.risk_level || meta.level || '').toLowerCase();
  const colorClass = RISK_COLORS[level] || '';

  return (
    <div className="text-muted-foreground space-y-0.5">
      {level && (
        <div>
          Level: <span className={`font-medium ${colorClass}`}>{level.toUpperCase()}</span>
        </div>
      )}
      {meta.score != null && <div>Score: {Number(meta.score).toFixed(2)}</div>}
      {meta.requires_approval != null && (
        <div>Approval: {meta.requires_approval ? 'Required' : 'Not required'}</div>
      )}
    </div>
  );
};

const HITLDetail: FC<{ meta: Record<string, unknown>; step: PipelineStep }> = ({ meta, step }) => (
  <div className="text-muted-foreground">
    {step.status === 'paused' ? (
      <div className="text-yellow-600">Waiting for approval...</div>
    ) : (
      <div>Passed (no approval needed)</div>
    )}
  </div>
);

const RouteDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => (
  <div className="text-muted-foreground space-y-0.5">
    {meta.route && (
      <div>Route: <span className="font-medium text-foreground">{String(meta.route)}</span></div>
    )}
    {meta.reasoning && (
      <div className="line-clamp-2">{String(meta.reasoning)}</div>
    )}
  </div>
);

const PostProcessDetail: FC<{ meta: Record<string, unknown> }> = ({ meta }) => (
  <div className="text-muted-foreground space-y-0.5">
    {meta.checkpoint_id && <div>Checkpoint: {String(meta.checkpoint_id).slice(0, 12)}...</div>}
    <div>Memory extraction: scheduled</div>
  </div>
);

// --- Agent Row ---

const AGENT_STATUS_ICONS: Record<string, string> = {
  thinking: '...',
  tool_call: '...',
  completed: '✓',
};

const AgentRow: FC<{ agent: AgentProgress }> = ({ agent }) => (
  <div className="flex items-center gap-2 text-xs py-0.5">
    <span className={agent.status === 'completed' ? 'text-green-500' : 'text-blue-500 animate-pulse'}>
      {AGENT_STATUS_ICONS[agent.status] || '○'}
    </span>
    <span className="font-medium">{agent.agentName}</span>
    <span className="text-muted-foreground flex-1 truncate">
      {agent.status === 'completed' && agent.output
        ? agent.output.slice(0, 80)
        : agent.status === 'thinking'
        ? 'thinking...'
        : agent.status}
    </span>
    {agent.durationMs != null && (
      <span className="text-muted-foreground tabular-nums">
        {Math.round(agent.durationMs)}ms
      </span>
    )}
  </div>
);
