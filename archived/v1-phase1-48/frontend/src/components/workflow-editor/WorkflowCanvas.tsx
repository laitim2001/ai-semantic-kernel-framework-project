// =============================================================================
// IPA Platform - Workflow Canvas Component
// =============================================================================
// Sprint 133: ReactFlow Workflow DAG Visualization (Phase 34)
//
// Main canvas component for workflow DAG visualization.
// Features:
//   - ReactFlow with custom nodes and edges
//   - Auto-layout (dagre) with direction toggle
//   - Node detail panel on click
//   - Edge condition display on click
//   - Minimap, controls, background
//   - Export to JSON
//   - Save/load layout persistence
// =============================================================================

import { useCallback, useState, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Panel,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type OnSelectionChangeParams,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  ArrowLeft,
  LayoutGrid,
  ArrowRightLeft,
  ArrowDownUp,
  Save,
  Download,
  Loader2,
  X,
  Info,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

import { AgentNode } from './nodes/AgentNode';
import { ConditionNode } from './nodes/ConditionNode';
import { ActionNode } from './nodes/ActionNode';
import { StartEndNode } from './nodes/StartEndNode';
import { DefaultEdge } from './edges/DefaultEdge';
import { ConditionalEdge } from './edges/ConditionalEdge';
import { useWorkflowData } from './hooks/useWorkflowData';
import { useNodeDrag } from './hooks/useNodeDrag';
import { applyDagreLayout, type LayoutDirection } from './utils/layoutEngine';

// -------------------------------------------------------------------------
// Node and edge type registrations
// -------------------------------------------------------------------------

const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
  action: ActionNode,
  startEnd: StartEndNode,
};

const edgeTypes = {
  default: DefaultEdge,
  conditional: ConditionalEdge,
};

// -------------------------------------------------------------------------
// Props
// -------------------------------------------------------------------------

interface WorkflowCanvasProps {
  workflowId: string;
}

// -------------------------------------------------------------------------
// Detail Panel for selected node/edge
// -------------------------------------------------------------------------

interface DetailPanelProps {
  selectedNode: Node | null;
  selectedEdge: Edge | null;
  onClose: () => void;
}

