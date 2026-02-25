// =============================================================================
// IPA Platform - DAG Layout Engine
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Auto-layout engine using dagre algorithm for DAG positioning.
// Supports horizontal (LR) and vertical (TB) layout directions.
// =============================================================================

import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';

export type LayoutDirection = 'TB' | 'LR';

interface LayoutOptions {
  direction?: LayoutDirection;
  nodeWidth?: number;
  nodeHeight?: number;
  rankSep?: number;
  nodeSep?: number;
  edgeSep?: number;
}

const DEFAULT_OPTIONS: Required<LayoutOptions> = {
  direction: 'TB',
  nodeWidth: 180,
  nodeHeight: 80,
  rankSep: 80,
  nodeSep: 40,
  edgeSep: 20,
};

// Node type-specific sizing
const NODE_SIZES: Record<string, { width: number; height: number }> = {
  startEnd: { width: 80, height: 80 },
  condition: { width: 120, height: 120 },
  agent: { width: 180, height: 70 },
  action: { width: 170, height: 65 },
};

/**
 * Apply dagre auto-layout to nodes and edges.
 *
 * @param nodes - ReactFlow nodes array
 * @param edges - ReactFlow edges array
 * @param options - Layout configuration
 * @returns New arrays with updated positions (immutable)
 */
export function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: opts.direction,
    ranksep: opts.rankSep,
    nodesep: opts.nodeSep,
    edgesep: opts.edgeSep,
  });

  // Add nodes with type-specific dimensions
  for (const node of nodes) {
    const size = NODE_SIZES[node.type || 'agent'] || {
      width: opts.nodeWidth,
      height: opts.nodeHeight,
    };
    dagreGraph.setNode(node.id, { width: size.width, height: size.height });
  }

  // Add edges
  for (const edge of edges) {
    dagreGraph.setEdge(edge.source, edge.target);
  }

  // Run dagre layout
  dagre.layout(dagreGraph);

  // Map back to ReactFlow nodes (immutable — create new objects)
  const layoutedNodes = nodes.map((node) => {
    const dagreNode = dagreGraph.node(node.id);
    const size = NODE_SIZES[node.type || 'agent'] || {
      width: opts.nodeWidth,
      height: opts.nodeHeight,
    };

    return {
      ...node,
      position: {
        x: dagreNode.x - size.width / 2,
        y: dagreNode.y - size.height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

/**
 * Calculate the bounding box of all nodes.
 */
export function getNodesBounds(nodes: Node[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
} {
  if (nodes.length === 0) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const node of nodes) {
    const x = node.position?.x ?? 0;
    const y = node.position?.y ?? 0;
    const size = NODE_SIZES[node.type || 'agent'] || {
      width: DEFAULT_OPTIONS.nodeWidth,
      height: DEFAULT_OPTIONS.nodeHeight,
    };

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + size.width);
    maxY = Math.max(maxY, y + size.height);
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}
