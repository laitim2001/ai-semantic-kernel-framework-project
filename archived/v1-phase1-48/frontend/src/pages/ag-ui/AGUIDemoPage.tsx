/**
 * AGUIDemoPage - AG-UI Protocol Demo Page
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Main demo page showcasing all 7 AG-UI features.
 * Layout: Left side (8 cols) for feature demos, Right side (4 cols) for event log.
 */

import { FC, useState, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  EventLogPanel,
  EventLogEntry,
  AgenticChatDemo,
  ToolRenderingDemo,
  HITLDemo,
  GenerativeUIDemo,
  ToolUIDemo,
  SharedStateDemo,
  PredictiveDemo,
} from './components';

/** Feature tab configuration */
interface FeatureTab {
  id: string;
  label: string;
  shortLabel: string;
  icon: string;
  description: string;
}

const featureTabs: FeatureTab[] = [
  { id: 'chat', label: 'Agentic Chat', shortLabel: 'Chat', icon: '💬', description: 'Interactive AI chat with streaming' },
  { id: 'tool', label: 'Tool Rendering', shortLabel: 'Tools', icon: '🔧', description: 'Tool call result visualization' },
  { id: 'hitl', label: 'Human-in-the-Loop', shortLabel: 'HITL', icon: '🛡️', description: 'Risk-based approval workflow' },
  { id: 'generative', label: 'Generative UI', shortLabel: 'Gen UI', icon: '✨', description: 'Dynamic UI generation' },
  { id: 'toolui', label: 'Tool-based UI', shortLabel: 'Tool UI', icon: '📊', description: 'Form, chart, card, table' },
  { id: 'state', label: 'Shared State', shortLabel: 'State', icon: '🔄', description: 'Frontend-backend sync' },
  { id: 'predictive', label: 'Predictive', shortLabel: 'Predict', icon: '⚡', description: 'Optimistic updates' },
];

/**
 * AGUIDemoPage Component
 *
 * Main AG-UI demo page with tabbed feature navigation and event log.
 */
export const AGUIDemoPage: FC = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [events, setEvents] = useState<EventLogEntry[]>([]);
  const [threadId] = useState(() => `thread_${Date.now()}`);

  // Add event to log
  const handleEvent = useCallback((event: EventLogEntry) => {
    setEvents((prev) => [...prev.slice(-99), event]);
  }, []);

  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  // Get active tab info
  const activeTabInfo = useMemo(
    () => featureTabs.find((t) => t.id === activeTab) || featureTabs[0],
    [activeTab]
  );

  // Render active demo
  const renderDemo = () => {
    const props = { onEvent: handleEvent };

    switch (activeTab) {
      case 'chat':
        return <AgenticChatDemo threadId={threadId} {...props} />;
      case 'tool':
        return <ToolRenderingDemo {...props} />;
      case 'hitl':
        return <HITLDemo {...props} />;
      case 'generative':
        return <GenerativeUIDemo {...props} />;
      case 'toolui':
        return <ToolUIDemo {...props} />;
      case 'state':
        return <SharedStateDemo {...props} />;
      case 'predictive':
        return <PredictiveDemo {...props} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100" data-testid="ag-ui-demo-page">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AG-UI Protocol Demo</h1>
            <p className="text-sm text-gray-500">
              Interactive showcase of all 7 AG-UI features
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline">Thread: {threadId.slice(-12)}</Badge>
            <Badge variant="default">Phase 15</Badge>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* Left Panel - Feature Demo (8 cols) */}
        <div className="flex-[2] flex flex-col bg-white rounded-lg border overflow-hidden">
          {/* Tab Navigation */}
          <div className="flex items-center gap-1 p-2 bg-gray-50 border-b overflow-x-auto">
            {featureTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap
                  transition-colors
                  ${activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                  }
                `}
                data-testid={`tab-${tab.id}`}
              >
                <span>{tab.icon}</span>
                <span className="hidden lg:inline">{tab.label}</span>
                <span className="lg:hidden">{tab.shortLabel}</span>
              </button>
            ))}
          </div>

          {/* Active Tab Description */}
          <div className="px-4 py-3 bg-blue-50 border-b">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{activeTabInfo.icon}</span>
              <div>
                <div className="font-medium text-blue-900">{activeTabInfo.label}</div>
                <div className="text-sm text-blue-700">{activeTabInfo.description}</div>
              </div>
            </div>
          </div>

          {/* Demo Content */}
          <div className="flex-1 overflow-hidden p-4">
            {renderDemo()}
          </div>
        </div>

        {/* Right Panel - Event Log (4 cols) */}
        <div className="flex-1 flex flex-col min-w-[300px] max-w-[400px]">
          {/* Event Log Header */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Event Log</span>
            <Button variant="outline" size="sm" onClick={clearEvents}>
              Clear
            </Button>
          </div>

          {/* Event Log Panel */}
          <EventLogPanel
            events={events}
            maxEntries={100}
            autoScroll
            className="flex-1"
          />
        </div>
      </main>

      {/* Footer Status Bar */}
      <footer className="bg-gray-800 text-white px-6 py-2 text-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full" />
            Connected
          </span>
          <span>|</span>
          <span>Mode: Demo</span>
          <span>|</span>
          <span>Events: {events.length}</span>
        </div>
        <div>
          <span className="text-gray-400">
            Sprint 61 - AG-UI Frontend Integration
          </span>
        </div>
      </footer>
    </div>
  );
};

export default AGUIDemoPage;
