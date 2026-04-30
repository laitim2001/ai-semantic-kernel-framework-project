// =============================================================================
// IPA Platform - DevUI Event Tree Component
// =============================================================================
// Sprint 88: S88-2 - Event Tree Structure
//
// Tree view of execution events showing parent-child relationships.
//
// Dependencies:
//   - React
//   - TreeNode component
// =============================================================================

import { FC, useMemo, useState } from 'react';
import {
  ChevronRight,
  Expand,
  Shrink,
  Search,
  Clock,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { TreeNode, EventTreeNode } from './TreeNode';

interface EventTreeProps {
  /** List of events to display */
  events: TraceEvent[];
  /** Selected event ID */
  selectedEventId?: string;
  /** Event selection handler */
  onEventSelect?: (event: TraceEvent) => void;
  /** Maximum height */
  maxHeight?: string;
  /** Show search */
  showSearch?: boolean;
}

/**
 * Build tree structure from flat event list
 */
function buildEventTree(events: TraceEvent[]): EventTreeNode[] {
  // Sort events by timestamp
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Create node map
  const nodeMap = new Map<string, EventTreeNode>();
  sorted.forEach(event => {
    nodeMap.set(event.id, {
      event,
      children: [],
      depth: 0,
    });
  });

  // Build tree structure
  const roots: EventTreeNode[] = [];

  sorted.forEach(event => {
    const node = nodeMap.get(event.id)!;

    if (event.parent_event_id && nodeMap.has(event.parent_event_id)) {
      // Add as child of parent
      const parent = nodeMap.get(event.parent_event_id)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      // Root level event
      roots.push(node);
    }
  });

  return roots;
}

/**
 * Calculate tree statistics
 */
function getTreeStats(roots: EventTreeNode[]): {
  totalNodes: number;
  maxDepth: number;
  leafCount: number;
} {
  let totalNodes = 0;
  let maxDepth = 0;
  let leafCount = 0;

  function traverse(nodes: EventTreeNode[], depth: number) {
    nodes.forEach(node => {
      totalNodes++;
      maxDepth = Math.max(maxDepth, depth);
      if (node.children.length === 0) {
        leafCount++;
      } else {
        traverse(node.children, depth + 1);
      }
    });
  }

  traverse(roots, 0);

  return { totalNodes, maxDepth, leafCount };
}

/**
 * Filter tree nodes by search query
 */
function filterTree(
  nodes: EventTreeNode[],
  query: string
): EventTreeNode[] {
  if (!query) return nodes;

  const lowerQuery = query.toLowerCase();

  function matches(node: EventTreeNode): boolean {
    return node.event.event_type.toLowerCase().includes(lowerQuery) ||
           node.event.tags.some(t => t.toLowerCase().includes(lowerQuery));
  }

  function filterNode(node: EventTreeNode): EventTreeNode | null {
    const filteredChildren = node.children
      .map(filterNode)
      .filter((n): n is EventTreeNode => n !== null);

    if (matches(node) || filteredChildren.length > 0) {
      return {
        ...node,
        children: filteredChildren,
      };
    }

    return null;
  }

  return nodes
    .map(filterNode)
    .filter((n): n is EventTreeNode => n !== null);
}

/**
 * Event Tree Component
 * Displays events in a hierarchical tree structure
 */
export const EventTree: FC<EventTreeProps> = ({
  events,
  selectedEventId,
  onEventSelect,
  maxHeight = '500px',
  showSearch = true,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandAll, setExpandAll] = useState(false);

  // Build tree structure
  const tree = useMemo(() => buildEventTree(events), [events]);
  const stats = useMemo(() => getTreeStats(tree), [tree]);

  // Filter tree
  const filteredTree = useMemo(
    () => filterTree(tree, searchQuery),
    [tree, searchQuery]
  );

  // Force re-render for expand/collapse all
  const [expandKey, setExpandKey] = useState(0);

  const handleExpandAll = () => {
    setExpandAll(true);
    setExpandKey(prev => prev + 1);
  };

  const handleCollapseAll = () => {
    setExpandAll(false);
    setExpandKey(prev => prev + 1);
  };

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <Clock className="w-12 h-12 mb-2 text-gray-300" />
        <p>No events to display</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{stats.totalNodes} events</span>
          <span className="text-gray-300">|</span>
          <span>{stats.maxDepth + 1} levels</span>
          <span className="text-gray-300">|</span>
          <span>{tree.length} root events</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Search input */}
          {showSearch && (
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search events..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 w-40"
              />
            </div>
          )}

          {/* Expand/Collapse all buttons */}
          <button
            onClick={handleExpandAll}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-200 rounded"
            title="Expand all"
          >
            <Expand className="w-3.5 h-3.5" />
            <span>Expand</span>
          </button>
          <button
            onClick={handleCollapseAll}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-200 rounded"
            title="Collapse all"
          >
            <Shrink className="w-3.5 h-3.5" />
            <span>Collapse</span>
          </button>
        </div>
      </div>

      {/* Tree content */}
      <div
        className="overflow-auto p-2"
        style={{ maxHeight }}
      >
        {filteredTree.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No events match "{searchQuery}"
          </div>
        ) : (
          <div key={expandKey}>
            {filteredTree.map(node => (
              <TreeNode
                key={node.event.id}
                node={node}
                onClick={onEventSelect}
                selectedEventId={selectedEventId}
                defaultExpanded={expandAll || node.depth < 2}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <ChevronRight className="w-3 h-3" />
            Click to expand
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            Selected
          </span>
        </div>
      </div>
    </div>
  );
};

export default EventTree;
