// =============================================================================
// IPA Platform - Create Workflow Page
// =============================================================================
// Sprint 5: Frontend UI - Workflow Management
//
// Multi-step form for creating workflows with visual node configuration.
// Supports start/end nodes, agent nodes, and gateway nodes.
// =============================================================================

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileText,
  GitBranch,
  Settings,
  Eye,
  Plus,
  Trash2,
  Play,
  Square,
  Bot,
  GitMerge,
} from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';

// =============================================================================
// Types
// =============================================================================

interface WorkflowNode {
  id: string;
  type: 'start' | 'end' | 'agent' | 'gateway';
  name: string;
  agent_id: string | null;
  config: Record<string, unknown>;
}

interface WorkflowEdge {
  source: string;
  target: string;
  condition: string;
  label: string;
}

interface WorkflowFormData {
  name: string;
  description: string;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  graph_definition: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    variables: Record<string, unknown>;
  };
}

interface AgentOption {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
}

interface FormErrors {
  name?: string;
  nodes?: string;
  general?: string;
}

// =============================================================================
// Constants
// =============================================================================

const STEPS = [
  { id: 1, title: '基本資訊', icon: FileText },
  { id: 2, title: '節點配置', icon: GitBranch },
  { id: 3, title: '連接設定', icon: GitMerge },
  { id: 4, title: '觸發設定', icon: Settings },
  { id: 5, title: '確認建立', icon: Eye },
];

const TRIGGER_TYPES = [
  { value: 'manual', label: '手動觸發' },
  { value: 'schedule', label: '定時排程' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'event', label: '事件觸發' },
];

const NODE_TYPES = [
  { value: 'agent', label: 'Agent 節點', icon: Bot, description: '執行 AI Agent' },
  { value: 'gateway', label: '閘道節點', icon: GitMerge, description: '條件分支' },
];

const DEFAULT_FORM_DATA: WorkflowFormData = {
  name: '',
  description: '',
  trigger_type: 'manual',
  trigger_config: {},
  graph_definition: {
    nodes: [
      { id: 'start', type: 'start', name: '開始', agent_id: null, config: {} },
      { id: 'end', type: 'end', name: '結束', agent_id: null, config: {} },
    ],
    edges: [],
    variables: {},
  },
};

// =============================================================================
// Component
// =============================================================================

