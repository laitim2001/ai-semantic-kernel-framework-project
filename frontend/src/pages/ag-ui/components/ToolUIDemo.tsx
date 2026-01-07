/**
 * ToolUIDemo - Tool-based UI Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 5: Tool-based Dynamic UI.
 */

import { FC, useState } from 'react';
import {
  DynamicForm,
  DynamicChart,
  DynamicCard,
  DynamicTable,
} from '@/components/ag-ui/advanced';
import { Button } from '@/components/ui/Button';
import type { EventLogEntry } from './EventLogPanel';

export interface ToolUIDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

type UIType = 'form' | 'chart' | 'card' | 'table';

/**
 * ToolUIDemo Component
 *
 * Interactive demo of tool-generated UI components.
 */
export const ToolUIDemo: FC<ToolUIDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [activeUI, setActiveUI] = useState<UIType>('form');
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  // Handle form submit
  const handleFormSubmit = (data: Record<string, unknown>) => {
    setFormData(data);
    onEvent?.({
      id: `evt_${Date.now()}`,
      type: 'CUSTOM',
      timestamp: new Date().toISOString(),
      data: { event_name: 'FORM_SUBMIT', form_data: data },
    });
  };

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="tool-ui-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 5: Tool-based UI</h3>
        <p className="text-sm text-gray-500">
          Dynamically generated UI components: forms, charts, cards, tables.
        </p>
      </div>

      {/* Type Selector */}
      <div className="flex gap-2 mb-4">
        {(['form', 'chart', 'card', 'table'] as UIType[]).map((type) => (
          <Button
            key={type}
            variant={activeUI === type ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveUI(type)}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </Button>
        ))}
      </div>

      {/* Dynamic UI Display */}
      <div className="flex-1 overflow-y-auto border rounded-lg p-4 bg-white">
        {activeUI === 'form' && (
          <DynamicForm
            fields={[
              { name: 'name', label: 'Full Name', fieldType: 'text', required: true, placeholder: 'Enter your name' },
              { name: 'email', label: 'Email', fieldType: 'email', required: true, placeholder: 'Enter your email' },
              { name: 'role', label: 'Role', fieldType: 'select', required: false, options: [
                { label: 'Developer', value: 'dev' },
                { label: 'Designer', value: 'design' },
                { label: 'Manager', value: 'manager' },
              ]},
              { name: 'bio', label: 'Bio', fieldType: 'textarea', required: false, placeholder: 'Tell us about yourself' },
            ]}
            submitLabel="Register"
            onSubmit={handleFormSubmit}
          />
        )}

        {activeUI === 'chart' && (
          <DynamicChart
            chartType="bar"
            data={{
              labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
              datasets: [
                {
                  label: 'Revenue ($)',
                  data: [12000, 19000, 15000, 25000, 22000, 30000],
                  backgroundColor: '#3b82f6',
                },
              ],
            }}
          />
        )}

        {activeUI === 'card' && (
          <div className="grid grid-cols-2 gap-4">
            <DynamicCard
              title="Project Alpha"
              subtitle="Active Development"
              content="A revolutionary AI-powered platform for enterprise automation."
              actions={[
                { label: 'View Details', action: 'view', variant: 'default' },
                { label: 'Edit', action: 'edit', variant: 'outline' },
              ]}
              onAction={(action) => {
                onEvent?.({
                  id: `evt_${Date.now()}`,
                  type: 'CUSTOM',
                  timestamp: new Date().toISOString(),
                  data: { event_name: 'CARD_ACTION', action },
                });
              }}
            />
            <DynamicCard
              title="Project Beta"
              subtitle="Planning Phase"
              content="Next-generation data analytics dashboard."
              actions={[
                { label: 'View Details', action: 'view', variant: 'default' },
              ]}
            />
          </div>
        )}

        {activeUI === 'table' && (
          <DynamicTable
            columns={[
              { key: 'id', header: 'ID', sortable: true, filterable: false, width: '60px' },
              { key: 'name', header: 'Name', sortable: true, filterable: true },
              { key: 'email', header: 'Email', sortable: false, filterable: true },
              { key: 'role', header: 'Role', sortable: true, filterable: false },
              { key: 'status', header: 'Status', sortable: true, filterable: false },
            ]}
            rows={[
              { id: 1, name: 'Alice Chen', email: 'alice@example.com', role: 'Admin', status: 'Active' },
              { id: 2, name: 'Bob Wang', email: 'bob@example.com', role: 'Developer', status: 'Active' },
              { id: 3, name: 'Charlie Liu', email: 'charlie@example.com', role: 'Designer', status: 'Inactive' },
              { id: 4, name: 'Diana Zhang', email: 'diana@example.com', role: 'Manager', status: 'Active' },
            ]}
            pagination
            pageSize={10}
          />
        )}
      </div>

      {/* Form Data Display */}
      {activeUI === 'form' && Object.keys(formData).length > 0 && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-500 mb-2">Submitted Data</div>
          <pre className="text-xs font-mono">{JSON.stringify(formData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default ToolUIDemo;
