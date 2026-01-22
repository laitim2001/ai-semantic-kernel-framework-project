// =============================================================================
// IPA Platform - DevUI AG-UI Test Panel
// =============================================================================
// Sprint 99: AG-UI Feature Testing Panel
//
// Interactive testing panel for all AG-UI features:
// - Feature 1: Agentic Chat (standard messaging)
// - Feature 2: Tool Rendering (tool call display)
// - Feature 3: Human-in-the-Loop (HITL approval flow)
// - Feature 4: Generative UI (workflow progress)
// - Feature 5: Tool-based UI (dynamic UI components)
// - Feature 6: Shared State (automatic)
// - Feature 7: Predictive Updates (prediction events)
//
// Dependencies:
//   - React, Lucide React icons
//   - API client for backend calls
// =============================================================================

import { FC, useState, useCallback } from 'react';
import {
  TestTube2,
  MessageSquare,
  Wrench,
  ShieldCheck,
  Sparkles,
  LayoutGrid,
  Share2,
  Zap,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

/**
 * Test result status
 */
type TestStatus = 'idle' | 'running' | 'success' | 'error';

/**
 * AG-UI Feature interface
 */
interface AGUIFeature {
  id: number;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  testEndpoint?: string;
  testDescription: string;
  manualTest?: boolean;
}

/**
 * AG-UI features list
 */
const AGUI_FEATURES: AGUIFeature[] = [
  {
    id: 1,
    name: 'Agentic Chat',
    description: 'Standard agent messaging with streaming responses',
    icon: MessageSquare,
    testDescription: 'Go to /chat and send a message to test agent responses',
    manualTest: true,
  },
  {
    id: 2,
    name: 'Tool Rendering',
    description: 'Display tool calls with parameters and results',
    icon: Wrench,
    testDescription: 'Ask Claude to search or read files to trigger tool calls',
    manualTest: true,
  },
  {
    id: 3,
    name: 'Human-in-the-Loop',
    description: 'HITL approval flow for high-risk operations',
    icon: ShieldCheck,
    testEndpoint: '/api/v1/ag-ui/test/hitl/stream',
    testDescription: 'Triggers HITL approval event for testing approval dialog',
  },
  {
    id: 4,
    name: 'Generative UI',
    description: 'Dynamic workflow progress indicators',
    icon: Sparkles,
    testEndpoint: '/api/v1/ag-ui/test/workflow-progress/stream',
    testDescription: 'Sends workflow_progress events to test progress panel',
  },
  {
    id: 5,
    name: 'Tool-based UI',
    description: 'Agent-requested dynamic UI components',
    icon: LayoutGrid,
    testEndpoint: '/api/v1/ag-ui/test/ui-component/stream',
    testDescription: 'Streams a test UI component via SSE',
  },
  {
    id: 6,
    name: 'Shared State',
    description: 'Synchronized state between agent and UI',
    icon: Share2,
    testDescription: 'Automatic - state syncs during any agent interaction',
    manualTest: true,
  },
  {
    id: 7,
    name: 'Predictive Updates',
    description: 'Show pending changes before confirmation',
    icon: Zap,
    testEndpoint: '/api/v1/ag-ui/test/prediction/stream',
    testDescription: 'Sends prediction_update events for optimistic UI',
  },
];

/**
 * Test result interface
 */
interface TestResult {
  featureId: number;
  status: TestStatus;
  message?: string;
  timestamp?: Date;
}

/**
 * AGUITestPanel Component
 * Interactive testing panel for all AG-UI features
 */
export const AGUITestPanel: FC = () => {
  const [testResults, setTestResults] = useState<Map<number, TestResult>>(new Map());
  const [selectedThread, setSelectedThread] = useState<string>('');

  /**
   * Run test for a specific feature
   */
  const runTest = useCallback(async (feature: AGUIFeature) => {
    if (feature.manualTest || !feature.testEndpoint) {
      // Manual test - just update status
      setTestResults((prev) => {
        const newMap = new Map(prev);
        newMap.set(feature.id, {
          featureId: feature.id,
          status: 'success',
          message: 'Manual test - check /chat page',
          timestamp: new Date(),
        });
        return newMap;
      });
      return;
    }

    // Set running status
    setTestResults((prev) => {
      const newMap = new Map(prev);
      newMap.set(feature.id, {
        featureId: feature.id,
        status: 'running',
        timestamp: new Date(),
      });
      return newMap;
    });

    try {
      // Call test endpoint
      const threadId = selectedThread || `test-thread-${Date.now()}`;

      let response: Response;

      if (feature.id === 5) {
        // Tool-based UI - SSE stream test
        response = await fetch(feature.testEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            component_type: 'table',
            title: 'Test Data Table',
            props: {
              columns: [
                { key: 'id', label: 'ID' },
                { key: 'name', label: 'Name' },
                { key: 'status', label: 'Status' },
              ],
              rows: [
                { id: '1', name: 'Test Item 1', status: 'Active' },
                { id: '2', name: 'Test Item 2', status: 'Pending' },
              ],
            },
            thread_id: threadId,
          }),
        });
      } else if (feature.id === 3) {
        // HITL test
        response = await fetch(feature.testEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            tool_name: 'Bash',
            tool_input: { command: 'rm -rf /test' },
            risk_level: 'high',
          }),
        });
      } else if (feature.id === 4) {
        // Workflow progress test (using TestWorkflowProgressRequest schema)
        response = await fetch(feature.testEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            workflow_name: 'Test Workflow',
            total_steps: 3,
            current_step: 1,
            step_status: 'in_progress',
          }),
        });
      } else if (feature.id === 7) {
        // Prediction test
        response = await fetch(feature.testEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            prediction_type: 'file_edit',
            file_path: '/test/example.ts',
            preview: '// New content here',
          }),
        });
      } else {
        throw new Error('Unknown test endpoint');
      }

      if (response.ok) {
        const data = response.headers.get('content-type')?.includes('text/event-stream')
          ? { message: 'SSE stream started successfully' }
          : await response.json();

        setTestResults((prev) => {
          const newMap = new Map(prev);
          newMap.set(feature.id, {
            featureId: feature.id,
            status: 'success',
            message: data.message || 'Test passed',
            timestamp: new Date(),
          });
          return newMap;
        });
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Test failed');
      }
    } catch (error) {
      setTestResults((prev) => {
        const newMap = new Map(prev);
        newMap.set(feature.id, {
          featureId: feature.id,
          status: 'error',
          message: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date(),
        });
        return newMap;
      });
    }
  }, [selectedThread]);

  /**
   * Reset all test results
   */
  const resetTests = useCallback(() => {
    setTestResults(new Map());
  }, []);

  /**
   * Get status icon for a feature
   */
  const getStatusIcon = (featureId: number) => {
    const result = testResults.get(featureId);
    if (!result) return null;

    switch (result.status) {
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
              <TestTube2 className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AG-UI Test Panel</h1>
              <p className="text-gray-500">
                Test all 7 AG-UI features interactively
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={resetTests}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reset
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => window.open('/chat', '_blank')}
              className="gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Open Chat
            </Button>
          </div>
        </div>
      </div>

      {/* Thread ID Input */}
      <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Thread ID (optional)
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={selectedThread}
            onChange={(e) => setSelectedThread(e.target.value)}
            placeholder="Enter thread ID or leave empty for auto-generated"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedThread(`test-${Date.now()}`)}
          >
            Generate
          </Button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Use the same thread ID as your /chat session to see events there
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {AGUI_FEATURES.map((feature) => {
          const result = testResults.get(feature.id);
          const Icon = feature.icon;

          return (
            <div
              key={feature.id}
              className={cn(
                'bg-white rounded-lg border p-4 transition-all',
                result?.status === 'success' && 'border-green-200 bg-green-50/30',
                result?.status === 'error' && 'border-red-200 bg-red-50/30',
                result?.status === 'running' && 'border-blue-200 bg-blue-50/30',
                !result && 'border-gray-200 hover:border-purple-200'
              )}
            >
              {/* Feature Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      result?.status === 'success' && 'bg-green-100',
                      result?.status === 'error' && 'bg-red-100',
                      result?.status === 'running' && 'bg-blue-100',
                      !result && 'bg-gray-100'
                    )}
                  >
                    <Icon className="w-4 h-4 text-gray-600" />
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">Feature {feature.id}</span>
                    <h3 className="font-medium text-gray-900">{feature.name}</h3>
                  </div>
                </div>
                {getStatusIcon(feature.id)}
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 mb-3">{feature.description}</p>

              {/* Test Info */}
              <div className="bg-gray-50 rounded-lg p-2 mb-3">
                <p className="text-xs text-gray-500">{feature.testDescription}</p>
              </div>

              {/* Result Message */}
              {result?.message && (
                <div
                  className={cn(
                    'text-xs px-2 py-1 rounded mb-3',
                    result.status === 'success' && 'bg-green-100 text-green-700',
                    result.status === 'error' && 'bg-red-100 text-red-700'
                  )}
                >
                  {result.message}
                </div>
              )}

              {/* Action Button */}
              <Button
                variant={feature.manualTest ? 'outline' : 'default'}
                size="sm"
                className="w-full gap-2"
                onClick={() => runTest(feature)}
                disabled={result?.status === 'running'}
              >
                {result?.status === 'running' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    {feature.manualTest ? 'Mark as Tested' : 'Run Test'}
                  </>
                )}
              </Button>
            </div>
          );
        })}
      </div>

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 rounded-lg border border-blue-200 p-4">
        <h3 className="font-medium text-blue-900 mb-2">Testing Instructions</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Features 1, 2, 6</strong>: Manual tests - interact with /chat page</li>
          <li>• <strong>Features 3, 4, 5, 7</strong>: API tests - click "Run Test" to trigger events</li>
          <li>• Open /chat in a new tab and use the same Thread ID to see events in real-time</li>
          <li>• HITL test requires Write/Edit/Bash tool calls to trigger approval dialog</li>
        </ul>
      </div>
    </div>
  );
};

export default AGUITestPanel;
