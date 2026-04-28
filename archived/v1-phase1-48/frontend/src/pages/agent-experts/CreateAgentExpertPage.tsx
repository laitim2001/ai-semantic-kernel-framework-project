/**
 * CreateAgentExpertPage — 5-step form to create a new Agent Expert.
 *
 * Steps: Basic Info → System Prompt → Tools → Model → Review
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { FC, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  FileText,
  Wrench,
  Cpu,
  CheckCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCreateExpert } from '@/hooks/useExperts';
import { DomainBadge } from '@/components/unified-chat/agent-team/ExpertBadges';

const STEPS = [
  { id: 1, title: '基本資訊', icon: Bot },
  { id: 2, title: 'System Prompt', icon: FileText },
  { id: 3, title: '工具配置', icon: Wrench },
  { id: 4, title: '模型設定', icon: Cpu },
  { id: 5, title: '確認', icon: CheckCircle },
];

const DOMAIN_OPTIONS = [
  { value: 'network', label: '網路' },
  { value: 'database', label: '資料庫' },
  { value: 'application', label: '應用層' },
  { value: 'security', label: '資安' },
  { value: 'cloud', label: '雲端' },
  { value: 'general', label: '通用' },
  { value: 'custom', label: '自訂' },
];

const DEFAULT_TOOLS = [
  'assess_risk', 'search_knowledge', 'search_memory', 'create_task',
  'send_team_message', 'check_my_inbox', 'read_team_messages',
  'view_team_status', 'claim_next_task', 'report_task_result',
];

interface FormData {
  name: string;
  display_name: string;
  display_name_zh: string;
  description: string;
  domain: string;
  enabled: boolean;
  system_prompt: string;
  tools: string[];
  custom_tool: string;
  model: string;
  max_iterations: number;
  capabilities: string[];
  capabilities_input: string;
}

const INITIAL_FORM: FormData = {
  name: '',
  display_name: '',
  display_name_zh: '',
  description: '',
  domain: 'general',
  enabled: true,
  system_prompt: '',
  tools: [...DEFAULT_TOOLS],
  custom_tool: '',
  model: '',
  max_iterations: 5,
  capabilities: [],
  capabilities_input: '',
};

export const CreateAgentExpertPage: FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>({ ...INITIAL_FORM });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const createMutation = useCreateExpert();

  const updateField = <K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const validateStep = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (step === 1) {
      if (!form.name.trim()) newErrors.name = '必填';
      if (!/^[a-z0-9_]+$/.test(form.name)) newErrors.name = '只允許小寫字母、數字、底線';
      if (!form.display_name.trim()) newErrors.display_name = '必填';
      if (!form.display_name_zh.trim()) newErrors.display_name_zh = '必填';
    }
    if (step === 2) {
      if (!form.system_prompt.trim()) newErrors.system_prompt = '必填';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep()) setStep((s) => Math.min(s + 1, 5));
  };

  const handleBack = () => setStep((s) => Math.max(s - 1, 1));

  const handleAddCapability = () => {
    if (form.capabilities_input.trim()) {
      updateField('capabilities', [...form.capabilities, form.capabilities_input.trim()]);
      updateField('capabilities_input', '');
    }
  };

  const handleAddCustomTool = () => {
    if (form.custom_tool.trim() && !form.tools.includes(form.custom_tool.trim())) {
      updateField('tools', [...form.tools, form.custom_tool.trim()]);
      updateField('custom_tool', '');
    }
  };

  const handleSubmit = async () => {
    try {
      await createMutation.mutateAsync({
        name: form.name,
        display_name: form.display_name,
        display_name_zh: form.display_name_zh,
        description: form.description,
        domain: form.domain,
        capabilities: form.capabilities,
        model: form.model || null,
        max_iterations: form.max_iterations,
        system_prompt: form.system_prompt,
        tools: form.tools,
        enabled: form.enabled,
      });
      navigate(`/agent-experts/${form.name}`);
    } catch (err) {
      setErrors({ submit: String(err) });
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/agent-experts')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-xl font-bold">建立新專家</h1>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-between px-4">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = step === s.id;
          const isDone = step > s.id;
          return (
            <div key={s.id} className="flex items-center gap-2">
              <div className={cn(
                'flex items-center justify-center h-8 w-8 rounded-full text-xs font-bold',
                isActive ? 'bg-primary text-primary-foreground' :
                isDone ? 'bg-green-100 text-green-700' : 'bg-secondary text-muted-foreground'
              )}>
                {isDone ? <CheckCircle className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </div>
              <span className={cn('text-xs hidden sm:inline', isActive ? 'font-semibold' : 'text-muted-foreground')}>
                {s.title}
              </span>
              {i < STEPS.length - 1 && <div className="w-8 h-px bg-border mx-1" />}
            </div>
          );
        })}
      </div>

      {/* Form body */}
      <Card>
        <CardContent className="p-6 space-y-4">

          {/* Step 1: Basic Info */}
          {step === 1 && (
            <>
              <div className="space-y-2">
                <Label>名稱 (slug)</Label>
                <Input value={form.name} onChange={(e) => updateField('name', e.target.value)} placeholder="e.g. devops_expert" />
                {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>英文顯示名稱</Label>
                  <Input value={form.display_name} onChange={(e) => updateField('display_name', e.target.value)} placeholder="DevOps Expert" />
                  {errors.display_name && <p className="text-xs text-destructive">{errors.display_name}</p>}
                </div>
                <div className="space-y-2">
                  <Label>中文顯示名稱</Label>
                  <Input value={form.display_name_zh} onChange={(e) => updateField('display_name_zh', e.target.value)} placeholder="DevOps 專家" />
                  {errors.display_name_zh && <p className="text-xs text-destructive">{errors.display_name_zh}</p>}
                </div>
              </div>
              <div className="space-y-2">
                <Label>描述</Label>
                <Textarea value={form.description} onChange={(e) => updateField('description', e.target.value)} placeholder="專家的能力描述..." rows={2} />
              </div>
              <div className="space-y-2">
                <Label>Domain</Label>
                <div className="flex flex-wrap gap-2">
                  {DOMAIN_OPTIONS.map((opt) => (
                    <button key={opt.value} onClick={() => updateField('domain', opt.value)}
                      className={cn('px-3 py-1.5 text-xs rounded-full font-medium transition-colors',
                        form.domain === opt.value ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                      )}>{opt.label}</button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Capabilities</Label>
                <div className="flex gap-2">
                  <Input value={form.capabilities_input} onChange={(e) => updateField('capabilities_input', e.target.value)}
                    placeholder="e.g. container_deployment" onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCapability())} />
                  <Button variant="outline" size="sm" onClick={handleAddCapability}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {form.capabilities.map((cap) => (
                    <Badge key={cap} variant="outline" className="text-xs cursor-pointer"
                      onClick={() => updateField('capabilities', form.capabilities.filter((c) => c !== cap))}>
                      {cap} ×
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={form.enabled} onChange={(e) => updateField('enabled', e.target.checked)} id="enabled" />
                <Label htmlFor="enabled">啟用</Label>
              </div>
            </>
          )}

          {/* Step 2: System Prompt */}
          {step === 2 && (
            <div className="space-y-2">
              <Label>System Prompt</Label>
              <Textarea value={form.system_prompt} onChange={(e) => updateField('system_prompt', e.target.value)}
                placeholder="你是一位資深...專家，專精於：&#10;- ...&#10;- ...&#10;&#10;請用結構化方式分析問題，給出具體的排查步驟和建議。"
                rows={15} className="font-mono text-sm" />
              {errors.system_prompt && <p className="text-xs text-destructive">{errors.system_prompt}</p>}
              <p className="text-xs text-muted-foreground text-right">{form.system_prompt.length} 字元</p>
            </div>
          )}

          {/* Step 3: Tools */}
          {step === 3 && (
            <div className="space-y-4">
              <Label>可用工具</Label>
              <div className="grid grid-cols-2 gap-2">
                {DEFAULT_TOOLS.map((tool) => (
                  <label key={tool} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={form.tools.includes(tool)}
                      onChange={(e) => updateField('tools', e.target.checked
                        ? [...form.tools, tool] : form.tools.filter((t) => t !== tool))} />
                    {tool}
                  </label>
                ))}
              </div>
              <div className="space-y-2">
                <Label>自訂工具</Label>
                <div className="flex gap-2">
                  <Input value={form.custom_tool} onChange={(e) => updateField('custom_tool', e.target.value)}
                    placeholder="custom_tool_name" onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCustomTool())} />
                  <Button variant="outline" size="sm" onClick={handleAddCustomTool}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {form.tools.filter((t) => !DEFAULT_TOOLS.includes(t)).map((tool) => (
                    <Badge key={tool} variant="outline" className="text-xs cursor-pointer"
                      onClick={() => updateField('tools', form.tools.filter((t) => t !== tool))}>
                      {tool} ×
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Model */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>LLM Model (留空使用系統預設)</Label>
                <Input value={form.model} onChange={(e) => updateField('model', e.target.value)}
                  placeholder="e.g. gpt-5.4-mini" />
                <p className="text-xs text-muted-foreground">指定此專家使用的 LLM 模型。留空則使用系統預設模型。</p>
              </div>
              <div className="space-y-2">
                <Label>Max Iterations</Label>
                <Input type="number" min={1} max={20} value={form.max_iterations}
                  onChange={(e) => updateField('max_iterations', parseInt(e.target.value) || 5)} />
                <p className="text-xs text-muted-foreground">工具呼叫的最大迭代次數 (1-20)</p>
              </div>
            </div>
          )}

          {/* Step 5: Review */}
          {step === 5 && (
            <div className="space-y-4">
              <h3 className="font-semibold">確認建立以下專家</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-muted-foreground">Name:</span> <span className="font-mono">{form.name}</span></div>
                <div><span className="text-muted-foreground">Display:</span> {form.display_name}</div>
                <div><span className="text-muted-foreground">中文:</span> {form.display_name_zh}</div>
                <div className="flex items-center gap-1"><span className="text-muted-foreground">Domain:</span> <DomainBadge domain={form.domain} /></div>
                <div><span className="text-muted-foreground">Model:</span> {form.model || '(系統預設)'}</div>
                <div><span className="text-muted-foreground">Max Iter:</span> {form.max_iterations}</div>
                <div><span className="text-muted-foreground">Enabled:</span> {form.enabled ? 'Yes' : 'No'}</div>
                <div><span className="text-muted-foreground">Tools:</span> {form.tools.length} 個</div>
              </div>
              <div className="space-y-1">
                <span className="text-sm text-muted-foreground">Capabilities:</span>
                <div className="flex flex-wrap gap-1">
                  {form.capabilities.map((c) => <Badge key={c} variant="outline" className="text-xs">{c}</Badge>)}
                  {form.capabilities.length === 0 && <span className="text-xs text-muted-foreground">(none)</span>}
                </div>
              </div>
              <div className="space-y-1">
                <span className="text-sm text-muted-foreground">System Prompt (preview):</span>
                <pre className="bg-secondary p-3 rounded text-xs whitespace-pre-wrap max-h-40 overflow-auto">
                  {form.system_prompt}
                </pre>
              </div>
              {errors.submit && <p className="text-sm text-destructive">{errors.submit}</p>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={step === 1 ? () => navigate('/agent-experts') : handleBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          {step === 1 ? '取消' : '上一步'}
        </Button>
        {step < 5 ? (
          <Button onClick={handleNext}>
            下一步
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {createMutation.isPending ? '建立中...' : '確認建立'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default CreateAgentExpertPage;
