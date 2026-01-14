// =============================================================================
// IPA Platform - Event Filter Hook
// =============================================================================
// Sprint 89: S89-3 - Event Filtering and Search
//
// Hook for managing event filtering with URL sync support.
//
// Dependencies:
//   - React Router (for URL sync)
// =============================================================================

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { TraceEvent, EventSeverity } from '@/types/devtools';

/**
 * Filter state
 */
export interface EventFilterState {
  /** Selected event types (empty = all) */
  eventTypes: string[];
  /** Selected severity levels (empty = all) */
  severities: EventSeverity[];
  /** Selected executor IDs (empty = all) */
  executorIds: string[];
  /** Text search query */
  searchQuery: string;
  /** Show only errors */
  showErrorsOnly: boolean;
  /** Time range filter (ms from start) */
  timeRange?: {
    start: number;
    end: number;
  };
}

/**
 * Hook options
 */
export interface UseEventFilterOptions {
  /** Sync filters to URL */
  syncToUrl?: boolean;
  /** Initial filter state */
  initialState?: Partial<EventFilterState>;
  /** Debounce delay for search (ms) */
  searchDebounceMs?: number;
}

/**
 * Hook return type
 */
export interface UseEventFilterReturn {
  /** Current filter state */
  filters: EventFilterState;
  /** Filtered events */
  filteredEvents: TraceEvent[];
  /** Filter counts */
  filterCounts: {
    total: number;
    filtered: number;
    byType: Record<string, number>;
    bySeverity: Record<string, number>;
  };
  /** Available filter options (extracted from events) */
  filterOptions: {
    eventTypes: string[];
    severities: EventSeverity[];
    executorIds: string[];
  };
  /** Has any active filters */
  hasActiveFilters: boolean;
  /** Set event type filter */
  setEventTypes: (types: string[]) => void;
  /** Toggle event type */
  toggleEventType: (type: string) => void;
  /** Set severity filter */
  setSeverities: (severities: EventSeverity[]) => void;
  /** Toggle severity */
  toggleSeverity: (severity: EventSeverity) => void;
  /** Set executor ID filter */
  setExecutorIds: (ids: string[]) => void;
  /** Toggle executor ID */
  toggleExecutorId: (id: string) => void;
  /** Set search query */
  setSearchQuery: (query: string) => void;
  /** Set show errors only */
  setShowErrorsOnly: (show: boolean) => void;
  /** Set time range */
  setTimeRange: (range: { start: number; end: number } | undefined) => void;
  /** Clear all filters */
  clearFilters: () => void;
  /** Clear specific filter */
  clearFilter: (filterKey: keyof EventFilterState) => void;
}

/**
 * Default filter state
 */
const defaultFilterState: EventFilterState = {
  eventTypes: [],
  severities: [],
  executorIds: [],
  searchQuery: '',
  showErrorsOnly: false,
  timeRange: undefined,
};

/**
 * Event filter hook
 */
