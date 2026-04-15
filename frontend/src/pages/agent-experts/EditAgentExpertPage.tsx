/**
 * EditAgentExpertPage — Edit an existing Agent Expert definition.
 *
 * Same 5-step form as Create, pre-filled from API.
 * Built-in experts show a warning banner.
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { FC, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useExpertDetail, useUpdateExpert } from '@/hooks/useExperts';
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

export const EditAgentExpertPage: FC = () => {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const { data: expert, isLoading } = useExpertDetail(name || '');
  const updateMutation = useUpdateExpert();

  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (expert && !form) {
      setForm({
        display_name: expert.display_name,
        display_name_zh: expert.display_name_zh,
        description: expert.description || '',
        domain: expert.domain,
        enabled: expert.enabled,
        system_prompt: (expert as any).system_prompt || '',
        tools: expert.tools || [],
        custom_tool: '',
        model: expert.model || '',
        max_iterations: expert.max_iterations,
        capabilities: expert.capabilities || [],
        capabilities_input: '',
      });
    }
  }, [expert, form]);

  if (isLoading || !form) {
    return <div className="p-6 text-center text-muted-foreground">載入中...</div>;
  }

  const updateField = <K extends keyof FormData>(key: K, value: FormData[K]) => {
    setForm((prev) => prev ? { ...prev, [key]: value } : prev);
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const validateStep = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (step === 1) {
      if (!form.display_name.trim()) newErrors.display_name = '必填';
      if (!form.display_name_zh.trim()) newErrors.display_name_zh = '必填';
    }
    if (step === 2) {
      if (!form.system_prompt.trim()) newErrors.system_prompt = '必填';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => { if (validateStep()) setStep((s) => Math.min(s + 1, 5)); };
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
    if (!name) return;
    try {
      await updateMutation.mutateAsync({
        name,
        data: {
          display_name: form.display_name,
          display_name_zh: form.display_name_zh,
          description: form.description,
          domain: form.domain,
          capabilities: form.capabilities,
          model: form.model || undefined,
          max_iterations: form.max_iterations,
          system_prompt: form.system_prompt,
          tools: form.tools,
          enabled: form.enabled,
        },
      });
      navigate(`/agent-experts/${name}`);
    } catch (err) {
      setErrors({ submit: String(err) });
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/agent-experts/${name}`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-xl font-bold">編輯專家: {expert?.display_name}</h1>
      </div>

      {/* Built-in warning */}
      {expert?.is_builtin && (
        <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <span className="text-sm text-yellow-800 dark:text-yellow-200">
            此為內建專家，修改將覆蓋預設值。可透過 Reload 恢復。
          </span>
        </div>
      )}

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

      {/* Form */}
      <Card>
        <CardContent className="p-6 space-y-4">
          {step === 1 && (
            <>
              <div className="space-y-2">
                <Label>名稱 (不可修改)</Label>
                <Input value={name || ''} disabled className="bg-secondary" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>英文顯示名稱</Label>
                  <Input value={form.display_name} onChange={(e) => updateField('display_name', e.target.value)} />
                  {errors.display_name && <p className="text-xs text-destructive">{errors.display_name}</p>}
                </div>
                <div className="space-y-2">
                  <Label>中文顯示名稱</Label>
                  <Input value={form.display_name_zh} onChange={(e) => updateField('display_name_zh', e.target.value)} />
                  {errors.display_name_zh && <p className="text-xs text-destructive">{errors.display_name_zh}</p>}
                </div>
              </div>
              <div className="space-y-2">
                <Label>描述</Label>
                <Textarea value={form.description} onChange={(e) => updateField('description', e.target.value)} rows={2} />
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
                      onClick={() => updateField('capabilities', form.capabilities.filter((c) => c !== cap))}>{cap} ×</Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={form.enabled} onChange={(e) => updateField('enabled', e.target.checked)} id="enabled" />
                <Label htmlFor="enabled">啟用</Label>
              </div>
            </>
          )}

          {step === 2 && (
            <div className="space-y-2">
              <Label>System Prompt</Label>
              <Textarea value={form.system_prompt} onChange={(e) => updateField('system_prompt', e.target.value)} rows={15} className="font-mono text-sm" />
              {errors.system_prompt && <p className="text-xs text-destructive">{errors.system_prompt}</p>}
              <p className="text-xs text-muted-foreground text-right">{form.system_prompt.length} 字元</p>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <Label>可用工具</Label>
              <div className="grid grid-cols-2 gap-2">
                {DEFAULT_TOOLS.map((tool) => (
                  <label key={tool} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={form.tools.includes(tool)}
                      onChange={(e) => updateField('tools', e.target.checked ? [...form.tools, tool] : form.tools.filter((t) => t !== tool))} />
                    {tool}
                  </label>
                ))}
              </div>
              <div className="space-y-2">
                <Label>自訂工具</Label>
                <div className="flex gap-2">
                  <Input value={form.custom_tool} onChange={(e) => updateField('custom_tool', e.target.value)} placeholder="custom_tool_name"
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCustomTool())} />
                  <Button variant="outline" size="sm" onClick={handleAddCustomTool}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {form.tools.filter((t) => !DEFAULT_TOOLS.includes(t)).map((tool) => (
                    <Badge key={tool} variant="outline" className="text-xs cursor-pointer"
                      onClick={() => updateField('tools', form.tools.filter((t) => t !== tool))}>{tool} ×</Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>LLM Model (留空使用系統預設)</Label>
                <Input value={form.model} onChange={(e) => updateField('model', e.target.value)} placeholder="e.g. gpt-5.4-mini" />
              </div>
              <div className="space-y-2">
                <Label>Max Iterations</Label>
                <Input type="number" min={1} max={20} value={form.max_iterations} onChange={(e) => updateField('max_iterations', parseInt(e.target.value) || 5)} />
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4">
              <h3 className="font-semibold">確認更新</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-muted-foreground">Name:</span> <span className="font-mono">{name}</span></div>
                <div><span className="text-muted-foreground">Display:</span> {form.display_name}</div>
                <div><span className="text-muted-foreground">中文:</span> {form.display_name_zh}</div>
                <div className="flex items-center gap-1"><span className="text-muted-foreground">Domain:</span> <DomainBadge domain={form.domain} /></div>
                <div><span className="text-muted-foreground">Model:</span> {form.model || '(系統預設)'}</div>
                <div><span className="text-muted-foreground">Tools:</span> {form.tools.length} 個</div>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">System Prompt:</span>
                <pre className="bg-secondary p-3 rounded text-xs whitespace-pre-wrap max-h-40 overflow-auto mt-1">{form.system_prompt}</pre>
              </div>
              {errors.submit && <p className="text-sm text-destructive">{errors.submit}</p>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={step === 1 ? () => navigate(`/agent-experts/${name}`) : handleBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />{step === 1 ? '取消' : '上一步'}
        </Button>
        {step < 5 ? (
          <Button onClick={handleNext}>下一步 <ArrowRight className="h-4 w-4 ml-1" /></Button>
        ) : (
          <Button onClick={handleSubmit} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? '更新中...' : '確認更新'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default EditAgentExpertPage;
