// =============================================================================
// IPA Platform - Create Agent Page
// =============================================================================
// Sprint 5: Frontend UI - Agent Management
//
// Multi-step form for creating new AI agents following Microsoft Agent Framework
// patterns. Supports configuration of instructions, tools, and model settings.
// =============================================================================

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Bot,
  FileText,
  Wrench,
  Settings,
  Eye,
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
}

interface FormErrors {
  name?: string;
  instructions?: string;
  general?: string;
}

// =============================================================================
// Constants
// =============================================================================

const STEPS = [
  { id: 1, title: '基本資訊', icon: Bot },
  { id: 2, title: '指令設定', icon: FileText },
  { id: 3, title: '工具配置', icon: Wrench },
  { id: 4, title: '模型設定', icon: Settings },
  { id: 5, title: '確認建立', icon: Eye },
];

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

const AVAILABLE_TOOLS = [
  { id: 'search_knowledge_base', name: '知識庫搜索', description: '搜索內部知識庫' },
  { id: 'get_customer_info', name: '客戶資訊查詢', description: '獲取客戶資料' },
  { id: 'create_ticket', name: '建立工單', description: '建立支援工單' },
  { id: 'send_email', name: '發送郵件', description: '發送電子郵件通知' },
  { id: 'query_database', name: '資料庫查詢', description: '查詢業務資料庫' },
  { id: 'web_search', name: '網路搜索', description: '搜索網路資訊' },
];

const DEFAULT_FORM_DATA: AgentFormData = {
  name: '',
  description: '',
  category: 'general',
  instructions: '',
  tools: [],
  model_config_data: {
    provider: 'azure_openai',
    model: 'gpt-4o',
    temperature: 0.7,
    max_tokens: 2000,
  },
  max_iterations: 10,
};

// =============================================================================
// Component
// =============================================================================

