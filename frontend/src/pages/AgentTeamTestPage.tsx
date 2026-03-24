/**
 * AgentTeamTestPage — PoC test page for Agent Team + Subagent patterns.
 *
 * Tests three modes:
 * - Subagent: ConcurrentBuilder (parallel, independent)
 * - Team: GroupChatBuilder + SharedTaskList (collaborative)
 * - Hybrid: Orchestrator decides which mode
 *
 * Route: /agent-team-test
 * PoC: poc/agent-team branch
 */

import React, { FC, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import {
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Users,
  GitBranch,
  Brain,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  ListChecks,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';

// =============================================================================
// Types
// =============================================================================

type TestMode = 'subagent' | 'team' | 'hybrid' | 'orchestrator';
type Provider = 'anthropic' | 'azure';

interface TaskItem {
  task_id: string;
  description: string;
  status: string;
  claimed_by: string | null;
  result: string | null;
}

interface TeamMessage {
  from: string;
  content: string;
}

// =============================================================================
// Collapsible Section
// =============================================================================

const Section: FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
}> = ({ title, icon, children, defaultOpen = true, badge }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span>{title}</span>
          {badge && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-purple-100 text-purple-700 rounded">
              {badge}
            </span>
          )}
        </div>
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
      {open && <div className="p-3 border-t bg-gray-50/50">{children}</div>}
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

export const AgentTeamTestPage: FC = () => {
  // State
  const [mode, setMode] = useState<TestMode>('subagent');
  const [provider, setProvider] = useState<Provider>('anthropic');
  const [model, setModel] = useState('claude-haiku-4-5-20251001');
  const [task, setTask] = useState('');
  const [maxRounds, setMaxRounds] = useState(8);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Azure config
  const [azureEndpoint, setAzureEndpoint] = useState('');
  const [azureKey, setAzureKey] = useState('');
  const [azureDeployment, setAzureDeployment] = useState('');

  // Default tasks per mode
  const defaultTasks: Record<TestMode, string> = {
    subagent:
      'Check the status of three systems: 1) APAC ETL Pipeline, 2) CRM Service, 3) Email Server.',
    team:
      'Investigate APAC ETL Pipeline failure. Multiple experts needed: analyze application logs, check database changes, and verify network connectivity.',
    hybrid:
      'Check VPN connectivity for Taipei, Hong Kong, and Singapore offices.',
    orchestrator:
      'APAC Glider ETL Pipeline has been failing for 3 days, affecting financial reports. Please investigate.',
  };

  const handleModeChange = (m: TestMode) => {
    setMode(m);
    setTask(defaultTasks[m]);
    setResult(null);
  };

  // Initialize default task
  React.useEffect(() => {
    setTask(defaultTasks[mode]);
  }, []);

  const handleRun = useCallback(async () => {
    setLoading(true);
    setResult(null);

    const endpointMap: Record<TestMode, string> = {
      subagent: '/api/v1/poc/agent-team/test-subagent',
      team: '/api/v1/poc/agent-team/test-team',
      hybrid: '/api/v1/poc/agent-team/test-hybrid',
      orchestrator: '/api/v1/poc/agent-team/test-orchestrator',
    };
    const endpoint = endpointMap[mode];

    const params = new URLSearchParams({
      provider,
      model,
      task,
      ...(mode === 'team' ? { max_rounds: String(maxRounds) } : {}),
      ...(provider === 'azure'
        ? {
            azure_endpoint: azureEndpoint,
            azure_api_key: azureKey,
            azure_deployment: azureDeployment,
            azure_api_version: '2025-03-01-preview',
          }
        : {}),
    });

    try {
      const r = await fetch(`${endpoint}?${params}`, { method: 'POST' });
      const data = await r.json();
      setResult(data);
    } catch (e: any) {
      setResult({ status: 'error', error: e.message });
    }

    setLoading(false);
  }, [mode, provider, model, task, maxRounds, azureEndpoint, azureKey, azureDeployment]);

  return (
    <div className="flex h-full bg-gray-100">
      {/* Left: Controls */}
      <div className="w-96 bg-white border-r flex flex-col h-full overflow-hidden">
        <div className="px-4 py-3 border-b bg-gradient-to-r from-purple-600 to-indigo-600">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5" />
            Agent Team PoC
          </h1>
          <p className="text-xs text-purple-200 mt-1">Subagent + Team + Hybrid</p>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* Mode Selection */}
          <Section title="Execution Mode" icon={<GitBranch className="w-4 h-4 text-purple-600" />}>
            <div className="flex gap-1">
              {(['orchestrator', 'subagent', 'team', 'hybrid'] as TestMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => handleModeChange(m)}
                  className={cn(
                    'flex-1 px-2 py-1.5 text-xs font-medium rounded transition-colors',
                    mode === m
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {m === 'orchestrator' ? 'Orchestrator' : m === 'subagent' ? 'Subagent' : m === 'team' ? 'Team' : 'Hybrid'}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-gray-500 mt-2">
              {mode === 'orchestrator' && 'Full Orchestrator: memory + RAG + intent routing + mode decision + checkpoint'}
              {mode === 'subagent' && 'ConcurrentBuilder: 3 Agents parallel, independent, results aggregated'}
              {mode === 'team' && 'GroupChatBuilder + SharedTaskList: Teammates claim tasks, communicate, collaborate'}
              {mode === 'hybrid' && 'Orchestrator decides subagent or team mode via function calling'}
            </p>
          </Section>

          {/* Provider + Model */}
          <Section title="LLM Provider" icon={<Brain className="w-4 h-4 text-blue-600" />}>
            <div className="space-y-2">
              <select
                className="w-full p-2 text-sm border rounded"
                value={provider}
                onChange={(e) => {
                  const p = e.target.value as Provider;
                  setProvider(p);
                  setModel(p === 'azure' ? 'gpt-5.2' : 'claude-haiku-4-5-20251001');
                }}
              >
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="azure">Azure OpenAI</option>
              </select>

              {provider === 'anthropic' && (
                <select className="w-full p-2 text-sm border rounded" value={model} onChange={(e) => setModel(e.target.value)}>
                  <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (fast/cheap)</option>
                  <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (balanced)</option>
                  <option value="claude-opus-4-6">Claude Opus 4.6 (deep reasoning)</option>
                </select>
              )}

              {provider === 'azure' && (
                <div className="space-y-1.5">
                  <input className="w-full p-1.5 text-xs border rounded" placeholder="Azure Endpoint" value={azureEndpoint} onChange={(e) => setAzureEndpoint(e.target.value)} />
                  <input className="w-full p-1.5 text-xs border rounded" placeholder="API Key" type="password" value={azureKey} onChange={(e) => setAzureKey(e.target.value)} />
                  <input className="w-full p-1.5 text-xs border rounded" placeholder="Deployment (e.g. gpt-5.2)" value={azureDeployment} onChange={(e) => setAzureDeployment(e.target.value)} />
                </div>
              )}
            </div>
          </Section>

          {/* Task */}
          <Section title="Task" icon={<ListChecks className="w-4 h-4 text-green-600" />}>
            <textarea
              className="w-full p-2 text-sm border rounded resize-none"
              rows={3}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Enter task..."
            />
            {mode === 'team' && (
              <div className="mt-2">
                <label className="text-xs text-gray-500">Max Rounds: {maxRounds}</label>
                <input type="range" min="3" max="15" value={maxRounds} onChange={(e) => setMaxRounds(Number(e.target.value))} className="w-full" />
              </div>
            )}
          </Section>

          {/* Azure Warning for Team/Hybrid */}
          {(mode === 'team' || mode === 'hybrid') && provider === 'anthropic' && (
            <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
              <strong>Warning:</strong> Team and Hybrid modes require <strong>Azure OpenAI</strong> for function calling (tool use).
              Claude Haiku cannot call tools like claim_task/report_result. Switch to Azure provider above.
            </div>
          )}

          {/* Run Button */}
          <Button
            onClick={handleRun}
            disabled={loading || !task.trim()}
            className="w-full bg-purple-600 hover:bg-purple-700"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            Run {mode === 'orchestrator' ? 'Orchestrator' : mode === 'subagent' ? 'Subagent' : mode === 'team' ? 'Team' : 'Hybrid'} Test
          </Button>
        </div>
      </div>

      {/* Right: Results */}
      <div className="flex-1 overflow-y-auto p-4">
        {!result && !loading && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Select a mode and click Run to start the PoC test</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-purple-600" />
              <p className="text-gray-600">Running {mode} test...</p>
              <p className="text-xs text-gray-400 mt-1">This may take 30-120 seconds</p>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-4 max-w-4xl">
            {/* Status Banner */}
            <div className={cn(
              'p-4 rounded-lg border',
              result.status === 'ok' ? 'bg-green-50 border-green-200' :
              result.status === 'partial' ? 'bg-yellow-50 border-yellow-200' :
              'bg-red-50 border-red-200'
            )}>
              <div className="flex items-center gap-2">
                {result.status === 'ok' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : result.status === 'partial' ? (
                  <Zap className="w-5 h-5 text-yellow-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <span className="font-medium text-lg">
                  {result.status === 'ok' ? 'SUCCESS' : result.status === 'partial' ? 'PARTIAL' : 'FAILED'}
                </span>
                <span className="text-sm text-gray-500">({result.test})</span>
              </div>
              {result.summary && <p className="text-sm mt-1">{result.summary}</p>}
              {result.error && <p className="text-sm text-red-600 mt-1">{result.error}</p>}
            </div>

            {/* Steps */}
            {result.steps && (
              <Section title="Execution Steps" icon={<ListChecks className="w-4 h-4" />} badge={`${result.steps.length} steps`}>
                <div className="space-y-1">
                  {result.steps.map((s: any, i: number) => (
                    <div key={i} className="text-sm">
                      <div className="flex items-center gap-2">
                        {s.status === 'ok' ? (
                          <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                        )}
                        <span className="font-medium">{s.step}</span>
                        {s.duration_ms != null && (
                          <span className="text-xs text-gray-400">({s.duration_ms}ms)</span>
                        )}
                      </div>
                      {s.error && <p className="ml-6 text-xs text-red-500 mt-0.5">{s.error}</p>}
                      {s.reasoning_preview && (
                        <p className="ml-6 text-xs text-gray-600 mt-0.5 bg-white p-1 rounded">{s.reasoning_preview}</p>
                      )}
                      {s.selected_mode && (
                        <p className="ml-6 text-xs font-medium text-purple-700 mt-0.5">Mode: {s.selected_mode}</p>
                      )}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Agent Responses (Subagent mode) */}
            {result.agent_responses?.length > 0 && (
              <Section
                title="Agent Responses"
                icon={<Brain className="w-4 h-4 text-purple-600" />}
                badge={`${result.agent_responses.length} agents`}
              >
                <div className="space-y-3">
                  {result.agent_responses.map((r: any, i: number) => (
                    <div key={i} className="bg-white rounded-lg border p-3">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                          {r.agent}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{r.response}</p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Orchestrator Actions */}
            {result.orchestrator_actions?.length > 0 && (
              <Section
                title="Orchestrator Actions"
                icon={<Zap className="w-4 h-4 text-orange-600" />}
                badge={`${result.orchestrator_actions.length} actions`}
              >
                <div className="space-y-1.5">
                  {result.orchestrator_actions.map((a: any, i: number) => (
                    <div key={i} className={cn(
                      'p-2 rounded border text-sm',
                      a.tool ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                    )}>
                      {a.tool && (
                        <div>
                          <span className="font-medium text-blue-700">{a.tool}</span>
                          {a.args && <span className="text-xs text-gray-500 ml-2">{a.args.slice(0, 100)}</span>}
                        </div>
                      )}
                      {a.result && (
                        <p className="text-xs text-gray-600 mt-0.5 whitespace-pre-wrap">{a.result.slice(0, 200)}</p>
                      )}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Orchestrator Response */}
            {result.orchestrator_response && (
              <Section
                title="Orchestrator Response"
                icon={<Brain className="w-4 h-4 text-indigo-600" />}
              >
                <div className="bg-white rounded border p-3 text-sm whitespace-pre-wrap">
                  {result.orchestrator_response}
                </div>
              </Section>
            )}

            {/* SharedTaskList (Team mode) */}
            {result.shared_task_list && (
              <Section
                title="Shared Task List"
                icon={<ListChecks className="w-4 h-4 text-green-600" />}
                badge={`${result.shared_task_list.progress.completed}/${result.shared_task_list.progress.total} done`}
              >
                <div className="space-y-2">
                  {result.shared_task_list.tasks.map((t: TaskItem) => (
                    <div
                      key={t.task_id}
                      className={cn(
                        'p-2 rounded border text-sm',
                        t.status === 'completed' ? 'bg-green-50 border-green-200' :
                        t.status === 'in_progress' ? 'bg-blue-50 border-blue-200' :
                        t.status === 'failed' ? 'bg-red-50 border-red-200' :
                        'bg-gray-50 border-gray-200'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{t.task_id}: {t.description.slice(0, 60)}</span>
                        <span className={cn(
                          'px-1.5 py-0.5 text-[10px] rounded font-medium',
                          t.status === 'completed' ? 'bg-green-200 text-green-800' :
                          t.status === 'in_progress' ? 'bg-blue-200 text-blue-800' :
                          'bg-gray-200 text-gray-600'
                        )}>
                          {t.status}
                        </span>
                      </div>
                      {t.claimed_by && <p className="text-xs text-gray-500 mt-0.5">Claimed by: {t.claimed_by}</p>}
                      {t.result && <p className="text-xs mt-1 bg-white p-1 rounded">{t.result}</p>}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Team Messages */}
            {result.shared_task_list?.messages?.length > 0 && (
              <Section
                title="Team Messages"
                icon={<MessageSquare className="w-4 h-4 text-blue-600" />}
                badge={`${result.shared_task_list.messages.length} messages`}
              >
                <div className="space-y-1">
                  {result.shared_task_list.messages.map((m: TeamMessage, i: number) => (
                    <div key={i} className="text-sm bg-white p-2 rounded border">
                      <span className="font-medium text-purple-700">[{m.from}]</span>{' '}
                      <span>{m.content}</span>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Events */}
            {result.events?.length > 0 && (
              <Section
                title="Workflow Events"
                icon={<Zap className="w-4 h-4 text-yellow-600" />}
                badge={`${result.events.length} events`}
                defaultOpen={false}
              >
                <div className="space-y-0.5 max-h-64 overflow-auto">
                  {result.events.map((e: any, i: number) => (
                    <div key={i} className="text-xs text-gray-600 font-mono">
                      <span className="text-gray-400">[{i}]</span> {e.type}{' '}
                      {e.data_preview && (
                        <span className="text-gray-400">{e.data_preview.slice(0, 100)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentTeamTestPage;
