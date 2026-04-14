/**
 * AgentExpertDetailPage — View full expert configuration.
 *
 * Shows domain badge, capabilities, system prompt, tools, metadata.
 * Edit/Delete buttons with built-in guard.
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { FC } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Lock,
  Copy,
  RefreshCw,
} from 'lucide-react';
import { useExpertDetail, useDeleteExpert, useReloadExperts } from '@/hooks/useExperts';
import { DomainBadge, CapabilitiesChips } from '@/components/unified-chat/agent-team/ExpertBadges';

export const AgentExpertDetailPage: FC = () => {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const { data: expert, isLoading } = useExpertDetail(name || '');
  const deleteMutation = useDeleteExpert();
  const reloadMutation = useReloadExperts();

  if (isLoading) {
    return <div className="p-6 text-center text-muted-foreground">載入中...</div>;
  }

  if (!expert) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">找不到專家: {name}</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/agent-experts')}>
          返回列表
        </Button>
      </div>
    );
  }

  const handleDelete = async () => {
    if (!confirm(`確定要刪除專家「${expert.display_name}」嗎？`)) return;
    await deleteMutation.mutateAsync(expert.name);
    navigate('/agent-experts');
  };

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText((expert as any).system_prompt || '');
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/agent-experts')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              {expert.is_builtin && <Lock className="h-4 w-4 text-muted-foreground" />}
              <h1 className="text-xl font-bold">{expert.display_name}</h1>
            </div>
            <p className="text-sm text-muted-foreground">{expert.display_name_zh}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => reloadMutation.mutateAsync()}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Reload
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate(`/agent-experts/${name}/edit`)}>
            <Pencil className="h-4 w-4 mr-1" />
            編輯
          </Button>
          {!expert.is_builtin && (
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
              <Trash2 className="h-4 w-4 mr-1" />
              刪除
            </Button>
          )}
        </div>
      </div>

      {/* Status + Domain */}
      <div className="flex items-center gap-3">
        <DomainBadge domain={expert.domain} />
        <Badge variant={expert.enabled ? 'default' : 'secondary'}>
          {expert.enabled ? '啟用' : '停用'}
        </Badge>
        {expert.is_builtin && (
          <Badge variant="outline" className="text-xs">
            <Lock className="h-3 w-3 mr-1" />
            內建
          </Badge>
        )}
        <span className="text-xs text-muted-foreground font-mono">
          v{expert.version} · ID: {expert.id?.substring(0, 8)}
        </span>
      </div>

      {/* Description */}
      {expert.description && (
        <Card>
          <CardContent className="p-4">
            <h3 className="text-sm font-semibold mb-1">描述</h3>
            <p className="text-sm text-muted-foreground">{expert.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Capabilities */}
      <Card>
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold mb-2">Capabilities</h3>
          <CapabilitiesChips capabilities={expert.capabilities} maxDisplay={20} />
          {expert.capabilities.length === 0 && (
            <p className="text-xs text-muted-foreground">無已定義的 capabilities</p>
          )}
        </CardContent>
      </Card>

      {/* System Prompt */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">System Prompt</h3>
            <Button variant="ghost" size="sm" onClick={handleCopyPrompt}>
              <Copy className="h-3 w-3 mr-1" />
              Copy
            </Button>
          </div>
          <pre className="bg-secondary p-4 rounded text-xs whitespace-pre-wrap max-h-60 overflow-auto font-mono">
            {(expert as any).system_prompt || '(empty)'}
          </pre>
        </CardContent>
      </Card>

      {/* Tools */}
      <Card>
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold mb-2">Tools ({expert.tools.length})</h3>
          <div className="flex flex-wrap gap-1.5">
            {expert.tools.map((tool) => (
              <Badge key={tool} variant="outline" className="text-xs font-mono">
                {tool}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Model & Config */}
      <Card>
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold mb-2">模型配置</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Model:</span>{' '}
              <span className="font-mono">{expert.model || '(系統預設)'}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Max Iterations:</span>{' '}
              <span className="font-mono">{expert.max_iterations}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Domain:</span>{' '}
              <span className="font-mono">{expert.domain}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Name:</span>{' '}
              <span className="font-mono">{expert.name}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timestamps */}
      <div className="text-xs text-muted-foreground text-right">
        Created: {expert.created_at || 'N/A'} · Updated: {expert.updated_at || 'N/A'}
      </div>
    </div>
  );
};

export default AgentExpertDetailPage;
