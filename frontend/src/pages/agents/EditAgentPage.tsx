// =============================================================================
// IPA Platform - Edit Agent Page
// =============================================================================
// Sprint 5: Frontend UI - Agent Management
//
// Form for editing existing AI agents. Loads agent data and allows updating
// all configuration fields.
// =============================================================================

import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Check, Trash2 } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { PageLoading } from '@/components/shared/LoadingSpinner';

// =============================================================================
// Types
// =============================================================================

interface AgentResponse {
  id: string;
  name: string;
  description: string | null;
  instructions: string;
  category: string | null;
  tools: string[];
  model_config_data: Record<string, unknown>;
  max_iterations: number;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

interface AgentFormData {
  name: string;
  description: string;
  category: string;
  instructions: string;
  tools: string[];
  model_config_data: {
    provider: string;
    model: string;
    temperature: number;
    max_tokens: number;
    // Azure OpenAI specific
    azure_endpoint?: string;
    azure_deployment_name?: string;
    azure_api_version?: string;
    // OpenAI specific
    openai_org_id?: string;
    // Common
    api_key?: string;
    base_url?: string;
    // Google AI specific
    google_project_id?: string;
  };
  max_iterations: number;
  status: string;
}

interface FormErrors {
  name?: string;
  instructions?: string;
  general?: string;
}

// =============================================================================
// Constants
// =============================================================================

const CATEGORIES = [
  { value: 'support', label: '客服支援' },
  { value: 'sales', label: '銷售助理' },
  { value: 'it', label: 'IT 支援' },
  { value: 'hr', label: '人力資源' },
  { value: 'finance', label: '財務處理' },
  { value: 'general', label: '通用助理' },
];

const MODEL_PROVIDERS = [
  { value: 'azure_openai', label: 'Azure OpenAI', description: '透過 Azure AI Foundry 部署的 OpenAI 模型' },
  { value: 'openai', label: 'OpenAI', description: '直接使用 OpenAI API' },
  { value: 'anthropic', label: 'Anthropic', description: 'Claude 系列模型' },
  { value: 'google', label: 'Google AI', description: 'Gemini 系列模型' },
  { value: 'local', label: '本地模型', description: 'Ollama、vLLM 等本地部署的模型' },
];

const AZURE_API_VERSIONS = [
  { value: '2024-10-21', label: '2024-10-21 (最新穩定版)' },
  { value: '2024-08-01-preview', label: '2024-08-01-preview' },
  { value: '2024-06-01', label: '2024-06-01' },
  { value: '2024-02-15-preview', label: '2024-02-15-preview' },
  { value: '2023-12-01-preview', label: '2023-12-01-preview' },
];

const MODELS_BY_PROVIDER: Record<string, { value: string; label: string; description: string }[]> = {
  azure_openai: [
    { value: 'gpt-4o', label: 'GPT-4o', description: '最新多模態模型，速度快' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini', description: '輕量級多模態模型' },
    { value: 'gpt-4', label: 'GPT-4', description: '高性能推理模型' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo', description: '快速版 GPT-4' },
    { value: 'gpt-35-turbo', label: 'GPT-3.5 Turbo', description: '經濟實惠的選擇' },
  ],
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o', description: '最新多模態模型' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini', description: '輕量級多模態模型' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo', description: '快速版 GPT-4' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', description: '經濟實惠的選擇' },
    { value: 'o1-preview', label: 'O1 Preview', description: '推理模型（預覽）' },
    { value: 'o1-mini', label: 'O1 Mini', description: '輕量推理模型' },
  ],
  anthropic: [
    { value: 'claude-3-5-sonnet-latest', label: 'Claude 3.5 Sonnet', description: '最佳性價比' },
    { value: 'claude-3-5-haiku-latest', label: 'Claude 3.5 Haiku', description: '快速輕量' },
    { value: 'claude-3-opus-latest', label: 'Claude 3 Opus', description: '最強性能' },
  ],
  google: [
    { value: 'gemini-2.0-flash-exp', label: 'Gemini 2.0 Flash', description: '最新實驗版' },
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro', description: '高性能模型' },
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', description: '快速模型' },
  ],
  local: [
    { value: 'llama-3.1-70b', label: 'Llama 3.1 70B', description: 'Meta 開源大模型' },
    { value: 'llama-3.1-8b', label: 'Llama 3.1 8B', description: 'Meta 開源小模型' },
    { value: 'mistral-large', label: 'Mistral Large', description: 'Mistral AI 大模型' },
    { value: 'qwen-2.5-72b', label: 'Qwen 2.5 72B', description: '阿里通義千問' },
    { value: 'custom', label: '自訂模型', description: '手動輸入模型名稱' },
  ],
};

const STATUS_OPTIONS = [
  { value: 'active', label: '啟用中' },
  { value: 'inactive', label: '停用' },
  { value: 'deprecated', label: '已棄用' },
];

const AVAILABLE_TOOLS = [
  { id: 'search_knowledge_base', name: '知識庫搜索', description: '搜索內部知識庫' },
  { id: 'get_customer_info', name: '客戶資訊查詢', description: '獲取客戶資料' },
  { id: 'create_ticket', name: '建立工單', description: '建立支援工單' },
  { id: 'send_email', name: '發送郵件', description: '發送電子郵件通知' },
  { id: 'query_database', name: '資料庫查詢', description: '查詢業務資料庫' },
  { id: 'web_search', name: '網路搜索', description: '搜索網路資訊' },
];

// =============================================================================
// Component
// =============================================================================

export function EditAgentPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<AgentFormData | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch agent data
  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.get<AgentResponse>(`/agents/${id}`),
    enabled: !!id,
  });

  // Initialize form data when agent loads
  useEffect(() => {
    if (agent) {
      const config = agent.model_config_data || {};
      setFormData({
        name: agent.name,
        description: agent.description || '',
        category: agent.category || 'general',
        instructions: agent.instructions,
        tools: agent.tools || [],
        model_config_data: {
          provider: (config.provider as string) || 'azure_openai',
          model: (config.model as string) || 'gpt-4o',
          temperature: (config.temperature as number) || 0.7,
          max_tokens: (config.max_tokens as number) || 2000,
          // Azure OpenAI 特定欄位
          azure_endpoint: (config.azure_endpoint as string) || '',
          azure_deployment_name: (config.azure_deployment_name as string) || '',
          azure_api_version: (config.azure_api_version as string) || '',
          api_key: (config.api_key as string) || '',
          // OpenAI 特定欄位
          openai_org_id: (config.openai_org_id as string) || '',
          base_url: (config.base_url as string) || '',
          // Google AI 特定欄位
          google_project_id: (config.google_project_id as string) || '',
        },
        max_iterations: agent.max_iterations || 10,
        status: agent.status,
      });
    }
  }, [agent]);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<AgentFormData>) => api.put(`/agents/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', id] });
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      navigate(`/agents/${id}`);
    },
    onError: (error: Error) => {
      setErrors({ general: error.message });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/agents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      navigate('/agents');
    },
    onError: (error: Error) => {
      setErrors({ general: error.message });
    },
  });

  // =============================================================================
  // Handlers
  // =============================================================================

  const updateFormData = (updates: Partial<AgentFormData>) => {
    if (formData) {
      setFormData({ ...formData, ...updates });
      setErrors({});
    }
  };

  const toggleTool = (toolId: string) => {
    if (formData) {
      setFormData({
        ...formData,
        tools: formData.tools.includes(toolId)
          ? formData.tools.filter((t) => t !== toolId)
          : [...formData.tools, toolId],
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData?.name.trim()) {
      newErrors.name = 'Agent 名稱為必填';
    }

    if (!formData?.instructions.trim()) {
      newErrors.instructions = '指令為必填';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validate() && formData) {
      updateMutation.mutate(formData);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate();
  };

  // =============================================================================
  // Render
  // =============================================================================

  if (isLoading || !formData) {
    return <PageLoading />;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(`/agents/${id}`)}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">編輯 Agent</h1>
            <p className="text-gray-500">修改 Agent 配置</p>
          </div>
        </div>
        <Button
          variant="destructive"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          刪除
        </Button>
      </div>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-sm text-red-700 mb-4">
              確定要刪除此 Agent 嗎？此操作無法撤銷。
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteConfirm(false)}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? '刪除中...' : '確認刪除'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Alert */}
      {errors.general && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">{errors.general}</p>
        </div>
      )}

      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">基本資訊</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name" required>
                Agent 名稱
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => updateFormData({ name: e.target.value })}
                error={!!errors.name}
              />
              {errors.name && (
                <p className="text-sm text-red-500">{errors.name}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">狀態</Label>
              <Select
                id="status"
                value={formData.status}
                onChange={(e) => updateFormData({ status: e.target.value })}
                options={STATUS_OPTIONS}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => updateFormData({ description: e.target.value })}
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="category">類別</Label>
            <Select
              id="category"
              value={formData.category}
              onChange={(e) => updateFormData({ category: e.target.value })}
              options={CATEGORIES}
            />
          </div>
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">系統指令</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Textarea
              id="instructions"
              value={formData.instructions}
              onChange={(e) => updateFormData({ instructions: e.target.value })}
              rows={10}
              error={!!errors.instructions}
              className="font-mono text-sm"
            />
            {errors.instructions && (
              <p className="text-sm text-red-500">{errors.instructions}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tools */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">工具配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {AVAILABLE_TOOLS.map((tool) => (
              <div
                key={tool.id}
                onClick={() => toggleTool(tool.id)}
                className={`p-3 border rounded-lg cursor-pointer transition-all ${
                  formData.tools.includes(tool.id)
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                      formData.tools.includes(tool.id)
                        ? 'bg-primary border-primary'
                        : 'border-gray-300'
                    }`}
                  >
                    {formData.tools.includes(tool.id) && (
                      <Check className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-sm">{tool.name}</p>
                    <p className="text-xs text-gray-500">{tool.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Model Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">模型設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Provider and Model Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="provider">模型供應商</Label>
              <Select
                id="provider"
                value={formData.model_config_data.provider}
                onChange={(e) =>
                  updateFormData({
                    model_config_data: {
                      ...formData.model_config_data,
                      provider: e.target.value,
                      // Reset model when provider changes
                      model: MODELS_BY_PROVIDER[e.target.value]?.[0]?.value || 'gpt-4o',
                    },
                  })
                }
                options={MODEL_PROVIDERS}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">模型</Label>
              {formData.model_config_data.provider === 'azure_openai' ? (
                // Azure OpenAI: 自行填寫
                <>
                  <Input
                    id="model"
                    value={formData.model_config_data.model}
                    onChange={(e) =>
                      updateFormData({
                        model_config_data: {
                          ...formData.model_config_data,
                          model: e.target.value,
                        },
                      })
                    }
                    placeholder="例如：gpt-4o、gpt-4、gpt-35-turbo"
                  />
                  <p className="text-xs text-gray-500">
                    輸入在 Azure AI Foundry 中部署的模型名稱
                  </p>
                </>
              ) : (
                // 其他供應商：保留下拉選單
                <Select
                  id="model"
                  value={formData.model_config_data.model}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        model: e.target.value,
                      },
                    })
                  }
                  options={
                    MODELS_BY_PROVIDER[formData.model_config_data.provider]?.map((m) => ({
                      value: m.value,
                      label: m.label,
                    })) || []
                  }
                />
              )}
            </div>
          </div>

          {/* Model Description - 只顯示非 Azure OpenAI 供應商 */}
          {formData.model_config_data.provider !== 'azure_openai' && (() => {
            const selectedModel = MODELS_BY_PROVIDER[formData.model_config_data.provider]?.find(
              (m) => m.value === formData.model_config_data.model
            );
            return selectedModel ? (
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  <span className="font-medium">{selectedModel.label}</span>: {selectedModel.description}
                </p>
              </div>
            ) : null;
          })()}

          {/* Custom Model Input for local provider */}
          {formData.model_config_data.provider === 'local' &&
           formData.model_config_data.model === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="custom_model">自訂模型名稱</Label>
              <Input
                id="custom_model"
                placeholder="輸入模型名稱，例如：llama-3.2-8b"
                onChange={(e) =>
                  updateFormData({
                    model_config_data: {
                      ...formData.model_config_data,
                      model: e.target.value || 'custom',
                    },
                  })
                }
              />
            </div>
          )}

          {/* Provider-specific Configuration */}
          <div className="border-t pt-4 mt-4">
            <p className="text-sm font-medium text-gray-700 mb-3">
              {MODEL_PROVIDERS.find(p => p.value === formData.model_config_data.provider)?.label} 設定
            </p>
          </div>

          {/* Azure OpenAI Configuration */}
          {formData.model_config_data.provider === 'azure_openai' && (
            <div className="space-y-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="space-y-2">
                <Label htmlFor="azure_endpoint" required>Azure OpenAI 端點</Label>
                <Input
                  id="azure_endpoint"
                  type="url"
                  value={formData.model_config_data.azure_endpoint || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        azure_endpoint: e.target.value,
                      },
                    })
                  }
                  placeholder="https://your-resource.openai.azure.com/"
                />
                <p className="text-xs text-gray-500">
                  Azure AI Foundry 中的 OpenAI 資源端點 URL
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="azure_deployment_name" required>部署名稱</Label>
                <Input
                  id="azure_deployment_name"
                  value={formData.model_config_data.azure_deployment_name || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        azure_deployment_name: e.target.value,
                      },
                    })
                  }
                  placeholder="gpt-4o-deployment"
                />
                <p className="text-xs text-gray-500">
                  在 Azure AI Foundry 中創建的模型部署名稱
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="azure_api_version" required>API 版本</Label>
                <Input
                  id="azure_api_version"
                  value={formData.model_config_data.azure_api_version || '2024-10-21'}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        azure_api_version: e.target.value,
                      },
                    })
                  }
                  placeholder="例如：2024-10-21、2024-08-01-preview"
                />
                <p className="text-xs text-gray-500">
                  Azure OpenAI API 版本，可在 Azure AI Foundry 文檔中查看支援的版本
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="azure_api_key" required>API 金鑰</Label>
                <Input
                  id="azure_api_key"
                  type="password"
                  value={formData.model_config_data.api_key || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        api_key: e.target.value,
                      },
                    })
                  }
                  placeholder="輸入 Azure OpenAI API 金鑰"
                />
                <p className="text-xs text-gray-500">
                  在 Azure AI Foundry 「金鑰和端點」頁面取得
                </p>
              </div>
            </div>
          )}

          {/* OpenAI Configuration */}
          {formData.model_config_data.provider === 'openai' && (
            <div className="space-y-4 p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="space-y-2">
                <Label htmlFor="openai_api_key" required>API 金鑰</Label>
                <Input
                  id="openai_api_key"
                  type="password"
                  value={formData.model_config_data.api_key || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        api_key: e.target.value,
                      },
                    })
                  }
                  placeholder="sk-..."
                />
                <p className="text-xs text-gray-500">
                  在 <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">OpenAI Platform</a> 取得 API 金鑰
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="openai_org_id">組織 ID（選填）</Label>
                <Input
                  id="openai_org_id"
                  value={formData.model_config_data.openai_org_id || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        openai_org_id: e.target.value,
                      },
                    })
                  }
                  placeholder="org-..."
                />
                <p className="text-xs text-gray-500">
                  如果您屬於多個組織，請指定組織 ID
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="openai_base_url">自訂端點（選填）</Label>
                <Input
                  id="openai_base_url"
                  type="url"
                  value={formData.model_config_data.base_url || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        base_url: e.target.value,
                      },
                    })
                  }
                  placeholder="https://api.openai.com/v1"
                />
                <p className="text-xs text-gray-500">
                  如使用 OpenAI 兼容的第三方服務，請輸入其 API 端點
                </p>
              </div>
            </div>
          )}

          {/* Anthropic Configuration */}
          {formData.model_config_data.provider === 'anthropic' && (
            <div className="space-y-4 p-4 bg-orange-50 rounded-lg border border-orange-200">
              <div className="space-y-2">
                <Label htmlFor="anthropic_api_key" required>API 金鑰</Label>
                <Input
                  id="anthropic_api_key"
                  type="password"
                  value={formData.model_config_data.api_key || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        api_key: e.target.value,
                      },
                    })
                  }
                  placeholder="sk-ant-..."
                />
                <p className="text-xs text-gray-500">
                  在 <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Anthropic Console</a> 取得 API 金鑰
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="anthropic_base_url">自訂端點（選填）</Label>
                <Input
                  id="anthropic_base_url"
                  type="url"
                  value={formData.model_config_data.base_url || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        base_url: e.target.value,
                      },
                    })
                  }
                  placeholder="https://api.anthropic.com"
                />
                <p className="text-xs text-gray-500">
                  如使用代理或自訂端點，請在此輸入
                </p>
              </div>
            </div>
          )}

          {/* Google AI Configuration */}
          {formData.model_config_data.provider === 'google' && (
            <div className="space-y-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="space-y-2">
                <Label htmlFor="google_api_key" required>API 金鑰</Label>
                <Input
                  id="google_api_key"
                  type="password"
                  value={formData.model_config_data.api_key || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        api_key: e.target.value,
                      },
                    })
                  }
                  placeholder="AIza..."
                />
                <p className="text-xs text-gray-500">
                  在 <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Google AI Studio</a> 取得 API 金鑰
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="google_project_id">Google Cloud 專案 ID（選填）</Label>
                <Input
                  id="google_project_id"
                  value={formData.model_config_data.google_project_id || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        google_project_id: e.target.value,
                      },
                    })
                  }
                  placeholder="my-project-123"
                />
                <p className="text-xs text-gray-500">
                  如使用 Vertex AI，請輸入 Google Cloud 專案 ID
                </p>
              </div>
            </div>
          )}

          {/* Local Model Configuration */}
          {formData.model_config_data.provider === 'local' && (
            <div className="space-y-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="space-y-2">
                <Label htmlFor="local_base_url" required>服務端點</Label>
                <Input
                  id="local_base_url"
                  type="url"
                  value={formData.model_config_data.base_url || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        base_url: e.target.value,
                      },
                    })
                  }
                  placeholder="http://localhost:11434"
                />
                <p className="text-xs text-gray-500">
                  本地模型服務的 API 端點（如 Ollama: http://localhost:11434，vLLM: http://localhost:8000）
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="local_api_key">API 金鑰（選填）</Label>
                <Input
                  id="local_api_key"
                  type="password"
                  value={formData.model_config_data.api_key || ''}
                  onChange={(e) =>
                    updateFormData({
                      model_config_data: {
                        ...formData.model_config_data,
                        api_key: e.target.value,
                      },
                    })
                  }
                  placeholder="如有設定 API 金鑰，請在此輸入"
                />
                <p className="text-xs text-gray-500">
                  如果本地服務設有 API 金鑰驗證，請在此輸入
                </p>
              </div>
            </div>
          )}

          <div className="border-t pt-4 mt-4">
            <p className="text-sm font-medium text-gray-700 mb-3">模型參數</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="temperature">Temperature: {formData.model_config_data.temperature}</Label>
            <input
              type="range"
              id="temperature"
              min="0"
              max="2"
              step="0.1"
              value={formData.model_config_data.temperature}
              onChange={(e) =>
                updateFormData({
                  model_config_data: {
                    ...formData.model_config_data,
                    temperature: parseFloat(e.target.value),
                  },
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500">
              較低的值 (0-0.3) 產生更確定的回應，較高的值 (0.7-1.5) 產生更有創意的回應
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_tokens">最大 Tokens</Label>
              <Input
                type="number"
                id="max_tokens"
                value={formData.model_config_data.max_tokens}
                onChange={(e) =>
                  updateFormData({
                    model_config_data: {
                      ...formData.model_config_data,
                      max_tokens: parseInt(e.target.value) || 2000,
                    },
                  })
                }
                min={100}
                max={128000}
              />
              <p className="text-xs text-gray-500">控制回應的最大長度</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_iterations">最大迭代次數</Label>
              <Input
                type="number"
                id="max_iterations"
                value={formData.max_iterations}
                onChange={(e) =>
                  updateFormData({
                    max_iterations: parseInt(e.target.value) || 10,
                  })
                }
                min={1}
                max={100}
              />
              <p className="text-xs text-gray-500">Agent 執行的最大循環次數</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Version Info */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>版本: {agent?.version}</span>
            <span>·</span>
            <span>
              最後更新:{' '}
              {agent?.updated_at
                ? new Date(agent.updated_at).toLocaleString('zh-TW')
                : '-'}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end">
        <Button onClick={handleSubmit} disabled={updateMutation.isPending}>
          <Save className="w-4 h-4 mr-2" />
          {updateMutation.isPending ? '儲存中...' : '儲存變更'}
        </Button>
      </div>
    </div>
  );
}
