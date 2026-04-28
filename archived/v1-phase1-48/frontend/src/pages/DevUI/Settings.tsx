// =============================================================================
// IPA Platform - DevUI Settings Page
// =============================================================================
// Sprint 87: S87-1 - DevUI Core Pages (Placeholder)
//
// Settings page for DevUI configuration.
// Currently a placeholder - full implementation planned for future sprints.
//
// Dependencies:
//   - React
//   - Lucide React icons
// =============================================================================

import { FC } from 'react';
import { Settings as SettingsIcon, Construction } from 'lucide-react';

/**
 * DevUI Settings Page
 * Configuration and preferences (placeholder)
 */
export const Settings: FC = () => {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
            <SettingsIcon className="w-5 h-5 text-gray-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-500">
              Configure DevUI preferences and options.
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
          The Settings feature is currently under development.
          This will provide configuration options for trace retention,
          display preferences, and more.
        </p>
        <div className="mt-6 flex justify-center gap-4">
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            Trace Retention
          </div>
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            Display Options
          </div>
          <div className="px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
            Filters
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
