/**
 * SharedStateDemo - Shared State Feature Demo
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Demonstrates AG-UI Feature 6: Frontend-Backend State Synchronization.
 */

import { FC, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import type { EventLogEntry } from './EventLogPanel';

export interface SharedStateDemoProps {
  /** Callback when event occurs */
  onEvent?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

interface DemoState {
  counter: number;
  text: string;
  items: string[];
  lastUpdated: string;
  source: 'client' | 'server';
}

/**
 * SharedStateDemo Component
 *
 * Interactive demo of state synchronization between frontend and backend.
 */
export const SharedStateDemo: FC<SharedStateDemoProps> = ({
  onEvent,
  className = '',
}) => {
  const [state, setState] = useState<DemoState>({
    counter: 0,
    text: '',
    items: ['Item A', 'Item B'],
    lastUpdated: new Date().toISOString(),
    source: 'client',
  });
  const [newItem, setNewItem] = useState('');
  const [syncStatus, setSyncStatus] = useState<'synced' | 'pending' | 'syncing'>('synced');

  // Update state and emit event
  const updateState = useCallback((updates: Partial<DemoState>, source: 'client' | 'server' = 'client') => {
    setSyncStatus('syncing');

    setState((prev) => ({
      ...prev,
      ...updates,
      lastUpdated: new Date().toISOString(),
      source,
    }));

    // Simulate sync delay
    setTimeout(() => setSyncStatus('synced'), 300);

    onEvent?.({
      id: `evt_${Date.now()}`,
      type: source === 'client' ? 'STATE_DELTA' : 'STATE_SNAPSHOT',
      timestamp: new Date().toISOString(),
      data: { updates, source },
    });
  }, [onEvent]);

  // Increment counter
  const incrementCounter = () => {
    updateState({ counter: state.counter + 1 });
  };

  // Decrement counter
  const decrementCounter = () => {
    updateState({ counter: state.counter - 1 });
  };

  // Update text
  const handleTextChange = (text: string) => {
    updateState({ text });
  };

  // Add item
  const addItem = () => {
    if (newItem.trim()) {
      updateState({ items: [...state.items, newItem.trim()] });
      setNewItem('');
    }
  };

  // Remove item
  const removeItem = (index: number) => {
    updateState({ items: state.items.filter((_, i) => i !== index) });
  };

  // Simulate server update
  const simulateServerUpdate = () => {
    updateState({
      counter: Math.floor(Math.random() * 100),
      text: 'Updated from server',
      items: [...state.items, `Server Item ${Date.now() % 1000}`],
    }, 'server');
  };

  return (
    <div className={`flex flex-col h-full ${className}`} data-testid="shared-state-demo">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Feature 6: Shared State</h3>
        <p className="text-sm text-gray-500">
          Real-time state synchronization between frontend and backend.
        </p>
      </div>

      {/* Sync Status */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-500">Sync Status:</span>
        <div className={`
          px-2 py-1 rounded text-sm font-medium
          ${syncStatus === 'synced' ? 'bg-green-100 text-green-700' :
            syncStatus === 'syncing' ? 'bg-blue-100 text-blue-700 animate-pulse' :
            'bg-yellow-100 text-yellow-700'}
        `}>
          {syncStatus === 'synced' ? '✓ Synced' :
           syncStatus === 'syncing' ? '↻ Syncing...' :
           '⏳ Pending'}
        </div>
        <Button variant="outline" size="sm" onClick={simulateServerUpdate}>
          Simulate Server Update
        </Button>
      </div>

      {/* State Controls */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Counter */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm font-medium text-gray-500 mb-2">Counter</div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={decrementCounter}>-</Button>
            <span className="text-2xl font-bold w-16 text-center">{state.counter}</span>
            <Button variant="outline" size="sm" onClick={incrementCounter}>+</Button>
          </div>
        </div>

        {/* Text Input */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm font-medium text-gray-500 mb-2">Text Field</div>
          <Input
            value={state.text}
            onChange={(e) => handleTextChange(e.target.value)}
            placeholder="Type something..."
          />
        </div>
      </div>

      {/* Items List */}
      <div className="p-4 bg-gray-50 rounded-lg mb-4">
        <div className="text-sm font-medium text-gray-500 mb-2">Items List</div>
        <div className="flex gap-2 mb-2">
          <Input
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            placeholder="New item..."
            onKeyDown={(e) => e.key === 'Enter' && addItem()}
          />
          <Button variant="default" size="sm" onClick={addItem}>Add</Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {state.items.map((item, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded border"
            >
              {item}
              <button
                className="text-gray-400 hover:text-red-500"
                onClick={() => removeItem(index)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* State Debugger - Simple JSON Display */}
      <div className="flex-1 min-h-0 p-4 bg-gray-900 rounded-lg overflow-auto">
        <div className="text-xs font-medium text-gray-400 mb-2">Current State</div>
        <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap">
          {JSON.stringify(state, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default SharedStateDemo;