export function CreateAgentPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<AgentFormData>(DEFAULT_FORM_DATA);
  const [errors, setErrors] = useState<FormErrors>({});

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: AgentFormData) => api.post('/agents/', data),
    onSuccess: () => {
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
    setFormData((prev) => ({ ...prev, ...updates }));
    setErrors({});
  };

  const toggleTool = (toolId: string) => {
    setFormData((prev) => ({
      ...prev,
      tools: prev.tools.includes(toolId)
        ? prev.tools.filter((t) => t !== toolId)
        : [...prev.tools, toolId],
    }));
  };

  const validateStep = (step: number): boolean => {
    const newErrors: FormErrors = {};

    if (step === 1) {
      if (!formData.name.trim()) {
        newErrors.name = 'Agent 名稱為必填';
      } else if (formData.name.length > 255) {
        newErrors.name = 'Agent 名稱不能超過 255 個字元';
      }
    }

    if (step === 2) {
      if (!formData.instructions.trim()) {
        newErrors.instructions = '指令為必填，請輸入 Agent 的系統提示詞';
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
                Agent 名稱
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => updateFormData({ name: e.target.value })}
                placeholder="例如：customer-support-agent"
                error={!!errors.name}
              />
              {errors.name && (
                <p className="text-sm text-red-500">{errors.name}</p>
              )}
              <p className="text-xs text-gray-500">
                唯一識別名稱，建議使用英文和連字符
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => updateFormData({ description: e.target.value })}
                placeholder="描述這個 Agent 的用途和功能..."
                rows={3}
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
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="instructions" required>
                系統指令 (System Prompt)
              </Label>
              <Textarea
                id="instructions"
                value={formData.instructions}
                onChange={(e) => updateFormData({ instructions: e.target.value })}
                placeholder={`你是一個專業的客服代理，負責幫助用戶解決問題。

你的職責包括：
1. 回答客戶的問題
2. 提供產品資訊
3. 協助處理訂單問題

請始終保持禮貌和專業。`}
                rows={12}
                error={!!errors.instructions}
                className="font-mono text-sm"
              />
              {errors.instructions && (
                <p className="text-sm text-red-500">{errors.instructions}</p>
              )}
              <p className="text-xs text-gray-500">
                定義 Agent 的角色、職責和行為準則。這是 Agent 執行任務時的核心指令。
              </p>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div>
              <Label>可用工具</Label>
              <p className="text-sm text-gray-500 mb-4">
                選擇此 Agent 可以使用的工具。工具將決定 Agent 能執行的操作。
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {AVAILABLE_TOOLS.map((tool) => (
                  <div
                    key={tool.id}
                    onClick={() => toggleTool(tool.id)}
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
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

              <p className="text-xs text-gray-500 mt-4">
                已選擇 {formData.tools.length} 個工具
              </p>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            {/* Model Provider Selection */}
            <div className="space-y-2">
              <Label htmlFor="provider">模型供應商</Label>
              <Select
                id="provider"
                value={formData.model_config_data.provider}
                onChange={(e) => {
                  const newProvider = e.target.value;
                  const firstModel = MODELS_BY_PROVIDER[newProvider]?.[0]?.value || '';
                  updateFormData({
                    model_config_data: {
                      ...formData.model_config_data,
                      provider: newProvider,
                      model: firstModel,
                    },
                  });
                }}
                options={MODEL_PROVIDERS}
              />
              <p className="text-xs text-gray-500">
                選擇 AI 模型的供應商
              </p>
            </div>

            {/* Model Selection */}
            <div className="space-y-2">
              <Label htmlFor="model">模型</Label>
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
                options={(MODELS_BY_PROVIDER[formData.model_config_data.provider] || []).map((m) => ({
                  value: m.value,
                  label: m.label,
                }))}
              />
              {/* Show model description */}
              {formData.model_config_data.model && (
                <p className="text-xs text-gray-500">
                  {MODELS_BY_PROVIDER[formData.model_config_data.provider]?.find(
                    (m) => m.value === formData.model_config_data.model
                  )?.description || ''}
                </p>
              )}
            </div>

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
                  <Select
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
                    options={AZURE_API_VERSIONS}
                  />
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
                    在 OpenAI Platform 取得 API 金鑰
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
                    在 Anthropic Console 取得 API 金鑰
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
                    在 Google AI Studio 取得 API 金鑰
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

            {/* Temperature */}
            <div className="space-y-2">
              <Label htmlFor="temperature">Temperature</Label>
              <div className="flex items-center gap-4">
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
                  className="flex-1"
                />
                <span className="w-12 text-sm font-mono">
                  {formData.model_config_data.temperature}
                </span>
              </div>
              <p className="text-xs text-gray-500">
                控制輸出的隨機性。較低值 (0-0.5) 產生更確定的輸出，較高值 (0.5-2) 更有創意
              </p>
            </div>

            {/* Max Tokens */}
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
              <p className="text-xs text-gray-500">
                單次回應的最大 token 數量，不同模型上限不同
              </p>
            </div>

            {/* Max Iterations */}
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
              <p className="text-xs text-gray-500">
                Agent 執行任務時的最大推理循環次數 (1-100)
              </p>
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <div>
                <p className="text-sm font-medium text-gray-700">Agent 名稱</p>
                <p className="text-sm">{formData.name || '(未設定)'}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">描述</p>
                <p className="text-sm">{formData.description || '(無描述)'}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">類別</p>
                <Badge variant="secondary">
                  {CATEGORIES.find((c) => c.value === formData.category)?.label}
                </Badge>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">系統指令</p>
                <pre className="text-sm bg-white p-3 rounded border mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">
                  {formData.instructions || '(未設定)'}
                </pre>
              </div>

              <div>
                <p className="text-sm font-medium text-gray-700">啟用工具</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {formData.tools.length > 0 ? (
                    formData.tools.map((toolId) => {
                      const tool = AVAILABLE_TOOLS.find((t) => t.id === toolId);
                      return (
                        <Badge key={toolId} variant="outline">
                          {tool?.name || toolId}
                        </Badge>
                      );
                    })
                  ) : (
                    <span className="text-sm text-gray-500">(無)</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-700">模型供應商</p>
                  <Badge variant="secondary">
                    {MODEL_PROVIDERS.find((p) => p.value === formData.model_config_data.provider)?.label || formData.model_config_data.provider}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">模型</p>
                  <p className="text-sm">{
                    MODELS_BY_PROVIDER[formData.model_config_data.provider]?.find(
                      (m) => m.value === formData.model_config_data.model
                    )?.label || formData.model_config_data.model
                  }</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-700">Temperature</p>
                  <p className="text-sm">{formData.model_config_data.temperature}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">最大 Tokens</p>
                  <p className="text-sm">{formData.model_config_data.max_tokens}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">最大迭代</p>
                  <p className="text-sm">{formData.max_iterations}</p>
                </div>
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
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/agents')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">建立 Agent</h1>
          <p className="text-gray-500">設定您的 AI Agent 配置</p>
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
                  className={`w-8 md:w-16 h-0.5 mx-2 ${
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
            {createMutation.isPending ? '建立中...' : '建立 Agent'}
            <Check className="w-4 h-4 ml-2" />
          </Button>
        )}
      </div>
    </div>
  );
}