export function useEventFilter(
  events: TraceEvent[],
  options: UseEventFilterOptions = {}
): UseEventFilterReturn {
  const {
    syncToUrl = false,
    initialState = {},
    searchDebounceMs: _searchDebounceMs = 300,
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL or defaults
  const getInitialState = useCallback((): EventFilterState => {
    if (syncToUrl) {
      const urlEventTypes = searchParams.get('types')?.split(',').filter(Boolean) || [];
      const urlSeverities = searchParams.get('severities')?.split(',').filter(Boolean) as EventSeverity[] || [];
      const urlExecutorIds = searchParams.get('executors')?.split(',').filter(Boolean) || [];
      const urlSearch = searchParams.get('search') || '';
      const urlErrorsOnly = searchParams.get('errorsOnly') === 'true';

      return {
        eventTypes: urlEventTypes.length > 0 ? urlEventTypes : initialState.eventTypes || [],
        severities: urlSeverities.length > 0 ? urlSeverities : initialState.severities || [],
        executorIds: urlExecutorIds.length > 0 ? urlExecutorIds : initialState.executorIds || [],
        searchQuery: urlSearch || initialState.searchQuery || '',
        showErrorsOnly: urlErrorsOnly || initialState.showErrorsOnly || false,
        timeRange: initialState.timeRange,
      };
    }
    return { ...defaultFilterState, ...initialState };
  }, [searchParams, syncToUrl, initialState]);

  const [filters, setFilters] = useState<EventFilterState>(getInitialState);

  // Sync to URL when filters change
  useEffect(() => {
    if (!syncToUrl) return;

    const newParams = new URLSearchParams(searchParams);

    if (filters.eventTypes.length > 0) {
      newParams.set('types', filters.eventTypes.join(','));
    } else {
      newParams.delete('types');
    }

    if (filters.severities.length > 0) {
      newParams.set('severities', filters.severities.join(','));
    } else {
      newParams.delete('severities');
    }

    if (filters.executorIds.length > 0) {
      newParams.set('executors', filters.executorIds.join(','));
    } else {
      newParams.delete('executors');
    }

    if (filters.searchQuery) {
      newParams.set('search', filters.searchQuery);
    } else {
      newParams.delete('search');
    }

    if (filters.showErrorsOnly) {
      newParams.set('errorsOnly', 'true');
    } else {
      newParams.delete('errorsOnly');
    }

    setSearchParams(newParams, { replace: true });
  }, [filters, syncToUrl, searchParams, setSearchParams]);

  // Extract available filter options from events
  const filterOptions = useMemo(() => {
    const types = new Set<string>();
    const severities = new Set<EventSeverity>();
    const executors = new Set<string>();

    events.forEach((event) => {
      types.add(event.event_type);
      severities.add(event.severity);
      if (event.executor_id) {
        executors.add(event.executor_id);
      }
    });

    return {
      eventTypes: Array.from(types).sort(),
      severities: Array.from(severities) as EventSeverity[],
      executorIds: Array.from(executors).sort(),
    };
  }, [events]);

  // Apply filters to events
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      // Event type filter
      if (filters.eventTypes.length > 0 && !filters.eventTypes.includes(event.event_type)) {
        return false;
      }

      // Severity filter
      if (filters.severities.length > 0 && !filters.severities.includes(event.severity)) {
        return false;
      }

      // Executor ID filter
      if (filters.executorIds.length > 0) {
        if (!event.executor_id || !filters.executorIds.includes(event.executor_id)) {
          return false;
        }
      }

      // Errors only filter
      if (filters.showErrorsOnly) {
        if (event.severity !== 'error' && event.severity !== 'critical') {
          return false;
        }
      }

      // Text search filter
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const searchableText = [
          event.event_type,
          event.executor_id,
          JSON.stringify(event.data),
          ...event.tags,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();

        if (!searchableText.includes(query)) {
          return false;
        }
      }

      // Time range filter
      if (filters.timeRange) {
        const eventTime = new Date(event.timestamp).getTime();
        const firstEventTime = events.length > 0 ? new Date(events[0].timestamp).getTime() : 0;
        const relativeTime = eventTime - firstEventTime;

        if (relativeTime < filters.timeRange.start || relativeTime > filters.timeRange.end) {
          return false;
        }
      }

      return true;
    });
  }, [events, filters]);

  // Calculate filter counts
  const filterCounts = useMemo(() => {
    const byType: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};

    filteredEvents.forEach((event) => {
      byType[event.event_type] = (byType[event.event_type] || 0) + 1;
      bySeverity[event.severity] = (bySeverity[event.severity] || 0) + 1;
    });

    return {
      total: events.length,
      filtered: filteredEvents.length,
      byType,
      bySeverity,
    };
  }, [events, filteredEvents]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      filters.eventTypes.length > 0 ||
      filters.severities.length > 0 ||
      filters.executorIds.length > 0 ||
      filters.searchQuery !== '' ||
      filters.showErrorsOnly ||
      filters.timeRange !== undefined
    );
  }, [filters]);

  // Filter setters
  const setEventTypes = useCallback((types: string[]) => {
    setFilters((prev) => ({ ...prev, eventTypes: types }));
  }, []);

  const toggleEventType = useCallback((type: string) => {
    setFilters((prev) => ({
      ...prev,
      eventTypes: prev.eventTypes.includes(type)
        ? prev.eventTypes.filter((t) => t !== type)
        : [...prev.eventTypes, type],
    }));
  }, []);

  const setSeverities = useCallback((severities: EventSeverity[]) => {
    setFilters((prev) => ({ ...prev, severities }));
  }, []);

  const toggleSeverity = useCallback((severity: EventSeverity) => {
    setFilters((prev) => ({
      ...prev,
      severities: prev.severities.includes(severity)
        ? prev.severities.filter((s) => s !== severity)
        : [...prev.severities, severity],
    }));
  }, []);

  const setExecutorIds = useCallback((ids: string[]) => {
    setFilters((prev) => ({ ...prev, executorIds: ids }));
  }, []);

  const toggleExecutorId = useCallback((id: string) => {
    setFilters((prev) => ({
      ...prev,
      executorIds: prev.executorIds.includes(id)
        ? prev.executorIds.filter((e) => e !== id)
        : [...prev.executorIds, id],
    }));
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    setFilters((prev) => ({ ...prev, searchQuery: query }));
  }, []);

  const setShowErrorsOnly = useCallback((show: boolean) => {
    setFilters((prev) => ({ ...prev, showErrorsOnly: show }));
  }, []);

  const setTimeRange = useCallback((range: { start: number; end: number } | undefined) => {
    setFilters((prev) => ({ ...prev, timeRange: range }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters(defaultFilterState);
  }, []);

  const clearFilter = useCallback((filterKey: keyof EventFilterState) => {
    setFilters((prev) => ({
      ...prev,
      [filterKey]: defaultFilterState[filterKey],
    }));
  }, []);

  return {
    filters,
    filteredEvents,
    filterCounts,
    filterOptions,
    hasActiveFilters,
    setEventTypes,
    toggleEventType,
    setSeverities,
    toggleSeverity,
    setExecutorIds,
    toggleExecutorId,
    setSearchQuery,
    setShowErrorsOnly,
    setTimeRange,
    clearFilters,
    clearFilter,
  };
}

export default useEventFilter;
