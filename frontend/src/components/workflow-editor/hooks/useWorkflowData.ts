// =============================================================================
// IPA Platform - Workflow Data Hook
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Transforms backend Workflow data into ReactFlow node/edge format.
// Handles both graph_definition and legacy definition formats.
// =============================================================================

import { useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Node, Edge } from '@xyflow/react';
import { api } from '@/api/client';
import type {
  Workflow,
  WorkflowGraphNode,
  WorkflowGraphEdge,
  WorkflowNode as LegacyWorkflowNode,
  WorkflowEdge as LegacyWorkflowEdge,
} from '@/types';
import { applyDagreLayout, type LayoutDirection } from '../utils/layoutEngine';

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

interface WorkflowGraphResponse {
  workflow_id: string;
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
  layout_metadata?: Record<string, unknown>;
}

interface GraphLayoutRequest {
  direction: LayoutDirection;
}

interface UseWorkflowDataResult {
  nodes: Node[];
  edges: Edge[];
  isLoading: boolean;
  error: Error | null;
  workflow: Workflow | undefined;
  saveLayout: (nodes: Node[], edges: Edge[]) => void;
  isSaving: boolean;
  autoLayout: (direction: LayoutDirection) => void;
  isLayouting: boolean;
  exportToJson: () => string;
}

// -------------------------------------------------------------------------
// Node type mapping
// -------------------------------------------------------------------------

function mapNodeType(
  type: string
): 'startEnd' | 'agent' | 'condition' | 'action' {
  switch (type) {
    case 'start':
    case 'end':
      return 'startEnd';
    case 'agent':
      return 'agent';
    case 'gateway':
    case 'decision':
      return 'condition';
    case 'approval':
    case 'task':
    default:
      return 'action';
  }
}

function buildNodeData(
  type: string,
  name: string | null,
  agentId: string | null,
  config: Record<string, unknown>
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    label: name || type,
  };

  switch (type) {
    case 'start':
      return { ...base, nodeRole: 'start' };
    case 'end':
      return { ...base, nodeRole: 'end' };
    case 'agent':
      return { ...base, agentId, agentType: config.agent_type || 'chat' };
    case 'gateway':
    case 'decision':
      return {
        ...base,
        gatewayType: config.gateway_type || 'exclusive',
        condition: config.condition,
      };
    default:
      return {
        ...base,
        actionType: config.action_type || 'generic',
        config,
      };
  }
}

// -------------------------------------------------------------------------
// Transform functions
// -------------------------------------------------------------------------

function graphNodesToReactFlow(
  graphNodes: WorkflowGraphNode[]
): Node[] {
  return graphNodes.map((gn) => ({
    id: gn.id,
    type: mapNodeType(gn.type),
    position: gn.position || { x: 0, y: 0 },
    data: buildNodeData(gn.type, gn.name, gn.agent_id, gn.config),
  }));
}

function graphEdgesToReactFlow(
  graphEdges: WorkflowGraphEdge[]
): Edge[] {
  return graphEdges.map((ge, idx) => ({
    id: `e-${ge.source}-${ge.target}-${idx}`,
    source: ge.source,
    target: ge.target,
    type: ge.condition ? 'conditional' : 'default',
    label: ge.label || ge.condition || undefined,
    data: ge.condition ? { condition: ge.condition } : undefined,
  }));
}

function legacyNodesToReactFlow(nodes: LegacyWorkflowNode[]): Node[] {
  return nodes.map((n) => ({
    id: n.id,
    type: mapNodeType(n.type),
    position: { x: 0, y: 0 },
    data: buildNodeData(n.type, n.name, null, n.config),
  }));
}

function legacyEdgesToReactFlow(edges: LegacyWorkflowEdge[]): Edge[] {
  return edges.map((e, idx) => ({
    id: e.id || `e-${e.source}-${e.target}-${idx}`,
    source: e.source,
    target: e.target,
    type: e.condition ? 'conditional' : 'default',
    label: e.condition || undefined,
    data: e.condition ? { condition: e.condition } : undefined,
  }));
}

// -------------------------------------------------------------------------
// Hook
// -------------------------------------------------------------------------

