// =============================================================================
// IPA Platform - DevUI Live Monitor Page
// =============================================================================
// Sprint 87: S87-1 - DevUI Core Pages (Placeholder)
//
// Live monitoring page for real-time execution tracking.
// Currently a placeholder - full implementation planned for future sprints.
//
// Dependencies:
//   - React
//   - Lucide React icons
// =============================================================================

import { FC } from 'react';
import { Activity, Construction } from 'lucide-react';

/**
 * DevUI Live Monitor Page
 * Real-time execution monitoring (placeholder)
 */
export const LiveMonitor: FC = () => {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Activity className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Live Monitor</h1>
            <p className="text-gray-500">
              Real-time execution monitoring and event streaming.
            </p>
          </div>
        </div>
      </div>

      {/* Coming Soon Notice */}
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        <Construction className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Coming Soon
        </h2>
        <p className="text-gray-500 max-w-md mx-auto">
          The Live Monitor feature is currently under development.
          This will provide real-time WebSocket-based execution tracking
          and event streaming.
        </p>
        <div className="mt-6 flex justify-center gap-4">
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            WebSocket Events
          </div>
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            Real-time Updates
          </div>
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            Live Metrics
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveMonitor;
