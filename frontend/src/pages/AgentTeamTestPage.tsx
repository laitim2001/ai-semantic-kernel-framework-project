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
  RotateCcw,
  ShieldCheck,
  ArrowRightLeft,
  History,
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
  const [provider, setProvider] = useState<Provider>('azure');
  const [model, setModel] = useState('gpt-5.4-mini');
  const [task, setTask] = useState('');
  const [maxRounds, setMaxRounds] = useState(8);
  const [loading, setLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeResult, setResumeResult] = useState<any>(null);
  const [result, setResult] = useState<any>(null);

  // Azure config — credentials loaded from server .env by default
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

  const handleResume = useCallback(async (checkpointId: string, type: 'reroute' | 'hitl_approve' | 'hitl_reject', overrideRoute?: string) => {
    setResumeLoading(true);
    setResumeResult(null);

    const params = new URLSearchParams({
      checkpoint_id: checkpointId,
      user_id: 'user-chris',
      ...(type === 'reroute' && overrideRoute ? { override_route: overrideRoute } : {}),
      ...(type === 'hitl_approve' ? { approval_status: 'approved', approval_approver: 'manager-ui' } : {}),
      ...(type === 'hitl_reject' ? { approval_status: 'rejected' } : {}),
    });

    try {
      const r = await fetch(`/api/v1/poc/agent-team/resume?${params}`, { method: 'POST' });
      const data = await r.json();
      setResumeResult(data);
    } catch (e: any) {
      setResumeResult({ status: 'error', error: e.message });
    }

    setResumeLoading(false);
  }, []);

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
                  setModel(p === 'azure' ? 'gpt-5.4-mini' : 'claude-haiku-4-5-20251001');
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
                  <select className="w-full p-2 text-sm border rounded" value={model} onChange={(e) => setModel(e.target.value)}>
                    <option value="gpt-5.4-nano">GPT-5.4 Nano (fastest/cheapest)</option>
                    <option value="gpt-5.4-mini">GPT-5.4 Mini (best small model)</option>
                    <option value="gpt-5-mini">GPT-5 Mini</option>
                    <option value="gpt-5">GPT-5</option>
                    <option value="gpt-5.2">GPT-5.2 (deep reasoning)</option>
                  </select>
                  <p className="text-[10px] text-gray-400">Azure credentials loaded from server .env</p>
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

          {/* Provider hint for Team/Hybrid */}
          {(mode === 'team' || mode === 'hybrid') && provider === 'anthropic' && (
            <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
              <strong>Tip:</strong> Team and Hybrid modes work best with <strong>Azure OpenAI</strong> (no rate limiting).
              Switch to Azure provider above for better results.
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
              result.status === 'pending_approval' ? 'bg-amber-50 border-amber-300' :
              result.status === 'partial' ? 'bg-yellow-50 border-yellow-200' :
              'bg-red-50 border-red-200'
            )}>
              <div className="flex items-center gap-2">
                {result.status === 'ok' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : result.status === 'pending_approval' ? (
                  <ShieldCheck className="w-5 h-5 text-amber-600" />
                ) : result.status === 'partial' ? (
                  <Zap className="w-5 h-5 text-yellow-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <span className="font-medium text-lg">
                  {result.status === 'ok' ? 'SUCCESS' :
                   result.status === 'pending_approval' ? 'AWAITING APPROVAL' :
                   result.status === 'partial' ? 'PARTIAL' : 'FAILED'}
                </span>
                <span className="text-sm text-gray-500">({result.test})</span>
              </div>
              {result.summary && <p className="text-sm mt-1">{result.summary}</p>}
              {result.error && <p className="text-sm text-red-600 mt-1">{result.error}</p>}
            </div>

            {/* HITL Approval Panel */}
            {result.status === 'pending_approval' && result.approval && (
              <div className="bg-amber-50 border-2 border-amber-300 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-5 h-5 text-amber-600" />
                  <span className="font-bold text-amber-800 text-lg">需要主管審批</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-red-100 text-red-700 font-medium">
                    {result.approval.risk_level}
                  </span>
                </div>

                <div className="bg-white rounded border p-3 mb-3 text-sm space-y-1">
                  <p><span className="text-gray-500">操作:</span> <span className="font-medium">{result.task}</span></p>
                  <p><span className="text-gray-500">Session:</span> <span className="font-mono text-xs">{result.session_id}</span></p>
                  <p><span className="text-gray-500">Checkpoint:</span> <span className="font-mono text-xs">{result.approval.checkpoint_id?.slice(0, 16)}...</span></p>
                  <p><span className="text-gray-500">Approval ID:</span> <span className="font-mono text-xs">{result.approval.id}</span></p>
                  <p className="text-amber-700 font-medium mt-2">{result.approval.message}</p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={async () => {
                      setResumeLoading(true);
                      setResumeResult(null);
                      try {
                        const params = new URLSearchParams({
                          user_id: result.user_id || 'user-chris',
                          action: 'approve',
                          decided_by: 'manager-ui',
                          auto_resume: 'true',
                          provider: 'azure',
                          model: 'gpt-5.4-mini',
                        });
                        const r = await fetch(`/api/v1/poc/agent-team/approvals/${result.approval.id}/decide?${params}`, { method: 'POST' });
                        const data = await r.json();
                        setResumeResult(data);
                        // Update result status after successful approval
                        if (data.status === 'ok' && data.action === 'approve') {
                          setResult((prev: any) => ({
                            ...prev,
                            status: 'ok',
                            summary: `Approved by ${data.decided_by} — pipeline resumed`,
                            orchestrator_response: data.resume?.orchestrator_response || prev.orchestrator_response,
                          }));
                        }
                      } catch (e: any) {
                        setResumeResult({ status: 'error', error: e.message });
                      }
                      setResumeLoading(false);
                    }}
                    disabled={resumeLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50"
                  >
                    {resumeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    批准並繼續執行
                  </button>
                  <button
                    onClick={async () => {
                      setResumeLoading(true);
                      setResumeResult(null);
                      try {
                        const params = new URLSearchParams({
                          user_id: result.user_id || 'user-chris',
                          action: 'reject',
                          decided_by: 'manager-ui',
                          reason: 'Risk too high, need more investigation',
                        });
                        const r = await fetch(`/api/v1/poc/agent-team/approvals/${result.approval.id}/decide?${params}`, { method: 'POST' });
                        const data = await r.json();
                        setResumeResult(data);
                        if (data.status === 'ok' && data.action === 'reject') {
                          setResult((prev: any) => ({
                            ...prev,
                            status: 'error',
                            summary: `Rejected by ${data.decided_by} — pipeline terminated`,
                          }));
                        }
                      } catch (e: any) {
                        setResumeResult({ status: 'error', error: e.message });
                      }
                      setResumeLoading(false);
                    }}
                    disabled={resumeLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-100 text-red-700 font-medium border border-red-300 hover:bg-red-200 disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" />
                    拒絕
                  </button>
                </div>

                {/* Approval Result */}
                {resumeLoading && (
                  <div className="flex items-center gap-2 mt-3 p-2 bg-blue-50 rounded border border-blue-200">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    <span className="text-sm text-blue-700">正在處理審批並恢復執行...</span>
                  </div>
                )}
                {resumeResult && (
                  <div className={cn(
                    'mt-3 p-3 rounded border text-sm',
                    resumeResult.status === 'ok' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      {resumeResult.status === 'ok' ? <CheckCircle className="w-4 h-4 text-green-600" /> : <XCircle className="w-4 h-4 text-red-600" />}
                      <span className="font-medium">
                        {resumeResult.action === 'approve' ? '已批准' : '已拒絕'}
                        {resumeResult.resume?.status === 'ok' ? ' — 執行已恢復' : ''}
                      </span>
                    </div>
                    {resumeResult.resume?.orchestrator_response && (
                      <details className="mt-2" open>
                        <summary className="text-xs text-indigo-600 cursor-pointer font-medium">LLM 恢復執行結果</summary>
                        <div className="text-xs text-gray-700 mt-1 bg-white p-2 rounded border whitespace-pre-wrap max-h-64 overflow-auto">
                          {resumeResult.resume.orchestrator_response}
                        </div>
                      </details>
                    )}
                    {resumeResult.error && <p className="text-xs text-red-600 mt-1">{resumeResult.error}</p>}
                  </div>
                )}
              </div>
            )}

            {/* Steps */}
            {result.steps && (
              <Section title="Execution Steps" icon={<ListChecks className="w-4 h-4" />} badge={`${result.steps.length} steps`}>
                <div className="space-y-1">
                  {result.steps.map((s: any, i: number) => (
                    <div key={i} className="text-sm">
                      <div className="flex items-center gap-2">
                        {s.status === 'ok' ? (
                          <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                        ) : s.status === 'partial' ? (
                          <Zap className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                        ) : s.status === 'simulated' ? (
                          <Zap className="w-4 h-4 text-blue-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                        )}
                        <span className="font-medium">{s.step}</span>
                        {s.status && s.status !== 'ok' && (
                          <span className={cn(
                            'text-[10px] px-1 py-0.5 rounded font-medium',
                            s.status === 'partial' ? 'bg-yellow-100 text-yellow-700' :
                            s.status === 'simulated' ? 'bg-blue-100 text-blue-700' :
                            'bg-red-100 text-red-700'
                          )}>{s.status}</span>
                        )}
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

            {/* Agent States & Responses */}
            {(result.agent_responses?.length > 0 || result.agent_states) && (
              <Section
                title="Agent Responses"
                icon={<Brain className="w-4 h-4 text-purple-600" />}
                badge={`${result.agent_responses?.length || 0} responses`}
              >
                <div className="space-y-3">
                  {/* Agent State Summary with Retry */}
                  {result.agent_states && Object.keys(result.agent_states).length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded border">
                      {Object.entries(result.agent_states).map(([name, status]: [string, any]) => (
                        <div key={name} className="flex items-center gap-1.5">
                          <span className={cn(
                            'px-2 py-0.5 text-[11px] font-medium rounded',
                            status === 'complete' || status === 'kept' ? 'bg-green-100 text-green-700' :
                            status === 'running' ? 'bg-blue-100 text-blue-700' :
                            status === 'error' || status === 'no_response' || status === 'retry_failed' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                          )}>
                            {status === 'complete' || status === 'kept' ? '✓' : status === 'running' ? '⟳' : '✗'} {name}
                          </span>
                          {(status === 'error' || status === 'no_response' || status === 'retry_failed') && result.checkpoints?.[0]?.id && (
                            <button
                              onClick={() => handleResume(result.checkpoints[0].id, 'reroute', undefined)}
                              disabled={resumeLoading}
                              className="text-[10px] px-1.5 py-0.5 rounded border bg-orange-50 border-orange-200 text-orange-700 hover:bg-orange-100 disabled:opacity-50"
                            >
                              <RotateCcw className="w-3 h-3 inline mr-0.5" />Retry
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Agent Response Cards */}
                  {result.agent_responses?.map((r: any, i: number) => (
                    <div key={i} className={cn(
                      'bg-white rounded-lg border p-3',
                      r.status === 'retry_complete' ? 'border-orange-200 bg-orange-50/30' :
                      r.status === 'retry_failed' ? 'border-red-200 bg-red-50/30' : ''
                    )}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                          {r.agent}
                        </span>
                        {r.status === 'retry_complete' && (
                          <span className="px-1.5 py-0.5 text-[10px] bg-orange-100 text-orange-700 rounded font-medium">
                            <RotateCcw className="w-3 h-3 inline mr-0.5" />retried
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{r.response}</p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Resume Agent Retry Results */}
            {resumeResult?.agent_responses?.length > 0 && (
              <Section
                title="Agent Retry Results"
                icon={<RotateCcw className="w-4 h-4 text-orange-600" />}
                badge={`${resumeResult.agent_responses.length} retried`}
              >
                <div className="space-y-2">
                  {resumeResult.agent_states && (
                    <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded border">
                      {Object.entries(resumeResult.agent_states).map(([name, status]: [string, any]) => (
                        <span key={name} className={cn(
                          'px-2 py-0.5 text-[11px] font-medium rounded',
                          status === 'complete' || status === 'kept' ? 'bg-green-100 text-green-700' :
                          'bg-red-100 text-red-700'
                        )}>
                          {status === 'kept' ? '⟶' : status === 'complete' ? '✓' : '✗'} {name}: {status}
                        </span>
                      ))}
                    </div>
                  )}
                  {resumeResult.agent_responses.map((r: any, i: number) => (
                    <div key={i} className={cn(
                      'bg-white rounded-lg border p-3',
                      r.status === 'retry_complete' ? 'border-green-200' : 'border-red-200'
                    )}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 text-xs font-medium bg-orange-100 text-orange-800 rounded">
                          {r.agent} (retry)
                        </span>
                        <span className={cn(
                          'text-[10px] px-1 py-0.5 rounded',
                          r.status === 'retry_complete' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        )}>{r.status}</span>
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
                        <p className="text-xs text-gray-600 mt-0.5 whitespace-pre-wrap">{a.result}</p>
                      )}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* IPA Checkpoints & Resume */}
            {result.checkpoints?.length > 0 && (
              <Section
                title="IPA Checkpoints & Resume"
                icon={<History className="w-4 h-4 text-emerald-600" />}
                badge={`${result.checkpoints.length} checkpoint(s)`}
              >
                <div className="space-y-2">
                  {result.checkpoints.map((cp: any, i: number) => (
                    <div key={i} className="bg-white rounded-lg border p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-emerald-600" />
                          <span className="text-sm font-medium">Step {cp.step}: {cp.reason}</span>
                          {cp.route && (
                            <span className="px-1.5 py-0.5 text-[10px] rounded bg-purple-100 text-purple-700 font-medium">
                              route: {cp.route}
                            </span>
                          )}
                          {cp.risk && (
                            <span className="px-1.5 py-0.5 text-[10px] rounded bg-red-100 text-red-700 font-medium">
                              {cp.risk}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-gray-400 font-mono">{cp.id?.slice(0, 12)}...</span>
                      </div>

                      {/* Resume Actions */}
                      <div className="flex flex-wrap gap-2 mt-2">
                        {/* Re-Route buttons */}
                        {cp.step === 4 && ['direct_answer', 'subagent', 'team', 'swarm', 'workflow'].filter(r => r !== cp.route).map((route) => (
                          <button
                            key={route}
                            onClick={() => handleResume(cp.id, 'reroute', route)}
                            disabled={resumeLoading}
                            className="flex items-center gap-1 px-2 py-1 text-[11px] rounded border bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                          >
                            <ArrowRightLeft className="w-3 h-3" />
                            Re-route → {route}
                          </button>
                        ))}

                        {/* HITL Approve/Reject (only if not already handled by top panel) */}
                        {cp.reason === 'high_risk_hitl' && result.status !== 'pending_approval' && (
                          <>
                            <button
                              onClick={() => handleResume(cp.id, 'hitl_approve')}
                              disabled={resumeLoading}
                              className="flex items-center gap-1 px-2 py-1 text-[11px] rounded border bg-green-50 border-green-200 text-green-700 hover:bg-green-100 disabled:opacity-50"
                            >
                              <CheckCircle className="w-3 h-3" />
                              Approve
                            </button>
                            <button
                              onClick={() => handleResume(cp.id, 'hitl_reject')}
                              disabled={resumeLoading}
                              className="flex items-center gap-1 px-2 py-1 text-[11px] rounded border bg-red-50 border-red-200 text-red-700 hover:bg-red-100 disabled:opacity-50"
                            >
                              <XCircle className="w-3 h-3" />
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Resume Result */}
                  {resumeLoading && (
                    <div className="flex items-center gap-2 p-2 bg-blue-50 rounded border border-blue-200">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="text-sm text-blue-700">Resuming from checkpoint...</span>
                    </div>
                  )}
                  {resumeResult && (
                    <div className={cn(
                      'p-3 rounded border text-sm',
                      resumeResult.status === 'ok' ? 'bg-green-50 border-green-200' :
                      resumeResult.status === 'rejected' ? 'bg-yellow-50 border-yellow-200' :
                      'bg-red-50 border-red-200'
                    )}>
                      <div className="flex items-center gap-2 mb-1">
                        {resumeResult.status === 'ok' ? <CheckCircle className="w-4 h-4 text-green-600" /> :
                         resumeResult.status === 'rejected' ? <XCircle className="w-4 h-4 text-yellow-600" /> :
                         <XCircle className="w-4 h-4 text-red-600" />}
                        <span className="font-medium">
                          Resume: {resumeResult.resume_type} — {resumeResult.status}
                        </span>
                      </div>
                      {resumeResult.original_route && resumeResult.new_route && (
                        <p className="text-xs text-gray-600">
                          Route changed: <span className="line-through">{resumeResult.original_route}</span> → <span className="font-medium text-purple-700">{resumeResult.new_route}</span>
                        </p>
                      )}
                      {resumeResult.error && <p className="text-xs text-red-600 mt-1">{resumeResult.error}</p>}
                      {resumeResult.effective_route && (
                        <p className="text-xs mt-1">
                          <span className="text-gray-500">Executing as: </span>
                          <span className="font-medium text-purple-700">{resumeResult.effective_route}</span>
                          {resumeResult.steps_executed?.find((s: any) => s.duration_ms) && (
                            <span className="text-gray-400 ml-2">
                              ({resumeResult.steps_executed.find((s: any) => s.duration_ms)?.duration_ms}ms)
                            </span>
                          )}
                        </p>
                      )}
                      {resumeResult.orchestrator_response && (
                        <details className="mt-2" open>
                          <summary className="text-xs text-indigo-600 cursor-pointer font-medium">LLM Response</summary>
                          <div className="text-xs text-gray-700 mt-1 bg-white p-2 rounded border whitespace-pre-wrap max-h-64 overflow-auto">
                            {resumeResult.orchestrator_response}
                          </div>
                        </details>
                      )}
                      {resumeResult.metadata?.restored_state && (
                        <details className="mt-2">
                          <summary className="text-[10px] text-gray-400 cursor-pointer">Restored state</summary>
                          <pre className="text-[10px] text-gray-500 mt-1 bg-white p-1 rounded overflow-auto max-h-32">
                            {JSON.stringify(resumeResult.metadata.restored_state, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
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
