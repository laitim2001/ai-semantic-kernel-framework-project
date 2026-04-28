// =============================================================================
// IPA Platform - DevUI Event Filter Component
// =============================================================================
// Sprint 89: S89-3 - Event Filtering and Search
//
// UI component for filtering and searching trace events.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC, useState } from 'react';
import {
  Search,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Check,
  Bot,
  Wrench,
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EventSeverity } from '@/types/devtools';

interface EventFilterProps {
  /** Available event types */
  eventTypes: string[];
  /** Selected event types */
  selectedEventTypes: string[];
  /** Available severities */
  severities: EventSeverity[];
  /** Selected severities */
  selectedSeverities: EventSeverity[];
  /** Available executor IDs */
  executorIds: string[];
  /** Selected executor IDs */
  selectedExecutorIds: string[];
  /** Search query */
  searchQuery: string;
  /** Show errors only flag */
  showErrorsOnly: boolean;
  /** Has active filters */
  hasActiveFilters: boolean;
  /** Filter counts */
  filterCounts: {
    total: number;
    filtered: number;
  };
  /** Toggle event type */
  onToggleEventType: (type: string) => void;
  /** Toggle severity */
  onToggleSeverity: (severity: EventSeverity) => void;
  /** Toggle executor ID */
  onToggleExecutorId: (id: string) => void;
  /** Set search query */
  onSearchChange: (query: string) => void;
  /** Set show errors only */
  onShowErrorsOnlyChange: (show: boolean) => void;
  /** Clear all filters */
  onClearFilters: () => void;
  /** Collapsible mode */
  collapsible?: boolean;
  /** Initial collapsed state */
  defaultCollapsed?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get icon for event type
 */
function getEventTypeIcon(type: string) {
  const upperType = type.toUpperCase();
  if (upperType.includes('LLM')) return Bot;
  if (upperType.includes('TOOL')) return Wrench;
  if (upperType.includes('WORKFLOW')) return Settings;
  if (upperType.includes('CHECKPOINT')) return CheckCircle;
  if (upperType.includes('ERROR')) return XCircle;
  if (upperType.includes('WARNING')) return AlertTriangle;
  return Filter;
}

/**
 * Get color for event type
 */
function getEventTypeColor(type: string): string {
  const upperType = type.toUpperCase();
  if (upperType.includes('LLM')) return 'text-purple-600 bg-purple-100';
  if (upperType.includes('TOOL')) return 'text-green-600 bg-green-100';
  if (upperType.includes('WORKFLOW')) return 'text-blue-600 bg-blue-100';
  if (upperType.includes('CHECKPOINT')) return 'text-yellow-600 bg-yellow-100';
  if (upperType.includes('ERROR')) return 'text-red-600 bg-red-100';
  if (upperType.includes('WARNING')) return 'text-orange-600 bg-orange-100';
  return 'text-gray-600 bg-gray-100';
}

/**
 * Severity configuration
 */
const severityConfig: Record<EventSeverity, { label: string; color: string; icon: typeof AlertCircle }> = {
  debug: { label: 'Debug', color: 'text-gray-500 bg-gray-100', icon: Settings },
  info: { label: 'Info', color: 'text-blue-500 bg-blue-100', icon: AlertCircle },
  warning: { label: 'Warning', color: 'text-yellow-600 bg-yellow-100', icon: AlertTriangle },
  error: { label: 'Error', color: 'text-red-600 bg-red-100', icon: XCircle },
  critical: { label: 'Critical', color: 'text-red-700 bg-red-200', icon: AlertCircle },
};

/**
 * Event Filter Component
 */
export const EventFilter: FC<EventFilterProps> = ({
  eventTypes,
  selectedEventTypes,
  severities,
  selectedSeverities,
  executorIds,
  selectedExecutorIds,
  searchQuery,
  showErrorsOnly,
  hasActiveFilters,
  filterCounts,
  onToggleEventType,
  onToggleSeverity,
  onToggleExecutorId,
  onSearchChange,
  onShowErrorsOnlyChange,
  onClearFilters,
  collapsible = true,
  defaultCollapsed = false,
  className,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [expandedSection, setExpandedSection] = useState<string | null>('types');

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className={cn('bg-white border border-gray-200 rounded-lg', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">篩選器</span>
          {hasActiveFilters && (
            <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded">
              {filterCounts.filtered} / {filterCounts.total}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              清除
            </button>
          )}
          {collapsible && (
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              {isCollapsed ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronUp className="w-4 h-4 text-gray-500" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Filter content */}
      {!isCollapsed && (
        <div className="p-3 space-y-4">
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="搜索事件..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Quick filters */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onShowErrorsOnlyChange(!showErrorsOnly)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full border transition-colors',
                showErrorsOnly
                  ? 'bg-red-100 border-red-200 text-red-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              )}
            >
              <XCircle className="w-3.5 h-3.5" />
              僅顯示錯誤
            </button>
          </div>

          {/* Event types section */}
          <div className="border border-gray-100 rounded-lg">
            <button
              onClick={() => toggleSection('types')}
              className="w-full flex items-center justify-between p-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <span>事件類型 {selectedEventTypes.length > 0 && `(${selectedEventTypes.length})`}</span>
              {expandedSection === 'types' ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
            {expandedSection === 'types' && (
              <div className="p-2 pt-0 space-y-1 max-h-48 overflow-y-auto">
                {eventTypes.map((type) => {
                  const Icon = getEventTypeIcon(type);
                  const isSelected = selectedEventTypes.includes(type);
                  return (
                    <button
                      key={type}
                      onClick={() => onToggleEventType(type)}
                      className={cn(
                        'w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded transition-colors',
                        isSelected
                          ? getEventTypeColor(type)
                          : 'text-gray-600 hover:bg-gray-50'
                      )}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span className="flex-1 text-left truncate">{type}</span>
                      {isSelected && <Check className="w-3.5 h-3.5" />}
                    </button>
                  );
                })}
                {eventTypes.length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-2">無可用選項</p>
                )}
              </div>
            )}
          </div>

          {/* Severity section */}
          <div className="border border-gray-100 rounded-lg">
            <button
              onClick={() => toggleSection('severity')}
              className="w-full flex items-center justify-between p-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <span>嚴重性 {selectedSeverities.length > 0 && `(${selectedSeverities.length})`}</span>
              {expandedSection === 'severity' ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
            {expandedSection === 'severity' && (
              <div className="p-2 pt-0 space-y-1">
                {severities.map((severity) => {
                  const config = severityConfig[severity];
                  const Icon = config.icon;
                  const isSelected = selectedSeverities.includes(severity);
                  return (
                    <button
                      key={severity}
                      onClick={() => onToggleSeverity(severity)}
                      className={cn(
                        'w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded transition-colors',
                        isSelected ? config.color : 'text-gray-600 hover:bg-gray-50'
                      )}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span className="flex-1 text-left">{config.label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Executor IDs section (if any) */}
          {executorIds.length > 0 && (
            <div className="border border-gray-100 rounded-lg">
              <button
                onClick={() => toggleSection('executors')}
                className="w-full flex items-center justify-between p-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <span>執行器 {selectedExecutorIds.length > 0 && `(${selectedExecutorIds.length})`}</span>
                {expandedSection === 'executors' ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>
              {expandedSection === 'executors' && (
                <div className="p-2 pt-0 space-y-1 max-h-32 overflow-y-auto">
                  {executorIds.map((id) => {
                    const isSelected = selectedExecutorIds.includes(id);
                    return (
                      <button
                        key={id}
                        onClick={() => onToggleExecutorId(id)}
                        className={cn(
                          'w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded transition-colors',
                          isSelected
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        )}
                      >
                        <span className="flex-1 text-left truncate font-mono text-xs">{id}</span>
                        {isSelected && <Check className="w-3.5 h-3.5" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Compact filter bar for inline use
 */
export const FilterBar: FC<{
  searchQuery: string;
  hasActiveFilters: boolean;
  filterCount: number;
  totalCount: number;
  onSearchChange: (query: string) => void;
  onOpenFilters?: () => void;
  onClearFilters: () => void;
  className?: string;
}> = ({
  searchQuery,
  hasActiveFilters,
  filterCount,
  totalCount,
  onSearchChange,
  onOpenFilters,
  onClearFilters,
  className,
}) => (
  <div className={cn('flex items-center gap-2', className)}>
    {/* Search */}
    <div className="relative flex-1">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="搜索事件..."
        className="w-full pl-9 pr-4 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
      />
    </div>

    {/* Filter button */}
    {onOpenFilters && (
      <button
        onClick={onOpenFilters}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors',
          hasActiveFilters
            ? 'bg-purple-50 border-purple-200 text-purple-700'
            : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
        )}
      >
        <Filter className="w-4 h-4" />
        篩選
        {hasActiveFilters && (
          <span className="ml-1 px-1.5 py-0.5 text-xs bg-purple-200 rounded">
            {filterCount}/{totalCount}
          </span>
        )}
      </button>
    )}

    {/* Clear button */}
    {hasActiveFilters && (
      <button
        onClick={onClearFilters}
        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
        title="清除篩選"
      >
        <X className="w-4 h-4" />
      </button>
    )}
  </div>
);

export default EventFilter;