function DetailPanel({ selectedNode, selectedEdge, onClose }: DetailPanelProps) {
  if (!selectedNode && !selectedEdge) return null;

  return (
    <Card className="w-72 shadow-lg">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-1">
            <Info className="w-4 h-4" />
            {selectedNode ? 'Node Details' : 'Edge Details'}
          </CardTitle>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
            <X className="w-3 h-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="text-xs space-y-2">
        {selectedNode && (
          <>
            <div>
              <span className="text-gray-500">ID:</span>{' '}
              <span className="font-mono">{selectedNode.id}</span>
            </div>
            <div>
              <span className="text-gray-500">Type:</span>{' '}
              <Badge variant="outline" className="text-xs">{selectedNode.type}</Badge>
            </div>
            <div>
              <span className="text-gray-500">Label:</span>{' '}
              {(selectedNode.data as Record<string, unknown>)?.label as string || '-'}
            </div>
            <div>
              <span className="text-gray-500">Position:</span>{' '}
              <span className="font-mono">
                ({Math.round(selectedNode.position.x)}, {Math.round(selectedNode.position.y)})
              </span>
            </div>
            {(selectedNode.data as Record<string, unknown>)?.agentId && (
              <div>
                <span className="text-gray-500">Agent ID:</span>{' '}
                <span className="font-mono text-[10px]">
                  {(selectedNode.data as Record<string, unknown>).agentId as string}
                </span>
              </div>
            )}
            {(selectedNode.data as Record<string, unknown>)?.condition && (
              <div>
                <span className="text-gray-500">Condition:</span>{' '}
                <code className="text-[10px] bg-gray-100 px-1 rounded">
                  {(selectedNode.data as Record<string, unknown>).condition as string}
                </code>
              </div>
            )}
          </>
        )}
        {selectedEdge && (
          <>
            <div>
              <span className="text-gray-500">ID:</span>{' '}
              <span className="font-mono">{selectedEdge.id}</span>
            </div>
            <div>
              <span className="text-gray-500">Source:</span>{' '}
              <span className="font-mono">{selectedEdge.source}</span>
            </div>
            <div>
              <span className="text-gray-500">Target:</span>{' '}
              <span className="font-mono">{selectedEdge.target}</span>
            </div>
            <div>
              <span className="text-gray-500">Type:</span>{' '}
              <Badge variant="outline" className="text-xs">{selectedEdge.type}</Badge>
            </div>
            {selectedEdge.label && (
              <div>
                <span className="text-gray-500">Label:</span>{' '}
                {selectedEdge.label as string}
              </div>
            )}
            {(selectedEdge.data as Record<string, unknown>)?.condition && (
              <div>
                <span className="text-gray-500">Condition:</span>{' '}
                <code className="text-[10px] bg-gray-100 px-1 rounded">
                  {(selectedEdge.data as Record<string, unknown>).condition as string}
                </code>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// -------------------------------------------------------------------------
// Main Component
// -------------------------------------------------------------------------

export function WorkflowCanvas({ workflowId }: WorkflowCanvasProps) {
  const {
    nodes: initialNodes,
    edges: initialEdges,
    isLoading,
    workflow,
    saveLayout,
    isSaving,
    exportToJson,
  } = useWorkflowData(workflowId);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [layoutDirection, setLayoutDirection] = useState<LayoutDirection>('TB');

  // Sync when initial data changes
  useMemo(() => {
    if (initialNodes.length > 0) {
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Node drag with auto-save
  const { isDragging, hasUnsavedChanges, onNodeDragStart, onNodeDragStop, markSaved } =
    useNodeDrag({
      onSave: (updatedNodes) => {
        saveLayout(updatedNodes, edges);
        markSaved();
      },
      debounceMs: 2000,
    });

  // Selection handler
  const onSelectionChange = useCallback(
    ({ nodes: selNodes, edges: selEdges }: OnSelectionChangeParams) => {
      if (selNodes.length > 0) {
        setSelectedNode(selNodes[0]);
        setSelectedEdge(null);
      } else if (selEdges.length > 0) {
        setSelectedEdge(selEdges[0]);
        setSelectedNode(null);
      } else {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    },
    []
  );

  // Auto-layout (client-side)
  const handleAutoLayout = useCallback(
    (direction: LayoutDirection) => {
      setLayoutDirection(direction);
      const result = applyDagreLayout(nodes, edges, { direction });
      setNodes(result.nodes);
    },
    [nodes, edges, setNodes]
  );

  // Manual save
  const handleSave = useCallback(() => {
    saveLayout(nodes, edges);
    markSaved();
  }, [nodes, edges, saveLayout, markSaved]);

  // Export
  const handleExport = useCallback(() => {
    const json = exportToJson();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-${workflowId}-graph.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportToJson, workflowId]);

  // Close detail panel
  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-3 text-gray-500">Loading workflow...</span>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-white">
        <div className="flex items-center gap-3">
          <Link to={`/workflows/${workflowId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              {workflow?.name || 'Workflow Editor'}
            </h1>
            <p className="text-xs text-gray-500">
              {nodes.length} nodes, {edges.length} edges
              {hasUnsavedChanges && (
                <span className="ml-2 text-amber-600">Unsaved changes</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Layout controls */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAutoLayout('TB')}
            className={layoutDirection === 'TB' ? 'bg-gray-100' : ''}
          >
            <ArrowDownUp className="w-3.5 h-3.5 mr-1" />
            Vertical
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAutoLayout('LR')}
            className={layoutDirection === 'LR' ? 'bg-gray-100' : ''}
          >
            <ArrowRightLeft className="w-3.5 h-3.5 mr-1" />
            Horizontal
          </Button>

          <div className="w-px h-6 bg-gray-200" />

          {/* Save */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            disabled={isSaving || !hasUnsavedChanges}
          >
            {isSaving ? (
              <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5 mr-1" />
            )}
            Save
          </Button>

          {/* Export */}
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="w-3.5 h-3.5 mr-1" />
            Export
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStart={onNodeDragStart}
          onNodeDragStop={onNodeDragStop}
          onSelectionChange={onSelectionChange}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.1}
          maxZoom={2}
          defaultEdgeOptions={{
            type: 'default',
            animated: false,
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Controls
            position="bottom-left"
            className="!bg-white !border !border-gray-200 !shadow-sm !rounded-lg"
          />
          <MiniMap
            position="bottom-right"
            nodeColor={(node) => {
              switch (node.type) {
                case 'agent':
                  return '#3b82f6';
                case 'condition':
                  return '#f59e0b';
                case 'action':
                  return '#10b981';
                case 'startEnd':
                  return '#6366f1';
                default:
                  return '#94a3b8';
              }
            }}
            className="!bg-white !border !border-gray-200 !shadow-sm !rounded-lg"
            maskColor="rgba(0, 0, 0, 0.05)"
          />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />

          {/* Legend Panel */}
          <Panel position="top-left" className="!m-2">
            <div className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-3 py-2 text-xs space-y-1">
              <div className="font-medium text-gray-700 flex items-center gap-1">
                <LayoutGrid className="w-3 h-3" /> Node Types
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-indigo-400" />
                <span>Start / End</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-blue-400" />
                <span>Agent</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rotate-45 rounded-sm bg-amber-400" />
                <span>Condition</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-emerald-400" />
                <span>Action</span>
              </div>
            </div>
          </Panel>

          {/* Detail Panel */}
          <Panel position="top-right" className="!m-2">
            <DetailPanel
              selectedNode={selectedNode}
              selectedEdge={selectedEdge}
              onClose={handleCloseDetail}
            />
          </Panel>

          {/* Drag indicator */}
          {isDragging && (
            <Panel position="bottom-center" className="!m-2">
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-1 text-xs text-blue-700">
                Dragging... Release to update position
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>
    </div>
  );
}