export function useWorkflowData(workflowId: string): UseWorkflowDataResult {
  const queryClient = useQueryClient();

  // Fetch workflow base data
  const {
    data: workflow,
    isLoading: isLoadingWorkflow,
    error: workflowError,
  } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => api.get<Workflow>(`/workflows/${workflowId}`),
    enabled: !!workflowId,
  });

  // Fetch graph data (may have layout positions saved)
  const {
    data: graphData,
    isLoading: isLoadingGraph,
    error: graphError,
  } = useQuery({
    queryKey: ['workflow-graph', workflowId],
    queryFn: () =>
      api.get<WorkflowGraphResponse>(`/workflows/${workflowId}/graph`),
    enabled: !!workflowId,
    retry: false, // Fall back to workflow definition if graph endpoint not available
  });

  // Transform to ReactFlow format
  const { nodes, edges } = useMemo(() => {
    // Priority 1: Dedicated graph endpoint data
    if (graphData?.nodes?.length) {
      const rfNodes = graphNodesToReactFlow(graphData.nodes);
      const rfEdges = graphEdgesToReactFlow(graphData.edges);

      // If no positions, apply auto-layout
      const hasPositions = rfNodes.some(
        (n) => n.position.x !== 0 || n.position.y !== 0
      );
      if (!hasPositions) {
        return applyDagreLayout(rfNodes, rfEdges);
      }
      return { nodes: rfNodes, edges: rfEdges };
    }

    // Priority 2: Workflow graph_definition
    if (workflow?.graph_definition?.nodes?.length) {
      const rfNodes = graphNodesToReactFlow(workflow.graph_definition.nodes);
      const rfEdges = graphEdgesToReactFlow(workflow.graph_definition.edges);
      const hasPositions = rfNodes.some(
        (n) => n.position.x !== 0 || n.position.y !== 0
      );
      if (!hasPositions) {
        return applyDagreLayout(rfNodes, rfEdges);
      }
      return { nodes: rfNodes, edges: rfEdges };
    }

    // Priority 3: Legacy definition format
    if (workflow?.definition?.nodes?.length) {
      const rfNodes = legacyNodesToReactFlow(workflow.definition.nodes);
      const rfEdges = legacyEdgesToReactFlow(workflow.definition.edges);
      return applyDagreLayout(rfNodes, rfEdges);
    }

    // Empty
    return { nodes: [], edges: [] };
  }, [graphData, workflow]);

  // Save layout mutation
  const saveLayoutMutation = useMutation({
    mutationFn: (payload: { nodes: Node[]; edges: Edge[] }) =>
      api.put<WorkflowGraphResponse>(`/workflows/${workflowId}/graph`, {
        nodes: payload.nodes.map((n) => ({
          id: n.id,
          type: n.data?.nodeRole === 'start' || n.data?.nodeRole === 'end'
            ? n.data.nodeRole
            : n.type === 'condition'
              ? 'gateway'
              : n.type === 'action'
                ? 'task'
                : n.type || 'agent',
          name: (n.data as Record<string, unknown>)?.label as string || null,
          agent_id: (n.data as Record<string, unknown>)?.agentId as string || null,
          config: (n.data as Record<string, unknown>)?.config as Record<string, unknown> || {},
          position: n.position,
        })),
        edges: payload.edges.map((e) => ({
          source: e.source,
          target: e.target,
          condition: (e.data as Record<string, unknown>)?.condition as string || e.label || null,
          label: e.label || null,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['workflow-graph', workflowId],
      });
    },
  });

  // Auto-layout mutation
  const autoLayoutMutation = useMutation({
    mutationFn: (payload: GraphLayoutRequest) =>
      api.post<WorkflowGraphResponse>(
        `/workflows/${workflowId}/graph/layout`,
        payload
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['workflow-graph', workflowId],
      });
    },
  });

  const saveLayout = useCallback(
    (updatedNodes: Node[], updatedEdges: Edge[]) => {
      saveLayoutMutation.mutate({ nodes: updatedNodes, edges: updatedEdges });
    },
    [saveLayoutMutation]
  );

  const autoLayout = useCallback(
    (direction: LayoutDirection) => {
      autoLayoutMutation.mutate({ direction });
    },
    [autoLayoutMutation]
  );

  const exportToJson = useCallback(() => {
    return JSON.stringify(
      {
        workflow_id: workflowId,
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.label,
          data: e.data,
        })),
      },
      null,
      2
    );
  }, [workflowId, nodes, edges]);

  return {
    nodes,
    edges,
    isLoading: isLoadingWorkflow || isLoadingGraph,
    error: (workflowError || graphError) as Error | null,
    workflow,
    saveLayout,
    isSaving: saveLayoutMutation.isPending,
    autoLayout,
    isLayouting: autoLayoutMutation.isPending,
    exportToJson,
  };
}