export function CreateWorkflowPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<WorkflowFormData>(DEFAULT_FORM_DATA);
  const [errors, setErrors] = useState<FormErrors>({});
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Fetch available agents
  const { data: agentsResponse } = useQuery({
    queryKey: ['agents-for-workflow'],
    queryFn: () =>
      api.get<{ items: AgentOption[]; total: number }>('/agents/?status=active&page_size=100'),
  });

  const agents = agentsResponse?.items || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: WorkflowFormData) => api.post('/workflows/', data),
    onSuccess: () => {
      navigate('/workflows');
    },
    onError: (error: Error) => {
      setErrors({ general: error.message });
    },
  });

  // =============================================================================
  // Handlers
  // =============================================================================

  const updateFormData = (updates: Partial<WorkflowFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
    setErrors({});
  };

  const addNode = (type: 'agent' | 'gateway') => {
    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type,
      name: type === 'agent' ? '新 Agent 節點' : '新閘道節點',
      agent_id: null,
      config: {},
    };

    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        nodes: [...prev.graph_definition.nodes, newNode],
      },
    }));

    setSelectedNodeId(newNode.id);
  };

  const updateNode = (nodeId: string, updates: Partial<WorkflowNode>) => {
    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        nodes: prev.graph_definition.nodes.map((node) =>
          node.id === nodeId ? { ...node, ...updates } : node
        ),
      },
    }));
  };

  const deleteNode = (nodeId: string) => {
    if (nodeId === 'start' || nodeId === 'end') return;

    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        nodes: prev.graph_definition.nodes.filter((n) => n.id !== nodeId),
        edges: prev.graph_definition.edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId
        ),
      },
    }));

    if (selectedNodeId === nodeId) {
      setSelectedNodeId(null);
    }
  };

  const addEdge = (source: string, target: string) => {
    // Check if edge already exists
    const exists = formData.graph_definition.edges.some(
      (e) => e.source === source && e.target === target
    );
    if (exists) return;

    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        edges: [
          ...prev.graph_definition.edges,
          { source, target, condition: '', label: '' },
        ],
      },
    }));
  };

  const updateEdge = (index: number, updates: Partial<WorkflowEdge>) => {
    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        edges: prev.graph_definition.edges.map((edge, i) =>
          i === index ? { ...edge, ...updates } : edge
        ),
      },
    }));
  };

  const deleteEdge = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        edges: prev.graph_definition.edges.filter((_, i) => i !== index),
      },
    }));
  };

  const validateStep = (step: number): boolean => {
    const newErrors: FormErrors = {};

    if (step === 1) {
      if (!formData.name.trim()) {
        newErrors.name = '工作流名稱為必填';
      }
    }

    if (step === 2) {
      // Check if there are any agent nodes
      const agentNodes = formData.graph_definition.nodes.filter(
        (n) => n.type === 'agent'
      );
      if (agentNodes.length === 0) {
        newErrors.nodes = '請至少添加一個 Agent 節點';
      }

      // Check if agent nodes have assigned agents
      const unassignedAgents = agentNodes.filter((n) => !n.agent_id);
      if (unassignedAgents.length > 0) {
        newErrors.nodes = '請為所有 Agent 節點指定 Agent';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, STEPS.length));
    }
  };

  const prevStep = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmit = () => {
    if (validateStep(currentStep)) {
      createMutation.mutate(formData);
    }
  };

  // Auto-connect nodes helper
  const autoConnectNodes = () => {
    const nodes = formData.graph_definition.nodes;
    const newEdges: WorkflowEdge[] = [];

    // Simple linear connection
    const orderedNodes = [
      nodes.find((n) => n.type === 'start'),
      ...nodes.filter((n) => n.type !== 'start' && n.type !== 'end'),
      nodes.find((n) => n.type === 'end'),
    ].filter(Boolean) as WorkflowNode[];

    for (let i = 0; i < orderedNodes.length - 1; i++) {
      newEdges.push({
        source: orderedNodes[i].id,
        target: orderedNodes[i + 1].id,
        condition: '',
        label: '',
      });
    }

    setFormData((prev) => ({
      ...prev,
      graph_definition: {
        ...prev.graph_definition,
        edges: newEdges,
      },
    }));
  };

  // =============================================================================
  // Step Content Renderers
  // =============================================================================

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name" required>
                工作流名稱
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => updateFormData({ name: e.target.value })}
                placeholder="例如：customer-support-workflow"
                error={!!errors.name}
              />
              {errors.name && (
                <p className="text-sm text-red-500">{errors.name}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => updateFormData({ description: e.target.value })}
                placeholder="描述這個工作流的用途..."
                rows={3}
              />
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            {errors.nodes && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-600">{errors.nodes}</p>
              </div>
            )}

            <div className="flex gap-2 mb-4">
              {NODE_TYPES.map((nodeType) => {
                const Icon = nodeType.icon;
                return (
                  <Button
                    key={nodeType.value}
                    variant="outline"
                    onClick={() => addNode(nodeType.value as 'agent' | 'gateway')}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    添加{nodeType.label}
                  </Button>
                );
              })}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Nodes List */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700 mb-2">節點列表</p>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {formData.graph_definition.nodes.map((node) => {
                    const isSelected = selectedNodeId === node.id;
                    const isFixed = node.type === 'start' || node.type === 'end';

                    return (
                      <div
                        key={node.id}
                        onClick={() => setSelectedNodeId(node.id)}
                        className={`p-3 border rounded-lg cursor-pointer transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {node.type === 'start' && (
                              <Play className="w-4 h-4 text-green-500" />
                            )}
                            {node.type === 'end' && (
                              <Square className="w-4 h-4 text-red-500" />
                            )}
                            {node.type === 'agent' && (
                              <Bot className="w-4 h-4 text-blue-500" />
                            )}
                            {node.type === 'gateway' && (
                              <GitMerge className="w-4 h-4 text-purple-500" />
                            )}
                            <span className="text-sm font-medium">{node.name}</span>
                          </div>
                          {!isFixed && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteNode(node.id);
                              }}
                            >
                              <Trash2 className="w-3 h-3 text-gray-400" />
                            </Button>
                          )}
                        </div>
                        {node.type === 'agent' && node.agent_id && (
                          <p className="text-xs text-gray-500 mt-1 ml-6">
                            Agent: {agents.find((a) => a.id === node.agent_id)?.name}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Node Editor */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">節點設定</p>
                {selectedNodeId ? (
                  <Card>
                    <CardContent className="pt-4 space-y-4">
                      {(() => {
                        const node = formData.graph_definition.nodes.find(
                          (n) => n.id === selectedNodeId
                        );
                        if (!node) return null;

                        const isFixed =
                          node.type === 'start' || node.type === 'end';

                        return (
                          <>
                            <div className="space-y-2">
                              <Label>節點名稱</Label>
                              <Input
                                value={node.name}
                                onChange={(e) =>
                                  updateNode(node.id, { name: e.target.value })
                                }
                                disabled={isFixed}
                              />
                            </div>

                            {node.type === 'agent' && (
                              <div className="space-y-2">
                                <Label required>選擇 Agent</Label>
                                <Select
                                  value={node.agent_id || ''}
                                  onChange={(e) =>
                                    updateNode(node.id, {
                                      agent_id: e.target.value || null,
                                    })
                                  }
                                  options={agents.map((a) => ({
                                    value: a.id,
                                    label: a.name,
                                  }))}
                                  placeholder="選擇要執行的 Agent"
                                />
                                {agents.length === 0 && (
                                  <p className="text-xs text-yellow-600">
                                    沒有可用的 Agent，請先建立 Agent
                                  </p>
                                )}
                              </div>
                            )}

                            <div className="pt-2">
                              <Badge
                                variant={
                                  node.type === 'start'
                                    ? 'success'
                                    : node.type === 'end'
                                    ? 'destructive'
                                    : node.type === 'agent'
                                    ? 'info'
                                    : 'secondary'
                                }
                              >
                                {node.type === 'start' && '開始節點'}
                                {node.type === 'end' && '結束節點'}
                                {node.type === 'agent' && 'Agent 節點'}
                                {node.type === 'gateway' && '閘道節點'}
                              </Badge>
                            </div>
                          </>
                        );
                      })()}
                    </CardContent>
                  </Card>
                ) : (
                  <div className="p-8 text-center text-gray-500 border rounded-lg border-dashed">
                    選擇節點以編輯設定
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm text-gray-500">
                設定節點之間的連接關係
              </p>
              <Button variant="outline" size="sm" onClick={autoConnectNodes}>
                <GitBranch className="w-4 h-4 mr-2" />
                自動連接
              </Button>
            </div>

            {/* Add Edge */}
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">添加連接</CardTitle>
              </CardHeader>
              <CardContent className="pb-3">
                <div className="grid grid-cols-3 gap-2">
                  <Select
                    placeholder="來源節點"
                    options={formData.graph_definition.nodes
                      .filter((n) => n.type !== 'end')
                      .map((n) => ({ value: n.id, label: n.name }))}
                    onChange={(e) => {
                      const target = document.getElementById(
                        'target-select'
                      ) as HTMLSelectElement;
                      if (e.target.value && target?.value) {
                        addEdge(e.target.value, target.value);
                        e.target.value = '';
                        target.value = '';
                      }
                    }}
                  />
                  <div className="flex items-center justify-center text-gray-400">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                  <Select
                    id="target-select"
                    placeholder="目標節點"
                    options={formData.graph_definition.nodes
                      .filter((n) => n.type !== 'start')
                      .map((n) => ({ value: n.id, label: n.name }))}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Edges List */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">已建立的連接</p>
              {formData.graph_definition.edges.length === 0 ? (
                <div className="p-8 text-center text-gray-500 border rounded-lg border-dashed">
                  尚未建立任何連接
                </div>
              ) : (
                <div className="space-y-2">
                  {formData.graph_definition.edges.map((edge, index) => {
                    const sourceNode = formData.graph_definition.nodes.find(
                      (n) => n.id === edge.source
                    );
                    const targetNode = formData.graph_definition.nodes.find(
                      (n) => n.id === edge.target
                    );

                    return (
                      <div
                        key={index}
                        className="flex items-center gap-3 p-3 border rounded-lg"
                      >
                        <div className="flex-1 flex items-center gap-2">
                          <Badge variant="secondary">{sourceNode?.name}</Badge>
                          <ArrowRight className="w-4 h-4 text-gray-400" />
                          <Badge variant="secondary">{targetNode?.name}</Badge>
                        </div>
                        <Input
                          placeholder="條件 (可選)"
                          value={edge.condition}
                          onChange={(e) =>
                            updateEdge(index, { condition: e.target.value })
                          }
                          className="w-40"
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteEdge(index)}
                        >
                          <Trash2 className="w-4 h-4 text-gray-400" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="trigger_type">觸發類型</Label>
              <Select
                id="trigger_type"
                value={formData.trigger_type}
                onChange={(e) => updateFormData({ trigger_type: e.target.value })}
                options={TRIGGER_TYPES}
              />
            </div>

            {formData.trigger_type === 'schedule' && (
              <div className="space-y-2">
                <Label htmlFor="cron">Cron 表達式</Label>
                <Input
                  id="cron"
                  placeholder="0 9 * * *"
                  value={(formData.trigger_config.cron as string) || ''}
                  onChange={(e) =>
                    updateFormData({
                      trigger_config: {
                        ...formData.trigger_config,
                        cron: e.target.value,
                      },
                    })
                  }
                />
                <p className="text-xs text-gray-500">
                  例如：0 9 * * * 表示每天早上 9 點執行
                </p>
              </div>
            )}

            {formData.trigger_type === 'webhook' && (
              <div className="space-y-2">
                <Label htmlFor="endpoint">Webhook 端點</Label>
                <Input
                  id="endpoint"
                  placeholder="/webhooks/my-workflow"
                  value={(formData.trigger_config.endpoint as string) || ''}
                  onChange={(e) =>
                    updateFormData({
                      trigger_config: {
                        ...formData.trigger_config,
                        endpoint: e.target.value,
                      },
                    })
                  }
                />
              </div>
            )}

            {formData.trigger_type === 'event' && (
              <div className="space-y-2">
                <Label htmlFor="event_type">事件類型</Label>
                <Input
                  id="event_type"
                  placeholder="ticket.created"
                  value={(formData.trigger_config.event_type as string) || ''}
                  onChange={(e) =>
                    updateFormData({
                      trigger_config: {
                        ...formData.trigger_config,
                        event_type: e.target.value,
                      },
                    })
                  }
                />
              </div>
            )}

            {formData.trigger_type === 'manual' && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  手動觸發的工作流需要透過 API 或 UI 手動啟動執行。
                </p>
              </div>
            )}
          </div>
        );

      case 5:
        return (
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <div>
                <p className="text-sm font-medium text-gray-700">工作流名稱</p>
                <p className="text-sm">{formData.name || '(未設定)'}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">描述</p>
                <p className="text-sm">{formData.description || '(無描述)'}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">觸發類型</p>
                <Badge variant="secondary">
                  {TRIGGER_TYPES.find((t) => t.value === formData.trigger_type)?.label}
                </Badge>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">工作流程</p>
                <div className="flex flex-wrap items-center gap-2">
                  {formData.graph_definition.edges.length > 0 ? (
                    formData.graph_definition.edges.map((edge, i) => {
                      const source = formData.graph_definition.nodes.find(
                        (n) => n.id === edge.source
                      );
                      const target = formData.graph_definition.nodes.find(
                        (n) => n.id === edge.target
                      );
                      return (
                        <div key={i} className="flex items-center gap-1">
                          <Badge variant="outline">{source?.name}</Badge>
                          <ArrowRight className="w-3 h-3 text-gray-400" />
                          <Badge variant="outline">{target?.name}</Badge>
                          {i < formData.graph_definition.edges.length - 1 && (
                            <span className="mx-2 text-gray-300">|</span>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <span className="text-sm text-gray-500">(未建立連接)</span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">節點數量</p>
                <p className="text-sm">
                  {formData.graph_definition.nodes.length} 個節點，
                  {formData.graph_definition.edges.length} 個連接
                </p>
              </div>
            </div>

            {errors.general && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-600">{errors.general}</p>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/workflows')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">建立工作流</h1>
          <p className="text-gray-500">設計您的自動化工作流程</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const isCompleted = currentStep > step.id;
          const isCurrent = currentStep === step.id;

          return (
            <div key={step.id} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                  isCompleted
                    ? 'bg-primary border-primary'
                    : isCurrent
                    ? 'border-primary text-primary'
                    : 'border-gray-300 text-gray-400'
                }`}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span
                className={`ml-2 text-sm font-medium hidden md:inline ${
                  isCurrent ? 'text-primary' : 'text-gray-500'
                }`}
              >
                {step.title}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={`w-8 md:w-12 h-0.5 mx-2 ${
                    isCompleted ? 'bg-primary' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {STEPS[currentStep - 1].title}
          </CardTitle>
        </CardHeader>
        <CardContent>{renderStepContent()}</CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={prevStep}
          disabled={currentStep === 1}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          上一步
        </Button>

        {currentStep < STEPS.length ? (
          <Button onClick={nextStep}>
            下一步
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? '建立中...' : '建立工作流'}
            <Check className="w-4 h-4 ml-2" />
          </Button>
        )}
      </div>
    </div>
  );
}
